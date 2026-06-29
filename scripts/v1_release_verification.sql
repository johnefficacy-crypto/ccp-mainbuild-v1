-- v1 release-gate verification (READ-ONLY, FAIL-CLOSED).
--
-- Operationalizes the verification queries from docs/ops/v1-go-live-runbook.md
-- and the RPC/RLS audit docs. Run against STAGING first, then PROD:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/v1_release_verification.sql
--
-- Exit status: the BLOCKING checks (1, 1c, 4) RAISE EXCEPTION on any failure, so
-- with ON_ERROR_STOP=1 the script exits non-zero and stops at the first failure.
-- CHECK 2 (RLS) is INFO and requires manual classification. CHECK 3 (extraction
-- archive-race) is OBSERVATION-ONLY and never asserts PASS — a quiet database can
-- return zero rows while the race remains reproducible, so the extraction gate
-- stays BLOCKED until the RPC/caller fix + regression test land. No writes.

\pset pager off
\set ON_ERROR_STOP on

\echo ''
\echo '================================================================'
\echo 'CHECK 1 (BLOCKING) — the 16 migration-203 RPCs, matched by EXACT'
\echo 'signature: each must exist, DENY PUBLIC/anon/authenticated EXECUTE,'
\echo 'and STILL GRANT service_role. Fails closed on any violation.'
\echo '================================================================'
do $$
declare
  r record;
  v_oid oid;
begin
  for r in select * from (values
      ('promote_recruitment',                       'jsonb'),
      ('create_verification_report',                'jsonb'),
      ('supersede_and_create_verification_report',  'uuid, jsonb'),
      ('claim_source_for_scrape',                   'uuid, integer'),
      ('apply_mock_mastery_delta',                  'uuid, uuid, uuid, numeric, text'),
      ('claim_mock_mastery_retry',                  'uuid, text, timestamp with time zone'),
      ('complete_mock_mastery_retry',               'uuid'),
      ('fn_fanout_alert_event',                     'uuid'),
      ('claim_eligibility_queue',                   'integer'),
      ('enqueue_eligibility_recompute',             'uuid, uuid, text, jsonb'),
      ('upsert_field_review',                       'uuid, text, text, text, text, uuid, text, jsonb, jsonb, text, uuid'),
      ('consume_profile_merge_claim',               'text, uuid'),
      ('update_pyq_question_review_atomic',         'uuid, text, uuid, timestamp with time zone'),
      ('start_attempt_from_blueprint',              'uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamp with time zone'),
      ('fn_invalidate_projection_for_question',     'uuid'),
      ('fn_block_projection_for_question',          'uuid, text')
    ) as t(name, args)
  loop
    select p.oid into v_oid
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
    where p.proname = r.name
      and pg_get_function_identity_arguments(p.oid) = r.args;

    if v_oid is null then
      raise exception 'CHECK 1 FAIL: public.%(%) not found (signature mismatch or missing)', r.name, r.args;
    end if;
    if has_function_privilege('anon', v_oid, 'EXECUTE') then
      raise exception 'CHECK 1 FAIL: public.%(%) is EXECUTE-able by anon', r.name, r.args;
    end if;
    if has_function_privilege('authenticated', v_oid, 'EXECUTE') then
      raise exception 'CHECK 1 FAIL: public.%(%) is EXECUTE-able by authenticated', r.name, r.args;
    end if;
    if not has_function_privilege('service_role', v_oid, 'EXECUTE') then
      raise exception 'CHECK 1 FAIL: public.%(%) is NOT EXECUTE-able by service_role (over-revoked)', r.name, r.args;
    end if;
  end loop;
  raise notice 'CHECK 1 PASS: all 16 hardened RPCs deny PUBLIC/anon/authenticated and allow service_role';
end $$;

\echo ''
\echo '================================================================'
\echo 'CHECK 1c (BLOCKING) — authoritative sweep: NO non-trigger function'
\echo 'in schema public may be EXECUTE-able by anon/authenticated except the'
\echo 'documented exceptions (is_admin + community_inc_*). A newly exposed'
\echo 'backend RPC fails this. Keep the exception list in sync with'
\echo 'docs/schema/rpc-grant-audit-v1.md.'
\echo '================================================================'
do $$
declare
  v_bad text;
begin
  select string_agg(format('%s(%s)', p.proname, pg_get_function_identity_arguments(p.oid)), ', ' order by p.proname)
    into v_bad
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
  where p.prokind = 'f'
    and p.prorettype <> 'trigger'::regtype
    and (has_function_privilege('anon', p.oid, 'EXECUTE')
         or has_function_privilege('authenticated', p.oid, 'EXECUTE'))
    and p.proname not in (
      'is_admin',
      'community_inc_thread_reply_count',
      'community_inc_thread_vote_count',
      'community_inc_reply_vote_count',
      'community_inc_resource_upvote_count',
      'community_inc_resource_report_count'
    );
  if v_bad is not null then
    raise exception 'CHECK 1c FAIL: undocumented public function(s) reachable by anon/authenticated: %', v_bad;
  end if;
  raise notice 'CHECK 1c PASS: no undocumented public function is EXECUTE-able by anon/authenticated';
