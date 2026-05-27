"""Mock Engine API — PR1 vertical slice.

Routes (all under /api/study/mocks):
  POST /attempts/start          -> start or 409 active conflict
  GET  /attempts/:id            -> current attempt state
  POST /attempts/:id/answer     -> idempotent upsert, reject if expired
  POST /attempts/:id/submit     -> score + finalise, idempotent
  GET  /attempts/:id/result     -> score summary + per-question breakdown
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.study_os.mock_engine import (
    ConflictError,
    get_attempt,
    get_result,
    get_review,
    get_analytics,
    save_answer,
    start_attempt,
    submit_attempt,
)

logger = logging.getLogger("career_copilot.api.mock_engine")

router = APIRouter(prefix="/study/mocks", tags=["mock-engine"])


# ── request bodies ─────────────────────────────────────────────────────────────

class StartAttemptBody(BaseModel):
    template_slug: str


class AnswerBody(BaseModel):
    question_id: str
    selected_option_id: str | None = None
    is_marked_for_review: bool = False
    client_seq: int = Field(ge=0)
    time_spent_sec: int = Field(default=0, ge=0)


# ── routes ─────────────────────────────────────────────────────────────────────

@router.post("/attempts/start")
async def start(
    body: StartAttemptBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        return start_attempt(get_supabase_admin(), user_id, body.template_slug)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError:
        logger.exception("start_attempt failed for user=%s slug=%s", user_id, body.template_slug)
        raise HTTPException(status_code=500, detail="Could not create attempt.")


@router.get("/attempts/{attempt_id}")
async def read_attempt(
    attempt_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        return get_attempt(get_supabase_admin(), user_id, attempt_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/attempts/{attempt_id}/answer")
async def answer(
    attempt_id: str,
    body: AnswerBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        return save_answer(
            get_supabase_admin(),
            user_id,
            attempt_id,
            body.question_id,
            body.selected_option_id,
            body.is_marked_for_review,
            body.client_seq,
            body.time_spent_sec,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/attempts/{attempt_id}/submit")
async def submit(
    attempt_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        return submit_attempt(get_supabase_admin(), user_id, attempt_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError:
        logger.exception("submit_attempt failed attempt=%s user=%s", attempt_id, user_id)
        raise HTTPException(status_code=500, detail="Could not submit attempt.")


@router.get("/attempts/{attempt_id}/result")
async def result(
    attempt_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        return get_result(get_supabase_admin(), user_id, attempt_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/attempts/{attempt_id}/review")
async def review(
    attempt_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        return get_review(get_supabase_admin(), user_id, attempt_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/attempts/{attempt_id}/analytics")
async def analytics(
    attempt_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        return get_analytics(get_supabase_admin(), user_id, attempt_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
