"""Behavioural integration test for the EWP-1 migration.

Applies migration 205 to a real Postgres and exercises the contracts that
substring inspection cannot prove: append-only immutability against
service-role, the effective-evidence view isolation, the session-snapshot
guard, review-override coexistence, value-domain rejection, and the taxonomy
seed. Reproducible CI evidence where a database is available.

Runs only when ``EWP_PG_DSN`` points at a Postgres superuser connection to a
DISPOSABLE database (the test creates prerequisite stub tables and applies the
migration into it). Skips otherwise, so it never blocks environments without a
database. Example:

    createdb ewp_it
    EWP_PG_DSN="postgresql:///ewp_it" pytest tests/study_os/test_writing_schema_integration.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")
_MIGRATION = (
    Path(__file__).parents[3]
    / "supabase/migrations/205_english_writing_practice_schema.sql"
)

pytestmark = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)

_BOOTSTRAP = r"""
DO $$ BEGIN CREATE ROLE authenticated LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE service_role LOGIN BYPASSRLS; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA public TO authenticated, service_role;
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

_GRANTS = """
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO authenticated, service_role;
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
    _psql(_BOOTSTRAP)
    _psql_file(_MIGRATION)
    _psql_file(_MIGRATION)  # idempotent re-apply
    _psql(_GRANTS)
    # minimal fixtures
    _psql("""
      INSERT INTO exams(id) VALUES ('00000000-0000-0000-0000-0000000000e1') ON CONFLICT DO NOTHING;
      INSERT INTO profiles(id) VALUES ('00000000-0000-0000-0000-0000000000aa'),
                                      ('00000000-0000-0000-0000-0000000000bb') ON CONFLICT DO NOTHING;
      INSERT INTO writing_prompts(id,exam_id,subject_id,topic_id,exercise_type,prompt_text,difficulty_level)
        SELECT '00000000-0000-0000-0000-0000000000d1','00000000-0000-0000-0000-0000000000e1',
               (SELECT id FROM subjects WHERE slug='english-language'),
               (SELECT id FROM topics WHERE slug='grammar'),'sentence_construction','p',1
        WHERE NOT EXISTS (SELECT 1 FROM writing_prompts WHERE id='00000000-0000-0000-0000-0000000000d1');
      INSERT INTO writing_sessions(id,user_id,prompt_id,mode,projection_revision,feedback_release_policy)
        SELECT '00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000aa',
               '00000000-0000-0000-0000-0000000000d1','learning',1,'immediate'
        WHERE NOT EXISTS (SELECT 1 FROM writing_sessions WHERE id='00000000-0000-0000-0000-0000000000d2');
      INSERT INTO writing_session_units(id,session_id,unit_number)
        SELECT '00000000-0000-0000-0000-0000000000d3','00000000-0000-0000-0000-0000000000d2',1
        WHERE NOT EXISTS (SELECT 1 FROM writing_session_units WHERE id='00000000-0000-0000-0000-0000000000d3');
      INSERT INTO writing_unit_versions(id,unit_id,version_number,answer_text,content_hash)
        SELECT '00000000-0000-0000-0000-0000000000d4','00000000-0000-0000-0000-0000000000d3',1,'h',repeat('a',64)
        WHERE NOT EXISTS (SELECT 1 FROM writing_unit_versions WHERE id='00000000-0000-0000-0000-0000000000d4');
    """)
    yield


def test_seed_counts():
    assert _scalar("SELECT count(*) FROM topics WHERE level='topic'") == "8"
    assert _scalar("SELECT count(*) FROM topics WHERE level='microtopic'") == "24"
    assert _scalar("SELECT count(*) FROM writing_issue_type_microtopic_map") == "19"
    # every mapped microtopic is an active English microtopic
    assert _scalar("""
      SELECT count(*) FROM writing_issue_type_microtopic_map m JOIN topics t ON t.id=m.microtopic_id
      WHERE t.level<>'microtopic' OR t.is_active=false
        OR t.subject_id<>(SELECT id FROM subjects WHERE slug='english-language')
    """) == "0"


def test_immutability_blocks_service_role_update_and_delete():
    _psql("UPDATE writing_unit_versions SET answer_text='x' WHERE id='00000000-0000-0000-0000-0000000000d4'", expect_ok=False)
    _psql("DELETE FROM writing_unit_versions WHERE id='00000000-0000-0000-0000-0000000000d4'", expect_ok=False)


def test_effective_view_isolation():
    # authenticated sees zero rows through the view even with a valid uid.
    # (BEGIN/SET/COMMIT emit command tags; take the lone numeric line.)
    out = _scalar("""
      BEGIN; SET LOCAL ROLE authenticated; SET LOCAL ewp.uid='00000000-0000-0000-0000-0000000000aa';
      SELECT count(*) FROM public.effective_user_topic_mastery_evidence; COMMIT;
    """)
    digits = [ln for ln in out.splitlines() if ln.strip().isdigit()]
    assert digits == ["0"], out


def test_session_snapshot_guard():
    _psql("UPDATE writing_sessions SET projection_revision=2 WHERE id='00000000-0000-0000-0000-0000000000d2'", expect_ok=False)
    _psql("UPDATE writing_sessions SET status='completed' WHERE id='00000000-0000-0000-0000-0000000000d2'", expect_ok=True)


def test_value_domains_rejected():
    _psql("INSERT INTO writing_unit_versions(unit_id,version_number,answer_text,content_hash) "
          "VALUES ('00000000-0000-0000-0000-0000000000d3',9,'x','NOTHEX')", expect_ok=False)
    _psql("INSERT INTO writing_session_units(session_id,unit_number) "
          "VALUES ('00000000-0000-0000-0000-0000000000d2',0)", expect_ok=False)


def test_feedback_policy_check_null_safe():
    _psql("INSERT INTO exam_descriptive_requirements(exam_id,exercise_type,feedback_release_policy) "
          "VALUES ('00000000-0000-0000-0000-0000000000e1','essay_it','scheduled_after_submit')", expect_ok=False)
    _psql("INSERT INTO exam_descriptive_requirements(exam_id,exercise_type,feedback_release_policy,feedback_release_delay_seconds) "
          "VALUES ('00000000-0000-0000-0000-0000000000e1','essay_it','scheduled_after_submit',600)", expect_ok=True)


def test_cascade_into_immutable_blocks_profile_delete():
    _psql("""
      INSERT INTO user_topic_mastery_evidence(user_id,topic_id,source_type,source_entity_id,evidence_tier,evidence_key,observed_at)
      SELECT '00000000-0000-0000-0000-0000000000bb',(SELECT id FROM topics WHERE slug='grammar'),
             'sentence_drill','00000000-0000-0000-0000-0000000000d4','production','it-ek-bb',now()
      WHERE NOT EXISTS (SELECT 1 FROM user_topic_mastery_evidence WHERE evidence_key='it-ek-bb')
    """)
    _psql("DELETE FROM profiles WHERE id='00000000-0000-0000-0000-0000000000bb'", expect_ok=False)
