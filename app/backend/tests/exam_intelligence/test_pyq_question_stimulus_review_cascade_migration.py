"""Text-assertion checks on migration 226 (no live DB).

Migration 226 supersedes migration 162's update_pyq_question_review_atomic()
via CREATE OR REPLACE, keeping the same signature so the existing caller
(review_item) is unchanged, and extends the atomic question-review cascade to
the question<->stimulus ASSOCIATION rows (pyq_question_stimuli) — but NOT to
the shared stimulus CONTENT (pyq_stimuli), which is reviewed independently.

These assertions prove the SQL is structured correctly without executing it,
mirroring the repo's text-assertion migration-test convention
(e.g. test_coverage_migration.py).
"""
from __future__ import annotations

from pathlib import Path

_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "supabase"
    / "migrations"
    / "226_pyq_question_stimulus_review_cascade.sql"
)


def _sql_text() -> str:
    assert _MIGRATION.exists(), (
        f"expected the landed migration SQL at {_MIGRATION} — "
        "PYQ PR-3 must ship this migration under app/supabase/migrations/"
    )
    return _MIGRATION.read_text()


def test_migration_is_a_live_sql_file():
    live_migrations_dir = (
        Path(__file__).resolve().parents[3] / "supabase" / "migrations"
    )
    assert live_migrations_dir in _MIGRATION.parents
    assert _MIGRATION.name.endswith(".sql")
    assert not _MIGRATION.name.endswith(".sql.pending")


def test_create_or_replace_same_signature():
    sql = _sql_text().lower()
    assert "create or replace function public.update_pyq_question_review_atomic" in sql
    # Same signature as migration 162 so the existing caller stays unchanged.
    assert "p_question_id     uuid" in sql
    assert "p_reviewer_status text" in sql
    assert "p_reviewed_by     uuid" in sql
    assert "p_reviewed_at     timestamptz" in sql
    assert "returns jsonb" in sql


def test_cascades_to_question_stimuli_links_inside_guard():
    sql = _sql_text().lower()
    # The link cascade must live inside the verified/rejected/needs_correction
    # guard, after the pyq_options cascade — not fire on 'pending'.
    guard_pos = sql.index("if p_reviewer_status in ('verified', 'rejected', 'needs_correction') then")
    options_pos = sql.index("update public.pyq_options")
    links_pos = sql.index("update public.pyq_question_stimuli")
    end_if_pos = sql.rindex("end if")
    assert guard_pos < options_pos < links_pos < end_if_pos, (
        "link cascade must be inside the status guard, after the options cascade"
    )
    assert "where question_id = p_question_id" in sql


def test_does_not_touch_shared_stimulus_content():
    """Shared passage CONTENT (pyq_stimuli) is reviewed independently — the
    question-review RPC must never update pyq_stimuli."""
    sql = _sql_text()
    assert "update public.pyq_stimuli" not in sql.lower()


def test_returns_cascaded_link_count():
    sql = _sql_text().lower()
    assert "cascaded_link_count" in sql
    # Original return keys preserved.
    assert "cascaded_option_count" in sql
    assert "'question'" in sql
    assert "get diagnostics v_link_count = row_count" in sql


def test_preserves_security_definer_and_grant_pattern():
    sql = _sql_text().lower()
    assert "security definer" in sql
    assert "set search_path = public" in sql
    assert "revoke all on function public.update_pyq_question_review_atomic(uuid, text, uuid, timestamptz) from public" in sql
    assert "grant execute on function public.update_pyq_question_review_atomic(uuid, text, uuid, timestamptz) to service_role" in sql
    assert "pg_notify('pgrst', 'reload schema')" in sql


def test_does_not_edit_migration_162():
    """226 supersedes 162 via CREATE OR REPLACE — 162 must remain untouched."""
    m162 = (
        Path(__file__).resolve().parents[4]
        / "app" / "supabase" / "migrations" / "162_pyq_review_cascade_rpc.sql"
    )
    assert m162.exists()
    assert "cascaded_link_count" not in m162.read_text()
