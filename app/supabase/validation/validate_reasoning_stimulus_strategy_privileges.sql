-- GQR-S7 — live privilege/RLS proof for content_card_links (migration 292,
-- which merged reasoning_stimulus_strategies and the two question-link tables).
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
  if to_regclass('public.content_card_links') is null then
    raise exception 'FAIL: public.content_card_links does not exist; apply migration 292 first';
  end if;

  select c.relrowsecurity
    into v_rls_enabled
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public'
     and c.relname = 'content_card_links';

  if not coalesce(v_rls_enabled, false) then
    raise exception 'FAIL: RLS is not enabled on content_card_links';
  end if;

  select count(*)
    into v_policy_count
    from pg_policies
   where schemaname = 'public'
     and tablename = 'content_card_links';

  if v_policy_count <> 0 then
    raise exception 'FAIL: expected zero direct client policies, found %', v_policy_count;
  end if;

  if to_regrole('anon') is null
     or to_regrole('authenticated') is null
     or to_regrole('service_role') is null then
    raise exception 'FAIL: Supabase roles anon/authenticated/service_role are required';
  end if;

  if has_table_privilege('anon', 'public.content_card_links', 'SELECT')
     or has_table_privilege('anon', 'public.content_card_links', 'INSERT')
     or has_table_privilege('anon', 'public.content_card_links', 'UPDATE')
     or has_table_privilege('anon', 'public.content_card_links', 'DELETE') then
    raise exception 'FAIL: anon has a direct table privilege';
  end if;

  if has_table_privilege('authenticated', 'public.content_card_links', 'SELECT')
     or has_table_privilege('authenticated', 'public.content_card_links', 'INSERT')
     or has_table_privilege('authenticated', 'public.content_card_links', 'UPDATE')
     or has_table_privilege('authenticated', 'public.content_card_links', 'DELETE') then
    raise exception 'FAIL: authenticated has a direct table privilege';
  end if;

  if not has_table_privilege('service_role', 'public.content_card_links', 'SELECT')
     or not has_table_privilege('service_role', 'public.content_card_links', 'INSERT')
     or not has_table_privilege('service_role', 'public.content_card_links', 'UPDATE')
     or not has_table_privilege('service_role', 'public.content_card_links', 'DELETE') then
    raise exception 'FAIL: service_role is missing one or more required table privileges';
  end if;
end
$$;

select 'ALL PASS — content_card_links is RLS-enabled and service-role-only' as result;
