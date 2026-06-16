"""Generated-mock attempt API (A-PR3, clean redo).

POST /api/study/mocks/generated/start
  Authed. Body carries ONLY exam_id, exam_phase_id, source — any client-supplied
  threshold fields are ignored (the service fixes them server-side). On a ready
  outcome it returns {blueprint_id, attempt_id, question_count, outcome,
  expires_at, selector_snapshot}; on a non-ready readiness verdict it returns 409
  with the verdict payload and writes nothing.

  Lives under the same /study/mocks/* family as the existing mock-engine routes
  (mock_engine.router), so submit/answer/result/review for a generated attempt go
  through the EXISTING engine endpoints unchanged.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.study_os.generated_mock_attempt import persist_and_start

logger = logging.getLogger("career_copilot.api.generated_mock")

router = APIRouter(prefix="/study/mocks/generated", tags=["generated-mock"])


class GeneratedStartBody(BaseModel):
    exam_id: str
    exam_phase_id: str
    source: str = "exam_realistic"
    # Extra fields (e.g. client-supplied thresholds) are ignored by default —
    # thresholds are fixed server-side in persist_and_start and cannot be
    # weakened by the caller.


@router.post("/start")
async def start_generated(
    body: GeneratedStartBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    try:
        result = persist_and_start(
            get_supabase_admin(),
            user_id=user_id,
            exam_id=body.exam_id,
            exam_phase_id=body.exam_phase_id,
            source=body.source,
        )
    except ValueError as exc:
        # Unsupported source (e.g. 'personalized' is A-PR5).
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError:
        logger.exception(
            "generated start failed user=%s exam=%s phase=%s",
            user_id, body.exam_id, body.exam_phase_id,
        )
        raise HTTPException(status_code=500, detail="Could not start generated attempt.")

    if result.get("outcome") != "ready":
        # READY-GATE: nothing was started; surface the verdict to the caller.
        raise HTTPException(status_code=409, detail=result)

    return {
        "blueprint_id": result["blueprint_id"],
        "attempt_id": result["attempt_id"],
        "question_count": result["question_count"],
        "outcome": result["outcome"],
        "expires_at": result["expires_at"],
        "selector_snapshot": result["selector_snapshot"],
    }
