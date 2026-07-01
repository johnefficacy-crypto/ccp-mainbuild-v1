"""Behavioural integration test for the EWP-2 atomic runtime RPCs (migration 206).

Applies migrations 205 + 206 to a real Postgres and exercises the contracts
that substring inspection cannot prove: exam-mode rejection, the version CAS
(mandatory token, stale/duplicate rejection), the in-DB unit state machine, the
in-transaction session rollup (submit/reopen never leave a stale session
status), the completion gate, authoritative-coverage staleness by
version_set_hash, in-DB/Python version_set_hash parity, and user isolation.

Runs in CI (the backend job provides a Postgres service and sets
``EWP_PG_DSN``); locally set ``EWP_PG_DSN`` to a disposable Postgres superuser
DB. Skips only when no database is configured, so it never blocks environments
without one.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import struct
import subprocess
import uuid
from pathlib import Path

import pytest

_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")
_MIG_DIR = Path(__file__).parents[3] / "supabase/migrations"
_M205 = _MIG_DIR / "205_english_writing_practice_schema.sql"
_M206 = _MIG_DIR / "206_english_writing_practice_rpcs.sql"

pytestmark = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)

_A = "00000000-0000-0000-0000-0000000000aa"   # owner
_B = "00000000-0000-0000-0000-0000000000bb"   # other user
_PROMPT = "00000000-0000-0000-0000-0000000000d1"
_HEX = "a" * 64

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
INSERT INTO profiles(id) VALUES ('{_A}'), ('{_B}') ON CONFLICT DO NOTHING;
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


def _fails_with(sql: str, token: str) -> None:
    proc = _psql(sql, expect_ok=False)
    assert token in proc.stderr, f"expected {token!r} in:\n{proc.stderr}"


@pytest.fixture(scope="module", autouse=True)
def _apply():
    _psql(_BOOTSTRAP)
    _psql_file(_M205)
    _psql_file(_M206)
    _psql_file(_M206)  # idempotent re-apply
    _psql(_FIXTURES)
    yield


def _create(mode: str = "learning", units: int = 2) -> str:
    return _scalar(
        f"SELECT (ewp_create_writing_session('{_A}','{_PROMPT}',NULL,'{mode}',1,'immediate',"
        f"NULL,{units},NULL,'{{\"schema_version\":1}}'::jsonb))->>'id'"
    )


def _submit(sid: str, unit: int, text: str, ch: str, expected, *, expect_ok=True):
    ev = "NULL" if expected is None else str(expected)
    sql = (
        f"SELECT ewp_submit_writing_unit('{_A}','{sid}',{unit},'{text}',{len(text.split())},"
        f"{len(text.split())},'{ch}',{ev},'{{}}'::jsonb,'det-v1')"
    )
    return _psql(sql, expect_ok=expect_ok)


def test_exam_mode_rejected():
    _fails_with(
        f"SELECT ewp_create_writing_session('{_A}','{_PROMPT}',NULL,'exam',1,'immediate',"
        "NULL,2,NULL,'{}'::jsonb)",
        "ewp_mode_unsupported",
    )


def test_create_is_atomic_session_plus_units():
    sid = _create(units=2)
    assert _scalar(f"SELECT count(*) FROM writing_session_units WHERE session_id='{sid}'") == "2"
    assert _scalar(f"SELECT status FROM writing_sessions WHERE id='{sid}'") == "active"


def test_submit_transitions_unit_and_rolls_session_up():
    sid = _create(units=2)
    _submit(sid, 1, "The cat sat.", "a" * 64, 1)
    assert _scalar(
        f"SELECT status FROM writing_session_units WHERE session_id='{sid}' AND unit_number=1"
    ) == "evaluation_pending"
    # unit 2 still not_started -> session active (in-transaction rollup, §4.3b rule 1).
    assert _scalar(f"SELECT status FROM writing_sessions WHERE id='{sid}'") == "active"


def test_mandatory_cas_rejects_null_and_stale():
    sid = _create(units=1)
    _submit(sid, 1, "x y z", "b" * 64, None, expect_ok=False)   # missing token
    _submit(sid, 1, "x y z", "c" * 64, 9, expect_ok=False)      # stale token (next is 1)
    _submit(sid, 1, "x y z", "d" * 64, 1)                       # correct -> ok


def test_duplicate_submit_on_pending_is_rejected():
    sid = _create(units=1)
    _submit(sid, 1, "first answer here", "e" * 64, 1)
    # unit is now evaluation_pending; a duplicate/retry cannot mint another version.
    _fails_with(
        f"SELECT ewp_submit_writing_unit('{_A}','{sid}',1,'dup','1','1','{'f' * 64}',2,'{{}}'::jsonb,'det-v1')",
        "ewp_not_submittable",
    )


def test_completion_gate_and_reopen_rollback_are_atomic():
    sid = _create(units=1)
    _submit(sid, 1, "The cat sat.", "a" * 64, 1)
    unit = _scalar(f"SELECT id FROM writing_session_units WHERE session_id='{sid}' AND unit_number=1")
    ver = _scalar(f"SELECT id FROM writing_unit_versions WHERE unit_id='{unit}'")
    ev = _scalar(f"SELECT id FROM writing_evaluations WHERE unit_version_id='{ver}'")
    vsh = _scalar(f"SELECT ewp_private.ewp_version_set_hash('{sid}')")
    # simulate the worker terminalising the evaluation + a passing coverage row.
    _psql(
        f"UPDATE writing_evaluations SET overall_status='completed', language_status='completed' WHERE id='{ev}';"
        f"UPDATE writing_session_units SET status='ready' WHERE id='{unit}';"
        f"INSERT INTO writing_session_checks(session_id,check_type,version_set_hash,passed,details,checker_version) "
        f"VALUES ('{sid}','required_word_coverage','{vsh}',true,'{{}}'::jsonb,'coverage-v1');"
    )
    out = _scalar(f"SELECT ewp_finalize_writing_session('{_A}','{sid}')")
    assert '"status": "completed"' in out and '"evaluation_outcome": "fully_evaluated"' in out

    # reopen the ready unit -> draft AND session rolls back to active atomically;
    # outcome is monotonic (never downgraded).
    _scalar(f"SELECT ewp_reopen_writing_unit('{_A}','{sid}','{unit}','{ver}')")
    assert _scalar(f"SELECT status FROM writing_session_units WHERE id='{unit}'") == "draft"
    assert _scalar(f"SELECT status FROM writing_sessions WHERE id='{sid}'") == "active"
    assert _scalar(f"SELECT evaluation_outcome FROM writing_sessions WHERE id='{sid}'") == "fully_evaluated"


def test_stale_coverage_hash_blocks_completion():
    sid = _create(units=1)
    _submit(sid, 1, "The cat sat.", "a" * 64, 1)
    unit = _scalar(f"SELECT id FROM writing_session_units WHERE session_id='{sid}' AND unit_number=1")
    ver1 = _scalar(f"SELECT id FROM writing_unit_versions WHERE unit_id='{unit}'")
    stale_hash = _scalar(f"SELECT ewp_private.ewp_version_set_hash('{sid}')")
    # write a passing coverage row for THIS version set, then supersede it.
    _psql(
        f"INSERT INTO writing_session_checks(session_id,check_type,version_set_hash,passed,details,checker_version) "
        f"VALUES ('{sid}','required_word_coverage','{stale_hash}',true,'{{}}'::jsonb,'coverage-v1');"
    )
    # a rewrite changes the version_set_hash; mark the unit ready + eval terminal.
    _psql(f"UPDATE writing_session_units SET status='rewrite_required' WHERE id='{unit}'")
    _submit(sid, 1, "A dog ran fast today.", "d" * 64, 2)
    ver2 = _scalar(f"SELECT id FROM writing_unit_versions WHERE unit_id='{unit}' ORDER BY version_number DESC LIMIT 1")
    ev2 = _scalar(f"SELECT id FROM writing_evaluations WHERE unit_version_id='{ver2}'")
    _psql(
        f"UPDATE writing_evaluations SET overall_status='completed' WHERE id='{ev2}';"
        f"UPDATE writing_session_units SET status='ready' WHERE id='{unit}';"
    )
    # coverage row is pinned to the OLD hash -> not authoritative -> not completed.
    out = _scalar(f"SELECT ewp_finalize_writing_session('{_A}','{sid}')")
    assert '"status": "rewrite_required"' in out
    assert ver1 != ver2


def test_version_set_hash_matches_python_layout():
    sid = _create(units=1)
    _submit(sid, 1, "hash parity check", "a" * 64, 1)
    db_hash = _scalar(f"SELECT ewp_private.ewp_version_set_hash('{sid}')")
    unit = _scalar(f"SELECT id FROM writing_session_units WHERE session_id='{sid}' AND unit_number=1")
    ver = _scalar(f"SELECT id FROM writing_unit_versions WHERE unit_id='{unit}'")
    ch = _scalar(f"SELECT content_hash FROM writing_unit_versions WHERE id='{ver}'")
    payload = bytearray(b"WPS_VERSION_SET_V1\x00") + struct.pack(">I", 1)
    payload += struct.pack(">I", 1) + uuid.UUID(unit).bytes + uuid.UUID(ver).bytes + bytes.fromhex(ch)
    assert db_hash == hashlib.sha256(bytes(payload)).hexdigest()


def test_user_isolation_on_write_paths():
    sid = _create(units=1)
    # a different user cannot submit, reopen, or finalize this session.
    _fails_with(
        f"SELECT ewp_submit_writing_unit('{_B}','{sid}',1,'x','1','1','{'a' * 64}',1,'{{}}'::jsonb,'det-v1')",
        "ewp_not_found",
    )
    _fails_with(f"SELECT ewp_finalize_writing_session('{_B}','{sid}')", "ewp_not_found")


def test_concurrent_duplicate_submit_serialized_by_lock():
    """Two connections race the SAME first submission (expected_version=1).

    The canonical session-row FOR UPDATE lock serializes them: whichever commits
    first mints version 1 and advances the unit to evaluation_pending; the other
    blocks, then is rejected — either by the submittable-status guard (the unit
    is now evaluation_pending: ewp_not_submittable) or, if it re-read as a
    resubmittable state, by the CAS (next is 2, expected 1: ewp_stale_version).
    Exactly one wins; never a lost update or a duplicate version 1.
    """
    sid = _create(units=1)
    call = (
        f"SELECT ewp_submit_writing_unit('{_A}','{sid}',1,'racing answer text',3,3,"
        f"'{'a' * 64}',1,'{{}}'::jsonb,'det-v1')"
    )
    # Fire both simultaneously so they genuinely contend on the session lock.
    procs = [
        subprocess.Popen(
            [_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", call],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        for _ in range(2)
    ]
    results = [(p.wait(), p.communicate()[1]) for p in procs]
    rcs = [rc for rc, _ in results]
    assert rcs.count(0) == 1, f"exactly one submit must win: {results}"
    loser_err = next(err for rc, err in results if rc != 0)
    assert ("ewp_not_submittable" in loser_err) or ("ewp_stale_version" in loser_err), loser_err
    # exactly one version 1, unit advanced to evaluation_pending.
    assert _scalar(
        f"SELECT count(*) FROM writing_unit_versions v JOIN writing_session_units u ON u.id=v.unit_id "
        f"WHERE u.session_id='{sid}' AND v.version_number=1"
    ) == "1"
    assert _scalar(
        f"SELECT status FROM writing_session_units WHERE session_id='{sid}' AND unit_number=1"
    ) == "evaluation_pending"


def test_public_rpcs_execute_only_for_service_role():
    # authenticated/anon must not be able to call the write RPCs directly.
    for role in ("authenticated", "anon"):
        _psql(
            f"SET ROLE {role}; "
            f"SELECT ewp_create_writing_session('{_A}','{_PROMPT}',NULL,'learning',1,'immediate',"
            "NULL,1,NULL,'{}'::jsonb)",
            expect_ok=False,
        )
