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
\echo 'CHECK 1 (BLOCKING) — the 16 migration-203 RPCs, resolved by canonical'
\echo 'signature via to_regprocedure(): each must exist, DENY PUBLIC/anon/'
\echo 'authenticated EXECUTE, and STILL GRANT service_role.'
\echo '================================================================'
do $$
declare
  v_sig  text;
  v_oid  oid;
begin
  foreach v_sig in array array[
      'public.promote_recruitment(jsonb)',
      'public.create_verification_report(jsonb)',
      'public.supersede_and_create_verification_report(uuid, jsonb)',
      'public.claim_source_for_scrape(uuid, integer)',
      'public.apply_mock_mastery_delta(uuid, uuid, uuid, numeric, text)',
      'public.claim_mock_mastery_retry(uuid, text, timestamptz)',
      'public.complete_mock_mastery_retry(uuid)',
      'public.fn_fanout_alert_event(uuid)',
      'public.claim_eligibility_queue(integer)',
      'public.enqueue_eligibility_recompute(uuid, uuid, text, jsonb)',
      'public.upsert_field_review(uuid, text, text, text, text, uuid, text, jsonb, jsonb, text, uuid)',
      'public.consume_profile_merge_claim(text, uuid)',
      'public.update_pyq_question_review_atomic(uuid, text, uuid, timestamptz)',
      'public.start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz)',
      'public.fn_invalidate_projection_for_question(uuid)',
      'public.fn_block_projection_for_question(uuid, text)'
    ]
  loop
    v_oid := to_regprocedure(v_sig);
    if v_oid is null then
      raise exception 'CHECK 1 FAIL: % not found (missing or signature drift)', v_sig;
    end if;
    if has_function_privilege('anon', v_oid, 'EXECUTE') then
      raise exception 'CHECK 1 FAIL: % is EXECUTE-able by anon', v_sig;
    end if;
    if has_function_privilege('authenticated', v_oid, 'EXECUTE') then
      raise exception 'CHECK 1 FAIL: % is EXECUTE-able by authenticated', v_sig;
    end if;
    if not has_function_privilege('service_role', v_oid, 'EXECUTE') then
      raise exception 'CHECK 1 FAIL: % is NOT EXECUTE-able by service_role (over-revoked)', v_sig;
    end if;
  end loop;
  raise notice 'CHECK 1 PASS: all 16 hardened RPCs deny PUBLIC/anon/authenticated and allow service_role';
end $$;

\echo ''
\echo '================================================================'
\echo 'CHECK 1c (BLOCKING) — authoritative sweep: NO non-trigger function in'
\echo 'schema public may be EXECUTE-able by anon/authenticated except the'
\echo 'documented exceptions, matched by EXACT signature so a newly added/'
\echo 'redefined overload (e.g. is_admin(text)) is NOT silently allowed:'
\echo '  is_admin(uuid) and community_inc_*(uuid, integer).'
\echo 'Keep this list in sync with docs/schema/rpc-grant-audit-v1.md.'
\echo '================================================================'
do $$
declare
  v_bad text;
begin
  with allowed(name, args) as (
    values
      ('is_admin',                          'uuid'),
      ('community_inc_thread_reply_count',  'uuid, integer'),
      ('community_inc_thread_vote_count',   'uuid, integer'),
      ('community_inc_reply_vote_count',    'uuid, integer'),
      ('community_inc_resource_upvote_count','uuid, integer'),
      ('community_inc_resource_report_count','uuid, integer')
  )
  select string_agg(format('%s(%s)', p.proname, pg_get_function_identity_arguments(p.oid)), ', ' order by p.proname)
    into v_bad
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
  where p.prokind = 'f'
    and p.prorettype <> 'trigger'::regtype
    and (has_function_privilege('anon', p.oid, 'EXECUTE')
         or has_function_privilege('authenticated', p.oid, 'EXECUTE'))
    and not exists (
      select 1 from allowed a
      where a.name = p.proname
        and a.args = pg_get_function_identity_arguments(p.oid)
    );
  if v_bad is not null then
    raise exception 'CHECK 1c FAIL: undocumented public function(s) reachable by anon/authenticated: %', v_bad;
  end if;
  -- positive assertion: the documented exceptions must actually be reachable as intended
  if not has_function_privilege('authenticated', 'public.is_admin(uuid)'::regprocedure, 'EXECUTE') then
    raise exception 'CHECK 1c FAIL: public.is_admin(uuid) is NOT EXECUTE-able by authenticated (RLS policies need it)';
  end if;
  raise notice 'CHECK 1c PASS: only the documented exact-signature exceptions are anon/authenticated-reachable';
end $$;

