"""Sanity checks on the landed migration SQL for J3 PR 4.

The migration lives at app/supabase/migrations/217_evidence_derived_coverage.sql
(landed after J3 PR 1 / migration 216 and its follow-up fix #869, ahead of
J3 PR 2, per explicit operator direction — see
docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md). These tests
assert on the SQL TEXT directly (no live DB) to prove the fail-closed
duplicate-detection DO block and the two required schema changes are present
and structured correctly, per
docs/status/J3-OD-Resolutions-Locked-2026-07-02.md §5.3/§5.5.
"""
from __future__ import annotations

from pathlib import Path

_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "supabase"
    / "migrations"
    / "217_evidence_derived_coverage.sql"
)


def _sql_text() -> str:
    assert _MIGRATION.exists(), (
        f"expected the landed migration SQL at {_MIGRATION} — "
        "J3 PR4 must ship this migration under app/supabase/migrations/"
    )
    return _MIGRATION.read_text()


def test_migration_is_under_live_migrations_dir():
    live_migrations_dir = (
        Path(__file__).resolve().parents[3] / "supabase" / "migrations"
    )
    assert live_migrations_dir in _MIGRATION.parents


def test_migration_is_a_live_sql_file():
    """The file must be picked up by a `*.sql` migration runner glob."""
    assert _MIGRATION.name.endswith(".sql")
    assert not _MIGRATION.name.endswith(".sql.pending")


def test_migration_extends_source_basis_check():
    sql = _sql_text()
    assert "exam_topic_coverage_source_basis_check" in sql
    assert "'evidence_derived'" in sql
    # All pre-existing basis values must be preserved (additive, not a
    # breaking rename) — losing one would silently invalidate existing rows.
    for basis in (
        "official_syllabus", "pyq_analysis", "admin_review",
        "hybrid", "manual", "model_generated",
    ):
        assert f"'{basis}'" in sql


def test_migration_adds_exam_wide_partial_unique_index():
    sql = _sql_text().lower()
    assert "create unique index" in sql
    assert "exam_topic_coverage_exam_wide_uq" in sql
    assert "exam_cycle_id is null and exam_phase_id is null" in sql
    assert "(exam_id, topic_id)" in sql


def test_migration_has_fail_closed_duplicate_do_block():
    sql = _sql_text().lower()
    assert "do $$" in sql
    assert "raise exception" in sql
    # The fail-closed DO block must run BEFORE the index creation, and must
    # detect duplicates by grouping on the exact exam-wide scope.
    do_block_pos = sql.index("do $$")
    index_pos = sql.index("create unique index")
    assert do_block_pos < index_pos, "duplicate detection must run before the index is created"
    assert "having count(*) > 1" in sql
    assert "group by exam_id, topic_id" in sql


def test_migration_never_auto_resolves_duplicates():
    """The migration must not contain any auto-keep-latest logic — duplicate
    resolution is manual/operator-only per §5.3."""
    sql = _sql_text().lower()
    assert "delete from public.exam_topic_coverage" not in sql
    assert "order by reviewed_at desc limit 1" not in sql
    assert "runbook" in sql  # operator runbook documented in-file
