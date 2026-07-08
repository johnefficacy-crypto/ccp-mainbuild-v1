"""Text-assertion checks on migration 236 (no live DB).

Every prior invocation of public.ewp_complete_language_evaluation() (migration
209, the RPC evaluation_worker.run_worker_pass() calls to finalize a language
evaluation) failed with HTTP 400 / postgrest error {"message": "DELETE
requires a WHERE clause", "code": "21000"}, confirmed against a real e2e CI
run's job log. Root cause: Supabase's Postgres image runs the function's
owning role (postgres) with the pg_safeupdate extension active, which rejects
ANY unqualified UPDATE/DELETE statement — including one issued from inside a
SECURITY DEFINER plpgsql function body, not only raw client SQL. Migration
209's function resets its per-call temp table with a bare
`DELETE FROM _ewp_regressions;`, which pg_safeupdate blocks every time.

Migration 236 CREATE OR REPLACEs the identical function with that one
statement changed to `DELETE FROM _ewp_regressions WHERE true;` — same rows
deleted (all of them; the temp table is ON COMMIT DROP and scoped to a single
call), but syntactically satisfies pg_safeupdate.

These assertions prove the SQL is structured correctly without executing it,
mirroring the repo's text-assertion migration-test convention (e.g.
test_pyq_question_stimulus_review_cascade_migration.py).
"""
from __future__ import annotations

import re
from pathlib import Path

_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "supabase"
    / "migrations"
    / "236_ewp_complete_evaluation_safeupdate_fix.sql"
)
_ORIGINAL = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "supabase"
    / "migrations"
    / "209_english_writing_practice_evaluator.sql"
)


def _sql_text() -> str:
    assert _MIGRATION.exists(), (
        f"expected the landed migration SQL at {_MIGRATION} — "
        "the pg_safeupdate fix must ship this migration under app/supabase/migrations/"
    )
    return _MIGRATION.read_text()


def test_migration_is_a_live_sql_file():
    live_migrations_dir = (
        Path(__file__).resolve().parents[3] / "supabase" / "migrations"
    )
    assert live_migrations_dir in _MIGRATION.parents
    assert _MIGRATION.name.endswith(".sql")


def test_replaces_ewp_complete_language_evaluation_with_same_signature():
    sql = _sql_text()
    assert "CREATE OR REPLACE FUNCTION public.ewp_complete_language_evaluation(" in sql
    # Same nine parameters, same order, as migration 209 — CREATE OR REPLACE
    # on a matching signature preserves existing grants; no caller changes.
    for param in (
        "p_job_id uuid", "p_claim_token uuid", "p_evaluator_version text",
        "p_issues jsonb", "p_language_result jsonb", "p_dimension_scores jsonb",
        "p_needs_human_review boolean", "p_mastery_flag text",
        "p_mastery_idempotency_key text",
    ):
        assert param in sql, f"signature parameter {param!r} missing or reordered"


def test_regressions_temp_table_delete_has_where_clause():
    sql = _sql_text()
    start = sql.index("CREATE OR REPLACE FUNCTION public.ewp_complete_language_evaluation(")
    body = sql[start:]
    # The exact bug: a bare DELETE with no WHERE, rejected by pg_safeupdate.
    # (Scoped to the function body — the header comment quotes the buggy form
    # in backticks for documentation and must not trip this assertion.)
    assert re.search(r"DELETE\s+FROM\s+_ewp_regressions\s*;", body) is None, (
        "an unqualified DELETE FROM _ewp_regressions reintroduces the "
        "pg_safeupdate 400 that broke every writing-practice evaluation completion"
    )
    assert "DELETE FROM _ewp_regressions WHERE true;" in body


def test_original_migration_209_still_has_the_bug_unpatched():
    """Migrations are immutable once merged (CLAUDE.md) — 209 must be left as
    landed; this fix must be a new CREATE OR REPLACE migration, not an edit."""
    original = _ORIGINAL.read_text()
    assert "DELETE FROM _ewp_regressions;" in original


def test_function_body_otherwise_matches_the_original_verbatim():
    """Prove this is a surgical one-statement fix, not a broader rewrite: strip
    the fixed DELETE line from both and diff the remaining function bodies."""
    def _extract_body(sql: str) -> str:
        start = sql.index("CREATE OR REPLACE FUNCTION public.ewp_complete_language_evaluation(")
        end = sql.index("$$;", start) + len("$$;")
        return sql[start:end]

    original_body = _extract_body(_ORIGINAL.read_text())
    fixed_body = _extract_body(_sql_text())

    # Normalize the one intentionally-changed statement (with its new comment)
    # back to the original bare form so the remainder can be compared exactly.
    normalized = re.sub(
        r"\s*-- WHERE true.*?\n(\s*)DELETE FROM _ewp_regressions WHERE true;",
        r"\n\1DELETE FROM _ewp_regressions;",
        fixed_body,
        count=1,
        flags=re.DOTALL,
    )
    assert normalized == original_body, (
        "migration 236's function body diverges from 209 beyond the intended "
        "DELETE ... WHERE true fix — re-check for accidental drift"
    )


def test_reloads_postgrest_schema_cache():
    assert "notify pgrst, 'reload schema';" in _sql_text()
