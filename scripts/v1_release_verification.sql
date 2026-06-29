-- v1 release-gate verification (READ-ONLY).
--
-- Operationalizes the verification queries from docs/ops/v1-go-live-runbook.md
-- (Phase 1 RPC grants + Phase 2 RLS) and the migration-202 extraction archive-race
-- check into one runnable sheet. Run against STAGING first, then PROD:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/v1_release_verification.sql
--
-- Convention: each CHECK prints a header, then a query that returns rows ONLY on
-- failure (empty result = PASS). No writes are performed.

\pset pager off

\echo ''
\echo '================================================================'
\echo 'CHECK 1 — RPC grant hardening (migration 203): the 16 backend-only'
\echo 'RPCs must NOT be EXECUTE-able by PUBLIC / anon / authenticated.'
\echo 'has_function_privilege() accounts for the default PUBLIC grant, so a'
\echo 'function with no explicit revoke is correctly reported here.'
\echo 'EXPECT ZERO ROWS.'
\echo '================================================================'
with hardened(name) as (
  values
    ('promote_recruitment'),
    ('create_verification_report'),
    ('supersede_and_create_verification_report'),
    ('claim_source_for_scrape'),
    ('apply_mock_mastery_delta'),
    ('claim_mock_mastery_retry'),
    ('complete_mock_mastery_retry'),
    ('fn_fanout_alert_event'),
    ('claim_eligibility_queue'),
    ('enqueue_eligibility_recompute'),
    ('upsert_field_review'),
    ('consume_profile_merge_claim'),
    ('update_pyq_question_review_atomic'),
    ('start_attempt_from_blueprint'),
    ('fn_invalidate_projection_for_question'),
    ('fn_block_projection_for_question')
)
select p.proname,
       pg_get_function_identity_arguments(p.oid)                  as args,
       has_function_privilege('anon',          p.oid, 'EXECUTE')  as anon_can_execute,
       has_function_privilege('authenticated', p.oid, 'EXECUTE')  as authenticated_can_execute
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
join hardened h     on h.name = p.proname
where has_function_privilege('anon',          p.oid, 'EXECUTE')
   or has_function_privilege('authenticated', p.oid, 'EXECUTE')
order by p.proname;

\echo ''
\echo 'CHECK 1b — sanity: all 16 hardened functions actually exist (EXPECT 16).'
select count(*) as hardened_functions_present
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
where p.proname in (
  'promote_recruitment','create_verification_report',
  'supersede_and_create_verification_report','claim_source_for_scrape',
  'apply_mock_mastery_delta','claim_mock_mastery_retry','complete_mock_mastery_retry',
  'fn_fanout_alert_event','claim_eligibility_queue','enqueue_eligibility_recompute',
  'upsert_field_review','consume_profile_merge_claim','update_pyq_question_review_atomic',
  'start_attempt_from_blueprint','fn_invalidate_projection_for_question',
  'fn_block_projection_for_question'
);

\echo ''
\echo '================================================================'
\echo 'CHECK 2 — RLS coverage (INFO): public tables with RLS enabled and'
\echo 'ZERO policies. This is NOT auto-pass: diff the list + count against'
\echo 'docs/schema/rls-coverage-reconciliation-v1.md and CLASSIFY every'
\echo 'addition/removal. A FAIL is any returned table the frontend reads'
\echo 'directly with the anon/authenticated key (judgement, not SQL).'
\echo '================================================================'
select count(*) as zero_policy_table_count
from pg_class c
join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
where c.relkind = 'r' and c.relrowsecurity = true
  and not exists (
    select 1 from pg_policies p
    where p.schemaname = 'public' and p.tablename = c.relname
  );

select c.relname as zero_policy_table
from pg_class c
join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
where c.relkind = 'r' and c.relrowsecurity = true
  and not exists (
    select 1 from pg_policies p
    where p.schemaname = 'public' and p.tablename = c.relname
  )
order by c.relname;

\echo ''
\echo '================================================================'
\echo 'CHECK 3 — extraction archive-race (migration 202): no text_extract'
\echo 'job may be stranded in `running`. Until the finalize RPC/caller'
\echo 'terminalizes the document_archived path, this can be non-empty.'
\echo 'EXPECT ZERO ROWS (gate stays BLOCKED while any row returns).'
\echo '================================================================'
select id, document_id, status, created_at, updated_at
from document_processing_jobs
where job_type = 'text_extract'
  and status = 'running'
  and updated_at < now() - interval '15 minutes'
order by updated_at;

\echo ''
\echo '================================================================'
\echo 'CHECK 4 — is_admin hardening (migration 195/196): canonical'
\echo 'public.is_admin(uuid) exists AND no policy still references the'
\echo 'deprecated profiles.is_admin predicate (the 035-replay hazard).'
\echo 'EXPECT: is_admin present = true, and ZERO deprecated-predicate rows.'
\echo '================================================================'
select exists (
  select 1 from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
  where p.proname = 'is_admin'
) as canonical_is_admin_present;

select schemaname, tablename, policyname
from pg_policies
where schemaname = 'public'
  and (
    coalesce(qual, '')       ilike '%profiles%is_admin%'
    or coalesce(with_check,'') ilike '%profiles%is_admin%'
  )
order by tablename, policyname;

\echo ''
\echo '=== DONE. PASS = CHECK 1 / 3 / 4-deprecated empty, 1b = 16,'
\echo 'CHECK 4 is_admin = true; CHECK 2 reviewed against the RLS doc. ==='
\echo 'RLS per-row visibility (reviewed/locked only for authenticated) must be'
\echo 'proven separately with a real user JWT — see runbook Phase 2.'
