"""Behavioural integration test for migration 215 (Content Studio writing-prompt ops).

Applies migrations 205 → 213 → 214 → 215 to a real, ISOLATED Postgres and proves
the subject-scoped operator write path (all atomic SECURITY DEFINER RPCs):

  - cms_create_writing_prompt: forces pending/inactive, validates subject/topic/
    microtopic scope, writes an audit row; rejects a non-english subject, an
    INACTIVE topic, a WRONG-LEVEL topic, a cross-topic microtopic, an archived
    source document, a short reason, and a NULL actor,
  - the activation-integrity CHECK: is_active=true is impossible unless verified,
  - cms_review_writing_prompt: transitions; MANDATORY updated_at CAS (NULL token
    and stale token both rejected); re-runs scope validation before 'verified' so
    a topic/document that went inactive/archived after authoring cannot verify,
  - cms_update_writing_prompt: verified-locked (P0422); MANDATORY CAS; scope re-val,
  - cms_bulk_upsert_writing_prompts: subject-scoped external_key idempotency
    (create/identical/changed-pending/changed-verified-locked/in-batch-dup) AND a
    two-connection concurrent first-import of the same key (advisory-lock serialized),
  - Exam Assignments J2 split: cms_propose_writing_prompt_target (manage: inert
    pending_review; duplicate scope → 409), cms_review_writing_prompt_target
    (review: pending_review→active|excluded, CAS, global-exclude rejected, valid
    family/exam/phase exclusion), cms_remove_writing_prompt_target (review: CAS,
    exact-old audit) + a two-connection same-target review race,
  - deterministic review-vs-curation and review-vs-bulk contention (stale review
    loses with 409, no transition audit commits, prompt stays pending),
  - the service-role-only privilege matrix.

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

_ENGLISH = "(SELECT id FROM subjects WHERE slug='english-language')"
_GRAMMAR = ("(SELECT id FROM topics WHERE slug='grammar' "
            "AND parent_topic_id IS NULL ORDER BY created_at LIMIT 1)")
_SEED = f"""
INSERT INTO topics(subject_id, parent_topic_id, slug, name, level, is_active)
  SELECT {_ENGLISH}, {_GRAMMAR}, 'tenses', 'Tenses', 'microtopic', true
  WHERE NOT EXISTS (SELECT 1 FROM topics WHERE slug='tenses' AND subject_id={_ENGLISH});
INSERT INTO subjects(slug, name, is_active) VALUES ('reasoning','Reasoning',true)
  ON CONFLICT (slug) DO NOTHING;
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
    return "'" + json.dumps(v).replace("'", "''") + "'::jsonb"


def _ts(v) -> str:
    """Render a timestamp argument: the sentinel 'NULL' → SQL NULL, else a literal."""
    return "NULL" if v == "NULL" else f"'{v}'::timestamptz"


# ── create ──────────────────────────────────────────────────────────────────


def _create(payload: dict, reason: str = _REASON, actor: str = _ACTOR) -> subprocess.CompletedProcess:
    actor_sql = "NULL" if actor is None else f"'{actor}'::uuid"
    return _try(f"SELECT cms_create_writing_prompt({_q(payload)}, '{reason}', {actor_sql}, 'op@x');")


def _create_id(payload: dict) -> str:
    return _scalar(f"SELECT cms_create_writing_prompt({_q(payload)}, '{_REASON}', '{_ACTOR}'::uuid, 'op@x')->>'prompt_id';")


def _base_payload(**over) -> dict:
    p = {"subject_id": _ENGLISH_ID, "topic_id": _GRAMMAR_ID,
         "exercise_type": "sentence_construction",
         "prompt_text": "Write one grammatical sentence.", "difficulty_level": 2}
    p.update(over)
    return p


def _prompt_updated_at(pid: str) -> str:
    return _scalar(f"SELECT updated_at FROM writing_prompts WHERE id='{pid}';")


def _fresh_topic(slug: str) -> str:
    return _scalar(
        f"INSERT INTO topics(subject_id,slug,name,level,is_active) "
        f"SELECT {_ENGLISH},'{slug}','{slug}','topic',true RETURNING id;")


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


