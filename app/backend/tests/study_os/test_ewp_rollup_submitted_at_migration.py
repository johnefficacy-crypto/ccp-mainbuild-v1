"""Migration 240 — session `submitted_at` written by the rollup (cleared-parallel).

`public.writing_sessions.submitted_at` has existed since the schema migration
(205:206) but no path ever wrote it; migration 238 wired `completed_at` and
deliberately left `submitted_at` alone. Migration 240 CREATE OR REPLACEs the
rollup to maintain the invariant

    submitted_at IS NOT NULL  <=>  status <> 'active'   (session past drafting)

parallel to `completed_at`: stamped once when the session leaves 'active' (all
units submitted; monotonic while past-drafting), cleared on a learning-mode
reopen that returns the session to 'active'.

Two layers:
  * text assertions (no DB) — prove 240 is a CREATE OR REPLACE that sets
    submitted_at with the cleared-parallel rule, and that immutable migrations
    207/238 were NOT edited;
  * pg behaviour (gated on EWP_PG_DSN + psql) — drive real transitions and assert
    the stamp is set / cleared / preserved.

The pg layer applies the **current** EWP chain that 240 actually lands after —
205 → 207 → 209 → 214 → 222 → 238 → 240 — NOT the historical 205→207 shape:
migration 214 drops the exam-scope columns from `writing_prompts` (so the fixture
is subject-scoped, no `exam_id`) and 222 replaces `ewp_create_writing_session`
(pinned `prompt_snapshot` + exam derivation). 209 is included because 222 also
CREATE OR REPLACEs `ewp_claim_evaluation_job` / `ewp_claim_mastery_outbox`, whose
bodies reference the evaluator/outbox tables 209 creates. This proves 240 works
against the real runtime function + table shape, not the pre-214 historical one.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

_MIG_DIR = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
_M205 = _MIG_DIR / "205_english_writing_practice_schema.sql"
_M207 = _MIG_DIR / "207_english_writing_practice_rpcs.sql"
_M209 = _MIG_DIR / "209_english_writing_practice_evaluator.sql"
_M214 = _MIG_DIR / "214_writing_prompt_content_scoping.sql"
_M222 = _MIG_DIR / "222_ewp_prompt_snapshot_and_exam_derivation.sql"
_M238 = _MIG_DIR / "238_ewp_rollup_completed_at.sql"
_M240 = _MIG_DIR / "240_ewp_rollup_submitted_at.sql"


# --------------------------------------------------------------------------- #
# text assertions (no DB)
# --------------------------------------------------------------------------- #
def test_migration_is_a_live_sql_file():
    assert _M240.exists(), f"expected the landed migration SQL at {_M240}"
    assert _MIG_DIR in _M240.parents and _M240.name.endswith(".sql")


def test_replaces_rollup_and_writes_submitted_at():
    sql = _M240.read_text()
    assert "CREATE OR REPLACE FUNCTION ewp_private.ewp_apply_session_rollup(p_session uuid)" in sql
    start = sql.index("CREATE OR REPLACE FUNCTION ewp_private.ewp_apply_session_rollup(")
    body = sql[start:]
    # Past-drafting -> COALESCE(existing, now()); back to active -> NULL.
    assert "COALESCE(v_cur_submitted_at, now())" in body
    assert "v_status <> 'active'" in body
    assert "submitted_at = v_new_submitted_at" in body
    # The no-op guard must also gate on submitted_at, or a set/clear could be skipped.
    assert "submitted_at IS DISTINCT FROM v_new_submitted_at" in body
    # completed_at handling from 238 must be carried forward unchanged (this is a
    # superset CREATE OR REPLACE, not a regression of 238's behaviour).
    assert "COALESCE(v_cur_completed_at, now())" in body
    assert "completed_at = v_new_completed_at" in body
    assert "pg_notify('pgrst'" in sql  # PostgREST schema-cache reload


def test_immutable_prior_rollups_left_unpatched():
    """Migrations are immutable once merged (CLAUDE.md): 207 and 238 stay as
    landed. 207's rollup must remain status+outcome-only; 238 must not mention
    submitted_at. The fix is a new CREATE OR REPLACE, never an edit."""
    body207 = _M207.read_text()
    start = body207.index("CREATE OR REPLACE FUNCTION ewp_private.ewp_apply_session_rollup(")
    end = body207.index("$$;", start)
    assert "completed_at" not in body207[start:end], "migration 207 must not have been edited"

    sql238 = _M238.read_text()
    start = sql238.index("CREATE OR REPLACE FUNCTION ewp_private.ewp_apply_session_rollup(")
    end = sql238.index("$$;", start)
    assert "submitted_at" not in sql238[start:end], "migration 238 must not have been edited"


# --------------------------------------------------------------------------- #
# pg behaviour (gated)
# --------------------------------------------------------------------------- #
_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")

pg = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)


def _swap_db(dsn: str, db: str) -> str:
    p = urlsplit(dsn)
    return urlunsplit((p.scheme, p.netloc, "/" + db, p.query, p.fragment))


# This test applies migration 214, which DROPs `writing_prompts.exam_id`. The CI
# backend job runs ALL pg tests in ONE pytest process against the shared `ewp_it`
# db, and the sibling EWP pg tests still insert the pre-214 `writing_prompts`
# shape — so mutating the shared db here would break them. We therefore run the
# whole current-chain apply in a DEDICATED, freshly-created db and never touch
# `ewp_it`. ``_RUN_DSN`` is what every psql helper targets; it points at the
# isolated db once the module fixture provisions it.
_OWN_DB = "ewp_submitted_at_it"
_ADMIN_DSN = _swap_db(_DSN, "postgres") if _DSN else None
_RUN_DSN = _DSN

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
CREATE TABLE IF NOT EXISTS public.exam_families (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exams (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_cycles (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_phases (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.document_assets (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.study_tasks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, task_type text, exam_id uuid, exam_phase_id uuid);
CREATE TABLE IF NOT EXISTS public.subjects (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), slug text NOT NULL UNIQUE, name text NOT NULL, subject_group text, default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS public.topics (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), subject_id uuid NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE, parent_topic_id uuid REFERENCES public.topics(id) ON DELETE CASCADE, slug text NOT NULL, name text NOT NULL, level text NOT NULL DEFAULT 'topic' CHECK (level IN ('topic','microtopic','concept')), default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(subject_id, parent_topic_id, slug));
"""

