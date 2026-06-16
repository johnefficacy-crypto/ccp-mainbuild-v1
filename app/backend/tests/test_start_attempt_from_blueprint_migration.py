"""Schema-contract test for A-PR3 migration 178 (start_attempt_from_blueprint).

The repo has no live-DB migration harness; existing migration tests assert
against the migration SQL text. This pins the function signature, the atomic
step sequence, the idempotency guard, and the service_role-only execute grant
that the A-PR3 service depends on.

Manual SQL validation (run against a Supabase branch DB after apply):

  -- ready: returns (blueprint_id, attempt_id); blueprint row -> 'started',
  --        attempt row template_id NULL + generated_blueprint_id set,
  --        N mock_attempt_responses frozen.
  select * from public.start_attempt_from_blueprint(
    :uid, :exam, :phase, :blueprint_jsonb, :template_snapshot_jsonb,
    :response_rows_jsonb, now() + interval '24 hours');

  -- atomicity: a bad question_id cast inside p_response_rows aborts the whole
  --            call; assert zero blueprint/attempt/response rows persisted.

  -- idempotency: call twice with the same p_blueprint->>'id' -> one attempt.
"""

from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
SQL = (MIGRATIONS / "178_start_attempt_from_blueprint.sql").read_text().lower()


def test_function_signature_and_return_shape():
    assert "create or replace function public.start_attempt_from_blueprint(" in SQL
    for param in (
        "p_user",
        "p_exam",
        "p_exam_phase",
        "p_blueprint",
        "p_template_snapshot",
        "p_response_rows",
        "p_expires_at",
    ):
        assert param in SQL
    assert "returns table(blueprint_id uuid, attempt_id uuid)" in SQL


def test_security_definer_and_search_path():
    assert "language plpgsql" in SQL
    assert "security definer" in SQL
    assert "set search_path = public" in SQL


def test_inserts_blueprint_draft_with_content_columns():
    assert "insert into public.mock_generated_blueprints" in SQL
    assert "'draft'" in SQL
    for col in (
        "template_snapshot",
        "section_snapshot",
        "selector_snapshot",
        "question_ids",
        "readiness_snapshot",
        "expires_at",
    ):
        assert col in SQL


def test_inserts_attempt_with_null_template_and_blueprint_owner():
    assert "insert into public.mock_attempts" in SQL
    assert "generated_blueprint_id" in SQL
    assert "'in_progress'" in SQL
    # template_id is explicitly null in the attempt insert (XOR one-source).
    assert "p_user, null, v_blueprint_id" in SQL


def test_freezes_responses_and_flips_blueprint_started():
    assert "insert into public.mock_attempt_responses" in SQL
    assert "question_snapshot" in SQL
    assert "jsonb_array_elements(coalesce(p_response_rows" in SQL
    # status flip draft -> started happens only after the freeze.
    assert "set status = 'started'" in SQL


def test_idempotent_on_unique_violation():
    # The in_progress unique index (migration 175) is handled gracefully —
    # the existing attempt is returned rather than erroring.
    assert "exception when unique_violation then" in SQL
    assert "on conflict (id) do nothing" in SQL


def test_service_role_only_execute_grant():
    assert (
        "revoke all on function public.start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz) from public"
        in SQL
    )
    assert (
        "grant execute on function public.start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz) to service_role"
        in SQL
    )


def test_pgrst_reload_footer():
    assert "pg_notify('pgrst', 'reload schema')" in SQL
