"""Behavioural integration test for migration 215 (Content Studio writing-prompt ops).

Applies migrations 205 → 213 → 214 → 215 to a real, ISOLATED Postgres and proves
the subject-scoped operator write path (all atomic SECURITY DEFINER RPCs):

  - cms_create_writing_prompt: forces pending/inactive, validates subject/topic/
    microtopic scope, writes an audit row; rejects a non-english subject, a
    cross-topic microtopic, a short reason, and a NULL actor,
  - the activation-integrity CHECK: is_active=true is impossible unless
    reviewer_status='verified',
  - cms_review_writing_prompt: pending→verified transition, CAS on updated_at
    (stale token → concurrent_modification), disallowed transition rejected,
  - cms_update_writing_prompt: verified rows are locked (P0422), pending rows edit,
  - cms_bulk_upsert_writing_prompts: subject-scoped external_key idempotency —
    create / identical-unchanged / changed-pending-update / changed-verified-locked,
    and an in-batch duplicate external_key is rejected,
  - cms_set_writing_prompt_target / cms_remove_writing_prompt_target: the Exam
    Assignments write path (global target upsert + audit + removal); zero-scope
    rejected.

Migration 214 DROPS columns (destructive) so — like
test_writing_prompt_targets_migration_behaviour — this suite runs against an
isolated throwaway DB, leaving the shared EWP_PG_DSN database untouched.

Runs in CI (backend job provides Postgres + EWP_PG_DSN); locally set EWP_PG_DSN
to a disposable superuser DB (with psql). Skips when no DB is configured.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.parse as _urlparse
from pathlib import Path

import pytest

_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")
_MIG = Path(__file__).parents[3] / "supabase/migrations"

pytestmark = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)

_OWN_DB = "cs_ops_it_" + re.sub(r"\W", "", os.environ.get("PYTEST_XDIST_WORKER", "main"))

_ACTOR = "00000000-0000-0000-0000-0000000000aa"
_REASON = "operator smoke reason"  # >= 8 chars

# Resolved after migrations apply (module fixture).
_ENGLISH_ID = ""
_GRAMMAR_ID = ""
_MICRO_ID = ""
_OTHER_SUBJECT_ID = ""
_DOC_OK_ID = ""


def _swap_dbname(dsn: str, dbname: str) -> str:
    parts = _urlparse.urlsplit(dsn)
    if parts.scheme:
        return _urlparse.urlunsplit((parts.scheme, parts.netloc, "/" + dbname, parts.query, parts.fragment))
    if re.search(r"\bdbname=", dsn):
        return re.sub(r"\bdbname=\S+", "dbname=" + dbname, dsn)
    return dsn.rstrip() + " dbname=" + dbname


# Base tables 205/214/215 reference but do not create. admin_audit_logs is
# permissive (the RPCs insert provenance rows). document_assets carries the
# columns ewp_validate_prompt_scope inspects.
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
CREATE TABLE IF NOT EXISTS public.document_assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scope text, document_kind text, status text,
  storage_bucket text, storage_path text);
CREATE TABLE IF NOT EXISTS public.study_tasks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, task_type text);
CREATE TABLE IF NOT EXISTS public.admin_audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid, actor_email text, admin_user_id uuid,
  action text, entity_type text, entity_id text,
  old_value jsonb, new_value jsonb, notes text,
  created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS public.subjects (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), slug text NOT NULL UNIQUE, name text NOT NULL, subject_group text, default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS public.topics (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), subject_id uuid NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE, parent_topic_id uuid REFERENCES public.topics(id) ON DELETE CASCADE, slug text NOT NULL, name text NOT NULL, level text NOT NULL DEFAULT 'topic' CHECK (level IN ('topic','microtopic','concept')), default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(subject_id, parent_topic_id, slug));
"""

# Seeded AFTER 205 (needs subjects/topics; 205 seeds english-language + grammar).
_ENGLISH = "(SELECT id FROM subjects WHERE slug='english-language')"
_GRAMMAR = ("(SELECT id FROM topics WHERE slug='grammar' "
            "AND parent_topic_id IS NULL ORDER BY created_at LIMIT 1)")
