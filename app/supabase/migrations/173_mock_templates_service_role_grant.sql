-- 173_mock_templates_service_role_grant.sql
-- Migration 135 enabled RLS on mock_templates but did not grant table-level
-- privileges to service_role.  Supabase's service_role bypasses RLS policies
-- but still requires explicit Postgres table grants.  The e2e global setup
-- and seed fixtures read this table under service_role and fail with 42501
-- without this grant.

grant select, insert, update, delete on public.mock_templates to service_role;

notify pgrst, 'reload schema';
