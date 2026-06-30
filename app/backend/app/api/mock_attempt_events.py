"""Mock Attempt Events API (PR2b).

Routes (mounted under /api/study/mocks/attempts):
  POST /:attempt_id/events   — ingest client event batch (attempt owner only)
  GET  /:attempt_id/events   — list events (attempt owner OR mock_questions:publish)

Server-emitted events are written by mock_engine.py directly; this router
handles only the client-side telemetry ingest and the read path.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import get_current_user, require_permission
from app.core.permissions import MOCK_QUESTIONS_PUBLISH
from app.db.supabase_client import get_supabase_admin
from app.study_os import attempt_events as svc

logger = logging.getLogger("career_copilot.api.mock_attempt_events")

router = APIRouter(prefix="/study/mocks/attempts", tags=["mock-attempt-events"])

MAX_BATCH = 100
_SUBMIT_GRACE_SECS = 300  # allow client flush up to 5 min after submit


# ── request bodies ─────────────────────────────────────────────────────────────

class ClientEvent(BaseModel):
    event_type: str
    sequence_no: int | None = None
    occurred_at: str
    payload: dict = Field(default_factory=dict)


class PostEventsBody(BaseModel):
    events: list[ClientEvent]


# ── helpers ────────────────────────────────────────────────────────────────────

def _fetch_attempt_for_user(supabase: Any, user_id: str, attempt_id: str) -> dict:
    rows = supabase.table("mock_attempts") \
        .select("id,user_id,status,submitted_at") \
        .eq("id", attempt_id) \
        .eq("user_id", user_id) \
        .limit(1) \
        .execute()
    items = getattr(rows, "data", None) or []
    if not items:
        raise HTTPException(status_code=403, detail="Attempt not found or access denied.")
    return items[0]


def _assert_attempt_accepts_events(attempt: dict) -> None:
    """Raise 409 if the attempt is in a terminal state past the grace window."""
    status = attempt.get("status")
    if status == "in_progress":
        return
    if status == "submitted":
        submitted_at_str = attempt.get("submitted_at")
        if submitted_at_str:
            try:
                submitted_at = datetime.fromisoformat(
                    submitted_at_str.replace("Z", "+00:00")
                )
                grace_end = submitted_at + timedelta(seconds=_SUBMIT_GRACE_SECS)
                if datetime.now(timezone.utc) <= grace_end:
                    return
            except Exception:  # noqa: BLE001
                pass
    raise HTTPException(
        status_code=409,
        detail=f"Attempt is in terminal state '{status}' and no longer accepts events.",
    )


# ── routes ─────────────────────────────────────────────────────────────────────

@router.post("/{attempt_id}/events")
async def post_events(
    attempt_id: str,
    body: PostEventsBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if len(body.events) > MAX_BATCH:
        raise HTTPException(
            status_code=413,
            detail=f"Batch too large: max {MAX_BATCH} events per call, got {len(body.events)}.",
        )

    supabase = get_supabase_admin()
    attempt = _fetch_attempt_for_user(supabase, user["id"], attempt_id)
    _assert_attempt_accepts_events(attempt)

    raw_events = [e.model_dump() for e in body.events]
    result = svc.ingest_client_events(supabase, attempt_id, user["id"], raw_events)

    # If client events were accepted AFTER submission (late delivery within the
    # grace window), idempotently recompute the persisted analytics so the frozen
    # classifications / dwell reflect them. This closes the submit/late-event
    # race: even if a pre-submit flush did not fully drain, the analytics snapshot
    # the shadow gate validates is brought up to date. Best-effort — a recompute
    # failure never breaks ingest.
    if attempt.get("status") == "submitted" and result.get("accepted"):
        try:
            from app.study_os.attempt_analytics.service import compute_and_persist
            compute_and_persist(supabase, attempt_id)
            result["analytics_recomputed"] = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("late-event analytics recompute failed for %s: %s", attempt_id, exc)
            result["analytics_recomputed"] = False
    return result


@router.get("/{attempt_id}/events")
async def get_events(
    attempt_id: str,
    page: int = Query(default=0, ge=0),
    page_size: int = Query(default=500, ge=1, le=1000),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    supabase = get_supabase_admin()

    # Attempt owner OR publisher can read events.
    rows = supabase.table("mock_attempts") \
        .select("id,user_id") \
        .eq("id", attempt_id) \
        .limit(1) \
        .execute()
    items = getattr(rows, "data", None) or []
    if not items:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    is_owner = items[0].get("user_id") == user["id"]
    is_publisher = (
        user.get("role") == "super_admin"
        or MOCK_QUESTIONS_PUBLISH in (user.get("permissions") or [])
    )
    if not is_owner and not is_publisher:
        raise HTTPException(status_code=403, detail="Access denied.")

    return svc.get_events(supabase, attempt_id, page=page, page_size=page_size)
