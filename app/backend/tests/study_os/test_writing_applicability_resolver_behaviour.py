"""Behavioural integration test for the EWP applicability resolver + the
migration-218 public-read lockdown.

Applies migrations 205 -> 213 -> 214 -> 215 -> 218 to a REAL Postgres (an
ISOLATED throwaway database, created/dropped per module — never the shared
EWP_PG_DSN db, because 214 destructively drops columns), seeds real
target rows through the actual schema (CHECK + unique index enforced), and
feeds those rows to the pure resolver
(`app.study_os.writing_practice.applicability.evaluate_targets`). This proves the
resolver's verdict against ACTUAL migration-applied data, plus:

  * DEFAULT-DENY: a prompt with no active target is not applicable; deleting the
    only active target (and cascading an exam delete) never widens to global.
  * explicit is_global -> applicable everywhere.
  * exclusion subtracts a narrower scope from a broader active scope.
  * pending_review / rejected targets never widen applicability.
  * phase vs exam-wide scoping isolation.
  * migration 218 removes `writing_prompts_public_read` so a non-service client
    (role `authenticated`) reads ZERO prompt rows — the raw-read bypass is gone.

The isolated chain applies 205 -> 213 -> 214 -> 215 -> 218 and DELIBERATELY
SKIPS 216/217: those are unrelated exam-intelligence migrations with no
dependency on 218 (or on any object this test touches), so replaying them here
would only add surface area. The live `schema_migrations` version number for
218 and the FULL real-database apply order remain operator-gated (VERIFY DB) —
this throwaway ordering proves the resolver + lockdown behaviour, not the
production migration sequence.

Runs in CI (backend job provides Postgres + EWP_PG_DSN). Locally, set EWP_PG_DSN
to a disposable superuser DB (and have psql). Skips otherwise. Every psql call
is behind an explicit timeout to prevent CI hangs.
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

from app.study_os.writing_practice import applicability

_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")
_MIG = Path(__file__).parents[3] / "supabase/migrations"

pytestmark = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)

# Isolated throwaway DB (per-xdist-worker name, though this repo runs pytest
# serially). 214 drops columns destructively; must never touch the shared db.
_OWN_DB = "wpt_resolver_it_" + re.sub(
    r"\W", "", os.environ.get("PYTEST_XDIST_WORKER", "main")
)

_EXAM = "00000000-0000-0000-0000-0000000000e1"
_EXAM2 = "00000000-0000-0000-0000-0000000000e2"
_FAMILY = "00000000-0000-0000-0000-0000000000f1"
_PHASE = "00000000-0000-0000-0000-0000000000c1"
_PHASE2 = "00000000-0000-0000-0000-0000000000c2"

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
CREATE TABLE IF NOT EXISTS public.exams (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), exam_family_id uuid REFERENCES public.exam_families(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS public.exam_cycles (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_phases (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.document_assets (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
-- study_tasks mirrors migration 034's exam-link shape (exam_id / exam_phase_id)
-- so the enforcement path's task rows type-check against the live column set.
CREATE TABLE IF NOT EXISTS public.study_tasks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, task_type text, exam_id uuid REFERENCES public.exams(id) ON DELETE SET NULL, exam_phase_id uuid REFERENCES public.exam_phases(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS public.subjects (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), slug text NOT NULL UNIQUE, name text NOT NULL, subject_group text, default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS public.topics (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), subject_id uuid NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE, parent_topic_id uuid REFERENCES public.topics(id) ON DELETE CASCADE, slug text NOT NULL, name text NOT NULL, level text NOT NULL DEFAULT 'topic' CHECK (level IN ('topic','microtopic','concept')), default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(subject_id, parent_topic_id, slug));
"""

_ENGLISH = "(SELECT id FROM subjects WHERE slug='english-language')"
_GRAMMAR = ("(SELECT id FROM topics WHERE slug='grammar' "
            "AND parent_topic_id IS NULL ORDER BY created_at LIMIT 1)")

