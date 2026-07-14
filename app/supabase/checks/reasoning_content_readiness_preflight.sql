-- GQR-S3b — Reasoning content-readiness preflight (read-only counts).
--
-- The Reasoning mirror of quant_content_readiness_preflight.sql (GQR-S2).
-- Answers the readiness questions before/after any authoring/seed work:
--   * How many verified + active reasoning strategies exist?
--   * How many verified question↔strategy links exist?
--   * How many DISTINCT bank questions have a fully-verified, SCOPE-MATCHED
--     reasoning surface — i.e. are learner-ready under the exact conjunctive gate
--     the GQR-S4 read authority will enforce (mirrors quant_heuristics.py:
--     link verified AND strategy verified AND active AND every populated strategy
--     scope dimension resolves to the canonical Reasoning family AND equals the
--     question's topic/microtopic; missing/mismatched scope fails closed)?
--   * How many of those questions are reachable through mock/generated-mock
--     review (a bank row admitted by the mock-pipeline status gate)?
--
-- The scope gate matters (checkpost #996 P1): a null-scoped or cross-subject link
-- must NOT count as learner-ready, or the readiness signal is a false positive
-- once GQR-S4 mirrors the hardened Quant authority.
--
-- Read-only: emits NOTICEs, mutates nothing. If every count is zero the lane has
-- no production-ready verified linked content and GQR-S3b must seed/author some
-- before the VERIFY-DB proof (and GQR-S4 learner delivery) can pass.
--
-- Manual run:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f app/supabase/checks/reasoning_content_readiness_preflight.sql

begin read only;

do $$
declare
  v_strategies_verified   int;
  v_strategies_total      int;
  v_links_verified        int;
  v_links_total           int;
  v_ready_questions       int;
  v_ready_reachable       int;
  v_ready_ignoring_scope  int;
begin
  select count(*) into v_strategies_total from public.reasoning_strategies;
  select count(*) into v_strategies_verified
    from public.reasoning_strategies
    where reviewer_status = 'verified' and is_active = true;

  select count(*) into v_links_total from public.reasoning_question_strategies;
  select count(*) into v_links_verified
    from public.reasoning_question_strategies where reviewer_status = 'verified';

  -- Learner-ready questions: the exact conjunctive + SCOPE gate GQR-S4 will apply
  -- (see reasoning_scope_matches CTE-style predicate below).
  select count(distinct l.question_id) into v_ready_questions
    from public.reasoning_question_strategies l
    join public.reasoning_strategies s on s.id = l.strategy_id
    join public.mock_question_bank q on q.id = l.question_id
    where l.reviewer_status = 'verified'
      and s.reviewer_status = 'verified'
      and s.is_active = true
      -- at least one scope dimension present (fail closed on fully null scope)
      and (s.topic_id is not null or s.microtopic_id is not null)
      -- every populated scope dimension equals the question's scope
      and (s.topic_id is null or q.topic_id = s.topic_id)
      and (s.microtopic_id is null or q.microtopic_id = s.microtopic_id)
      -- every populated scope dimension resolves to canonical Reasoning family
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

  -- Of those, reachable through mock/generated-mock review. The selector/RLS
  -- gate admits only verified/live/published bank rows; mere existence is not
  -- sufficient (reviewed/draft/archived rows are not learner-reachable).
  select count(distinct l.question_id) into v_ready_reachable
    from public.reasoning_question_strategies l
    join public.reasoning_strategies s on s.id = l.strategy_id
    join public.mock_question_bank q on q.id = l.question_id
    where l.reviewer_status = 'verified'
      and s.reviewer_status = 'verified'
      and s.is_active = true
      and q.reviewer_status in ('verified', 'live', 'published')
      and (s.topic_id is not null or s.microtopic_id is not null)
      and (s.topic_id is null or q.topic_id = s.topic_id)
      and (s.microtopic_id is null or q.microtopic_id = s.microtopic_id)
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

  -- Diagnostic: links that WOULD look ready if scope were ignored. A positive
  -- delta vs v_ready_questions flags null-scoped / cross-subject / mis-topic
  -- links that the real gate rejects — content that needs re-scoping, not a pass.
  select count(distinct l.question_id) into v_ready_ignoring_scope
    from public.reasoning_question_strategies l
    join public.reasoning_strategies s on s.id = l.strategy_id
    where l.reviewer_status = 'verified'
      and s.reviewer_status = 'verified'
      and s.is_active = true;

  raise notice 'reasoning strategies: % verified+active / % total', v_strategies_verified, v_strategies_total;
  raise notice 'reasoning question links: % verified / % total', v_links_verified, v_links_total;
  raise notice 'learner-ready questions (conjunctive + scope gate): %', v_ready_questions;
  raise notice 'of which reachable via mock bank: %', v_ready_reachable;
  if v_ready_ignoring_scope > v_ready_questions then
    raise notice 'SCOPE WARNING: % verified link(s) fail the scope gate (null/cross-subject/mis-topic) — re-scope, they are NOT learner-ready.',
      v_ready_ignoring_scope - v_ready_questions;
  end if;

  if v_ready_reachable = 0 then
    raise notice 'READINESS: NONE — seed/author verified, scope-matched linked Reasoning content before the VERIFY-DB proof.';
  else
    raise notice 'READINESS: PRESENT — % learner-ready reachable question(s).', v_ready_reachable;
  end if;
end $$;

rollback;
