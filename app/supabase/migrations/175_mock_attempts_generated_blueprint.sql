-- 175_mock_attempts_generated_blueprint.sql
-- A-PR0 (D4 Option-B): wire mock_attempts to generated blueprints.
--
-- Delicate, deliberately separate from 174. After this migration an attempt
-- is backed by EXACTLY ONE source:
--   * a reusable mock_template  (template_id set, generated_blueprint_id null)
--   * a single-use generated blueprint (template_id null, generated_blueprint_id set)
--
-- This migration does NOT change start_attempt or any application code. The
-- generated-attempt write path (start_attempt_from_blueprint) lands later.
--
-- Idempotent: every step uses IF EXISTS / IF NOT EXISTS / catalog guards.

-- ── 1. template_id becomes nullable ──────────────────────────────────────────
-- Was NOT NULL (migration 135). Generated attempts carry no template_id.
alter table public.mock_attempts
  alter column template_id drop not null;

-- ── 2. generated_blueprint_id column ─────────────────────────────────────────
-- on delete restrict: a blueprint that backs an attempt must not vanish out
-- from under it; the lifecycle/cleanup PR handles teardown explicitly.
alter table public.mock_attempts
  add column if not exists generated_blueprint_id uuid
    references public.mock_generated_blueprints(id) on delete restrict;

-- ── 3. exactly-one-source XOR check ──────────────────────────────────────────
do $$
begin
  if exists (
    select 1 from pg_constraint c
    join pg_class r on r.oid = c.conrelid
    join pg_namespace n on n.oid = r.relnamespace
    where n.nspname = 'public'
      and r.relname = 'mock_attempts'
      and c.conname = 'mock_attempts_one_source_chk'
  ) then
    alter table public.mock_attempts
      drop constraint mock_attempts_one_source_chk;
  end if;

  alter table public.mock_attempts
    add constraint mock_attempts_one_source_chk check (
      (
        template_id is not null
        and generated_blueprint_id is null
      )
      or
      (
        template_id is null
        and generated_blueprint_id is not null
      )
    );
end $$;

-- ── 4. active generated-blueprint uniqueness ─────────────────────────────────
-- One in_progress attempt per (user_id, generated_blueprint_id). Mirrors the
-- existing template guard uq_mock_attempts_active, which is left untouched.
create unique index if not exists uq_mock_attempts_active_blueprint
  on public.mock_attempts(user_id, generated_blueprint_id)
  where status = 'in_progress'
    and generated_blueprint_id is not null;

-- ── 5. owner-consistency composite FK ────────────────────────────────────────
-- Enforces attempt.user_id == blueprint.user_id. Feasible because
-- mock_generated_blueprints carries a unique index on (id, user_id)
-- (migration 174) and both user_id columns are uuid. profiles.id == auth.users.id
-- (profiles is 1:1 with auth.users), so the legacy auth.users-scoped
-- mock_attempts.user_id is value-compatible with the profiles-scoped
-- blueprint.user_id.
do $$
begin
  if not exists (
    select 1 from pg_constraint c
    join pg_class r on r.oid = c.conrelid
    join pg_namespace n on n.oid = r.relnamespace
    where n.nspname = 'public'
      and r.relname = 'mock_attempts'
      and c.conname = 'mock_attempts_generated_blueprint_owner_fkey'
  ) then
    alter table public.mock_attempts
      add constraint mock_attempts_generated_blueprint_owner_fkey
      foreign key (generated_blueprint_id, user_id)
      references public.mock_generated_blueprints(id, user_id)
      on delete restrict;
  end if;
end $$;

notify pgrst, 'reload schema';
