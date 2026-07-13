-- 251_pyq_projection_service_role_read_grant.sql
--
-- Grant service_role SELECT on public.pyq_mock_question_projections.
--
-- Migration 183 created the projection-bridge table with RLS, granted EXECUTE on
-- the projection/invalidation RPCs to service_role, and revoked direct
-- INSERT/UPDATE/DELETE from public/anon/authenticated — writes flow ONLY through
-- the SECURITY DEFINER project_pyq_question_to_mock_bank() RPC. But it never
-- granted service_role any TABLE-level privilege, so the backend's service-role
-- client — which READS this table directly to gate learner PYQ practice
-- (pyq_practice._active_projection_ids / practice_ready_counts_by_paper /
-- practiceable_topic_ids) — fails with `42501 permission denied for table
-- pyq_mock_question_projections` on any database where service_role relies on
-- explicit grants rather than implicit superuser/default privileges.
--
-- Symptom: practice readiness fails closed (every paper shows 0 practice-ready,
-- no Practice CTA) and the practice launch 500s, wherever projected PYQ data
-- exists. It went unnoticed because no path had exercised the service-role read
-- against a projected pool until the projected-PYQ practice E2E landed.
--
-- Fix: grant SELECT only. Writes stay RPC-only, so the governance posture from
-- 183 ("service_role only for the RPC") is preserved — the backend never DMLs
-- this table directly. service_role bypasses RLS, so the existing policies are
-- unaffected. Additive + idempotent (GRANT is a no-op if already held). Mirrors
-- migration 174, which granted service_role table privileges on the sibling
-- mock_generated_blueprints.

grant select on public.pyq_mock_question_projections to service_role;

notify pgrst, 'reload schema';