_SEED = f"""
INSERT INTO exams(id) VALUES ('{_EXAM}'),('{_EXAM2}') ON CONFLICT DO NOTHING;
INSERT INTO exam_families(id) VALUES ('{_FAMILY}') ON CONFLICT DO NOTHING;
INSERT INTO exam_phases(id) VALUES ('{_PHASE}'),('{_PHASE2}') ON CONFLICT DO NOTHING;
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


def _scalar(sql: str) -> str:
    proc = subprocess.run([_PSQL, _DSN, "-t", "-A", "-X", "-q", "-c", sql],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    out = re.sub(r"\s*(?:INSERT|UPDATE|DELETE)\s+\d+\s+\d+\s*$", "", out)
    return out.strip()


def _admin_psql(sql: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_PSQL, _swap_dbname(_DSN, "postgres"), "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
        capture_output=True, text=True, timeout=180,
    )


def _new_prompt() -> str:
    return _scalar(f"""
    INSERT INTO writing_prompts(subject_id,topic_id,exercise_type,prompt_text,difficulty_level)
    SELECT {_ENGLISH}, {_GRAMMAR}, 'sentence_construction','p',1
    RETURNING id;""")


def _targets(prompt_id: str) -> list[dict]:
    raw = _scalar(
        f"""SELECT coalesce(jsonb_agg(to_jsonb(t)), '[]'::jsonb)
            FROM writing_prompt_targets t WHERE prompt_id='{prompt_id}'""")
    return json.loads(raw)


def _applicable(prompt_id: str, *, exam=None, phase=None, family=None) -> bool:
    return applicability.evaluate_targets(
        _targets(prompt_id), exam_id=exam, exam_phase_id=phase, exam_family_id=family
    )


# --------------------------------------------------------------------------- #
# Minimal service-role Supabase shim backed by REAL psql reads.               #
#                                                                             #
# Exercises the resolver's DB-facing path (`is_prompt_applicable`) end-to-end #
# against the live schema — the exams->exam_family_id join AND the            #
# writing_prompt_targets fetch run as actual SQL, not a hand-built fake dict. #
# It implements ONLY the two query shapes the resolver issues.                #
# --------------------------------------------------------------------------- #
class _PsqlResult:
    def __init__(self, data):
        self.data = data


class _PsqlQuery:
    def __init__(self, table: str):
        self._table = table
        self._cols = "*"
        self._eq: list[tuple[str, str]] = []
        self._in: tuple[str, list[str]] | None = None
        self._single = False

    def select(self, cols: str) -> "_PsqlQuery":
        self._cols = cols
        return self

    def eq(self, col: str, val) -> "_PsqlQuery":
        self._eq.append((col, str(val)))
        return self

    def in_(self, col: str, vals) -> "_PsqlQuery":
        self._in = (col, [str(v) for v in vals])
        return self

    def maybe_single(self) -> "_PsqlQuery":
        self._single = True
        return self

    def execute(self) -> _PsqlResult:
        where: list[str] = [f"{c} = '{v}'" for c, v in self._eq]
        if self._in is not None:
            col, vals = self._in
            where.append(
                f"{col} IN ({','.join(chr(39) + v + chr(39) for v in vals)})"
                if vals else "false"
            )
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        raw = _scalar(
            "SELECT coalesce(jsonb_agg(to_jsonb(t)), '[]'::jsonb) FROM "
            f"(SELECT {self._cols} FROM {self._table}{clause}) t"
        )
        rows = json.loads(raw)
        if self._single:
            return _PsqlResult(rows[0] if rows else None)
        return _PsqlResult(rows)


class _PsqlSupabase:
    def table(self, name: str) -> _PsqlQuery:
        return _PsqlQuery(name)


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
        _psql_file(_MIG / "205_english_writing_practice_schema.sql")
        _psql(_SEED)
        _psql_file(_MIG / "213_english_writing_practice_error_lab_read_model.sql")
        _psql_file(_MIG / "214_writing_prompt_content_scoping.sql")
        _psql_file(_MIG / "215_writing_prompt_content_studio_ops.sql")
        _psql_file(_MIG / "218_writing_prompts_public_read_lockdown.sql")
        # authenticated must have table privilege so the RLS check (not a GRANT
        # error) is what returns zero rows below.
        _psql("GRANT SELECT ON public.writing_prompts TO authenticated;")
        yield
    finally:
        _admin_psql(f"DROP DATABASE IF EXISTS {_OWN_DB} WITH (FORCE)")


# --------------------------------------------------------------------------- #
# Resolver over REAL rows.                                                     #
# --------------------------------------------------------------------------- #
def test_default_deny_no_target():
    pid = _new_prompt()
    assert _applicable(pid, exam=_EXAM) is False


def test_explicit_global_applies_everywhere():
    pid = _new_prompt()
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,is_global) VALUES ('{pid}',true);")
    assert _applicable(pid, exam=_EXAM) is True
    assert _applicable(pid, exam=_EXAM2, phase=_PHASE) is True
    assert _applicable(pid, exam=None) is True  # context-independent


def test_active_exam_target_applies_and_isolates():
    pid = _new_prompt()
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id) VALUES ('{pid}','{_EXAM}');")
    assert _applicable(pid, exam=_EXAM) is True
    assert _applicable(pid, exam=_EXAM2) is False


def test_pending_review_never_widens():
    pid = _new_prompt()
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id,applicability_status) "
          f"VALUES ('{pid}','{_EXAM}','pending_review');")
    assert _applicable(pid, exam=_EXAM) is False


def test_rejected_via_review_never_widens():
    # 'rejected' is not a target status; the closest inert operator state is
    # pending_review. Any status that is not active|excluded is inert — assert a
    # second inert row alongside a non-matching exam cannot widen.
    pid = _new_prompt()
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id,applicability_status) "
          f"VALUES ('{pid}','{_EXAM2}','active');")
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id,applicability_status) "
          f"VALUES ('{pid}','{_EXAM}','pending_review');")
    assert _applicable(pid, exam=_EXAM) is False  # only the OTHER exam is active


def test_exclusion_subtracts_from_global():
    pid = _new_prompt()
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,is_global) VALUES ('{pid}',true);")
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id,applicability_status) "
          f"VALUES ('{pid}','{_EXAM}','excluded');")
    assert _applicable(pid, exam=_EXAM) is False   # excluded here
    assert _applicable(pid, exam=_EXAM2) is True    # global still elsewhere


def test_phase_vs_exam_scoping_isolation():
    pid = _new_prompt()
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_phase_id) VALUES ('{pid}','{_PHASE}');")
    assert _applicable(pid, exam=_EXAM, phase=_PHASE) is True
    assert _applicable(pid, exam=_EXAM, phase=_PHASE2) is False
    assert _applicable(pid, exam=_EXAM, phase=None) is False


def test_target_deletion_never_widens_to_global():
    pid = _new_prompt()
    tid = _scalar(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id) "
                  f"VALUES ('{pid}','{_EXAM}') RETURNING id;")
    assert _applicable(pid, exam=_EXAM) is True
    _psql(f"DELETE FROM writing_prompt_targets WHERE id='{tid}';")
    assert _applicable(pid, exam=_EXAM) is False   # unassigned, not global


def test_exam_deletion_cascade_never_widens():
    pid = _new_prompt()
    ex = _scalar("INSERT INTO exams DEFAULT VALUES RETURNING id;")
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id) VALUES ('{pid}','{ex}');")
    assert _applicable(pid, exam=ex) is True
    _psql(f"DELETE FROM exams WHERE id='{ex}';")
    assert _applicable(pid, exam=ex) is False


# --------------------------------------------------------------------------- #
# DB-facing resolver path end-to-end (`is_prompt_applicable`) over REAL rows.  #
# Proves the exams->exam_family_id join + target fetch on the live schema, not #
# just the in-memory fake used by the unit test.                              #
# --------------------------------------------------------------------------- #
def test_is_prompt_applicable_end_to_end_over_real_rows():
    sb = _PsqlSupabase()
    pid = _new_prompt()
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_id) VALUES ('{pid}','{_EXAM}');")
    # The service-role client fetches the real target row and matches the exam.
    assert applicability.is_prompt_applicable(
        sb, pid, exam_id=_EXAM, exam_phase_id=None) is True
    assert applicability.is_prompt_applicable(
        sb, pid, exam_id=_EXAM2, exam_phase_id=None) is False
    # No exam context: a scoped prompt with no global target is denied.
    assert applicability.is_prompt_applicable(
        sb, pid, exam_id=None, exam_phase_id=None) is False


def test_is_prompt_applicable_resolves_exam_family_over_real_rows():
    sb = _PsqlSupabase()
    pid = _new_prompt()
    # _EXAM belongs to _FAMILY; the resolver must JOIN exams->exam_family_id to
    # match a family-scoped target. This drives that join through actual rows.
    _psql(f"UPDATE exams SET exam_family_id='{_FAMILY}' WHERE id='{_EXAM}';")
    _psql(f"INSERT INTO writing_prompt_targets(prompt_id,exam_family_id) VALUES ('{pid}','{_FAMILY}');")
    assert applicability.is_prompt_applicable(
        sb, pid, exam_id=_EXAM, exam_phase_id=None) is True
    # _EXAM2 has no family -> resolved family None -> the family target can't match.
    assert applicability.is_prompt_applicable(
        sb, pid, exam_id=_EXAM2, exam_phase_id=None) is False


# --------------------------------------------------------------------------- #
# Migration 218 — public-read lockdown.                                       #
# --------------------------------------------------------------------------- #
def test_public_read_policy_removed():
    n = _scalar("SELECT count(*) FROM pg_policies WHERE tablename='writing_prompts' "
                "AND policyname='writing_prompts_public_read'")
    assert n == "0", "migration 218 must drop writing_prompts_public_read"


def test_writing_prompts_rls_still_enabled():
    on = _scalar("SELECT relrowsecurity FROM pg_class "
                 "WHERE oid='public.writing_prompts'::regclass")
    assert on == "t", "RLS must remain ENABLED so no-policy fails closed"


def test_authenticated_client_reads_zero_prompt_rows():
    # Force a verified+active prompt to exist, then prove a non-service client
    # (role authenticated) can no longer read it directly — the bypass is closed.
    pid = _new_prompt()
    _psql(f"UPDATE writing_prompts SET reviewer_status='verified', is_active=true WHERE id='{pid}';")
    # service role / superuser sees it; authenticated (RLS-enforced) sees none.
    visible = _scalar(
        "SET ROLE authenticated; "
        "SELECT count(*) FROM public.writing_prompts; RESET ROLE;")
    assert visible == "0", f"authenticated must read 0 prompt rows post-218, saw {visible}"
