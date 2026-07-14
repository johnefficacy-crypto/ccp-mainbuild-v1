"""15-case test suite for resolve_exam_target_window.

All DB access goes through an in-memory SBStub; today is always injected.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.study_os.exam_target_window import resolve_exam_target_window
from tests.persona_questions._stub import SBStub

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

EXAM_ID = "exam-upsc-001"
CYCLE_2026_ID = "cycle-2026"
CYCLE_2025_ID = "cycle-2025"

TODAY = date(2026, 6, 11)


def _cycle(id=CYCLE_2026_ID, status="active", exam_start=None, year=2026, cycle_name="2026 Cycle"):
    return {
        "id": id,
        "exam_id": EXAM_ID,
        "status": status,
        "exam_start": exam_start,
        "year": year,
        "cycle_name": cycle_name,
        "created_at": f"{year}-01-01T00:00:00Z",
        # Trust gate (migration 261): Study OS only reads verified cycles.
        "reviewer_status": "verified",
    }


def _phase(
    id,
    *,
    exam_cycle_id=CYCLE_2026_ID,
    phase_name="Prelims",
    phase_slug="prelims",
    phase_order=1,
    status="active",
    phase_start=None,
    phase_end=None,
):
    return {
        "id": id,
        "exam_id": EXAM_ID,
        "exam_cycle_id": exam_cycle_id,
        "phase_name": phase_name,
        "phase_slug": phase_slug,
        "phase_order": phase_order,
        "status": status,
        "phase_start": phase_start,
        "phase_end": phase_end,
    }


def _resolve(sb_data, *, today=TODAY, manual_phase_id=None):
    sb = SBStub(sb_data)
    return resolve_exam_target_window(
        sb, exam_id=EXAM_ID, manual_phase_id=manual_phase_id, today=today
    )


# ---------------------------------------------------------------------------
# Case 1 — manual future active phase wins
# ---------------------------------------------------------------------------

def test_case01_manual_future_active_phase_wins():
    """Future manual phase: target_date = phase_start (not phase_end).

    phase_start=2026-09-01, phase_end=2026-10-31, today=2026-06-11.
    The phase has not started yet so it is a future manual selection;
    the contract says target = phase_start so users count down to kick-off.
    """
    ph = _phase("ph-1", status="active", phase_start="2026-09-01", phase_end="2026-10-31")
    out = _resolve(
        {"exam_cycles": [_cycle()], "exam_phases": [ph]},
        manual_phase_id="ph-1",
    )
    assert out["status"] == "connected"
    assert out["reason"] == "manual_phase"
    assert out["target_kind"] == "phase"
    assert out["target_phase_id"] == "ph-1"
    # Future manual → target_date = phase_start, not phase_end
    assert out["target_date"] == "2026-09-01"
    assert out["days_remaining"] == (date(2026, 9, 1) - TODAY).days


# ---------------------------------------------------------------------------
# Case 2 — manual completed phase is skipped
# ---------------------------------------------------------------------------

def test_case02_manual_completed_phase_skipped():
    """completed phase is not valid; resolver falls through to not_connected."""
    ph = _phase("ph-comp", status="completed", phase_start="2026-01-01", phase_end="2026-03-31")
    out = _resolve(
        {"exam_cycles": [_cycle()], "exam_phases": [ph]},
        manual_phase_id="ph-comp",
    )
    assert out["status"] == "not_connected"
    assert "manual_phase_invalid_or_stale" in (out["diagnostic"] or [])


# ---------------------------------------------------------------------------
# Case 3 — manual ended phase (today > phase_end) is skipped
# ---------------------------------------------------------------------------

def test_case03_manual_ended_phase_skipped():
    """Phase whose phase_end is in the past is not valid for manual selection."""
    ph = _phase("ph-past", status="active", phase_start="2026-01-01", phase_end="2026-06-01")
    out = _resolve(
        {"exam_cycles": [_cycle()], "exam_phases": [ph]},
        manual_phase_id="ph-past",
    )
    assert out["status"] == "not_connected"
    assert "manual_phase_invalid_or_stale" in (out["diagnostic"] or [])


# ---------------------------------------------------------------------------
# Case 4 — manual active phase with null phase_end → target_date null
# ---------------------------------------------------------------------------

def test_case04_manual_active_null_phase_end():
    """Valid manual phase with no phase_end → connected but target_date and days_remaining are null."""
    ph = _phase("ph-open", status="active", phase_start="2026-06-01", phase_end=None)
    out = _resolve(
        {"exam_cycles": [_cycle()], "exam_phases": [ph]},
        manual_phase_id="ph-open",
    )
    assert out["status"] == "connected"
    assert out["reason"] == "manual_phase"
    assert out["target_date"] is None
    assert out["days_remaining"] is None


# ---------------------------------------------------------------------------
# Case 5 — current active phase wins over next future phase
# ---------------------------------------------------------------------------

def test_case05_current_phase_wins_over_future():
    """When both a current and a future phase exist, current_phase is chosen."""
    current = _phase(
        "ph-cur",
        status="active",
        phase_start="2026-05-01",
        phase_end="2026-08-31",
        phase_order=1,
    )
    future = _phase(
        "ph-fut",
        status="expected",
        phase_start="2026-09-15",
        phase_end="2026-11-30",
        phase_order=2,
        phase_name="Mains",
        phase_slug="mains",
    )
    out = _resolve({"exam_cycles": [_cycle()], "exam_phases": [current, future]})
    assert out["reason"] == "current_phase"
    assert out["target_phase_id"] == "ph-cur"
    assert out["target_date"] == "2026-08-31"


# ---------------------------------------------------------------------------
# Case 6 — current active phase with null phase_end → target_date null
# ---------------------------------------------------------------------------

def test_case06_current_phase_null_phase_end():
    """Current active phase with no phase_end → connected/current_phase, target_date null."""
    ph = _phase("ph-cur-open", status="active", phase_start="2026-06-01", phase_end=None)
    out = _resolve({"exam_cycles": [_cycle()], "exam_phases": [ph]})
    assert out["status"] == "connected"
    assert out["reason"] == "current_phase"
    assert out["target_date"] is None
    assert out["days_remaining"] is None


# ---------------------------------------------------------------------------
# Case 7 — next future phase when no current
# ---------------------------------------------------------------------------

def test_case07_next_future_phase_days_remaining():
    """next_future_phase branch: target_date = phase_start, days_remaining is asserted."""
    future_start = "2026-09-01"
    ph = _phase(
        "ph-fut-only",
        status="expected",
        phase_start=future_start,
        phase_end="2026-10-31",
        phase_name="Mains",
        phase_slug="mains",
    )
    out = _resolve({"exam_cycles": [_cycle()], "exam_phases": [ph]})
    assert out["reason"] == "next_future_phase"
    assert out["target_date"] == future_start
    expected_days = (date(2026, 9, 1) - TODAY).days
    assert out["days_remaining"] == expected_days
    assert expected_days > 0


# ---------------------------------------------------------------------------
# Case 8 — generic unattached phases generate diagnostic
# ---------------------------------------------------------------------------

def test_case08_template_phases_generate_diagnostic():
    """Phases with exam_cycle_id=None are templates; they produce a diagnostic but are never targeted."""
    template = _phase(
        "ph-template",
        exam_cycle_id=None,
        status="active",
        phase_start="2026-09-01",
        phase_end="2026-10-31",
    )
    # Cycle exists; no cycle-attached phases; exam_start in past → not_connected
    cycle = _cycle(exam_start="2026-05-01")
    out = _resolve({"exam_cycles": [cycle], "exam_phases": [template]})
    assert out["status"] == "not_connected"
    assert "generic_templates_available_but_unattached" in (out["diagnostic"] or [])
    assert out["target_phase_id"] is None


# ---------------------------------------------------------------------------
# Case 9 — future cycle exam_start fallback
# ---------------------------------------------------------------------------

def test_case09_cycle_exam_start_fallback():
    """When no phase matches, fall back to cycle.exam_start if in the future."""
    future_exam_start = "2026-10-05"
    cycle = _cycle(exam_start=future_exam_start, status="active")
    out = _resolve({"exam_cycles": [cycle], "exam_phases": []})
    assert out["status"] == "connected"
    assert out["reason"] == "cycle_exam_start"
    assert out["target_kind"] == "exam_start"
    assert out["target_date"] == future_exam_start
    assert out["days_remaining"] == (date(2026, 10, 5) - TODAY).days


# ---------------------------------------------------------------------------
# Case 10 — past cycle exam_start, no future phase → not_connected
# ---------------------------------------------------------------------------

def test_case10_past_exam_start_not_connected():
    """Past cycle.exam_start with no phases → not_connected / no_dated_target."""
    cycle = _cycle(exam_start="2026-06-01", status="active")  # already past TODAY
    out = _resolve({"exam_cycles": [cycle], "exam_phases": []})
    assert out["status"] == "not_connected"
    assert out["reason"] == "no_dated_target"


# ---------------------------------------------------------------------------
# Case 11 — cycle selection: 2025 completed + 2026 active → 2026 chosen
# ---------------------------------------------------------------------------

def test_case11_active_cycle_wins_over_completed():
    """Active cycle is preferred over a completed one regardless of year ordering."""
    old = _cycle(id=CYCLE_2025_ID, status="completed", year=2025, cycle_name="2025 Cycle")
    new = _cycle(id=CYCLE_2026_ID, status="active", year=2026, cycle_name="2026 Cycle")
    ph = _phase("ph-2026", exam_cycle_id=CYCLE_2026_ID, status="active",
                phase_start="2026-06-01", phase_end="2026-08-31")
    out = _resolve({"exam_cycles": [old, new], "exam_phases": [ph]})
    assert out["cycle_id"] == CYCLE_2026_ID
    assert out["reason"] == "current_phase"


# ---------------------------------------------------------------------------
# Case 12 — no cycles → not_connected / no_cycle
# ---------------------------------------------------------------------------

def test_case12_no_cycles():
    """No exam cycles at all → not_connected / no_cycle."""
    out = _resolve({"exam_cycles": [], "exam_phases": []})
    assert out["status"] == "not_connected"
    assert out["reason"] == "no_cycle"
    assert out["cycle_id"] is None


# ---------------------------------------------------------------------------
# Case 13 — phases lack structured dates → structured_phase_dates_missing
# ---------------------------------------------------------------------------

def test_case13_phases_no_structured_dates():
    """Cycle-attached phases with no phase_start or phase_end → diagnostic structured_phase_dates_missing."""
    ph = _phase("ph-nodate", status="active", phase_start=None, phase_end=None)
    cycle = _cycle(exam_start="2026-05-01")  # past
    out = _resolve({"exam_cycles": [cycle], "exam_phases": [ph]})
    assert "structured_phase_dates_missing" in (out["diagnostic"] or [])
    assert out["status"] == "not_connected"


# ---------------------------------------------------------------------------
# Case 14 — days_remaining numeric vs null
# ---------------------------------------------------------------------------

def test_case14_days_remaining_numeric_vs_null():
    """Future phase has numeric days_remaining; open-ended current has null."""
    future_ph = _phase(
        "ph-future",
        status="expected",
        phase_start="2026-09-01",
        phase_end="2026-10-31",
        phase_name="Mains",
        phase_slug="mains",
    )
    out_future = _resolve({"exam_cycles": [_cycle()], "exam_phases": [future_ph]})
    assert out_future["reason"] == "next_future_phase"
    assert isinstance(out_future["days_remaining"], int)
    assert out_future["days_remaining"] > 0

    open_ph = _phase("ph-open2", status="active", phase_start="2026-06-01", phase_end=None)
    out_open = _resolve({"exam_cycles": [_cycle()], "exam_phases": [open_ph]})
    assert out_open["reason"] == "current_phase"
    assert out_open["days_remaining"] is None


# ---------------------------------------------------------------------------
# Case 15 — manual_phase_id invalid/stale → diagnostic + ladder continues
# ---------------------------------------------------------------------------

def test_case15_invalid_manual_phase_ladder_continues():
    """Invalid manual_phase_id appends diagnostic but resolver continues down the ladder."""
    # A current phase is available after the manual one fails
    current = _phase("ph-current", status="active", phase_start="2026-06-01", phase_end="2026-08-31")
    out = _resolve(
        {"exam_cycles": [_cycle()], "exam_phases": [current]},
        manual_phase_id="ph-does-not-exist",
    )
    # Manual fails → diagnostic added → ladder finds current_phase
    assert out["status"] == "connected"
    assert out["reason"] == "current_phase"
    assert "manual_phase_invalid_or_stale" in (out["diagnostic"] or [])
    assert out["target_phase_id"] == "ph-current"
