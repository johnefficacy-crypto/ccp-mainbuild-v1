"""Schema-contract tests for J3 PR1 migration 216 (competition structure).

Following the repo's documented convention (see test_mock_generated_blueprints_migration.py):
"The repo has no live-DB migration harness; existing migration tests assert
against the migration SQL text." These guard the checkpost-review fixes
against regression — the actual SQL was additionally validated by hand
against a real Postgres 16 instance (full 001-215 migration replay, plus
synthetic legacy-data disposition/conflict/normalization scenarios and a
full create->evidence->submit->review->lock RPC lifecycle) as part of
landing this PR; see the PR discussion for that evidence.
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase" / "migrations" / "216_j3_competition_structure.sql"
).read_text().lower()


def test_p0_conflicting_cycle_level_facts_abort_not_discard():
    # The split-on-disposition path must compare existing cycle_summary
    # values against the phase row's before discarding them, and abort
    # (not silently merge) on any distinct conflict.
    assert "v_conflict" in MIGRATION
    assert "distinct legacy values cannot be silently merged or discarded" in MIGRATION


def test_cycle_less_rows_are_triaged_not_blindly_assigned():
    assert "legacy_needs_cycle_assignment" in MIGRATION
    assert "if r.exam_cycle_id is null then" in MIGRATION


def test_working_lane_duplicates_fail_closed_not_keep_latest():
    assert "j3 §1.4 lane initialization blocked" in MIGRATION
    assert "have multiple draft/pending_review rows" in MIGRATION
    # The old keep-latest-by-updated_at heuristic must be gone.
    assert "order by updated_at desc, created_at desc" not in MIGRATION


def test_od5_legacy_value_normalization_present():
    assert "od-5 selective legacy value normalization" in MIGRATION
    assert "legacy_cutoff_trend_unconverted" in MIGRATION
    assert "legacy_difficulty_trend_unconverted" in MIGRATION


def test_publication_happens_on_pending_review_to_reviewed_not_on_lock():
    assert "p_new_status = 'reviewed' and v_row.reviewer_status = 'pending_review'" in MIGRATION
    # reviewed must not have a direct path to rejected (published rows are
    # corrected via reopen-for-edit, never rejected in place).
    assert "v_row.reviewer_status = 'reviewed'        and p_new_status = 'locked')" in MIGRATION
    assert "v_row.reviewer_status = 'reviewed'        and p_new_status in ('locked', 'rejected'))" not in MIGRATION


def test_model_generated_gated_on_submit_not_on_promote():
    assert "v_row.reviewer_status = 'draft' and p_new_status = 'pending_review'" in MIGRATION
    assert "model_generated_requires_evidence" in MIGRATION


def test_evidence_source_trust_and_reviewed_analysis_restriction():
    assert "sr.is_active and sr.is_verified and not sr.discovery_only and sr.source_type <> 'aggregator'" in MIGRATION
    assert "e.evidence_kind <> 'reviewed_analysis'" in MIGRATION


def test_per_category_claim_value_checks_for_vacancy_and_cutoff():
    assert "jsonb_each(v_row.vacancy_by_category)" in MIGRATION
    assert "jsonb_each(v_row.cutoff_by_category)" in MIGRATION


def test_evidence_key_is_server_computed_not_caller_supplied():
    assert "_ecme_compute_evidence_key" in MIGRATION
    assert "new.evidence_key :=" in MIGRATION


def test_taxonomy_rls_has_no_authenticated_read_policy():
    assert "reservation_categories_read_authenticated" not in MIGRATION
    assert "for select to authenticated using (true)" not in MIGRATION


def test_scope_integrity_trigger_present():
    assert "_ecm_check_scope" in MIGRATION
    assert "does not belong to exam_id" in MIGRATION


def test_evidence_table_has_no_hardcoded_evidence_key_default():
    # evidence_key has no DEFAULT clause in the table DDL — the compute
    # trigger is the sole source of truth for it.
    assert "evidence_key text not null unique" in MIGRATION
