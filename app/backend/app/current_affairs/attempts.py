"""Current-affairs learner attempt runtime (GQR-G5a) — OWN tables, no mastery.

A weekly attempt freezes its bundle's STILL-ELIGIBLE promoted current-event questions
into ``current_affairs_attempt_responses.question_snapshot`` (mirroring the mock freeze,
plus a frozen §10 provenance envelope) and scores inline at submit against the frozen
correct option. It NEVER touches ``mock_attempts`` and NEVER enters
``mock_engine.submit_attempt``, so no mastery / SRS / Mistake-Book / correction-task
write can fire (policy: ``mastery_enabled=False``). The server owns bundle + question
selection; the browser submits only answers. Start / save / submit are atomic RPCs.
"""
from __future__ import annotations

import logging
from typing import Any

from app.current_affairs.bundles import (
    bundle_question_ids,
    eligible_bundle_question_ids,
    load_question_provenance,
    resolve_eligible_bundle,
)
from app.study_os.generated_mock_attempt import _load_questions
from app.study_os.mock_engine import _question_snapshot

logger = logging.getLogger("career_copilot.current_affairs.attempts")

_MARKS_PER_CORRECT = 1.0
_MARKS_PER_WRONG = 0.0  # current-affairs practice: no negative marking

# KNOWN RPC domain error tokens → Python exception class (mapped to HTTP at the router).
# Anything NOT in these sets is an infrastructure fault (transport/timeout/unexpected DB
# error) and is re-raised unchanged so it surfaces as a 500 — never mislabelled a learner
# 4xx (checkpost #976 F5).
_LOOKUP_TOKENS = ("attempt_not_found", "bundle_not_found")
_PERMISSION_TOKENS = ("not_attempt_owner", "bundle_scope_mismatch")
_VALUE_TOKENS = (
    "user_required", "attempt_not_in_progress", "question_not_in_attempt",
    "option_not_in_question", "attempt_already_submitted",
    "bundle_not_published", "bundle_not_verified", "bundle_not_yet_published",
    "bundle_unavailable", "empty_bundle", "bundle_set_mismatch", "bundle_degraded",
    "snapshot_answer_mismatch", "snapshot_options_mismatch", "snapshot_text_mismatch",
    # GQR-G6 monthly + retry tail.
    "not_a_monthly_bundle", "not_a_weekly_attempt", "attempt_not_submitted",
    "retry_tail_cap_exceeded", "retry_tail_duplicate", "retry_tail_overlaps_core",
    "retry_tail_not_eligible", "retry_tail_not_relevant",
)


def _raise_mapped(exc: Exception) -> None:
    """Translate a KNOWN CA RPC domain error into a typed exception; re-raise the rest.

    Only recognised domain tokens become 4xx. An unrecognised failure (Supabase transport
    error, timeout, malformed response, unexpected DB fault) is re-raised as-is so the
    router returns 500/503 rather than blaming the learner with a 422."""
    msg = str(getattr(exc, "message", None) or exc)
    low = msg.lower()
    if any(tok in low for tok in _LOOKUP_TOKENS):
        raise LookupError(msg) from exc
    if any(tok in low for tok in _PERMISSION_TOKENS):
        raise PermissionError(msg) from exc
    if any(tok in low for tok in _VALUE_TOKENS):
        raise ValueError(msg) from exc
    raise exc  # unknown → infrastructure fault, surfaces as 500


def _rpc(supabase: Any, name: str, params: dict[str, Any]) -> Any:
    try:
        return supabase.rpc(name, params).execute().data
    except (LookupError, PermissionError, ValueError):
        raise
    except Exception as exc:  # domain error raised by the SECURITY DEFINER function
        _raise_mapped(exc)


def start_weekly_current_affairs_attempt(
    supabase: Any, *, user_id: str, exam_id: str | None
) -> dict[str, Any]:
    """Resolve the eligible weekly bundle, freeze its still-eligible questions + the §10
    provenance envelope, and start a CA attempt.

    Returns ``{outcome, attempt_id, ...}`` or ``{outcome:'no_bundle'}`` / ``'empty_bundle'``
    when no servable weekly bundle (or no still-eligible question) is available."""
    bundle = resolve_eligible_bundle(supabase, exam_id=exam_id, cadence="weekly")
    if not bundle:
        return {"outcome": "no_bundle"}
    raw = bundle_question_ids(supabase, str(bundle["id"]))
    if not raw:
        return {"outcome": "empty_bundle", "bundle_id": bundle["id"]}
    # Freeze the AUTHORITATIVE set. A published bundle whose raw members are not ALL
    # still-eligible + provenance-complete has degraded — fail closed (re-publish needed)
    # rather than serve a silently shortened attempt. The RPC re-checks this under lock.
    qids = eligible_bundle_question_ids(supabase, str(bundle["id"]))
    if qids != raw:
        return {"outcome": "bundle_degraded", "bundle_id": bundle["id"]}

    questions_by_id = _load_questions(supabase, qids)
    provenance = load_question_provenance(supabase, qids)
    response_rows: list[dict[str, Any]] = []
    ordered: list[str] = []
    for qid in qids:
        q = questions_by_id.get(qid)
        if q is None:
            # Loader dropped an eligible id — refuse rather than shorten the attempt.
            raise RuntimeError(f"current-affairs freeze aborted: missing bank row for {qid}")
        snap = _question_snapshot(q, marks_per_correct=_MARKS_PER_CORRECT, marks_per_wrong=_MARKS_PER_WRONG)
        if not snap.get("options") or not snap.get("correct_option_id"):
            raise RuntimeError(f"current-affairs freeze aborted: bad snapshot for {qid}")
        # Freeze the §10 provenance envelope alongside the question (revealed post-submit).
        snap["current_affairs"] = provenance.get(qid, {})
        response_rows.append({"question_id": qid, "question_snapshot": snap})
        ordered.append(qid)

    template_snapshot = {
        "source": "current_affairs_bundle",
        "practice": True,
        "practice_mode": "weekly_current_affairs",
        "bundle_id": str(bundle["id"]),
        "cadence": bundle.get("cadence"),
        "period_start": bundle.get("period_start"),
        "period_end": bundle.get("period_end"),
        "question_ids": ordered,
        "total_questions": len(ordered),
        "negative_marking": False,
        "marks_per_correct": _MARKS_PER_CORRECT,
        "marks_per_wrong": _MARKS_PER_WRONG,
        "interface_mode": "simple",
    }
    result = _rpc(supabase, "ca_start_current_affairs_attempt", {
        "p_user": user_id,
        "p_bundle": str(bundle["id"]),
        "p_exam": exam_id,
        "p_template_snapshot": template_snapshot,
        "p_response_rows": response_rows,
    })
    return result if isinstance(result, dict) else (result or {"outcome": "error"})


