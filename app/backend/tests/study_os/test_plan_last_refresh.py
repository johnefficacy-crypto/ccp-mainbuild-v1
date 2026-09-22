"""PLAN-UX-01 — ``GET /api/study/plan``'s ``plan.last_refresh``.

The nightly sweep and a user's own regeneration are indistinguishable by
``event_type``: ``regen.py`` passes ``event_type="manual_regeneration"`` for
the sweep too, so ``study_os._derive_plan_trigger`` labels the sweep
``{"type": "manual"}``. What does separate them is the reason string —
``regen.py`` passes ``reason="scheduled_stale_refresh"`` and ``generate_plan``
persists it verbatim to ``study_plan_versions.reason``. This field reads that
column and nothing else.
"""
from __future__ import annotations

from app.api.canonical import _plan_last_refresh, _SWEEP_REASON


class _Rows:
    """Minimal supabase stub: records the query and returns canned rows."""

    def __init__(self, rows, *, raises=False):
        self._rows = rows
        self._raises = raises
        self.filters: list[tuple] = []
        self.ordered: list[tuple] = []
        self.limited: int | None = None
        self.selected: str | None = None

    def table(self, name):
        self.table_name = name
        return self

    def select(self, cols):
        self.selected = cols
        return self

    def eq(self, k, v):
        self.filters.append((k, v))
        return self

    def order(self, col, desc=False):
        self.ordered.append((col, desc))
        return self

    def limit(self, n):
        self.limited = n
        return self

    def execute(self):
        if self._raises:
            raise RuntimeError("read failed")
        return type("R", (), {"data": self._rows})()


def test_sweep_reason_reads_as_a_scheduled_trigger():
    sb = _Rows([{"reason": _SWEEP_REASON, "activated_at": "2026-09-22T02:05:00Z"}])
    assert _plan_last_refresh(sb, "plan-1") == {
        "trigger": "scheduled",
        "at": "2026-09-22T02:05:00Z",
    }


def test_any_other_reason_reads_as_manual():
    """A user apply, a mock-triggered regen and a null reason are all 'manual'
    for this field's purpose: something other than the nightly sweep produced
    the plan, so the auto-refresh notice must not claim otherwise."""
    for reason in ("user_apply", "mock_logged", "manual_regeneration", None):
        sb = _Rows([{"reason": reason, "activated_at": "2026-09-22T02:05:00Z"}])
        assert _plan_last_refresh(sb, "plan-1")["trigger"] == "manual", reason


def test_reads_the_newest_version_only():
    sb = _Rows([{"reason": _SWEEP_REASON, "activated_at": "2026-09-22T02:05:00Z"}])
    _plan_last_refresh(sb, "plan-1")
    assert sb.table_name == "study_plan_versions"
    assert ("plan_id", "plan-1") in sb.filters
    assert ("version_number", True) in sb.ordered  # desc
    assert sb.limited == 1


def test_falls_back_to_created_at_when_never_activated():
    sb = _Rows([{"reason": _SWEEP_REASON, "activated_at": None,
                 "created_at": "2026-09-22T02:05:00Z"}])
    assert _plan_last_refresh(sb, "plan-1")["at"] == "2026-09-22T02:05:00Z"


def test_no_version_rows_yields_none():
    """A plan predating version rows is a real state. None, never a guess from
    the plan's own updated_at — the notice would then fire on any recent edit."""
    assert _plan_last_refresh(_Rows([]), "plan-1") is None


def test_a_row_with_no_timestamp_yields_none():
    sb = _Rows([{"reason": _SWEEP_REASON, "activated_at": None, "created_at": None}])
    assert _plan_last_refresh(sb, "plan-1") is None


def test_a_failed_read_yields_none_rather_than_a_wrong_trigger():
    assert _plan_last_refresh(_Rows([], raises=True), "plan-1") is None
