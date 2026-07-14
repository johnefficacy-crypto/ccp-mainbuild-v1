-- GQR-S3b — Reasoning content-readiness preflight (read-only counts).
--
-- The Reasoning mirror of quant_content_readiness_preflight.sql (GQR-S2).
-- Answers the readiness questions before/after any authoring/seed work:
--   * How many verified + active reasoning strategies exist?
--   * How many verified question↔strategy links exist?
--   * How many DISTINCT bank questions have a fully-verified reasoning surface
--     (link verified AND strategy verified AND active) — i.e. are learner-ready
--     under the conjunctive gate the GQR-S4 read authority will enforce
--     (reasoning_strategies.py docstring: strategy verified AND active AND link
--     verified)?
--   * How many of those questions are reachable through mock/generated-mock
--     review (a bank row admitted by the mock-pipeline status gate)?
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
begin
  select count(*) into v_strategies_total from public.reasoning_strategies;
  select count(*) into v_strategies_verified
    from public.reasoning_strategies
    where reviewer_status = 'verified' and is_active = true;

  select count(*) into v_links_total from public.reasoning_question_strategies;
  select count(*) into v_links_verified
    from public.reasoning_question_strategies where reviewer_status = 'verified';

  -- Learner-ready questions: the exact conjunctive gate GQR-S4 will apply —
  -- verified link AND verified+active strategy.
  select count(distinct l.question_id) into v_ready_questions
    from public.reasoning_question_strategies l
    join public.reasoning_strategies s on s.id = l.strategy_id
    where l.reviewer_status = 'verified'
      and s.reviewer_status = 'verified'
      and s.is_active = true;

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
      and q.reviewer_status in ('verified', 'live', 'published');

  raise notice 'reasoning strategies: % verified+active / % total', v_strategies_verified, v_strategies_total;
  raise notice 'reasoning question links: % verified / % total', v_links_verified, v_links_total;
  raise notice 'learner-ready questions (conjunctive gate): %', v_ready_questions;
  raise notice 'of which reachable via mock bank: %', v_ready_reachable;

  if v_ready_reachable = 0 then
    raise notice 'READINESS: NONE — seed/author verified linked Reasoning content before the VERIFY-DB proof.';
  else
    raise notice 'READINESS: PRESENT — % learner-ready reachable question(s).', v_ready_reachable;
  end if;
end $$;

rollback;
