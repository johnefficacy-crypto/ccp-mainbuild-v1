"""Behavioural integration test for migration 214 (writing_prompt content scoping).

Applies migrations 205 -> 214 to a real Postgres and proves the content-scoping
revision:

  - the dual-authority exam-scope columns (`exam_id`, `exam_cycle_id`,
    `exam_phase_id`) are DROPPED from `writing_prompts`,
  - a legacy exam-scoped prompt is BACKFILLED into a `writing_prompt_targets`
    row BEFORE the columns are dropped, and re-applying 214 does NOT duplicate
    it (idempotency — the migration is applied a second time in-test),
  - the exactly-one-scope CHECK rejects a 0-scope and a 2-scope insert,
  - the null-safe unique identity rejects a duplicate `(prompt, same scope)`,
  - `ON DELETE CASCADE` from `writing_prompts` removes target rows,
  - RLS is enabled on `writing_prompt_targets` with NO anon/authenticated policy.

Runs in CI (the backend job provides Postgres + EWP_PG_DSN); locally set
EWP_PG_DSN to a disposable superuser DB. Skips when no DB is configured.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")
_MIG = Path(__file__).parents[3] / "supabase/migrations"

pytestmark = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)

_EXAM = "00000000-0000-0000-0000-0000000000e1"
_EXAM2 = "00000000-0000-0000-0000-0000000000e2"
_FAMILY = "00000000-0000-0000-0000-0000000000f1"
_PHASE = "00000000-0000-0000-0000-0000000000c1"
_LEGACY_PROMPT = "00000000-0000-0000-0000-0000000000d1"

# Base tables migration 205/214 reference but do not create (real schema builds
# them in migration 030). exam_families is required by 214's FK.
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
CREATE TABLE IF NOT EXISTS public.exam_families (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_cycles (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_phases (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.document_assets (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.study_tasks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, task_type text);
CREATE TABLE IF NOT EXISTS public.subjects (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), slug text NOT NULL UNIQUE, name text NOT NULL, subject_group text, default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS public.topics (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), subject_id uuid NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE, parent_topic_id uuid REFERENCES public.topics(id) ON DELETE CASCADE, slug text NOT NULL, name text NOT NULL, level text NOT NULL DEFAULT 'topic' CHECK (level IN ('topic','microtopic','concept')), default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(subject_id, parent_topic_id, slug));
"""

# Seeded AFTER migration 205 (needs subjects/topics) and BEFORE migration 214
# (needs the still-present exam_id column). One exam-scoped legacy prompt.
_SEED_LEGACY = f"""
INSERT INTO exams(id) VALUES ('{_EXAM}'),('{_EXAM2}') ON CONFLICT DO NOTHING;
INSERT INTO exam_families(id) VALUES ('{_FAMILY}') ON CONFLICT DO NOTHING;
INSERT INTO exam_phases(id) VALUES ('{_PHASE}') ON CONFLICT DO NOTHING;
INSERT INTO subjects(slug,name) VALUES ('english-language','English') ON CONFLICT DO NOTHING;
INSERT INTO topics(subject_id,slug,name,level)
  SELECT id,'grammar','Grammar','topic' FROM subjects WHERE slug='english-language'
  ON CONFLICT DO NOTHING;
INSERT INTO writing_prompts(id,exam_id,subject_id,topic_id,exercise_type,prompt_text,difficulty_level,reviewer_status,is_active)
  SELECT '{_LEGACY_PROMPT}','{_EXAM}',
    (SELECT id FROM subjects WHERE slug='english-language'),
    (SELECT id FROM topics WHERE slug='grammar'),
    'sentence_construction','write a sentence',1,'verified',true
  WHERE NOT EXISTS (SELECT 1 FROM writing_prompts WHERE id='{_LEGACY_PROMPT}');
"""


def _psql(sql: str) -> None:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"unexpected failure:\n{proc.stderr}"


def _psql_file(path: Path) -> None:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(path)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"failed applying {path.name}:\n{proc.stderr}"


def _psql_try(sql: str) -> subprocess.CompletedProcess:
    """Run `sql`; return the completed process so the caller can assert failure."""
    return subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
                          capture_output=True, text=True)


