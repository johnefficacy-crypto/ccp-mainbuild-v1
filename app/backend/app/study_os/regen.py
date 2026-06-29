"""Event-driven Study OS plan regeneration.

Two entry points:

* ``regenerate_on_signal`` — called from a request path (e.g. a logged
  mock that just changed the user's topic mastery). Regenerates the plan
  *only* when the user already has an active plan and hasn't opted out of
  auto-regeneration. It never creates a plan from nothing on a
  side-channel signal — that stays an explicit action.
* ``regenerate_stale_plans`` — a periodic sweep (wired into the
  APScheduler) that refreshes every active plan not already regenerated
  today, for users who keep auto-regeneration on.

Both are fully defensive — they never raise out to their caller.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from app.study_os import calibration
from app.study_os.plan_preferences import get_plan_preferences
from app.study_os.planner import _resolve_target_exam, generate_plan

logger = logging.getLogger("career_copilot.study_os.regen")


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("regen read failed: %s", exc)
        return default


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _active_plan(supabase: Any, user_id: str) -> dict[str, Any] | None:
    rows = (
        _safe(
            lambda: (
                supabase.table("study_plans")
                .select("id, status, updated_at")
                .eq("user_id", user_id)
                .eq("status", "active")
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    return rows[0] if rows else None


def _calibration_blocks_regen(
    supabase: Any, user_id: str, *, has_active_plan: bool
) -> bool:
    """Safety-net onboarding-calibration guard for scheduled/signal regen.

    The calibration gate is a *pre-first-plan* interstitial. Both regen entry
    points only ever act on users who already have an active plan, so they are
    grandfathered by construction: when ``has_active_plan`` is True this returns
    False and behavior is unchanged for every existing-plan user (the guard then
    only matters as a tripwire, never blocking the population regen serves).

    For completeness it still consults the shared
    ``calibration.calibration_required`` for the user's resolved target exam; if
    the exam cannot be resolved it returns False (no block) rather than guessing.
    Fully defensive — never raises out to the caller.
    """
    if has_active_plan:
        return False
    exam = _safe(lambda: _resolve_target_exam(supabase, user_id), default=None)
    exam_id = exam.get("id") if exam else None
    if not exam_id:
        return False
    try:
        return bool(calibration.calibration_required(supabase, user_id, str(exam_id)))
    except calibration.CalibrationUnavailable:
        # Unknown gate state → fail closed: skip this regeneration rather than
        # risk generating an uncalibrated first plan under a transient read error.
        return True
    except Exception:  # noqa: BLE001 — defensive tripwire, never raises out
        return False


def regenerate_on_signal(
    supabase: Any, user_id: str, *, event_type: str, reason: str
) -> dict[str, Any]:
    """Regenerate the user's plan in response to a runtime signal.

    No-ops (returning ``regenerated=False`` with a ``reason``) when the
    user has opted out of auto-regeneration or has no active plan yet.
    """
    if not user_id:
        return {"regenerated": False, "reason": "no_user"}

    prefs = get_plan_preferences(supabase, user_id)
    if not prefs.get("auto_regenerate", True):
        return {"regenerated": False, "reason": "auto_regenerate_off"}

    if not _active_plan(supabase, user_id):
        return {"regenerated": False, "reason": "no_active_plan"}

    # Safety net only: the user provably has an active plan here, so the
    # pre-first-plan calibration gate never blocks this path (grandfathered).
    if _calibration_blocks_regen(supabase, user_id, has_active_plan=True):
        logger.info(
            "regen skipped for %s: onboarding calibration required", user_id
        )
        return {"regenerated": False, "reason": "calibration_required"}

    result = _safe(
        lambda: generate_plan(
            supabase, user_id, reason=reason, event_type=event_type
        ),
        default=None,
    )
    if not result or not result.get("generated"):
        return {
            "regenerated": False,
            "reason": (result or {}).get("reason", "generate_failed"),
        }
    return {
        "regenerated": True,
        "plan_id": result.get("plan_id"),
        "version_number": result.get("version_number"),
        "task_count": result.get("task_count"),
    }


def regenerate_stale_plans(supabase: Any, *, limit: int = 200) -> dict[str, Any]:
    """Refresh every active plan that hasn't been regenerated today.

    Intended for the daily APScheduler sweep. Users with
    ``auto_regenerate=false`` are skipped; plans already updated today are
    left alone. Returns a small summary; never raises.
    """
    today = _today_iso()
    plans = (
        _safe(
            lambda: (
                supabase.table("study_plans")
                .select("id, user_id, status, updated_at")
                .eq("status", "active")
                .limit(limit)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )

    checked = 0
    regenerated = 0
    skipped_fresh = 0
    skipped_opt_out = 0
    for plan in plans:
        user_id = plan.get("user_id")
        if not user_id:
            continue
        checked += 1
        if str(plan.get("updated_at") or "")[:10] >= today:
            skipped_fresh += 1
            continue
        prefs = get_plan_preferences(supabase, user_id)
        if not prefs.get("auto_regenerate", True):
            skipped_opt_out += 1
            continue
        # Each iterated plan is already status='active', so this guard is a
        # tripwire only and never blocks an existing-plan user (grandfathered).
        if _calibration_blocks_regen(supabase, user_id, has_active_plan=True):
            logger.info(
                "stale-regen skipped for %s: onboarding calibration required",
                user_id,
            )
            continue
        result = _safe(
            lambda uid=user_id: generate_plan(
                supabase,
                uid,
                reason="scheduled_stale_refresh",
                event_type="manual_regeneration",
            ),
            default=None,
        )
        if result and result.get("generated"):
            regenerated += 1

    return {
        "checked": checked,
        "regenerated": regenerated,
        "skipped_fresh": skipped_fresh,
        "skipped_opt_out": skipped_opt_out,
    }
