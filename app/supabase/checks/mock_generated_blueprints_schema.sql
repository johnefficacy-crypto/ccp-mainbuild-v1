-- A-PR0 generated-mock blueprint schema foundation smoke check.
-- Read-only: SELECT-only assertions, raises an exception on any mismatch.
-- Verifies migrations 174 + 175 landed: the public.mock_generated_blueprints
-- table (columns / constraints / indexes / trigger / RLS) and the
-- public.mock_attempts wiring (nullable template_id, generated_blueprint_id,
-- one-source XOR check, active-blueprint partial unique index, owner FK).
--
-- Object names are taken from the migrations, not from any review note. If a
-- name in an external note disagrees with the migration, the migration wins.
--
-- Manual validation:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f app/supabase/checks/mock_generated_blueprints_schema.sql
--
-- Behavioral coverage (XOR accept/reject, partial-unique blocking, owner-FK
-- mismatch, RLS owner vs non-owner vs service_role) is exercised manually via
-- wrapped BEGIN/ROLLBACK SQL documented in
-- app/backend/tests/test_mock_generated_blueprints_migration.py — there is no
-- live-DB behavioral harness in this repo.

begin read only;

do $$
begin
  -- ── 1. mock_generated_blueprints table exists ─────────────────────────────
  if to_regclass('public.mock_generated_blueprints') is null then
    raise exception 'table public.mock_generated_blueprints is missing';
  end if;

  -- ── 2. columns: type / nullability / default (174) ────────────────────────
  -- id uuid not null, default gen_random_uuid().
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'id' and data_type = 'uuid'
       and is_nullable = 'NO' and column_default like '%gen_random_uuid()%'
  ) then
    raise exception 'mock_generated_blueprints.id (uuid not null default gen_random_uuid()) missing';
  end if;

  -- user_id uuid not null.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'user_id' and data_type = 'uuid' and is_nullable = 'NO'
  ) then
    raise exception 'mock_generated_blueprints.user_id (uuid not null) missing';
  end if;

  -- exam_id uuid nullable.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'exam_id' and data_type = 'uuid' and is_nullable = 'YES'
  ) then
    raise exception 'mock_generated_blueprints.exam_id (uuid, nullable) missing';
  end if;

  -- exam_phase_id uuid nullable.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'exam_phase_id' and data_type = 'uuid' and is_nullable = 'YES'
  ) then
    raise exception 'mock_generated_blueprints.exam_phase_id (uuid, nullable) missing';
  end if;

  -- source text not null.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'source' and data_type = 'text' and is_nullable = 'NO'
  ) then
    raise exception 'mock_generated_blueprints.source (text not null) missing';
  end if;

  -- status text not null default 'draft'.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'status' and data_type = 'text'
       and is_nullable = 'NO' and column_default like '%draft%'
  ) then
    raise exception 'mock_generated_blueprints.status (text not null default draft) missing';
  end if;

  -- template_snapshot jsonb not null default '{}'.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'template_snapshot' and data_type = 'jsonb'
       and is_nullable = 'NO' and column_default like '%''{}''::jsonb%'
  ) then
    raise exception 'mock_generated_blueprints.template_snapshot (jsonb not null default {}) missing';
  end if;

  -- section_snapshot jsonb not null default '[]'.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'section_snapshot' and data_type = 'jsonb'
       and is_nullable = 'NO' and column_default like '%''[]''::jsonb%'
  ) then
    raise exception 'mock_generated_blueprints.section_snapshot (jsonb not null default []) missing';
  end if;

  -- selector_snapshot jsonb not null default '{}'.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'selector_snapshot' and data_type = 'jsonb'
       and is_nullable = 'NO' and column_default like '%''{}''::jsonb%'
  ) then
    raise exception 'mock_generated_blueprints.selector_snapshot (jsonb not null default {}) missing';
  end if;

  -- question_ids uuid[] not null default '{}'.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'question_ids' and data_type = 'ARRAY'
       and udt_name = '_uuid' and is_nullable = 'NO'
  ) then
    raise exception 'mock_generated_blueprints.question_ids (uuid[] not null) missing';
  end if;

  -- readiness_snapshot jsonb not null default '{}'.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'readiness_snapshot' and data_type = 'jsonb'
       and is_nullable = 'NO' and column_default like '%''{}''::jsonb%'
  ) then
    raise exception 'mock_generated_blueprints.readiness_snapshot (jsonb not null default {}) missing';
  end if;

  -- expires_at timestamptz not null.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'expires_at' and data_type = 'timestamp with time zone'
       and is_nullable = 'NO'
  ) then
    raise exception 'mock_generated_blueprints.expires_at (timestamptz not null) missing';
  end if;

  -- created_at timestamptz not null default now().
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'created_at' and data_type = 'timestamp with time zone'
       and is_nullable = 'NO' and column_default like '%now()%'
  ) then
    raise exception 'mock_generated_blueprints.created_at (timestamptz not null default now()) missing';
  end if;

  -- started_at timestamptz nullable.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'started_at' and data_type = 'timestamp with time zone'
       and is_nullable = 'YES'
  ) then
    raise exception 'mock_generated_blueprints.started_at (timestamptz, nullable) missing';
  end if;

  -- updated_at timestamptz not null default now().
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_generated_blueprints'
       and column_name = 'updated_at' and data_type = 'timestamp with time zone'
       and is_nullable = 'NO' and column_default like '%now()%'
  ) then
    raise exception 'mock_generated_blueprints.updated_at (timestamptz not null default now()) missing';
  end if;

  -- ── 3. source + status check constraints (174) ────────────────────────────
  -- Inline column CHECKs are auto-named; assert by definition, not name.
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.mock_generated_blueprints'::regclass
       and contype = 'c'
       and pg_get_constraintdef(oid) ilike '%exam_realistic%'
       and pg_get_constraintdef(oid) ilike '%personalized%'
  ) then
    raise exception 'mock_generated_blueprints source check (exam_realistic/personalized) missing';
  end if;

  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.mock_generated_blueprints'::regclass
       and contype = 'c'
       and pg_get_constraintdef(oid) ilike '%draft%'
       and pg_get_constraintdef(oid) ilike '%started%'
       and pg_get_constraintdef(oid) ilike '%expired%'
       and pg_get_constraintdef(oid) ilike '%cancelled%'
  ) then
    raise exception 'mock_generated_blueprints status check (draft/started/expired/cancelled) missing';
  end if;

  -- ── 4. foreign keys (174) ─────────────────────────────────────────────────
  -- user_id -> public.profiles(id).
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.mock_generated_blueprints'::regclass
       and contype = 'f'
       and confrelid = 'public.profiles'::regclass
       and array_length(conkey, 1) = 1
       and conkey[1] = (select attnum from pg_attribute
                         where attrelid = 'public.mock_generated_blueprints'::regclass
                           and attname = 'user_id')
  ) then
    raise exception 'mock_generated_blueprints.user_id FK -> public.profiles(id) missing';
  end if;

  -- exam_id -> public.exams(id).
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.mock_generated_blueprints'::regclass
       and contype = 'f' and confrelid = 'public.exams'::regclass
       and array_length(conkey, 1) = 1
       and conkey[1] = (select attnum from pg_attribute
                         where attrelid = 'public.mock_generated_blueprints'::regclass
                           and attname = 'exam_id')
  ) then
    raise exception 'mock_generated_blueprints.exam_id FK -> public.exams(id) missing';
  end if;

  -- exam_phase_id -> public.exam_phases(id).
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.mock_generated_blueprints'::regclass
       and contype = 'f' and confrelid = 'public.exam_phases'::regclass
       and array_length(conkey, 1) = 1
       and conkey[1] = (select attnum from pg_attribute
                         where attrelid = 'public.mock_generated_blueprints'::regclass
                           and attname = 'exam_phase_id')
  ) then
    raise exception 'mock_generated_blueprints.exam_phase_id FK -> public.exam_phases(id) missing';
  end if;

  -- ── 5. indexes (174) ──────────────────────────────────────────────────────
  if not exists (
    select 1 from pg_indexes
     where schemaname = 'public' and tablename = 'mock_generated_blueprints'
       and indexname = 'idx_mock_generated_blueprints_user_status'
  ) then
    raise exception 'index idx_mock_generated_blueprints_user_status missing';
  end if;

  if not exists (
    select 1 from pg_indexes
     where schemaname = 'public' and tablename = 'mock_generated_blueprints'
       and indexname = 'idx_mock_generated_blueprints_expires_at'
  ) then
    raise exception 'index idx_mock_generated_blueprints_expires_at missing';
  end if;

  if not exists (
    select 1 from pg_indexes
     where schemaname = 'public' and tablename = 'mock_generated_blueprints'
       and indexname = 'idx_mock_generated_blueprints_exam_phase'
  ) then
    raise exception 'index idx_mock_generated_blueprints_exam_phase missing';
  end if;

  -- composite-unique (id, user_id) backing the 175 owner FK.
  if not exists (
    select 1 from pg_indexes
     where schemaname = 'public' and tablename = 'mock_generated_blueprints'
       and indexname = 'uq_mock_generated_blueprints_id_user'
       and indexdef ilike '%unique%'
  ) then
    raise exception 'unique index uq_mock_generated_blueprints_id_user missing';
  end if;

  -- ── 6. updated_at trigger (174) ───────────────────────────────────────────
  if not exists (
    select 1 from pg_trigger t
     join pg_class c on c.oid = t.tgrelid
     join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relname = 'mock_generated_blueprints'
       and t.tgname = 'mock_generated_blueprints_updated_at'
       and not t.tgisinternal
  ) then
    raise exception 'trigger mock_generated_blueprints_updated_at missing';
  end if;

  -- ── 7. RLS enabled + policies (174) ───────────────────────────────────────
  if not exists (
    select 1 from pg_class c
     join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relname = 'mock_generated_blueprints'
       and c.relrowsecurity is true
  ) then
    raise exception 'RLS is not enabled on public.mock_generated_blueprints';
  end if;

  if not exists (
    select 1 from pg_policies
     where schemaname = 'public' and tablename = 'mock_generated_blueprints'
       and policyname = 'mock_generated_blueprints_owner_select'
  ) then
    raise exception 'policy mock_generated_blueprints_owner_select missing';
  end if;

  if not exists (
    select 1 from pg_policies
     where schemaname = 'public' and tablename = 'mock_generated_blueprints'
       and policyname = 'mock_generated_blueprints_service_role_all'
  ) then
    raise exception 'policy mock_generated_blueprints_service_role_all missing';
  end if;

  -- ── 8. mock_attempts wiring (175) ─────────────────────────────────────────
  -- template_id is now nullable.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_attempts'
       and column_name = 'template_id' and is_nullable = 'YES'
  ) then
    raise exception 'mock_attempts.template_id should be nullable after migration 175';
  end if;

  -- generated_blueprint_id uuid, nullable.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_attempts'
       and column_name = 'generated_blueprint_id' and data_type = 'uuid'
       and is_nullable = 'YES'
  ) then
    raise exception 'mock_attempts.generated_blueprint_id (uuid, nullable) missing';
  end if;

  -- single-column FK generated_blueprint_id -> mock_generated_blueprints(id).
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.mock_attempts'::regclass
       and contype = 'f'
       and confrelid = 'public.mock_generated_blueprints'::regclass
       and array_length(conkey, 1) = 1
       and conkey[1] = (select attnum from pg_attribute
                         where attrelid = 'public.mock_attempts'::regclass
                           and attname = 'generated_blueprint_id')
  ) then
    raise exception 'mock_attempts.generated_blueprint_id FK -> mock_generated_blueprints(id) missing';
  end if;

  -- one-source XOR check constraint.
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.mock_attempts'::regclass
       and contype = 'c'
       and conname = 'mock_attempts_one_source_chk'
  ) then
    raise exception 'constraint mock_attempts_one_source_chk missing';
  end if;

  -- composite owner-consistency FK (generated_blueprint_id, user_id).
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.mock_attempts'::regclass
       and contype = 'f'
       and conname = 'mock_attempts_generated_blueprint_owner_fkey'
       and confrelid = 'public.mock_generated_blueprints'::regclass
  ) then
    raise exception 'composite FK mock_attempts_generated_blueprint_owner_fkey missing';
  end if;

  -- active-blueprint partial unique index.
  if not exists (
    select 1 from pg_indexes
     where schemaname = 'public' and tablename = 'mock_attempts'
       and indexname = 'uq_mock_attempts_active_blueprint'
       and indexdef ilike '%unique%'
       and indexdef ilike '%where%'
  ) then
    raise exception 'partial unique index uq_mock_attempts_active_blueprint missing';
  end if;
end $$;

rollback;
