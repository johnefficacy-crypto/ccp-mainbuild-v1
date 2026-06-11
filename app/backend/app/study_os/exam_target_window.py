from __future__ import annotations

from datetime import date
from typing import Any

from app.db.utils import execute_or_default


def resolve_exam_target_window(sb, *, exam_id, manual_phase_id=None, today=None):
    """Resolve the study target window for an exam.

    Returns a dict with status, reason, target_kind, and date fields.
    Reads only — no writes, no persistence.
    """
    if today is None:
        today = date.today()
    today_str = today.isoformat()

    # --- Cycle selection ---
    cycles = execute_or_default(
        "exam_cycles.select",
        lambda: sb.table("exam_cycles").select("*").eq("exam_id", exam_id).execute().data or [],
        [],
    )
    non_cancelled = [c for c in cycles if c.get("status") != "cancelled"]

    chosen_cycle = _pick_cycle(non_cancelled, today_str)

    if chosen_cycle is None:
        return _make(
            status="not_connected",
            reason="no_cycle",
            target_kind=None,
            exam_id=exam_id,
            cycle_id=None,
            cycle_name=None,
            phase=None,
            target_date=None,
            today=today,
            diagnostics=None,
        )

    cycle_id = chosen_cycle["id"]
    cycle_name = chosen_cycle.get("cycle_name")

    # --- Fetch all phases for this exam ---
    all_phases = execute_or_default(
        "exam_phases.select",
        lambda: sb.table("exam_phases").select("*").eq("exam_id", exam_id).execute().data or [],
        [],
    )

    # Phases with exam_cycle_id IS NULL are templates — never targeted
    template_phases = [p for p in all_phases if p.get("exam_cycle_id") is None]
    cycle_phases = [p for p in all_phases if p.get("exam_cycle_id") == cycle_id]

    diagnostics: list[str] = []
    if template_phases:
        diagnostics.append("generic_templates_available_but_unattached")

    if cycle_phases:
        has_structured = any(
            p.get("phase_start") is not None or p.get("phase_end") is not None
            for p in cycle_phases
        )
        if not has_structured:
            diagnostics.append("structured_phase_dates_missing")

    # --- Resolution ladder ---

    # 1. manual_phase_id (only if valid within the chosen cycle)
    if manual_phase_id is not None:
        manual = next((p for p in cycle_phases if p["id"] == manual_phase_id), None)
        if manual is not None and _is_valid(manual, today_str):
            return _make(
                status="connected",
                reason="manual_phase",
                target_kind="phase",
                exam_id=exam_id,
                cycle_id=cycle_id,
                cycle_name=cycle_name,
                phase=manual,
                target_date=manual.get("phase_end"),
                today=today,
                diagnostics=diagnostics or None,
            )
        diagnostics.append("manual_phase_invalid_or_stale")

    # 2. current phase: status=active, phase_start<=today, phase_end null or >=today
    current = _find_current(cycle_phases, today_str)
    if current is not None:
        return _make(
            status="connected",
            reason="current_phase",
            target_kind="phase",
            exam_id=exam_id,
            cycle_id=cycle_id,
            cycle_name=cycle_name,
            phase=current,
            target_date=current.get("phase_end"),
            today=today,
            diagnostics=diagnostics or None,
        )

    # 3. next future phase: smallest phase_start > today
    nfp = _find_next_future(cycle_phases, today_str)
    if nfp is not None:
        return _make(
            status="connected",
            reason="next_future_phase",
            target_kind="phase",
            exam_id=exam_id,
            cycle_id=cycle_id,
            cycle_name=cycle_name,
            phase=nfp,
            target_date=nfp["phase_start"],
            today=today,
            diagnostics=diagnostics or None,
        )

    # 4. cycle exam_start in the future
    cycle_exam_start = chosen_cycle.get("exam_start")
    if cycle_exam_start is not None and cycle_exam_start > today_str:
        return _make(
            status="connected",
            reason="cycle_exam_start",
            target_kind="exam_start",
            exam_id=exam_id,
            cycle_id=cycle_id,
            cycle_name=cycle_name,
            phase=None,
            target_date=cycle_exam_start,
            today=today,
            diagnostics=diagnostics or None,
        )

    # 5. not_connected / no_dated_target
    return _make(
        status="not_connected",
        reason="no_dated_target",
        target_kind=None,
        exam_id=exam_id,
        cycle_id=cycle_id,
        cycle_name=cycle_name,
        phase=None,
        target_date=None,
        today=today,
        diagnostics=diagnostics or None,
    )


# ---------------------------------------------------------------------------
# Cycle selection helpers
# ---------------------------------------------------------------------------

def _pick_cycle(non_cancelled: list[dict], today_str: str) -> dict | None:
    if not non_cancelled:
        return None

    # 1. active
    actives = [c for c in non_cancelled if c.get("status") == "active"]
    if actives:
        return actives[0]

    # 2. open
    opens = [c for c in non_cancelled if c.get("status") == "open"]
    if opens:
        return opens[0]

    # 3. expected with future exam_start (pick earliest)
    expected_future = sorted(
        [
            c for c in non_cancelled
            if c.get("status") == "expected"
            and c.get("exam_start") is not None
            and c["exam_start"] > today_str
        ],
        key=lambda c: c["exam_start"],
    )
    if expected_future:
        return expected_future[0]

    # 4. most-recent non-cancelled by exam_start desc, then created_at desc
    return sorted(
        non_cancelled,
        key=lambda c: c.get("exam_start") or c.get("created_at") or "",
        reverse=True,
    )[0]


# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------

def _is_valid(phase: dict, today_str: str) -> bool:
    """Phase validity predicate for the manual/current resolution branches."""
    if phase.get("status") not in ("expected", "active"):
        return False
    phase_end = phase.get("phase_end")
    if phase_end is not None and phase_end < today_str:
        return False
    return True


def _find_current(cycle_phases: list[dict], today_str: str) -> dict | None:
    candidates = [
        p for p in cycle_phases
        if p.get("status") == "active"
        and p.get("phase_start") is not None
        and p["phase_start"] <= today_str
        and (p.get("phase_end") is None or p["phase_end"] >= today_str)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.get("phase_order", 0))
    return candidates[0]


def _find_next_future(cycle_phases: list[dict], today_str: str) -> dict | None:
    candidates = [
        p for p in cycle_phases
        if p.get("phase_start") is not None
        and p["phase_start"] > today_str
        and p.get("status") in ("expected", "active")
        and (p.get("phase_end") is None or p["phase_end"] >= today_str)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p["phase_start"])
    return candidates[0]


# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------

def _days_remaining(target_date_str: str | None, today: date) -> int | None:
    if target_date_str is None:
        return None
    try:
        td = date.fromisoformat(target_date_str)
        return (td - today).days
    except (ValueError, TypeError):
        return None


def _make(
    *,
    status: str,
    reason: str,
    target_kind: str | None,
    exam_id: str,
    cycle_id: str | None,
    cycle_name: str | None,
    phase: dict | None,
    target_date: str | None,
    today: date,
    diagnostics: list[str] | None,
) -> dict:
    return {
        "status": status,
        "reason": reason,
        "target_kind": target_kind,
        "exam_id": exam_id,
        "cycle_id": cycle_id,
        "cycle_name": cycle_name,
        "target_phase_id": phase["id"] if phase else None,
        "target_phase_slug": phase.get("phase_slug") if phase else None,
        "target_phase_name": phase.get("phase_name") if phase else None,
        "target_date": target_date,
        "days_remaining": _days_remaining(target_date, today),
        "diagnostic": diagnostics,
    }
