-- 225_pyq_stimuli_service_role_grant.sql
-- pyq_stimuli and pyq_question_stimuli (created in migration 223) were never
-- granted table-level privileges to service_role. Migration 173 did a blanket
-- `grant ... on all tables in schema public to service_role`, but that runs
-- once against the tables existing AT THAT TIME; no ALTER DEFAULT PRIVILEGES
-- was set, so tables created afterward (223's) do not inherit the grant.
--
-- Supabase's service_role bypasses RLS policies but still requires explicit
-- Postgres grants. The PYQ bulk importer (get_supabase_admin() == service_role)
-- now SELECTs pyq_stimuli during commit() (durable shared-stimulus identity,
-- fail-closed), which fails with 42501 "permission denied for table
-- pyq_stimuli" without this grant — surfaced by the e2e bulk-import flow.
--
-- Mirrors the sibling pyq_papers/pyq_questions/pyq_options tables (granted by
-- migration 173 because they already existed then). Idempotent.

grant select, insert, update, delete on public.pyq_stimuli to service_role;
grant select, insert, update, delete on public.pyq_question_stimuli to service_role;

notify pgrst, 'reload schema';
