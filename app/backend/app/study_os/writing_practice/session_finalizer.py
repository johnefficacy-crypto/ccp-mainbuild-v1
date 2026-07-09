"""finalize_writing_session — pure reference rollup for session/unit status (§9).

Wraps the pure rollup logic in `session_state` with Supabase reads, the
session-level completion gate (coverage + unresolved must_fix, §4.6c), and the
conditional, monotonic session-status/outcome write.

Locking note: the AUTHORITATIVE, transaction-safe finalizer is now the in-DB
``public.ewp_finalize_writing_session`` RPC (migration 206), which acquires the
canonical lock order (§8.0 — session row, then all required units ascending)
and applies ``ewp_private.ewp_apply_session_rollup`` under those locks; submit
and reopen roll up in the same transaction. The API calls the RPC, not this
module. This module is retained as the pure, unit-tested reference for the
rollup decision (mirrored byte-for-byte by the SQL) and is NOT the runtime
write path.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.study_os.writing_practice import coverage_checker
from app.study_os.writing_practice import session_state as st

logger = logging.getLogger("career_copilot.study_os.writing_finalizer")


def _now_iso() -> str:
    """UTC completion stamp. Mirrors the SQL rollup's now() (migration 238);
    the SQL RPC is the runtime write path, this reference is unit-tested only."""
    return datetime.now(timezone.utc).isoformat()


def _latest_evaluation(supabase: Any, unit_version_id: str) -> dict | None:
    rows = (
        supabase.table("writing_evaluations")
        .select("id,evaluation_revision,overall_status")
        .eq("unit_version_id", unit_version_id)
        .order("evaluation_revision", desc=True)
        .limit(1)
        .execute()
    ).data or []
    return rows[0] if rows else None


def _recovery_available(supabase: Any, evaluation_id: str | None) -> bool:
    """A failed unit is recoverable while a job for its evaluation can retry.

    NOTE: keyed on evaluation_id (the correct FK), not unit_version_id.
    """
    if not evaluation_id:
        return True
    jobs = (
        supabase.table("writing_evaluation_jobs")
        .select("attempts,max_attempts,status")
        .eq("evaluation_id", evaluation_id)
        .execute()
    ).data or []
    if not jobs:
        return True  # a new generation can still be enqueued
    return any((j.get("attempts") or 0) < (j.get("max_attempts") or 0) for j in jobs)


def build_unit_views(supabase: Any, session_id: str) -> list[st.UnitView]:
    """Read units + their latest version's latest evaluation into UnitViews."""
    units = (
        supabase.table("writing_session_units")
        .select("id,unit_number,status")
        .eq("session_id", session_id)
        .order("unit_number")
        .execute()
    ).data or []

    versions = (
        supabase.table("writing_unit_versions")
        .select("id,unit_id,version_number")
        .in_("unit_id", [u["id"] for u in units] or ["_none_"])
        .execute()
    ).data or []
    latest_version_by_unit: dict[str, dict] = {}
    for v in versions:
        uid = v["unit_id"]
        if uid not in latest_version_by_unit or v["version_number"] > latest_version_by_unit[uid]["version_number"]:
            latest_version_by_unit[uid] = v

    views: list[st.UnitView] = []
    for u in units:
        lv = latest_version_by_unit.get(u["id"])
        evaluation = _latest_evaluation(supabase, lv["id"]) if lv else None
        overall = evaluation.get("overall_status") if evaluation else None
        recovery = (
            _recovery_available(supabase, evaluation.get("id") if evaluation else None)
            if u["status"] == st.UNIT_EVAL_FAILED
            else False
        )
        views.append(st.UnitView(
            unit_number=u["unit_number"],
            status=u["status"],
            overall_status=overall,
            recovery_available=recovery,
        ))
    return views


def _has_unresolved_must_fix(supabase: Any, session_id: str) -> bool:
    """Any effective, unresolved must_fix issue on a latest version (§4.6c).

    Empty until EWP-2B produces language issues; forward-compatible here.
    """
    units = (
        supabase.table("writing_session_units").select("id").eq("session_id", session_id).execute()
    ).data or []
    version_ids: list[str] = []
    for u in units:
        rows = (
            supabase.table("writing_unit_versions").select("id,version_number")
            .eq("unit_id", u["id"]).order("version_number", desc=True).limit(1).execute()
        ).data or []
        if rows:
            version_ids.append(rows[0]["id"])
    if not version_ids:
        return False
    evals = (
        supabase.table("writing_evaluations").select("id")
        .in_("unit_version_id", version_ids).execute()
    ).data or []
    eval_ids = [e["id"] for e in evals]
    if not eval_ids:
        return False
    issues = (
        supabase.table("writing_issue_events")
        .select("id,severity,affects_current_state")
        .in_("evaluation_id", eval_ids)
        .eq("severity", "must_fix")
        .eq("affects_current_state", True)
        .execute()
    ).data or []
    if not issues:
        return False
    resolved = (
        supabase.table("writing_issue_resolution_events")
        .select("issue_event_id,outcome")
        .in_("issue_event_id", [i["id"] for i in issues])
        .eq("outcome", "resolved")
        .execute()
    ).data or []
    resolved_ids = {r["issue_event_id"] for r in resolved}
    return any(i["id"] not in resolved_ids for i in issues)


def finalize_writing_session(supabase: Any, session_id: str) -> dict:
    """Recompute and persist session status + evaluation_outcome. Idempotent."""
    session = (
        supabase.table("writing_sessions")
        .select("id,status,evaluation_outcome,completed_at,prompt_id")
        .eq("id", session_id)
        .single()
        .execute()
    ).data
    if not session:
        raise ValueError(f"writing session {session_id} not found")

    views = build_unit_views(supabase, session_id)
    coverage_passed = coverage_checker.latest_authoritative_coverage(supabase, session_id)
    unresolved_must_fix = _has_unresolved_must_fix(supabase, session_id)

    new_status = st.roll_up_session_status(
        views,
        coverage_passed=coverage_passed,
        has_unresolved_must_fix=unresolved_must_fix,
    )
    new_outcome = st.monotonic_outcome(
        session.get("evaluation_outcome"), st.aggregate_session_outcome(views)
    )

    # Completion-timestamp invariant, mirrored byte-for-byte by the SQL rollup
    # (migration 238): completed_at IS NOT NULL <=> status == 'completed'. Into
    # completed -> stamp once (monotonic: keep an existing stamp on a re-roll);
    # out of completed (e.g. a learning-mode reopen) -> clear back to None.
    cur_completed_at = session.get("completed_at")
    if new_status == st.SESSION_COMPLETED:
        new_completed_at = cur_completed_at or _now_iso()
    else:
        new_completed_at = None

    patch: dict[str, Any] = {}
    if new_status != session.get("status"):
        patch["status"] = new_status
    if new_outcome != session.get("evaluation_outcome"):
        patch["evaluation_outcome"] = new_outcome
    if new_completed_at != cur_completed_at:
        patch["completed_at"] = new_completed_at
    if patch:
        supabase.table("writing_sessions").update(patch).eq("id", session_id).execute()

    return {"status": new_status, "evaluation_outcome": new_outcome}