# Post-214 the prompt is SUBJECT-scoped — `writing_prompts` no longer has
# `exam_id` (migration 214 dropped it). The behaviour test creates ad-hoc
# sessions (`p_study_task = NULL`), so the post-222 `ewp_create_writing_session`
# derives a NULL exam context and no applicability target is consulted; the
# rollup under test reads none of the exam/applicability columns.
_FIXTURES = f"""
INSERT INTO exams(id) VALUES ('00000000-0000-0000-0000-0000000000e1') ON CONFLICT DO NOTHING;
INSERT INTO profiles(id) VALUES ('{_A}') ON CONFLICT DO NOTHING;
INSERT INTO writing_prompts(id,subject_id,topic_id,exercise_type,prompt_text,difficulty_level,reviewer_status,is_active,required_sentence_count)
  SELECT '{_PROMPT}',
         (SELECT id FROM subjects WHERE slug='english-language'),
         (SELECT id FROM topics WHERE slug='grammar'),'sentence_construction','write',1,'verified',true,2
  WHERE NOT EXISTS (SELECT 1 FROM writing_prompts WHERE id='{_PROMPT}');
"""


def _psql(sql: str, *, expect_ok: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [_PSQL, _RUN_DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
        capture_output=True, text=True,
    )
    if expect_ok:
        assert proc.returncode == 0, f"unexpected failure:\n{proc.stderr}"
    else:
        assert proc.returncode != 0, f"expected failure but succeeded:\n{proc.stdout}"
    return proc


def _psql_file(path: Path) -> None:
    proc = subprocess.run(
        [_PSQL, _RUN_DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"failed applying {path.name}:\n{proc.stderr}"


def _scalar(sql: str) -> str:
    proc = subprocess.run(
        [_PSQL, _RUN_DSN, "-t", "-A", "-X", "-c", sql],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _admin(sql: str) -> None:
    subprocess.run(
        [_PSQL, _ADMIN_DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
        capture_output=True, text=True,
    )


@pytest.fixture(scope="module", autouse=True)
def _apply():
    global _RUN_DSN
    if not (_DSN and _PSQL):
        yield
        return
    # Provision a dedicated db so applying 214 (drops writing_prompts.exam_id)
    # never mutates the shared ewp_it db that sibling pre-214 pg tests reuse.
    _admin(
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{_OWN_DB}';"
    )
    _admin(f"DROP DATABASE IF EXISTS {_OWN_DB};")
    _admin(f"CREATE DATABASE {_OWN_DB};")
    _RUN_DSN = _swap_db(_DSN, _OWN_DB)
    _psql(_BOOTSTRAP)
    # Current EWP chain that 240 lands after (not the historical 205->207 shape):
    # 214 reshapes writing_prompts (drops exam_id); 222 replaces the create RPC
    # (+ prompt_snapshot / exam derivation) and recreates the claim functions that
    # reference 209's evaluator/outbox tables.
    _psql_file(_M205)
    _psql_file(_M207)
    _psql_file(_M209)
    _psql_file(_M214)
    _psql_file(_M222)
    _psql_file(_M238)
    _psql_file(_M240)
    _psql_file(_M240)  # idempotent re-apply
    _psql(_FIXTURES)
    yield
    # Drop the isolated db so it never lingers for a later run.
    _RUN_DSN = _DSN
    _admin(
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{_OWN_DB}';"
    )
    _admin(f"DROP DATABASE IF EXISTS {_OWN_DB};")


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
def test_first_submit_stamps_submitted_at():
    """active -> (all units submitted) evaluation_pending sets submitted_at."""
    sid = _create(units=1)
    # freshly created: still drafting -> active, submitted_at NULL.
    assert _scalar(f"SELECT status FROM writing_sessions WHERE id='{sid}'") == "active"
    assert _scalar(f"SELECT submitted_at IS NULL FROM writing_sessions WHERE id='{sid}'") == "t"
    _submit(sid, 1, "The cat sat.", "a" * 64, 1)
    # left drafting -> submitted_at stamped.
    assert _scalar(f"SELECT status FROM writing_sessions WHERE id='{sid}'") != "active"
    assert _scalar(f"SELECT submitted_at IS NOT NULL FROM writing_sessions WHERE id='{sid}'") == "t"


@pg
def test_reopen_clears_submitted_at():
    """past-drafting -> active (learning-mode reopen) clears submitted_at back to NULL."""
    sid = _create(units=1)
    _submit(sid, 1, "The cat sat.", "a" * 64, 1)
    unit, ver = _drive_to_completed(sid)
    assert _scalar(f"SELECT submitted_at IS NOT NULL FROM writing_sessions WHERE id='{sid}'") == "t"
    _scalar(f"SELECT ewp_reopen_writing_unit('{_A}','{sid}','{unit}','{ver}')")
    assert _scalar(f"SELECT status FROM writing_sessions WHERE id='{sid}'") == "active"
    assert _scalar(f"SELECT submitted_at IS NULL FROM writing_sessions WHERE id='{sid}'") == "t"


@pg
def test_reroll_while_past_drafting_preserves_submitted_at():
    """past-drafting -> past-drafting preserves the existing submitted_at
    (monotonic: COALESCE keeps the first stamp, now() is not re-applied)."""
    sid = _create(units=1)
    _submit(sid, 1, "The cat sat.", "a" * 64, 1)
    _drive_to_completed(sid)
    sentinel = "2020-01-01 00:00:00+00"
    _psql(f"UPDATE writing_sessions SET submitted_at='{sentinel}' WHERE id='{sid}'")
    out = _scalar(f"SELECT ewp_finalize_writing_session('{_A}','{sid}')")
    assert '"status": "completed"' in out, out
    assert _scalar(f"SELECT submitted_at FROM writing_sessions WHERE id='{sid}'").startswith("2020-01-01")
