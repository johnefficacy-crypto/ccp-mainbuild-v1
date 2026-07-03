"""Schema-contract tests for J3 PR2 migration 219 (applied-vs-appeared).

Following the repo's documented convention (see
test_j3_competition_structure_migration.py / test_mock_generated_blueprints_migration.py):
"The repo has no live-DB migration harness; existing migration tests assert
against the migration SQL text."
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase" / "migrations" / "219_j3_applied_vs_appeared.sql"
).read_text().lower()


def test_table_is_exam_id_scoped_never_recruitment_id():
    assert "exam_id uuid not null references public.exams(id)" in MIGRATION
    # recruitment_id is never a column/FK anywhere in the file (only appears,
    # if at all, inside prose comments explaining canonicity — never as a
    # "references public.recruitments" column).
    assert "recruitment_id uuid" not in MIGRATION
    assert "references public.recruitments" not in MIGRATION


def test_reuses_shared_reservation_categories_does_not_recreate():
    assert "create table if not exists public.reservation_categories" not in MIGRATION
    assert "references public.reservation_categories(id)" in MIGRATION


def test_scope_kind_and_count_type_shape_checks_present():
    assert "ecc_count_type_scope_shape" in MIGRATION
    assert "count_type = 'applied' and scope_kind = 'cycle' and exam_phase_id is null" in MIGRATION
    assert "count_type = 'appeared' and (" in MIGRATION


def test_scope_integrity_trigger_present():
    assert "_ecc_check_scope" in MIGRATION
    assert "trg_ecc_check_scope" in MIGRATION


def test_null_safe_two_lane_indexes_use_nulls_not_distinct():
    assert "ecc_current_pub_uq" in MIGRATION
    assert "ecc_working_uq" in MIGRATION
    assert "nulls not distinct" in MIGRATION


def test_version_lineage_constraints_present():
    assert "ecc_no_self_supersede" in MIGRATION
    assert "ecc_version_no_positive" in MIGRATION
    assert "ecc_supersedes_self_fk" in MIGRATION


def test_current_published_state_and_superseded_checks_present():
    assert "ecc_current_published_state" in MIGRATION
    assert "ecc_superseded_not_current" in MIGRATION


def test_published_parent_update_guard_present():
    assert "_ecc_guard_published_update" in MIGRATION
    assert "published_row_immutable" in MIGRATION
    assert "app.candidate_count_lifecycle_rpc" in MIGRATION


def test_published_parent_delete_guard_present():
    assert "_ecc_guard_published_delete" in MIGRATION


def test_evidence_table_has_no_claim_field_or_category_column():
    # §4.1: the parent row IS the single claim — no claim_field, no
    # reservation_category_id on the evidence row.
    evidence_section = MIGRATION[MIGRATION.index("create table if not exists public.exam_candidate_count_evidence"):]
    evidence_section = evidence_section[: evidence_section.index(");")]
    assert "claim_field" not in evidence_section
    assert "reservation_category_id" not in evidence_section


def test_evidence_key_is_server_computed_not_caller_supplied():
    assert "_ecce_compute_evidence_key" in MIGRATION
    assert "new.evidence_key :=" in MIGRATION


def test_evidence_append_only_immutability_triggers_present():
    assert "_ecce_guard_immutable" in MIGRATION
    assert "evidence_immutable" in MIGRATION
    assert "trg_ecce_guard_immutable" in MIGRATION


def test_evidence_source_present_check():
    assert "ecce_source_present" in MIGRATION
    assert "num_nonnulls(source_id, document_asset_id, evidence_url) >= 1" in MIGRATION


def test_rls_read_predicate_uses_is_admin_not_profiles_is_admin():
    assert "public.is_admin(auth.uid())" in MIGRATION
    # No policy predicate references the deprecated profiles.is_admin flag
    # (migration comments mentioning "NOT profiles.is_admin" for context are
    # fine; an actual `p.is_admin = true` predicate clause is not).
    assert "p.is_admin = true" not in MIGRATION
    assert "reviewer_status in ('reviewed', 'locked')" in MIGRATION


def test_evidence_has_no_authenticated_policy():
    # Mirrors 216's posture: evidence access is service-role only, no
    # authenticated grant/policy exists for it at all.
    assert "grant select, insert, update, delete on public.exam_candidate_count_evidence to service_role" in MIGRATION
    assert "create policy" not in MIGRATION[
        MIGRATION.index("alter table public.exam_candidate_count_evidence enable row level security"):
        MIGRATION.index("h. lifecycle rpcs")
    ]


def test_promotion_gate_compares_claim_value_to_current_parent():
    assert "(e.claim_value ->> 'count_value')::numeric = v_row.count_value" in MIGRATION
    assert "e.evidence_kind <> 'reviewed_analysis'" in MIGRATION


def test_promotion_gate_enforces_full_source_trust_predicate():
    # checkpost P1-5: source_id IS NULL is no longer treated as trusted. An
    # inner JOIN drops null/dangling sources, and url-or-doc is required.
    assert "join public.source_registry sr on sr.id = e.source_id" in MIGRATION
    assert "sr.is_active and sr.is_verified and not sr.discovery_only" in MIGRATION
    assert "sr.source_type <> 'aggregator'" in MIGRATION
    assert "e.evidence_url is not null or e.document_asset_id is not null" in MIGRATION
    # The old "source_id is null OR trusted" escape hatch is gone.
    assert "e.source_id is null or (sr.is_active" not in MIGRATION


def test_promotion_gate_guards_claim_value_shape_before_cast():
    # checkpost P1-5: a jsonb_typeof number guard precedes the numeric cast so
    # a malformed direct insert fails the predicate instead of raising.
    assert "jsonb_typeof(e.claim_value -> 'count_value') = 'number'" in MIGRATION


def test_scope_trigger_requires_exact_cycle_match():
    # checkpost P1-3: the phase must belong to the same exam AND the same
    # cycle. The NULL-cycle wildcard is removed.
    assert "p.exam_cycle_id = new.exam_cycle_id" in MIGRATION
    assert "p.exam_cycle_id is null or p.exam_cycle_id = new.exam_cycle_id" not in MIGRATION


def test_lineage_trigger_enforces_scope_and_version_monotonicity():
    # checkpost P1-4: a superseding revision must share the full scope/category
    # and version_no = parent.version_no + 1, enforced by a trigger (a CHECK
    # cannot express a cross-row invariant).
    assert "_ecc_check_lineage" in MIGRATION
    assert "trg_ecc_check_lineage" in MIGRATION
    assert "version_no must be parent.version_no + 1" in MIGRATION
    assert "v_parent.reservation_category_id is distinct from new.reservation_category_id" in MIGRATION


def test_od6_backfill_decision_is_zero_rows_with_fail_closed_evidence():
    assert "0 rows migrated from exam_competition_metrics.applicant_count" in MIGRATION
    assert "zero evidence trail exists" in MIGRATION
    # checkpost P1-6: Section I now carries executable, fail-closed evidence
    # (RAISE-on-mismatch), not a prose-only notice.
    section_i = MIGRATION[MIGRATION.index("od-6 option b backfill decision: no rows migrated (documented judgment"):MIGRATION.rindex("commit;")]
    # No bulk conversion: a superseding INSERT..SELECT from the legacy table
    # into exam_candidate_counts must not exist.
    assert "insert into public.exam_candidate_counts (\n" not in section_i
    assert "insert into public.exam_candidate_counts\n" not in section_i
    # Executable fail-closed assertions are present:
    assert "raise exception 'j3 pr2 §i (od-6): expected 0 converted rows" in section_i
    assert "zero-loss accounting failed" in section_i
    assert "applicant_count was mutated" in section_i
    assert "competition_pressure_score changed for representative row" in section_i
    assert "v_pre_count" in section_i and "v_converted" in section_i


def test_reopen_for_edit_never_mutates_published_row_in_place():
    assert "cms_reopen_candidate_count_for_edit" in MIGRATION
    assert "not_published: only a reviewed/locked row can be reopened for edit" in MIGRATION


def test_transition_matrix_matches_competition_metric_lifecycle():
    assert "v_row.reviewer_status = 'reviewed'        and p_new_status = 'locked')" in MIGRATION
    assert "v_row.reviewer_status = 'locked'          and p_new_status = 'reviewed')" in MIGRATION
