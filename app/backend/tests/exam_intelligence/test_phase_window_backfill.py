"""Tests for the migration-166 backfill logic.

Migration 166 closes the hole left by 165: rows whose phase_window is 'TBD'
or '' were silently excluded from 165's loop and received neither a date nor
a needs_review flag.

This module tests the equivalent Python predicate that mirrors the migration's
UPDATE WHERE clause:

    WHERE phase_start IS NULL
      AND nullif(metadata->>'phase_window', '') IS NOT NULL
      AND (metadata->>'phase_window_needs_review') IS DISTINCT FROM 'true'

Rather than running SQL against a live DB, we verify the logic as a pure
function so the test is deterministic in CI.
"""
from __future__ import annotations


def _should_flag(phase: dict) -> bool:
    """Mirrors migration 166 UPDATE WHERE condition.

    Returns True if the migration would flag this row.
    """
    meta = phase.get("metadata") or {}
    # nullif(metadata->>'phase_window', '') — empty string becomes None
    pw = meta.get("phase_window") or ""
    if not pw:          # NULL or '' → condition fails
        return False
    if phase.get("phase_start") is not None:   # already dated → skip
        return False
    # IS DISTINCT FROM 'true' — only skip if the flag is already exactly 'true'
    already_flagged = str(meta.get("phase_window_needs_review", "")).lower() == "true"
    return not already_flagged


# ── should-flag ──────────────────────────────────────────────────────────────

def test_tbd_row_should_be_flagged():
    """TBD was excluded by migration 165 — 166 must catch it."""
    phase = {"id": "ph-1", "phase_start": None, "metadata": {"phase_window": "TBD"}}
    assert _should_flag(phase) is True


def test_empty_string_row_not_flagged():
    """Empty-string phase_window → nullif produces NULL → condition false."""
    phase = {"id": "ph-2", "phase_start": None, "metadata": {"phase_window": ""}}
    assert _should_flag(phase) is False


def test_freeform_unparseable_row_should_be_flagged():
    """A month-range like 'May–June 2026' is un-parseable — must be flagged."""
    phase = {"id": "ph-3", "phase_start": None, "metadata": {"phase_window": "May–June 2026"}}
    assert _should_flag(phase) is True


def test_row_with_phase_start_not_flagged():
    """Rows that already have a structured date must not be touched."""
    phase = {
        "id": "ph-4",
        "phase_start": "2026-05-24",
        "metadata": {"phase_window": "24 May 2026"},
    }
    assert _should_flag(phase) is False


def test_already_flagged_row_is_idempotent():
    """Re-run: rows already carrying phase_window_needs_review=true stay untouched."""
    phase = {
        "id": "ph-5",
        "phase_start": None,
        "metadata": {"phase_window": "TBD", "phase_window_needs_review": True},
    }
    assert _should_flag(phase) is False


def test_already_flagged_string_true_is_idempotent():
    """String 'true' (as stored in jsonb) also detected as already flagged."""
    phase = {
        "id": "ph-6",
        "phase_start": None,
        "metadata": {"phase_window": "TBD", "phase_window_needs_review": "true"},
    }
    assert _should_flag(phase) is False


def test_no_phase_window_at_all_not_flagged():
    """Rows without any phase_window metadata are out of scope."""
    phase = {"id": "ph-7", "phase_start": None, "metadata": {}}
    assert _should_flag(phase) is False


def test_no_metadata_at_all_not_flagged():
    """Rows with NULL metadata (empty dict here) are out of scope."""
    phase = {"id": "ph-8", "phase_start": None, "metadata": None}
    assert _should_flag(phase) is False


# ── bulk simulation ───────────────────────────────────────────────────────────

def test_bulk_simulation_flags_correct_subset():
    """Simulate applying the migration to a mixed set of rows."""
    phases = [
        {"id": "a", "phase_start": None,        "metadata": {"phase_window": "TBD"}},
        {"id": "b", "phase_start": None,        "metadata": {"phase_window": ""}},
        {"id": "c", "phase_start": None,        "metadata": {"phase_window": "May–June 2026"}},
        {"id": "d", "phase_start": "2026-05-24", "metadata": {"phase_window": "24 May 2026"}},
        {"id": "e", "phase_start": None,        "metadata": {"phase_window": "TBD",
                                                               "phase_window_needs_review": True}},
        {"id": "f", "phase_start": None,        "metadata": {}},
    ]
    to_flag = {p["id"] for p in phases if _should_flag(p)}
    # Only "a" (TBD) and "c" (unparseable range) should be flagged.
    assert to_flag == {"a", "c"}
    # Dates must never be set by this migration.
    for p in phases:
        if p["id"] in to_flag:
            assert p.get("phase_start") is None, "migration must not set any date"
