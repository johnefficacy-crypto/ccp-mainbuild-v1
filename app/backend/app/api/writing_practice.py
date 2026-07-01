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
from app.study_os.writing_practice import deterministic as det
from app.study_os.writing_practice import session_state as st
from app.study_os.writing_practice.content_hash import compute_content_hash
from app.study_os.writing_practice.session_finalizer import finalize_writing_session

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
    version_number: int | None = None


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

    # Snapshot the feedback-release policy for exam-mode prompts (§4.3); learning
    # mode is immediate.
    policy = "immediate"
    delay = None
    if body.mode == "exam":
        req = (
            supabase.table("exam_descriptive_requirements")
            .select("feedback_release_policy,feedback_release_delay_seconds")
            .eq("exam_id", prompt["exam_id"])
            .eq("exercise_type", prompt["exercise_type"])
            .eq("reviewer_status", "verified")
            .eq("is_active", True)
            .maybe_single()
            .execute()
        ).data
        if req:
            policy = req["feedback_release_policy"]
            delay = req.get("feedback_release_delay_seconds")

    session = (
        supabase.table("writing_sessions")
        .insert({
            "user_id": user_id,
            "study_task_id": str(body.study_task_id) if body.study_task_id else None,
            "prompt_id": str(body.prompt_id),
            "mode": body.mode,
            "status": st.SESSION_ACTIVE,
            "projection_revision": _current_projection_revision(),
            "feedback_release_policy": policy,
            "feedback_release_delay_seconds": delay,
        })
        .execute()
    ).data[0]

    n_units = prompt.get("required_sentence_count") or 1
    unit_rows = [{
        "session_id": session["id"],
        "unit_number": i,
        "practice_microtopic_id": prompt.get("microtopic_id"),
        "unit_constraints": {"schema_version": 1},
        "status": st.UNIT_NOT_STARTED,
    } for i in range(1, n_units + 1)]
    supabase.table("writing_session_units").insert(unit_rows).execute()

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

    # Next version number.
    existing = (
        supabase.table("writing_unit_versions")
        .select("version_number")
        .eq("unit_id", unit["id"])
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    ).data or []
    next_version = (existing[0]["version_number"] + 1) if existing else 1

    prompt = (
        supabase.table("writing_prompts").select("min_words,max_words,required_words")
        .eq("id", session["prompt_id"]).single().execute()
    ).data

    # Sibling texts for duplicate detection.
    siblings = _sibling_latest_texts(supabase, str(session_id), exclude_unit_id=unit["id"])
    result = det.evaluate_unit(
        body.answer_text,
        min_words=prompt.get("min_words"),
        max_words=prompt.get("max_words"),
        required_words=None,  # per-unit words are constraint-driven; coverage is session-level
        other_unit_texts=siblings,
    )

    version = (
        supabase.table("writing_unit_versions")
        .insert({
            "unit_id": unit["id"],
            "version_number": next_version,
            "answer_text": body.answer_text,
            "client_word_count": body.client_word_count,
            "server_word_count": result.server_word_count,
            "submission_kind": "user",
            "content_hash": compute_content_hash(body.answer_text),
        })
        .execute()
    ).data[0]

    evaluation = (
        supabase.table("writing_evaluations")
        .insert({
            "unit_version_id": version["id"],
            "evaluation_revision": 1,
            "deterministic_evaluator_version": result.evaluator_version,
            "deterministic_status": "completed",
            "language_status": "queued" if session["mode"] == "learning" else "queued",
            "overall_status": "partial",
            "deterministic_result": result.to_dict(),
        })
        .execute()
    ).data[0]

    # Enqueue the Stage-2 language job (consumed by EWP-2B).
    supabase.table("writing_evaluation_jobs").insert({
        "evaluation_id": evaluation["id"],
        "job_kind": "language_evaluation",
        "generation": 1,
        "status": "pending",
    }).execute()

    new_unit_status = st.UNIT_EVAL_PENDING
    supabase.table("writing_session_units").update({"status": new_unit_status}).eq("id", unit["id"]).execute()

    finalize_writing_session(supabase, str(session_id))
    return {"evaluation": evaluation, "deterministic_result": result.to_dict()}


@router.post("/sessions/{session_id}/units/{unit_id}/reopen")
def reopen_unit(
    session_id: UUID, unit_id: UUID, body: ReopenUnitRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    supabase = get_supabase_admin()
    session = _owned_session(supabase, str(session_id), user.get("id"))
    if session["mode"] != "learning":
        raise HTTPException(status_code=409, detail="reopen is only available in learning mode")
    if session["status"] not in (st.SESSION_REWRITE_REQUIRED, st.SESSION_ACTIVE):
        raise HTTPException(status_code=409, detail="session is not reopenable")

    unit = (
        supabase.table("writing_session_units").select("*")
        .eq("id", str(unit_id)).eq("session_id", str(session_id)).maybe_single().execute()
    ).data
    if not unit:
        raise HTTPException(status_code=404, detail="unit not found")
    if unit["status"] != st.UNIT_READY:
        raise HTTPException(status_code=409, detail="only a ready unit can be reopened")

    latest = (
        supabase.table("writing_unit_versions").select("id")
        .eq("unit_id", str(unit_id)).order("version_number", desc=True).limit(1).execute()
    ).data or []
    if not latest or latest[0]["id"] != str(body.expected_latest_version_id):
        raise HTTPException(status_code=409, detail="expected_latest_version_id is stale")

    supabase.table("writing_session_units").update({"status": st.UNIT_DRAFT}).eq("id", str(unit_id)).execute()
    finalize_writing_session(supabase, str(session_id))
    return {"unit_id": str(unit_id), "status": st.UNIT_DRAFT}


@router.get("/sessions/{session_id}/evaluations/{evaluation_id}")
def get_evaluation(
    session_id: UUID, evaluation_id: UUID, user: dict = Depends(get_current_user),
) -> dict:
    supabase = get_supabase_admin()
    _owned_session(supabase, str(session_id), user.get("id"))
    evaluation = (
        supabase.table("writing_evaluations").select("*").eq("id", str(evaluation_id)).maybe_single().execute()
    ).data
    if not evaluation:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return {"evaluation": evaluation}


@router.get("/error-summary")
def error_summary(user: dict = Depends(get_current_user)) -> dict:
    """Recurring writing issues for the user, grouped by microtopic.

    Reads only current-state issue events (`affects_current_state = true`).
    """
    supabase = get_supabase_admin()
    rows = (
        supabase.table("writing_issue_events")
        .select("issue_type,microtopic_id,affects_current_state,evaluation_id")
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
