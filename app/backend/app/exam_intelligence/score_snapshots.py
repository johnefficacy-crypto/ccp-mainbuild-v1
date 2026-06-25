"""Versioned exam-topic score snapshot writer and reader.

Computes draft ``exam_topic_score_snapshots`` from verified PYQ evidence and
locked coverage. Snapshots are draft until an operator reviews/locks them.
Only locked snapshots reach the planner and user surfaces.

Frequency contract: primary-only. One verified question contributes at most
one count to a topic's frequency, through its primary tag. Secondary, trap,
and calculation_layer roles are not included in the frequency component.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.score_snapshots")

MODEL_VERSION = "v1.0"  # bump when computation logic changes

_BATCH = 250  # max items per Supabase IN() filter

# Postgres SQLSTATEs we want to surface loudly (schema drift / missing table)
_LOUD_PG_CODES = {"42703", "42P01"}


def _chunks(lst: list[Any], n: int) -> list[list[Any]]:
    """Split *lst* into chunks of at most *n* items each."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


def _safe(
    call: Any,
    default: Any = None,
    *,
    table: str | None = None,
    operation: str | None = None,
) -> Any:
    """Call *call()*, return *default* on any exception, logging the error."""
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None) or getattr(exc, "pgcode", None)
        message = str(exc)
        level = logging.ERROR if code in _LOUD_PG_CODES else logging.WARNING
        logger.log(
            level,
            "exam_intelligence score_snapshots operation failed",
            extra={
                "operation": operation or "read",
                "table": table,
                "error_code": code,
                "error_message": message,
            },
        )
        return default


def compute_exam_topic_scores(
    sb: Any,
    exam_id: str,
    model_version: str = MODEL_VERSION,
    *,
    exam_phase_id: str | None = None,
) -> dict[str, int]:
    """Compute and write draft score snapshots for every topic in *exam_id*.

    Returns a summary dict::

        {"written": int, "skipped": int, "errors": int, "total_topics": int}

    Idempotent: topics whose existing draft already has the same fingerprint
    are skipped without re-writing.  Locked rows are never touched.
    """
    zero: dict[str, int] = {"written": 0, "skipped": 0, "errors": 0, "total_topics": 0}
    if not exam_id:
        return zero

    # ── 1. Verified papers ────────────────────────────────────────────────
    paper_rows = _safe(
        lambda: (
            sb.table("pyq_papers")
            .select("id")
            .eq("exam_id", exam_id)
            .eq("trust_status", "verified")
            .execute()
            .data
        ),
        default=[],
        table="pyq_papers",
        operation="select_verified_by_exam",
    ) or []
    paper_ids: list[str] = [r["id"] for r in paper_rows if r.get("id")]
    if not paper_ids:
        return zero

    # ── 2. Verified questions (batched) ───────────────────────────────────
    question_ids: list[str] = []
    for chunk in _chunks(paper_ids, _BATCH):
        rows = _safe(
            lambda c=chunk: (
                sb.table("pyq_questions")
                .select("id")
                .in_("pyq_paper_id", c)
                .eq("reviewer_status", "verified")
                .execute()
                .data
            ),
            default=[],
            table="pyq_questions",
            operation="select_verified",
        ) or []
        question_ids.extend(r["id"] for r in rows if r.get("id"))

    if not question_ids:
        return zero

    # ── 3. Primary tags (batched) ─────────────────────────────────────────
    primary_counts: dict[str, int] = {}
    for chunk in _chunks(question_ids, _BATCH):
        tag_rows = _safe(
            lambda c=chunk: (
                sb.table("pyq_question_topic_tags")
                .select("topic_id")
                .in_("question_id", c)
                .eq("reviewer_status", "verified")
                .eq("tag_role", "primary")
                .execute()
                .data
            ),
            default=[],
            table="pyq_question_topic_tags",
            operation="select_primary_verified",
        ) or []
        for row in tag_rows:
            tid = row.get("topic_id")
            if tid:
                primary_counts[tid] = primary_counts.get(tid, 0) + 1

    # ── 4. Locked coverage ────────────────────────────────────────────────
    cov_query = (
        sb.table("exam_topic_coverage")
        .select("topic_id, exam_priority_score, is_high_yield")
        .eq("exam_id", exam_id)
        .eq("reviewer_status", "locked")
    )
    if exam_phase_id:
        cov_query = cov_query.eq("exam_phase_id", exam_phase_id)

    locked_cov_rows = _safe(
        lambda: cov_query.execute().data,
        default=[],
        table="exam_topic_coverage",
        operation="select_locked",
    ) or []
    locked_cov: dict[str, dict[str, Any]] = {
        r["topic_id"]: r for r in locked_cov_rows if r.get("topic_id")
    }

    # ── 5. Fingerprint ────────────────────────────────────────────────────
    fingerprint = hashlib.sha256(
        f"{exam_id}:{model_version}:{','.join(sorted(paper_ids))}:{','.join(sorted(question_ids))}".encode()
    ).hexdigest()[:24]

    # ── 6. Existing drafts ────────────────────────────────────────────────
    existing_rows = _safe(
        lambda: (
            sb.table("exam_topic_score_snapshots")
            .select("topic_id, input_summary")
            .eq("exam_id", exam_id)
            .eq("model_version", model_version)
            .eq("status", "draft")
            .execute()
            .data
        ),
        default=[],
        table="exam_topic_score_snapshots",
        operation="select_drafts",
    ) or []
    existing_drafts: dict[str, dict[str, Any]] = {
        r["topic_id"]: r for r in existing_rows if r.get("topic_id")
    }

    # ── 7. Score each topic ───────────────────────────────────────────────
    all_topic_ids = set(primary_counts.keys()) | set(locked_cov.keys())
    total_primary = sum(primary_counts.values())

    written = skipped = errors = 0

    for tid in all_topic_ids:
        freq_component = primary_counts.get(tid, 0) / max(total_primary, 1)
        cov_component = float(locked_cov.get(tid, {}).get("exam_priority_score") or 0) / 100
        evidence_quality = min(primary_counts.get(tid, 0) / 10.0, 1.0)

        exam_priority_score = round(
            freq_component * 50 + cov_component * 40 + evidence_quality * 10, 2
        )
        is_high_yield = bool(locked_cov.get(tid, {}).get("is_high_yield")) or freq_component > 0.15
        confidence_score = round(min(0.3 + evidence_quality * 0.7, 1.0), 3)

        score_components = {
            "frequency_component": round(freq_component, 4),
            "coverage_component": round(cov_component, 4),
            "evidence_quality": round(evidence_quality, 4),
        }
        input_summary = {
            "fingerprint": fingerprint,
            "paper_count": len(paper_ids),
            "question_count": len(question_ids),
            "topic_primary_count": primary_counts.get(tid, 0),
            "corpus_total_primary": total_primary,
        }

        # Idempotency check
        existing = existing_drafts.get(tid)
        if existing and existing.get("input_summary", {}).get("fingerprint") == fingerprint:
            skipped += 1
            continue

        try:
            sb.table("exam_topic_score_snapshots").insert(
                {
                    "exam_id": exam_id,
                    "exam_phase_id": exam_phase_id,
                    "topic_id": tid,
                    "model_version": model_version,
                    "exam_priority_score": exam_priority_score,
                    "is_high_yield": is_high_yield,
                    "confidence_score": confidence_score,
                    "evidence_count": primary_counts.get(tid, 0),
                    "score_components": score_components,
                    "input_summary": input_summary,
                    "status": "draft",
                }
            ).execute()
            written += 1
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", None) or getattr(exc, "pgcode", None)
            logger.warning(
                "score_snapshots insert failed",
                extra={
                    "operation": "insert_draft",
                    "table": "exam_topic_score_snapshots",
                    "topic_id": tid,
                    "error_code": code,
                    "error_message": str(exc),
                },
            )
            errors += 1

    return {
        "written": written,
        "skipped": skipped,
        "errors": errors,
        "total_topics": len(all_topic_ids),
    }


