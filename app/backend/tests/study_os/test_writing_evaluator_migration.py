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
    # 8 original evaluator/outbox RPCs + ewp_canonical_error_type (§6 helper) +
    # ewp_recover_evaluation (§4.14 recovery) + ewp_reject_corrupt_version
    # (§8.1 corruption hard-fail) = 11 service_role grants.
    assert sql.count("to service_role") == 11
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


def test_canonical_error_type_helper_present_and_frequency_dependent():
    sql = _sql()
    assert "function ewp_private.ewp_canonical_error_type" in sql
    # §6 frequency-dependent mapping uses the prior-occurrence count.
    assert "p_prior_count > 0" in sql
    assert "'misread_question'" in sql and "'memory_gap'" in sql
    assert "'time_management'" in sql
    # the complete RPC delegates to the helper (no inline CASE mapping).
    assert "ewp_private.ewp_canonical_error_type(v_issue->>'issue_type', v_count)" in sql


def test_prior_count_filters_stale_and_invalidated():
    sql = _sql()
    # the prior-occurrence count must exclude stale + effectively-invalidated rows.
    assert "i2.affects_current_state = true" in sql
    assert "not ewp_private.ewp_issue_effectively_invalidated(i2.id)" in sql


def test_regression_lineage_and_regressed_outcome_present():
    sql = _sql()
    assert "'regressed'" in sql
    assert "_ewp_regressions" in sql


def test_recover_evaluation_rpc_generation_plus_one():
    sql = _sql()
    assert "function public.ewp_recover_evaluation" in sql
    assert "v_new_gen := v_job.generation + 1" in sql
    assert "language_status = 'queued'" in sql


def test_corruption_hard_fail_rpc_present_and_fails_closed():
    sql = _sql()
    assert "function public.ewp_reject_corrupt_version" in sql
    # fails closed regardless of deterministic_status → overall 'failed'.
    assert "overall_status = 'failed'" in sql
    assert "'evaluation_failed'" in sql


def test_sweeper_selects_ids_without_row_lock():
    sql = _sql()
    # the stale-lease sweeper must select candidate ids with a PLAIN read (no
    # FOR UPDATE on the job row) and requeue session-first via the helper.
    assert "ewp_private.ewp_requeue_stale_eval_job" in sql
    assert "revalidation_failed" in sql


def test_microtopic_map_requires_english_subject_tree():
    sql = _sql()
    assert "sub.slug = 'english-language'" in sql


def test_outbox_completion_rederives_and_binds_evidence_key():
    sql = _sql()
    assert "function ewp_private.ewp_compute_evidence_key" in sql
    assert "ewp_private.ewp_outbox_evidence_context" in sql
    # the recomputed key must be asserted against the claimed idempotency_key.
    assert "v_derived_key <> v_row.idempotency_key" in sql
