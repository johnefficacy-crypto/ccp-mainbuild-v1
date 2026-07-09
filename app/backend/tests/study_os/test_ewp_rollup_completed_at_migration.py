"""Migration 238 — session `completed_at` written by the rollup.

`public.writing_sessions` has carried `submitted_at` / `completed_at` since the
schema migration (205:206-207), but the authoritative rollup
`ewp_private.ewp_apply_session_rollup` (migration 207) only ever wrote `status`
+ `evaluation_outcome`. Every runtime write path funnels through that rollup, so
a session could reach `status='completed'` with `completed_at` still NULL — seen
live. Migration 238 CREATE OR REPLACEs the rollup to maintain the invariant
`completed_at IS NOT NULL  <=>  status='completed'` (monotonic: an existing
stamp is preserved on a completed->completed re-roll; cleared on a transition
out of completed such as a learning-mode reopen).

Two layers:
  * text assertions (no DB) — prove 238 is a CREATE OR REPLACE that sets
    completed_at, and that immutable migration 207 was NOT edited;
  * pg behaviour (gated on EWP_PG_DSN + psql, like
    test_writing_rpcs_behaviour.py) — drive real transitions and assert the
    stamp is set / cleared / preserved.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_MIG_DIR = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
_M205 = _MIG_DIR / "205_english_writing_practice_schema.sql"
_M207 = _MIG_DIR / "207_english_writing_practice_rpcs.sql"
_M238 = _MIG_DIR / "238_ewp_rollup_completed_at.sql"


# --------------------------------------------------------------------------- #
# text assertions (no DB)
# --------------------------------------------------------------------------- #
def test_migration_is_a_live_sql_file():
    assert _M238.exists(), f"expected the landed migration SQL at {_M238}"
    assert _MIG_DIR in _M238.parents and _M238.name.endswith(".sql")


def test_replaces_rollup_and_writes_completed_at():
    sql = _M238.read_text()
    assert "CREATE OR REPLACE FUNCTION ewp_private.ewp_apply_session_rollup(p_session uuid)" in sql
    start = sql.index("CREATE OR REPLACE FUNCTION ewp_private.ewp_apply_session_rollup(")
    body = sql[start:]
    # Into completed -> COALESCE(existing, now()); out of completed -> NULL.
    assert "COALESCE(v_cur_completed_at, now())" in body
    assert "completed_at = v_new_completed_at" in body
    # The no-op guard must also gate on completed_at, or a set/clear could be skipped.
    assert "completed_at IS DISTINCT FROM v_new_completed_at" in body
    assert "pg_notify('pgrst'" in sql  # PostgREST schema-cache reload


def test_immutable_207_rollup_left_unpatched():
    """Migrations are immutable once merged (CLAUDE.md): 207 stays as landed and
    its rollup UPDATE must remain the status+outcome-only form. The fix is a new
    CREATE OR REPLACE, never an edit to 207."""
    sql = _M207.read_text()
    start = sql.index("CREATE OR REPLACE FUNCTION ewp_private.ewp_apply_session_rollup(")
    end = sql.index("$$;", start)
    body = sql[start:end]
    assert "completed_at" not in body, "migration 207 must not have been edited"


# --------------------------------------------------------------------------- #
# pg behaviour (gated)
# --------------------------------------------------------------------------- #
_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")

pg = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)

_A = "00000000-0000-0000-0000-0000000000aa"   # owner
_PROMPT = "00000000-0000-0000-0000-0000000000d1"

_BOOTSTRAP = r"""
DO $$ BEGIN CREATE ROLE authenticated LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE service_role LOGIN BYPASSRLS; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE anon LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA public TO authenticated, service_role, anon;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $fn$
  SELECT NULLIF(current_setting('ewp.uid', true), '')::uuid $fn$;
