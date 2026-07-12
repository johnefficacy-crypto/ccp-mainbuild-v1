"""Schema-contract tests for migration 242 (Lane R §6 identity seed).

Repo convention (see test_j3_applied_vs_appeared_migration.py): no live-DB
migration harness in CI, so these assert against the migration SQL text. The
behavioural apply + idempotency is pinned by the committed regression
app/supabase/tests/regression_242_financial_regulatory_identity_seed.sql
(validated on ephemeral PG16).
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / ".." / "supabase" / "migrations" / "242_financial_regulatory_family_identity_seed.sql"
).read_text().lower()


def test_seeds_sector_tagged_families_idempotently():
    for slug in ("nabard", "irdai", "pfrda", "ifsca", "sidbi", "nhb", "exim", "nabfid"):
        assert f"'{slug}'" in MIGRATION
    assert "'sector', 'financial-regulatory'" in MIGRATION
    # Merge, not clobber: existing rbi/sebi metadata is preserved.
    assert "on conflict (slug) do update" in MIGRATION
    assert "set metadata = public.exam_families.metadata || excluded.metadata" in MIGRATION


def test_seeds_core_exams_and_streams():
    for slug in ("nabard-grade-a", "irdai-am", "pfrda-grade-a", "ifsca-grade-a", "sidbi-grade-a"):
        assert f"'{slug}'" in MIGRATION
    # RBI/SEBI streams seeded in full.
    for key in ("'depr'", "'dsim'", "'official-language'", "'engineering'"):
        assert key in MIGRATION
    assert "insert into public.exam_streams" in MIGRATION
    assert "on conflict (exam_id, stream_key) do nothing" in MIGRATION
    assert "on conflict (slug) do nothing" in MIGRATION


def test_nothing_verified_and_ifsca_blocked():
    # Governance: nothing aspirant-verified; IFSCA blocked on its PDF.
    assert "'provenance', 'draft'" in MIGRATION
    assert "'verified', false" in MIGRATION
    assert "blocked_on_advertisement_pdf" in MIGRATION


def test_no_cycle_or_eligibility_or_notification_data_seeded():
    # Identity only — cycles/availability/eligibility are per-cycle operator work.
    assert "exam_cycles" not in MIGRATION
    assert "exam_cycle_streams" not in MIGRATION
    assert "exam_eligibility_rules" not in MIGRATION
    assert "exam_phases" not in MIGRATION


def test_entity_canonicity_exam_not_recruitment():
    assert "references public.recruitments" not in MIGRATION
    assert "recruitment_id" not in MIGRATION


def test_committed_behavioral_regression_exists():
    reg = (
        Path(__file__).resolve().parents[1]
        / ".." / "supabase" / "tests" / "regression_242_financial_regulatory_identity_seed.sql"
    )
    body = reg.read_text().lower()
    for marker in ("financial-regulatory families tagged", "without clobbering identity", "all rg242 checks complete"):
        assert marker in body
