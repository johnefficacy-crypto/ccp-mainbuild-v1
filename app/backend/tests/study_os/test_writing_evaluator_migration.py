"""Pure text-contract tests for migration 208 (EWP-2B evaluator RPCs).

No DB. Reads the SQL file as text and asserts the structural invariants that the
async evaluator + mastery-outbox workers depend on (fencing, replay guard,
canonical lock order, shadow/live gating, service_role-only grants).
"""
from __future__ import annotations

from pathlib import Path

_SQL_PATH = (
    Path(__file__).parents[3] / "supabase/migrations/208_english_writing_practice_evaluator.sql"
)


def _sql() -> str:
    return _SQL_PATH.read_text(encoding="utf-8").lower()


def test_migration_header():
    text = _SQL_PATH.read_text(encoding="utf-8")
    assert text.startswith("-- Migration 208")


def test_security_definer_functions_present():
    sql = _sql()
    for fn in (
        "function public.ewp_claim_evaluation_job",
        "ewp_complete_language_evaluation",
        "ewp_fail_evaluation_job",
        "ewp_sweep_stale_evaluation_jobs",
        "ewp_claim_mastery_outbox",
        "ewp_complete_mastery_outbox",
        "ewp_fail_mastery_outbox",
        "function public.ewp_sweep_stale_mastery_outbox",
        "function ewp_private.ewp_terminalize_eval_job",
    ):
        assert fn in sql, f"missing function reference: {fn}"


def test_for_update_skip_locked_used_twice():
    sql = _sql()
    assert "for update skip locked" in sql
    assert sql.count("for update skip locked") >= 2


def test_canonical_lock_order_in_complete_fail_path():
    assert "order by unit_number for update" in _sql()


def test_fencing_guard():
    sql = _sql()
    assert "ewp_job_fencing_failed" in sql
    assert "claim_token is distinct from p_claim_token" in sql


def test_replay_guard():
    assert "overall_status in ('completed','terminal_partial','failed')" in _sql()


def test_race_safe_projection_advisory_lock():
    assert "pg_advisory_xact_lock" in _sql()


def test_mastery_shadow_live_gated():
    assert "p_mastery_flag in ('shadow','live')" in _sql()


def test_grants_service_role_only():
    sql = _sql()
    assert sql.count("to service_role") == 8
    first_grant = sql.index("grant execute")
    assert "to authenticated" not in sql[first_grant:]


def test_pg_notify_reload_present():
    assert "pg_notify" in _sql()


def test_claim_token_column_added():
    assert (
        "alter table public.writing_mastery_outbox add column if not exists claim_token uuid"
        in _sql()
    )


def test_outbox_fencing_and_payload_validation_tokens():
    sql = _sql()
    assert "ewp_outbox_fencing_failed" in sql
    assert "ewp_outbox_payload_mismatch" in sql


def test_mastery_claim_only_evaluation_rows():
    assert "source_kind = 'evaluation'" in _sql()


def test_stale_path_current_gating():
    sql = _sql()
    assert sql.count("if v_is_current then") >= 2


def test_canonical_projection_mapping_present():
    sql = _sql()
    assert "canonical_error_type" in sql
    assert "'careless'" in sql
    assert "'concept_gap'" in sql


def test_sweeper_terminalises_via_helper():
    sql = _sql()
    assert sql.count("ewp_private.ewp_terminalize_eval_job") >= 2
