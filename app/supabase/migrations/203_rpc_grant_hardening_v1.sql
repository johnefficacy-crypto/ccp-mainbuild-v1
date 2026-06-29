-- Migration 203: RPC EXECUTE grant hardening (v1 least-privilege)
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 203 = MAX filesystem migration + 1.
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
--   C. SECURITY DEFINER backend RPCs that only `GRANT ... TO service_role` and never
--      revoke the default PUBLIC (a GRANT does not remove it): claim_eligibility_queue
--      (010), enqueue_eligibility_recompute (041), upsert_field_review (127),
--      consume_profile_merge_claim (128).
--
--   D. SECURITY DEFINER backend RPCs that revoke only PUBLIC (insufficient per migration
--      190): update_pyq_question_review_atomic (162), start_attempt_from_blueprint (179),
--      fn_invalidate_projection_for_question (184), fn_block_projection_for_question (184).
--
--   16 functions total. NOTE: `is_admin(uuid)` is intentionally left executable by
--   `authenticated` because RLS policies evaluate it; `refresh_course_stats` /
--   `refresh_enrollment_count` are trigger helpers, not /rpc/-callable, and are out of scope.
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
-- BACKEND IMPACT: none. All 16 targets are backend-only; every live call site uses
-- the service-role client (fn_fanout_alert_event is legacy/dead, trigger-invoked):
--   • promote_recruitment            -> api/admin_scrape.py, scraping/runner.py
--   • create/supersede verification  -> scraping/verification_reports.py, verification_gateway.py
--   • claim_source_for_scrape        -> scraping/runner.py
--   • apply_mock_mastery_delta       -> study_os/mastery_writer.py
--   • claim/complete_mock_mastery_retry -> study_os/mock_engine.py
--   • claim_eligibility_queue / enqueue_eligibility_recompute -> eligibility worker/endpoints
--   • upsert_field_review            -> api/admin_scrape.py
--   • consume_profile_merge_claim    -> profile/merge_claim.py
--   • update_pyq_question_review_atomic / start_attempt_from_blueprint / fn_invalidate_projection_for_question / fn_block_projection_for_question -> exam-intelligence + study_os (service_role)
--
-- ROLLBACK
--   Rollback is intentionally NOT provided as an exact prior-state restore: the
--   "prior state" for these 16 functions is precisely the insecure posture this
--   migration closes (default PUBLIC for Groups B/C, explicit authenticated for
--   Group A, PUBLIC-only revoke for Group D), so reverting would re-open the
--   exposure. If a function must be re-exposed, do it deliberately and narrowly,
--   e.g. `grant execute on function public.<fn>(<args>) to authenticated;` for the
--   single function in question — never a blanket revert of this migration.

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

-- ── Group C: SECURITY DEFINER backend RPCs that only GRANT service_role and never
--    revoke the default PUBLIC (a GRANT does not remove the default PUBLIC EXECUTE) ──
-- claim_eligibility_queue(integer) — def 010
revoke execute on function public.claim_eligibility_queue(integer) from public;
revoke execute on function public.claim_eligibility_queue(integer) from anon;
revoke execute on function public.claim_eligibility_queue(integer) from authenticated;
grant  execute on function public.claim_eligibility_queue(integer) to service_role;

-- enqueue_eligibility_recompute(uuid, uuid, text, jsonb) — def 041
revoke execute on function public.enqueue_eligibility_recompute(uuid, uuid, text, jsonb) from public;
revoke execute on function public.enqueue_eligibility_recompute(uuid, uuid, text, jsonb) from anon;
revoke execute on function public.enqueue_eligibility_recompute(uuid, uuid, text, jsonb) from authenticated;
grant  execute on function public.enqueue_eligibility_recompute(uuid, uuid, text, jsonb) to service_role;

-- upsert_field_review(uuid,text,text,text,text,uuid,text,jsonb,jsonb,text,uuid) — def 127
revoke execute on function public.upsert_field_review(uuid, text, text, text, text, uuid, text, jsonb, jsonb, text, uuid) from public;
revoke execute on function public.upsert_field_review(uuid, text, text, text, text, uuid, text, jsonb, jsonb, text, uuid) from anon;
revoke execute on function public.upsert_field_review(uuid, text, text, text, text, uuid, text, jsonb, jsonb, text, uuid) from authenticated;
grant  execute on function public.upsert_field_review(uuid, text, text, text, text, uuid, text, jsonb, jsonb, text, uuid) to service_role;

-- consume_profile_merge_claim(text, uuid) — def 128
revoke execute on function public.consume_profile_merge_claim(text, uuid) from public;
revoke execute on function public.consume_profile_merge_claim(text, uuid) from anon;
revoke execute on function public.consume_profile_merge_claim(text, uuid) from authenticated;
grant  execute on function public.consume_profile_merge_claim(text, uuid) to service_role;

-- ── Group D: SECURITY DEFINER backend RPCs that revoke only PUBLIC (insufficient —
--    migration 190 proved Supabase also holds explicit anon/authenticated grants) ──
-- update_pyq_question_review_atomic(uuid, text, uuid, timestamptz) — def 162
revoke execute on function public.update_pyq_question_review_atomic(uuid, text, uuid, timestamptz) from public;
revoke execute on function public.update_pyq_question_review_atomic(uuid, text, uuid, timestamptz) from anon;
revoke execute on function public.update_pyq_question_review_atomic(uuid, text, uuid, timestamptz) from authenticated;
grant  execute on function public.update_pyq_question_review_atomic(uuid, text, uuid, timestamptz) to service_role;

-- start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz) — def 179
revoke execute on function public.start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz) from public;
revoke execute on function public.start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz) from anon;
revoke execute on function public.start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz) from authenticated;
grant  execute on function public.start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz) to service_role;

-- fn_invalidate_projection_for_question(uuid) — def 184
revoke execute on function public.fn_invalidate_projection_for_question(uuid) from public;
revoke execute on function public.fn_invalidate_projection_for_question(uuid) from anon;
revoke execute on function public.fn_invalidate_projection_for_question(uuid) from authenticated;
grant  execute on function public.fn_invalidate_projection_for_question(uuid) to service_role;

-- fn_block_projection_for_question(uuid, text) — def 184
revoke execute on function public.fn_block_projection_for_question(uuid, text) from public;
revoke execute on function public.fn_block_projection_for_question(uuid, text) from anon;
revoke execute on function public.fn_block_projection_for_question(uuid, text) from authenticated;
grant  execute on function public.fn_block_projection_for_question(uuid, text) to service_role;

commit;
