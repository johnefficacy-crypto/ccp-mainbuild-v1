"""Subject Practice Hub — server-owned practice launch orchestrator.

POST /api/study/subjects/{subject_id}/practice/start dispatches a learner's
"practice this subject" click to the correct governed runtime WITHOUT the browser
choosing a prompt_id or a question set:
  * english_writing -> resolve a verified+active+applicable+runtime-ready writing
    prompt server-side, create a learning session (EWP single-birth path).
  * topic_pyq       -> assemble a verified, actively-projected PYQ practice attempt
    via the existing PYQ practice engine (topic mode).
Exam context is ALWAYS resolved server-side from the caller's target exam — a
client-supplied exam is never trusted (mirrors the planner launch endpoints).
A backend route under the existing /api/study surface — NOT a new sidebar
destination (no-new-surface rule)."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.writing_practice import create_learning_session
from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.study_os.planner import _resolve_target_exam
from app.study_os.pyq_practice import PracticeInputError, start_pyq_practice
from app.study_os.writing_practice.subject_launch import resolve_launch_prompt_id

logger = logging.getLogger("career_copilot.api.subject_practice")

router = APIRouter(prefix="/study/subjects", tags=["study"])

_PRACTICE_LIMIT = 100


class StartSubjectPracticeRequest(BaseModel):
    mode: str
    topic_id: UUID | None = None


@router.post("/{subject_id}/practice/start")
def start_subject_practice(
    subject_id: UUID,
    body: StartSubjectPracticeRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    user_id = user.get("id")
    supabase = get_supabase_admin()
    target = _resolve_target_exam(supabase, user_id)
    exam_id = target.get("id") if target else None

    if body.mode == "english_writing":
        session_id = _launch_english(
            supabase, user_id=user_id, subject_id=str(subject_id),
            topic_id=str(body.topic_id) if body.topic_id else None, exam_id=exam_id,
        )
        return {"kind": "english_writing", "route": f"/app/study/practice/english/{session_id}"}
    if body.mode == "topic_pyq":
        attempt_id = _launch_topic_pyq(
            supabase, user_id=user_id,
            topic_id=str(body.topic_id) if body.topic_id else None, exam_id=exam_id,
        )
        return {"kind": "pyq_practice", "route": f"/app/study/mocks/attempts/{attempt_id}"}
    raise HTTPException(status_code=422, detail=f"unknown practice mode: {body.mode}")


def _launch_english(supabase, *, user_id, subject_id, topic_id, exam_id):
    prompt_id = resolve_launch_prompt_id(
        supabase, subject_id=subject_id, topic_id=topic_id, exam_id=exam_id, exam_phase_id=None
    )
    if prompt_id is None:
        raise HTTPException(status_code=409, detail="no_eligible_prompt")
    session = create_learning_session(
        supabase, user_id=user_id, prompt_id=prompt_id, study_task_id=None,
        exam_id=exam_id, exam_phase_id=None,
    )
    return session.get("id")


def _launch_topic_pyq(supabase, *, user_id, topic_id, exam_id):
    if not topic_id:
        raise HTTPException(status_code=422, detail="topic_id is required for topic practice")
    if not exam_id:
        raise HTTPException(status_code=409, detail="no target exam resolved for topic practice")
    try:
        result = start_pyq_practice(
            supabase, user_id=user_id, mode="topic", target_id=topic_id,
            exam_id=exam_id, limit=_PRACTICE_LIMIT,
        )
    except PracticeInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError:
        logger.exception("subject topic practice failed user=%s topic=%s", user_id, topic_id)
        raise HTTPException(status_code=500, detail="Could not create practice attempt.")
    if result.get("outcome") == "empty_pool":
        raise HTTPException(status_code=409, detail="No verified practice set yet for this topic.")
    return result.get("attempt_id")
