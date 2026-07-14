-- GQR-S3b — Reasoning content-readiness VERIFY-DB proof (rollback-only, self-contained).
--
-- The Reasoning mirror of validate_quant_heuristic_readiness.sql (GQR-S2).
-- Proves the end-to-end governed readiness path WITHOUT a migration, using only
-- existing paths: service-role INSERT into the authority tables + the existing
-- cms_review_reasoning_strategy lifecycle RPC (migration 262) to reach verified.
--
-- Asserted invariants (the GQR-S3b data/operator gate — what unblocks GQR-S4):
--   1. A reviewed (verified+active) strategy with a verified link appears in the
--      conjunctive learner-ready read.
--   2. Moving the LINK out of verified makes it disappear on the next read.
--   3. Retiring the STRATEGY (is_active=false via edit, then needs_correction via
--      the review RPC) each make it disappear.
--   4. The review RPC enforces its guards (bad reason rejected) and audits the
--      transition.
--
-- Rollback-only; leaves no data. Requires service_role / superuser (the tables
-- are service-role-only and the RPC is SECURITY DEFINER granted to service_role).
--
-- Manual run:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f app/supabase/validation/validate_reasoning_strategy_readiness.sql

begin;

-- Real actor so reviewed_by / created_by FKs → auth.users resolve.
insert into auth.users (id, instance_id, aud, role, email)
values ('eeeeeeee-0000-0000-0000-000000000503'::uuid,
        '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
        'reasoning-verify@example.com')
on conflict (id) do nothing;

-- Self-contained Reasoning fixtures (subject → topic → bank question).
insert into public.subjects (id, slug, name, subject_group)
values ('55550000-0000-0000-0000-000000000503'::uuid, 'reasoning-verify', 'Reasoning (verify)', 'reasoning')
on conflict (id) do nothing;

insert into public.topics (id, subject_id, slug, name, level)
values ('66660000-0000-0000-0000-000000000503'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
        'coding-decoding-verify', 'Coding-Decoding (verify)', 'topic')
on conflict (id) do nothing;

insert into public.mock_question_bank (id, question_text, question_type, reviewer_status)
values ('b2220000-0000-0000-0000-000000000503'::uuid,
        'In a code, CAT is written as DBU. How is DOG written?', 'mcq', 'verified')
on conflict (id) do nothing;

-- Author a strategy (pending) + assign it to the question (link pending) — the
-- governed intake path is a service-role INSERT; verification is the RPC below.
insert into public.reasoning_strategies
  (id, topic_id, strategy_code, name, strategy_type, applicability_rule,
   standard_method, faster_method, key_observation, worked_example, common_traps,
   reviewer_status, is_active, created_by)
values ('a0000000-0000-0000-0000-000000000503'::uuid,
        '66660000-0000-0000-0000-000000000503'::uuid,
        'RS-VERIFY-CODING-LETTERSHIFT', 'Letter-shift coding',
        'approach', '{"pattern": "coding_decoding", "method": "positional_shift"}'::jsonb,
        'Find the constant shift between plain and coded letters, then apply it.',
        'Read the gap from the first letter pair and reuse it.',
        'A constant shift means every letter moves by the same gap.',
        'CAT→DBU is +1, so DOG→EPH.',
        'Forgetting Z→A wrap-around.',
        'pending', true, 'eeeeeeee-0000-0000-0000-000000000503'::uuid)
on conflict (id) do nothing;

insert into public.reasoning_question_strategies
  (id, question_id, strategy_id, relevance, reviewer_status)
values ('11110000-0000-0000-0000-000000000503'::uuid,
        'b2220000-0000-0000-0000-000000000503'::uuid,
        'a0000000-0000-0000-0000-000000000503'::uuid, 'primary', 'pending')
on conflict (id) do nothing;

-- ── The conjunctive learner-ready read, expressed once as a reusable check. ──
-- Mirrors the gate GQR-S4's strategies_for_questions() will apply.
create function pg_temp._rs_ready(p_question uuid) returns int
language sql as $$
  select count(*)::int
  from public.reasoning_question_strategies l
  join public.reasoning_strategies s on s.id = l.strategy_id
  join public.mock_question_bank q on q.id = l.question_id
  where l.question_id = p_question
    and l.reviewer_status = 'verified'
    and s.reviewer_status = 'verified'
    and s.is_active = true
    and q.reviewer_status in ('verified', 'live', 'published');