def _scalar(sql: str) -> str:
    proc = subprocess.run([_PSQL, _DSN, "-t", "-A", "-X", "-q", "-c", sql], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    out = re.sub(r"\s*(?:INSERT|UPDATE|DELETE)\s+\d+\s+\d+\s*$", "", out)
    return out.strip()


def _new_prompt() -> str:
    """A subject-scoped prompt (no exam columns — they no longer exist)."""
    return _scalar("""
    INSERT INTO writing_prompts(subject_id,topic_id,exercise_type,prompt_text,difficulty_level)
    SELECT (SELECT id FROM subjects WHERE slug='english-language'),
           (SELECT id FROM topics WHERE slug='grammar'),
           'sentence_construction','p',1
    RETURNING id;""")


@pytest.fixture(scope="module", autouse=True)
def _apply():
    _psql(_BOOTSTRAP)
    _psql_file(_MIG / "205_english_writing_practice_schema.sql")
    _psql(_SEED_LEGACY)
    # Migration 213 (Error Lab read model) is applied in the real OPERATOR order
    # (213 then 214); it is not required for these assertions but keeps the apply
    # sequence faithful.
    _psql_file(_MIG / "213_english_writing_practice_error_lab_read_model.sql")
    _psql_file(_MIG / "214_writing_prompt_content_scoping.sql")
    yield


def _columns(table: str) -> set[str]:
    raw = _scalar(f"""SELECT COALESCE(string_agg(column_name, ','), '')
      FROM information_schema.columns
      WHERE table_schema='public' AND table_name='{table}'""")
    return set(raw.split(",")) if raw else set()


def test_exam_scope_columns_are_dropped():
    cols = _columns("writing_prompts")
    assert "exam_id" not in cols
    assert "exam_cycle_id" not in cols
    assert "exam_phase_id" not in cols
    # canonical subject-scoped identity survives
    assert {"subject_id", "topic_id", "microtopic_id"} <= cols


def test_legacy_exam_prompt_was_backfilled_exam_scoped():
    n = _scalar(f"""SELECT count(*) FROM writing_prompt_targets
      WHERE prompt_id='{_LEGACY_PROMPT}' AND exam_id='{_EXAM}'
        AND exam_family_id IS NULL AND exam_phase_id IS NULL
        AND applicability_status='active' AND source_basis='legacy_backfill'""")
    assert n == "1", f"expected exactly one backfilled exam-scoped target, got {n}"


def test_reapplying_214_is_idempotent_no_duplicate_backfill():
    before = _scalar(f"SELECT count(*) FROM writing_prompt_targets WHERE prompt_id='{_LEGACY_PROMPT}'")
    _psql_file(_MIG / "214_writing_prompt_content_scoping.sql")  # second apply
    after = _scalar(f"SELECT count(*) FROM writing_prompt_targets WHERE prompt_id='{_LEGACY_PROMPT}'")
    assert before == after == "1", f"re-apply must not duplicate ({before} -> {after})"


def test_exactly_one_scope_check_rejects_zero_scopes():
    pid = _new_prompt()
    proc = _psql_try(f"INSERT INTO writing_prompt_targets(prompt_id) VALUES ('{pid}');")
    assert proc.returncode != 0, "0-scope insert must be rejected"
    assert "writing_prompt_targets_scope_exactly_one" in proc.stderr, proc.stderr


def test_exactly_one_scope_check_rejects_two_scopes():
    pid = _new_prompt()
    proc = _psql_try(
        f"INSERT INTO writing_prompt_targets(prompt_id,exam_id,exam_family_id) "
        f"VALUES ('{pid}','{_EXAM}','{_FAMILY}');")
    assert proc.returncode != 0, "2-scope insert must be rejected"
    assert "writing_prompt_targets_scope_exactly_one" in proc.stderr, proc.stderr


def test_unique_identity_rejects_duplicate_same_scope():
    pid = _new_prompt()
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id) VALUES ('{pid}','{_EXAM}');")
    proc = _psql_try(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id) VALUES ('{pid}','{_EXAM}');")
    assert proc.returncode != 0, "duplicate (prompt, same scope) must be rejected"
    assert "uq_writing_prompt_targets_scope" in proc.stderr or "duplicate key" in proc.stderr.lower(), proc.stderr
    # A DIFFERENT scope for the same prompt is allowed (many-to-many).
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id) VALUES ('{pid}','{_EXAM2}');")


def test_prompt_delete_cascades_targets():
    pid = _new_prompt()
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id) VALUES ('{pid}','{_EXAM}');")
    assert _scalar(f"SELECT count(*) FROM writing_prompt_targets WHERE prompt_id='{pid}'") == "1"
    _psql(f"DELETE FROM writing_prompts WHERE id='{pid}';")
    assert _scalar(f"SELECT count(*) FROM writing_prompt_targets WHERE prompt_id='{pid}'") == "0"


def test_exam_delete_cascades_exam_scoped_targets():
    # exam_id FK is declared ON DELETE CASCADE, so removing an exam removes its
    # exam-scoped target rows (the prompt itself, being subject-scoped, remains).
    pid = _new_prompt()
    ex = _scalar("INSERT INTO exams DEFAULT VALUES RETURNING id;")
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id) VALUES ('{pid}','{ex}');")
    _psql(f"DELETE FROM exams WHERE id='{ex}';")
    assert _scalar(f"SELECT count(*) FROM writing_prompt_targets WHERE prompt_id='{pid}' AND exam_id='{ex}'") == "0"
    assert _scalar(f"SELECT count(*) FROM writing_prompts WHERE id='{pid}'") == "1"


def test_rls_enabled_with_no_client_policy():
    enabled = _scalar("""SELECT relrowsecurity FROM pg_class
      WHERE oid = 'public.writing_prompt_targets'::regclass""")
    assert enabled == "t", "RLS must be ENABLED on writing_prompt_targets"
    npol = _scalar("SELECT count(*) FROM pg_policies WHERE tablename='writing_prompt_targets'")
    assert npol == "0", f"service-role-managed table must have NO client policy, found {npol}"
