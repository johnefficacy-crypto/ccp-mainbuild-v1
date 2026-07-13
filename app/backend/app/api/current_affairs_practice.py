"""Current-affairs learner attempt API (GQR-G5a).

Server-owned CA attempt runtime on its OWN tables — GET state / save answer / submit.
The learner never supplies question IDs or bundle dates; those are frozen at start
(via the Subject Practice Hub ``weekly_current_affairs`` launch). Scoring is inline at
submit — NO mastery / SRS / Mistake-Book / correction-task write ever fires (GA never
enters the mock attempt path). Routes live under the existing /api/study surface — NOT
a new sidebar destination (no-new-surface rule)."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.current_affairs.attempts import (
    get_current_affairs_attempt,
    save_current_affairs_answer,
    submit_current_affairs_attempt,
)
from app.db.supabase_client import get_supabase_admin

logger = logging.getLogger("career_copilot.api.current_affairs_practice")

router = APIRouter(prefix="/study/current-affairs", tags=["study"])


class CaAnswerBody(BaseModel):
    question_id: UUID
    selected_option_id: UUID | None = None
    is_marked_for_review: bool = False
    time_spent_sec: int = 0
    client_seq: int = 0


@router.get("/attempts/{attempt_id}")
def get_ca_attempt(attempt_id: UUID, user: dict = Depends(get_current_user)) -> dict:
    try:
        return get_current_affairs_attempt(get_supabase_admin(), user.get("id"), str(attempt_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="attempt not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not attempt owner")


@router.post("/attempts/{attempt_id}/answer")
def save_ca_answer(
    attempt_id: UUID, body: CaAnswerBody, user: dict = Depends(get_current_user)
) -> dict:
    try:
        return save_current_affairs_answer(
            get_supabase_admin(), user.get("id"), str(attempt_id),
            question_id=str(body.question_id),
            selected_option_id=str(body.selected_option_id) if body.selected_option_id else None,
            is_marked_for_review=body.is_marked_for_review,
            time_spent_sec=body.time_spent_sec, client_seq=body.client_seq,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="attempt not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not attempt owner")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/attempts/{attempt_id}/submit")
def submit_ca_attempt(attempt_id: UUID, user: dict = Depends(get_current_user)) -> dict:
    try:
        result = submit_current_affairs_attempt(
            get_supabase_admin(), user.get("id"), str(attempt_id)
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="attempt not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not attempt owner")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if (result or {}).get("outcome") == "error":
        raise HTTPException(status_code=500, detail="Could not submit attempt.")
    return result
