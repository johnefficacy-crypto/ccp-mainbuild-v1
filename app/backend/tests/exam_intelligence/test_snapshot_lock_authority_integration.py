"""PostgreSQL integration tests for migration 206: snapshot lock-authority guards.

Applies migrations 204 + 206 against a disposable PostgreSQL 16 database and
verifies:

  Guard A — stale-model rejection on reviewed→locked
  Guard B — superseded-snapshot rejection (strictly newer + equal-timestamp)
  Concurrency — advisory lock serialises two concurrent reviewed→locked attempts
                on equal-computed_at rows in the same scope; exactly one wins,
                the other gets superseded_snapshot, no orphan audit row is left

Set SNAP_LOCK_PG_DSN to a superuser connection string for a disposable Postgres
database to run these tests.  CI sets it automatically (see ci.yml).

Example:
    export SNAP_LOCK_PG_DSN=postgresql://postgres:postgres@localhost:5432/snap_lock_it
    pytest tests/exam_intelligence/test_snapshot_lock_authority_integration.py -v
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

import pytest

# ─── DSN guard ───────────────────────────────────────────────────────────────

_DSN  = os.environ.get("SNAP_LOCK_PG_DSN")
_PSQL = shutil.which("psql")

pytestmark = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason=(
        "set SNAP_LOCK_PG_DSN to a disposable Postgres superuser DB "
        "(and have psql in PATH) to run snapshot lock-authority integration tests"
    ),
)

# ─── Deterministic IDs ───────────────────────────────────────────────────────

_EXAM_ID    = "00000000-0000-0000-0001-000000000001"
_TOPIC_ID   = "00000000-0000-0000-0002-000000000001"
_ACTOR_ID   = "00000000-0000-0000-0003-000000000001"
_SNAP_OLD   = "00000000-0000-0000-0004-000000000001"  # computed_at = T1 (older)
_SNAP_NEW   = "00000000-0000-0000-0004-000000000002"  # computed_at = T2 (newer)
_SNAP_STALE = "00000000-0000-0000-0004-000000000003"  # stale model_version
_SNAP_EQ_A  = "00000000-0000-0000-0004-000000000004"  # equal computed_at — row A
_SNAP_EQ_B  = "00000000-0000-0000-0004-000000000005"  # equal computed_at — row B

_MODEL_VERSION = "v1.0"
_STALE_VERSION = "v0.9"

_T1 = "2026-05-01T00:00:00+00:00"
_T2 = "2026-05-02T00:00:00+00:00"
_T_EQ = "2026-05-03T00:00:00+00:00"  # shared timestamp for equal-ts test

# ─── SQL helpers ─────────────────────────────────────────────────────────────

_MIGRATIONS = Path(__file__).parents[3] / "supabase" / "migrations"
_M204 = _MIGRATIONS / "204_atomic_snapshot_review_transition.sql"
_M206 = _MIGRATIONS / "206_snapshot_lock_authority_guards.sql"


def _psql(sql: str, *, expect_ok: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
        capture_output=True, text=True,
    )
    if expect_ok:
        assert proc.returncode == 0, f"unexpected psql failure:\n{proc.stderr}"
    else:
        assert proc.returncode != 0, f"expected psql failure but succeeded:\n{proc.stdout}"
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


def _rpc_call(snap_id: str, new_status: str, *, notes: str | None = None) -> str:
    """Run the RPC as service_role and return the raw psql output."""
    notes_sql = "NULL" if notes is None else f"'{notes}'"
    sql = (
        f"SELECT cms_review_exam_topic_snapshot("
        f"'{snap_id}'::uuid, "
        f"(SELECT status FROM exam_topic_score_snapshots WHERE id='{snap_id}'), "
        f"'{new_status}', "
        f"{notes_sql}, "
        f"'{_ACTOR_ID}'::uuid, "
        f"'test@test.com', "
        f"'{_MODEL_VERSION}'"
        f");"
    )
    proc = subprocess.run(
        [_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-t", "-A", "-c",
         f"SET ROLE service_role; {sql}"],
        capture_output=True, text=True,
    )
    return proc


# ─── Bootstrap SQL ───────────────────────────────────────────────────────────

_BOOTSTRAP = f"""
-- Roles (idempotent)
DO $$ BEGIN CREATE ROLE authenticated LOGIN;      EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE service_role LOGIN BYPASSRLS; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE anon LOGIN;               EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA public TO authenticated, service_role, anon;

-- Minimal stub: admin_audit_logs
CREATE TABLE IF NOT EXISTS public.admin_audit_logs (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id       uuid,
    actor_email    text,
    admin_user_id  uuid,
    action         text,
    entity_type    text,
    entity_id      text,
    old_value      jsonb,
    new_value      jsonb,
    notes          text,
    created_at     timestamptz DEFAULT now()
);

