"""Behavioural integration test for migration 303 (answer_structures).

Applies 303 to a real, throwaway Postgres database over minimal stubs of the
tables it references, then proves:

  - RLS: a learner (authenticated, non-admin) reads ONLY verified structures of
    verified questions — never draft / in_review / rejected, never a verified
    structure of an unverified question;
  - an admin-role user reads every status; a learner cannot insert or update;
  - no DELETE / TRUNCATE for authenticated, nothing at all for anon;
  - one verified structure per question (partial unique index);
  - review transitions, CAS, rejection-needs-note, and that approving a new
    version demotes the old verified one atomically, with audit rows;
  - an edit of a verified structure is refused;
  - descriptive_attempts' coverage columns travel as a pair.

Runs in CI (backend job provides Postgres + EWP_PG_DSN). Skips without a DB.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import urllib.parse as _urlparse
import uuid
from pathlib import Path

import pytest

_BASE_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")
_MIG = Path(__file__).parents[3] / "supabase/migrations/303_answer_structures.sql"

pytestmark = pytest.mark.skipif(
    not (_BASE_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)

_OWN_DB = "answer_structures_it_" + re.sub(
    r"\W", "", os.environ.get("PYTEST_XDIST_WORKER", "main")
)


def _swap_dbname(dsn: str, dbname: str) -> str:
    parts = _urlparse.urlsplit(dsn)
    if parts.scheme:
        return _urlparse.urlunsplit(
            (parts.scheme, parts.netloc, "/" + dbname, parts.query, parts.fragment)
        )
    if re.search(r"\bdbname=", dsn):
        return re.sub(r"\bdbname=\S+", "dbname=" + dbname, dsn)
    return dsn.rstrip() + " dbname=" + dbname


_DSN = _swap_dbname(_BASE_DSN, _OWN_DB) if _BASE_DSN else None

ADMIN = "00000000-0000-0000-0000-00000000ad01"
LEARNER = "00000000-0000-0000-0000-00000000ee01"
Q_VERIFIED = "00000000-0000-0000-0000-0000000000a1"
Q_PENDING = "00000000-0000-0000-0000-0000000000a2"

_BOOTSTRAP = rf"""
DO $$ BEGIN CREATE ROLE authenticated NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE service_role NOLOGIN BYPASSRLS; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE anon NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA public TO authenticated, service_role, anon;
CREATE SCHEMA IF NOT EXISTS auth;
GRANT USAGE ON SCHEMA auth TO authenticated, service_role, anon;
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $fn$
  SELECT NULLIF(current_setting('ewp.uid', true), '')::uuid $fn$;
CREATE TABLE IF NOT EXISTS auth.users (id uuid PRIMARY KEY, raw_app_meta_data jsonb NOT NULL DEFAULT '{{}}');
CREATE OR REPLACE FUNCTION public.is_admin(uid uuid) RETURNS boolean LANGUAGE sql STABLE
  SECURITY DEFINER SET search_path = public AS $fn$
  SELECT EXISTS (SELECT 1 FROM auth.users u WHERE u.id = uid
    AND coalesce(u.raw_app_meta_data->>'role','') IN ('admin','super_admin')) $fn$;
CREATE OR REPLACE FUNCTION public.tg_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $fn$
  BEGIN NEW.updated_at = clock_timestamp(); RETURN NEW; END $fn$;
CREATE TABLE IF NOT EXISTS public.pyq_questions (
  id uuid PRIMARY KEY, reviewer_status text NOT NULL, question_type text NOT NULL DEFAULT 'descriptive');
GRANT SELECT ON public.pyq_questions TO authenticated;
CREATE TABLE IF NOT EXISTS public.descriptive_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL,
  pyq_question_id uuid NOT NULL, status text NOT NULL DEFAULT 'draft');
CREATE TABLE IF NOT EXISTS public.admin_audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), actor_id uuid, actor_email text,
  action text NOT NULL, entity_type text NOT NULL, entity_id text, old_value jsonb,
  new_value jsonb, notes text, created_at timestamptz NOT NULL DEFAULT now(),
  admin_user_id uuid);
