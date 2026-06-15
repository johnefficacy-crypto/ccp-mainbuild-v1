"""Schema-contract tests for A-PR0 generated-mock blueprint migrations.

The repo has no live-DB migration harness; existing migration tests
(``test_migrations_contract.py``, ``test_subscription_active_invariant.py``)
assert against the migration SQL text. These follow the same style and pin the
schema decisions that later PRs (start_attempt_from_blueprint, generator,
cleanup sweeper) depend on.

Manual SQL validation (run against a Supabase branch DB after apply):

  -- 2. template-backed attempt still valid (template_id set, blueprint null)
  insert into mock_attempts(user_id, template_id, template_snapshot, expires_at)
    values (:uid, :tid, '{}'::jsonb, now() + interval '1 hour');   -- OK

  -- 3. both ids set -> rejected by mock_attempts_one_source_chk
  insert into mock_attempts(user_id, template_id, generated_blueprint_id,
                            template_snapshot, expires_at)
    values (:uid, :tid, :bpid, '{}'::jsonb, now() + interval '1 hour'); -- ERROR

  -- 4. neither id set -> rejected by mock_attempts_one_source_chk
  insert into mock_attempts(user_id, template_snapshot, expires_at)
    values (:uid, '{}'::jsonb, now() + interval '1 hour');          -- ERROR

  -- 5. second in_progress for same (user_id, generated_blueprint_id) -> rejected
  --    by uq_mock_attempts_active_blueprint
  -- 6. second in_progress for same (user_id, template_id) -> still rejected by
  --    pre-existing uq_mock_attempts_active
  -- 7. mismatched (generated_blueprint_id, user_id) -> rejected by
  --    mock_attempts_generated_blueprint_owner_fkey
  -- 8. RLS: wrap role + jwt claims + select in BEGIN/ROLLBACK (see AGENTS.md).
"""

from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
BLUEPRINTS = (MIGRATIONS / "174_mock_generated_blueprints.sql").read_text().lower()
ATTEMPTS = (MIGRATIONS / "175_mock_attempts_generated_blueprint.sql").read_text().lower()


# ── Migration 174: mock_generated_blueprints ─────────────────────────────────

def test_blueprints_table_created_with_owner_profile_fk():
    assert "create table if not exists public.mock_generated_blueprints" in BLUEPRINTS
    # newer owner-scoped convention -> profiles(id), NOT auth.users(id)
    assert "user_id uuid not null\n    references public.profiles(id) on delete cascade" in BLUEPRINTS


def test_blueprints_exam_and_phase_fks():
    assert "references public.exams(id) on delete set null" in BLUEPRINTS
    assert "references public.exam_phases(id) on delete set null" in BLUEPRINTS


def test_blueprints_check_constraints():
    assert "check (source in ('exam_realistic','personalized'))" in BLUEPRINTS
    assert "check (status in ('draft','started','expired','cancelled'))" in BLUEPRINTS
    assert "default 'draft'" in BLUEPRINTS


def test_blueprints_snapshot_columns():
    for col in (
        "template_snapshot",
        "section_snapshot",
        "selector_snapshot",
        "question_ids",
        "readiness_snapshot",
    ):
        assert col in BLUEPRINTS
    assert "uuid[] not null default '{}'" in BLUEPRINTS


def test_blueprints_indexes():
    assert "idx_mock_generated_blueprints_user_status" in BLUEPRINTS
    assert "idx_mock_generated_blueprints_expires_at" in BLUEPRINTS
    assert "idx_mock_generated_blueprints_exam_phase" in BLUEPRINTS
    # composite-unique target for migration 175's owner FK
    assert "uq_mock_generated_blueprints_id_user" in BLUEPRINTS
    assert "on public.mock_generated_blueprints(id, user_id)" in BLUEPRINTS


def test_blueprints_updated_at_trigger():
    assert "mock_generated_blueprints_updated_at" in BLUEPRINTS
    assert "execute function public.tg_set_updated_at()" in BLUEPRINTS


def test_blueprints_rls_owner_and_service_role_only():
    assert "enable row level security" in BLUEPRINTS
    assert "mock_generated_blueprints_owner_select" in BLUEPRINTS
    assert "using (user_id = auth.uid())" in BLUEPRINTS
    assert "mock_generated_blueprints_service_role_all" in BLUEPRINTS
    assert "for all to service_role using (true) with check (true)" in BLUEPRINTS
    # no end-user write policies in this PR
    assert "for insert" not in BLUEPRINTS
    assert "for update" not in BLUEPRINTS
    assert "for delete" not in BLUEPRINTS


def test_blueprints_pgrst_reload_footer():
    assert "notify pgrst, 'reload schema';" in BLUEPRINTS


# ── Migration 175: mock_attempts alterations ─────────────────────────────────

def test_attempts_template_id_made_nullable():
    assert (
        "alter table public.mock_attempts\n  alter column template_id drop not null"
        in ATTEMPTS
    )


def test_attempts_generated_blueprint_column_with_restrict():
    assert "add column if not exists generated_blueprint_id uuid" in ATTEMPTS
    assert (
        "references public.mock_generated_blueprints(id) on delete restrict"
        in ATTEMPTS
    )


def test_attempts_xor_one_source_check():
    assert "mock_attempts_one_source_chk" in ATTEMPTS
    assert "drop constraint mock_attempts_one_source_chk" in ATTEMPTS
    assert "template_id is not null" in ATTEMPTS
    assert "generated_blueprint_id is null" in ATTEMPTS
    assert "template_id is null" in ATTEMPTS
    assert "generated_blueprint_id is not null" in ATTEMPTS


def test_attempts_active_blueprint_unique_index():
    assert "uq_mock_attempts_active_blueprint" in ATTEMPTS
    assert "on public.mock_attempts(user_id, generated_blueprint_id)" in ATTEMPTS
    assert "where status = 'in_progress'" in ATTEMPTS


def test_attempts_owner_consistency_composite_fk():
    assert "mock_attempts_generated_blueprint_owner_fkey" in ATTEMPTS
    assert "foreign key (generated_blueprint_id, user_id)" in ATTEMPTS
    assert (
        "references public.mock_generated_blueprints(id, user_id)" in ATTEMPTS
    )


def test_attempts_does_not_touch_existing_template_active_index():
    # The pre-existing template guard must remain untouched by this PR.
    assert "uq_mock_attempts_active " not in ATTEMPTS  # no redefinition
    assert "drop index" not in ATTEMPTS


def test_attempts_pgrst_reload_footer():
    assert "notify pgrst, 'reload schema';" in ATTEMPTS
