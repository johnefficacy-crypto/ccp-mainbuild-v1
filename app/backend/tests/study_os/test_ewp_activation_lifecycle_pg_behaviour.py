"""Behavioural integration test for migration 224 (EWP activation lifecycle).

Applies migrations 205 → 213 → 214 → 215 → 224 to a real, ISOLATED Postgres and
proves the deterministic activation precondition machine (all atomic, service-
role-only SECURITY DEFINER RPCs):

  - cms_activate_writing_prompt: NOT a boolean toggle. Under a row lock it
    verifies ALL preconditions and, on ANY failure, returns a structured
    {eligible:false, blockers:[...]} verdict and writes NOTHING; only when every
    precondition passes does it flip is_active=true + audit old→new. Each blocker
    path is exercised (prompt_not_verified, already_active,
    no_active_applicability_target, exercise_type_not_runtime_ready,
    semantic_evaluator_not_live, rubric_missing + paragraph_gate_closed,
    invalid_scope, reason_required) and proven write-free.
  - the happy path (runtime-ready type + verified + active target) flips is_active
    and audits, then round-trips through cms_deactivate_writing_prompt.
  - mandatory updated_at CAS (NULL token and stale token both → 409) and not_found.
  - the service-role-only privilege matrix (has_function_privilege).

Migration 214 DROPS columns (destructive) so — like the sibling Content Studio
behaviour suite — this runs against an isolated throwaway DB, leaving the shared
EWP_PG_DSN database untouched.

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

_OWN_DB = "ewp_act_it_" + re.sub(r"\W", "", os.environ.get("PYTEST_XDIST_WORKER", "main"))

_ACTOR = "00000000-0000-0000-0000-0000000000aa"
_REASON = "operator activation reason"  # >= 8 chars

_ENGLISH_ID = ""
_GRAMMAR_ID = ""


def _swap_dbname(dsn: str, dbname: str) -> str:
    parts = _urlparse.urlsplit(dsn)
    if parts.scheme:
        return _urlparse.urlunsplit((parts.scheme, parts.netloc, "/" + dbname, parts.query, parts.fragment))
    if re.search(r"\bdbname=", dsn):
        return re.sub(r"\bdbname=\S+", "dbname=" + dbname, dsn)
    return dsn.rstrip() + " dbname=" + dbname


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
    return "NULL" if v == "NULL" else f"'{v}'::timestamptz"


# ── shared write helpers (mirror the Content Studio ops behaviour suite) ──────


def _base_payload(**over) -> dict:
    p = {"subject_id": _ENGLISH_ID, "topic_id": _GRAMMAR_ID,
         "exercise_type": "sentence_construction",
         "prompt_text": "Write one grammatical sentence.", "difficulty_level": 2}
    p.update(over)
    return p


def _create_id(payload: dict) -> str:
    return _scalar(f"SELECT cms_create_writing_prompt({_q(payload)}, '{_REASON}', '{_ACTOR}'::uuid, 'op@x')->>'prompt_id';")


def _prompt_updated_at(pid: str) -> str:
    return _scalar(f"SELECT updated_at FROM writing_prompts WHERE id='{pid}';")


def _is_active(pid: str) -> str:
    return _scalar(f"SELECT is_active FROM writing_prompts WHERE id='{pid}';")


def _review(pid, expected_status, new_status, updated_at="__fetch__", reason=_REASON):
    ua = _prompt_updated_at(pid) if updated_at == "__fetch__" else updated_at
    return _try(
        f"SELECT cms_review_writing_prompt('{pid}','{expected_status}',{_ts(ua)},"
        f"'{new_status}','{reason}',NULL,'{_ACTOR}'::uuid,'op@x');")


def _add_active_target(pid) -> str:
    tid = _scalar(
        f"SELECT cms_propose_writing_prompt_target('{pid}',true,NULL,NULL,NULL,NULL,"
        f"'{_REASON}','{_ACTOR}'::uuid,'op@x')->>'target_id';")
    ua = _scalar(f"SELECT updated_at FROM writing_prompt_targets WHERE id='{tid}';")
    _try(f"SELECT cms_review_writing_prompt_target('{tid}','{ua}'::timestamptz,'active',NULL,"
         f"'{_REASON}','{_ACTOR}'::uuid,'op@x');")
    return tid


def _activate(pid, updated_at="__fetch__", reason=_REASON, allowlist="NULL"):
    ua = _prompt_updated_at(pid) if updated_at == "__fetch__" else updated_at
    return _try(
        f"SELECT cms_activate_writing_prompt('{pid}',{_ts(ua)},'{reason}',{allowlist},"
        f"'{_ACTOR}'::uuid,'op@x');")


def _activate_result(pid, reason=_REASON, allowlist="NULL") -> dict:
    ua = _prompt_updated_at(pid)
    out = _scalar(
        f"SELECT cms_activate_writing_prompt('{pid}','{ua}'::timestamptz,'{reason}',{allowlist},"
        f"'{_ACTOR}'::uuid,'op@x')::text;")
    return json.loads(out)


def _deactivate(pid, updated_at="__fetch__", reason=_REASON):
    ua = _prompt_updated_at(pid) if updated_at == "__fetch__" else updated_at
    return _try(
        f"SELECT cms_deactivate_writing_prompt('{pid}',{_ts(ua)},'{reason}','{_ACTOR}'::uuid,'op@x');")


def _verified_prompt_with_target(**over) -> str:
    """A verified prompt that carries an active global applicability target."""
    pid = _create_id(_base_payload(**over))
    _review(pid, "pending", "verified")
    _add_active_target(pid)
    return pid


@pytest.fixture(scope="module", autouse=True)
def _apply():
    global _DSN, _ENGLISH_ID, _GRAMMAR_ID
    pre = _admin_psql(f"DROP DATABASE IF EXISTS {_OWN_DB} WITH (FORCE)")
    assert pre.returncode == 0, f"pre-drop failed:\n{pre.stderr}"
    created = _admin_psql(f"CREATE DATABASE {_OWN_DB}")
    assert created.returncode == 0, f"create failed:\n{created.stderr}"

    _DSN = _swap_dbname(_DSN, _OWN_DB)
    try:
        _psql(_BOOTSTRAP)
        _psql_file(_MIG / "205_english_writing_practice_schema.sql")
        _psql_file(_MIG / "213_english_writing_practice_error_lab_read_model.sql")
        _psql_file(_MIG / "214_writing_prompt_content_scoping.sql")
        _psql_file(_MIG / "215_writing_prompt_content_studio_ops.sql")
        _psql_file(_MIG / "226_ewp_prompt_activation_lifecycle.sql")
        _ENGLISH_ID = _scalar(f"SELECT {_ENGLISH};")
        _GRAMMAR_ID = _scalar(f"SELECT {_GRAMMAR};")
        yield
    finally:
        _admin_psql(f"DROP DATABASE IF EXISTS {_OWN_DB} WITH (FORCE)")


# ── happy path ────────────────────────────────────────────────────────────────


def test_activate_happy_path_flips_active_and_audits():
    pid = _verified_prompt_with_target()
    res = _activate_result(pid)
    assert res.get("eligible") is True, res
    assert _is_active(pid) == "t"
    n = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE entity_id='{pid}' AND action='writing_prompt_activate';")
    assert n == "1"
    old_new = _scalar(
        f"SELECT (old_value->>'is_active')||'->'||(new_value->>'is_active') FROM admin_audit_logs "
        f"WHERE entity_id='{pid}' AND action='writing_prompt_activate' ORDER BY created_at DESC LIMIT 1;")
    assert old_new == "false->true"


def test_deactivate_round_trips():
    pid = _verified_prompt_with_target()
    _activate(pid)
    assert _is_active(pid) == "t"
    proc = _deactivate(pid)
    assert proc.returncode == 0, proc.stderr
    assert _is_active(pid) == "f"
    n = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE entity_id='{pid}' AND action='writing_prompt_deactivate';")
    assert n == "1"


# ── blocker paths (each writes NOTHING) ───────────────────────────────────────


def _assert_blocked(pid, expected_blocker, reason=_REASON):
    res = _activate_result(pid, reason=reason)
    assert res.get("eligible") is False, res
    assert expected_blocker in res.get("blockers", []), res
    assert _is_active(pid) == "f", "a blocked activation must write nothing"
    n = _scalar(f"SELECT count(*) FROM admin_audit_logs WHERE entity_id='{pid}' AND action='writing_prompt_activate';")
    assert n == "0", "a blocked activation must not audit"


def test_blocked_prompt_not_verified():
    pid = _create_id(_base_payload())
    _add_active_target(pid)  # active target, but still pending
    _assert_blocked(pid, "prompt_not_verified")


def test_blocked_no_active_applicability_target():
    pid = _create_id(_base_payload())
    _review(pid, "pending", "verified")  # verified but UNASSIGNED
    _assert_blocked(pid, "no_active_applicability_target")


def test_blocked_pending_review_target_is_inert():
    # A pending_review (non-active) target does not satisfy applicability.
    pid = _create_id(_base_payload())
    _review(pid, "pending", "verified")
    _scalar(f"SELECT cms_propose_writing_prompt_target('{pid}',true,NULL,NULL,NULL,NULL,"
            f"'{_REASON}','{_ACTOR}'::uuid,'op@x')->>'target_id';")  # left pending_review
    _assert_blocked(pid, "no_active_applicability_target")


def test_blocked_exercise_type_not_runtime_ready():
    pid = _verified_prompt_with_target(exercise_type="sentence_correction",
                                       source_text="The cat sat on the mat.")
    _assert_blocked(pid, "exercise_type_not_runtime_ready")


def test_blocked_semantic_evaluator_not_live_for_source_dependent():
    pid = _verified_prompt_with_target(exercise_type="sentence_correction",
                                       source_text="The cat sat on the mat.")
    _assert_blocked(pid, "semantic_evaluator_not_live")


def test_blocked_paragraph_rubric_missing_and_gate_closed():
    pid = _verified_prompt_with_target(exercise_type="paragraph_writing")
    res = _activate_result(pid)
    assert res.get("eligible") is False, res
    assert "rubric_missing" in res["blockers"] and "paragraph_gate_closed" in res["blockers"], res
    assert _is_active(pid) == "f"


def test_blocked_already_active():
    pid = _verified_prompt_with_target()
    _activate(pid)
    assert _is_active(pid) == "t"
    res = _activate_result(pid)
    assert res.get("eligible") is False and "already_active" in res["blockers"], res


def test_blocked_invalid_scope_when_topic_inactivated_after_verify():
    # Verify with a valid scope, add an active target, then inactivate the topic.
    t = _scalar(
        f"INSERT INTO topics(subject_id,slug,name,level,is_active) "
        f"SELECT {_ENGLISH},'act-inactivation','act','topic',true RETURNING id;")
    pid = _create_id(_base_payload(topic_id=t))
    _review(pid, "pending", "verified")
    _add_active_target(pid)
    _psql(f"UPDATE topics SET is_active=false WHERE id='{t}';")
    _assert_blocked(pid, "invalid_scope")


def test_blocked_reason_required_writes_nothing():
    pid = _verified_prompt_with_target()
    res = _activate_result(pid, reason="short")  # < 8 chars
    assert res.get("eligible") is False and "reason_required" in res["blockers"], res
    assert _is_active(pid) == "f"


def test_caller_allowlist_can_only_narrow_not_widen():
    # An active, verified sentence_construction prompt is runtime-ready by the
    # SERVER table. A caller allowlist that excludes it must still block; it can
    # never widen to a type the server table omits.
    pid = _verified_prompt_with_target()
    res_narrow = json.loads(_scalar(
        f"SELECT cms_activate_writing_prompt('{pid}','{_prompt_updated_at(pid)}'::timestamptz,'{_REASON}',"
        f"ARRAY['sentence_correction']::text[],'{_ACTOR}'::uuid,'op@x')::text;"))
    assert res_narrow.get("eligible") is False
    assert "exercise_type_not_runtime_ready" in res_narrow["blockers"]
    assert _is_active(pid) == "f"


# ── CAS + not-found (hard errors, not blockers) ───────────────────────────────


def test_activate_requires_expected_updated_at():
    pid = _verified_prompt_with_target()
    proc = _activate(pid, updated_at="NULL")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr
    assert _is_active(pid) == "f"


def test_activate_stale_token_is_concurrent_modification():
    pid = _verified_prompt_with_target()
    proc = _activate(pid, updated_at="2000-01-01T00:00:00Z")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr
    assert _is_active(pid) == "f"


def test_activate_missing_prompt_is_not_found():
    proc = _activate("00000000-0000-0000-0000-0000000000ff",
                     updated_at="2026-07-01T00:00:00Z")
    assert proc.returncode != 0 and "not_found" in proc.stderr, proc.stderr


def test_deactivate_requires_expected_updated_at():
    pid = _verified_prompt_with_target()
    _activate(pid)
    proc = _deactivate(pid, updated_at="NULL")
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr, proc.stderr
    assert _is_active(pid) == "t"


def test_activate_null_actor_rejected():
    pid = _verified_prompt_with_target()
    ua = _prompt_updated_at(pid)
    proc = _try(f"SELECT cms_activate_writing_prompt('{pid}',{_ts(ua)},'{_REASON}',NULL,NULL,'op@x');")
    assert proc.returncode != 0 and "missing_actor_id" in proc.stderr, proc.stderr


# ── service-role-only privilege matrix ────────────────────────────────────────


def test_activation_rpcs_revoked_from_anon_and_authenticated():
    sigs = [
        "cms_activate_writing_prompt(uuid, timestamptz, text, text[], uuid, text)",
        "cms_deactivate_writing_prompt(uuid, timestamptz, text, uuid, text)",
        "cms_writing_runtime_ready_types()",
        "cms_writing_gate_open(text)",
    ]
    for sig in sigs:
        for role in ("anon", "authenticated"):
            ok = _scalar(f"SELECT has_function_privilege('{role}','{sig}','EXECUTE');")
            assert ok == "f", f"{role} must NOT execute {sig}"
        svc = _scalar(f"SELECT has_function_privilege('service_role','{sig}','EXECUTE');")
        assert svc == "t", f"service_role must execute {sig}"
