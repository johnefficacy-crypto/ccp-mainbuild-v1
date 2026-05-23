-- =============================================================================
-- 134_rbac_unification.sql
-- RBAC hardening: unify the auth-role source of truth and introduce mentor as
-- a domain capability (not an auth role).
--
-- Source of truth for an auth role is auth.users.raw_app_meta_data.role
-- (Supabase app_metadata), enforced server-side by FastAPI
-- (require_admin / require_super_admin). profiles.admin_role and
-- profiles.is_admin are LEGACY and only marked deprecated here — NOT dropped,
-- to avoid breaking unknown consumers.
--
-- Idempotent: safe to run on a fresh DB and to re-run on an existing one.
-- =============================================================================

-- ── Step 6: deprecate legacy role columns (mark only, do NOT drop) ───────────
-- profiles.admin_role only exists on databases that applied the legacy
-- migration 019; the canonical migration set never adds it. Guard the COMMENT
-- so this migration applies cleanly on a fresh canonical DB too.
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'profiles' and column_name = 'admin_role'
  ) then
    comment on column public.profiles.admin_role is
      'DEPRECATED: source of truth is auth.users.raw_app_meta_data.role';
  end if;

  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'profiles' and column_name = 'is_admin'
  ) then
    comment on column public.profiles.is_admin is
      'DEPRECATED: source of truth is auth.users.raw_app_meta_data.role';
  end if;
end $$;

-- admin_audit_logs and its indexes are PRESERVED — intentionally untouched.

-- ── RLS decision: admin tables are FastAPI-only ──────────────────────────────
-- The frontend never reaches admin tables (profiles/admin_audit_logs/
-- source_registry/scrape_queue/recruitment_verification_conflicts) through the
-- Supabase JS client; it only calls supabase.auth.* and routes all admin data
-- through the FastAPI service-role backend. No new RLS policies are added and
-- no `GRANT ... TO authenticated` is created here.
-- Admin tables are FastAPI-only. Direct PostgREST access not granted.

-- ── Step 7: mentor as a capability ───────────────────────────────────────────
alter table public.profiles
  add column if not exists is_mentor boolean not null default false;

comment on column public.profiles.is_mentor is
  'Mentor is a domain capability, NOT an auth role. Surfaced as '
  'capabilities.mentor on /api/auth/me. Auth roles live in '
  'auth.users.raw_app_meta_data.role (user|admin|super_admin).';

-- Backfill from the only legacy mentor signal in the data model: an auth user
-- whose app_metadata.role was set to 'mentor' (now coerced to "user" as a
-- role). auth.users may be absent on a non-Supabase test DB — guard for that.
do $$
declare
  n integer := 0;
begin
  begin
    update public.profiles p
      set is_mentor = true
      from auth.users u
      where u.id = p.id
        and (u.raw_app_meta_data ->> 'role') = 'mentor'
        and coalesce(p.is_mentor, false) = false;
    get diagnostics n = row_count;
    raise notice 'rbac_unification: backfilled is_mentor=true for % profile(s) from legacy app_metadata.role=mentor', n;
  exception
    when undefined_table then
      raise notice 'rbac_unification: auth.users not present; skipped is_mentor backfill';
  end;
end $$;
