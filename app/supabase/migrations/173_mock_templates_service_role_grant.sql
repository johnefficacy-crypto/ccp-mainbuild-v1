-- 173_mock_templates_service_role_grant.sql
-- Several tables had RLS enabled without granting table-level privileges to
-- service_role.  Supabase's service_role bypasses RLS policies but still
-- requires explicit Postgres grants; the e2e global setup and seed fixtures
-- hit these tables under service_role and fail with 42501 without them.

grant select, insert, update, delete on public.mock_templates to service_role;
grant select, insert, update, delete on public.mock_attempts to service_role;
grant select, insert, update, delete on public.mock_template_sections to service_role;
grant select, insert, update, delete on public.notification_alerts to service_role;
grant select, insert, update, delete on public.profiles to service_role;

notify pgrst, 'reload schema';