-- Minimal stub: exam_topic_score_snapshots
CREATE TABLE IF NOT EXISTS public.exam_topic_score_snapshots (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id             uuid NOT NULL,
    exam_phase_id       uuid,
    topic_id            uuid NOT NULL,
    status              text NOT NULL DEFAULT 'draft',
    model_version       text,
    computed_at         timestamptz,
    reviewed_by         uuid,
    reviewed_at         timestamptz,
    reviewer_notes      text,
    exam_priority_score numeric,
    is_high_yield       boolean,
    confidence_score    numeric,
    evidence_count      int,
    score_components    jsonb,
    input_summary       jsonb
);

GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO service_role;
"""

_FIXTURES = f"""
-- Seed rows (idempotent via ON CONFLICT DO NOTHING)
INSERT INTO public.exam_topic_score_snapshots
    (id, exam_id, topic_id, exam_phase_id, status, model_version, computed_at)
VALUES
    ('{_SNAP_OLD}',   '{_EXAM_ID}', '{_TOPIC_ID}', NULL, 'reviewed', '{_MODEL_VERSION}', '{_T1}'),
    ('{_SNAP_NEW}',   '{_EXAM_ID}', '{_TOPIC_ID}', NULL, 'reviewed', '{_MODEL_VERSION}', '{_T2}'),
    ('{_SNAP_STALE}', '{_EXAM_ID}', '{_TOPIC_ID}', NULL, 'reviewed', '{_STALE_VERSION}', '{_T2}'),
    ('{_SNAP_EQ_A}',  '{_EXAM_ID}', '{_TOPIC_ID}', NULL, 'reviewed', '{_MODEL_VERSION}', '{_T_EQ}'),
    ('{_SNAP_EQ_B}',  '{_EXAM_ID}', '{_TOPIC_ID}', NULL, 'reviewed', '{_MODEL_VERSION}', '{_T_EQ}')
ON CONFLICT DO NOTHING;
"""

_RESET_FIXTURES = f"""
-- Reset all seed rows to 'reviewed' and clear audit log
DELETE FROM public.admin_audit_logs;
UPDATE public.exam_topic_score_snapshots
    SET status='reviewed', reviewed_by=NULL, reviewed_at=NULL, reviewer_notes=NULL
WHERE id IN (
    '{_SNAP_OLD}', '{_SNAP_NEW}', '{_SNAP_STALE}',
    '{_SNAP_EQ_A}', '{_SNAP_EQ_B}'
);
UPDATE public.exam_topic_score_snapshots
    SET model_version='{_STALE_VERSION}'
