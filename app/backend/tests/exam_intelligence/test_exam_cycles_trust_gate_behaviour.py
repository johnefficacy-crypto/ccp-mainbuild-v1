"""Behavioural integration test for migration 261 (exam_cycles trust gate).

Applies migration 261 to a real Postgres (over a hand-bootstrapped minimal
schema that stands in for the 030/035/210 lineage exam_cycles depends on) and
proves the trust gate end-to-end:

  - LEGACY GRANDFATHER: cycles that pre-exist the migration are back-filled to
    reviewer_status='verified'; a row inserted AFTER the migration defaults to
    'draft'. Re-applying 261 does NOT re-verify the post-migration draft
    (idempotent one-time backfill).
  - RLS: an authenticated non-admin sees ONLY verified cycles; an admin sees
    drafts too.
  - REVIEW RPC transitions: draft -> verified is rejected (must pass through
    reviewed); draft -> reviewed and reviewed -> verified (by a DIFFERENT actor)
    succeed and stamp reviewed_by/reviewed_at; a demotion to draft clears the
    stamp.
  - REVIEWER SEPARATION: reviewed -> verified by the cycle's own created_by is
    rejected (reviewer_is_creator); a cycle with NULL created_by cannot be
    verified at all (creator_missing — fail closed).
  - CAS + reason gate: a stale expected status is a concurrent_modification; a
    <8 char reason is invalid_reason.
  - BLOCK TRIGGER: editing reviewed content (exam_start) of a verified cycle
    while it stays verified raises P0422; changing operational `status` on a
    verified cycle is allowed (not reviewed content).
  - AUDIT: every review writes an admin_audit_logs row in the same transaction.

Runs in CI (the backend job provides Postgres + EWP_PG_DSN); locally set
EWP_PG_DSN to a disposable superuser DB. Skips when no DB is configured.
"""
from __future__ import annotations

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

# Per-xdist-worker isolated throwaway DB (see the writing_prompt behavioural
# suite for the rationale behind the worker-suffixed name).
_OWN_DB = "exam_cycles_trust_it_" + re.sub(
    r"\W", "", os.environ.get("PYTEST_XDIST_WORKER", "main")
)

_EXAM = "00000000-0000-0000-0000-0000000000e1"
_AUTHOR = "00000000-0000-0000-0000-00000000a001"    # auth.users / created_by
_REVIEWER = "00000000-0000-0000-0000-00000000a002"  # a distinct reviewer
_ADMIN_PROFILE = "00000000-0000-0000-0000-00000000ad01"
_USER_PROFILE = "00000000-0000-0000-0000-00000000ab01"
_LEGACY_CYCLE = "00000000-0000-0000-0000-0000000c1001"  # seeded BEFORE 261