def test_create_rejects_inactive_topic():
    t = _fresh_topic("inactive-topic")
    _psql(f"UPDATE topics SET is_active=false WHERE id='{t}';")
    proc = _create(_base_payload(topic_id=t))
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_create_rejects_wrong_level_topic():
    # a microtopic (level='microtopic') may not be used as the topic scope.
    proc = _create(_base_payload(topic_id=_MICRO_ID))
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_create_rejects_microtopic_not_child_of_topic():
    other_topic = _fresh_topic("vocab-parent")
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
    pid = _create_id(_base_payload())
    proc = _try(f"UPDATE writing_prompts SET is_active=true WHERE id='{pid}';")
    assert proc.returncode != 0, "activating a non-verified prompt must be rejected"
    assert "writing_prompts_active_requires_verified" in proc.stderr, proc.stderr


# ── review (mandatory CAS + re-validation) ──────────────────────────────────


def _review(pid, expected_status, new_status, updated_at="__fetch__", reason=_REASON):
    ua = _prompt_updated_at(pid) if updated_at == "__fetch__" else updated_at
    return _try(
        f"SELECT cms_review_writing_prompt('{pid}','{expected_status}',{_ts(ua)},"
        f"'{new_status}','{reason}',NULL,'{_ACTOR}'::uuid,'op@x');")


def test_review_pending_to_verified_and_audit():
    pid = _create_id(_base_payload())
    proc = _review(pid, "pending", "verified")
    assert proc.returncode == 0, proc.stderr
    assert _scalar(f"SELECT reviewer_status FROM writing_prompts WHERE id='{pid}';") == "verified"
    n = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE entity_id='{pid}' AND action='writing_prompt_status_transition';")
    assert n == "1"


def test_review_requires_expected_updated_at():
    pid = _create_id(_base_payload())
    proc = _review(pid, "pending", "verified", updated_at="NULL")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr
    assert _scalar(f"SELECT reviewer_status FROM writing_prompts WHERE id='{pid}';") == "pending"


def test_review_disallowed_transition_rejected():
    pid = _create_id(_base_payload())
    _review(pid, "pending", "rejected")
    proc = _review(pid, "rejected", "verified")
    assert proc.returncode != 0 and "transition_not_allowed" in proc.stderr, proc.stderr


def test_review_stale_updated_at_is_concurrent_modification():
    pid = _create_id(_base_payload())
    proc = _review(pid, "pending", "verified", updated_at="2000-01-01T00:00:00Z")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr


def test_review_wrong_expected_status_is_concurrent_modification():
    pid = _create_id(_base_payload())
    proc = _review(pid, "verified", "rejected")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr


def test_review_revalidates_scope_blocks_verify_when_topic_inactivated():
    t = _fresh_topic("post-authoring-inactivation")
    pid = _create_id(_base_payload(topic_id=t))
    _psql(f"UPDATE topics SET is_active=false WHERE id='{t}';")  # goes bad AFTER authoring
    proc = _review(pid, "pending", "verified")
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr
    assert _scalar(f"SELECT reviewer_status FROM writing_prompts WHERE id='{pid}';") == "pending"


def test_review_revalidates_scope_blocks_verify_when_document_archived():
    doc = _scalar(
        "INSERT INTO document_assets(scope,document_kind,status,storage_bucket,storage_path) "
        "VALUES ('admin_exam_intelligence','syllabus','ready','docs','later.pdf') RETURNING id;")
    pid = _create_id(_base_payload(source_document_id=doc))
    _psql(f"UPDATE document_assets SET status='archived' WHERE id='{doc}';")
    proc = _review(pid, "pending", "verified")
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_review_rejected_still_allowed_when_scope_went_bad():
    # scope re-validation gates ONLY 'verified'; rejecting a now-invalid prompt is fine.
    t = _fresh_topic("rejectable-after-inactivation")
    pid = _create_id(_base_payload(topic_id=t))
    _psql(f"UPDATE topics SET is_active=false WHERE id='{t}';")
    proc = _review(pid, "pending", "rejected")
    assert proc.returncode == 0, proc.stderr
    assert _scalar(f"SELECT reviewer_status FROM writing_prompts WHERE id='{pid}';") == "rejected"


