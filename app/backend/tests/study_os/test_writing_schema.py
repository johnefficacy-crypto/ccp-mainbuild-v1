"""EWP-1 migration contract for English Writing Practice.

Asserts migration 205 declares the full locked schema
(docs/architecture/english-writing-practice.md): all 17 tables, the append-only
immutability triggers, the review-override partial unique indexes, the
service-role-only RLS posture, the effective-evidence fold view, and the
deterministic taxonomy seed. Text-assertion style matches the repo's other
migration contracts (e.g. test_mock_mastery_shadow_migration.py); live apply is
an OPERATOR PENDING gate.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_SQL = (
    Path(__file__).parents[3]
    / "supabase/migrations/205_english_writing_practice_schema.sql"
).read_text()
_SQLL = _SQL.lower()
# Whitespace-collapsed view for assertions that shouldn't depend on alignment.
_SQLW = " ".join(_SQLL.split())


@pytest.mark.parametrize("table", [
    "writing_rubrics",
    "writing_prompts",
    "exam_descriptive_requirements",
    "writing_sessions",
    "writing_session_units",
    "writing_unit_versions",
    "writing_evaluations",
    "writing_session_checks",
    "writing_issue_events",
    "writing_issue_resolution_events",
    "writing_issue_projections",
    "writing_issue_review_events",
    "user_topic_mastery_evidence",
    "writing_evaluation_jobs",
    "writing_mastery_shadow",
    "writing_mastery_outbox",
    "writing_issue_type_microtopic_map",
])
def test_table_created(table):
    assert f"create table if not exists public.{table}" in _SQLL


def test_no_microtopics_table_reference():
    # The repo has no `microtopics` table; taxonomy lives in `topics`.
    assert "references public.microtopics" not in _SQLL
    assert "microtopics(id)" not in _SQLL


def test_user_fks_use_profiles_not_auth_users():
    # Repo convention: user FKs reference public.profiles(id).
    assert "references public.profiles(id)" in _SQLL
    assert "references auth.users" not in _SQLL


def test_reviewer_status_vocabulary():
    assert "reviewer_status" in _SQLL
    assert "'pending','verified','rejected','needs_correction'" in _SQLL
    # never the retired draft->published lifecycle
    assert "'published'" not in _SQLL


def test_study_tasks_typed_launch_target_columns():
    assert "add column if not exists launch_type" in _SQLL
    assert "add column if not exists launch_entity_id" in _SQLL
    assert "add column if not exists launch_context" in _SQLL


def test_tier_rank_helper_not_lexical():
    assert "function public.ewp_tier_rank" in _SQLL
    for tier in ("recognition", "correction", "production", "retention"):
        assert tier in _SQLL


def test_immutability_triggers_on_append_only_tables():
    assert "function public.ewp_forbid_mutation" in _SQLL
    assert "before update or delete" in _SQLL
    assert "append_only_violation" in _SQLL
    for table in (
        "writing_unit_versions",
        "writing_issue_events",
        "writing_issue_resolution_events",
        "writing_issue_projections",
        "writing_issue_review_events",
        "user_topic_mastery_evidence",
        "writing_mastery_shadow",
    ):
        assert f"'{table}'" in _SQLL


def test_review_override_projection_partial_unique_indexes():
    # automatic projections are unique per (issue, revision); overrides live alongside.
    assert "projection_kind" in _SQLL
    assert "uq_writing_issue_projections_automatic" in _SQLL
    assert "where projection_kind = 'automatic'" in _SQLL
    assert "uq_writing_issue_projections_override" in _SQLL
    assert "where projection_kind = 'review_override'" in _SQLL


def test_evidence_key_and_correction_columns():
    assert "evidence_key" in _SQLL
    assert "evidence_op" in _SQLL
    assert "supersedes_evidence_key" in _SQLL
    assert "unique (evidence_key)" in _SQLL


def test_outbox_mode_pinning_and_source_kind():
    assert "mastery_flag_state" in _SQLL
    assert "source_kind" in _SQLL
    assert "'evaluation','review_correction'" in _SQLL
    assert "unique (idempotency_key)" in _SQLL


def test_evaluation_jobs_lease_fencing_columns():
    assert "claim_token" in _SQLL
    assert "locked_at" in _SQLL


def test_terminal_partial_status_present():
    assert "terminal_partial" in _SQLL


def test_session_evaluation_incomplete_state():
    assert "evaluation_incomplete" in _SQLL


def test_feedback_release_check_is_null_safe():
    # scheduled_after_submit must require a positive delay; a bare `delay > 0`
    # would let a NULL delay through (CHECK only fails on FALSE).
    assert "feedback_release_delay_seconds is not null and feedback_release_delay_seconds > 0" in _SQLL


def test_effective_evidence_fold_view():
    assert "create or replace view public.effective_user_topic_mastery_evidence" in _SQLL
    assert "supersedes_evidence_key" in _SQLL


def test_service_role_only_tables_have_no_client_policy():
    for table in (
        "writing_issue_review_events",
        "user_topic_mastery_evidence",
        "writing_evaluation_jobs",
        "writing_mastery_shadow",
        "writing_mastery_outbox",
    ):
        # RLS enabled (whitespace-insensitive) ...
        assert f"alter table public.{table} enable row level security" in _SQLW
        # ... but no policy targets the table.
        assert f"create policy {table}" not in _SQLW
        assert f"on public.{table} for" not in _SQLW


def test_owner_select_policies_present():
    for table in (
        "writing_sessions",
        "writing_session_units",
        "writing_unit_versions",
        "writing_session_checks",
        "writing_evaluations",
    ):
        assert f"on public.{table}" in _SQLL
    assert "auth.uid()" in _SQLL
    assert "feedback_released_at" in _SQLL


def test_deterministic_seed_no_gen_random_uuid_for_taxonomy():
    # Seed IDs are deterministic; gen_random_uuid is only for surrogate PK defaults.
    assert "md5('ewp:subject:english-language')::uuid" in _SQLL
    assert "english-language" in _SQLL
    # every §5.1 issue_type is mapped
    for issue_type in (
        "sentence_fragment", "run_on_sentence", "subject_verb_agreement", "tense",
        "article", "preposition", "pronoun_reference", "modifier", "spelling",
        "punctuation", "word_choice", "collocation", "redundancy", "informal_usage",
        "cohesion", "logical_order", "off_topic", "word_limit", "format_violation",
    ):
        assert issue_type in _SQLL


def test_schema_reload_notify():
    assert "pg_notify('pgrst', 'reload schema')" in _SQLL


def test_migration_is_number_205():
    assert _SQL.startswith("-- Migration 205")
