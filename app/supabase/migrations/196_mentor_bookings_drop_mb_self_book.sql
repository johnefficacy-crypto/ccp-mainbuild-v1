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
-- After the drops, scan pg_policies. If ANY policy on mentor_bookings
-- permits INSERT for the public, anon, or authenticated roles (regardless
-- of policy name), abort the migration with a descriptive error so the
-- issue is caught immediately on apply rather than silently left open.
do $$
declare
  v_survivors text;
begin
  if to_regclass('public.mentor_bookings') is null then
    return;  -- table absent — nothing to assert
  end if;

  select string_agg(
    format('  policyname=%L cmd=%L roles=%s', policyname, cmd, roles::text),
    chr(10)
  )
  into v_survivors
  from pg_policies
  where schemaname = 'public'
    and tablename  = 'mentor_bookings'
    and cmd        in ('INSERT', 'ALL')
    and (
      -- policy is unrestricted (roles array empty = applies to all)
      array_length(roles, 1) is null
      -- or it explicitly targets a client role
      or roles && array['public', 'anon', 'authenticated']
    )
    -- service_role-only policies are fine
    and not (roles = array['service_role']::text[]);

  if v_survivors is not null then
    raise exception
      'SECURITY: surviving INSERT-capable client policies found on '
      'public.mentor_bookings after migration 196 drop step. '
      'These must be dropped before this migration can complete:%s%',
      chr(10), v_survivors;
  end if;
end $$;

commit;

-- PostgREST: reload schema cache so the policy removal takes effect.
select pg_notify('pgrst', 'reload schema');