# ── update (verified-lock + mandatory CAS) ──────────────────────────────────


def _update(pid, patch: dict, expected_updated_at="__fetch__", reason=_REASON):
    ua = _prompt_updated_at(pid) if expected_updated_at == "__fetch__" else expected_updated_at
    return _try(f"SELECT cms_update_writing_prompt('{pid}',{_ts(ua)},{_q(patch)},'{reason}','{_ACTOR}'::uuid,'op@x');")


def test_update_pending_edits_content():
    pid = _create_id(_base_payload())
    proc = _update(pid, {"difficulty_level": 7})
    assert proc.returncode == 0, proc.stderr
    assert _scalar(f"SELECT difficulty_level FROM writing_prompts WHERE id='{pid}';") == "7"


def test_update_requires_expected_updated_at():
    pid = _create_id(_base_payload())
    proc = _update(pid, {"difficulty_level": 8}, expected_updated_at="NULL")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr


def test_update_verified_is_locked():
    pid = _create_id(_base_payload())
    _review(pid, "pending", "verified")
    proc = _update(pid, {"difficulty_level": 9})
    assert proc.returncode != 0 and "prompt_verified_locked" in proc.stderr, proc.stderr


def test_update_rescopes_and_revalidates():
    pid = _create_id(_base_payload())
    proc = _update(pid, {"subject_id": _OTHER_SUBJECT_ID})
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


# ── bulk upsert (subject-scoped external_key idempotency + concurrency) ──────


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
    c, u, n = _bulk_counts([_row("bk-1", prompt_text="Sentence one here.")])
    assert (c, u, n) == ("1", "0", "0")
    c, u, n = _bulk_counts([_row("bk-1", prompt_text="Sentence one here.")])
    assert (c, u, n) == ("0", "0", "1")
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


