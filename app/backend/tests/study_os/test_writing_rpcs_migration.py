"""Migration 206 contract: atomic EWP-2 runtime RPCs.

Text-assertion style (matches the repo's migration contracts); behavioural
apply/round-trip is validated against Postgres in the operator/integration pass.
"""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3]
    / "supabase/migrations/206_english_writing_practice_rpcs.sql"
).read_text()
_L = _SQL.lower()


def test_is_migration_206():
    assert _SQL.startswith("-- Migration 206")


def test_three_rpcs_defined_security_definer():
    for fn in (
        "ewp_create_writing_session",
        "ewp_submit_writing_unit",
        "ewp_reopen_writing_unit",
    ):
        assert f"function public.{fn}" in _L
    assert _L.count("security definer") >= 3          # one per function (+ header prose)
    assert _L.count("set search_path = public") == 3  # exactly one per function


def test_canonical_lock_order_session_then_units_ascending():
    # session row locked first, then all units ascending (§8.0)
    assert "from public.writing_sessions" in _L and "for update" in _L
    assert "order by unit_number for update" in _L


def test_version_cas_and_transition_guards():
    assert "ewp_stale_version" in _L
    assert "p_expected_version <> v_next_version" in _L
    assert "ewp_not_submittable" in _L
    assert "status not in ('not_started','draft','rewrite_required','evaluation_pending')" in _L


def test_exam_mode_rejected():
    assert "ewp_mode_unsupported" in _L
    assert "p_mode <> 'learning'" in _L


def test_service_role_only_grants():
    assert _L.count("revoke all on function") == 3
    assert _L.count("to service_role") == 3
    assert "to authenticated" not in _L.split("grant execute", 1)[-1]


def test_schema_reload_notify():
    assert "pg_notify('pgrst', 'reload schema')" in _SQL
