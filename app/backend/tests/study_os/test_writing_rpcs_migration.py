"""Migration 206 contract: atomic EWP-2 runtime RPCs.

Text-assertion style (matches the repo's migration contracts); behavioural
apply/round-trip is validated against Postgres in the operator/integration pass
and by test_writing_rpcs_behaviour.py (gated on EWP_PG_DSN).
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


def test_public_rpcs_defined_security_definer():
    for fn in (
        "ewp_create_writing_session",
        "ewp_submit_writing_unit",
        "ewp_reopen_writing_unit",
        "ewp_finalize_writing_session",
    ):
        assert f"function public.{fn}" in _L
    # four public RPCs + four private security-definer helpers.
    assert _L.count("security definer") >= 8


def test_private_helpers_in_private_schema():
    for fn in (
        "ewp_private.ewp_version_set_hash",
        "ewp_private.ewp_recovery_available",
        "ewp_private.ewp_has_unresolved_must_fix",
        "ewp_private.ewp_apply_session_rollup",
    ):
        assert f"function {fn}" in _L
    # The private helpers are never granted to service_role (no RPC oracle).
    assert "grant execute on function ewp_private" not in _L


def test_canonical_lock_order_session_then_units_ascending():
    # session row locked first, then all units ascending (§8.0)
    assert "from public.writing_sessions" in _L and "for update" in _L
    assert "order by unit_number for update" in _L


def test_mandatory_version_cas_and_transition_guards():
    assert "ewp_stale_version" in _L
    assert "p_expected_version is null" in _L          # CAS token is mandatory
    assert "p_expected_version <> v_next_version" in _L
    assert "ewp_not_submittable" in _L
    # evaluation_pending is NOT a submittable source state (no duplicate submit).
    assert "status not in ('not_started','draft','rewrite_required')" in _L


def test_in_transaction_rollup_on_write_paths():
    # submit and reopen both roll the session up inside their own transaction.
    assert _L.count("perform ewp_private.ewp_apply_session_rollup") == 2
    # finalizer acquires the canonical locks then applies the rollup.
    assert "return ewp_private.ewp_apply_session_rollup(p_session)" in _L


def test_in_db_version_set_hash_matches_backend_layout():
    # byte-for-byte reconstruction of compute_version_set_hash (§4.5a).
    assert "convert_to('wps_version_set_v1', 'utf8')" in _L
    assert "int4send" in _L and "uuid_send" in _L
    assert "encode(sha256(v_payload), 'hex')" in _L


def test_exam_mode_rejected():
    assert "ewp_mode_unsupported" in _L
    assert "p_mode <> 'learning'" in _L


def test_service_role_only_grants():
    assert _L.count("revoke all on function") == 4
    assert _L.count("to service_role") == 4
    assert "to authenticated" not in _L.split("grant execute", 1)[-1]


def test_schema_reload_notify():
    assert "pg_notify('pgrst', 'reload schema')" in _SQL


def test_defensive_private_schema_guard():
    # applies cleanly even if run in isolation (does not assume 205 ran first).
    assert "create schema if not exists ewp_private" in _L