# Minimal stand-in for the 030 exam_cycles table (+ 210's planner flag), plus the
# auth/profiles/exams/audit surfaces migration 261 references, and the permissive
# 035 read policy it must replace.
_BOOTSTRAP = f"""
DO $$ BEGIN CREATE ROLE authenticated LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE service_role LOGIN BYPASSRLS; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE anon LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA public TO authenticated, service_role, anon;

CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (
  id uuid PRIMARY KEY,
  raw_app_meta_data jsonb NOT NULL DEFAULT '{{}}'::jsonb
);
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $fn$
  SELECT NULLIF(current_setting('ewp.uid', true), '')::uuid $fn$;
CREATE OR REPLACE FUNCTION public.is_admin(uid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, auth AS $fn$
  SELECT EXISTS (
    SELECT 1 FROM auth.users
    WHERE id = uid
      AND raw_app_meta_data->>'role' IN ('admin', 'super_admin')
  )
$fn$;

CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid PRIMARY KEY,
  is_admin boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS public.exams (id uuid PRIMARY KEY DEFAULT gen_random_uuid());

CREATE TABLE IF NOT EXISTS public.exam_cycles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id uuid NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
  year integer,
  cycle_name text NOT NULL,
  status text NOT NULL DEFAULT 'expected'
    CHECK (status IN ('expected','open','active','closed','completed','cancelled')),
  notification_date date,
  application_start date,
  application_end date,
  exam_start date,
  exam_end date,
  source_url text,
  planner_activation_enabled boolean NOT NULL DEFAULT false,
  metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(exam_id, year, cycle_name)
);
ALTER TABLE public.exam_cycles ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON public.exam_cycles TO authenticated;
-- The permissive 035 policy that migration 261 must drop + replace.
CREATE POLICY exam_cycles_read_authenticated ON public.exam_cycles
  FOR SELECT TO authenticated USING (true);

CREATE TABLE IF NOT EXISTS public.admin_audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid,
  actor_email text,
  action text,
  entity_type text,
  entity_id text,
  new_value jsonb,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO auth.users(id, raw_app_meta_data) VALUES
  ('{_AUTHOR}', '{{}}'), ('{_REVIEWER}', '{{}}'),
  ('{_ADMIN_PROFILE}', '{{"role":"admin"}}'), ('{_USER_PROFILE}', '{{}}')
ON CONFLICT (id) DO UPDATE SET raw_app_meta_data = excluded.raw_app_meta_data;
INSERT INTO public.profiles(id, is_admin) VALUES
  ('{_ADMIN_PROFILE}', true), ('{_USER_PROFILE}', false) ON CONFLICT DO NOTHING;
INSERT INTO public.exams(id) VALUES ('{_EXAM}') ON CONFLICT DO NOTHING;

-- A cycle that PRE-EXISTS migration 261 -> must be grandfathered to verified.
INSERT INTO public.exam_cycles(id, exam_id, year, cycle_name, status, exam_start)
  VALUES ('{_LEGACY_CYCLE}', '{_EXAM}', 2025, 'Legacy 2025', 'open', '2025-09-01')
  ON CONFLICT DO NOTHING;
"""


def _swap_dbname(dsn: str, dbname: str) -> str:
    parts = _urlparse.urlsplit(dsn)
    if parts.scheme:
        return _urlparse.urlunsplit(
            (parts.scheme, parts.netloc, "/" + dbname, parts.query, parts.fragment)
        )
    if re.search(r"\bdbname=", dsn):
        return re.sub(r"\bdbname=\S+", "dbname=" + dbname, dsn)
    return dsn.rstrip() + " dbname=" + dbname


def _psql(sql: str) -> None:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"unexpected failure:\n{proc.stderr}"


def _psql_file(path: Path) -> None:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(path)],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"failed applying {path.name}:\n{proc.stderr}"


def _psql_try(sql: str) -> subprocess.CompletedProcess:
    return subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
                          capture_output=True, text=True, timeout=180)


