"""B-PR1: descriptive-answer schema foundation — migration contract.

Pure file-content assertions (no DB) so the check runs in CI without
Supabase credentials.  It pins the two forward migrations that:

  * 176 — extend mock_question_type with descriptive/essay/precis/letter.
  * 177 — add the additive descriptive columns to mock_attempt_responses.

The live-schema equivalents are exercised by
app/supabase/checks/mock_descriptive_answer_schema.sql against a real DB.
"""
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parents[4] / "app" / "supabase" / "migrations"

_ENUM_MIGRATION = _MIGRATIONS / "176_mock_question_type_descriptive_values.sql"
_COLUMNS_MIGRATION = _MIGRATIONS / "177_mock_attempt_responses_descriptive_columns.sql"


def _executable_sql(path: Path) -> str:
    """Lowercased migration text with ``--`` comment lines stripped.

    Structural assertions (no DO block, no table ALTERs, …) must look at the
    statements actually run, not at prose in the header comment.
    """
    lines = [
        line for line in path.read_text().splitlines()
        if not line.lstrip().startswith("--")
    ]
    return "\n".join(lines).lower()


def test_enum_migration_adds_descriptive_values_only():
    sql = _executable_sql(_ENUM_MIGRATION)

    for value in ("descriptive", "essay", "precis", "letter"):
        assert (
            f"add value if not exists '{value}'" in sql
        ), f"missing enum add for {value}"

    # Forced strategy: enum ADD VALUE only — no table ALTERs, no DO/BEGIN
    # wrapper, and no reference to the new values in the same migration.
    assert "alter table" not in sql
    assert "do $$" not in sql
    assert "begin" not in sql


def test_columns_migration_is_additive_and_safe():
    sql = _executable_sql(_COLUMNS_MIGRATION)

    # All columns are added idempotently and never reference the new enum
    # values (descriptive columns are type-agnostic).
    assert "add column if not exists answer_text       text" in sql
    assert "add column if not exists word_count        int" in sql
    assert (
        "add column if not exists autosave_snapshot jsonb not null default '{}'::jsonb"
        in sql
    )
    assert (
        "add column if not exists evaluation_status text  not null default 'not_required'"
        in sql
    )
    assert (
        "add column if not exists rubric_score      jsonb not null default '{}'::jsonb"
        in sql
    )

    # Constraints: non-negative/NULL word count + the evaluation lifecycle gate.
    assert "check (word_count is null or word_count >= 0)" in sql
    for status in (
        "not_required",
        "pending_evaluation",
        "in_review",
        "completed",
    ):
        assert f"'{status}'" in sql

    # Out of scope for this PR — guard against scope creep.
    assert "mock_answer_assets" not in sql
    assert "mock_answer_evaluations" not in sql
    assert "create index" not in sql
