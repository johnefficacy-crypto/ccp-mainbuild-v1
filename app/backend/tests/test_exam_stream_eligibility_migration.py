"""Schema-contract tests for migration 245 (Lane R §4 stream eligibility).

Repo convention (test_j3_applied_vs_appeared_migration.py): no live-DB migration
harness in CI, so these assert against the SQL text. Behaviour is pinned by the
committed regression app/supabase/tests/regression_245_exam_stream_eligibility.sql
(validated on ephemeral PG16).
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / ".." / "supabase" / "migrations" / "245_exam_stream_eligibility.sql"
).read_text().lower()


def test_baseline_gains_stream_dimension_and_rule_types():
    assert "add column if not exists stream_id uuid references public.exam_streams(id) on delete restrict" in MIGRATION
    assert "add column if not exists value_json jsonb" in MIGRATION
    for rt in ("'discipline'", "'min_percentage'", "'certification'",
               "'qualification_combination'", "'stream_availability'"):
        assert rt in MIGRATION
    # Category scope is NOT overloaded — the axis is a separate stream_id column.
    assert "'age_min', 'age_max', 'education_min_level', 'nationality', 'gender', 'attempts_max'" in MIGRATION
    # experience_min_years is cycle-only — NOT in the baseline enum, but IS on cycle.
    assert "'stream_availability'\n  ));" in MIGRATION            # baseline enum ends here
    assert "'stream_availability','experience_min_years'" in MIGRATION  # cycle enum


def test_qualification_combination_structurally_validated_and_fail_closed():
    # Structural validator (not just NOT NULL) enforced by a CHECK on both tables.
    assert "create or replace function public.is_valid_qualification_combination" in MIGRATION
    assert "rule_type <> 'qualification_combination'\n         or public.is_valid_qualification_combination(value_json)" in MIGRATION
    assert "value_json is not null)" not in MIGRATION  # the weak check is gone
    # Fail-closed: unsupported rule_types cannot be verified.
    assert "exam_eligibility_rules_verified_supported_check" in MIGRATION
    assert "reviewer_status <> 'verified' or rule_type in (" in MIGRATION


def test_parent_side_stream_move_guard_includes_eligibility_rules():
    # 242's guard omitted exam_eligibility_rules; 245 replaces the function so a
    # stream referenced only by a baseline rule can't be reassigned cross-exam.
    assert "create or replace function public._exam_streams_guard_exam_move()" in MIGRATION
    assert "from public.exam_eligibility_rules r where r.stream_id = old.id" in MIGRATION


def test_stream_aware_uniqueness_null_safe():
    # Old key dropped by definition lookup; new one is stream-aware + NULLS NOT DISTINCT.
    assert "pg_get_constraintdef(oid) ilike '%(exam_id, scope, rule_type)%'" in MIGRATION
    assert "exam_eligibility_rules_exam_stream_scope_type_uidx" in MIGRATION
    assert "on public.exam_eligibility_rules(exam_id, stream_id, scope, rule_type)" in MIGRATION
    assert "nulls not distinct" in MIGRATION


def test_baseline_cross_parent_trigger():
    assert "create or replace function public._exam_eligibility_rules_check_stream()" in MIGRATION
    assert "before insert or update on public.exam_eligibility_rules" in MIGRATION
    assert "for share" in MIGRATION
    assert "using errcode = 'p0422'" in MIGRATION


def test_cycle_eligibility_table_full_value_contract_and_restrict():
    assert "create table if not exists public.exam_cycle_stream_eligibility" in MIGRATION
    # Composite FK to the canonical (cycle, stream) pair — RESTRICT preserves the
    # reviewer/source audit trail (P1: no destructive cascade of reviewed rows).
    assert "foreign key (exam_cycle_id, stream_id)" in MIGRATION
    assert "references public.exam_cycle_streams(exam_cycle_id, stream_id) on delete restrict" in MIGRATION
    assert "on delete cascade" not in MIGRATION
    assert "unique (exam_cycle_id, stream_id, scope, rule_type)" in MIGRATION
    # Full value contract: age cut-off date semantics, experience, structured combo.
    assert "cutoff_date_basis" in MIGRATION
    assert "in ('cycle_notification','fixed_date')" in MIGRATION
    assert "cutoff_date date" in MIGRATION
    assert "'experience_min_years'" in MIGRATION
    assert "value_json jsonb" in MIGRATION
    assert "alter table public.exam_cycle_stream_eligibility enable row level security" in MIGRATION
    assert "exam_cycle_stream_eligibility_updated_at" in MIGRATION


def test_baseline_vs_cycle_separation_is_evergreen():
    # Baseline stays evergreen — no cycle column added to exam_eligibility_rules.
    assert "add column if not exists exam_cycle_id" not in MIGRATION
    assert "notify pgrst, 'reload schema';" in MIGRATION


def test_committed_behavioral_regression_exists():
    reg = (
        Path(__file__).resolve().parents[1]
        / ".." / "supabase" / "tests" / "regression_245_exam_stream_eligibility.sql"
    )
    body = reg.read_text().lower()
    for marker in (
        "common + stream-specific rule coexist",
        "new baseline rule_types incl qualification_combination accepted",
        "experience_min_years rejected on baseline",
        "new rule_type cannot be verified (fail-closed)",
        "structural check rejects malformed",
        "update move cross-exam stream",
        "exam reassign with dependent baseline rule",
        "cutoff + experience on a real pair",
        "cycle eligibility on a non-existent pair",
        "audit preserved",
    ):
        assert marker in body