def _learner_question_view(resp: dict[str, Any], *, submitted: bool) -> dict[str, Any]:
    """Frozen question as the learner sees it. The correct option / explanation / source
    provenance are hidden until the attempt is submitted (no answer leakage mid-attempt)."""
    snap = resp.get("question_snapshot") or {}
    view = {
        "question_id": resp.get("mock_question_id"),
        "question_text": snap.get("question_text"),
        "question_type": snap.get("question_type"),
        "options": [
            {"id": o.get("id"), "option_text": o.get("option_text"),
             "option_index": o.get("option_index"), "source_label": o.get("source_label")}
            for o in (snap.get("options") or [])
        ],
        "selected_option_id": resp.get("selected_option_id"),
        "is_marked_for_review": bool(resp.get("is_marked_for_review")),
        "is_visited": bool(resp.get("is_visited")),
        # Persisted save state so a reloaded client can seed its per-question monotonic
        # counter ABOVE the stored value (else a legitimate later edit would be swallowed
        # as `already_recorded` by the client_seq guard) — checkpost #976 F4.
        "client_seq": int(resp.get("client_seq") or 0),
        "time_spent_sec": int(resp.get("time_spent_sec") or 0),
    }
    if submitted:
        # Post-submission feedback (§10): correct answer, explanation, event date,
        # source publication date, source link, and a supersession warning where present.
        prov = snap.get("current_affairs") or {}
        view["correct_option_id"] = snap.get("correct_option_id")
        view["is_correct"] = resp.get("is_correct")
        view["explanation"] = snap.get("explanation")
        view["event_date"] = prov.get("event_date")
        view["source_published_at"] = prov.get("source_published_at")
        view["source_url"] = prov.get("source_url")
        view["superseded"] = bool(prov.get("superseded"))
        if prov.get("supersession_note"):
            view["supersession_note"] = prov.get("supersession_note")
    return view


def get_current_affairs_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict[str, Any]:
    """Learner attempt state (ownership-checked; answer hidden until submitted)."""
    rows = (
        supabase.table("current_affairs_attempts").select("*")
        .eq("id", attempt_id).limit(1).execute().data
    ) or []
    if not rows:
        raise LookupError("attempt not found")
    attempt = rows[0]
    if str(attempt.get("user_id")) != str(user_id):
        raise PermissionError("not attempt owner")
    submitted = attempt.get("status") == "submitted"
    resp_rows = (
        supabase.table("current_affairs_attempt_responses").select("*")
        .eq("attempt_id", attempt_id).execute().data
    ) or []
    by_id = {str(r.get("mock_question_id")): r for r in resp_rows}
    order = (attempt.get("template_snapshot") or {}).get("question_ids") or list(by_id.keys())
    questions = [
        _learner_question_view(by_id[qid], submitted=submitted)
        for qid in order if qid in by_id
    ]
    return {
        "attempt_id": attempt["id"], "status": attempt.get("status"),
        "cadence": attempt.get("cadence"), "bundle_id": attempt.get("bundle_id"),
        "total_questions": attempt.get("total_questions"),
        "score_raw": attempt.get("score_raw"), "total_correct": attempt.get("total_correct"),
        "total_wrong": attempt.get("total_wrong"), "total_unattempted": attempt.get("total_unattempted"),
        "submitted_at": attempt.get("submitted_at"),
        "questions": questions,
    }


def save_current_affairs_answer(
    supabase: Any, user_id: str, attempt_id: str, *, question_id: str,
    selected_option_id: str | None, is_marked_for_review: bool = False,
    time_spent_sec: int = 0, client_seq: int = 0,
) -> dict[str, Any]:
    """Persist one answer via the atomic save RPC (owner + in-progress + frozen-question
    + frozen-option membership + monotonic client_seq, all under an attempt lock). An
    equal-or-lower client_seq is an idempotent no-op (never an overwrite)."""
    result = _rpc(supabase, "ca_save_current_affairs_answer", {
        "p_attempt_id": attempt_id,
        "p_user": user_id,
        "p_question_id": question_id,
        "p_selected_option_id": selected_option_id,
        "p_is_marked_for_review": bool(is_marked_for_review),
        "p_time_spent_sec": int(time_spent_sec or 0),
        "p_client_seq": int(client_seq or 0),
    })
    return result if isinstance(result, dict) else (result or {"ok": True})


def submit_current_affairs_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict[str, Any]:
    """Score + finalise atomically via the RPC (no mastery/correction/SRS)."""
    result = _rpc(supabase, "ca_submit_current_affairs_attempt", {
        "p_attempt_id": attempt_id, "p_user": user_id,
    })
    return result if isinstance(result, dict) else (result or {"outcome": "error"})
