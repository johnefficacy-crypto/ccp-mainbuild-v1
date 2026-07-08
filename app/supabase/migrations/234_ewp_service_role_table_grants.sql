-- 234_ewp_service_role_table_grants.sql
-- The English Writing Practice (EWP) tables were created in migration 205
-- (writing_* + exam_descriptive_requirements + user_topic_mastery_evidence) and
-- migration 214 (writing_prompt_targets) — all AFTER migration 173's one-time
-- blanket `grant ... on all tables in schema public to service_role`. That grant
-- runs once against the tables existing at that time and no ALTER DEFAULT
-- PRIVILEGES was set, so tables created afterward never inherited it. Migration
-- 205 granted service_role only on EWP functions and the
-- effective_user_topic_mastery_evidence view — never table-level CRUD.
--
-- Supabase's service_role bypasses RLS policies but still requires explicit
-- Postgres grants. The writing-practice backend (get_supabase_admin() ==
-- service_role) reads/writes these tables directly — e.g. launch_writing()
-- SELECTs writing_sessions — which fails with 42501 "permission denied for
-- table writing_sessions" without this grant, surfaced by the writing-practice
-- e2e flow (POST /api/study/tasks/{id}/launch-writing → 500). The same latent
-- gap affects every EWP table the service_role backend touches.
--
-- Mirrors migration 225 (pyq_stimuli service_role grant). Idempotent — re-running
-- a grant is a no-op, so tables already covered elsewhere are unaffected.

grant select, insert, update, delete on public.writing_prompts               to service_role;
grant select, insert, update, delete on public.writing_rubrics               to service_role;
grant select, insert, update, delete on public.exam_descriptive_requirements to service_role;
grant select, insert, update, delete on public.writing_prompt_targets        to service_role;
grant select, insert, update, delete on public.writing_sessions              to service_role;
grant select, insert, update, delete on public.writing_session_units         to service_role;
grant select, insert, update, delete on public.writing_unit_versions         to service_role;
grant select, insert, update, delete on public.writing_evaluations           to service_role;
grant select, insert, update, delete on public.writing_evaluation_jobs       to service_role;
grant select, insert, update, delete on public.writing_session_checks        to service_role;
grant select, insert, update, delete on public.writing_issue_events          to service_role;
grant select, insert, update, delete on public.writing_issue_resolution_events to service_role;
grant select, insert, update, delete on public.writing_issue_projections     to service_role;
grant select, insert, update, delete on public.writing_issue_review_events   to service_role;
grant select, insert, update, delete on public.writing_issue_type_microtopic_map to service_role;
grant select, insert, update, delete on public.writing_mastery_shadow        to service_role;
grant select, insert, update, delete on public.writing_mastery_outbox        to service_role;
grant select, insert, update, delete on public.user_topic_mastery_evidence   to service_role;

notify pgrst, 'reload schema';