INSERT INTO auth.users(id, raw_app_meta_data) VALUES
  ('{ADMIN}', '{{"role":"admin"}}'), ('{LEARNER}', '{{"role":"user"}}')
  ON CONFLICT DO NOTHING;
INSERT INTO public.pyq_questions(id, reviewer_status) VALUES
  ('{Q_VERIFIED}', 'verified'), ('{Q_PENDING}', 'pending') ON CONFLICT DO NOTHING;
"""


def _run(sql: str, dsn: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_PSQL, dsn or _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-t", "-A", "-c", sql],
        capture_output=True, text=True, timeout=180,
    )


def _ok(sql: str) -> str:
    proc = _run(sql)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _as(user: str | None, role: str, sql: str) -> subprocess.CompletedProcess:
    uid = f"SET ewp.uid = '{user}';" if user else ""
    return _run(f"{uid} SET ROLE {role}; {sql}")


@pytest.fixture(scope="module", autouse=True)
def _apply():
    admin_dsn = _swap_dbname(_BASE_DSN, "postgres")
    _run(f'DROP DATABASE IF EXISTS "{_OWN_DB}" WITH (FORCE);', admin_dsn)
    proc = _run(f'CREATE DATABASE "{_OWN_DB}";', admin_dsn)
    assert proc.returncode == 0, proc.stderr
    _ok(_BOOTSTRAP)
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(_MIG)],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    # Re-applying is idempotent (if-not-exists guards everywhere).
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(_MIG)],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    yield
    _run(f'DROP DATABASE IF EXISTS "{_OWN_DB}" WITH (FORCE);', admin_dsn)


_PAYLOAD = (
    '{"directive":"Discuss","demand":"What is asked.","intro_angles":["a"],'
    '"body_points":[{"id":"p1","point":"x"},{"id":"p2","point":"y"}],'
    '"conclusion_angles":["c"],"pitfalls":["p"]}'
)


def _draft(question: str) -> str:
    out = _ok(
        "SELECT (public.cms_create_answer_structure_draft("
        f"'{question}', '{_PAYLOAD}'::jsonb, 'ai:test', '{{}}'::jsonb, 'fixture draft', null, null))->>'id';"
    )
    return out.splitlines()[-1]


def _row(sid: str) -> tuple[str, str]:
    out = _ok(f"SELECT status || '|' || updated_at::text FROM answer_structures WHERE id='{sid}';")
    status, updated = out.split("|", 1)
    return status, updated


def _review(sid: str, new_status: str, notes: str | None = None) -> subprocess.CompletedProcess:
    status, updated = _row(sid)
    n = "null" if notes is None else f"'{notes}'"
    return _run(
        "SELECT public.cms_review_answer_structure("
        f"'{sid}', '{status}', '{updated}'::timestamptz, '{new_status}', {n}, '{ADMIN}', 'a@x');"
    )


def _fresh_question(verified: bool = True) -> str:
    qid = str(uuid.uuid4())
    _ok(f"INSERT INTO pyq_questions(id, reviewer_status) VALUES ('{qid}', "
        f"'{'verified' if verified else 'pending'}');")
    return qid


# ── RLS ──────────────────────────────────────────────────────────────────────


def test_learner_reads_only_verified_structures_of_verified_questions():
    q = _fresh_question()
    draft = _draft(q)
    in_review = _draft(q)
    assert _review(in_review, "in_review").returncode == 0
    verified = _draft(q)
    assert _review(verified, "verified").returncode == 0
    rejected = _draft(q)
    assert _review(rejected, "rejected", "not usable").returncode == 0

    proc = _as(LEARNER, "authenticated",
               f"SELECT id FROM answer_structures WHERE pyq_question_id='{q}' ORDER BY version;")
    assert proc.returncode == 0, proc.stderr
    seen = set(proc.stdout.split())
    assert seen == {verified}
    assert draft not in seen and in_review not in seen and rejected not in seen


def test_learner_cannot_read_a_verified_structure_of_an_unverified_question():
    q = _fresh_question(verified=False)
    sid = _draft(q)
    assert _review(sid, "verified").returncode == 0
    proc = _as(LEARNER, "authenticated", f"SELECT count(*) FROM answer_structures WHERE id='{sid}';")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split()[-1] == "0"


def test_admin_reads_every_status():
    q = _fresh_question()
    _draft(q)
    _draft(q)
    proc = _as(ADMIN, "authenticated",
               f"SELECT count(*) FROM answer_structures WHERE pyq_question_id='{q}';")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split()[-1] == "2"


def test_learner_cannot_insert_or_update():
    q = _fresh_question()
    sid = _draft(q)
    ins = _as(LEARNER, "authenticated",
              "INSERT INTO answer_structures(pyq_question_id, version, directive, demand, generated_by) "
              f"VALUES ('{q}', 99, 'x', 'y', 'human');")
    assert ins.returncode != 0 and "row-level security" in ins.stderr
    upd = _as(LEARNER, "authenticated",
              f"UPDATE answer_structures SET status='verified' WHERE id='{sid}' RETURNING id;")
    # RLS hides the row from the learner, so the update matches nothing.
    assert upd.returncode == 0 and upd.stdout.split()[-1:] != [sid]
    assert _row(sid)[0] == "draft"


def test_no_delete_or_truncate_for_authenticated_and_nothing_for_anon():
    q = _fresh_question()
    sid = _draft(q)
    for sql in (f"DELETE FROM answer_structures WHERE id='{sid}';",
                "TRUNCATE answer_structures;"):
        proc = _as(ADMIN, "authenticated", sql)
        assert proc.returncode != 0 and "permission denied" in proc.stderr
    proc = _as(None, "anon", "SELECT count(*) FROM answer_structures;")
    assert proc.returncode != 0 and "permission denied" in proc.stderr
    assert _ok(
        "SELECT count(*) FROM information_schema.role_table_grants "
        "WHERE table_name='answer_structures' AND grantee='authenticated' "
        "AND privilege_type IN ('DELETE','TRUNCATE');"
    ) == "0"


def test_rpcs_are_service_role_only():
    proc = _as(ADMIN, "authenticated",
               f"SELECT public.cms_create_answer_structure_draft('{Q_VERIFIED}', "
               f"'{_PAYLOAD}'::jsonb, 'x', '{{}}'::jsonb, 'reason here', null, null);")
    assert proc.returncode != 0 and "permission denied" in proc.stderr


def test_every_policy_exists():
    names = set(_ok(
        "SELECT policyname FROM pg_policies WHERE tablename='answer_structures';"
    ).split())
    assert names == {
        "answer_structures_learner_select_verified",
        "answer_structures_admin_select",
        "answer_structures_admin_insert",
        "answer_structures_admin_update",
    }


# ── one verified per question ────────────────────────────────────────────────


def test_partial_unique_index_allows_only_one_verified():
    q = _fresh_question()
    a, b = _draft(q), _draft(q)
    _ok(f"UPDATE answer_structures SET status='verified', reviewed_by='{ADMIN}', "
        f"reviewed_at=now() WHERE id='{a}';")
    proc = _run(f"UPDATE answer_structures SET status='verified', reviewed_by='{ADMIN}', "
                f"reviewed_at=now() WHERE id='{b}';")
    assert proc.returncode != 0 and "uq_answer_structures_one_verified" in proc.stderr


def test_approving_a_new_version_demotes_the_old_one():
    q = _fresh_question()
    v1 = _draft(q)
    assert _review(v1, "verified").returncode == 0
    v2 = _draft(q)
    assert _review(v2, "verified").returncode == 0
    assert _row(v1)[0] == "rejected"
    assert _row(v2)[0] == "verified"
    note = _ok(f"SELECT review_notes FROM answer_structures WHERE id='{v1}';")
    assert "Superseded by version 2" in note


def test_versions_are_allocated_sequentially():
    q = _fresh_question()
    ids = [_draft(q) for _ in range(3)]
    versions = _ok(
        f"SELECT string_agg(version::text, ',' ORDER BY version) FROM answer_structures "
        f"WHERE id IN ('{ids[0]}','{ids[1]}','{ids[2]}');"
    )
    assert versions == "1,2,3"


# ── review transitions ───────────────────────────────────────────────────────


@pytest.mark.parametrize("path,ok", [
    (["in_review", "verified"], True),
    (["in_review", "draft", "verified"], True),
    (["verified", "in_review"], False),
    (["verified", "draft"], False),
])
def test_review_transitions(path, ok):
    q = _fresh_question()
    sid = _draft(q)
    results = [_review(sid, s).returncode == 0 for s in path]
    assert all(results[:-1])
    assert results[-1] is ok


def test_rejected_is_terminal():
    q = _fresh_question()
    sid = _draft(q)
    assert _review(sid, "rejected", "bad draft").returncode == 0
    for target in ("draft", "in_review", "verified"):
        proc = _review(sid, target)
        assert proc.returncode != 0 and "transition_not_allowed" in proc.stderr


def test_reject_requires_a_note():
    q = _fresh_question()
    sid = _draft(q)
    proc = _review(sid, "rejected")
    assert proc.returncode != 0 and "invalid_review_notes" in proc.stderr


def test_review_is_cas_guarded():
    q = _fresh_question()
    sid = _draft(q)
    status, _updated = _row(sid)
    proc = _run(
        "SELECT public.cms_review_answer_structure("
        f"'{sid}', '{status}', '2000-01-01'::timestamptz, 'verified', null, '{ADMIN}', 'a@x');"
    )
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr


def test_every_decision_is_audited():
    q = _fresh_question()
    sid = _draft(q)
    _review(sid, "in_review")
    _review(sid, "verified")
    actions = _ok(
        "SELECT string_agg(action || ':' || coalesce(new_value->>'status',''), ',' ORDER BY created_at) "
        f"FROM admin_audit_logs WHERE entity_id='{sid}';"
    )
    assert actions == (
        "answer_structure_draft_created:,"
        "answer_structure_status_transition:in_review,"
        "answer_structure_status_transition:verified"
    )


def test_a_verified_structure_cannot_be_edited_in_place():
    q = _fresh_question()
    sid = _draft(q)
    assert _review(sid, "verified").returncode == 0
    _status, updated = _row(sid)
    proc = _run(
        "SELECT public.cms_update_answer_structure("
        f"'{sid}', '{updated}'::timestamptz, '{{\"demand\":\"changed\"}}'::jsonb, "
        f"'edit after approve', '{ADMIN}', 'a@x');"
    )
    assert proc.returncode != 0 and "structure_locked" in proc.stderr


def test_a_draft_edit_changes_only_the_patched_fields():
    q = _fresh_question()
    sid = _draft(q)
    _status, updated = _row(sid)
    _ok(
        "SELECT public.cms_update_answer_structure("
        f"'{sid}', '{updated}'::timestamptz, '{{\"demand\":\"sharper demand\"}}'::jsonb, "
        f"'tighten the demand line', '{ADMIN}', 'a@x');"
    )
    out = _ok(f"SELECT demand || '|' || directive FROM answer_structures WHERE id='{sid}';")
    assert out == "sharper demand|Discuss"


# ── descriptive_attempts coverage columns ───────────────────────────────────


def test_coverage_columns_travel_as_a_pair():
    proc = _run(
        f"INSERT INTO descriptive_attempts(user_id, pyq_question_id, status, structure_version) "
        f"VALUES ('{LEARNER}', '{Q_VERIFIED}', 'submitted', 1);"
    )
    assert proc.returncode != 0 and "descriptive_attempts_coverage_pairs" in proc.stderr
    _ok(
        f"INSERT INTO descriptive_attempts(user_id, pyq_question_id, status, structure_version, "
        f"covered_point_ids) VALUES ('{LEARNER}', '{Q_VERIFIED}', 'submitted', 1, '[\"p1\"]');"
    )
    proc = _run(
        f"INSERT INTO descriptive_attempts(user_id, pyq_question_id, status, structure_version, "
        f"covered_point_ids) VALUES ('{LEARNER}', '{Q_VERIFIED}', 'submitted', 1, '{{}}');"
    )
    assert proc.returncode != 0
