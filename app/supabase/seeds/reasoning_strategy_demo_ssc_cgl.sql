-- GQR-S3b — Reasoning strategy demo seed (SSC-CGL), idempotent and audited.
--
-- The Reasoning mirror of quant_heuristic_demo_ssc_cgl.sql (GQR-S2). Authors
-- pending rows through service-role table writes, then verifies each strategy
-- through cms_review_reasoning_strategy (migration 262). This preserves CAS +
-- audit ownership instead of publishing by direct reviewer_status writes.
-- Question-link review remains a service-role UPDATE because v1 has no link RPC
-- (the link carries its own reviewer_status; migration 262 ships only the
-- strategy review RPC, mirroring the Quant lane).
--
-- SCOPE-AWARE (checkpost #996 P1): the demo question is seeded with the canonical
-- Reasoning subject_id + Coding-Decoding topic_id that MATCH the strategy scope,
-- so it satisfies the same conjunctive scope gate the GQR-S4 read authority will
-- enforce (mirrors quant_heuristics._scope_matches: every populated strategy
-- scope dimension resolves to the canonical Reasoning family AND equals the
-- question's topic/microtopic; missing scope fails closed). A null-scoped or
-- cross-subject question would NOT be learner-ready and is not seeded.
--
-- POSTCONDITION-GUARDED (checkpost #996 P2): the question is reconciled to the
-- admitted+scoped state deterministically, and a final assertion block raises
-- (aborting the transaction) unless the promised end state — 2 verified active
-- strategies + exactly 1 verified, scope-matched link — actually exists. The seed
-- can therefore never commit a silent no-op.
--
-- Depends on:
--   exam_intelligence_demo_ssc_cgl.sql  (Reasoning subject + Coding-Decoding topic)
--   migration 262
--
-- Required psql variables:
--   actor_user_id — an existing auth.users.id for the reviewing operator
--   actor_email   — that operator's audit email
--
-- Manual run:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -v actor_user_id="<admin-auth-user-uuid>" \
--     -v actor_email="<admin-email>" \
--     -f app/supabase/seeds/reasoning_strategy_demo_ssc_cgl.sql
--
-- Re-runs are stable: unchanged verified rows are not re-reviewed. If content
-- differs, the row returns to pending and the RPC creates a fresh audit record.
-- Links resolve the strategy by strategy_code, so a pre-existing row with the
-- same code but a different UUID cannot break the FK.

begin;

create temporary table reasoning_seed_actor (
  user_id uuid primary key,
  email text
) on commit drop;

insert into pg_temp.reasoning_seed_actor (user_id, email)
values (:'actor_user_id'::uuid, nullif(:'actor_email', ''));

do $$
begin
  if not exists (
    select 1
    from auth.users u
    join pg_temp.reasoning_seed_actor a on a.user_id = u.id
  ) then
    raise exception 'seed_actor_not_found: actor_user_id must reference auth.users';
  end if;
  -- The Coding-Decoding topic (under the Reasoning subject) is the canonical scope
  -- the strategies and demo question share; it must be canonical Reasoning family.
  if not exists (
    select 1
    from public.topics t
    join public.subjects s on s.id = t.subject_id
    where t.id = '66666666-6666-6666-6666-666666666667'::uuid
      and (lower(s.subject_group) = 'reasoning'
           or lower(s.slug) in ('general-intelligence-reasoning', 'reasoning'))
  ) then
    raise exception 'seed_scope_not_found: run exam_intelligence_demo_ssc_cgl.sql first (canonical Reasoning Coding-Decoding topic)';
  end if;
end $$;

-- A learner-reachable demo Reasoning bank question (verified) SCOPED to the same
-- canonical Reasoning subject/topic as the strategies. The pilot bank ships Quant
-- rows only, so the Reasoning surface needs its own reachable, correctly-scoped
-- question. Reconcile scope + admitted status deterministically so a pre-existing
-- row with the same demo id cannot leave the link ungated (checkpost P2).
insert into public.mock_question_bank (id, subject_id, topic_id, question_text, question_type, reviewer_status)
values ('b2000001-0000-0000-0000-0000000d5301'::uuid,
        '55555555-5555-5555-5555-555555555553'::uuid,
        '66666666-6666-6666-6666-666666666667'::uuid,
        'In a code, CAT is written as DBU. How is DOG written?', 'mcq', 'verified')
on conflict (id) do update
set subject_id = excluded.subject_id,
    topic_id = excluded.topic_id,
    reviewer_status = 'verified';

-- Author pending content. Existing rows are reset to pending only when their
-- governed content changes; unchanged verified rows remain untouched. Both
-- strategies are scoped to the Coding-Decoding topic (topic-only scope) so the
-- linked question's topic_id must equal it to be learner-ready.
insert into public.reasoning_strategies as existing
  (id, topic_id, strategy_code, name, strategy_type, applicability_rule,
   formula_latex, standard_method, faster_method, key_observation,
   worked_example, common_traps, reviewer_status, is_active, created_by)
select v.id, v.topic_id, v.strategy_code, v.name, v.strategy_type,
       v.applicability_rule, v.formula_latex, v.standard_method, v.faster_method,
       v.key_observation, v.worked_example, v.common_traps,
       'pending', true, a.user_id
from (
  values
    ('a0000000-0000-0000-0000-0000000d5301'::uuid,
     '66666666-6666-6666-6666-666666666667'::uuid,
     'RS-SSC-CODING-LETTERSHIFT', 'Letter-shift coding', 'approach',
     '{"pattern": "coding_decoding", "method": "positional_shift"}'::jsonb,
     null,
     'Map each letter to its alphabet position, find the constant shift between the plain and coded word, then apply the same shift to decode/encode.',
     'Read the gap from the first matching letter pair and reuse it — no need to re-derive per letter once the shift is constant.',
     'A constant forward/backward shift means the gap between plain and coded positions is identical for every letter.',
     'CAT→DBU is a +1 shift (C→D, A→B, T→U); so DOG→EPH.',
     'Forgetting to wrap around Z→A, or mixing forward and backward shifts within one word.'),
    ('a0000000-0000-0000-0000-0000000d5302'::uuid,
     '66666666-6666-6666-6666-666666666667'::uuid,
     'RS-SSC-CODING-PATTERNSCAN', 'Scan for the coding pattern class', 'pattern',
     '{"pattern": "coding_decoding", "method": "pattern_classification"}'::jsonb,
     null,
     'Before solving, classify the code: letter-shift, letter-to-number, reversal, or symbol substitution — the class dictates the technique.',
     'Check the first and last letters first; reversal and shift codes reveal themselves immediately from the endpoints.',
     'Most coding-decoding questions belong to one of four recurring classes; identifying the class collapses the search.',
     'If TIGER→REGIT, the endpoints swap → it is a reversal code, not a shift.',
     'Assuming a shift code when the mapping is actually a reversal or a number substitution.')
) as v(
  id, topic_id, strategy_code, name, strategy_type, applicability_rule,
  formula_latex, standard_method, faster_method, key_observation,
  worked_example, common_traps
)
cross join pg_temp.reasoning_seed_actor a
on conflict (strategy_code) do update
set topic_id = excluded.topic_id,
    name = excluded.name,
    strategy_type = excluded.strategy_type,
    applicability_rule = excluded.applicability_rule,
    formula_latex = excluded.formula_latex,
    standard_method = excluded.standard_method,
    faster_method = excluded.faster_method,
    key_observation = excluded.key_observation,
    worked_example = excluded.worked_example,
    common_traps = excluded.common_traps,
    reviewer_status = 'pending',
    reviewer_notes = null,
    reviewed_by = null,
    reviewed_at = null,
    is_active = true,
    updated_at = now()
where (
  existing.topic_id, existing.name, existing.strategy_type,
  existing.applicability_rule, existing.formula_latex,
  existing.standard_method, existing.faster_method, existing.key_observation,
  existing.worked_example, existing.common_traps, existing.is_active
) is distinct from (
  excluded.topic_id, excluded.name, excluded.strategy_type,
  excluded.applicability_rule, excluded.formula_latex,
  excluded.standard_method, excluded.faster_method, excluded.key_observation,
  excluded.worked_example, excluded.common_traps, excluded.is_active
);

-- Route every non-verified target through the lifecycle matrix, then verify it.
-- Unchanged verified rows are no-ops, keeping re-runs audit-idempotent.
do $$
declare
  v_s record;
  v_actor uuid;
  v_email text;
  v_status text;
  v_updated_at timestamptz;
begin
  select user_id, email into v_actor, v_email
  from pg_temp.reasoning_seed_actor;

  for v_s in
    select id, strategy_code, reviewer_status, updated_at
    from public.reasoning_strategies
    where strategy_code in ('RS-SSC-CODING-LETTERSHIFT', 'RS-SSC-CODING-PATTERNSCAN')
    order by strategy_code
  loop
    if v_s.reviewer_status in ('rejected', 'needs_correction') then
      perform public.cms_review_reasoning_strategy(
        v_s.id, v_s.reviewer_status, v_s.updated_at, 'pending', null,
        'Demo seed reopens governed Reasoning content for review', v_actor, v_email
      );
      select reviewer_status, updated_at
        into v_status, v_updated_at
      from public.reasoning_strategies
      where id = v_s.id;
      v_s.reviewer_status := v_status;
      v_s.updated_at := v_updated_at;
    end if;

    if v_s.reviewer_status = 'pending' then
      perform public.cms_review_reasoning_strategy(
        v_s.id, 'pending', v_s.updated_at, 'verified', null,
        'Demo seed verifies reviewed SSC-CGL Reasoning content', v_actor, v_email
      );
    elsif v_s.reviewer_status <> 'verified' then
      raise exception 'seed_unexpected_status: strategy % has status %',
        v_s.strategy_code, v_s.reviewer_status;
    end if;
  end loop;
end $$;

-- Assign the letter-shift strategy to the reachable, scope-matched demo question.
-- Resolve by strategy_code to survive UUID conflicts.
insert into public.reasoning_question_strategies as existing
  (id, question_id, strategy_id, relevance, reviewer_status)
select '11110000-0000-0000-0000-0000000d5301'::uuid,
       q.id, s.id, 'primary', 'pending'
from public.mock_question_bank q
join public.reasoning_strategies s
  on s.strategy_code = 'RS-SSC-CODING-LETTERSHIFT'
where q.id = 'b2000001-0000-0000-0000-0000000d5301'::uuid
  and q.reviewer_status in ('verified', 'live', 'published')
on conflict (question_id, strategy_id) do update
set relevance = excluded.relevance,
    reviewer_status = 'pending',
    reviewed_by = null,
    reviewed_at = null
where existing.relevance is distinct from excluded.relevance;

update public.reasoning_question_strategies l
set reviewer_status = 'verified',
    reviewed_by = a.user_id,
    reviewed_at = now()
from public.reasoning_strategies s
cross join pg_temp.reasoning_seed_actor a
where l.strategy_id = s.id
  and s.strategy_code = 'RS-SSC-CODING-LETTERSHIFT'
  and l.question_id = 'b2000001-0000-0000-0000-0000000d5301'::uuid
  and l.reviewer_status <> 'verified';

-- Postcondition (checkpost #996 P2): fail loudly rather than commit a no-op. The
-- link check applies the SAME conjunctive + scope gate GQR-S4 will consume, so a
-- committed seed provably produced learner-ready content.
do $$
declare
  v_strats int;
  v_ready_link int;
begin
  select count(*) into v_strats
  from public.reasoning_strategies
  where strategy_code in ('RS-SSC-CODING-LETTERSHIFT', 'RS-SSC-CODING-PATTERNSCAN')
    and reviewer_status = 'verified' and is_active = true;
  if v_strats <> 2 then
    raise exception 'seed_postcondition_failed: expected 2 verified active strategies, found %', v_strats;
  end if;

  select count(*) into v_ready_link
  from public.reasoning_question_strategies l
  join public.reasoning_strategies s on s.id = l.strategy_id
  join public.mock_question_bank q on q.id = l.question_id
  where s.strategy_code = 'RS-SSC-CODING-LETTERSHIFT'
    and l.question_id = 'b2000001-0000-0000-0000-0000000d5301'::uuid
    and l.reviewer_status = 'verified'
    and s.reviewer_status = 'verified'
    and s.is_active = true
    and q.reviewer_status in ('verified', 'live', 'published')
    -- scope gate: topic-scoped strategy ⇒ question topic must equal it; a
    -- populated microtopic must match the question and be a child of the topic.
    and s.topic_id is not null
    and q.topic_id = s.topic_id
    and (s.microtopic_id is null or q.microtopic_id = s.microtopic_id)
    and (s.microtopic_id is null or exists (
          select 1 from public.topics mt
          where mt.id = s.microtopic_id and mt.parent_topic_id = s.topic_id));
  if v_ready_link <> 1 then
    raise exception 'seed_postcondition_failed: expected 1 verified scope-matched link, found %', v_ready_link;
  end if;

  raise notice 'SEED OK — 2 verified strategies + 1 verified scope-matched learner-ready link';
end $$;

commit;
