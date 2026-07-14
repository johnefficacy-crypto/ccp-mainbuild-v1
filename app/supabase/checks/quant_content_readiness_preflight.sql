-- GQR-S2 — Quant content-readiness preflight (read-only counts).
--
-- Answers the GQR-S2 preflight questions before any authoring/seed work:
--   * How many verified + active quant heuristics exist?
--   * How many verified question↔heuristic links exist?
--   * How many DISTINCT bank questions have a fully-verified heuristic surface
--     (link verified AND heuristic verified AND active) — i.e. are learner-ready
--     under the conjunctive gate the read authority enforces?
--   * How many of those questions are reachable through mock/generated-mock
--     review (a bank row admitted by the mock-pipeline status gate)?
--
-- Read-only: emits NOTICEs, mutates nothing. If every count is zero the lane has
-- no production-ready verified linked content and GQR-S2 must seed/author some
-- before the VERIFY-DB proof can pass.
--
-- Manual run:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f app/supabase/checks/quant_content_readiness_preflight.sql

begin read only;

do $$
declare
  v_heuristics_verified   int;
  v_heuristics_total      int;
  v_links_verified        int;
  v_links_total           int;
  v_ready_questions       int;
  v_ready_reachable       int;
begin
  select count(*) into v_heuristics_total from public.quant_heuristics;
  select count(*) into v_heuristics_verified
    from public.quant_heuristics
    where reviewer_status = 'verified' and is_active = true;

  select count(*) into v_links_total from public.quant_question_heuristics;
  select count(*) into v_links_verified
    from public.quant_question_heuristics where reviewer_status = 'verified';

  -- Learner-ready questions: the exact conjunctive gate heuristics_for_question()
  -- applies — verified link AND verified+active heuristic.
  select count(distinct l.question_id) into v_ready_questions
    from public.quant_question_heuristics l
    join public.quant_heuristics h on h.id = l.heuristic_id
    where l.reviewer_status = 'verified'
      and h.reviewer_status = 'verified'
      and h.is_active = true;

  -- Of those, reachable through mock/generated-mock review. The selector/RLS
  -- gate admits only verified/live/published bank rows; mere existence is not
  -- sufficient (reviewed/draft/archived rows are not learner-reachable).
  select count(distinct l.question_id) into v_ready_reachable
    from public.quant_question_heuristics l
    join public.quant_heuristics h on h.id = l.heuristic_id
    join public.mock_question_bank q on q.id = l.question_id
    where l.reviewer_status = 'verified'
      and h.reviewer_status = 'verified'
      and h.is_active = true
      and q.reviewer_status in ('verified', 'live', 'published');

  raise notice 'quant heuristics: % verified+active / % total', v_heuristics_verified, v_heuristics_total;
  raise notice 'quant question links: % verified / % total', v_links_verified, v_links_total;
  raise notice 'learner-ready questions (conjunctive gate): %', v_ready_questions;
  raise notice 'of which reachable via mock bank: %', v_ready_reachable;

  if v_ready_reachable = 0 then
    raise notice 'READINESS: NONE — seed/author verified linked Quant content before the VERIFY-DB proof.';
  else
    raise notice 'READINESS: PRESENT — % learner-ready reachable question(s).', v_ready_reachable;
  end if;
end $$;

rollback;
