-- GQR-S3b — Reasoning content-readiness VERIFY-DB proof (rollback-only, self-contained).
--
-- The Reasoning mirror of validate_quant_heuristic_readiness.sql (GQR-S2), hardened
-- per checkpost #996 to prove the SCOPE gate the GQR-S4 read authority will enforce
-- (mirrors quant_heuristics._scope_matches). Uses only existing paths: service-role
-- INSERT into the authority tables + the existing cms_review_reasoning_strategy
-- lifecycle RPC (migration 262) to reach verified.
--
-- Asserted invariants (the GQR-S3b data/operator gate — what unblocks GQR-S4):
--   1. A reviewed (verified+active) strategy with a verified, SCOPE-MATCHED link on
--      a canonical-Reasoning-scoped question appears in the learner-ready read.
--   2. Moving the LINK out of verified makes it disappear.
--   3. Retiring the STRATEGY (is_active=false via edit, then needs_correction via
--      the review RPC) each make it disappear.
--   4. The review RPC enforces its guards (bad reason rejected) and audits the
--      transition.
--   5. SCOPE fails closed: a verified+active strategy with a verified link is NOT
--      learner-ready when the question's scope is MISSING (null topic), MISMATCHED
--      (different topic), or CROSS-SUBJECT (strategy scoped to a non-Reasoning
--      family topic). These are the false positives checkpost #996 flagged.
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

-- Self-contained fixtures. Canonical Reasoning subject (subject_group='reasoning')
-- with two topics, plus a Quant subject for the cross-subject negative.
insert into public.subjects (id, slug, name, subject_group) values
  ('55550000-0000-0000-0000-000000000503'::uuid, 'reasoning-verify', 'Reasoning (verify)', 'reasoning'),
  ('55550000-0000-0000-0000-0000000005f0'::uuid, 'quant-verify-xsub', 'Quant (verify xsub)', 'numerical')
on conflict (id) do nothing;