def _scalar(sql: str) -> str:
    proc = subprocess.run([_PSQL, _DSN, "-t", "-A", "-X", "-q", "-c", sql],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _admin_psql(sql: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_PSQL, _swap_dbname(_DSN, "postgres"), "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
        capture_output=True, text=True, timeout=180,
    )


def _review(cycle_id: str, expected: str, target: str, actor: str,
            reason: str = "trust gate behavioural test review") -> subprocess.CompletedProcess:
    """Invoke the review RPC; return the completed process so callers assert."""
    return _psql_try(
        "SELECT public.review_exam_cycle("
        f"'{cycle_id}', '{expected}', '{target}', '{reason}', "
        f"'{actor}', 'actor@example.com')"
    )


def _new_cycle(name: str, created_by: str | None) -> str:
    """Insert a fresh cycle (post-migration -> defaults reviewer_status='draft')."""
    cb = f"'{created_by}'" if created_by else "NULL"
    return _scalar(
        "INSERT INTO public.exam_cycles(exam_id, year, cycle_name, status, exam_start, created_by) "
        f"VALUES ('{_EXAM}', 2026, '{name}', 'expected', '2026-09-01', {cb}) RETURNING id"
    )


@pytest.fixture(scope="module", autouse=True)
def _apply():
    global _DSN
    pre = _admin_psql(f"DROP DATABASE IF EXISTS {_OWN_DB} WITH (FORCE)")
    assert pre.returncode == 0, f"pre-drop failed:\n{pre.stderr}"
    created = _admin_psql(f"CREATE DATABASE {_OWN_DB}")
    assert created.returncode == 0, f"create failed:\n{created.stderr}"

    _DSN = _swap_dbname(_DSN, _OWN_DB)
    try:
        _psql(_BOOTSTRAP)
        _psql_file(_MIG / "261_exam_cycles_trust_gate.sql")
        yield
    finally:
        _admin_psql(f"DROP DATABASE IF EXISTS {_OWN_DB} WITH (FORCE)")


# ── legacy grandfather + default ────────────────────────────────────────────


def test_legacy_cycle_grandfathered_verified():
    assert _scalar(
        f"SELECT reviewer_status FROM public.exam_cycles WHERE id='{_LEGACY_CYCLE}'"
    ) == "verified"


def test_new_cycle_defaults_to_draft():
    cid = _new_cycle("Default Draft", _AUTHOR)
    assert _scalar(
        f"SELECT reviewer_status FROM public.exam_cycles WHERE id='{cid}'"
    ) == "draft"


def test_reapply_migration_does_not_reverify_new_draft():
    cid = _new_cycle("Idempotency Draft", _AUTHOR)
    _psql_file(_MIG / "261_exam_cycles_trust_gate.sql")  # second apply
    assert _scalar(
        f"SELECT reviewer_status FROM public.exam_cycles WHERE id='{cid}'"
    ) == "draft", "re-apply must not blanket-re-verify post-migration drafts"


# ── RLS verified-only ───────────────────────────────────────────────────────


def _count_as(role_uid: str) -> str:
    return _scalar(
        "SET ROLE authenticated; "
        f"SET ewp.uid = '{role_uid}'; "
        "SELECT count(*) FROM public.exam_cycles; RESET ROLE"
    )


def test_rls_non_admin_sees_only_verified():
    draft = _new_cycle("RLS Draft", _AUTHOR)
    # non-admin: only the verified legacy cycle(s), never the draft
    n = _scalar(
        "SET ROLE authenticated; "
        f"SET ewp.uid = '{_USER_PROFILE}'; "
        f"SELECT count(*) FROM public.exam_cycles WHERE id='{draft}'; RESET ROLE"
    )
    assert n == "0", "authenticated non-admin must not see a draft cycle"
    verified_visible = _scalar(
        "SET ROLE authenticated; "
        f"SET ewp.uid = '{_USER_PROFILE}'; "
        f"SELECT count(*) FROM public.exam_cycles WHERE id='{_LEGACY_CYCLE}'; RESET ROLE"
    )
    assert verified_visible == "1", "authenticated non-admin must see verified cycles"


def test_rls_admin_sees_draft():
    draft = _new_cycle("RLS Admin Draft", _AUTHOR)
    n = _scalar(
        "SET ROLE authenticated; "
        f"SET ewp.uid = '{_ADMIN_PROFILE}'; "
        f"SELECT count(*) FROM public.exam_cycles WHERE id='{draft}'; RESET ROLE"
    )
    assert n == "1", "admin must see draft cycles"


# ── review RPC transitions ──────────────────────────────────────────────────


def test_draft_cannot_jump_straight_to_verified():
    cid = _new_cycle("No Jump", _AUTHOR)
    proc = _review(cid, "draft", "verified", _REVIEWER)
    assert proc.returncode != 0 and "transition_not_allowed" in proc.stderr.lower()


def test_two_step_promotion_by_distinct_reviewer_stamps():
    cid = _new_cycle("Two Step", _AUTHOR)
    assert _review(cid, "draft", "reviewed", _REVIEWER).returncode == 0
    assert _scalar(f"SELECT reviewer_status FROM public.exam_cycles WHERE id='{cid}'") == "reviewed"
    assert _review(cid, "reviewed", "verified", _REVIEWER).returncode == 0
    row = _scalar(
        "SELECT reviewer_status||'|'||coalesce(reviewed_by::text,'')||'|'||"
        f"(reviewed_at IS NOT NULL)::text FROM public.exam_cycles WHERE id='{cid}'"
    )
    assert row == f"verified|{_REVIEWER}|true"


def test_demote_to_draft_clears_stamp():
    cid = _new_cycle("Demote", _AUTHOR)
    _review(cid, "draft", "reviewed", _REVIEWER)
    _review(cid, "reviewed", "verified", _REVIEWER)
    assert _review(cid, "verified", "draft", _REVIEWER).returncode == 0
    row = _scalar(
        "SELECT reviewer_status||'|'||coalesce(reviewed_by::text,'none')||'|'||"
        f"coalesce(reviewed_at::text,'none') FROM public.exam_cycles WHERE id='{cid}'"
    )
    assert row == "draft|none|none"


# ── reviewer separation (fail closed) ───────────────────────────────────────


def test_creator_cannot_verify_own_cycle():
    cid = _new_cycle("Self Verify", _AUTHOR)
    _review(cid, "draft", "reviewed", _AUTHOR)
    proc = _review(cid, "reviewed", "verified", _AUTHOR)
    assert proc.returncode != 0 and "reviewer_is_creator" in proc.stderr.lower()


def test_missing_creator_cannot_be_verified():
    cid = _new_cycle("No Author", None)
    _review(cid, "draft", "reviewed", _REVIEWER)
    proc = _review(cid, "reviewed", "verified", _REVIEWER)
    assert proc.returncode != 0 and "creator_missing" in proc.stderr.lower()


# ── CAS + reason gate ───────────────────────────────────────────────────────


def test_stale_expected_status_is_concurrent_modification():
    cid = _new_cycle("Stale CAS", _AUTHOR)
    proc = _review(cid, "reviewed", "verified", _REVIEWER)  # actual status is draft
    assert proc.returncode != 0 and "concurrent_modification" in proc.stderr.lower()


def test_short_reason_rejected():
    cid = _new_cycle("Short Reason", _AUTHOR)
    proc = _review(cid, "draft", "reviewed", _REVIEWER, reason="short")
    assert proc.returncode != 0 and "invalid_reason" in proc.stderr.lower()


# ── verified-material-edit block trigger ────────────────────────────────────


def test_editing_verified_cycle_content_is_blocked():
    proc = _psql_try(
        "UPDATE public.exam_cycles SET exam_start='2030-01-01' "
        f"WHERE id='{_LEGACY_CYCLE}'"
    )
    assert proc.returncode != 0 and "reviewed content of a reviewed or verified cycle" in proc.stderr.lower()


def test_editing_reviewed_cycle_content_is_blocked():
    cid = _new_cycle("Reviewed Edit Guard", _AUTHOR)
    assert _review(cid, "draft", "reviewed", _REVIEWER).returncode == 0
    proc = _psql_try(
        "UPDATE public.exam_cycles SET metadata='{\"tier\":\"changed\"}'::jsonb "
        f"WHERE id='{cid}'"
    )
    assert proc.returncode != 0 and "reviewed content of a reviewed or verified cycle" in proc.stderr.lower()


def test_source_provenance_edit_requires_demotion():
    proc = _psql_try(
        "UPDATE public.exam_cycles SET source_url='https://example.invalid/replaced' "
        f"WHERE id='{_LEGACY_CYCLE}'"
    )
    assert proc.returncode != 0 and "reviewed content of a reviewed or verified cycle" in proc.stderr.lower()


def test_operational_status_edit_on_verified_cycle_allowed():
    # operational status is NOT reviewed content -> the trigger must not block it
    assert _psql_try(
        f"UPDATE public.exam_cycles SET status='active' WHERE id='{_LEGACY_CYCLE}'"
    ).returncode == 0


# ── audit trail ─────────────────────────────────────────────────────────────


def test_review_writes_audit_row():
    cid = _new_cycle("Audited", _AUTHOR)
    _review(cid, "draft", "reviewed", _REVIEWER)
    n = _scalar(
        "SELECT count(*) FROM public.admin_audit_logs "
        f"WHERE entity_id='{cid}' AND action='exam_intel.cms.cycle.review'"
    )
    assert n == "1"