WHERE id = '{_SNAP_STALE}';
"""


# ─── Module fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def _apply():
    """Apply bootstrap + migrations 204 and 206 once for the module."""
    _psql(_BOOTSTRAP)
    _psql_file(_M204)
    _psql_file(_M206)
    _psql(_FIXTURES)
    yield


@pytest.fixture(autouse=True)
def _reset():
    """Reset fixture rows and audit log before each test."""
    yield
    _psql(_RESET_FIXTURES)


# ─── Guard A tests ───────────────────────────────────────────────────────────

def test_guard_a_rejects_stale_model_version():
    """reviewed→locked with a stale model_version raises stale_model_version."""
    proc = _rpc_call(_SNAP_STALE, "locked")
    assert proc.returncode != 0
    assert "stale_model_version" in proc.stderr


def test_guard_a_allows_draft_to_reviewed_regardless_of_model():
    """draft→reviewed always succeeds regardless of model_version (Guard A inactive)."""
    # Put SNAP_STALE into draft first.
    _psql(f"UPDATE public.exam_topic_score_snapshots SET status='draft' WHERE id='{_SNAP_STALE}';")
    proc = subprocess.run(
        [_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-t", "-A", "-c",
         f"SET ROLE service_role; "
         f"SELECT cms_review_exam_topic_snapshot("
         f"'{_SNAP_STALE}'::uuid,'draft','reviewed',NULL,"
         f"'{_ACTOR_ID}'::uuid,'test@test.com','{_MODEL_VERSION}');"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"draft→reviewed must succeed for stale model: {proc.stderr}"
    assert "true" in proc.stdout


# ─── Guard B tests ────────────────────────────────────────────────────────────

def test_guard_b_allows_lock_when_no_newer_exists():
    """reviewed→locked succeeds when no newer locked row exists in scope."""
    proc = _rpc_call(_SNAP_OLD, "locked")
    assert proc.returncode == 0, f"expected success: {proc.stderr}"
    status = _scalar(f"SELECT status FROM exam_topic_score_snapshots WHERE id='{_SNAP_OLD}'")
    assert status == "locked"


def test_guard_b_rejects_when_newer_locked_exists():
    """reviewed→locked fails when a newer locked row already exists for the same scope."""
    # Lock the newer row first.
    r = _rpc_call(_SNAP_NEW, "locked")
    assert r.returncode == 0, f"setup failed: {r.stderr}"
    # Now attempt to lock the older row — Guard B must reject.
    proc = _rpc_call(_SNAP_OLD, "locked")
    assert proc.returncode != 0
    assert "superseded_snapshot" in proc.stderr


def test_guard_b_rejects_equal_computed_at():
    """reviewed→locked fails when a locked row with the SAME computed_at exists (>= contract)."""
    # Lock EQ_A first.
    r = _rpc_call(_SNAP_EQ_A, "locked")
    assert r.returncode == 0, f"setup failed: {r.stderr}"
    # EQ_B has the same computed_at — Guard B must reject it.
    proc = _rpc_call(_SNAP_EQ_B, "locked")
    assert proc.returncode != 0
    assert "superseded_snapshot" in proc.stderr


def test_guard_b_locked_to_reviewed_always_allowed():
    """locked→reviewed reversal succeeds even when a newer locked row exists."""
    # Lock OLD, then lock NEW.
    _rpc_call(_SNAP_OLD, "locked")
    _rpc_call(_SNAP_NEW, "locked")
    # Revert OLD (the superseded one) — must succeed.
    proc = _rpc_call(_SNAP_OLD, "reviewed", notes="reverting for correction")
    assert proc.returncode == 0, f"locked→reviewed must always succeed: {proc.stderr}"


def test_guard_b_no_orphan_audit_on_rejection():
    """When Guard B rejects, no orphan audit row is written."""
    # Lock the newer row.
    _rpc_call(_SNAP_NEW, "locked")
    audit_before = _scalar("SELECT count(*) FROM admin_audit_logs")
    # Attempt (and fail) to lock the older row.
    _rpc_call(_SNAP_OLD, "locked")  # will fail; returncode ignored
    audit_after = _scalar("SELECT count(*) FROM admin_audit_logs")
    assert audit_before == audit_after, (
        f"audit log grew from {audit_before} to {audit_after} on a Guard B rejection"
    )


# ─── Concurrency test ─────────────────────────────────────────────────────────

def test_concurrent_lock_equal_computed_at_exactly_one_winner():
    """Advisory lock serialises two concurrent reviewed→locked attempts on equal-computed_at rows.

    Both EQ_A and EQ_B are in the same scope with identical computed_at.  When
    attempted concurrently, pg_advisory_xact_lock ensures they are serialised:
    exactly one wins and the other receives superseded_snapshot.  No orphan
    audit row must be written for the loser.
    """
    try:
        import asyncpg  # noqa: PLC0415
    except ImportError:  # pragma: no cover
        pytest.skip("asyncpg not installed — cannot run concurrency test")

    async def _try_lock(snap_id: str) -> tuple[str, str]:
        """Return ('ok', jsonb_text) or ('err', error_message)."""
        conn = await asyncpg.connect(_DSN)
        try:
            result = await conn.fetchval(
                "SELECT cms_review_exam_topic_snapshot("
                "$1, 'reviewed', 'locked', NULL, $2, 'test@test.com', $3)",
                snap_id, _ACTOR_ID, _MODEL_VERSION,
            )
            return ("ok", str(result))
        except asyncpg.PostgresError as exc:
            return ("err", exc.message)
        finally:
            await conn.close()

    async def _race() -> tuple[tuple, tuple]:
        return await asyncio.gather(
            _try_lock(_SNAP_EQ_A),
            _try_lock(_SNAP_EQ_B),
        )

    results = asyncio.run(_race())
    outcomes = [r[0] for r in results]
    errors   = [r[1] for r in results if r[0] == "err"]

    # Exactly one success, one failure.
    assert outcomes.count("ok")  == 1, f"expected 1 success, got: {results}"
    assert outcomes.count("err") == 1, f"expected 1 failure, got: {results}"
    assert any("superseded_snapshot" in e for e in errors), (
        f"losing attempt must raise superseded_snapshot, got: {errors}"
    )

    # Exactly one locked row in scope, exactly one audit row for the winner.
    locked_count = _scalar(
        f"SELECT count(*) FROM exam_topic_score_snapshots "
        f"WHERE id IN ('{_SNAP_EQ_A}','{_SNAP_EQ_B}') AND status='locked'"
    )
    audit_count = _scalar(
        f"SELECT count(*) FROM admin_audit_logs "
        f"WHERE entity_id IN ('{_SNAP_EQ_A}','{_SNAP_EQ_B}')"
    )
    assert locked_count == "1", f"expected exactly 1 locked row, got {locked_count}"
    assert audit_count  == "1", f"expected exactly 1 audit row (no orphan), got {audit_count}"
