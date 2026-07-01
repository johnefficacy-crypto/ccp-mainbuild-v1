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


def test_effective_view_is_security_invoker_and_service_role_only():
    # A plain view runs with the owner's privileges and would leak every user's
    # evidence. security_invoker + REVOKE authenticated + GRANT service_role only.
    assert "with (security_invoker = true)" in _SQLL
    assert "revoke all on public.effective_user_topic_mastery_evidence from authenticated" in _SQLL
    assert "grant select on public.effective_user_topic_mastery_evidence to service_role" in _SQLL
    assert "grant select on public.effective_user_topic_mastery_evidence to authenticated" not in _SQLL


def test_fold_excludes_stale_and_invalidated_and_superseded():
    assert "affects_current_state = true" in _SQLL
    assert "decision = 'invalidated'" in _SQLL
    assert "s.supersedes_evidence_key = e.evidence_key" in _SQLL
    assert "s.user_id = e.user_id" in _SQLL  # same-user chain, no cross-user hiding


def test_evidence_supersession_integrity():
    assert "utme_supersedes_fk" in _SQLL
    # composite same-user FK (enforced at write, not just in the read view)
    assert "references public.user_topic_mastery_evidence(user_id, evidence_key)" in _SQLL
    assert "uq_utme_one_successor" in _SQLL          # linear chain
    assert "utme_op_cause_ck" in _SQLL               # retract/replace require cause + predecessor
    assert "utme_no_self_supersede_ck" in _SQLL


def test_session_snapshot_immutability_guard():
    assert "function public.ewp_guard_session_snapshot" in _SQLL
    assert "session_snapshot_immutable" in _SQLL
    assert "ewp_session_snapshot_guard" in _SQLL
    assert "writing_sessions_feedback_delay_ck" in _SQLL


def test_value_domain_constraints():
    assert "content_hash ~ '^[0-9a-f]{64}$'" in _SQLL
    assert "unit_number > 0" in _SQLL
    assert "version_number > 0" in _SQLL
    assert "span_end_utf16 >= span_start_utf16" in _SQLL
    assert "issue_type in (" in _SQLL
    assert "canonical_error_type in (" in _SQLL
    assert "'concept_gap','memory_gap','careless'" in _SQLL


def test_immutable_history_fks_not_cascade():
    # A cascade into an immutable child fires its BEFORE DELETE trigger and fails.
    for immutable_ref in (
        "references public.writing_unit_versions(id) on delete cascade",
        "references public.writing_issue_events(id) on delete cascade",
        "references public.writing_issue_events(id) on delete set null",
        "references public.writing_evaluations(id) on delete cascade",
    ):
        assert immutable_ref not in _SQLL


def test_full_section3_taxonomy_seeded():
    for slug in (
        "simple-sentences", "compound-sentences", "complex-sentences", "sentence-transformation",
        "topic-sentence", "conclusion",
        # descriptive leaves seeded as microtopics
        "precis-writing-general", "essay-writing-general",
        "letter-report-writing-general", "comprehension-summary-general",
    ):
        assert slug in _SQLL


def test_map_seed_validates_microtopic_level_and_active():
    assert "t.level = 'microtopic' and t.is_active = true" in _SQLL
    assert "no active english microtopic for slug" in _SQLL


def test_effective_review_uses_created_at_and_seq_tiebreak():
    # created_at alone ties within a transaction; event_seq is the monotonic
    # tiebreak. The helper is one shared definition used by view + RLS.
    assert "function public.ewp_issue_effectively_invalidated" in _SQLL
    assert "event_seq bigint generated always as identity" in _SQLW
    assert "order by r.created_at desc, r.event_seq desc" in _SQLL


def test_owner_rls_filters_effectively_invalidated_issues():
    # issue/resolution/projection owner reads must exclude effectively-invalidated
    # issues, not just check ownership + feedback release.
    assert _SQLL.count("ewp_issue_effectively_invalidated(writing_issue") >= 3


def test_same_user_supersession_enforced_at_write():
    assert "unique (user_id, evidence_key)" in _SQLL
    assert "foreign key (user_id, supersedes_evidence_key)" in _SQLL
    assert "references public.user_topic_mastery_evidence(user_id, evidence_key)" in _SQLL


def test_blank_version_and_key_domains():
    assert "writing_unit_versions_blank_ck" in _SQLL
    assert "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in _SQLL
    assert "evidence_key text not null check (evidence_key ~ '^[0-9a-f]{64}$')" in _SQLW
    assert "idempotency_key text not null check (idempotency_key ~ '^[0-9a-f]{64}$')" in _SQLW


def test_queue_lease_shape_constraints():
    assert "writing_evaluation_jobs_running_lease_ck" in _SQLL
    assert "writing_mastery_outbox_processing_lease_ck" in _SQLL


def test_review_override_integrity_enforced():
    assert "writing_issue_review_events_corrected_ck" in _SQLL
    assert "function public.ewp_check_override_projection" in _SQLL
    assert "ewp_override_projection_guard" in _SQLL
