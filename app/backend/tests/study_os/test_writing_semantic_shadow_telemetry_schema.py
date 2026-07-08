"""EWP semantic shadow telemetry migration contract.

Migration 235 adds append-only, service-role-only telemetry for semantic
evaluator SHADOW runs. These rows are measurement artifacts only and must not
become lifecycle, prompt activation, human-review, or mastery authority.
"""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3]
    / "supabase/migrations/235_ewp_semantic_shadow_telemetry.sql"
).read_text()
_SQLL = _SQL.lower()
_SQLW = " ".join(_SQLL.split())


def test_migration_is_number_235():
    assert _SQL.startswith("-- Migration 235")


def test_shadow_telemetry_table_created():
    assert "create table if not exists public.writing_language_evaluator_runs" in _SQLL
    assert "role text not null default 'shadow'" in _SQLL
    assert "check (role in ('shadow'))" in _SQLW


def test_required_context_and_hash_columns_present():
    for token in (
        "evaluation_id uuid not null",
        "unit_version_id uuid not null",
        "evaluation_revision int not null",
        "input_hash text not null",
        "deterministic_evaluator_version text not null",
        "adapter_version text not null",
    ):
        assert token in _SQLL
    assert "input_hash ~ '^[0-9a-f]{64}$'" in _SQLL


def test_status_and_fail_closed_outcomes_are_locked():
    for status in (
        "succeeded",
        "failed",
        "timeout",
        "malformed",
        "low_confidence",
        "refusal",
        "provider_error",
        "skipped",
    ):
        assert f"'{status}'" in _SQLL


def test_comparison_and_disagreement_fields_present():
    for comparison in (
        "source_unchanged",
        "meaning_not_preserved",
        "source_comparison_uncertain",
    ):
        assert f"'{comparison}'" in _SQLL
    assert "disagrees_with_deterministic boolean generated always as" in _SQLL


def test_latency_token_cost_metadata_present():
    for token in (
        "latency_ms int",
        "input_tokens int",
        "output_tokens int",
        "total_tokens int",
        "estimated_cost_usd numeric",
        "metadata jsonb not null default '{}'::jsonb",
    ):
        assert token in _SQLL


def test_append_only_service_role_only():
    assert "alter table public.writing_language_evaluator_runs enable row level security" in _SQLW
    assert "revoke all on table public.writing_language_evaluator_runs from public, anon, authenticated" in _SQLW
    assert "grant select, insert on table public.writing_language_evaluator_runs to service_role" in _SQLW
    assert "before update or delete on public.writing_language_evaluator_runs" in _SQLW
    assert "execute function public.ewp_forbid_mutation()" in _SQLW


def test_no_client_policy_or_mastery_authority():
    assert "create policy" not in _SQLL
    assert "user_topic_mastery_evidence" not in _SQLL
    assert "writing_mastery_shadow" not in _SQLL
    assert "writing_mastery_outbox" not in _SQLL


def test_no_raw_user_or_prompt_payload_columns():
    forbidden = (
        "user_id",
        "exam_id",
        "answer_text",
        "prompt_text",
        "source_text",
        "provider_prompt",
        "raw_prompt",
    )
    for token in forbidden:
        assert token not in _SQLL


def test_service_role_insert_rpc_present():
    assert "create or replace function public.ewp_record_language_evaluator_run" in _SQLL
    assert "security definer" in _SQLL
    assert "insert into public.writing_language_evaluator_runs" in _SQLL
    assert "grant execute on function public.ewp_record_language_evaluator_run" in _SQLL
    assert "to service_role" in _SQLL
    assert "from public, anon, authenticated" in _SQLL


def test_no_unique_constraint_drops_shadow_retries():
    assert "uq_writing_language_evaluator_runs_eval_adapter_role" not in _SQLL
    assert "on conflict" not in _SQLL


def test_schema_reload_notify_present():
    assert "pg_notify('pgrst', 'reload schema')" in _SQLL



def test_no_corrupted_spacing_tokens():
    bad_tokens = (
        ("raw", "learner"),
        ("or", "provider"),
        (">", "0"),
    )
    for left, right in bad_tokens:
        assert f"{left}{right}" not in _SQLL
