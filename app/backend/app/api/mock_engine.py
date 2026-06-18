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
from app.study_os.mastery_writer import MasteryWriter, get_mastery_write_flag
from app.study_os.mock_engine import (
    AnswerPersistenceError,
    AttemptFinalizationError,
    ConflictError,
    SubmissionPersistenceError,
    SubmitConsistencyError,
    enqueue_mastery_retry_required,
    has_active_mastery_retry,
    mark_mastery_retry_done_required,
    mastery_retry_done,
    get_attempt,
    get_result,
    get_review,
    get_analytics,
    save_answer,
    start_attempt,
    submit_attempt,
    enter_section,
)

logger = logging.getLogger("career_copilot.api.mock_engine")

router = APIRouter(prefix="/study/mocks", tags=["mock-engine"])


# ── request bodies ─────────────────────────────────────────────────────────────

class StartAttemptBody(BaseModel):
    template_slug: str


class EnterSectionBody(BaseModel):
    section_index: int = Field(ge=0)


class AnswerBody(BaseModel):
    question_id: str
    selected_option_id: str | None = None
    is_marked_for_review: bool = False
    client_seq: int = Field(ge=0)
    time_spent_sec: int = Field(default=0, ge=0)


class SubmitBody(BaseModel):
    claimed_answered_count: int | None = None


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


@router.post("/attempts/{attempt_id}/enter-section")
async def enter_section_route(
    attempt_id: str,
    body: EnterSectionBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        return enter_section(get_supabase_admin(), user_id, attempt_id, body.section_index)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


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
        raise HTTPException(status_code=422, detail=str(exc))
    except AnswerPersistenceError as exc:
        logger.error("answer persistence failed attempt=%s", attempt_id, exc_info=exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "persistence_failed", "detail": str(exc)},
            headers={"Retry-After": "1"},
        )


def _attempt_status(sb: Any, attempt_id: str) -> str | None:
    rows = (
        sb.table("mock_attempts")
        .select("status")
        .eq("id", attempt_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0].get("status") if rows else None


@router.post("/attempts/{attempt_id}/submit")
async def submit(
    attempt_id: str,
    body: SubmitBody = SubmitBody(),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        sb = get_supabase_admin()
        # submit_attempt already scores, flips status, and runs derivation with
        # its own retry queue — no second compute_and_persist here. The mastery
        # writer derives inline from the persisted raw responses (implementation
        # B; see mastery_writer.process_attempt), so it runs independently and a
        # derivation failure cannot silently suppress the write-back.
        was_submitted = _attempt_status(sb, attempt_id) == "submitted"
        result = submit_attempt(sb, user_id, attempt_id, body.claimed_answered_count)
        flag_state = get_mastery_write_flag()
        if flag_state != "off" and not (was_submitted and mastery_retry_done(sb, attempt_id, flag_state)):
            if not has_active_mastery_retry(sb, attempt_id):
                try:
                    writer = MasteryWriter(sb, flag_state)
                    await writer.process_attempt(attempt_id)
                    mark_mastery_retry_done_required(sb, attempt_id, flag_state)
                except Exception as exc:  # noqa: BLE001
                    try:
                        enqueue_mastery_retry_required(sb, attempt_id, flag_state, last_error=str(exc))
                    except Exception as enqueue_exc:  # noqa: BLE001
                        logger.exception(
                            "mastery retry enqueue failed attempt=%s user=%s",
                            attempt_id,
                            user_id,
                        )
                        raise HTTPException(
                            status_code=503,
                            detail={"error": "mastery_retry_enqueue_failed", "detail": str(enqueue_exc)},
                            headers={"Retry-After": "1"},
                        ) from enqueue_exc
                    logger.exception("mastery write-back failed attempt=%s user=%s", attempt_id, user_id)
        return result
    except SubmitConsistencyError as exc:
        logger.warning("submit consistency mismatch attempt=%s: %s", attempt_id, exc)
        raise HTTPException(status_code=409, detail={"error": "client_server_mismatch", "detail": str(exc)})
    except (SubmissionPersistenceError, AttemptFinalizationError) as exc:
        # A correctness-critical write failed mid-finalization. The attempt is
        # left in_progress (no silent 200), so signal a retryable 503 rather
        # than a generic 500 — submit is idempotent and safe to re-run.
        logger.error("submit persistence failed attempt=%s user=%s", attempt_id, user_id, exc_info=exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "submit_persist_failed", "detail": str(exc)},
            headers={"Retry-After": "1"},
        )
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
