-- Migration 202: RPC EXECUTE grant hardening (v1 least-privilege)
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 202 = MAX filesystem migration + 1.
--
-- FINDING (v1 RPC grant audit — docs/schema/rpc-grant-audit-v1.md)
--   Four SECURITY INVOKER functions were granted EXECUTE to `authenticated`:
--
--   A. Explicitly granted to `authenticated` (SECURITY INVOKER):
--     • promote_recruitment(jsonb)                          -- defs 043/044/048/058/059
--     • create_verification_report(jsonb)                   -- def 076
--     • supersede_and_create_verification_report(uuid,jsonb)-- def 076
--     • claim_source_for_scrape(uuid, integer)              -- def 054
--
--   Each is an admin- or worker-only operation invoked EXCLUSIVELY through the
--   service-role backend client (get_supabase_admin()). None declares
--   `security definer`, so each runs as the *caller*. Granting EXECUTE to
--   `authenticated` exposes them on the PostgREST `/rpc/` surface to any logged-in
--   user, bypassing the application-layer admin gate. Today only table-level RLS
--   stands between such a call and a privileged write — there is no in-function
--   authorization check. This is a defense-in-depth gap, not a confirmed live
--   exploit, but it must be closed before v1.
--
--   B. No explicit grant anywhere → hold the PostgreSQL DEFAULT, which grants
--      EXECUTE to PUBLIC (the repo has NO `ALTER DEFAULT PRIVILEGES` migration —
--      the only mention is a comment in migration 174). These are backend-only
--      mastery RPCs; two are SECURITY DEFINER (highest-risk class):
--     • apply_mock_mastery_delta(uuid,uuid,uuid,numeric,text) -- def 145, INVOKER, mastery_writer.py
--     • claim_mock_mastery_retry(uuid,text,timestamptz)       -- def 180, DEFINER, mock_engine.py
--     • complete_mock_mastery_retry(uuid)                     -- def 180, DEFINER, mock_engine.py
--
--   NOTE: `is_admin(uuid)` is intentionally left executable by `authenticated`
--   because RLS policies evaluate it; `refresh_course_stats` / `refresh_enrollment_count`
--   are trigger helpers, not /rpc/-callable, and are out of scope here.
--
-- FIX
--   Revoke EXECUTE from PUBLIC, anon AND authenticated, then re-assert the
--   intended service_role grant. All three are revoked explicitly because
--   `REVOKE FROM PUBLIC` does NOT remove explicit per-role grants held by anon /
--   authenticated — see migration 190, which records exactly this on staging
--   ("Migrations 188/189 only revoked from PUBLIC ... REVOKE FROM PUBLIC does not
--   remove those explicit per-role grants"). REVOKE of a privilege that was never
--   held is a no-op in PostgreSQL, so this is safe and idempotent.
--
-- BACKEND IMPACT: none. All eight (4 explicit + 3 mastery + 1 legacy) targets — the seven live call sites all use the service-role client:
--   • promote_recruitment            -> api/admin_scrape.py, scraping/runner.py
--   • create/supersede verification  -> scraping/verification_reports.py, verification_gateway.py
--   • claim_source_for_scrape        -> scraping/runner.py
--   • apply_mock_mastery_delta       -> study_os/mastery_writer.py
--   • claim/complete_mock_mastery_retry -> study_os/mock_engine.py
--
-- ROLLBACK
--   To restore the prior (insecure) state:
--     grant execute on function public.promote_recruitment(jsonb) to authenticated;
--     grant execute on function public.create_verification_report(jsonb) to authenticated;
--     grant execute on function public.supersede_and_create_verification_report(uuid, jsonb) to authenticated;
--     grant execute on function public.claim_source_for_scrape(uuid, integer) to authenticated;
--   The three mastery RPCs previously held the default PUBLIC grant:
--     grant execute on function public.apply_mock_mastery_delta(uuid, uuid, uuid, numeric, text) to public;
--     grant execute on function public.claim_mock_mastery_retry(uuid, text, timestamptz) to public;
--     grant execute on function public.complete_mock_mastery_retry(uuid) to public;

begin;

-- promote_recruitment(jsonb)
revoke execute on function public.promote_recruitment(jsonb) from public;
revoke execute on function public.promote_recruitment(jsonb) from anon;
revoke execute on function public.promote_recruitment(jsonb) from authenticated;
grant  execute on function public.promote_recruitment(jsonb) to service_role;

-- create_verification_report(jsonb)
revoke execute on function public.create_verification_report(jsonb) from public;
revoke execute on function public.create_verification_report(jsonb) from anon;
revoke execute on function public.create_verification_report(jsonb) from authenticated;
grant  execute on function public.create_verification_report(jsonb) to service_role;

-- supersede_and_create_verification_report(uuid, jsonb)
revoke execute on function public.supersede_and_create_verification_report(uuid, jsonb) from public;
revoke execute on function public.supersede_and_create_verification_report(uuid, jsonb) from anon;
revoke execute on function public.supersede_and_create_verification_report(uuid, jsonb) from authenticated;
grant  execute on function public.supersede_and_create_verification_report(uuid, jsonb) to service_role;

-- claim_source_for_scrape(uuid, integer)
revoke execute on function public.claim_source_for_scrape(uuid, integer) from public;
revoke execute on function public.claim_source_for_scrape(uuid, integer) from anon;
revoke execute on function public.claim_source_for_scrape(uuid, integer) from authenticated;
grant  execute on function public.claim_source_for_scrape(uuid, integer) to service_role;

-- apply_mock_mastery_delta(uuid, uuid, uuid, numeric, text) — default-PUBLIC, INVOKER
revoke execute on function public.apply_mock_mastery_delta(uuid, uuid, uuid, numeric, text) from public;
revoke execute on function public.apply_mock_mastery_delta(uuid, uuid, uuid, numeric, text) from anon;
revoke execute on function public.apply_mock_mastery_delta(uuid, uuid, uuid, numeric, text) from authenticated;
grant  execute on function public.apply_mock_mastery_delta(uuid, uuid, uuid, numeric, text) to service_role;

-- claim_mock_mastery_retry(uuid, text, timestamptz) — default-PUBLIC, SECURITY DEFINER
revoke execute on function public.claim_mock_mastery_retry(uuid, text, timestamptz) from public;
revoke execute on function public.claim_mock_mastery_retry(uuid, text, timestamptz) from anon;
revoke execute on function public.claim_mock_mastery_retry(uuid, text, timestamptz) from authenticated;
grant  execute on function public.claim_mock_mastery_retry(uuid, text, timestamptz) to service_role;

-- complete_mock_mastery_retry(uuid) — default-PUBLIC, SECURITY DEFINER
revoke execute on function public.complete_mock_mastery_retry(uuid) from public;
revoke execute on function public.complete_mock_mastery_retry(uuid) from anon;
revoke execute on function public.complete_mock_mastery_retry(uuid) from authenticated;
grant  execute on function public.complete_mock_mastery_retry(uuid) to service_role;

-- fn_fanout_alert_event(uuid) — def 007, SECURITY DEFINER, MUTATING, default-PUBLIC.
-- Legacy/dead (no current caller) but still /rpc/-exposed; harden defensively.
-- Invoked by DB triggers, which are unaffected by EXECUTE grants.
revoke execute on function public.fn_fanout_alert_event(uuid) from public;
revoke execute on function public.fn_fanout_alert_event(uuid) from anon;
revoke execute on function public.fn_fanout_alert_event(uuid) from authenticated;
grant  execute on function public.fn_fanout_alert_event(uuid) to service_role;

commit;
