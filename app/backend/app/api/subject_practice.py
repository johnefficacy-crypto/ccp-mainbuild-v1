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
from app.study_os.subject_runtime_policy import (
    MODE_ENGLISH_WRITING,
    MODE_TIMED_PRACTICE,
    MODE_TOPIC_PYQ,
    is_wired_mode,
    policy_for_family,
)
from app.study_os.subjects import locked_topic_ids_for_subject, subject_family_for
from app.study_os.writing_practice.subject_launch import resolve_launch_prompt_id

logger = logging.getLogger("career_copilot.api.subject_practice")

router = APIRouter(prefix="/study/subjects", tags=["study"])

_PRACTICE_LIMIT = 100

# Server-owned timed-practice countdown rate (GQR-R10). The attempt freezes
# ``seconds_per_question × frozen_question_count`` as its duration; the browser
# never sets the timer. A reviewed, per-topic target time may replace this flat
# rate later from real attempt data (mirrors the Quant target-time deferral).
_TIMED_SECONDS_PER_QUESTION = 60


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

    # Registry-driven dispatch (GQR-1): the mode must be a wired runtime mode in the
    # server-owned SubjectRuntimePolicy registry, and it routes through the handler
    # registered here — no ``if mode ==`` ladder. The browser submits only the mode;
    # the server still owns exam, prompt, bundle and question selection.
    handler = _LAUNCH_HANDLERS.get(body.mode) if is_wired_mode(body.mode) else None
    if handler is None:
        raise HTTPException(status_code=422, detail=f"unknown practice mode: {body.mode}")
    # Subject-family gate (checkpost #960): a wired mode must also be wired for THIS
    # subject's family — the browser is never trusted to only send modes the hub
    # offered. e.g. timed_practice is Reasoning-only in v1; posting it to a Quant
    # subject is rejected here, before any handler runs.
    family = subject_family_for(supabase, exam_id, str(subject_id))
    if body.mode not in policy_for_family(family).wired_runtime_modes:
        raise HTTPException(
            status_code=422,
            detail=f"practice mode {body.mode!r} is not available for this subject",
        )
    return handler(
        supabase, user_id=user_id, subject_id=str(subject_id),
        topic_id=str(body.topic_id) if body.topic_id else None, exam_id=exam_id,
    )


def _handle_english_writing(supabase, *, user_id, subject_id, topic_id, exam_id) -> dict:
    session_id = _launch_english(
        supabase, user_id=user_id, subject_id=subject_id, topic_id=topic_id, exam_id=exam_id,
    )
    return {"kind": "english_writing", "route": f"/app/study/practice/english/{session_id}"}


def _handle_topic_pyq(supabase, *, user_id, subject_id, topic_id, exam_id) -> dict:
    attempt_id = _launch_topic_pyq(
        supabase, user_id=user_id, subject_id=subject_id, topic_id=topic_id, exam_id=exam_id,
    )
    return {"kind": "pyq_practice", "route": f"/app/study/mocks/attempts/{attempt_id}"}


def _handle_timed_practice(supabase, *, user_id, subject_id, topic_id, exam_id) -> dict:
    # GQR-R10: identical server-owned topic assembly + scope gate as topic_pyq, plus a
    # server-owned countdown. Lands in the same objective attempt shell (which already
    # renders a timer when the frozen template carries duration_sec).
    attempt_id = _launch_topic_pyq(
        supabase, user_id=user_id, subject_id=subject_id, topic_id=topic_id, exam_id=exam_id,
        seconds_per_question=_TIMED_SECONDS_PER_QUESTION,
    )
    return {"kind": "pyq_practice", "route": f"/app/study/mocks/attempts/{attempt_id}"}


# Launch-handler dispatch table, keyed by wired runtime mode. Registering a new
# runtime = one entry here + one policy in subject_runtime_policy, not an if-ladder.
_LAUNCH_HANDLERS = {
    MODE_ENGLISH_WRITING: _handle_english_writing,
    MODE_TOPIC_PYQ: _handle_topic_pyq,
    MODE_TIMED_PRACTICE: _handle_timed_practice,
}


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


def _launch_topic_pyq(supabase, *, user_id, subject_id, topic_id, exam_id, seconds_per_question=None):
    if not topic_id:
        raise HTTPException(status_code=422, detail="topic_id is required for topic practice")
    if not exam_id:
        raise HTTPException(status_code=409, detail="no target exam resolved for topic practice")
    # Server-owned subject scope: the topic must belong to the PATH subject in the
    # caller's resolved exam. Never trust the browser-supplied topic_id to match
    # the path subject_id — reject a cross-subject topic (e.g. a Quant topic posted
    # to the English subject's launch path).
    if topic_id not in locked_topic_ids_for_subject(supabase, exam_id, subject_id):
        raise HTTPException(status_code=422, detail="topic_id does not belong to this subject")
    try:
        result = start_pyq_practice(
            supabase, user_id=user_id, mode="topic", target_id=topic_id,
            exam_id=exam_id, limit=_PRACTICE_LIMIT,
            seconds_per_question=seconds_per_question,
        )
    except PracticeInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError:
        logger.exception("subject topic practice failed user=%s topic=%s", user_id, topic_id)
        raise HTTPException(status_code=500, detail="Could not create practice attempt.")
    if result.get("outcome") == "empty_pool":
        raise HTTPException(status_code=409, detail="No verified practice set yet for this topic.")
    return result.get("attempt_id")