\echo ''
\echo '================================================================'
\echo 'CHECK 2 (INFO — manual classification required, NOT auto-pass):'
\echo 'public tables with RLS enabled and ZERO policies. Diff list + count'
\echo 'against docs/schema/rls-coverage-reconciliation-v1.md and classify'
\echo 'every addition/removal. A FAIL is any returned table the frontend'
\echo 'reads directly with the anon/authenticated key (judgement).'
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
\echo 'AND a mid-flight regression test exists — empty here does NOT pass.'
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
\echo '  a. canonical public.is_admin(uuid): SECURITY DEFINER, reads'
\echo '     auth.users.raw_app_meta_data (migration 151), not profiles.is_admin;'
\echo '  b. every EXISTING migration-195 target table has its named policy;'
\echo '  c. NO policy references the deprecated profiles.is_admin predicate;'
\echo '  d. mentor_bookings has NO client-writable INSERT/ALL policy reachable'
\echo '     by PUBLIC/anon/authenticated (migration 196 role-survivor scan).'
\echo '================================================================'
do $$
declare
  r          record;
  v_secdef   boolean;
  v_src      text;
  v_canon    int;
  v_dep      text;
  v_mb       text;
begin
  -- a. canonical is_admin(uuid) definition
  select p.prosecdef, p.prosrc into v_secdef, v_src
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
  where p.proname = 'is_admin' and pg_get_function_identity_arguments(p.oid) = 'uuid';
  if not found then
    raise exception 'CHECK 4 FAIL: canonical public.is_admin(uuid) not found';
  end if;
  if not v_secdef then
    raise exception 'CHECK 4 FAIL: public.is_admin(uuid) is not SECURITY DEFINER';
  end if;
  if v_src not ilike '%raw_app_meta_data%' then
    raise exception 'CHECK 4 FAIL: public.is_admin(uuid) body does not read auth.users.raw_app_meta_data (stale/non-canonical body)';
  end if;
  if v_src ilike '%profiles%is_admin%' then
    raise exception 'CHECK 4 FAIL: public.is_admin(uuid) still consults deprecated profiles.is_admin';
  end if;

  -- b. migration-195 named policies present for every EXISTING target table
  for r in select * from (values
      ('exam_topic_coverage_read_reviewed',        'exam_topic_coverage'),
      ('exam_topic_score_snapshots_read_reviewed', 'exam_topic_score_snapshots'),
      ('exam_competition_metrics_read_reviewed',   'exam_competition_metrics'),
      ('exam_policy_updates_read_trusted',         'exam_policy_updates'),
      ('plan_impact_decisions_admin_all',          'plan_impact_decisions'),
      ('extraction_runs_admin_all',                'extraction_runs'),
      ('mqg_admin_all',                            'mock_question_groups'),
      ('mqtt_admin_all',                           'mock_question_topic_tags'),
      ('mqs_admin_all',                            'mock_question_sources'),
      ('mqrl_admin_all',                           'mock_question_review_log')
    ) as t(pol, tbl)
  loop
    if to_regclass('public.' || r.tbl) is not null
       and not exists (
         select 1 from pg_policies
         where schemaname = 'public' and tablename = r.tbl and policyname = r.pol
       ) then
      raise exception 'CHECK 4 FAIL: migration-195 policy % missing on existing table public.%', r.pol, r.tbl;
    end if;
  end loop;

  -- c. no deprecated predicate anywhere
  select string_agg(format('%s.%s', tablename, policyname), ', ') into v_dep
  from pg_policies
  where schemaname = 'public'
    and (coalesce(qual,'') ilike '%profiles%is_admin%' or coalesce(with_check,'') ilike '%profiles%is_admin%');
  if v_dep is not null then
    raise exception 'CHECK 4 FAIL: policies still reference deprecated profiles.is_admin: %', v_dep;
  end if;

  -- d. migration-196 role-survivor scan on mentor_bookings (name-agnostic)
  select string_agg(format('%s [%s, roles=%s]', policyname, cmd, array_to_string(roles, '/')), ', ') into v_mb
  from pg_policies
  where schemaname = 'public' and tablename = 'mentor_bookings'
    and cmd in ('INSERT', 'ALL')
    and roles && array['public','anon','authenticated']::name[];
  if v_mb is not null then
    raise exception 'CHECK 4 FAIL: mentor_bookings has a client-writable INSERT/ALL policy: %', v_mb;
  end if;

  raise notice 'CHECK 4 PASS: canonical is_admin in force, migration-195 policies present, no deprecated predicate, mentor_bookings not client-writable';
end $$;

\echo ''
\echo '================================================================'
\echo 'BLOCKING CHECKS (1, 1c, 4) PASSED — reaching this line means every'
\echo 'fail-closed assertion held. This does NOT by itself close the v1'
\echo 'gates: CHECK 2 needs manual RLS classification, CHECK 3 (extraction'
\echo 'archive-race) stays BLOCKED pending the code fix, and per-row RLS'
\echo 'visibility must be proven with a real user JWT (runbook Phase 2).'
\echo '================================================================'
