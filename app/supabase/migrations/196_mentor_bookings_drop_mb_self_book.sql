-- =============================================================================
-- 196_mentor_bookings_drop_mb_self_book.sql
-- Security (forward fix): remove the surviving client INSERT policy on
-- public.mentor_bookings that migration 195 did not cover.
--
-- Background:
--   Migration 195 §5 dropped mb_owner_insert (migration 099) and
--   mb_owner_update (migration 099), but missed mb_self_book, which was
--   independently created by migration 070 (070_study_os_social_groups.sql).
--   Both policies grant INSERT to any authenticated session with
--   auth.uid() = user_id, so either one allows a direct PostgREST INSERT
--   with payment_status="captured", price_inr=0, and NULL payment IDs —
--   bypassing all Razorpay verification in the backend. The partial UNIQUE
--   indexes added in migration 195 (IS NOT NULL) do not block NULL values.
--
-- This migration:
--   1. Drops mb_self_book (and re-drops mb_owner_insert / mb_owner_update as
--      belt-and-braces, in case they were recreated).
--   2. Asserts that no INSERT policy remains on public.mentor_bookings for
--      the public, anon, or authenticated roles — the migration fails closed
--      if any such policy is found, regardless of its name.
--   3. Reloads the PostgREST schema cache.
--
-- The ONLY remaining write path is mb_service_role_all (all operations for
-- the service_role, used exclusively by the hardened backend). Owners retain
-- mb_owner_read and mb_self_select (SELECT only; these are safe).
--
-- Idempotent: DROP POLICY IF EXISTS is a no-op when the policy is absent.
-- The final assertion will PASS on a DB where the policies never existed.
-- =============================================================================

begin;

-- ─────────────────────────────────────────────────────────────────────────────
-- Step 1 — Drop all known client INSERT policies on mentor_bookings
-- ─────────────────────────────────────────────────────────────────────────────
do $$
begin
  if to_regclass('public.mentor_bookings') is not null then
    -- Primary target: missed by migration 195.
    drop policy if exists mb_self_book    on public.mentor_bookings;
    -- Belt-and-braces: already absent after migration 195, but idempotent.
    drop policy if exists mb_owner_insert on public.mentor_bookings;
    drop policy if exists mb_owner_update on public.mentor_bookings;
  end if;
end $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- Step 2 — Fail closed: assert no INSERT policy remains for client roles
-- ─────────────────────────────────────────────────────────────────────────────
-- After the drops, scan pg_policies. If ANY policy on mentor_bookings permits
-- INSERT (or ALL) for a non-service_role principal, abort with a descriptive
-- error so the gap is caught immediately on apply rather than silently left.
--
-- pg_policies.roles is name[] — use unnest() to avoid name[]/text[] operator
-- mismatch and keep comparisons type-safe.
do $$
declare
  v_survivors text;
begin
  if to_regclass('public.mentor_bookings') is null then
    return;  -- table absent — nothing to assert
  end if;

  -- Collect policies whose command allows INSERT and which are not restricted
  -- exclusively to service_role. A NULL / empty roles array means the policy
  -- applies to all principals (PostgreSQL PUBLIC).
  select string_agg(policyname, ', ' order by policyname)
  into   v_survivors
  from (
    select p.policyname,
           -- Does the policy target any non-service_role principal?
           -- An empty roles array means "all roles" (PUBLIC), so it is unsafe.
           (
             array_length(p.roles, 1) is null  -- empty → PUBLIC
             or exists (
               select 1
               from   unnest(p.roles) as r(role_name)
               where  r.role_name::text <> 'service_role'
             )
           ) as is_client_accessible
    from   pg_policies p
    where  p.schemaname = 'public'
      and  p.tablename  = 'mentor_bookings'
      and  p.cmd        in ('INSERT', 'ALL')
  ) sub
  where is_client_accessible;

  if v_survivors is not null then
    raise exception
      'SECURITY: client-accessible INSERT policies remain on '
      'public.mentor_bookings after migration 196: %. '
      'Drop them and re-run this migration.',
      v_survivors;
  end if;
end $$;

commit;

-- PostgREST: reload schema cache so the policy removal takes effect.
select pg_notify('pgrst', 'reload schema');