CREATE TABLE IF NOT EXISTS public.profiles (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exams (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_cycles (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_phases (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.document_assets (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.study_tasks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, task_type text);
CREATE TABLE IF NOT EXISTS public.subjects (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), slug text NOT NULL UNIQUE, name text NOT NULL, subject_group text, default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS public.topics (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), subject_id uuid NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE, parent_topic_id uuid REFERENCES public.topics(id) ON DELETE CASCADE, slug text NOT NULL, name text NOT NULL, level text NOT NULL DEFAULT 'topic' CHECK (level IN ('topic','microtopic','concept')), default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(subject_id, parent_topic_id, slug));
"""

_FIXTURES = f"""
INSERT INTO exams(id) VALUES ('00000000-0000-0000-0000-0000000000e1') ON CONFLICT DO NOTHING;
INSERT INTO profiles(id) VALUES ('{_A}') ON CONFLICT DO NOTHING;
INSERT INTO writing_prompts(id,exam_id,subject_id,topic_id,exercise_type,prompt_text,difficulty_level,reviewer_status,is_active,required_sentence_count)
  SELECT '{_PROMPT}','00000000-0000-0000-0000-0000000000e1',
         (SELECT id FROM subjects WHERE slug='english-language'),
         (SELECT id FROM topics WHERE slug='grammar'),'sentence_construction','write',1,'verified',true,2
  WHERE NOT EXISTS (SELECT 1 FROM writing_prompts WHERE id='{_PROMPT}');
"""


def _psql(sql: str, *, expect_ok: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
        capture_output=True, text=True,
    )
    if expect_ok:
        assert proc.returncode == 0, f"unexpected failure:\n{proc.stderr}"
    else:
        assert proc.returncode != 0, f"expected failure but succeeded:\n{proc.stdout}"
    return proc


def _psql_file(path: Path) -> None:
    proc = subprocess.run(
        [_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"failed applying {path.name}:\n{proc.stderr}"


def _scalar(sql: str) -> str:
    proc = subprocess.run(
        [_PSQL, _DSN, "-t", "-A", "-X", "-c", sql],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


@pytest.fixture(scope="module", autouse=True)
def _apply():
    if not (_DSN and _PSQL):
        yield
        return
    _psql(_BOOTSTRAP)
    _psql_file(_M205)
    _psql_file(_M207)
    _psql_file(_M238)
    _psql_file(_M238)  # idempotent re-apply
    _psql(_FIXTURES)
    yield


def _create(units: int = 1) -> str:
    return _scalar(
        f"SELECT (ewp_create_writing_session('{_A}','{_PROMPT}',NULL,'learning',1,'immediate',"
        f"NULL,{units},NULL,'{{\"schema_version\":1}}'::jsonb))->>'id'"
    )


def _submit(sid: str, unit: int, text: str, ch: str, expected: int) -> None:
    _psql(
        f"SELECT ewp_submit_writing_unit('{_A}','{sid}',{unit},'{text}',{len(text.split())},"
        f"{len(text.split())},'{ch}',{expected},'{{}}'::jsonb,'det-v1')"
    )


def _drive_to_completed(sid: str) -> tuple[str, str]:
    """Terminalise the single unit's evaluation + write a passing coverage row,
    then finalize. Returns (unit_id, latest_version_id)."""
    unit = _scalar(f"SELECT id FROM writing_session_units WHERE session_id='{sid}' AND unit_number=1")
    ver = _scalar(f"SELECT id FROM writing_unit_versions WHERE unit_id='{unit}'")
    ev = _scalar(f"SELECT id FROM writing_evaluations WHERE unit_version_id='{ver}'")
    vsh = _scalar(f"SELECT ewp_private.ewp_version_set_hash('{sid}')")
    _psql(
        f"UPDATE writing_evaluations SET overall_status='completed', language_status='completed' WHERE id='{ev}';"
        f"UPDATE writing_session_units SET status='ready' WHERE id='{unit}';"
        f"INSERT INTO writing_session_checks(session_id,check_type,version_set_hash,passed,details,checker_version) "
        f"VALUES ('{sid}','required_word_coverage','{vsh}',true,'{{}}'::jsonb,'coverage-v1');"
    )
    out = _scalar(f"SELECT ewp_finalize_writing_session('{_A}','{sid}')")
    assert '"status": "completed"' in out, out
    return unit, ver


@pg
def test_completed_transition_stamps_completed_at():
    """active/evaluation_pending -> completed sets completed_at."""
    sid = _create(units=1)
    _submit(sid, 1, "The cat sat.", "a" * 64, 1)
    # before completion: session not completed, completed_at NULL.
    assert _scalar(f"SELECT completed_at IS NULL FROM writing_sessions WHERE id='{sid}'") == "t"
    _drive_to_completed(sid)
    assert _scalar(f"SELECT status FROM writing_sessions WHERE id='{sid}'") == "completed"
    assert _scalar(f"SELECT completed_at IS NOT NULL FROM writing_sessions WHERE id='{sid}'") == "t"


@pg
def test_reopen_clears_completed_at():
    """completed -> active (learning-mode reopen) clears completed_at back to NULL."""
    sid = _create(units=1)
    _submit(sid, 1, "The cat sat.", "a" * 64, 1)
    unit, ver = _drive_to_completed(sid)
    assert _scalar(f"SELECT completed_at IS NOT NULL FROM writing_sessions WHERE id='{sid}'") == "t"
    # reopen the ready unit -> session rolls back to active; stamp cleared.
    _scalar(f"SELECT ewp_reopen_writing_unit('{_A}','{sid}','{unit}','{ver}')")
    assert _scalar(f"SELECT status FROM writing_sessions WHERE id='{sid}'") == "active"
    assert _scalar(f"SELECT completed_at IS NULL FROM writing_sessions WHERE id='{sid}'") == "t"


@pg
def test_completed_reroll_preserves_completed_at():
    """completed -> completed preserves the existing completed_at (monotonic:
    COALESCE keeps the first stamp, now() is not re-applied on re-roll)."""
    sid = _create(units=1)
    _submit(sid, 1, "The cat sat.", "a" * 64, 1)
    _drive_to_completed(sid)
    # Pin a deterministic sentinel so a re-applied now() would be detectable.
    sentinel = "2020-01-01 00:00:00+00"
    _psql(f"UPDATE writing_sessions SET completed_at='{sentinel}' WHERE id='{sid}'")
    # Re-run the finalizer while still completed: status stays completed, so the
    # stamp must be preserved (COALESCE), never overwritten with now().
    out = _scalar(f"SELECT ewp_finalize_writing_session('{_A}','{sid}')")
    assert '"status": "completed"' in out, out
    assert _scalar(f"SELECT completed_at FROM writing_sessions WHERE id='{sid}'").startswith("2020-01-01")
