-- GQR-S7 — live privilege/RLS proof for reasoning_stimulus_strategies.
--
-- Run only after migration 263 has been applied to the target Supabase database:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f app/supabase/validation/validate_reasoning_stimulus_strategy_privileges.sql
--
-- Read-only catalog validation; leaves no data.

\set ON_ERROR_STOP on

do $$
declare
  v_rls_enabled boolean;
  v_policy_count integer;
begin
  if to_regclass('public.reasoning_stimulus_strategies') is null then
    raise exception 'FAIL: public.reasoning_stimulus_strategies does not exist; apply migration 263 first';
  end if;

  select c.relrowsecurity
    into v_rls_enabled
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public'
     and c.relname = 'reasoning_stimulus_strategies';

  if not coalesce(v_rls_enabled, false) then
    raise exception 'FAIL: RLS is not enabled on reasoning_stimulus_strategies';
  end if;

  select count(*)
    into v_policy_count
    from pg_policies
   where schemaname = 'public'
     and tablename = 'reasoning_stimulus_strategies';

  if v_policy_count <> 0 then
    raise exception 'FAIL: expected zero direct client policies, found %', v_policy_count;
  end if;

  if to_regrole('anon') is null
     or to_regrole('authenticated') is null
     or to_regrole('service_role') is null then
    raise exception 'FAIL: Supabase roles anon/authenticated/service_role are required';
  end if;

  if has_table_privilege('anon', 'public.reasoning_stimulus_strategies', 'SELECT')
     or has_table_privilege('anon', 'public.reasoning_stimulus_strategies', 'INSERT')
     or has_table_privilege('anon', 'public.reasoning_stimulus_strategies', 'UPDATE')
     or has_table_privilege('anon', 'public.reasoning_stimulus_strategies', 'DELETE') then
    raise exception 'FAIL: anon has a direct table privilege';
  end if;

  if has_table_privilege('authenticated', 'public.reasoning_stimulus_strategies', 'SELECT')
     or has_table_privilege('authenticated', 'public.reasoning_stimulus_strategies', 'INSERT')
     or has_table_privilege('authenticated', 'public.reasoning_stimulus_strategies', 'UPDATE')
     or has_table_privilege('authenticated', 'public.reasoning_stimulus_strategies', 'DELETE') then
    raise exception 'FAIL: authenticated has a direct table privilege';
  end if;

  if not has_table_privilege('service_role', 'public.reasoning_stimulus_strategies', 'SELECT')
     or not has_table_privilege('service_role', 'public.reasoning_stimulus_strategies', 'INSERT')
     or not has_table_privilege('service_role', 'public.reasoning_stimulus_strategies', 'UPDATE')
     or not has_table_privilege('service_role', 'public.reasoning_stimulus_strategies', 'DELETE') then
    raise exception 'FAIL: service_role is missing one or more required table privileges';
  end if;
end
$$;

select 'ALL PASS — reasoning_stimulus_strategies is RLS-enabled and service-role-only' as result;