insert into public.topics (id, subject_id, slug, name, level, parent_topic_id) values
  ('66660000-0000-0000-0000-000000000503'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
   'coding-decoding-verify', 'Coding-Decoding (verify)', 'topic', null),
  ('66660000-0000-0000-0000-0000000005b0'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
   'series-verify', 'Series (verify)', 'topic', null),
  ('66660000-0000-0000-0000-0000000005f0'::uuid, '55550000-0000-0000-0000-0000000005f0'::uuid,
   'percentage-verify-xsub', 'Percentage (verify xsub)', 'topic', null),
  -- Microtopics for the parent-consistency check (checkpost #996 follow-up):
  --   m_ok  is a child of the Coding-Decoding topic (…503) → consistent pair
  --   m_bad is a child of the Series topic (…5b0), NOT …503 → inconsistent pair
  ('66660000-0000-0000-0000-0000000005a1'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
   'cd-letter-shift-verify', 'CD: letter shift (verify)', 'microtopic', '66660000-0000-0000-0000-000000000503'::uuid),
  ('66660000-0000-0000-0000-0000000005a2'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
   'series-geometric-verify', 'Series: geometric (verify)', 'microtopic', '66660000-0000-0000-0000-0000000005b0'::uuid)
on conflict (id) do nothing;

-- Bank questions. Scope varies to exercise the gate; all admitted (verified).
--   v_q  : correct Coding-Decoding scope  → should be ready
--   v_q2 : different Reasoning topic       → mismatched scope, not ready
--   v_q3 : NULL topic                      → missing scope, not ready
--   v_qx : Quant topic                     → cross-subject, not ready
insert into public.mock_question_bank (id, subject_id, topic_id, question_text, question_type, reviewer_status) values
  ('b2220000-0000-0000-0000-000000000503'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
   '66660000-0000-0000-0000-000000000503'::uuid, 'CAT→DBU, DOG→?', 'mcq', 'verified'),
  ('b2220000-0000-0000-0000-0000000005b0'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
   '66660000-0000-0000-0000-0000000005b0'::uuid, 'Next in 2,4,8,16,?', 'mcq', 'verified'),
  ('b2220000-0000-0000-0000-0000000005c0'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
   null, 'Unscoped reasoning question', 'mcq', 'verified'),
  ('b2220000-0000-0000-0000-0000000005f0'::uuid, '55550000-0000-0000-0000-0000000005f0'::uuid,
   '66660000-0000-0000-0000-0000000005f0'::uuid, '+20% then -20% net?', 'mcq', 'verified'),
  -- Both-dimension questions for the parent-consistency check.
  --   v_qb_ok : topic …503 + microtopic …5a1 (child of …503)  → consistent
  --   v_qb_bad: topic …503 + microtopic …5a2 (child of …5b0)  → inconsistent parent
  ('b2220000-0000-0000-0000-0000000005a1'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
   '66660000-0000-0000-0000-000000000503'::uuid, 'CAT→DBU (micro), DOG→?', 'mcq', 'verified'),
  ('b2220000-0000-0000-0000-0000000005a2'::uuid, '55550000-0000-0000-0000-000000000503'::uuid,
   '66660000-0000-0000-0000-000000000503'::uuid, 'CAT→DBU (bad micro), DOG→?', 'mcq', 'verified')
on conflict (id) do nothing;
update public.mock_question_bank set microtopic_id = '66660000-0000-0000-0000-0000000005a1'::uuid
  where id = 'b2220000-0000-0000-0000-0000000005a1'::uuid;
update public.mock_question_bank set microtopic_id = '66660000-0000-0000-0000-0000000005a2'::uuid
  where id = 'b2220000-0000-0000-0000-0000000005a2'::uuid;

-- Strategies: a Reasoning one (Coding-Decoding scope) and a Quant one (cross-subject).
insert into public.reasoning_strategies
  (id, topic_id, strategy_code, name, strategy_type, applicability_rule,
   standard_method, faster_method, key_observation, worked_example, common_traps,
   reviewer_status, is_active, created_by) values
  ('a0000000-0000-0000-0000-000000000503'::uuid, '66660000-0000-0000-0000-000000000503'::uuid,
   'RS-VERIFY-CODING-LETTERSHIFT', 'Letter-shift coding', 'approach',
   '{"pattern": "coding_decoding", "method": "positional_shift"}'::jsonb,
   'Find the constant shift between plain and coded letters, then apply it.',
   'Read the gap from the first letter pair and reuse it.',
   'A constant shift means every letter moves by the same gap.',
   'CAT→DBU is +1, so DOG→EPH.', 'Forgetting Z→A wrap-around.',
   'pending', true, 'eeeeeeee-0000-0000-0000-000000000503'::uuid),
  ('a0000000-0000-0000-0000-0000000005f0'::uuid, '66660000-0000-0000-0000-0000000005f0'::uuid,
   'RS-VERIFY-XSUB-QUANT', 'Cross-subject (Quant-scoped) strategy', 'approach',
   '{"pattern": "successive_percentage"}'::jsonb,
   'net% = a + b + a*b/100 (signed).', 'Reuse the signed formula.',
   'The ab/100 term is the trap.', '+20% then -20% → -4%.', 'Dropping the ab/100 term.',
   'pending', true, 'eeeeeeee-0000-0000-0000-000000000503'::uuid),
  -- Both-dimension strategies for the parent-consistency check.
  ('a0000000-0000-0000-0000-0000000005a1'::uuid, '66660000-0000-0000-0000-000000000503'::uuid,
   'RS-VERIFY-CD-MICRO-OK', 'Letter-shift (topic+micro, consistent)', 'approach',
   '{"pattern": "coding_decoding"}'::jsonb,
   'Apply the constant shift.', 'Reuse the first-pair gap.', 'Constant gap.',
   'CAT→DBU is +1.', 'Wrap-around.', 'pending', true, 'eeeeeeee-0000-0000-0000-000000000503'::uuid),
  ('a0000000-0000-0000-0000-0000000005a2'::uuid, '66660000-0000-0000-0000-000000000503'::uuid,
   'RS-VERIFY-CD-MICRO-BAD', 'Letter-shift (topic+micro, INCONSISTENT parent)', 'approach',
   '{"pattern": "coding_decoding"}'::jsonb,
   'Apply the constant shift.', 'Reuse the first-pair gap.', 'Constant gap.',
   'CAT→DBU is +1.', 'Wrap-around.', 'pending', true, 'eeeeeeee-0000-0000-0000-000000000503'::uuid)
on conflict (id) do nothing;
-- The micro dimensions are set post-insert so the strategy column list stays lean.
update public.reasoning_strategies set microtopic_id = '66660000-0000-0000-0000-0000000005a1'::uuid
  where id = 'a0000000-0000-0000-0000-0000000005a1'::uuid;   -- child of …503 → consistent
update public.reasoning_strategies set microtopic_id = '66660000-0000-0000-0000-0000000005a2'::uuid
  where id = 'a0000000-0000-0000-0000-0000000005a2'::uuid;   -- child of …5b0 → inconsistent

-- Links (author pending; verified below). Each question links to a strategy.
insert into public.reasoning_question_strategies (id, question_id, strategy_id, relevance, reviewer_status) values
  ('11110000-0000-0000-0000-000000000503'::uuid, 'b2220000-0000-0000-0000-000000000503'::uuid,
   'a0000000-0000-0000-0000-000000000503'::uuid, 'primary', 'pending'),
  ('11110000-0000-0000-0000-0000000005b0'::uuid, 'b2220000-0000-0000-0000-0000000005b0'::uuid,
   'a0000000-0000-0000-0000-000000000503'::uuid, 'primary', 'pending'),
  ('11110000-0000-0000-0000-0000000005c0'::uuid, 'b2220000-0000-0000-0000-0000000005c0'::uuid,
   'a0000000-0000-0000-0000-000000000503'::uuid, 'primary', 'pending'),
  ('11110000-0000-0000-0000-0000000005f0'::uuid, 'b2220000-0000-0000-0000-0000000005f0'::uuid,
   'a0000000-0000-0000-0000-0000000005f0'::uuid, 'primary', 'pending'),
  ('11110000-0000-0000-0000-0000000005a1'::uuid, 'b2220000-0000-0000-0000-0000000005a1'::uuid,
   'a0000000-0000-0000-0000-0000000005a1'::uuid, 'primary', 'pending'),
  ('11110000-0000-0000-0000-0000000005a2'::uuid, 'b2220000-0000-0000-0000-0000000005a2'::uuid,
   'a0000000-0000-0000-0000-0000000005a2'::uuid, 'primary', 'pending')
on conflict (id) do nothing;

-- ── The conjunctive + SCOPE learner-ready read, expressed once. ──
-- Mirrors the exact gate GQR-S4's strategies_for_questions() will apply:
-- link verified AND strategy verified AND active AND question admitted AND every
-- populated strategy scope dimension resolves to canonical Reasoning family AND
-- equals the question's topic/microtopic (missing/mismatched scope fails closed).
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
    and q.reviewer_status in ('verified', 'live', 'published')
    and (s.topic_id is not null or s.microtopic_id is not null)
    and (s.topic_id is null or q.topic_id = s.topic_id)
    and (s.microtopic_id is null or q.microtopic_id = s.microtopic_id)
    -- both dimensions populated ⇒ microtopic must be a child of the topic
    and (s.topic_id is null or s.microtopic_id is null or exists (
          select 1 from public.topics mt
          where mt.id = s.microtopic_id and mt.parent_topic_id = s.topic_id))
    and (s.topic_id is null or exists (
          select 1 from public.topics t join public.subjects sub on sub.id = t.subject_id
          where t.id = s.topic_id
            and (lower(sub.subject_group) = 'reasoning'
                 or lower(sub.slug) in ('general-intelligence-reasoning', 'reasoning'))))
    and (s.microtopic_id is null or exists (
          select 1 from public.topics t join public.subjects sub on sub.id = t.subject_id
          where t.id = s.microtopic_id
            and (lower(sub.subject_group) = 'reasoning'
                 or lower(sub.slug) in ('general-intelligence-reasoning', 'reasoning'))));
$$;

do $$
declare
  v_q   constant uuid := 'b2220000-0000-0000-0000-000000000503'::uuid;  -- correct scope
  v_q2  constant uuid := 'b2220000-0000-0000-0000-0000000005b0'::uuid;  -- mismatched topic
  v_q3  constant uuid := 'b2220000-0000-0000-0000-0000000005c0'::uuid;  -- null scope
  v_qx  constant uuid := 'b2220000-0000-0000-0000-0000000005f0'::uuid;  -- cross-subject
  v_qb_ok  constant uuid := 'b2220000-0000-0000-0000-0000000005a1'::uuid; -- topic+micro consistent
  v_qb_bad constant uuid := 'b2220000-0000-0000-0000-0000000005a2'::uuid; -- topic+micro inconsistent
  v_s   constant uuid := 'a0000000-0000-0000-0000-000000000503'::uuid;  -- reasoning strategy
  v_sx  constant uuid := 'a0000000-0000-0000-0000-0000000005f0'::uuid;  -- quant-scoped strategy
  v_sb_ok  constant uuid := 'a0000000-0000-0000-0000-0000000005a1'::uuid; -- both dims, consistent
  v_sb_bad constant uuid := 'a0000000-0000-0000-0000-0000000005a2'::uuid; -- both dims, inconsistent
  v_l   constant uuid := '11110000-0000-0000-0000-000000000503'::uuid;  -- correct-scope link
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

  -- Verify BOTH strategies via the governed RPC (pending → verified).
  select updated_at into v_tok from public.reasoning_strategies where id = v_s;
  perform public.cms_review_reasoning_strategy(
    v_s, 'pending', v_tok, 'verified', null, 'clear, correct letter-shift approach', v_act, 'op@example.com');
  select updated_at into v_tok from public.reasoning_strategies where id = v_sx;
  perform public.cms_review_reasoning_strategy(
    v_sx, 'pending', v_tok, 'verified', null, 'cross-subject fixture verified for the negative test', v_act, 'op@example.com');
  select updated_at into v_tok from public.reasoning_strategies where id = v_sb_ok;
  perform public.cms_review_reasoning_strategy(
    v_sb_ok, 'pending', v_tok, 'verified', null, 'consistent topic+microtopic pair fixture', v_act, 'op@example.com');
  select updated_at into v_tok from public.reasoning_strategies where id = v_sb_bad;
  perform public.cms_review_reasoning_strategy(
    v_sb_bad, 'pending', v_tok, 'verified', null, 'inconsistent parent pair fixture for the negative test', v_act, 'op@example.com');
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

  -- Verify every link (governed assignment path = service-role UPDATE; links carry
  -- their own reviewer_status but have no separate RPC in v1).
  update public.reasoning_question_strategies set reviewer_status = 'verified', reviewed_by = v_act, reviewed_at = now()
    where id in ('11110000-0000-0000-0000-000000000503'::uuid,
                 '11110000-0000-0000-0000-0000000005b0'::uuid,
                 '11110000-0000-0000-0000-0000000005c0'::uuid,
                 '11110000-0000-0000-0000-0000000005f0'::uuid,
                 '11110000-0000-0000-0000-0000000005a1'::uuid,
                 '11110000-0000-0000-0000-0000000005a2'::uuid);

  -- Correct scope + fully verified + active → appears.
  if pg_temp._rs_ready(v_q) <> 1 then raise exception 'FAIL: double-verified, scope-matched strategy must be learner-ready'; end if;
  raise notice 'PASS double-verified scope-matched strategy IS learner-ready';

  -- ── Scope gate negatives (checkpost #996 P1) ──
  if pg_temp._rs_ready(v_q2) <> 0 then raise exception 'FAIL: mismatched topic must NOT be learner-ready'; end if;
  raise notice 'PASS mismatched-topic question is not learner-ready';
  if pg_temp._rs_ready(v_q3) <> 0 then raise exception 'FAIL: missing (null) scope must fail closed'; end if;
  raise notice 'PASS null-scope question fails closed';
  if pg_temp._rs_ready(v_qx) <> 0 then raise exception 'FAIL: cross-subject (non-Reasoning family) scope must NOT be learner-ready'; end if;
  raise notice 'PASS cross-subject strategy is not learner-ready';

  -- Parent-consistency (checkpost #996 follow-up): both dims populated ⇒ the
  -- microtopic must be a child of the topic. A consistent pair is ready; an
  -- inconsistent parent (microtopic under a different topic) fails closed.
  if pg_temp._rs_ready(v_qb_ok) <> 1 then raise exception 'FAIL: consistent topic+microtopic pair must be learner-ready'; end if;
  raise notice 'PASS consistent topic+microtopic pair IS learner-ready';
  if pg_temp._rs_ready(v_qb_bad) <> 0 then raise exception 'FAIL: inconsistent microtopic parent must fail closed'; end if;
  raise notice 'PASS inconsistent topic/microtopic parent fails closed';

  -- Move the correct-scope LINK out of verified → disappears.
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

do $$ begin raise notice 'ALL PASS — Reasoning content readiness proven (scope-aware)'; end $$;

rollback;
