-- 174_mock_generated_blueprints.sql
-- A-PR0 (D4 Option-B): generated-mock blueprint schema foundation.
--
-- Schema ONLY. This migration introduces the per-user, service-created
-- "generated blueprint" entity that backs generated (non-template) mock
-- attempts. It does NOT add any application logic:
--   * no start_attempt_from_blueprint
--   * no generator (exam-realistic / personalized)
--   * no cleanup sweeper
--   * no API / frontend
-- Those land in later PRs.
--
-- Why a new table instead of reusing mock_templates:
--   mock_engine.start_attempt() loads templates by (slug, status='active')
--   and mock_templates are reusable, shareable, status-gated authoring
--   artifacts. Generated blueprints are single-use, owner-scoped, expiring
--   snapshots. Conflating them would expose generated payloads through the
--   active-template read path. They are deliberately kept separate.
--
-- Conventions mirrored from migration 114 (library_ocr_jobs):
--   - owner FK -> public.profiles(id) (newer owner-scoped convention;
--     legacy mock_attempts.user_id references auth.users(id) and is left
--     untouched)
--   - `create table if not exists` / `create index if not exists`
--   - DO-block guarded `create policy ...`
--   - relies on public.tg_set_updated_at() from migration 014
--   - owner-select + service_role-all RLS; no end-user write policies
--   - `notify pgrst, 'reload schema'` footer

--------------------------------------------------
-- mock_generated_blueprints — single-use generated mock blueprint
--------------------------------------------------

create table if not exists public.mock_generated_blueprints (
  id uuid primary key default gen_random_uuid(),

  user_id uuid not null
    references public.profiles(id) on delete cascade,

  exam_id uuid
    references public.exams(id) on delete set null,

  exam_phase_id uuid
    references public.exam_phases(id) on delete set null,

  source text not null
    check (source in ('exam_realistic','personalized')),

  status text not null default 'draft'
    check (status in ('draft','started','expired','cancelled')),

  template_snapshot  jsonb  not null default '{}'::jsonb,
  section_snapshot   jsonb  not null default '[]'::jsonb,
  selector_snapshot  jsonb  not null default '{}'::jsonb,
  question_ids       uuid[] not null default '{}',
  readiness_snapshot jsonb  not null default '{}'::jsonb,

  expires_at  timestamptz not null,
  created_at  timestamptz not null default now(),
  started_at  timestamptz,
  updated_at  timestamptz not null default now()
);

create index if not exists idx_mock_generated_blueprints_user_status
  on public.mock_generated_blueprints(user_id, status);

create index if not exists idx_mock_generated_blueprints_expires_at
  on public.mock_generated_blueprints(expires_at);

create index if not exists idx_mock_generated_blueprints_exam_phase
  on public.mock_generated_blueprints(exam_id, exam_phase_id);

-- Composite-unique on (id, user_id) so migration 175 can attach a composite
-- FK from mock_attempts(generated_blueprint_id, user_id) and enforce
-- attempt-owner == blueprint-owner consistency at the database level.
create unique index if not exists uq_mock_generated_blueprints_id_user
  on public.mock_generated_blueprints(id, user_id);

drop trigger if exists mock_generated_blueprints_updated_at
  on public.mock_generated_blueprints;
create trigger mock_generated_blueprints_updated_at
  before update on public.mock_generated_blueprints
  for each row execute function public.tg_set_updated_at();

--------------------------------------------------
-- RLS — mock_generated_blueprints
--
-- Owner-select on own rows. Service-role full. No insert/update/delete for
-- end-user roles in this PR — generated blueprints are service-created so
-- the generator + lifecycle stay enforceable from one place. Postgres
-- default-deny covers everything else.
--------------------------------------------------

alter table public.mock_generated_blueprints enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'mock_generated_blueprints'
      and policyname = 'mock_generated_blueprints_owner_select'
  ) then
    create policy mock_generated_blueprints_owner_select
      on public.mock_generated_blueprints
      for select
      to authenticated
      using (user_id = auth.uid());
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'mock_generated_blueprints'
      and policyname = 'mock_generated_blueprints_service_role_all'
  ) then
    create policy mock_generated_blueprints_service_role_all
      on public.mock_generated_blueprints
      for all to service_role using (true) with check (true);
  end if;
end $$;

notify pgrst, 'reload schema';
