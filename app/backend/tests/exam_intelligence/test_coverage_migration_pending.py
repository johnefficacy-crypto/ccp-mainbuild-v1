"""Sanity checks on the HELD-OUT migration SQL for J3 PR 4.

The real migration SQL is intentionally NOT placed under
app/supabase/migrations/ yet (coordination: migration slot lands after PR 2,
per docs/status/J3-Implementation-Checklist-2026-07-02.md). It is held as a
`.sql.pending` file OUTSIDE app/supabase/migrations/ entirely (P1-5 fix,
checkpost: the file used to live physically inside
app/supabase/migrations/, which contradicted "held outside" even though the
`.pending` extension meant no `*.sql` migration-runner glob picked it up —
see .github/workflows/migration-numbers.yml and the e2e Supabase-apply step,
both of which only ever match `app/supabase/migrations/*.sql`). It now lives
under docs/status/j3-pr4-pending-migration/ alongside the other J3 PR4
status docs. These tests assert on the SQL TEXT directly (no live DB) to
prove the fail-closed duplicate-detection DO block and the two required
schema changes are present and structured correctly, per
docs/status/J3-OD-Resolutions-Locked-2026-07-02.md §5.3/§5.5.
"""
from __future__ import annotations

from pathlib import Path

_PENDING_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "status"
    / "j3-pr4-pending-migration"
    / "215_PENDING_evidence_derived_coverage.sql.pending"
)


def _sql_text() -> str:
    assert _PENDING_MIGRATION.exists(), (
        f"expected held-out migration SQL at {_PENDING_MIGRATION} — "
        "J3 PR4 must include the migration content for review even though "
        "it is not placed in app/supabase/migrations/ yet"
    )
    return _PENDING_MIGRATION.read_text()


def test_pending_migration_not_under_live_migrations_dir():
    """P1-5: the file must be physically OUTSIDE app/supabase/migrations/,
    not merely excluded from it by a `.pending` extension."""
    live_migrations_dir = (
        Path(__file__).resolve().parents[3] / "supabase" / "migrations"
    )
    assert live_migrations_dir not in _PENDING_MIGRATION.parents


def test_pending_migration_not_a_live_sql_file():
    """The file must NOT be picked up by a `*.sql` migration runner glob."""
    assert not _PENDING_MIGRATION.name.endswith(".sql")
    assert _PENDING_MIGRATION.name.endswith(".sql.pending")


def test_pending_migration_extends_source_basis_check():
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


def test_pending_migration_adds_exam_wide_partial_unique_index():
    sql = _sql_text().lower()
    assert "create unique index" in sql
    assert "exam_topic_coverage_exam_wide_uq" in sql
    assert "exam_cycle_id is null and exam_phase_id is null" in sql
    assert "(exam_id, topic_id)" in sql


def test_pending_migration_has_fail_closed_duplicate_do_block():
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


def test_pending_migration_never_auto_resolves_duplicates():
    """The migration must not contain any auto-keep-latest logic — duplicate
    resolution is manual/operator-only per §5.3."""
    sql = _sql_text().lower()
    assert "delete from public.exam_topic_coverage" not in sql
    assert "order by reviewed_at desc limit 1" not in sql
    assert "runbook" in sql  # operator runbook documented in-file