def test_bulk_concurrent_first_import_same_key_is_idempotent():
    """Two connections race the SAME first import of one external_key. The
    per-(subject,key) advisory xact lock serializes them: exactly one row exists
    and BOTH callers succeed (create then identical-unchanged) — never a
    unique-violation abort."""
    rows = [_row("bk-race", prompt_text="Racing identical sentence.")]
    call = (f"SELECT cms_bulk_upsert_writing_prompts('{_ENGLISH_ID}'::uuid,{_q(rows)},"
            f"'{_REASON}','{_ACTOR}'::uuid,'op@x');")
    procs = [subprocess.Popen([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", call],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for _ in range(2)]
    results = [(p.wait(), p.communicate()[1]) for p in procs]
    assert all(rc == 0 for rc, _ in results), f"both must succeed: {results}"
    n = _scalar(f"SELECT count(*) FROM writing_prompts "
                f"WHERE subject_id='{_ENGLISH_ID}' AND metadata->>'external_key'='bk-race';")
    assert n == "1", f"advisory lock must yield exactly one row, got {n}"


# ── review-vs-curation / review-vs-bulk contention (deterministic CAS) ───────


def test_review_loses_to_concurrent_curation_stale_token():
    pid = _create_id(_base_payload())
    stale = _prompt_updated_at(pid)          # reviewer's snapshot
    _update(pid, {"difficulty_level": 6})    # curation commits first, bumps updated_at
    proc = _review(pid, "pending", "verified", updated_at=stale)
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr
    assert _scalar(f"SELECT reviewer_status FROM writing_prompts WHERE id='{pid}';") == "pending"
    n = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE entity_id='{pid}' AND action='writing_prompt_status_transition';")
    assert n == "0", "no review transition audit may commit when the review loses"


def test_review_loses_to_concurrent_bulk_stale_token():
    _bulk_counts([_row("bk-vs", prompt_text="Original bulk sentence.")])
    pid = _scalar(f"SELECT id FROM writing_prompts WHERE metadata->>'external_key'='bk-vs' AND subject_id='{_ENGLISH_ID}';")
    stale = _prompt_updated_at(pid)
    _bulk_counts([_row("bk-vs", prompt_text="Revised bulk sentence.")])  # bulk update bumps updated_at
    proc = _review(pid, "pending", "verified", updated_at=stale)
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr
    assert _scalar(f"SELECT reviewer_status FROM writing_prompts WHERE id='{pid}';") == "pending"


# ── Exam Assignments (J2 split: propose / review / remove) ───────────────────


def _propose_target(pid, *, is_global="false", family="NULL", exam="NULL", phase="NULL", reason=_REASON):
    def u(v):
        return "NULL" if v == "NULL" else f"'{v}'::uuid"
    return _try(
        f"SELECT cms_propose_writing_prompt_target('{pid}',{is_global},{u(family)},{u(exam)},{u(phase)},"
        f"NULL,'{reason}','{_ACTOR}'::uuid,'op@x');")


def _propose_target_id(pid, **kw) -> str:
    def u(v):
        return "NULL" if v == "NULL" else f"'{v}'::uuid"
    ig = kw.get("is_global", "false")
    return _scalar(
        f"SELECT cms_propose_writing_prompt_target('{pid}',{ig},{u(kw.get('family','NULL'))},"
        f"{u(kw.get('exam','NULL'))},{u(kw.get('phase','NULL'))},NULL,'{_REASON}','{_ACTOR}'::uuid,'op@x')->>'target_id';")


def _target_updated_at(tid: str) -> str:
    return _scalar(f"SELECT updated_at FROM writing_prompt_targets WHERE id='{tid}';")


def _review_target(tid, new_status, updated_at="__fetch__", reason=_REASON):
    ua = _target_updated_at(tid) if updated_at == "__fetch__" else updated_at
    return _try(
        f"SELECT cms_review_writing_prompt_target('{tid}',{_ts(ua)},'{new_status}',NULL,"
        f"'{reason}','{_ACTOR}'::uuid,'op@x');")


def _remove_target(tid, updated_at="__fetch__", reason=_REASON):
    ua = _target_updated_at(tid) if updated_at == "__fetch__" else updated_at
    return _try(
        f"SELECT cms_remove_writing_prompt_target('{tid}',{_ts(ua)},'{reason}','{_ACTOR}'::uuid,'op@x');")


def test_propose_lands_pending_review_inert_with_audit():
    pid = _create_id(_base_payload())
    tid = _propose_target_id(pid, is_global="true")
    st = _scalar(f"SELECT applicability_status FROM writing_prompt_targets WHERE id='{tid}';")
    assert st == "pending_review", "manage may only PROPOSE an inert assignment"
    a = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE entity_id='{tid}' AND action='writing_prompt_target_propose';")
    assert a == "1"


def test_propose_zero_scope_rejected():
    pid = _create_id(_base_payload())
    proc = _propose_target(pid)
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_propose_duplicate_scope_rejected_409():
    pid = _create_id(_base_payload())
    _propose_target_id(pid, is_global="true")
    proc = _propose_target(pid, is_global="true")
    assert proc.returncode != 0 and "target_exists" in proc.stderr, proc.stderr


def test_review_promotes_pending_to_active_and_audits_old_new():
    pid = _create_id(_base_payload())
    tid = _propose_target_id(pid, is_global="true")
    proc = _review_target(tid, "active")
    assert proc.returncode == 0, proc.stderr
    assert _scalar(f"SELECT applicability_status FROM writing_prompt_targets WHERE id='{tid}';") == "active"
    # audit carries the EXACT old (pending_review) and new (active) rows.
    row = _scalar(
        f"SELECT (old_value->>'applicability_status')||'->'||(new_value->>'applicability_status') "
        f"FROM admin_audit_logs WHERE entity_id='{tid}' AND action='writing_prompt_target_review' "
        f"ORDER BY created_at DESC LIMIT 1;")
    assert row == "pending_review->active"


def test_review_global_exclude_rejected():
    pid = _create_id(_base_payload())
    tid = _propose_target_id(pid, is_global="true")
    proc = _review_target(tid, "excluded")
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_review_exam_scope_exclude_allowed():
    pid = _create_id(_base_payload())
    ex = _scalar("INSERT INTO exams DEFAULT VALUES RETURNING id;")
    tid = _propose_target_id(pid, exam=ex)
    proc = _review_target(tid, "excluded")
    assert proc.returncode == 0, proc.stderr
    assert _scalar(f"SELECT applicability_status FROM writing_prompt_targets WHERE id='{tid}';") == "excluded"


def test_review_target_requires_cas_token():
    pid = _create_id(_base_payload())
    tid = _propose_target_id(pid, is_global="true")
    proc = _review_target(tid, "active", updated_at="NULL")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr


def test_review_target_stale_token_rejected():
    pid = _create_id(_base_payload())
    tid = _propose_target_id(pid, is_global="true")
    proc = _review_target(tid, "active", updated_at="2000-01-01T00:00:00Z")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr


def test_concurrent_target_review_serialized_exactly_one_wins():
    pid = _create_id(_base_payload())
    tid = _propose_target_id(pid, is_global="true")
    token = _target_updated_at(tid)
    call = (f"SELECT cms_review_writing_prompt_target('{tid}','{token}'::timestamptz,'active',NULL,"
            f"'{_REASON}','{_ACTOR}'::uuid,'op@x');")
    procs = [subprocess.Popen([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", call],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for _ in range(2)]
    results = [(p.wait(), p.communicate()[1]) for p in procs]
    rcs = [rc for rc, _ in results]
    assert rcs.count(0) == 1, f"exactly one review must win: {results}"
    loser = next(err for rc, err in results if rc != 0)
    assert "concurrent_modification" in loser, loser


def test_remove_target_cas_and_exact_old_audit():
    pid = _create_id(_base_payload())
    tid = _propose_target_id(pid, is_global="true")
    _review_target(tid, "active")
    proc = _remove_target(tid)
    assert proc.returncode == 0, proc.stderr
    assert _scalar(f"SELECT count(*) FROM writing_prompt_targets WHERE id='{tid}';") == "0"
    old_status = _scalar(
        f"SELECT old_value->>'applicability_status' FROM admin_audit_logs "
        f"WHERE entity_id='{tid}' AND action='writing_prompt_target_remove' ORDER BY created_at DESC LIMIT 1;")
    assert old_status == "active", "removal must audit the exact old row (not NULL)"


def test_remove_target_requires_cas_token():
    pid = _create_id(_base_payload())
    tid = _propose_target_id(pid, is_global="true")
    proc = _remove_target(tid, updated_at="NULL")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr


def test_remove_missing_target_is_not_found():
    proc = _remove_target("00000000-0000-0000-0000-0000000000ff",
                          updated_at="2026-07-01T00:00:00Z")
    assert proc.returncode != 0 and "not_found" in proc.stderr, proc.stderr


# ── NULL-safe source-document provenance validation ─────────────────────────


def _doc(scope="admin_exam_intelligence", kind="syllabus", status="ready"):
    def v(x):
        return "NULL" if x is None else f"'{x}'"
    return _scalar(
        f"INSERT INTO document_assets(scope,document_kind,status,storage_bucket,storage_path) "
        f"VALUES ({v(scope)},{v(kind)},{v(status)},'docs','p.pdf') RETURNING id;")


def test_create_rejects_null_scope_document():
    proc = _create(_base_payload(source_document_id=_doc(scope=None)))
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_create_rejects_null_kind_document():
    proc = _create(_base_payload(source_document_id=_doc(kind=None)))
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


def test_create_rejects_null_status_document():
    proc = _create(_base_payload(source_document_id=_doc(status=None)))
    assert proc.returncode != 0 and "invalid_scope" in proc.stderr, proc.stderr


# ── prompt content guards (blank prompt / invalid required words) ────────────


def test_create_rejects_blank_prompt_text():
    proc = _create(_base_payload(prompt_text="   "))
    assert proc.returncode != 0 and "invalid_content" in proc.stderr, proc.stderr


def test_create_rejects_blank_required_word():
    proc = _create(_base_payload(required_words=["ok", "  "]))
    assert proc.returncode != 0 and "invalid_content" in proc.stderr, proc.stderr


def test_create_rejects_multiword_required_word():
    proc = _create(_base_payload(required_words=["two words"]))
    assert proc.returncode != 0 and "invalid_content" in proc.stderr, proc.stderr


def test_create_rejects_case_duplicate_required_word():
    proc = _create(_base_payload(required_words=["Policy", "policy"]))
    assert proc.returncode != 0 and "invalid_content" in proc.stderr, proc.stderr


# ── external_key is system-owned + immutable (bulk-import identity) ──────────


def _ext_key(pid: str) -> str:
    return _scalar(f"SELECT metadata->>'external_key' FROM writing_prompts WHERE id='{pid}';")


def test_create_rejects_reserved_external_key_metadata():
    proc = _create(_base_payload(metadata={"external_key": "hijack"}))
    assert proc.returncode != 0 and "reserved_metadata_key" in proc.stderr, proc.stderr


def test_patch_preserves_external_key_across_metadata_edit():
    _bulk_counts([_row("ek-keep", prompt_text="Keepable sentence.")])
    pid = _scalar(f"SELECT id FROM writing_prompts WHERE metadata->>'external_key'='ek-keep' AND subject_id='{_ENGLISH_ID}';")
    proc = _update(pid, {"metadata": {"foo": "bar"}})
    assert proc.returncode == 0, proc.stderr
    assert _ext_key(pid) == "ek-keep", "patch must preserve the import key"
    assert _scalar(f"SELECT metadata->>'foo' FROM writing_prompts WHERE id='{pid}';") == "bar"


def test_patch_cannot_change_external_key():
    _bulk_counts([_row("ek-immut", prompt_text="Immutable key sentence.")])
    pid = _scalar(f"SELECT id FROM writing_prompts WHERE metadata->>'external_key'='ek-immut' AND subject_id='{_ENGLISH_ID}';")
    proc = _update(pid, {"metadata": {"external_key": "other"}})
    assert proc.returncode != 0 and "reserved_metadata_key" in proc.stderr, proc.stderr


def test_bulk_reimport_after_metadata_edit_stays_idempotent():
    # create via bulk, add provenance via a normal edit, then re-import the SAME
    # key with changed content → must MATCH the same row (update), not duplicate,
    # and preserve the unrelated provenance metadata.
    _bulk_counts([_row("ek-reimp", prompt_text="Original reimport sentence.")])
    pid = _scalar(f"SELECT id FROM writing_prompts WHERE metadata->>'external_key'='ek-reimp' AND subject_id='{_ENGLISH_ID}';")
    _update(pid, {"metadata": {"prov": "manual"}})
    c, u, n = _bulk_counts([_row("ek-reimp", prompt_text="Revised reimport sentence.")])
    assert (c, u, n) == ("0", "1", "0"), "re-import must resolve to the same row"
    rows = _scalar(f"SELECT count(*) FROM writing_prompts WHERE metadata->>'external_key'='ek-reimp' AND subject_id='{_ENGLISH_ID}';")
    assert rows == "1", "no duplicate row after metadata edit + re-import"
    assert _scalar(f"SELECT metadata->>'prov' FROM writing_prompts WHERE id='{pid}';") == "manual", \
        "bulk update must preserve unrelated provenance metadata"


# ── RPCs are service-role-only (not executable by anon/authenticated) ────────


def test_rpcs_revoked_from_anon_and_authenticated():
    sigs = [
        "cms_create_writing_prompt(jsonb, text, uuid, text)",
        "cms_propose_writing_prompt_target(uuid, boolean, uuid, uuid, uuid, numeric, text, uuid, text)",
        "cms_review_writing_prompt_target(uuid, timestamptz, text, numeric, text, uuid, text)",
        "cms_remove_writing_prompt_target(uuid, timestamptz, text, uuid, text)",
    ]
    for sig in sigs:
        for role in ("anon", "authenticated"):
            ok = _scalar(f"SELECT has_function_privilege('{role}','{sig}','EXECUTE');")
            assert ok == "f", f"{role} must NOT execute {sig}"
        svc = _scalar(f"SELECT has_function_privilege('service_role','{sig}','EXECUTE');")
        assert svc == "t", f"service_role must execute {sig}"