end $$;

\echo ''
\echo '================================================================'
\echo 'CHECK 2 (INFO — manual classification required, NOT auto-pass):'
\echo 'public tables with RLS enabled and ZERO policies. Diff the list +'
\echo 'count against docs/schema/rls-coverage-reconciliation-v1.md and'
\echo 'classify every addition/removal. A FAIL is any returned table the'
\echo 'frontend reads directly with the anon/authenticated key (judgement).'
\echo '================================================================'
select count(*) as zero_policy_table_count
from pg_class c
join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
where c.relkind = 'r' and c.relrowsecurity = true
  and not exists (select 1 from pg_policies p
                  where p.schemaname = 'public' and p.tablename = c.relname);

select c.relname as zero_policy_table
from pg_class c
join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
where c.relkind = 'r' and c.relrowsecurity = true
  and not exists (select 1 from pg_policies p
                  where p.schemaname = 'public' and p.tablename = c.relname)
order by c.relname;

\echo ''
\echo '================================================================'
\echo 'CHECK 3 (OBSERVATION ONLY — NOT a pass/fail gate): text_extract jobs'
\echo 'stranded in `running`. The extraction archive-race gate stays BLOCKED'
\echo 'until the finalize RPC/caller terminalizes the document_archived path'
\echo 'AND a mid-flight regression test exists — a zero result here does NOT'
\echo 'close that gate. Investigate any rows; do not treat empty as PASS.'
\echo '================================================================'
select id, document_id, status, created_at, updated_at
from document_processing_jobs
where job_type = 'text_extract'
  and status = 'running'
  and updated_at < now() - interval '15 minutes'
order by updated_at;

\echo ''
\echo '================================================================'
\echo 'CHECK 4 (BLOCKING) — admin authorization hardening:'
\echo '  a. canonical public.is_admin(uuid) exists;'
\echo '  b. >=1 policy uses the canonical is_admin() predicate (mig 195);'
\echo '  c. NO policy references the deprecated profiles.is_admin predicate;'
\echo '  d. mb_self_book policy removed from mentor_bookings (mig 196).'
\echo '================================================================'
do $$
declare
  v_canonical_policy_count int;
  v_deprecated text;
  v_mb text;
begin
  if not exists (
    select 1 from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
    where p.proname = 'is_admin'
      and pg_get_function_identity_arguments(p.oid) = 'uuid'
  ) then
    raise exception 'CHECK 4 FAIL: canonical public.is_admin(uuid) not found';
  end if;

  select count(*) into v_canonical_policy_count
  from pg_policies
  where schemaname = 'public'
    and (coalesce(qual,'') ilike '%is_admin(%' or coalesce(with_check,'') ilike '%is_admin(%')
    and coalesce(qual,'')       not ilike '%profiles%is_admin%'
    and coalesce(with_check,'') not ilike '%profiles%is_admin%';
  if v_canonical_policy_count = 0 then
    raise exception 'CHECK 4 FAIL: no policy uses the canonical is_admin() predicate (migration 195 not in force?)';
  end if;

  select string_agg(format('%s.%s', tablename, policyname), ', ') into v_deprecated
  from pg_policies
  where schemaname = 'public'
    and (coalesce(qual,'') ilike '%profiles%is_admin%' or coalesce(with_check,'') ilike '%profiles%is_admin%');
  if v_deprecated is not null then
    raise exception 'CHECK 4 FAIL: policies still reference deprecated profiles.is_admin: %', v_deprecated;
  end if;

  select string_agg(policyname, ', ') into v_mb
  from pg_policies
  where schemaname = 'public' and tablename = 'mentor_bookings' and policyname = 'mb_self_book';
  if v_mb is not null then
    raise exception 'CHECK 4 FAIL: mb_self_book still present on mentor_bookings (migration 196 not applied)';
  end if;

  raise notice 'CHECK 4 PASS: canonical is_admin in force, no deprecated predicate, mb_self_book removed';
end $$;

\echo ''
\echo '================================================================'
\echo 'BLOCKING CHECKS (1, 1c, 4) PASSED — reaching this line means every'
\echo 'fail-closed assertion held. This does NOT by itself close the v1'
\echo 'gates: CHECK 2 needs manual RLS classification, CHECK 3 (extraction'
\echo 'archive-race) stays BLOCKED pending the code fix, and per-row RLS'
\echo 'visibility must be proven with a real user JWT (runbook Phase 2).'
\echo '================================================================'
