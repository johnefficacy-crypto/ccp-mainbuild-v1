"""English Writing Practice — deterministic runtime API (EWP-2).

Practice-runtime endpoints under ``/api/study/practice/english``. Stage-1
(deterministic) evaluation runs synchronously here; the async language/rubric
worker is EWP-2B. These endpoints never create mock attempts (§2) and never
write live mastery (§10 — shadow only, gated).

DB-touching handlers use the service-role client and scope every read/write to
``user.id``; the schema's RLS is a defence-in-depth backstop, not the primary
authorization here.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.study_os.writing_practice import coverage_checker
from app.study_os.writing_practice import deterministic as det
from app.study_os.writing_practice import session_state as st
from app.study_os.writing_practice.constraints import validate_unit_constraints
from app.study_os.writing_practice.content_hash import compute_content_hash

logger = logging.getLogger("career_copilot.api.writing_practice")

router = APIRouter(prefix="/study/practice/english", tags=["writing-practice"])


# --- request models -------------------------------------------------------

class CreateSessionRequest(BaseModel):
    prompt_id: UUID
    study_task_id: UUID | None = None
    mode: str = Field(default="learning", pattern="^(learning|exam)$")


class SubmitUnitRequest(BaseModel):
    answer_text: str
    client_word_count: int | None = None
    # Mandatory version CAS token: the version number the caller expects to
    # create (1 for a unit's first submission). Rejects stale/duplicate submits.
    version_number: int = Field(ge=1)


class ReopenUnitRequest(BaseModel):
    expected_latest_version_id: UUID
    reason: str | None = None


# --- helpers --------------------------------------------------------------

def _owned_session(supabase: Any, session_id: str, user_id: str) -> dict:
    row = (
        supabase.table("writing_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    ).data
    if not row:
        raise HTTPException(status_code=404, detail="writing session not found")
    return row


def _session_payload(supabase: Any, session: dict) -> dict:
    units = (
        supabase.table("writing_session_units")
        .select("id,unit_number,status,practice_microtopic_id,unit_constraints")
        .eq("session_id", session["id"])
        .order("unit_number")
        .execute()
    ).data or []
    return {"session": session, "units": units}


# --- endpoints ------------------------------------------------------------

@router.post("/sessions")
def create_session(body: CreateSessionRequest, user: dict = Depends(get_current_user)) -> dict:
    user_id = user.get("id")
    # EWP-2 ships learning mode only; the exam-session runtime (§9.2/§9.3 —
    # answer locking, blank versions, feedback release) is a later slice.
    if body.mode != "learning":
        raise HTTPException(status_code=400, detail="exam mode is not available in EWP-2")

    supabase = get_supabase_admin()
    prompt = (
        supabase.table("writing_prompts")
        .select("*")
        .eq("id", str(body.prompt_id))
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
        .maybe_single()
        .execute()
    ).data
    if not prompt:
        raise HTTPException(status_code=404, detail="prompt not found or not verified/active")

    # A supplied study_task must belong to the caller (launch-identity check).
    if body.study_task_id is not None:
        task = (
            supabase.table("study_tasks").select("id,user_id")
            .eq("id", str(body.study_task_id)).maybe_single().execute()
        ).data
        if not task or task.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="study task not found")

    constraints = validate_unit_constraints({"schema_version": 1})
    # Atomic: session + all units in one transaction (§8.0). Learning-mode
    # feedback is immediate.
    session = (
        supabase.rpc("ewp_create_writing_session", {
            "p_user": user_id,
            "p_prompt": str(body.prompt_id),
            "p_study_task": str(body.study_task_id) if body.study_task_id else None,
            "p_mode": "learning",
            "p_projection_revision": _current_projection_revision(),
            "p_policy": "immediate",
            "p_delay": None,
            "p_unit_count": prompt.get("required_sentence_count") or 1,
            "p_microtopic": prompt.get("microtopic_id"),
            "p_constraints": constraints,
        }).execute()
    ).data
    return _session_payload(supabase, session)


@router.get("/sessions/{session_id}")
def get_session(session_id: UUID, user: dict = Depends(get_current_user)) -> dict:
    supabase = get_supabase_admin()
    session = _owned_session(supabase, str(session_id), user.get("id"))
    return _session_payload(supabase, session)


@router.post("/sessions/{session_id}/units/{unit_number}/submit")
def submit_unit(
    session_id: UUID, unit_number: int, body: SubmitUnitRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    supabase = get_supabase_admin()
    session = _owned_session(supabase, str(session_id), user.get("id"))
    if session["status"] in (st.SESSION_COMPLETED, st.SESSION_ABANDONED):
        raise HTTPException(status_code=409, detail="session is not open for submission")

    unit = (
        supabase.table("writing_session_units")
        .select("*")
        .eq("session_id", str(session_id))
        .eq("unit_number", unit_number)
        .maybe_single()
        .execute()
    ).data
    if not unit:
        raise HTTPException(status_code=404, detail="unit not found")

    prompt = (
        supabase.table("writing_prompts").select("min_words,max_words,required_words")
        .eq("id", session["prompt_id"]).single().execute()
    ).data
    required_words = prompt.get("required_words") or []
    constraints = unit.get("unit_constraints") or {}

    # Per-unit bounds override prompt-level bounds when present (§4.4a).
    min_words = constraints.get("min_words", prompt.get("min_words"))
    max_words = constraints.get("max_words", prompt.get("max_words"))

    # Deterministic Stage-1 (pure) — computed before the atomic write.
    siblings = _sibling_latest_texts(supabase, str(session_id), exclude_unit_id=unit["id"])
    result = det.evaluate_unit(
        body.answer_text,
        min_words=min_words,
        max_words=max_words,
        required_words=constraints.get("hint_words"),
        other_unit_texts=siblings,
    )

    # Atomic submit: locks (session -> all units ascending), version CAS,
    # version + evaluation + job insert, unit transition — one transaction (§8.0).
    try:
        submit = (
            supabase.rpc("ewp_submit_writing_unit", {
                "p_user": user.get("id"),
                "p_session": str(session_id),
                "p_unit_number": unit_number,
                "p_answer": body.answer_text,
                "p_client_wc": body.client_word_count,
                "p_server_wc": result.server_word_count,
                "p_content_hash": compute_content_hash(body.answer_text),
                "p_expected_version": body.version_number,
                "p_det_result": result.to_dict(),
                "p_det_version": result.evaluator_version,
            }).execute()
        ).data
    except Exception as exc:  # PostgREST surfaces the RAISE message
        raise _rpc_error(exc)

    # The submission (version + evaluation + job + unit transition) has already
    # committed atomically AND rolled the session up in-transaction inside the
    # RPC, so session status is already consistent here. Writing the authoritative
    # coverage row + re-finalizing under the completion gate (§4.7a, §8.0) is a
    # best-effort REFRESH: both are idempotent and pinned to the version_set_hash,
    # so a failure here is recomputed on the next submit/finalize/read. It must
    # NOT surface as an error — that would leave the client unable to resubmit an
    # already-committed version (duplicate submit is rejected by design).
    coverage: dict | None = None
    try:
        coverage = coverage_checker.run_coverage_check(supabase, str(session_id), required_words)
        supabase.rpc("ewp_finalize_writing_session", {
            "p_user": user.get("id"),
            "p_session": str(session_id),
        }).execute()
    except Exception:  # noqa: BLE001 — submission is durable; refresh is retryable
        logger.warning(
            "post-submit coverage/finalize refresh failed for session %s (submission committed; "
            "status already rolled up in-transaction, refresh is idempotent)",
            session_id, exc_info=True,
        )
    return {
        "evaluation": (submit or {}).get("evaluation"),
        "version_number": (submit or {}).get("version_number"),
        "deterministic_result": result.to_dict(),
        "coverage": coverage,
        "coverage_refresh_deferred": coverage is None,
    }


@router.post("/sessions/{session_id}/units/{unit_id}/reopen")
def reopen_unit(
    session_id: UUID, unit_id: UUID, body: ReopenUnitRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    supabase = get_supabase_admin()
    # Atomic: locks session + all units, validates learning-mode/status/ready +
    # optimistic latest-version, transitions ready -> draft (§7.3, §8.0).
    try:
        out = (
            supabase.rpc("ewp_reopen_writing_unit", {
                "p_user": user.get("id"),
                "p_session": str(session_id),
                "p_unit": str(unit_id),
                "p_expected_latest_version": str(body.expected_latest_version_id),
            }).execute()
        ).data
    except Exception as exc:
        raise _rpc_error(exc)

    # Reopen rolls the session up in the same transaction (ready -> draft ->
    # rollup, §8.0), so no separate finalize call is needed here.
    return out or {"unit_id": str(unit_id), "status": st.UNIT_DRAFT}


def _feedback_released(session: dict) -> bool:
    """Whether feedback is visible for a session (learning=always; exam=gated)."""
    if session.get("mode") == "learning":
        return True
    released = session.get("feedback_released_at")
    if not released:
        return False
    from datetime import datetime, timezone

    try:
        ts = datetime.fromisoformat(str(released).replace("Z", "+00:00"))
    except ValueError:
        return False
    return ts <= datetime.now(timezone.utc)


@router.get("/sessions/{session_id}/evaluations/{evaluation_id}")
def get_evaluation(
    session_id: UUID, evaluation_id: UUID, user: dict = Depends(get_current_user),
) -> dict:
    supabase = get_supabase_admin()
    session = _owned_session(supabase, str(session_id), user.get("id"))

    # Prove the evaluation belongs to THIS owned session: evaluation -> version
    # -> unit -> session. A globally-fetched evaluation is not sufficient.
    evaluation = (
        supabase.table("writing_evaluations").select("*").eq("id", str(evaluation_id)).maybe_single().execute()
    ).data
    if not evaluation:
        raise HTTPException(status_code=404, detail="evaluation not found")
    version = (
        supabase.table("writing_unit_versions").select("unit_id")
        .eq("id", evaluation["unit_version_id"]).maybe_single().execute()
    ).data
    unit = version and (
        supabase.table("writing_session_units").select("session_id")
        .eq("id", version["unit_id"]).maybe_single().execute()
    ).data
    if not unit or unit["session_id"] != str(session_id):
        raise HTTPException(status_code=404, detail="evaluation not found")

    # Exam-mode feedback is gated on release; before release, hide the body.
    if not _feedback_released(session):
        raise HTTPException(status_code=409, detail="feedback not yet released")
    return {"evaluation": evaluation}


@router.get("/error-summary")
def error_summary(user: dict = Depends(get_current_user)) -> dict:
    """Recurring writing issues for the CALLER, grouped by microtopic.

    Scoped to the caller's own sessions (service-role bypasses RLS), restricted
    to current-state issues (`affects_current_state = true`) on feedback-released
    sessions. Effective-invalidation exclusion applies once EWP-2B produces
    review events.
    """
    supabase = get_supabase_admin()
    user_id = user.get("id")

    sessions = (
        supabase.table("writing_sessions").select("id,mode,feedback_released_at")
        .eq("user_id", user_id).execute()
    ).data or []
    released_session_ids = [s["id"] for s in sessions if _feedback_released(s)]
    if not released_session_ids:
        return {"by_microtopic": {}}

    units = (
        supabase.table("writing_session_units").select("id,session_id")
        .in_("session_id", released_session_ids).execute()
    ).data or []
    if not units:
        return {"by_microtopic": {}}
    versions = (
        supabase.table("writing_unit_versions").select("id,unit_id")
        .in_("unit_id", [u["id"] for u in units]).execute()
    ).data or []
    if not versions:
        return {"by_microtopic": {}}
    evals = (
        supabase.table("writing_evaluations").select("id,unit_version_id")
        .in_("unit_version_id", [v["id"] for v in versions]).execute()
    ).data or []
    if not evals:
        return {"by_microtopic": {}}

    rows = (
        supabase.table("writing_issue_events")
        .select("microtopic_id,affects_current_state,evaluation_id")
        .in_("evaluation_id", [e["id"] for e in evals])
        .eq("affects_current_state", True)
        .execute()
    ).data or []
    counts: dict[str, int] = {}
    for r in rows:
        key = r.get("microtopic_id") or "unmapped"
        counts[key] = counts.get(key, 0) + 1
    return {"by_microtopic": counts}


# --- internals ------------------------------------------------------------

def _current_projection_revision() -> int:
    """Code-defined projection revision pinned at session creation (§4.11)."""
    return 1


# Map the RPC RAISE prefixes to HTTP status codes.
_RPC_STATUS = {
    "ewp_not_found": 404,
    "ewp_stale_version": 409,
    "ewp_not_submittable": 409,
    "ewp_session_closed": 409,
    "ewp_reopen_forbidden": 409,
    "ewp_mode_unsupported": 400,
}


def _rpc_error(exc: Exception) -> HTTPException:
    msg = str(getattr(exc, "message", None) or exc)
    for prefix, code in _RPC_STATUS.items():
        if prefix in msg:
            return HTTPException(status_code=code, detail=msg.split("\n", 1)[0])
    logger.exception("writing-practice RPC failed")
    return HTTPException(status_code=500, detail="writing practice operation failed")


def _sibling_latest_texts(supabase: Any, session_id: str, *, exclude_unit_id: str) -> dict[int, str]:
    units = (
        supabase.table("writing_session_units").select("id,unit_number")
        .eq("session_id", session_id).execute()
    ).data or []
    out: dict[int, str] = {}
    for u in units:
        if u["id"] == exclude_unit_id:
            continue
        latest = (
            supabase.table("writing_unit_versions").select("answer_text,version_number")
            .eq("unit_id", u["id"]).order("version_number", desc=True).limit(1).execute()
        ).data or []
        if latest:
            out[u["unit_number"]] = latest[0]["answer_text"]
    return out
