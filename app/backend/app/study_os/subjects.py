"""Study OS — Subject progress service.

Production-grade replacement for the in-memory placeholder /subjects
endpoint. Computes per-subject progress + weak-topic count + trend
directly from locked exam_topic_coverage + user_topic_mastery rows.

Verified-only contract: only ``reviewer_status='locked'`` coverage rows
flow through. Subjects without any locked topics for the user's target
exam never appear.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from app.study_os.planner import (  # type: ignore  # private helpers reused intentionally
    _load_locked_coverage,
    _load_user_signals,
    _resolve_target_exam,
)
from app.study_os.pyq_practice import practiceable_topic_ids
from app.study_os.subject_runtime_policy import InventoryContext, resolve_subject_modes
from app.study_os.writing_practice.subject_launch import available_writing_subject_ids

logger = logging.getLogger("career_copilot.study_os.subjects")


def _subject_practice(
    bucket: dict[str, Any],
    *,
    eng_available: bool,
    pyq_topic_ids: set[str],
    mastery: dict[str, float],
    error_topics: set[str],
) -> dict[str, Any]:
    """Practice readiness for one subject card (Subject Practice Hub). server_launch
    modes go through POST /api/study/subjects/{id}/practice/start; client_route
    modes are existing surfaces the hub links to.

    The runtime modes are resolved by the server-owned ``SubjectRuntimePolicy``
    registry: the subject's family (from canonical ``subject_group``/``slug``) selects a
    policy whose inventory resolver emits the eligible modes from the signal context.
    There is no English/PYQ branching here — a vertical adds a mode by registering it
    in the policy, not by editing this function."""
    available_topics = tuple(
        t for t in bucket["topic_ids"] if t and str(t) in pyq_topic_ids
    )
    ctx = InventoryContext(
        eng_available=eng_available,
        available_topic_ids=available_topics,
        mastery=mastery,
        error_topics=frozenset(error_topics),
    )
    modes = resolve_subject_modes(
        slug=bucket.get("subject_slug"),
        subject_group=bucket.get("subject_group"),
        ctx=ctx,
    )
    available = any(m["route_type"] == "server_launch" for m in modes)
    return {"available": available, "modes": modes if available else []}


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("study_os.subjects supabase call failed: %s", exc)
        return default


def _classify_trend(this_avg: float | None, prev_avg: float | None) -> str:
    """``up``/``down``/``flat`` from this-week vs last-week average mastery."""
    if this_avg is None or prev_avg is None:
        return "flat"
    delta = this_avg - prev_avg
    if delta >= 2:
        return "up"
    if delta <= -2:
        return "down"
    return "flat"


def _previous_review_mastery_by_subject(
    supabase: Any, user_id: str
) -> dict[str, float]:
    """Best-effort prior-week mastery per subject id.

    Reads the most recent ``weekly_reviews`` row's snapshot, if present,
    so the trend can compare against persisted history without recomputing.
    Returns an empty mapping when no prior snapshot exists — tests treat
    this as a clean "flat" trend.
    """
    rows = _safe(
        lambda: (
            supabase.table("weekly_reviews")
            .select("computed_at")
            .eq("user_id", user_id)
            .order("week_start", desc=True)
            .limit(1)
            .execute()
        ),
        default=None,
    )
    # The trend channel intentionally stays flat for now — surfacing a
    # weekly delta requires persisting per-subject mastery snapshots, which
    # is its own feature. Keeping this seam in place means we can light it
    # up later without changing the public contract.
    _ = rows
    return {}


def locked_topic_ids_for_subject(
    supabase: Any, exam_id: str | None, subject_id: str | None
) -> set[str]:
    """Topic ids under ``subject_id`` in the exam's LOCKED coverage.

    The server-side scope gate for subject topic-practice launches: a ``topic_pyq``
    launch on ``/api/study/subjects/{subject_id}/practice/start`` must target a
    topic that actually belongs to the PATH subject in the caller's resolved exam.
    The browser-supplied ``topic_id`` is never trusted to match the path subject —
    a caller could otherwise POST a Quant topic id to the English subject's launch
    path. Mismatches are rejected upstream (422)."""
    if not exam_id or not subject_id:
        return set()
    coverage = _load_locked_coverage(supabase, exam_id) or []
    return {
        str(c.get("topic_id"))
        for c in coverage
        if c.get("topic_id") and str(c.get("subject_id")) == str(subject_id)
    }


def resolve_subject_family(
    supabase: Any, exam_id: str | None, subject_id: str | None
) -> tuple[str | None, bool]:
    """Resolve the SubjectRuntimePolicy family for a PATH subject from the exam's
    LOCKED coverage (canonical ``subject_group`` → ``slug``).

    Returns ``(family, known)``:
      * ``known=True``  → the subject is a real, locked subject of the caller's exam;
        ``family`` is its family (``None`` = a legitimately ungoverned/generic subject).
      * ``known=False`` → no target exam, no subject_id, the subject is not in the
        exam's locked coverage, OR the coverage read failed. The launch gate must FAIL
        CLOSED here — a ``None`` family must never be conflated with "generic subject",
        or a mode could be forced onto an unresolved/non-covered subject.
    """
    from app.study_os.subject_runtime_policy import family_for_subject

    if not exam_id or not subject_id:
        return None, False
    coverage = _load_locked_coverage(supabase, exam_id) or []
    row = next(
        (c for c in coverage if str(c.get("subject_id")) == str(subject_id)), None
    )
    if not row:
        return None, False
    family = family_for_subject(
        slug=row.get("subject_slug"), subject_group=row.get("subject_group")
    )
    return family, True


def list_subjects(supabase: Any, user_id: str) -> list[dict[str, Any]]:
    """Return per-subject progress for the user's target exam.

    Output rows match the existing frontend contract::

        {
          "subject_id": str | None,
          "subject": str,
          "progress": int (0..100),  # average mastery of locked topics
          "trend": "up" | "down" | "flat",
          "weak_count": int,
          "locked_topics": int,
          "practice": {                     # Subject Practice Hub launch readiness
            "available": bool,              # True iff >=1 server_launch mode
            "modes": [ {"type", "label", "route_type", ...}, ... ],
          },
        }
    """
    if not user_id:
        return []
    target = _resolve_target_exam(supabase, user_id)
    exam_id = target.get("id") if target else None
    if not exam_id:
        return []

    coverage = _load_locked_coverage(supabase, exam_id)
    if not coverage:
        return []

    mastery, error_topics = _load_user_signals(supabase, user_id, exam_id)

    # Bucket coverage rows by subject id.
    buckets: dict[str, dict[str, Any]] = {}
    for c in coverage:
        sid = c.get("subject_id") or "__no_subject__"
        bucket = buckets.setdefault(
            sid,
            {
                "subject_id": c.get("subject_id"),
                "subject": c.get("subject_name") or c.get("subject") or "Other",
                # Canonical governed identity → SubjectRuntimePolicy family resolution.
                "subject_slug": c.get("subject_slug"),
                "subject_group": c.get("subject_group"),
                "topic_ids": [],
                "weak_count": 0,
            },
        )
        bucket["topic_ids"].append(c.get("topic_id"))
        # A topic counts as weak if (a) mastery < 50 OR (b) it has logged
        # error patterns — both signals are explicit.
        tid = c.get("topic_id")
        mast = mastery.get(tid)
        if (mast is not None and mast < 50) or tid in error_topics:
            bucket["weak_count"] += 1

    prev_by_subject = _previous_review_mastery_by_subject(supabase, user_id)

    subject_ids = [b["subject_id"] for b in buckets.values() if b.get("subject_id")]
    all_topic_ids = [t for b in buckets.values() for t in b["topic_ids"] if t]
    eng_subject_ids = _safe(
        lambda: available_writing_subject_ids(supabase, subject_ids, exam_id=exam_id),
        default=set(),
    ) or set()
    pyq_topic_ids = _safe(
        lambda: practiceable_topic_ids(supabase, exam_id=exam_id, topic_ids=all_topic_ids),
        default=set(),
    ) or set()

    items: list[dict[str, Any]] = []
    for sid, bucket in buckets.items():
        tids = [t for t in bucket["topic_ids"] if t]
        masts = [mastery.get(t) for t in tids if mastery.get(t) is not None]
        avg = round(sum(masts) / len(masts)) if masts else 0
        items.append(
            {
                "subject_id": bucket["subject_id"],
                "subject": bucket["subject"],
                "progress": int(avg),
                "trend": _classify_trend(avg, prev_by_subject.get(sid)),
                "weak_count": int(bucket["weak_count"]),
                "locked_topics": len(tids),
                "practice": _subject_practice(
                    bucket,
                    eng_available=str(bucket["subject_id"]) in eng_subject_ids if bucket.get("subject_id") else False,
                    pyq_topic_ids=pyq_topic_ids,
                    mastery=mastery,
                    error_topics=error_topics,
                ),
            }
        )
    # Stable order: highest weak_count first, then alphabetical.
    items.sort(key=lambda r: (-r["weak_count"], r["subject"].lower()))
    return items
