"""Study OS Mission Control API (PR3).

Adds GET /api/study/mission-control on top of the existing
``/api/study/*`` surface owned by ``app.api.canonical.router_study``.
Kept as a separate router so PR3 doesn't touch the canonical file.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.study_os.mission_control import (
    build_mission_control,
    build_mission_control_async,
    build_task_reasoning_response,
)
from app.study_os.plan_preferences import get_plan_preferences, upsert_plan_preferences
from app.study_os.mastery_writer import get_mastery_write_flag
from app.study_os.planner import apply_plan, compute_draft_plan, generate_plan
from app.study_os import calibration
from app.study_os import mocks as mocks_service
from app.study_os import plan_by_subject as plan_by_subject_service
from app.study_os import planner_board as planner_board_service
from app.study_os import plan_timeline as plan_timeline_service
from app.study_os import subjects as subjects_service
from app.study_os import weekly_review as weekly_review_service
from app.study_os import report_cards as report_cards_service
from app.study_os import roadmap as roadmap_service
from app.study_os.improvement_lab import build_feed as _build_improvement_lab_feed

logger = logging.getLogger("career_copilot.api.study_os")

router = APIRouter(prefix="/study", tags=["study"])


def _safe(call: Any, default: Any = None) -> Any:
    """Run a Supabase read; on any error return ``default``.

    Mirrors ``app.study_os.planner._safe``. Used by reads whose failure must be
    distinguishable from an empty result, by passing a ``None`` default.
    """
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("study_os read failed: %s", exc)
        return default



def _require_canonical_exam_flag() -> bool:
    raw = os.getenv("STUDY_OS_REQUIRE_CANONICAL_EXAM")
    if raw is None:
        env = (os.getenv("ENV") or os.getenv("APP_ENV") or os.getenv("PYTHON_ENV") or "").lower()
        return env in {"dev", "development", "local", "test"}
    return str(raw).lower() in {"1", "true", "yes", "on"}


_TARGET_EXAM_REQUIRED_DETAIL = {
    "code": "TARGET_EXAM_REQUIRED",
    "message": "Choose the exam you are preparing for.",
}

# A failed persist (any critical write returned no rows) is a server fault —
# 500. A precondition the user/admin must satisfy first (no target exam, no
# locked coverage, every topic muted) is unprocessable — 422.
_PLAN_UNPROCESSABLE_REASONS = {
    "no_user",
    "no_target_exam",
    "no_locked_coverage",
    "all_topics_muted",
    "target_changed",
    # The target exam is retired/sandbox. A client-correctable state (pick a
    # live exam), not a server fault — 422, not 500.
    "exam_inactive",
}


def _raise_for_plan_failure(result: dict[str, Any]) -> dict[str, Any]:
    """Translate a planner ``{generated|applied: False}`` envelope to HTTP.

    The planner reports failure in-band so it can stay non-raising and
    deterministic. The ``/apply`` and ``/generate`` routes must not return
    a 2xx on a failed apply (that let the frontend show "Plan applied" while
    the persist 23502'd). Success envelopes pass through unchanged.
    """
    if result.get("generated") is False or result.get("applied") is False:
        reason = result.get("reason") or "unknown"
        status_code = 422 if reason in _PLAN_UNPROCESSABLE_REASONS else 500
        raise HTTPException(status_code=status_code, detail=result)
    return result


def _calibration_gate_response(
    supabase: Any, user_id: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Backend half of the onboarding-calibration gate (must not be UI-only).

    Returns ``(early_response_or_None, resolved_exam_id)``. The target exam is
    resolved ONCE here (health-aware); the caller passes ``resolved_exam_id`` into
    the planner as ``expected_exam_id`` so the planner does not independently
    re-resolve — closing the gate→planner TOCTOU where the target could change to
    an unchecked exam between the two resolutions.

    The early response is the stable ``calibration_required`` envelope so the
    caller can short-circuit BEFORE the planner (no generation, HTTP 200). It is
    ``None`` — meaning "proceed" — when there is no target exam or calibration is
    not required. ``calibration_required`` already returns False for an empty
    required set, a completed/skipped gate, OR an existing plan (grandfathered).
    """
    # Resolve the target exam ONCE, health-aware. A transient profile/preference
    # read failure must NOT look like "no target exam → proceed" (which would let
    # the planner re-resolve and generate an uncalibrated first plan).
    exam, exam_ok = calibration.resolve_target_exam_checked(supabase, user_id)
    if not exam_ok:
        raise HTTPException(
            status_code=503,
            detail={"reason": "calibration_check_failed", "generated": False},
        )
    exam_id = exam.get("id") if exam else None
    if not exam_id:
        # Checked, reads healthy, genuinely NO target exam. Hand the planner a
        # sentinel rather than None so that if a target appears before the planner
        # resolves (no-target → exam B race), the planner's expected_exam_id guard
        # rejects B as target_changed instead of generating an unchecked plan.
        return None, calibration.NO_TARGET_SENTINEL
    try:
        required = calibration.calibration_required(supabase, user_id, str(exam_id))
    except calibration.CalibrationUnavailable:
        # Fail closed: the gate state is unknown (a read failed), so we must NOT
        # generate a possibly-uncalibrated first plan. Surface a retryable 503.
        raise HTTPException(
            status_code=503,
            detail={"reason": "calibration_check_failed", "generated": False},
        )
    if required:
        return calibration.calibration_required_payload(exam_id), str(exam_id)
    return None, str(exam_id)


def _require_canonical_target(supabase: Any, user_id: str) -> str | None:
    """Enforce the canonical-exam flag uniformly across plan endpoints.

    Returns the stored ``profiles.target_exam`` value when the flag is on,
    or ``None`` when the flag is off (callers should not branch on the
    return value beyond passing it through). Raises a 400 with a stable
    structured detail when the flag is on but no target is set.
    """
    if not _require_canonical_exam_flag():
        return None
    target = (
        supabase.table("profiles")
        .select("target_exam")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    value = target[0].get("target_exam") if target else None
    if not value:
        raise HTTPException(status_code=400, detail=_TARGET_EXAM_REQUIRED_DETAIL)
    return value


def _locked_coverage_counts(supabase: Any, exam_ids: list[str]) -> dict[str, int] | None:
    """Locked ``exam_topic_coverage`` row count per exam, or ``None`` when the
    read failed. One bulk read — the exam drawer and the roadmap share it."""
    coverage_rows = _safe(
        lambda: (
            supabase.table("exam_topic_coverage")
            .select("exam_id")
            .in_("exam_id", exam_ids)
            .eq("reviewer_status", "locked")
            .execute()
            .data
        ),
        default=None,
    )
    if coverage_rows is None:
        return None
    counts: dict[str, int] = {}
    for c in coverage_rows:
        key = str(c.get("exam_id"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _is_planner_ready(exam: dict[str, Any], locked_counts: dict[str, int] | None) -> bool:
    """The exam drawer's planner-ready rule: active AND at least one locked
    coverage row. Fails closed on a coverage read failure (``None``): reporting
    ready off a failed read would send a user into a planner with no syllabus."""
    if locked_counts is None:
        return False
    return bool(exam.get("is_active")) and locked_counts.get(str(exam.get("id")), 0) > 0


class SetTargetExamBody(BaseModel):
    exam_id: UUID


@router.get("/exams")
async def list_study_exams(
    planner_ready: bool | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Active exams with their planner-readiness.

    Previously this issued TWO Supabase round-trips PER EXAM inside a loop over
    up to 500 rows — a thousand sequential requests, none of them wrapped, on a
    route with no error handling. One slow or failed call anywhere in that loop
    threw out of the route as a 500, and the page showed "Couldn't load exams"
    for every user, every time. The per-exam reads are now two bulk queries,
    and a read failure degrades to a named reason instead of an exception.
    """
    del user
    supabase = get_supabase_admin()

    rows = _safe(
        lambda: (
            supabase.table("exams")
            .select("id,slug,name,exam_type,exam_family_id,default_difficulty_level,is_active")
            .eq("is_active", True)
            .order("name")
            .limit(500)
            .execute()
            .data
        ),
        default=None,
    )
    if rows is None:
        logger.error("study/exams: exams read failed")
        raise HTTPException(
            status_code=503,
            detail={"code": "exams_read_failed", "message": "Exams are unavailable right now."},
        )
    if not rows:
        logger.warning("study/exams: public.exams has zero active rows")
        return {"items": []}

    exam_ids = [r["id"] for r in rows if r.get("id")]

    # One read for every exam's locked-coverage subject ids. `count="exact"` per
    # exam is what forced the old loop; pulling the exam_id column and counting
    # in Python costs one request instead of N.
    counts = _locked_coverage_counts(supabase, exam_ids)
    coverage_ok = counts is not None
    locked_counts: dict[str, int] = counts or {}

    # One read for the soonest verified upcoming cycle per exam. Ordered
    # ascending so the first row seen for an exam is its soonest.
    today_iso = datetime.now(timezone.utc).date().isoformat()
    next_cycles: dict[str, dict[str, Any]] = {}
    cycle_rows = _safe(
        lambda: (
            supabase.table("exam_cycles")
            .select("id,exam_id,year,cycle_name,exam_start")
            .in_("exam_id", exam_ids)
            .eq("reviewer_status", "verified")  # trust gate (migration 261)
            .gte("exam_start", today_iso)
            .order("exam_start")
            .execute()
            .data
        ),
        default=None,
    )
    for c in cycle_rows or []:
        next_cycles.setdefault(str(c.get("exam_id")), c)

    out = []
    for r in rows:
        locked_count = locked_counts.get(str(r["id"]), 0)
        # Fail closed on a coverage read failure: an exam is only planner-ready
        # when we actually READ locked coverage for it (see _is_planner_ready).
        ready = _is_planner_ready(r, counts)
        row = {
            **r,
            "locked_coverage_count": locked_count,
            "next_cycle": next_cycles.get(str(r["id"])),
            "planner_ready": ready,
        }
        if planner_ready is None or row["planner_ready"] == planner_ready:
            out.append(row)
    return {"items": out, "coverage_read_failed": not coverage_ok}


@router.get("/target-exam")
async def get_target_exam(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Return the user's current target exam, or ``{"selected_exam": None}``.

    Lets the frontend hydrate the picker on mount without re-running plan
    compute. Looks the exam up by id (UUID) so the response shape matches
    ``PUT /target-exam`` and ``GET /plan/draft.selected_exam``.
    """
    user_id = user.get("id")
    supabase = get_supabase_admin()
    profile = (
        supabase.table("profiles")
        .select("target_exam")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    target_value = profile[0].get("target_exam") if profile else None
    if not target_value:
        return {"selected_exam": None}
    exam_rows = (
        supabase.table("exams")
        .select("id,slug,name,is_active")
        .eq("id", target_value)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not exam_rows:
        return {"selected_exam": None}
    ex = exam_rows[0]
    return {
        "selected_exam": {
            "id": ex.get("id"),
            "slug": ex.get("slug"),
            "name": ex.get("name"),
            "is_active": bool(ex.get("is_active")),
        }
    }


@router.put("/target-exam")
async def set_target_exam(
    body: SetTargetExamBody,
    confirm_archive: bool = False,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = user.get("id")
    exam_id = str(body.exam_id)
    supabase = get_supabase_admin()
    exam_rows = (
        supabase.table("exams").select("id,slug,name,is_active").eq("id", exam_id).eq("is_active", True).limit(1).execute().data
        or []
    )
    if not exam_rows:
        raise HTTPException(status_code=400, detail="Invalid active exam_id")
    exam = exam_rows[0]
    active = (
        supabase.table("study_plans")
        .select("id,exam_id,target_exam,end_date,status")
        .eq("user_id", user_id)
        .eq("status", "active")
        .limit(1)
        .execute()
        .data
        or []
    )
    previous_exam: str | None = None
    archived_plan_id: str | None = None
    if active:
        p = active[0]
        prev = p.get("exam_id") or p.get("target_exam")
        if prev and str(prev) != str(exam_id):
            if not confirm_archive:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "ACTIVE_PLAN_EXISTS", "requires_confirmation": True},
                )
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date().isoformat()
            supabase.table("study_plans").update({"status": "archived", "end_date": today}).eq("id", p["id"]).execute()
            previous_exam = str(prev)
            archived_plan_id = str(p.get("id"))
    supabase.table("profiles").update({"target_exam": exam_id}).eq("id", user_id).execute()
    pref = (
        supabase.table("aspirant_preferences").select("id,target_exams").eq("user_id", user_id).limit(1).execute().data
        or []
    )
    cur = list((pref[0].get("target_exams") if pref else []) or [])
    next_exams = [exam.get("slug")] + [x for x in cur if x != exam.get("slug")]
    supabase.table("aspirant_preferences").upsert({"user_id": user_id, "target_exams": next_exams}, on_conflict="user_id").execute()

    # D5 — regenerate for the NEW exam before returning.
    #
    # ``archived`` is terminal: nothing in the repo ever writes study_plans.status
    # back to 'active' (the only writer of 'active' is the planner's own INSERT in
    # _persist), and BOTH regeneration entry points require an active plan —
    # regenerate_stale_plans filters .eq("status","active") and regenerate_on_signal
    # returns no_active_plan. So a switch that archives without regenerating leaves
    # the user with zero active plans and no automatic route back; that is what
    # stopped this platform planning for two months.
    #
    # Strictly AFTER both the profiles and aspirant_preferences writes: the planner
    # resolves the target exam from profiles, so running earlier would rebuild the
    # plan for the exam the user just left. The old plan is never resurrected — the
    # planner INSERTs a fresh row for the new exam.
    #
    # Best-effort by contract: the switch is the user's request and has already
    # succeeded. Generation never fails it; the outcome is reported, not swallowed.
    plan_outcome: dict[str, Any] = {"created": False, "reason": "error"}
    try:
        envelope = _apply_plan_envelope(supabase, user_id)
        created = bool(envelope.get("generated") or envelope.get("applied"))
        plan_outcome = {
            "created": created,
            # Verbatim planner vocabulary — calibration_required, no_locked_coverage,
            # planner_activation_disabled, ... Never a string invented here.
            "reason": None if created else (envelope.get("reason") or "error"),
        }
    except Exception:  # noqa: BLE001 — a generation fault must not fail the switch
        logger.exception(
            "target-exam switch: plan regeneration failed for user=%s new_exam=%s",
            user_id,
            exam_id,
        )

    logger.info(
        "target-exam switch user=%s old_exam=%s new_exam=%s archived_plan=%s "
        "plan_created=%s reason=%s",
        user_id,
        previous_exam,
        exam_id,
        archived_plan_id,
        plan_outcome["created"],
        plan_outcome["reason"],
    )
    return {
        "ok": True,
        "selected_exam": {"id": exam["id"], "slug": exam.get("slug"), "name": exam.get("name")},
        "plan": plan_outcome,
    }


@router.get("/tracked-exams")
async def list_tracked_exams(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Return the user's tracked exams with the current primary flagged.

    The tracked list is the slug list stored in
    ``aspirant_preferences.target_exams`` (most-recent-first). The primary
    is ``profiles.target_exam`` (UUID). Each item also reports
    ``planner_ready`` so the frontend can disable switch-to-primary when
    the exam has no locked topic coverage yet.
    """
    user_id = user.get("id")
    supabase = get_supabase_admin()

    pref_rows = (
        supabase.table("aspirant_preferences")
        .select("target_exams")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    tracked_slugs: list[str] = list((pref_rows[0].get("target_exams") if pref_rows else []) or [])

    profile_rows = (
        supabase.table("profiles")
        .select("target_exam")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    primary_exam_id = profile_rows[0].get("target_exam") if profile_rows else None

    # Always include the primary in the response, even if it is somehow
    # missing from the slug list (covers data drift from older flows).
    exam_lookup: dict[str, dict[str, Any]] = {}
    if tracked_slugs:
        rows = (
            supabase.table("exams")
            .select("id,slug,name,is_active")
            .in_("slug", tracked_slugs)
            .execute()
            .data
            or []
        )
        for r in rows:
            slug = r.get("slug")
            if slug:
                exam_lookup[slug] = r

    primary_exam: dict[str, Any] | None = None
    if primary_exam_id:
        row = (
            supabase.table("exams")
            .select("id,slug,name,is_active")
            .eq("id", primary_exam_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if row:
            primary_exam = row[0]
            if primary_exam.get("slug") and primary_exam["slug"] not in exam_lookup:
                exam_lookup[primary_exam["slug"]] = primary_exam

    ordered_slugs: list[str] = []
    if primary_exam and primary_exam.get("slug"):
        ordered_slugs.append(primary_exam["slug"])
    for slug in tracked_slugs:
        if slug not in ordered_slugs and slug in exam_lookup:
            ordered_slugs.append(slug)

    exam_ids = [exam_lookup[slug]["id"] for slug in ordered_slugs if exam_lookup.get(slug)]
    locked_exam_ids: set[str] = set()
    if exam_ids:
        cov_rows = (
            supabase.table("exam_topic_coverage")
            .select("exam_id")
            .in_("exam_id", exam_ids)
            .eq("reviewer_status", "locked")
            .limit(len(exam_ids) * 500)
            .execute()
            .data
            or []
        )
        locked_exam_ids = {str(r["exam_id"]) for r in cov_rows if r.get("exam_id")}

    items: list[dict[str, Any]] = []
    for slug in ordered_slugs:
        exam = exam_lookup.get(slug)
        if not exam:
            continue
        items.append(
            {
                "id": exam.get("id"),
                "slug": exam.get("slug"),
                "name": exam.get("name"),
                "is_active": bool(exam.get("is_active")),
                "planner_ready": bool(exam.get("is_active")) and str(exam.get("id")) in locked_exam_ids,
                "is_primary": primary_exam_id is not None
                and str(exam.get("id")) == str(primary_exam_id),
            }
        )

    return {"items": items, "primary_exam_id": primary_exam_id}


@router.delete("/tracked-exams/{exam_id}")
async def remove_tracked_exam(
    exam_id: UUID,
    confirm: bool = False,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Drop one exam from the user's tracked list.

    The primary exam can only be removed when ``confirm=true`` is passed,
    because dropping it also clears ``profiles.target_exam`` and the
    StudyPlan page will fall back to the "pick an exam" empty state. The
    associated study plan is left in place (use ``PUT /target-exam`` to
    switch the primary, which already archives the old plan).
    """
    user_id = user.get("id")
    supabase = get_supabase_admin()

    exam_rows = (
        supabase.table("exams")
        .select("id,slug")
        .eq("id", str(exam_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not exam_rows:
        raise HTTPException(status_code=404, detail="exam_not_found")
    exam_slug = exam_rows[0].get("slug")

    profile_rows = (
        supabase.table("profiles")
        .select("target_exam")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    primary_exam_id = profile_rows[0].get("target_exam") if profile_rows else None
    removing_primary = primary_exam_id is not None and str(primary_exam_id) == str(exam_id)

    if removing_primary and not confirm:
        raise HTTPException(
            status_code=409,
            detail={"code": "PRIMARY_EXAM_REMOVAL_REQUIRES_CONFIRM", "requires_confirmation": True},
        )

    pref_rows = (
        supabase.table("aspirant_preferences")
        .select("target_exams")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    cur = list((pref_rows[0].get("target_exams") if pref_rows else []) or [])
    next_exams = [s for s in cur if s != exam_slug]
    supabase.table("aspirant_preferences").upsert(
        {"user_id": user_id, "target_exams": next_exams}, on_conflict="user_id"
    ).execute()

    if removing_primary:
        supabase.table("profiles").update({"target_exam": None}).eq("id", user_id).execute()

    return {"ok": True, "removed_exam_id": str(exam_id), "primary_cleared": removing_primary}


@router.get("/regulatory-overlap")
async def get_regulatory_overlap(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Read-only shared-core overlap across the user's active regulatory target
    exams (Lane R R2, increment 1): shared foundation vs per-exam delta, the
    already-mastered shared topics to reuse, and the 70/20/10 allocation targets.

    Reuses no new surface — a read the Compass / combined planner consume. Returns
    an empty (but well-shaped) summary when the user has fewer than two regulatory
    target exams, or on any read failure.
    """
    from app.study_os.shared_core import summarize_regulatory_overlap

    supabase = get_supabase_admin()
    return summarize_regulatory_overlap(supabase, user.get("id"))


@router.get("/mission-control")
async def mission_control(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    user_id = user.get("id")
    supabase = get_supabase_admin()
    try:
        # Async path: independent sub-loaders run via asyncio.gather +
        # to_thread so the sync supabase client's blocking calls overlap.
        return await build_mission_control_async(supabase, user_id)
    except Exception as exc:  # noqa: BLE001
        # Mission control composes many optional sources. Any unhandled
        # error must not break the Today page — return a minimal shape
        # the UI can still render.
        logger.exception("mission_control build failed for %s", user_id)
        from datetime import datetime, timezone

        return {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "user_context": {
                "persona_snapshot_id": None,
                "persona_version": "v1",
                "dimensions": {},
                "scores": {},
                "safe_user_explanation": [],
            },
            "study_policy": {},
            "plan": None,
            "exam_context": {
                "exam_id": None,
                "exam_family": None,
                "exam": None,
                "cycle": None,
                "phase": None,
                "days_remaining": None,
                "verified_intelligence_status": "none",
                "high_yield_topics": [],
            },
            "competition_context": {
                "available": False,
                "exam_id": None,
                "exam_cycle_id": None,
                "exam_phase_id": None,
                "vacancy_total": None,
                "vacancy_by_category": {},
                "applicant_count": None,
                "selection_ratio": None,
                "cutoff_trend": {},
                "difficulty_trend": {},
                "competition_pressure_score": None,
                "cycle_pressure": {
                    "days_remaining": None,
                    "pressure_level": "unknown",
                    "reason": None,
                },
                "trust": {
                    "source_basis": None,
                    "reviewer_status": None,
                    "confidence_score": None,
                    "evidence_count": 0,
                },
            },
            "policy_update_context": {
                "official_updates": [],
                "needs_verification": [],
                "affects_plan": False,
                "affects_deadline": False,
                "affects_eligibility": False,
                "affects_documents": False,
                "affects_syllabus": False,
                "affects_vacancy": False,
            },
            "update_context": {
                "official_updates": [],
                "needs_verification": [],
                "affects_plan": False,
                "affects_deadline": False,
                "affects_eligibility": False,
                "affects_documents": False,
                "affects_syllabus": False,
                "affects_vacancy": False,
            },
            "today_tasks": [],
            "plan_reasoning": [],
            "regen_triggers": [],
            "nudges": [],
            "metrics": {
                "tasks_total": 0,
                "tasks_completed": 0,
                "task_completion_rate": 0.0,
                "hours_studied_7d": 0.0,
                "hours_planned_week": 0.0,
                "adherence": None,
                "backlog_count": 0,
                "mocks_taken": 0,
                "revision_coverage": None,
            },
            "next_best_action": {
                "title": "Open your study plan",
                "description": "Check what's scheduled and adjust if needed.",
                "action_type": "study_plan",
                "task_id": None,
                "reason": "Mission control is temporarily unavailable.",
            },
            "truth_panel": {
                "summary": "Mission control is temporarily unavailable.",
                "corrections": [],
                "warnings": [],
            },
            "progressive_question": None,
            "eligibility_summary": {
                "eligible": [],
                "conditional": [],
                "not_eligible": [],
                "unknown": [],
                "rule_count": 0,
            },
            "engine_trace": [
                {"label": "User signals", "status": "missing", "details": "Persona snapshot not available"},
                {"label": "Study policy", "status": "missing", "details": "No study policy derived yet"},
                {"label": "Study plan", "status": "missing", "details": "No active study plan yet"},
                {"label": "Exam intelligence", "status": "not_connected", "details": "Admin-reviewed exam intelligence is not connected yet"},
            ],
            "meta": {
                "source": "mission_control_v1",
                "preview_flags": ["mission_control_degraded", "exam_intelligence_not_connected"],
                "degraded": True,
                "diagnostics": {
                    "error_class": type(exc).__name__,
                    "error_message": str(exc)[:200],
                },
                "error": str(exc)[:200],
            },
        }


class PlanPreferencesBody(BaseModel):
    focus: str | None = Field(
        default=None, pattern="^(balanced|weak_areas|exam_priority|high_yield)$"
    )
    max_tasks_per_day: int | None = Field(default=None, ge=1, le=8)
    preferred_task_size: str | None = Field(
        default=None, pattern="^(small|medium|large)$"
    )
    pinned_topic_ids: list[str] | None = None
    muted_topic_ids: list[str] | None = None
    auto_regenerate: bool | None = None


@router.get("/plan/preferences")
async def get_plan_prefs(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Return the user's Study OS plan preferences (defaults if none saved)."""
    return get_plan_preferences(get_supabase_admin(), user.get("id"))


@router.put("/plan/preferences")
async def put_plan_prefs(
    body: PlanPreferencesBody, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    """Update the user's plan preferences — the weighting focus, plan-shape
    overrides and pinned / muted topics that steer the deterministic planner.

    Only the fields present in the request body are changed. Saving does not
    itself regenerate the plan — call ``POST /plan/generate`` for that.
    """
    fields = body.model_dump(exclude_unset=True)
    return upsert_plan_preferences(get_supabase_admin(), user.get("id"), **fields)


@router.post("/plan/generate")
async def generate_study_plan(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Phase 7 — deterministic plan generation.

    Composes today's ``study_tasks`` from locked exam intelligence, verified
    PYQ frequency, the user's topic mastery, competition pressure and the
    persona study policy. Persists the plan, an audit version row and an
    adaptation event. Returns ``generated=False`` with a ``reason`` when the
    plan cannot be built (no target exam, or no locked coverage yet).
    """
    user_id = user.get("id")
    supabase = get_supabase_admin()
    gate, exam_id = _calibration_gate_response(supabase, user_id)
    if gate is not None:
        return gate
    try:
        result = generate_plan(supabase, user_id, expected_exam_id=exam_id)
    except Exception:  # noqa: BLE001
        logger.exception("plan generation failed for %s", user_id)
        raise HTTPException(
            status_code=500, detail="Plan generation is temporarily unavailable."
        )
    return _raise_for_plan_failure(result)


# ───────────────────────── Plan draft / apply / changelog ──────────────────
@router.get("/plan/draft")
async def get_plan_draft(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Preview today's deterministic plan without touching the active plan."""
    supabase = get_supabase_admin()
    user_id = user.get("id")
    _require_canonical_target(supabase, user_id)
    gate, exam_id = _calibration_gate_response(supabase, user_id)
    if gate is not None:
        return gate
    out = compute_draft_plan(supabase, user_id, expected_exam_id=exam_id)
    try:
        from app.study_os.planner import _resolve_target_exam
        ex = _resolve_target_exam(supabase, user_id)
        if ex:
            cov = supabase.table("exam_topic_coverage").select("id", count="exact").eq("exam_id", ex["id"]).eq("reviewer_status", "locked").limit(1).execute()
            out["selected_exam"] = {"id": ex.get("id"), "slug": ex.get("slug"), "name": ex.get("name"), "planner_ready": int(getattr(cov, "count", 0) or 0) > 0}
    except Exception:
        pass
    return out


@router.post("/plan/draft")
async def post_plan_draft(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Same payload as GET /plan/draft — write-style verb for explicit refresh."""
    supabase = get_supabase_admin()
    user_id = user.get("id")
    _require_canonical_target(supabase, user_id)
    gate, exam_id = _calibration_gate_response(supabase, user_id)
    if gate is not None:
        return gate
    return compute_draft_plan(supabase, user_id, expected_exam_id=exam_id)


def _apply_plan_envelope(supabase: Any, user_id: str) -> dict[str, Any]:
    """Run the ``/plan/apply`` preconditions and the planner, returning the envelope.

    Extracted so the exam-switch regeneration (D5) reuses this exact path rather
    than duplicating the preconditions or issuing an internal HTTP call. Returns
    the planner's in-band envelope untouched — including the calibration gate's
    ``calibration_required`` payload, which is a legitimate outcome and not a
    failure. Translating an envelope to HTTP stays the route's job.

    Still raises ``HTTPException`` for the two precondition faults the route
    already surfaced: a missing canonical target (400) and an undeterminable
    calibration gate (503). Callers that must not fail on those catch them.
    """
    _require_canonical_target(supabase, user_id)
    gate, exam_id = _calibration_gate_response(supabase, user_id)
    if gate is not None:
        return gate
    return apply_plan(supabase, user_id, expected_exam_id=exam_id)


@router.post("/plan/apply")
async def post_plan_apply(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Apply the deterministic plan candidate to the active plan."""
    user_id = user.get("id")
    supabase = get_supabase_admin()
    try:
        result = _apply_plan_envelope(supabase, user_id)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("plan apply failed for %s", user_id)
        raise HTTPException(status_code=500, detail="Plan apply is temporarily unavailable.")
    if result.get("calibration_required"):
        # The gate short-circuits with HTTP 200 and its own envelope — unchanged
        # from before the extraction. ``calibration_required`` is deliberately
        # NOT in _PLAN_UNPROCESSABLE_REASONS, so routing it through
        # _raise_for_plan_failure would turn a 200 interstitial into a 500.
        return result
    return _raise_for_plan_failure(result)


@router.get("/plan/timeline")
async def plan_timeline(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Exam-cycle timeline payload for the Study Plan page.

    Composes exam_context + plan_context + cycle_progress + milestones +
    phase_bands + weekly planned-vs-actual series + per-subject progress
    + deterministic risk flags. Safe fallback (status='not_connected') is
    returned whenever required data is missing — the UI must not assume
    every field is populated.
    """
    try:
        return plan_timeline_service.get_plan_timeline(
            get_supabase_admin(), user.get("id")
        )
    except Exception:  # noqa: BLE001
        logger.exception("plan_timeline build failed for %s", user.get("id"))
        return plan_timeline_service._empty_payload()  # type: ignore[attr-defined]


@router.get("/plan/by-subject")
async def plan_by_subject(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Per-subject allocation for the user's planning week.

    Aggregates study_tasks scheduled this Monday → Sunday, groups them by
    subject, and tags each bucket with a trust_status reflecting whether
    the subject has locked coverage in the target exam.
    """
    try:
        return plan_by_subject_service.list_plan_by_subject(
            get_supabase_admin(), user.get("id")
        )
    except Exception:  # noqa: BLE001
        logger.exception("plan_by_subject read failed for %s", user.get("id"))
        return {
            "week_start": None,
            "week_end": None,
            "items": [],
            "total_minutes": 0,
            "total_hours": 0,
            "trust_status": "preview",
        }


@router.get("/plan/changelog")
async def get_plan_changelog(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Recent study_adaptation_events for the user's active plan."""
    user_id = user.get("id")
    supabase = get_supabase_admin()
    try:
        rows = (
            supabase.table("study_adaptation_events")
            .select(
                "id, plan_id, plan_version_id, event_type, trigger_source, "
                "trigger_payload, change_summary, created_at"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
            .data
            or []
        )
        return {"items": rows, "count": len(rows)}
    except Exception:  # noqa: BLE001
        logger.exception("plan changelog read failed for %s", user_id)
        return {"items": [], "count": 0}




def _improvement_lab_feed(user_id: str | None, subject_family: str) -> dict[str, Any]:
    """Owner-scoped, bounded, verified-only strategy feed for one subject (GQR-S6).

    A genuinely empty history is a normal ``{"items": []}`` (200). A feed READ
    FAILURE surfaces as HTTP 502 so the client renders its error state rather than
    a misleading "no history" — the builder does NOT swallow its own read errors
    (checkpost #999 F1)."""
    try:
        return {"items": _build_improvement_lab_feed(get_supabase_admin(), user_id, subject_family)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("improvement_lab feed read failed subject=%s", subject_family)
        raise HTTPException(status_code=502, detail="improvement lab feed unavailable") from exc


@router.get("/improvement-lab/quant")
async def improvement_lab_quant(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Methods & Shortcuts — personalized, verified-only Quant strategy feed (GQR-S6)."""
    return _improvement_lab_feed(user.get("id"), "quant")


@router.get("/improvement-lab/reasoning")
async def improvement_lab_reasoning(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Approaches & Patterns — personalized, verified-only Reasoning strategy feed (GQR-S6)."""
    return _improvement_lab_feed(user.get("id"), "reasoning")


@router.get("/reports/mock-trend")
async def reports_mock_trend(days: int = 90, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    sb = get_supabase_admin(); user_id = user.get("id")
    rows = (sb.table("mock_attempts")
              .select("id, submitted_at, score_percentage, total_correct, total_wrong")
              .eq("user_id", user_id)
              .eq("status", "submitted")
              .order("submitted_at", desc=False)
              .limit(100)
              .execute()
              .data or [])
    items = []
    for r in rows:
        total_ans = (r.get("total_correct") or 0) + (r.get("total_wrong") or 0)
        accuracy = round((r.get("total_correct") or 0) / total_ans * 100, 2) if total_ans > 0 else 0.0
        items.append({
            "attempt_id": r.get("id"),
            "submitted_at": r.get("submitted_at"),
            "score_pct": float(r.get("score_percentage") or 0),
            "accuracy_pct": accuracy,
            "time_used_sec": 0,
        })
    return {"items": items}

@router.get("/reports/mistakes")
async def reports_mistakes(days: int = 90, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    sb = get_supabase_admin(); user_id = user.get("id")
    from datetime import datetime, timezone, timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = (
        sb.table("user_topic_error_patterns")
        .select("error_type, topic_id, question_id, frequency_count")
        .eq("user_id", user_id)
        .gte("last_seen_at", since)
        .limit(5000)
        .execute()
        .data
        or []
    )
    agg: dict[str, Any] = {}
    for r in rows:
        e = r.get("error_type") or "unknown"
        a = agg.setdefault(e, {"error_type": e, "count": 0, "topics": {}, "recent_question_ids": []})
        freq = int(r.get("frequency_count") or 1)
        a["count"] += freq
        t = r.get("topic_id")
        if t:
            a["topics"][t] = a["topics"].get(t, 0) + freq
        q = r.get("question_id")
        if q and q not in a["recent_question_ids"]:
            a["recent_question_ids"].append(q)
    items = []
    for v in agg.values():
        items.append({
            "error_type": v["error_type"],
            "count": v["count"],
            "topics": [{"topic_id": k, "count": c} for k, c in v["topics"].items()],
            "recent_question_ids": v["recent_question_ids"][:10],
        })
    return {"items": items}

# ─── Plan-change timeline (PR6 page set: /app/study/plan) ────────────────────
# Maps the raw planner audit + (PR5-live) mastery audit into the canonical
# event shape the PlanImpactTimeline UI consumes. `kind` is one of
# topic_added | priority_shift | topic_removed | phase_change.
_PLAN_KIND_BY_EVENT = {
    "manual_regeneration": "priority_shift",
    "weekly_review": "priority_shift",
    "revision_overdue": "priority_shift",
    "task_missed": "priority_shift",
    "task_completed": "priority_shift",
    "focus_session_completed": "priority_shift",
    "mock_logged": "priority_shift",
    "deadline_changed": "phase_change",
    "exam_update": "phase_change",
}

_PLAN_REASON_HUMAN = {
    "manual_regeneration": "Plan regenerated",
    "weekly_review": "Weekly review adjustment",
    "revision_overdue": "Revision overdue — topics reprioritized",
    "task_missed": "Task missed — plan adjusted",
    "task_completed": "Task completed",
    "focus_session_completed": "Focus session logged",
    "mock_logged": "Mock logged — plan adjusted",
    "deadline_changed": "Exam deadline changed",
    "exam_update": "Exam details updated",
}


def _derive_plan_kind(event_type: str | None, change_summary: dict | None) -> str:
    cs = change_summary or {}
    if cs.get("removed") or cs.get("removed_topics"):
        return "topic_removed"
    if cs.get("added") or cs.get("added_topics"):
        return "topic_added"
    return _PLAN_KIND_BY_EVENT.get(event_type or "", "priority_shift")


def _derive_plan_trigger(row: dict) -> dict[str, Any]:
    payload = row.get("trigger_payload") or {}
    event_type = row.get("event_type")
    source = row.get("trigger_source")
    attempt_id = payload.get("attempt_id") or payload.get("mock_attempt_id")
    if source == "admin":
        return {"type": "manual", "actor_id": payload.get("actor_id")}
    if attempt_id or event_type == "mock_logged":
        return {"type": "mock_attempt", "attempt_id": attempt_id}
    if event_type == "manual_regeneration":
        return {"type": "manual", "actor_id": payload.get("actor_id")}
    return {"type": "scheduled"}


def _plan_timeline_events(
    sb: Any, user_id: str, cutoff: str, mastery_flag: str
) -> list[dict[str, Any]]:
    adaptation = (
        sb.table("study_adaptation_events")
        .select("id, created_at, event_type, trigger_source, trigger_payload, change_summary")
        .eq("user_id", user_id)
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
        .limit(200)
        .execute()
        .data
        or []
    )
    events: list[dict[str, Any]] = []
    for r in adaptation:
        event_type = r.get("event_type")
        events.append(
            {
                "id": r.get("id"),
                "at": r.get("created_at"),
                "kind": _derive_plan_kind(event_type, r.get("change_summary")),
                "reason_code": event_type,
                "reason_human": _PLAN_REASON_HUMAN.get(event_type or "", "Plan updated"),
                "trigger": _derive_plan_trigger(r),
                "mastery_delta_db": None,
            }
        )

    # Mastery-driven plan changes are only honest when PR5 actually wrote them.
    # In off/shadow the audit table holds no live rows for this user, but we
    # still gate on the flag so a stale shadow row can never leak a delta.
    if mastery_flag == "live":
        audit = (
            sb.table("user_topic_mastery_audit")
            .select("id, topic_id, attempt_id, before_mastery_db, after_mastery_db, delta_applied_db, at")
            .eq("user_id", user_id)
            .gte("at", cutoff)
            .order("at", desc=True)
            .limit(200)
            .execute()
            .data
            or []
        )
        for r in audit:
            before = r.get("before_mastery_db")
            after = r.get("after_mastery_db")
            delta = r.get("delta_applied_db")
            if delta is None and before is not None and after is not None:
                delta = float(after) - float(before)
            events.append(
                {
                    "id": f"mastery:{r.get('id')}",
                    "at": r.get("at"),
                    "kind": "priority_shift",
                    "reason_code": "mastery_shift",
                    "reason_human": "Mastery updated from a mock attempt",
                    "trigger": {"type": "mock_attempt", "attempt_id": r.get("attempt_id")},
                    "mastery_delta_db": {
                        "topic_id": r.get("topic_id"),
                        "before": before,
                        "after": after,
                        "delta": delta,
                    },
                }
            )

    events.sort(key=lambda e: e.get("at") or "", reverse=True)
    return events[:200]


@router.get("/reports/plan-timeline")
async def reports_plan_timeline(days: int = 90, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Plan-change events for the /app/study/plan timeline.

    Unions rule-based planner audit (``study_adaptation_events``) with
    mastery-shift events (``user_topic_mastery_audit``). ``mastery_delta_db``
    is populated only when the PR5 write-back flag is ``live`` — it is null on
    every event otherwise so the UI can suppress delta indicators uniformly.
    """
    sb = get_supabase_admin()
    user_id = user.get("id")
    if not user_id:
        return {"events": []}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, days))).isoformat()
    events = _plan_timeline_events(sb, user_id, cutoff, get_mastery_write_flag())
    return {"events": events}

@router.get("/reports/topic-recovery")
async def reports_topic_recovery(days: int = 90, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    sb = get_supabase_admin(); user_id = user.get("id")
    rows = (sb.table("user_topic_mastery_audit").select("topic_id, topic_name, created_at, mastery_db").eq("user_id", user_id).order("created_at", desc=False).limit(5000).execute().data or [])
    by = {}
    for r in rows:
        t = r.get("topic_id")
        o = by.setdefault(t,{"topic_id":t,"name":r.get("topic_name"),"mastery_history":[]})
        o["mastery_history"].append({"at":r.get("created_at"),"mastery_db":r.get("mastery_db")})
    return {"items": list(by.values())}

@router.get("/reports/subject-mastery")
async def reports_subject_mastery(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    sb = get_supabase_admin(); user_id = user.get("id")
    rows = (sb.table("subject_mastery_snapshots").select("subject_id, subject_name, topic_id, topic_name, mastery, mastery_delta, attempt_volume").eq("user_id", user_id).order("attempt_volume", desc=True).limit(100).execute().data or [])
    return {"items": rows}

# ─────────────────────────── Syllabus roadmap ───────────────────────────────
@router.get("/progress/roadmap")
async def progress_roadmap(
    exam_id: UUID,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """ROADMAP-01 — the user's syllabus roadmap for one exam (read-only).

    Subject → macro topic → microtopic over the user's scoped locked coverage,
    each node carrying a state derived at read time (``study_os.roadmap``).
    409 when the exam is not planner-ready by the exam drawer's rule; 503 when
    any read behind the tree fails, so a partial tree never renders as complete.
    """
    user_id = user.get("id")
    supabase = get_supabase_admin()
    exam_key = str(exam_id)

    exam_rows = _safe(
        lambda: (
            supabase.table("exams")
            .select("id,is_active")
            .eq("id", exam_key)
            .limit(1)
            .execute()
            .data
        ),
        default=None,
    )
    if exam_rows is None:
        raise HTTPException(status_code=503, detail={"reason": "roadmap_read_failed"})
    counts = _locked_coverage_counts(supabase, [exam_key])
    if counts is None:
        raise HTTPException(status_code=503, detail={"reason": "roadmap_read_failed"})
    if not exam_rows or not _is_planner_ready(exam_rows[0], counts):
        raise HTTPException(status_code=409, detail={"reason": "not_planner_ready"})

    try:
        return roadmap_service.build_roadmap(supabase, user_id, exam_key)
    except roadmap_service.RoadmapReadError:
        logger.exception("roadmap read failed for %s / %s", user_id, exam_key)
        raise HTTPException(status_code=503, detail={"reason": "roadmap_read_failed"})


# ───────────────────────────── Subjects ─────────────────────────────────────
@router.get("/subjects")
async def list_subjects(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Per-subject progress for the user's target exam (verified topics only)."""
    try:
        items = subjects_service.list_subjects(get_supabase_admin(), user.get("id"))
        return {"items": items, "count": len(items)}
    except Exception:  # noqa: BLE001
        logger.exception("subjects read failed for %s", user.get("id"))
        return {"items": [], "count": 0}


# ─────────────────────── Subject topic/microtopic tree ──────────────────────
@router.get("/subjects/{subject_id}/topics")
async def subject_topic_tree(
    subject_id: str,
    exam_id: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Nested topic → microtopic tree for one subject, with locked-coverage
    priority attached where it exists.

    Step 1 of 2 for the Topic Study Hub: the read model behind a
    topic/microtopic breakdown under a subject. Structure comes from the
    ``topics`` table (so not-yet-scored topics still appear); locked
    ``exam_topic_coverage`` supplies priority; 0-evidence rollup nodes are
    flagged (PR #1030 guard). Read-only; no user mastery.
    """
    try:
        tree = subjects_service.subject_topic_tree(
            get_supabase_admin(), user.get("id"), subject_id, exam_id=exam_id
        )
    except Exception:  # noqa: BLE001
        logger.exception("subject topic tree read failed for %s / %s", user.get("id"), subject_id)
        raise HTTPException(status_code=500, detail="Topic tree is temporarily unavailable.")
    if tree is None:
        raise HTTPException(status_code=404, detail="Subject not found.")
    return tree


# ───────────────────────────── Topics tree ──────────────────────────────────
@router.get("/topics")
async def get_topics(
    exam_id: str | None = None,
    subject_id: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Locked-only topic intelligence — drives the Subjects topic tree."""
    user_id = user.get("id")
    supabase = get_supabase_admin()
    try:
        from app.exam_intelligence.coverage import verified_pyq_topic_counts
        from app.exam_intelligence.lookup import (
            InactiveExamError,
            resolve_exam_by_id,
            resolve_exam_by_slug,
        )
        from app.study_os.planner import (
            load_scoped_coverage,
            _load_user_signals,
            _resolve_target_exam,
        )

        try:
            if not exam_id:
                target = _resolve_target_exam(supabase, user_id)
                exam_id = target.get("id") if target else None
            else:
                target = resolve_exam_by_id(supabase, exam_id) or resolve_exam_by_slug(
                    supabase, exam_id
                )
                if target:
                    exam_id = target.get("id")
        except InactiveExamError:
            # Retired/sandbox exam — whether it came from the user's target or
            # an explicit ?exam_id=. Fall through to the same empty tree this
            # route already returns when there is no exam to read.
            logger.info(
                "topics: refusing inactive exam for user=%s exam_id=%s", user_id, exam_id
            )
            exam_id = None

        if not exam_id:
            return {
                "items": [],
                "exam_id": None,
                "subject_id": subject_id,
                "trust_status": "locked",
            }

        coverage = load_scoped_coverage(supabase, user_id, exam_id)
        if subject_id:
            coverage = [c for c in coverage if c.get("subject_id") == subject_id]

        pyq_counts = verified_pyq_topic_counts(supabase, exam_id) or {}
        mastery, error_topics = _load_user_signals(supabase, user_id, exam_id)

        def _next_action(mast, has_err):
            if mast is None:
                return "concept_learning"
            if mast < 45:
                return "concept_learning"
            if mast < 75 or has_err:
                return "retrieval_practice"
            return "revision"

        items: list[dict[str, Any]] = []
        for c in coverage:
            tid = c["topic_id"]
            mast = mastery.get(tid)
            has_err = tid in error_topics
            items.append(
                {
                    "subject_id": c.get("subject_id"),
                    "subject": c.get("subject_name"),
                    "topic_id": tid,
                    "topic": c.get("topic_name"),
                    # Hierarchy passes through from ``_load_locked_coverage``
                    # which now selects ``parent_topic_id`` + ``level``.
                    # Null is legitimate for root topics; null on a non-root
                    # row would indicate a DB inconsistency, not a bug here.
                    "parent_topic_id": c.get("parent_topic_id"),
                    "topic_level": c.get("topic_level"),
                    "mastery_score": mast,
                    "exam_priority_score": c.get("coverage_priority"),
                    "is_high_yield": bool(c.get("is_high_yield")),
                    "verified_pyq_count": int(pyq_counts.get(tid, 0)),
                    "revision_due": mast is not None and mast >= 75,
                    "error_pattern_count": 1 if has_err else 0,
                    "next_action": _next_action(mast, has_err),
                    "evidence_count": int(pyq_counts.get(tid, 0)),
                    "trust_status": "locked",
                }
            )
        return {
            "items": items,
            "exam_id": exam_id,
            "subject_id": subject_id,
            "trust_status": "locked",
        }
    except Exception:  # noqa: BLE001
        logger.exception("topics read failed for %s", user_id)
        return {
            "items": [],
            "exam_id": exam_id,
            "subject_id": subject_id,
            "trust_status": "locked",
        }


# ─────────────────────────── Weekly review ──────────────────────────────────
@router.get("/weekly-review")
async def weekly_review_read(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the persisted weekly-review snapshot, computing one if absent."""
    try:
        return weekly_review_service.get_weekly_review(
            get_supabase_admin(), user.get("id")
        )
    except Exception:  # noqa: BLE001
        logger.exception("weekly_review read failed for %s", user.get("id"))
        raise HTTPException(
            status_code=500, detail="Weekly review is temporarily unavailable."
        )


@router.post("/weekly-review/compute")
async def weekly_review_compute(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Force-recompute and persist this week's review snapshot."""
    try:
        return weekly_review_service.compute_weekly_review(
            get_supabase_admin(), user.get("id")
        )
    except Exception:  # noqa: BLE001
        logger.exception("weekly_review compute failed for %s", user.get("id"))
        raise HTTPException(
            status_code=500, detail="Could not recompute weekly review."
        )



@router.get("/report-card")
async def report_card_read(
    period: str = "weekly",
    date: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    from datetime import datetime, timezone

    anchor = datetime.now(timezone.utc).date() if not date else datetime.fromisoformat(date).date()
    try:
        return report_cards_service.get_report_card(get_supabase_admin(), user.get("id"), period, anchor)
    except Exception:
        logger.exception("report_card read failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="Report card is temporarily unavailable.")


@router.post("/report-card/compute")
async def report_card_compute(
    period: str = "weekly",
    date: str | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    from datetime import datetime, timezone

    anchor = datetime.now(timezone.utc).date() if not date else datetime.fromisoformat(date).date()
    try:
        return report_cards_service.compute_report_card(get_supabase_admin(), user.get("id"), period, anchor)
    except Exception:
        logger.exception("report_card compute failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="Could not recompute report card.")


@router.get("/report-card/history")
async def report_card_history(
    period: str = "weekly",
    limit: int = 12,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return {"items": report_cards_service.history(get_supabase_admin(), user.get("id"), period, limit)}
    except Exception:
        logger.exception("report_card history failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="Report card history is temporarily unavailable.")


# ─────────────────────────── Self-assessment ─────────────────────────────────
#
# Band→prior_mastery, attempts→confidence, the required-subject resolver and the
# set-hash live in ``app.study_os.calibration`` (single source of truth shared
# with the planner + scheduled regeneration). Module-level aliases below keep
# the historical import surface (``from app.api.study_os import ...``) intact.
_BAND_TO_PRIOR_MASTERY = calibration.BAND_TO_PRIOR_MASTERY
_report_confidence_from_attempts = calibration.report_confidence_from_attempts
_required_subject_set_hash = calibration.required_subject_set_hash


def _existing_evidence_subject_ids(supabase, user_id, exam_id) -> set[str]:
    rows = (
        supabase.table("user_topic_self_assessment")
        .select("subject_id")
        .eq("user_id", user_id)
        .eq("exam_id", exam_id)
        .limit(5000)
        .execute()
        .data
        or []
    )
    return {str(r["subject_id"]) for r in rows if r.get("subject_id")}


class BandItem(BaseModel):
    subject_id: UUID
    band: str = Field(pattern="^(strong|decent|weak|new)$")


class SelfAssessmentBody(BaseModel):
    bands: list[BandItem]
    attempts_used: int = Field(ge=0)


class SkipBody(BaseModel):
    attempts_used: int | None = Field(default=None, ge=0)


@router.get("/self-assessment")
async def get_self_assessment(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Return the user's calibration state + self-assessment bands for prefill."""
    user_id = user.get("id")
    supabase = get_supabase_admin()

    exam, exam_ok = calibration.resolve_target_exam_checked(supabase, user_id)
    if not exam_ok:
        # Target resolution failed — fail closed. Do NOT mistake a transient
        # profile/preference read for "no target exam" and report a bogus state.
        return {
            "exam_id": None,
            "calibrated": False,
            "calibration_check_failed": True,
            "status": "unknown",
            "needs_update": False,
            "required_subjects": [],
            "items": [],
            "attempts_used": None,
        }
    if not exam or not exam.get("id"):
        return {
            "exam_id": None,
            "calibrated": False,
            "status": "none",
            "needs_update": False,
            "required_subjects": [],
            "items": [],
            "attempts_used": None,
        }
    exam_id = str(exam["id"])

    ev = calibration.evaluate_calibration(supabase, user_id, exam_id)
    if ev["check_failed"]:
        # Fail closed: a read needed to decide calibration failed, so the state
        # is UNKNOWN. Do NOT report the user as calibrated (that would be a
        # bypass) — return a stable, retryable signal the UI can surface.
        return {
            "exam_id": exam_id,
            "calibrated": False,
            "calibration_check_failed": True,
            "status": "unknown",
            "needs_update": False,
            "required_subjects": [],
            "items": [],
            "attempts_used": None,
        }
    required_subjects = ev["required_subjects"]
    calibrated = not ev["required"]
    # Trust the evaluator's authoritative status: it already distinguishes an
    # empty required set ("completed") from a grandfathered/no-gate user (None →
    # "none"). Do NOT re-derive from required_subjects — a best-effort subjects
    # outage leaves required_subjects=[] for a grandfathered user, which would
    # otherwise be mislabelled "completed".
    status = ev["status"] or "none"
    needs_update = ev["needs_update"]
    attempts_used = ev["attempts_used"]  # from the gate row — no second read

    # Best-effort prefill: the evidence/subject-name reads are cosmetic. A failure
    # here must NOT change `calibrated` or revoke access — fall back to empty
    # items and the gate's attempts_used.
    items: list[dict[str, Any]] = []
    try:
        rows = (
            supabase.table("user_topic_self_assessment")
            .select(
                "id, subject_id, topic_id, band, prior_mastery, report_confidence, "
                "attempts_used, assessed_at"
            )
            .eq("user_id", user_id)
            .eq("exam_id", exam_id)
            .limit(500)
            .execute()
            .data
            or []
        )
        subject_ids = list({r["subject_id"] for r in rows if r.get("subject_id")})
        subjects_by_id: dict[str, str] = {}
        if subject_ids:
            subj_rows = (
                supabase.table("subjects")
                .select("id, name")
                .in_("id", subject_ids)
                .limit(500)
                .execute()
                .data
                or []
            )
            subjects_by_id = {s["id"]: s.get("name") for s in subj_rows if s.get("id")}
        items = [
            {
                "id": r.get("id"),
                "subject_id": r.get("subject_id"),
                "subject_name": subjects_by_id.get(r["subject_id"]) if r.get("subject_id") else None,
                "topic_id": r.get("topic_id"),
                "band": r.get("band"),
                "prior_mastery": r.get("prior_mastery"),
                "report_confidence": r.get("report_confidence"),
                "attempts_used": r.get("attempts_used"),
                "assessed_at": r.get("assessed_at"),
            }
            for r in rows
        ]
        if attempts_used is None:
            evidence_attempts = [r.get("attempts_used") for r in rows if r.get("attempts_used") is not None]
            if evidence_attempts:
                attempts_used = max(evidence_attempts)
    except Exception:
        logger.exception("self-assessment prefill read failed for %s", user_id)
        items = []

    return {
        "exam_id": exam_id,
        "calibrated": calibrated,
        "status": status,
        "needs_update": needs_update,
        "required_subjects": required_subjects,
        "items": items,
        "attempts_used": attempts_used,
    }


@router.put("/self-assessment")
async def put_self_assessment(
    body: SelfAssessmentBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Upsert subject-level bands and, when the required set is complete, the gate."""
    user_id = user.get("id")
    supabase = get_supabase_admin()

    exam, exam_ok = calibration.resolve_target_exam_checked(supabase, user_id)
    if not exam_ok:
        raise HTTPException(status_code=503, detail={"reason": "calibration_check_failed"})
    if not exam or not exam.get("id"):
        raise HTTPException(status_code=422, detail="No target exam set.")
    exam_id = str(exam["id"])

    required_subjects, required_ok = calibration.resolve_required_subjects(supabase, exam_id, user_id)
    if not required_ok:
        # Fail closed: cannot validate the submission against an unknown required
        # set. Surface a retryable error rather than accept a possibly
        # out-of-scope or wrongly-completing write.
        raise HTTPException(status_code=503, detail={"reason": "calibration_check_failed"})
    required_ids = {s["subject_id"] for s in required_subjects}
    current_hash = calibration.required_subject_set_hash(list(required_ids))

    # ── Validation (raised BEFORE the upsert try/except so 422 is never
    #    swallowed and remapped to 500). ──────────────────────────────────────
    submitted_ids = [str(item.subject_id) for item in body.bands]
    if not submitted_ids:
        raise HTTPException(status_code=422, detail="No bands submitted.")
    if len(submitted_ids) != len(set(submitted_ids)):
        raise HTTPException(status_code=422, detail="Duplicate subject in submission.")
    for sid in submitted_ids:
        if sid not in required_ids:
            raise HTTPException(
                status_code=422,
                detail=f"Subject {sid} is not part of this exam's calibration set.",
            )

    report_confidence = calibration.report_confidence_from_attempts(body.attempts_used)
    now_iso = datetime.now(timezone.utc).isoformat()
    payloads = []
    for item in body.bands:
        subject_id = str(item.subject_id)
        band = item.band
        prior_mastery = calibration.BAND_TO_PRIOR_MASTERY[band]
        payloads.append({
            "user_id": user_id,
            "exam_id": exam_id,
            "subject_id": subject_id,
            "topic_id": None,
            "band": band,
            "prior_mastery": prior_mastery,
            "report_confidence": report_confidence,
            "attempts_used": body.attempts_used,
            "source": "onboarding_self_report",
            "assessed_at": now_iso,
            "updated_at": now_iso,
        })

    try:
        result = (
            supabase.table("user_topic_self_assessment")
            .upsert(payloads, on_conflict="user_id,exam_id,subject_id")
            .execute()
        )
        upserted_count = len(result.data) if result and result.data else len(payloads)
    except HTTPException:
        raise
    except Exception:
        logger.exception("self-assessment upsert failed for %s", user_id)
        raise HTTPException(status_code=500, detail="Could not save self-assessment.")

    # Normalize attempts/confidence across multi-call completion: the required
    # set may be answered over several PUTs, so evidence rows from earlier calls
    # would otherwise keep a stale ``attempts_used``/``report_confidence``. The
    # attempts answer is exam-level, so the LATEST submission wins uniformly —
    # rewrite every evidence row for this (user, exam) to the submitted values
    # (whether or not the set is complete).
    try:
        supabase.table("user_topic_self_assessment").update(
            {
                "attempts_used": body.attempts_used,
                "report_confidence": report_confidence,
                "updated_at": now_iso,
            }
        ).eq("user_id", user_id).eq("exam_id", exam_id).execute()
    except Exception:
        logger.exception("self-assessment normalize failed for %s", user_id)
        raise HTTPException(status_code=500, detail="Could not save self-assessment.")

    # Determine whether the FULL required set is now answered (existing evidence
    # ∪ this submission). Only then is the exam-level gate marked completed.
    answered_ids = _existing_evidence_subject_ids(supabase, user_id, exam_id) | set(submitted_ids)
    missing = sorted(required_ids - answered_ids)

    if not missing:
        try:
            supabase.table("user_exam_calibration").upsert(
                {
                    "user_id": user_id,
                    "exam_id": exam_id,
                    "status": "completed",
                    "required_subject_set_hash": current_hash,
                    "attempts_used": body.attempts_used,
                    "completed_at": now_iso,
                    "updated_at": now_iso,
                },
                on_conflict="user_id,exam_id",
            ).execute()
        except Exception:
            logger.exception("calibration gate upsert failed for %s", user_id)
            raise HTTPException(status_code=500, detail="Could not save calibration.")

    return {
        "ok": True,
        "upserted_count": upserted_count,
        "calibrated": not missing,
        "missing_subject_ids": missing,
    }


@router.post("/self-assessment/skip")
async def skip_self_assessment(
    body: SkipBody | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Explicitly skip onboarding calibration for the target exam."""
    user_id = user.get("id")
    supabase = get_supabase_admin()

    exam, exam_ok = calibration.resolve_target_exam_checked(supabase, user_id)
    if not exam_ok:
        raise HTTPException(status_code=503, detail={"reason": "calibration_check_failed"})
    if not exam or not exam.get("id"):
        raise HTTPException(status_code=422, detail="No target exam set.")
    exam_id = str(exam["id"])

    required_subjects, required_ok = calibration.resolve_required_subjects(supabase, exam_id, user_id)
    if not required_ok:
        raise HTTPException(status_code=503, detail={"reason": "calibration_check_failed"})
    current_hash = calibration.required_subject_set_hash([s["subject_id"] for s in required_subjects])
    attempts_used = body.attempts_used if body is not None else None
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        supabase.table("user_exam_calibration").upsert(
            {
                "user_id": user_id,
                "exam_id": exam_id,
                "status": "skipped",
                "required_subject_set_hash": current_hash,
                "attempts_used": attempts_used,
                "updated_at": now_iso,
            },
            on_conflict="user_id,exam_id",
        ).execute()
    except Exception:
        logger.exception("calibration skip upsert failed for %s", user_id)
        raise HTTPException(status_code=500, detail="Could not skip calibration.")

    return {"ok": True, "calibrated": True, "status": "skipped"}


# ─────────────────────────────── Mocks ──────────────────────────────────────
class MockSubjectBreakdownBody(BaseModel):
    subject: str
    total_questions: int | None = None
    correct_answers: int | None = None
    wrong_answers: int | None = None
    marks: float | None = None
    accuracy: float | None = None


class MockCreateBody(BaseModel):
    name: str
    exam_slug: str | None = None
    score: float | None = None
    max_score: float | None = None
    duration_min: int | None = None
    attempted: int | None = None
    correct: int | None = None
    weak_topics: list[str] = Field(default_factory=list)
    error_patterns: dict[str, int] = Field(default_factory=dict)
    subject_breakdown: list[MockSubjectBreakdownBody] = Field(default_factory=list)
    notes: str | None = None
    attempted_at: str | None = None


class MockReviewStateBody(BaseModel):
    state: str = Field(pattern="^(scheduled|unreviewed|reviewed|correction_drafted)$")


@router.get("/mocks")
async def list_mocks(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    items = mocks_service.list_mocks(get_supabase_admin(), user.get("id"))
    return {"items": items, "trend": mocks_service.mock_trend(items)}


@router.post("/mocks")
async def create_mock(
    body: MockCreateBody, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    payload = body.model_dump()
    # Nested Pydantic models → plain dicts for the service layer.
    payload["subject_breakdown"] = [
        b.model_dump() if hasattr(b, "model_dump") else dict(b)
        for b in (body.subject_breakdown or [])
    ]
    try:
        return mocks_service.create_mock(get_supabase_admin(), user.get("id"), payload)
    except RuntimeError:
        logger.exception("mock insert failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="Could not log mock.")


@router.get("/mocks/{mock_id}")
async def get_mock(
    mock_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    row = mocks_service.get_mock(get_supabase_admin(), user.get("id"), mock_id)
    if not row:
        raise HTTPException(status_code=404, detail="Mock not found.")
    return row


@router.get("/mocks/{mock_id}/analysis")
async def get_mock_analysis(
    mock_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    bundle = mocks_service.get_mock_analysis(get_supabase_admin(), user.get("id"), mock_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Mock not found.")
    return bundle


@router.patch("/mocks/{mock_id}/review-state")
async def set_review_state(
    mock_id: str,
    body: MockReviewStateBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return mocks_service.set_review_state(
            get_supabase_admin(), user.get("id"), mock_id, body.state
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Mock not found.")


@router.post("/mocks/{mock_id}/correction-tasks")
async def draft_correction_tasks(
    mock_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    try:
        items = mocks_service.draft_correction_tasks(
            get_supabase_admin(), user.get("id"), mock_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Mock not found.")
    except mocks_service.PlatformAttemptCorrectionForbiddenError:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "PLATFORM_ATTEMPT_MANUAL_CORRECTION_FORBIDDEN",
                "detail": (
                    "Manual correction tasks cannot be drafted for platform attempts. "
                    "MasteryWriter owns that pipeline."
                ),
            },
        )
    return {"items": items}


@router.post("/mocks/correction-tasks/{correction_id}/apply")
async def apply_correction_task(
    correction_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    try:
        return mocks_service.apply_correction_task(
            get_supabase_admin(), user.get("id"), correction_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Correction task not found.")
    except RuntimeError:
        logger.exception("apply correction failed for %s", correction_id)
        raise HTTPException(status_code=500, detail="Could not apply correction task.")


@router.post("/mocks/correction-tasks/{correction_id}/dismiss")
async def dismiss_correction_task(
    correction_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    try:
        return mocks_service.dismiss_correction_task(
            get_supabase_admin(), user.get("id"), correction_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Correction task not found.")


@router.get("/task-reasoning/{task_id}")
async def task_reasoning(
    task_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    """Why was this task scheduled? Splits reasoning into persona / exam /
    progress / update channels plus one aspirant-safe summary line.

    404 when the task does not exist or is not owned by the caller — task
    ids cannot be probed across users.
    """
    user_id = user.get("id")
    supabase = get_supabase_admin()
    try:
        result = build_task_reasoning_response(supabase, user_id, task_id)
    except Exception:  # noqa: BLE001
        logger.exception("task_reasoning build failed for %s / %s", user_id, task_id)
        raise HTTPException(status_code=500, detail="Task reasoning is temporarily unavailable.")
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


_VALID_NUDGE_CODES = {
    "mock_review_pending",
    "subject_behind",
    "backlog_over_threshold",
    "milestone_in_7d",
    "focus_streak_break",
}


@router.post("/nudges/{code}/dismiss")
async def dismiss_nudge(
    code: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    """Record that the user dismissed a Study Home nudge.

    Persisted in ``study_nudge_dismissals`` (migration 136). Mission
    Control filters the nudge from the payload for a fixed 24h TTL and
    surfaces it again if the underlying condition is still true after
    that window. 400 on an unknown code so the closed-set contract is
    enforced server-side as well as in the table CHECK constraint.
    """
    if code not in _VALID_NUDGE_CODES:
        raise HTTPException(status_code=400, detail="Unknown nudge code.")
    user_id = user.get("id")
    supabase = get_supabase_admin()
    from datetime import datetime, timezone

    try:
        supabase.table("study_nudge_dismissals").upsert(
            {
                "user_id": user_id,
                "nudge_code": code,
                "dismissed_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="user_id,nudge_code",
        ).execute()
    except Exception:  # noqa: BLE001
        logger.exception("nudge dismiss failed for %s / %s", user_id, code)
        raise HTTPException(status_code=500, detail="Could not dismiss nudge.")
    return {"ok": True, "code": code}


# ───────────────────────── Planner board (PLAN-UI-01) ──────────────────────
# The drag-and-drop planner surface. Two reads (the seven-day board, the
# palette of unscheduled topics) and the three mutations PLAN-UI-01's endpoint
# inventory found missing: place a task on a day at a position, create a
# user-placed task from a palette topic, remove a task.
#
# There is deliberately no bulk-replace route that accepts a whole day. Every
# mutation names ONE task id; the server re-reads the affected day and writes
# the ordinals itself, so a stale client can never wipe or reorder rows it has
# not seen. Ownership is enforced inside the service against the authenticated
# user, because the service-role client bypasses RLS.


def _board_error(exc: planner_board_service.BoardError) -> HTTPException:
    return HTTPException(
        status_code=exc.status, detail={"code": exc.code, "message": exc.message}
    )


class BoardPlacementBody(BaseModel):
    """Where the user dropped one card."""

    scheduled_date: str
    position: int | None = Field(default=None, ge=0)


class BoardCreateBody(BaseModel):
    """A palette topic dragged onto a day."""

    topic_id: str
    scheduled_date: str
    position: int | None = Field(default=None, ge=0)
    task_type: str = Field(default="concept")


@router.get("/plan/board")
async def get_plan_board(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Today plus the next six days, each with its ordered task cards."""
    try:
        return planner_board_service.get_board(get_supabase_admin(), user.get("id"))
    except planner_board_service.BoardError as exc:
        raise _board_error(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("plan board read failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="The planner board is temporarily unavailable.")


@router.get("/plan/candidates")
async def get_plan_candidates(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Locked-coverage topics not already scheduled in the board window."""
    try:
        return planner_board_service.list_candidates(get_supabase_admin(), user.get("id"))
    except planner_board_service.BoardError as exc:
        raise _board_error(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("plan candidates read failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="Topics are temporarily unavailable.")


@router.post("/plan/board/tasks")
async def create_board_task(
    body: BoardCreateBody, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    """Create a user-placed task from a palette topic."""
    try:
        return planner_board_service.create_user_task(
            get_supabase_admin(),
            user.get("id"),
            topic_id=body.topic_id,
            scheduled_date=body.scheduled_date,
            position=body.position,
            task_type=body.task_type,
        )
    except planner_board_service.BoardError as exc:
        raise _board_error(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("board task create failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="Couldn't add that task.")


@router.patch("/plan/board/tasks/{task_id}/placement")
async def move_board_task(
    task_id: str, body: BoardPlacementBody, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    """Move one task to a day and a position. Reorder and move are one call."""
    try:
        return planner_board_service.move_task(
            get_supabase_admin(),
            user.get("id"),
            task_id,
            scheduled_date=body.scheduled_date,
            position=body.position,
        )
    except planner_board_service.BoardError as exc:
        raise _board_error(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("board task move failed for %s / %s", user.get("id"), task_id)
        raise HTTPException(status_code=500, detail="Couldn't move that task.")


@router.delete("/plan/board/tasks/{task_id}")
async def delete_board_task(
    task_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    """Remove one task from the board."""
    try:
        return planner_board_service.delete_task(
            get_supabase_admin(), user.get("id"), task_id
        )
    except planner_board_service.BoardError as exc:
        raise _board_error(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("board task delete failed for %s / %s", user.get("id"), task_id)
        raise HTTPException(status_code=500, detail="Couldn't remove that task.")
