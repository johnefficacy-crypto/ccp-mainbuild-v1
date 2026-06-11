-- 173_mock_templates_service_role_grant.sql
-- Several tables had RLS enabled without granting table-level privileges to
-- service_role.  Supabase's service_role bypasses RLS policies but still
-- requires explicit Postgres grants; the e2e global setup and seed fixtures
-- hit these tables under service_role and fail with 42501 without them.
-- Rather than enumerating individual tables, grant on all current public
-- tables in one statement (idempotent; existing grants are no-ops).

grant select, insert, update, delete on all tables in schema public to service_role;
grant usage on schema public to service_role;

notify pgrst, 'reload schema';