def locked_score_snapshots(
    sb: Any,
    exam_id: str,
    *,
    exam_phase_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return locked score snapshots for planner consumption.

    Only ``status='locked'`` rows are returned, sorted by
    ``exam_priority_score`` descending.

    Result row shape::

        {
            "topic_id": str,
            "exam_priority_score": float|None,
            "is_high_yield": bool,
            "confidence_score": float|None,
            "model_version": str,
            "score_components": dict,
        }
    """
    if not exam_id:
        return []

    query = (
        sb.table("exam_topic_score_snapshots")
        .select(
            "topic_id, exam_priority_score, is_high_yield, "
            "confidence_score, model_version, score_components"
        )
        .eq("exam_id", exam_id)
        .eq("status", "locked")
    )
    if exam_phase_id:
        query = query.eq("exam_phase_id", exam_phase_id)

    rows = _safe(
        lambda: query.order("exam_priority_score", desc=True).execute().data,
        default=[],
        table="exam_topic_score_snapshots",
        operation="select_locked",
    ) or []

    return [
        {
            "topic_id": r.get("topic_id"),
            "exam_priority_score": r.get("exam_priority_score"),
            "is_high_yield": bool(r.get("is_high_yield")),
            "confidence_score": r.get("confidence_score"),
            "model_version": r.get("model_version"),
            "score_components": r.get("score_components") or {},
        }
        for r in rows
    ]


def list_exam_score_snapshots(
    sb: Any,
    exam_id: str,
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return all snapshots for an admin list view.

    Optionally filter by *status*. Returns up to 2 000 full rows including
    review metadata (``reviewed_by``, ``reviewed_at``, ``reviewer_notes``).
    """
    if not exam_id:
        return []

    query = (
        sb.table("exam_topic_score_snapshots")
        .select("*")
        .eq("exam_id", exam_id)
    )
    if status:
        query = query.eq("status", status)

    rows = _safe(
        lambda: query.limit(2000).execute().data,
        default=[],
        table="exam_topic_score_snapshots",
        operation="select_all",
    ) or []

    return list(rows)
