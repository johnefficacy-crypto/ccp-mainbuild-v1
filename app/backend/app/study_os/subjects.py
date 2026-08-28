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
from app.exam_intelligence.coverage import verified_pyq_topic_counts
from app.current_affairs.bundles import resolve_eligible_bundle
from app.study_os.pyq_practice import practiceable_topic_ids
from app.study_os.subject_runtime_policy import (
    CURRENT_AFFAIRS_VIRTUAL_SUBJECT_ID,
    InventoryContext,
    resolve_subject_modes,
)
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
    from app.study_os.subject_runtime_policy import (
        FAMILY_GENERAL_AWARENESS,
        family_for_subject,
    )

    if not exam_id or not subject_id:
        return None, False
    # The reserved GA current-affairs subject is bundle-driven — it has no locked
    # coverage row. Resolve it to the GA family directly so the launch gate passes; the
    # weekly-bundle resolution inside the handler is the real availability authority.
    if str(subject_id) == CURRENT_AFFAIRS_VIRTUAL_SUBJECT_ID:
        return FAMILY_GENERAL_AWARENESS, True
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
    # Bundle-driven GA current-affairs card. GA is never a topic-coverage subject (CA is
    # bundle-driven, not topic-driven), so it can't surface through the coverage buckets
    # above. Emit it as a governed virtual subject WHENEVER the exam has a servable weekly
    # bundle — the launch gate resolves the reserved id to the GA family without coverage,
    # and the policy emitter (not a branch here) supplies the runnable mode.
    ca_bundle = _safe(
        lambda: resolve_eligible_bundle(supabase, exam_id=exam_id, cadence="weekly"),
        default=None,
    )
    if ca_bundle:
        items.append(
            {
                "subject_id": CURRENT_AFFAIRS_VIRTUAL_SUBJECT_ID,
                # Marker so the hub renders a current-affairs card WITHOUT a mastery line
                # (GA never writes user_topic_mastery — a 0% mastery label would be wrong).
                "kind": "current_affairs",
                "subject": "Current Affairs",
                "progress": 0,
                "trend": "flat",
                "weak_count": 0,
                "locked_topics": 0,
                "practice": _subject_practice(
                    {
                        "topic_ids": [],
                        "subject_slug": "general-awareness",
                        "subject_group": "general-awareness",
                    },
                    eng_available=False,
                    pyq_topic_ids=set(),
                    mastery={},
                    error_topics=set(),
                ),
            }
        )

    # Stable order: highest weak_count first, then alphabetical.
    items.sort(key=lambda r: (-r["weak_count"], r["subject"].lower()))
    return items


