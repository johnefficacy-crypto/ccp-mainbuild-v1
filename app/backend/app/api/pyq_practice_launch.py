"""PYQ v2 PR-9 (unit A) — server-owned "launch PYQ practice from a planner task".

A single POST under the existing ``/study/tasks`` surface — NOT a new top-level
or sidebar destination (respects the serial-delivery routing lock; no AdminShell/
adminRoutes/nav changes). The browser never picks mode/target/exam: the server
verifies task ownership, reads the pinned exam context from the caller-owned
``study_tasks`` row (the SOLE authority for exam context — client input is never
trusted), resolves the topic-practice payload, and starts the attempt through the
shared ``start_pyq_practice`` assembly path. The resulting attempt is a normal
mock attempt served by the existing ``/attempts/{id}`` routes.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.db.utils import maybe_single
from app.study_os import pyq_practice
from app.study_os.pyq_practice import start_pyq_practice
from app.study_os.pyq_practice_launch import resolve_practice_payload

router = APIRouter(prefix="/study/tasks", tags=["pyq-practice-launch"])


def _launch_blueprint_id(user_id: str, study_task_id: str) -> str:
    """Deterministic blueprint id for a (user, study task) launch, so a repeated
    POST (double-click / retry / refresh) reuses the same in-progress attempt via
    start_attempt_from_blueprint's idempotency path instead of duplicating it."""
    return str(uuid5(NAMESPACE_URL, f"pyq-practice-launch:{user_id}:{study_task_id}"))


def _owned_task(supabase: Any, user_id: str, study_task_id: str) -> dict:
    """The caller-owned ``study_tasks`` row, or 404.

    The task is the SOLE authoritative source of exam context (§17 content-
    scoping): study_tasks carry the exam_id / topic_id the task was scheduled
    under (migration 034). A client-supplied exam/topic is NEVER trusted —
    everything downstream reads the pinned columns here. A missing row or a row
    owned by another user is a 404 (never leak existence).
    """
    task = maybe_single(
        supabase.table("study_tasks")
        .select("id,user_id,exam_id,exam_phase_id,subject_id,topic_id,launch_context")
        .eq("id", str(study_task_id))
        .maybe_single()
    )
    if not task or task.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="study task not found")
    return task


@router.post("/{study_task_id}/launch-pyq-practice")
def launch_pyq_practice(study_task_id: UUID, user: dict = Depends(get_current_user)) -> dict:
    """Server-owned planner task -> PYQ practice launch (PYQ-PR9 unit A).

    Verifies ownership, resolves the task's topic-practice payload from its pinned
    exam context, and assembles the attempt. 404 when the task isn't the caller's,
    409 when the task has no topic/exam to practice or no projected PYQ pool exists,
    422 on malformed practice input.
    """
    supabase = get_supabase_admin()
    user_id = user.get("id")
    task = _owned_task(supabase, user_id, str(study_task_id))

    payload = resolve_practice_payload(task)
    if payload is None:
        raise HTTPException(status_code=409, detail="task has no topic/exam to practice")

    try:
        result = start_pyq_practice(
            supabase,
            user_id=user_id,
            mode=payload["mode"],
            target_id=payload["target_id"],
            exam_id=payload["exam_id"],
            # idempotent for the same task while the attempt is in-progress.
            blueprint_id=_launch_blueprint_id(user_id, str(study_task_id)),
        )
    except (pyq_practice.PracticeInputError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result.get("outcome") == "empty_pool":
        raise HTTPException(
            status_code=409,
            detail="No projected PYQ questions available for this topic yet.",
        )
    return result