$$;

do $$
declare
  v_q   constant uuid := 'b2220000-0000-0000-0000-000000000503'::uuid;
  v_s   constant uuid := 'a0000000-0000-0000-0000-000000000503'::uuid;
  v_l   constant uuid := '11110000-0000-0000-0000-000000000503'::uuid;
  v_act constant uuid := 'eeeeeeee-0000-0000-0000-000000000503'::uuid;
  v_tok timestamptz;
begin
  -- Pending strategy → not ready yet.
  if pg_temp._rs_ready(v_q) <> 0 then raise exception 'FAIL: pending strategy must not be learner-ready'; end if;
  raise notice 'PASS pending strategy is not learner-ready';

  -- Bad reason is rejected by the RPC (governance guard).
  begin
    select updated_at into v_tok from public.reasoning_strategies where id = v_s;
    perform public.cms_review_reasoning_strategy(v_s, 'pending', v_tok, 'verified', null, 'short', v_act, 'op@example.com');
    raise exception 'FAIL: short reason should be rejected';
  exception when others then
    if sqlerrm not like 'invalid_reason%' then raise; end if;
    raise notice 'PASS review reason gate';
  end;

  -- Verify the strategy via the governed RPC (pending → verified).
  select updated_at into v_tok from public.reasoning_strategies where id = v_s;
  perform public.cms_review_reasoning_strategy(
    v_s, 'pending', v_tok, 'verified', null, 'clear, correct letter-shift approach', v_act, 'op@example.com');
  if (select count(*) from public.admin_audit_logs
      where action = 'reasoning_strategy_status_transition'
        and entity_type = 'reasoning_strategy'
        and entity_id = v_s::text) <> 1 then
    raise exception 'FAIL: governed verification must create exactly one audit row';
  end if;
  raise notice 'PASS governed verification creates an audit row';

  -- Strategy verified but link still pending → still not ready (defense in depth).
  if pg_temp._rs_ready(v_q) <> 0 then raise exception 'FAIL: unverified link must gate a verified strategy'; end if;
  raise notice 'PASS verified strategy + pending link is not learner-ready';

  -- Verify the link (governed assignment path = service-role UPDATE; links carry
  -- their own reviewer_status but have no separate RPC in v1).
  update public.reasoning_question_strategies
    set reviewer_status = 'verified', reviewed_by = v_act, reviewed_at = now()
    where id = v_l;

  -- Now fully verified + active → appears.
  if pg_temp._rs_ready(v_q) <> 1 then raise exception 'FAIL: double-verified active strategy must be learner-ready'; end if;
  raise notice 'PASS double-verified active strategy IS learner-ready';

  -- Move the LINK out of verified → disappears.
  update public.reasoning_question_strategies set reviewer_status = 'rejected' where id = v_l;
  if pg_temp._rs_ready(v_q) <> 0 then raise exception 'FAIL: rejecting the link must remove the surface'; end if;
  raise notice 'PASS rejecting the link removes the surface';
  update public.reasoning_question_strategies set reviewer_status = 'verified' where id = v_l;

  -- Retire the STRATEGY (edit is_active=false) → disappears even with a verified link.
  update public.reasoning_strategies set is_active = false, updated_at = now() where id = v_s;
  if pg_temp._rs_ready(v_q) <> 0 then raise exception 'FAIL: retiring (is_active=false) must remove the surface'; end if;
  raise notice 'PASS retiring the strategy removes the surface';
  update public.reasoning_strategies set is_active = true, updated_at = now() where id = v_s;

  -- Reopen the STRATEGY for correction via the RPC (verified → needs_correction) → disappears.
  select updated_at into v_tok from public.reasoning_strategies where id = v_s;
  perform public.cms_review_reasoning_strategy(
    v_s, 'verified', v_tok, 'needs_correction', 'applicability rule under review',
    'reopening to re-verify the applicability rule', v_act, 'op@example.com');
  if pg_temp._rs_ready(v_q) <> 0 then raise exception 'FAIL: needs_correction must remove the surface'; end if;
  raise notice 'PASS needs_correction removes the surface';
end $$;

do $$ begin raise notice 'ALL PASS — Reasoning content readiness proven'; end $$;

rollback;