_SEED = f"""
-- a microtopic child of grammar (active, level=microtopic).
INSERT INTO topics(subject_id, parent_topic_id, slug, name, level, is_active)
  SELECT {_ENGLISH}, {_GRAMMAR}, 'tenses', 'Tenses', 'microtopic', true
  WHERE NOT EXISTS (SELECT 1 FROM topics WHERE slug='tenses' AND subject_id={_ENGLISH});
-- a non-english subject to prove scope validation rejects it.
INSERT INTO subjects(slug, name, is_active) VALUES ('reasoning','Reasoning',true)
  ON CONFLICT (slug) DO NOTHING;
-- a valid admin exam-intelligence document.
INSERT INTO document_assets(scope, document_kind, status, storage_bucket, storage_path)
  VALUES ('admin_exam_intelligence','syllabus','ready','docs','a/b.pdf');
"""


def _psql(sql: str) -> None:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"unexpected failure:\n{proc.stderr}"


def _psql_file(path: Path) -> None:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(path)],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"failed applying {path.name}:\n{proc.stderr}"


def _try(sql: str) -> subprocess.CompletedProcess:
    return subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
                          capture_output=True, text=True, timeout=180)


def _scalar(sql: str) -> str:
    proc = subprocess.run([_PSQL, _DSN, "-t", "-A", "-X", "-q", "-c", sql], capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    out = re.sub(r"\s*(?:INSERT|UPDATE|DELETE)\s+\d+\s+\d+\s*$", "", out)
    return out.strip()


def _admin_psql(sql: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_PSQL, _swap_dbname(_DSN, "postgres"), "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
        capture_output=True, text=True, timeout=180)


def _q(v) -> str:
    """JSON-encode `v` then SQL-quote it as a jsonb literal argument."""
    return "'" + json.dumps(v).replace("'", "''") + "'::jsonb"


def _create(payload: dict, reason: str = _REASON, actor: str = _ACTOR) -> subprocess.CompletedProcess:
    actor_sql = "NULL" if actor is None else f"'{actor}'::uuid"
    return _try(f"SELECT cms_create_writing_prompt({_q(payload)}, '{reason}', {actor_sql}, 'op@x');")


def _create_id(payload: dict) -> str:
    actor_sql = f"'{_ACTOR}'::uuid"
    return _scalar(f"SELECT cms_create_writing_prompt({_q(payload)}, '{_REASON}', {actor_sql}, 'op@x')->>'prompt_id';")


def _base_payload(**over) -> dict:
    p = {"subject_id": _ENGLISH_ID, "topic_id": _GRAMMAR_ID,
         "exercise_type": "sentence_construction",
         "prompt_text": "Write one grammatical sentence.", "difficulty_level": 2}
    p.update(over)
    return p


@pytest.fixture(scope="module", autouse=True)
def _apply():
    global _DSN, _ENGLISH_ID, _GRAMMAR_ID, _MICRO_ID, _OTHER_SUBJECT_ID, _DOC_OK_ID
    pre = _admin_psql(f"DROP DATABASE IF EXISTS {_OWN_DB} WITH (FORCE)")
    assert pre.returncode == 0, f"pre-drop failed:\n{pre.stderr}"
    created = _admin_psql(f"CREATE DATABASE {_OWN_DB}")
    assert created.returncode == 0, f"create failed:\n{created.stderr}"

    _DSN = _swap_dbname(_DSN, _OWN_DB)
    try:
        _psql(_BOOTSTRAP)
        _psql_file(_MIG / "205_english_writing_practice_schema.sql")
        _psql(_SEED)
        _psql_file(_MIG / "213_english_writing_practice_error_lab_read_model.sql")
        _psql_file(_MIG / "214_writing_prompt_content_scoping.sql")
        _psql_file(_MIG / "215_writing_prompt_content_studio_ops.sql")
        _ENGLISH_ID = _scalar(f"SELECT {_ENGLISH};")
        _GRAMMAR_ID = _scalar(f"SELECT {_GRAMMAR};")
        _MICRO_ID = _scalar(f"SELECT id FROM topics WHERE slug='tenses' AND subject_id={_ENGLISH};")
        _OTHER_SUBJECT_ID = _scalar("SELECT id FROM subjects WHERE slug='reasoning';")
        _DOC_OK_ID = _scalar("SELECT id FROM document_assets WHERE scope='admin_exam_intelligence' LIMIT 1;")
        yield
    finally:
        _admin_psql(f"DROP DATABASE IF EXISTS {_OWN_DB} WITH (FORCE)")


# ── create ─────────────────────────────────────────────────────────────────


def test_create_lands_pending_inactive_with_audit():
    pid = _create_id(_base_payload(microtopic_id=_MICRO_ID))
    row = _scalar(f"SELECT reviewer_status||'/'||is_active FROM writing_prompts WHERE id='{pid}';")
    assert row == "pending/false"
    n = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE entity_id='{pid}' AND action='writing_prompt_create';")
    assert n == "1"


def test_create_defaults_max_rewrite_attempts_to_3():
    pid = _create_id(_base_payload())
    assert _scalar(f"SELECT max_rewrite_attempts FROM writing_prompts WHERE id='{pid}';") == "3"


def test_create_ignores_client_supplied_status_and_active():
    pid = _create_id(_base_payload(reviewer_status="verified", is_active=True))
    assert _scalar(f"SELECT reviewer_status||'/'||is_active FROM writing_prompts WHERE id='{pid}';") == "pending/false"


def test_create_rejects_non_english_subject():
    proc = _create(_base_payload(subject_id=_OTHER_SUBJECT_ID))
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_create_rejects_microtopic_not_child_of_topic():
    # tenses is a child of grammar; pass a DIFFERENT topic as parent -> reject.
    other_topic = _scalar(
        f"INSERT INTO topics(subject_id,slug,name,level) "
        f"SELECT {_ENGLISH},'vocab','Vocab','topic' RETURNING id;")
    proc = _create(_base_payload(topic_id=other_topic, microtopic_id=_MICRO_ID))
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_create_rejects_short_reason():
    proc = _create(_base_payload(), reason="short")
    assert proc.returncode != 0 and "invalid_reason" in proc.stderr, proc.stderr


def test_create_rejects_null_actor():
    proc = _create(_base_payload(), actor=None)
    assert proc.returncode != 0 and "missing_actor_id" in proc.stderr, proc.stderr


def test_create_accepts_valid_source_document():
    pid = _create_id(_base_payload(source_document_id=_DOC_OK_ID))
    assert _scalar(f"SELECT source_document_id FROM writing_prompts WHERE id='{pid}';") == _DOC_OK_ID


def test_create_rejects_archived_source_document():
    bad = _scalar(
        "INSERT INTO document_assets(scope,document_kind,status,storage_bucket,storage_path) "
        "VALUES ('admin_exam_intelligence','syllabus','archived','docs','x.pdf') RETURNING id;")
    proc = _create(_base_payload(source_document_id=bad))
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


# ── activation-integrity CHECK ──────────────────────────────────────────────


def test_active_requires_verified_constraint_blocks_direct_activation():
    pid = _create_id(_base_payload())  # pending
    proc = _try(f"UPDATE writing_prompts SET is_active=true WHERE id='{pid}';")
    assert proc.returncode != 0, "activating a non-verified prompt must be rejected"
    assert "writing_prompts_active_requires_verified" in proc.stderr, proc.stderr


# ── review ──────────────────────────────────────────────────────────────────


def _review(pid, expected_status, new_status, updated_at="NULL", reason=_REASON):
    ua = updated_at if updated_at == "NULL" else f"'{updated_at}'::timestamptz"
    return _try(
        f"SELECT cms_review_writing_prompt('{pid}','{expected_status}',{ua},"
        f"'{new_status}','{reason}',NULL,'{_ACTOR}'::uuid,'op@x');")


def test_review_pending_to_verified_and_audit():
    pid = _create_id(_base_payload())
    proc = _review(pid, "pending", "verified")
    assert proc.returncode == 0, proc.stderr
    assert _scalar(f"SELECT reviewer_status FROM writing_prompts WHERE id='{pid}';") == "verified"
    n = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE entity_id='{pid}' AND action='writing_prompt_status_transition';")
    assert n == "1"


def test_review_disallowed_transition_rejected():
    pid = _create_id(_base_payload())
    _review(pid, "pending", "rejected")  # rejected is terminal
    proc = _review(pid, "rejected", "verified")
    assert proc.returncode != 0 and "transition_not_allowed" in proc.stderr, proc.stderr


def test_review_stale_updated_at_is_concurrent_modification():
    pid = _create_id(_base_payload())
    proc = _review(pid, "pending", "verified", updated_at="2000-01-01T00:00:00Z")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr


def test_review_wrong_expected_status_is_concurrent_modification():
    pid = _create_id(_base_payload())  # actually pending
    proc = _review(pid, "verified", "rejected")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr


# ── update (verified-lock + CAS) ────────────────────────────────────────────


def _update(pid, patch: dict, expected_updated_at="NULL", reason=_REASON):
    ua = expected_updated_at if expected_updated_at == "NULL" else f"'{expected_updated_at}'::timestamptz"
    return _try(f"SELECT cms_update_writing_prompt('{pid}',{ua},{_q(patch)},'{reason}','{_ACTOR}'::uuid,'op@x');")


def test_update_pending_edits_content():
    pid = _create_id(_base_payload())
    proc = _update(pid, {"difficulty_level": 7})
    assert proc.returncode == 0, proc.stderr
    assert _scalar(f"SELECT difficulty_level FROM writing_prompts WHERE id='{pid}';") == "7"


def test_update_verified_is_locked():
    pid = _create_id(_base_payload())
    _review(pid, "pending", "verified")
    proc = _update(pid, {"difficulty_level": 9})
    assert proc.returncode != 0 and "prompt_verified_locked" in proc.stderr, proc.stderr


def test_update_rescopes_and_revalidates():
    pid = _create_id(_base_payload())
    proc = _update(pid, {"subject_id": _OTHER_SUBJECT_ID})
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


# ── bulk upsert (subject-scoped external_key idempotency) ───────────────────


def _bulk(rows: list, reason: str = _REASON, subject: str = None):
    subj = subject or _ENGLISH_ID
    return _try(f"SELECT cms_bulk_upsert_writing_prompts('{subj}'::uuid,{_q(rows)},'{reason}','{_ACTOR}'::uuid,'op@x');")


def _bulk_counts(rows: list, subject: str = None) -> tuple[str, str, str]:
    subj = subject or _ENGLISH_ID
    out = _scalar(
        f"SELECT (r->>'created')||' '||(r->>'updated')||' '||(r->>'unchanged') "
        f"FROM cms_bulk_upsert_writing_prompts('{subj}'::uuid,{_q(rows)},'{_REASON}','{_ACTOR}'::uuid,'op@x') r;")
    c, u, n = out.split()
    return c, u, n


def _row(ext, **over) -> dict:
    r = _base_payload(**over)
    r["external_key"] = ext
    return r


def test_bulk_creates_then_unchanged_then_updates():
    # first import creates
    c, u, n = _bulk_counts([_row("bk-1", prompt_text="Sentence one here.")])
    assert (c, u, n) == ("1", "0", "0")
    # identical re-import -> unchanged
    c, u, n = _bulk_counts([_row("bk-1", prompt_text="Sentence one here.")])
    assert (c, u, n) == ("0", "0", "1")
    # changed content on a pending row -> update
    c, u, n = _bulk_counts([_row("bk-1", prompt_text="Sentence one, revised.")])
    assert (c, u, n) == ("0", "1", "0")


def test_bulk_external_key_scoped_to_subject_via_unique_index():
    _bulk_counts([_row("bk-uniq", prompt_text="Only sentence.")])
    n = _scalar(
        f"SELECT count(*) FROM writing_prompts "
        f"WHERE subject_id='{_ENGLISH_ID}' AND metadata->>'external_key'='bk-uniq';")
    assert n == "1"


def test_bulk_changed_verified_row_is_locked():
    _bulk_counts([_row("bk-lock", prompt_text="Lockable sentence.")])
    pid = _scalar(f"SELECT id FROM writing_prompts WHERE metadata->>'external_key'='bk-lock' AND subject_id='{_ENGLISH_ID}';")
    _review(pid, "pending", "verified")
    proc = _bulk([_row("bk-lock", prompt_text="Changed after verify.")])
    assert proc.returncode != 0 and "bulk_locked_row" in proc.stderr, proc.stderr


def test_bulk_rejects_in_batch_duplicate_external_key():
    proc = _bulk([_row("dup", prompt_text="a a a a."), _row("dup", prompt_text="b b b b.")])
    assert proc.returncode != 0 and "duplicate external_key" in proc.stderr, proc.stderr


# ── Exam Assignments (writing_prompt_targets) ───────────────────────────────


def _set_target(pid, *, is_global="false", family="NULL", exam="NULL", phase="NULL",
                status="active", reason=_REASON):
    def u(v):
        return "NULL" if v == "NULL" else f"'{v}'::uuid"
    return _try(
        f"SELECT cms_set_writing_prompt_target('{pid}',{is_global},{u(family)},{u(exam)},{u(phase)},"
        f"'{status}',NULL,'{reason}','{_ACTOR}'::uuid,'op@x');")


def test_set_global_target_and_audit():
    pid = _create_id(_base_payload())
    proc = _set_target(pid, is_global="true")
    assert proc.returncode == 0, proc.stderr
    n = _scalar(
        f"SELECT count(*) FROM writing_prompt_targets "
        f"WHERE prompt_id='{pid}' AND is_global=true AND source_basis='operator'")
    assert n == "1"
    a = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE action='writing_prompt_target_set';")
    assert int(a) >= 1


def test_set_target_zero_scope_rejected():
    pid = _create_id(_base_payload())
    proc = _set_target(pid)  # nothing set
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_set_target_upsert_updates_status_in_place():
    pid = _create_id(_base_payload())
    _set_target(pid, is_global="true", status="active")
    _set_target(pid, is_global="true", status="excluded")
    rows = _scalar(f"SELECT count(*) FROM writing_prompt_targets WHERE prompt_id='{pid}' AND is_global=true;")
    st = _scalar(f"SELECT applicability_status FROM writing_prompt_targets WHERE prompt_id='{pid}' AND is_global=true;")
    assert rows == "1" and st == "excluded"


def test_remove_target_deletes_and_audits():
    pid = _create_id(_base_payload())
    _set_target(pid, is_global="true")
    tid = _scalar(f"SELECT id FROM writing_prompt_targets WHERE prompt_id='{pid}' AND is_global=true;")
    proc = _try(f"SELECT cms_remove_writing_prompt_target('{tid}','{_REASON}','{_ACTOR}'::uuid,'op@x');")
    assert proc.returncode == 0, proc.stderr
    assert _scalar(f"SELECT count(*) FROM writing_prompt_targets WHERE id='{tid}';") == "0"
    a = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE entity_id='{tid}' AND action='writing_prompt_target_remove';")
    assert a == "1"


def test_remove_missing_target_is_not_found():
    proc = _try(f"SELECT cms_remove_writing_prompt_target(gen_random_uuid(),'{_REASON}','{_ACTOR}'::uuid,'op@x');")
    assert proc.returncode != 0 and "not_found" in proc.stderr, proc.stderr


# ── RPCs are service-role-only (not executable by anon/authenticated) ────────


def test_rpcs_revoked_from_anon_and_authenticated():
    for role in ("anon", "authenticated"):
        ok = _scalar(
            "SELECT has_function_privilege('%s','cms_create_writing_prompt(jsonb, text, uuid, text)','EXECUTE');" % role)
        assert ok == "f", f"{role} must NOT execute cms_create_writing_prompt"
    svc = _scalar(
        "SELECT has_function_privilege('service_role','cms_create_writing_prompt(jsonb, text, uuid, text)','EXECUTE');")
    assert svc == "t", "service_role must execute cms_create_writing_prompt"
