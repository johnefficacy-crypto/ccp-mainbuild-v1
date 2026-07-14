"""Calculation Gym learner runtime API (GQR-Q8 learner wiring).

Sessions are created only through the subject-practice launcher. This API reads
the frozen owner-scoped session and atomically submits the learner's answers.
The browser never supplies a seed, generator policy, question count, duration,
or expected answer.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.study_os.calc_gym import get_session, submit_session

router = APIRouter(prefix="/study/calculation-gym", tags=["study"])


class CalcGymAnswer(BaseModel):
    item_index: int = Field(ge=0, le=99)
    user_answer: str | None = Field(default=None, max_length=64)
    time_spent_sec: int = Field(default=0, ge=0, le=3600)


class CalcGymSubmitBody(BaseModel):
    answers: list[CalcGymAnswer] = Field(default_factory=list, max_length=100)


@router.get("/sessions/{session_id}")
def get_calc_gym_session(session_id: UUID, user: dict = Depends(get_current_user)) -> dict:
    try:
        return get_session(
            get_supabase_admin(), session_id=str(session_id), user_id=user.get("id")
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="session not found")


@router.post("/sessions/{session_id}/submit")
def submit_calc_gym_session(
    session_id: UUID,
    body: CalcGymSubmitBody,
    user: dict = Depends(get_current_user),
) -> dict:
    answers: dict[int, dict] = {}
    for answer in body.answers:
        if answer.item_index in answers:
            raise HTTPException(status_code=422, detail="duplicate item_index")
        answers[answer.item_index] = {
            "user_answer": answer.user_answer,
            "time_spent_sec": answer.time_spent_sec,
        }
    try:
        return submit_session(
            get_supabase_admin(), session_id=str(session_id),
            user_id=user.get("id"), answers=answers,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
