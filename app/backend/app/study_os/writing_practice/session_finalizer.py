"""finalize_writing_session — single owner of session/unit rollup writes (§9).

This wraps the pure rollup logic in `session_state` with the Supabase reads and
the conditional, monotonic session-status/outcome write. It is idempotent:
running it twice with the same DB state produces the same result.

Locking/ordering note: the production implementation must acquire the canonical
lock order (§8.0 — session row, then all required units ascending) via an RPC or
`SELECT ... FOR UPDATE`. The Supabase client used here issues discrete calls; the
row-lock RPC is tracked for the operator/DB hardening pass. The rollup decision
itself is pure and covered by unit tests.
"""
from __future__ import annotations

import logging
from typing import Any

from app.study_os.writing_practice import session_state as st

logger = logging.getLogger("career_copilot.study_os.writing_finalizer")


def _latest_overall_status(supabase: Any, unit_version_ids: list[str]) -> dict[str, str | None]:
    """Map unit_version_id -> latest evaluation overall_status (highest revision)."""
    if not unit_version_ids:
        return {}
    rows = (
        supabase.table("writing_evaluations")
        .select("unit_version_id,evaluation_revision,overall_status")
        .in_("unit_version_id", unit_version_ids)
        .execute()
    ).data or []
    latest: dict[str, tuple[int, str | None]] = {}
    for r in rows:
        uv = r["unit_version_id"]
        rev = r.get("evaluation_revision") or 0
        if uv not in latest or rev > latest[uv][0]:
            latest[uv] = (rev, r.get("overall_status"))
    return {uv: v[1] for uv, v in latest.items()}


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

    overall_by_uv = _latest_overall_status(
        supabase, [v["id"] for v in latest_version_by_unit.values()]
    )

    views: list[st.UnitView] = []
    for u in units:
        lv = latest_version_by_unit.get(u["id"])
        overall = overall_by_uv.get(lv["id"]) if lv else None
        views.append(st.UnitView(
            unit_number=u["unit_number"],
            status=u["status"],
            overall_status=overall,
            recovery_available=_recovery_available(supabase, lv["id"]) if (lv and u["status"] == st.UNIT_EVAL_FAILED) else False,
        ))
    return views


def _recovery_available(supabase: Any, unit_version_id: str) -> bool:
    """A failed unit is recoverable while a job can still retry / re-generate."""
    jobs = (
        supabase.table("writing_evaluation_jobs")
        .select("attempts,max_attempts,status")
        .eq("evaluation_id", unit_version_id)  # note: joined via evaluation in prod
        .execute()
    ).data or []
    # If no job rows are visible, assume recovery is still possible (a new
    # generation can be enqueued) rather than declaring the session terminal.
    if not jobs:
        return True
    return any((j.get("attempts") or 0) < (j.get("max_attempts") or 0) for j in jobs)


def finalize_writing_session(supabase: Any, session_id: str) -> dict:
    """Recompute and persist session status + evaluation_outcome. Idempotent."""
    session = (
        supabase.table("writing_sessions")
        .select("id,status,evaluation_outcome")
        .eq("id", session_id)
        .single()
        .execute()
    ).data
    if not session:
        raise ValueError(f"writing session {session_id} not found")

    views = build_unit_views(supabase, session_id)
    new_status = st.roll_up_session_status(views)
    new_outcome = st.monotonic_outcome(
        session.get("evaluation_outcome"), st.aggregate_session_outcome(views)
    )

    patch: dict[str, Any] = {}
    if new_status != session.get("status"):
        patch["status"] = new_status
    if new_outcome != session.get("evaluation_outcome"):
        patch["evaluation_outcome"] = new_outcome
    if patch:
        supabase.table("writing_sessions").update(patch).eq("id", session_id).execute()

    return {"status": new_status, "evaluation_outcome": new_outcome}