def _sort_topic_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Default order: by locked exam_priority_score desc, then name asc.

    A node with no locked coverage (priority absent) or a flagged 0-evidence
    rollup node sinks below real, scored leaves — the raw fields stay intact
    so a caller can re-sort differently. Rollup/uncovered nodes are ordered by
    name among themselves.
    """
    def _key(n: dict[str, Any]) -> tuple:
        cov = n.get("coverage")
        # Rollup/header contamination and uncovered topics never outrank a real
        # scored leaf: treat their priority as below any real 0..100 score.
        if n.get("is_rollup_zero_evidence") or not cov or cov.get("exam_priority_score") is None:
            return (1, 0.0, (n.get("name") or "").lower())
        return (0, -float(cov["exam_priority_score"]), (n.get("name") or "").lower())

    return sorted(nodes, key=_key)


def subject_topic_tree(
    supabase: Any,
    user_id: str,
    subject_id: str,
    *,
    exam_id: str | None = None,
) -> dict[str, Any] | None:
    """Topic → microtopic tree for one subject, with locked-coverage priority.

    Read-only. The ``topics`` table is the source of truth for STRUCTURE — every
    ``level='topic'`` (macro) row for the subject is returned, each with its
    ``level='microtopic'`` children nested underneath — so a topic appears even
    when it has no locked coverage yet (that is a legitimate not-yet-scored
    state, not an omission).

    Coverage priority (``exam_priority_score``, ``is_high_yield``) is attached
    only where a LOCKED ``exam_topic_coverage`` row exists for the caller's
    resolved exam; otherwise ``coverage`` is ``null``. ``evidence_count`` is the
    verified-primary PYQ tag count for the topic (0 when none).

    0-evidence rollup nodes are FLAGGED (``is_rollup_zero_evidence``) and sunk
    in the default order — the same guard PR #1030 applied to Score Snapshots:
    a topic that carries a locked coverage row but has zero verified primary
    tags exists only via coverage seeding (a rollup/header node), never a real
    evidence-backed leaf, and must not rank as one. It stays visible, never
    silently dropped.

    Returns ``None`` when ``subject_id`` does not exist (the route maps that to
    404). A real subject with no topics returns an empty ``topics`` list.

    User-specific mastery (``user_topic_mastery``) is intentionally NOT joined
    here — this endpoint is structure + coverage priority only.
    """
    if not subject_id:
        return None

    subject_rows = _safe(
        lambda: (
            supabase.table("subjects")
            .select("id, name, slug, subject_group")
            .eq("id", subject_id)
            .limit(1)
            .execute()
            .data
        ),
        default=None,
    )
    if not subject_rows:
        # Distinguish "no such subject" (404) from "subject exists, no topics"
        # (200 empty). A None default above means the read itself failed — treat
        # as not-found rather than fabricating an empty success.
        return None
    subject = subject_rows[0]

    # Resolve the exam whose locked coverage prioritises these topics: an
    # explicit override, else the caller's target exam. No exam ⇒ structure with
    # coverage null throughout (still a valid tree).
    if not exam_id:
        target = _resolve_target_exam(supabase, user_id)
        exam_id = target.get("id") if target else None

    # STRUCTURE — every macro + microtopic row under the subject, from topics.
    topic_rows = _safe(
        lambda: (
            supabase.table("topics")
            .select("id, name, slug, level, parent_topic_id, is_active")
            .eq("subject_id", subject_id)
            .in_("level", ["topic", "microtopic"])
            .limit(5000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    topic_rows = [t for t in topic_rows if t.get("is_active") is not False]

    # COVERAGE — locked priority indexed by topic_id (LEFT-join semantics).
    coverage_by_topic: dict[str, dict[str, Any]] = {}
    evidence_by_topic: dict[str, int] = {}
    if exam_id:
        for c in _load_locked_coverage(supabase, exam_id) or []:
            tid = c.get("topic_id")
            if tid and str(c.get("subject_id")) == str(subject_id):
                coverage_by_topic[tid] = c
        evidence_by_topic = _safe(
            lambda: verified_pyq_topic_counts(supabase, exam_id), default={}
        ) or {}

    def _node(t: dict[str, Any]) -> dict[str, Any]:
        tid = t.get("id")
        cov = coverage_by_topic.get(tid)
        evidence = int(evidence_by_topic.get(tid, 0))
        # PR #1030 definition: a locked-coverage row with zero verified primary
        # tags is a rollup/header node, not a real leaf. A macro parent with no
        # locked coverage is just structure (not flagged) — the flag requires an
        # actual locked coverage row present with 0 evidence.
        is_rollup = bool(cov) and evidence == 0
        return {
            "topic_id": tid,
            "name": t.get("name") or t.get("slug"),
            "slug": t.get("slug"),
            "level": t.get("level"),
            "parent_topic_id": t.get("parent_topic_id"),
            "evidence_count": evidence,
            "is_rollup_zero_evidence": is_rollup,
            "coverage": (
                {
                    "exam_priority_score": _cov_num(cov.get("coverage_priority")),
                    "is_high_yield": bool(cov.get("is_high_yield")),
                }
                if cov
                else None
            ),
            "children": [],
        }

    nodes_by_id = {t.get("id"): _node(t) for t in topic_rows if t.get("id")}

    # Nest microtopics under their macro parent; keep any orphan (parent not in
    # this subject's set) at the top level so no topic is dropped.
    roots: list[dict[str, Any]] = []
    for t in topic_rows:
        node = nodes_by_id.get(t.get("id"))
        if node is None:
            continue
        parent_id = t.get("parent_topic_id")
        if t.get("level") == "microtopic" and parent_id in nodes_by_id:
            nodes_by_id[parent_id]["children"].append(node)
        else:
            roots.append(node)

    for node in nodes_by_id.values():
        if node["children"]:
            node["children"] = _sort_topic_nodes(node["children"])

    return {
        "subject_id": subject.get("id"),
        "subject": subject.get("name") or subject.get("slug"),
        "subject_group": subject.get("subject_group"),
        "exam_id": exam_id,
        "trust_status": "locked",
        "topics": _sort_topic_nodes(roots),
    }


def _cov_num(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
