"""Schema-contract tests for migration 252
(service_role SELECT grant on pyq_mock_question_projections).

Migration 183 created the projection-bridge table and granted service_role
EXECUTE on the projection RPCs, but never granted it any TABLE privilege. The
backend reads the table directly with the service-role client to gate learner
PYQ practice, so the read failed with `42501 permission denied` on any database
where service_role relies on explicit grants — silently failing practice
readiness closed and 500ing the launch wherever projected PYQ data exists.

249 grants SELECT only, preserving the 183 posture that writes flow solely
through the SECURITY DEFINER project_pyq_question_to_mock_bank() RPC.

Following the repo convention (no live-DB migration harness): assert against the
migration SQL text. Migration 183 is MERGED + IMMUTABLE — the fix lives only in
the forward migration (249).
"""
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"

MIGRATION = (
    _MIGRATIONS / "252_pyq_projection_service_role_read_grant.sql"
).read_text()


def test_grants_select_to_service_role():
    low = " ".join(MIGRATION.lower().split())
    assert (
        "grant select on public.pyq_mock_question_projections to service_role"
        in low
    )


def test_does_not_grant_write_privileges():
    # Writes must stay RPC-only (183 posture): the read grant must not smuggle in
    # direct DML for service_role on the projection table.
    low = MIGRATION.lower()
    for verb in ("insert", "update", "delete", "grant all"):
        assert f"grant {verb}" not in low, f"249 must not grant {verb} on the projection table"
    assert "grant all on public.pyq_mock_question_projections" not in low
