"""Text-contract test for migration 231 (PYQ v2 PR-5/6 slice B).

Follows the repo's documented convention (no live-DB migration harness): assert
against the migration SQL text. Migration 174 (which first constrained
mock_generated_blueprints.source) is MERGED + IMMUTABLE — practice sources are
admitted only via the forward migration 231.
"""
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
MIGRATION = (_MIGRATIONS / "231_mock_practice_blueprint_source.sql").read_text().lower()
MIG_174 = (_MIGRATIONS / "174_mock_generated_blueprints.sql").read_text().lower()


def test_extends_source_check_with_practice_modes():
    assert "drop constraint if exists mock_generated_blueprints_source_check" in MIGRATION
    assert "add constraint mock_generated_blueprints_source_check" in MIGRATION
    for src in ("pyq_practice_paper", "pyq_practice_section", "pyq_practice_topic"):
        assert src in MIGRATION


def test_preserves_the_prior_source_values():
    assert "'exam_realistic'" in MIGRATION
    assert "'personalized'" in MIGRATION


def test_reloads_schema_cache():
    assert "pg_notify('pgrst', 'reload schema')" in MIGRATION


def test_174_remains_immutable_without_practice_sources():
    # the practice sources must be forward-only, never edited into 174.
    assert "pyq_practice_paper" not in MIG_174
