"""Current-affairs MONTHLY consolidation runtime (GQR-G6) — editorial core + retry tail.

A monthly attempt freezes an EDITORIAL CORE (a published+verified ``cadence='monthly'``
bundle, verified exactly like the weekly runtime) plus a per-learner capped RETRY TAIL of
the learner's still-relevant weekly mistakes (materialised in ``current_affairs_retry_items``).
Reuses the weekly freeze machinery (``_question_snapshot`` + ``_load_questions`` +
``load_question_provenance``) and the atomic monthly start RPC. Like the weekly runtime it
NEVER writes mastery / SRS / Mistake-Book / correction — GA stays on its own tables.
"""
from __future__ import annotations

import logging
from typing import Any

from app.current_affairs.attempts import _MARKS_PER_CORRECT, _MARKS_PER_WRONG, _rpc
from app.current_affairs.bundles import (
    bundle_question_ids,
    eligible_bundle_question_ids,
    load_question_provenance,
    resolve_eligible_bundle,
)
from app.study_os.generated_mock_attempt import _load_questions
from app.study_os.mock_engine import _question_snapshot

logger = logging.getLogger("career_copilot.current_affairs.monthly")

_RETRY_TAIL_CAP = 10  # capped personalised tail (pipeline §10); mirrors the RPC's v_cap.
_MONTHLY_START_RPC = "ca_start_monthly_current_affairs_attempt_guarded"


def enqueue_weekly_retry_items(supabase: Any, user_id: str, attempt_id: str) -> dict[str, Any]:
    """Enqueue a submitted weekly attempt's still-relevant mistakes for monthly review.

    Normal submission now invokes this atomically inside the submit RPC. This explicit wrapper
    remains useful for operator repair/backfill and is idempotent for the same source attempt.
    """
    count = _rpc(supabase, "ca_enqueue_weekly_retry_items", {
        "p_attempt_id": attempt_id, "p_user": user_id,
    })
    return {"enqueued": int(count or 0)}


def _eligible_retry_tail_ids(
    supabase: Any,
    user_id: str,
    *,
    exam_id: str | None,
    exclude: list[str],
    cap: int,
) -> list[str]:
    """Return the learner's exact-exam eligible retry-tail question ids.

    Results are oldest-due first, exclude editorial-core questions, and are capped. The
    database owns pending/due/expiry/relevance and exact-exam authority; Python only preserves
    that order and removes core overlap before freezing.
    """
    rows = (
        supabase.rpc(
            "ca_eligible_retry_tail",
            {"p_user": user_id, "p_exam": exam_id},
        ).execute().data
    ) or []
    excl = set(exclude)
    out: list[str] = []
    for row in rows:
        qid = str(row.get("question_id"))
        if not qid or qid == "None" or qid in excl or qid in out:
            continue
        out.append(qid)
        if len(out) >= cap:
            break
    return out


def _freeze_rows(supabase: Any, qids: list[str]) -> list[dict[str, Any]]:
    """Freeze snapshot + §10 provenance envelope for each question (mirrors the weekly freeze;
    refuses to shorten — a missing bank row / bad snapshot aborts)."""
    if not qids:
        return []
    questions_by_id = _load_questions(supabase, qids)
    provenance = load_question_provenance(supabase, qids)
    rows: list[dict[str, Any]] = []
    for qid in qids:
        question = questions_by_id.get(qid)
        if question is None:
            raise RuntimeError(f"monthly freeze aborted: missing bank row for {qid}")
        snapshot = _question_snapshot(
            question,
            marks_per_correct=_MARKS_PER_CORRECT,
            marks_per_wrong=_MARKS_PER_WRONG,
        )
        if not snapshot.get("options") or not snapshot.get("correct_option_id"):
            raise RuntimeError(f"monthly freeze aborted: bad snapshot for {qid}")
        snapshot["current_affairs"] = provenance.get(qid, {})
        rows.append({"question_id": qid, "question_snapshot": snapshot})
    return rows


