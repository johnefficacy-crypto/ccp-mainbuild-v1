"""Schema-contract tests for migration 242 (Lane R §6 identity seed).

Repo convention (see test_j3_applied_vs_appeared_migration.py): no live-DB
migration harness in CI, so these assert against the migration SQL text. The
behavioural apply / convergence / idempotency is pinned by the committed
regression app/supabase/tests/regression_242_financial_regulatory_identity_seed.sql
(validated on ephemeral PG16).

Reworked per the PR #962 checkpost to encode the CANONICAL model, not the
earlier per-body-family shape.
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / ".." / "supabase" / "migrations" / "242_financial_regulatory_family_identity_seed.sql"
).read_text().lower()


def test_single_umbrella_family_not_per_body():
    # Exactly one umbrella family; portfolio exams point at it via exam_family_id
    # (the field applicability.py resolves). No per-body family inserts.
    assert "'financial-regulatory'," in MIGRATION
    assert "financial regulatory & development institutions" in MIGRATION
    assert "join public.exam_families fam on fam.slug = 'financial-regulatory'" in MIGRATION
    # The rejected shape inserted a family row per body — must be gone.
    assert "('nabard', " not in MIGRATION
    assert "('irdai', " not in MIGRATION


def test_institution_dimension_via_organizations():
    assert "insert into public.organizations" in MIGRATION
    assert "conducting_organization_id = excluded.conducting_organization_id" in MIGRATION
    assert "join public.organizations org on org.name = v.org_name" in MIGRATION


def test_canonical_lane_fields_not_metadata():
    # management_mode / cadence are set as columns, not just metadata.
    assert "management_mode = excluded.management_mode" in MIGRATION
    for mode in ("'core'", "'light'", "'index_only'"):
        assert mode in MIGRATION
    assert "cadence = coalesce(public.exams.cadence, excluded.cadence)" in MIGRATION


def test_draft_exams_hidden_and_convergent_upsert():
    # New drafts insert is_active=false; DO UPDATE converges family/org/lane but
    # never touches is_active (live rows keep their disposition).
    assert "'unknown', false, v.description" in MIGRATION  # is_active=false on insert
    assert "on conflict (slug) do update" in MIGRATION
    assert "exam_family_id = excluded.exam_family_id" in MIGRATION
    # is_active must NOT be in the DO UPDATE set.
    update_clause = MIGRATION.split("on conflict (slug) do update", 1)[1].split(";", 1)[0]
    assert "is_active" not in update_clause


def test_coverage_complete_index_only_and_nabard_b_and_sebi_streams():
    for slug in ("nabard-grade-b", "nps-trust-officer", "epfo-apfc", "ecgc-po", "ibbi-grade-a"):
        assert f"'{slug}'" in MIGRATION
    # SEBI engineering split into electrical + civil.
    assert "'electrical-engineering'" in MIGRATION
    assert "'civil-engineering'" in MIGRATION
    # Streams upsert is convergent too.
    assert "on conflict (exam_id, stream_key) do update" in MIGRATION


def test_governance_draft_and_blocked_flags():
    assert '"provenance":"draft"' in MIGRATION
    assert '"verified":false' in MIGRATION
    assert "blocked_on_advertisement_pdf" in MIGRATION
    # No cycles / eligibility / phases seeded here.
    assert "exam_cycles" not in MIGRATION
    assert "exam_eligibility_rules" not in MIGRATION
    assert "exam_phases" not in MIGRATION


def test_entity_canonicity_exam_not_recruitment():
    assert "references public.recruitments" not in MIGRATION
    assert "recruitment_id" not in MIGRATION


def test_committed_behavioral_regression_null_safe_and_convergent():
    reg = (
        Path(__file__).resolve().parents[1]
        / ".." / "supabase" / "tests" / "regression_242_financial_regulatory_identity_seed.sql"
    )
    body = reg.read_text().lower()
    for marker in (
        "single umbrella family",
        "reparented onto the umbrella",
        "conducting_organization_id",
        "draft exams is_active=false",
        "index-only identities + nabard grade b",
        "converged (family + lane normalized)",
    ):
        assert marker in body
    # NULL-safe verified check, not the flagged `<> 'false'`.
    assert "is distinct from 'false'" in body