def start_monthly_current_affairs_attempt(
    supabase: Any, *, user_id: str, exam_id: str | None
) -> dict[str, Any]:
    """Resolve the monthly editorial bundle, freeze its core + capped retry tail, and start.

    Returns ``{outcome, attempt_id, core_count, retry_tail_count, ...}`` or a non-runnable
    ``no_bundle`` / ``empty_bundle`` / ``bundle_degraded`` outcome. The guarded SQL entry
    point serialises starts, binds retries to the exact exam, validates bundle authority
    before reuse, and canonicalises frozen list metadata.
    """
    bundle = resolve_eligible_bundle(supabase, exam_id=exam_id, cadence="monthly")
    if not bundle:
        return {"outcome": "no_bundle"}
    raw = bundle_question_ids(supabase, str(bundle["id"]))
    if not raw:
        return {"outcome": "empty_bundle", "bundle_id": bundle["id"]}
    core = eligible_bundle_question_ids(supabase, str(bundle["id"]))
    if core != raw:
        return {"outcome": "bundle_degraded", "bundle_id": bundle["id"]}
    tail = _eligible_retry_tail_ids(
        supabase,
        user_id,
        exam_id=exam_id,
        exclude=core,
        cap=_RETRY_TAIL_CAP,
    )

    core_rows = _freeze_rows(supabase, core)
    retry_rows = _freeze_rows(supabase, tail)
    template_snapshot = {
        "source": "current_affairs_bundle",
        "practice": True,
        "practice_mode": "monthly_current_affairs",
        "bundle_id": str(bundle["id"]),
        "cadence": bundle.get("cadence"),
        "period_start": bundle.get("period_start"),
        "period_end": bundle.get("period_end"),
        "question_ids": core + tail,
        "core_question_ids": core,
        "retry_tail_question_ids": tail,
        "total_questions": len(core) + len(tail),
        "negative_marking": False,
        "marks_per_correct": _MARKS_PER_CORRECT,
        "marks_per_wrong": _MARKS_PER_WRONG,
        "interface_mode": "simple",
    }
    result = _rpc(supabase, _MONTHLY_START_RPC, {
        "p_user": user_id,
        "p_bundle": str(bundle["id"]),
        "p_exam": exam_id,
        "p_template_snapshot": template_snapshot,
        "p_core_rows": core_rows,
        "p_retry_rows": retry_rows,
    })
    return result if isinstance(result, dict) else (result or {"outcome": "error"})


def monthly_consolidation_report(supabase: Any, user_id: str, attempt_id: str) -> dict[str, Any]:
    """Composition + score report split into editorial core and retry tail."""
    rows = (
        supabase.table("current_affairs_attempts").select("*")
        .eq("id", attempt_id).limit(1).execute().data
    ) or []
    if not rows:
        raise LookupError("attempt not found")
    attempt = rows[0]
    if str(attempt.get("user_id")) != str(user_id):
        raise PermissionError("not attempt owner")
    if attempt.get("cadence") != "monthly":
        raise ValueError("not a monthly attempt")
    responses = (
        supabase.table("current_affairs_attempt_responses")
        .select("item_role,is_correct,selected_option_id")
        .eq("attempt_id", attempt_id).execute().data
    ) or []

    def _bucket(role: str) -> dict[str, int]:
        items = [row for row in responses if (row.get("item_role") or "core") == role]
        return {
            "total": len(items),
            "attempted": sum(1 for row in items if row.get("selected_option_id") is not None),
            "correct": sum(1 for row in items if row.get("is_correct")),
        }

    return {
        "attempt_id": attempt_id,
        "cadence": attempt.get("cadence"),
        "status": attempt.get("status"),
        "score_raw": attempt.get("score_raw"),
        "submitted_at": attempt.get("submitted_at"),
        "core": _bucket("core"),
        "retry_tail": _bucket("retry_tail"),
    }
