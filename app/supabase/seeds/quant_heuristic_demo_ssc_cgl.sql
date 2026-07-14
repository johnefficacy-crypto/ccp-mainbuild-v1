-- GQR-S2 — Quant heuristic demo seed (SSC-CGL), idempotent.
--
-- Seeds production-ready VERIFIED + active quant heuristics and verified
-- question↔heuristic links so a demo/staging environment has real reviewed
-- strategy content behind the conjunctive learner-ready gate. Uses existing
-- paths only (service-role INSERT into the migration-243 authority tables) —
-- NO migration, NO new RPC.
--
-- Scopes onto the exam_intelligence_demo_ssc_cgl / pilot_content_ssc_cgl_banking
-- Quant taxonomy (subject 5555…551 'quantitative-aptitude'):
--   * Percentage topic  66666666-…-661
--   * Ratio & Proportion topic  cccccc01-…-001  (pilot seed)
-- Links attach to a demo bank question only WHERE that question already exists,
-- so the seed is safe to run whether or not the pilot question seed is loaded.
--
-- Idempotent: heuristics keyed on unique heuristic_code, links on
-- unique(question_id, heuristic_id). Re-running normalises to verified+active.
--
-- Manual run:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f app/supabase/seeds/quant_heuristic_demo_ssc_cgl.sql

begin;

-- ── Verified heuristics (Percentage + Ratio) ────────────────────────────────
insert into public.quant_heuristics
  (id, topic_id, heuristic_code, name, heuristic_type, applicability_rule,
   formula_latex, standard_method, shortcut_method, worked_example, common_traps,
   reviewer_status, is_active, reviewed_at)
values
  ('a0000000-0000-0000-0000-0000000d5201'::uuid,
   '66666666-6666-6666-6666-666666666661'::uuid,
   'QH-SSC-SUCCESSIVE-PCT', 'Successive percentage change', 'shortcut',
   '{"pattern": "successive_percentage"}'::jsonb,
   'a + b + \frac{ab}{100}',
   'Apply each percentage change in turn to the running value.',
   'net% = a + b + a*b/100 with signs; +20% then -20% → -4%.',
   'A price rises 20% then falls 20%: net = 20 - 20 - 400/100 = -4% (a fall).',
   'Adding the two percentages to zero and forgetting the ab/100 term.',
   'verified', true, now()),
  ('a0000000-0000-0000-0000-0000000d5202'::uuid,
   'cccccc01-0000-0000-0000-000000000001'::uuid,
   'QH-SSC-RATIO-UNITARY', 'Ratio via a single unit value', 'shortcut',
   '{"pattern": "ratio_total_to_parts"}'::jsonb,
   '\text{part} = \frac{\text{share}}{\text{sum of parts}} \times \text{total}',
   'Divide the total by the sum of ratio parts to get one unit, then scale.',
   'unit = total / (sum of parts); each share = unit × its part.',
   'Split 6000 in 2:3:1 → sum 6 → unit 1000 → 2000, 3000, 1000.',
   'Summing the parts wrong, or scaling before finding the unit value.',
   'verified', true, now())
on conflict (heuristic_code) do update
  set reviewer_status = 'verified', is_active = true, reviewed_at = now(),
      topic_id = excluded.topic_id, name = excluded.name;

-- ── Verified link to a demo Percentage bank question (guarded on existence) ──
insert into public.quant_question_heuristics
  (id, question_id, heuristic_id, relevance, reviewer_status, reviewed_at)
select '11110000-0000-0000-0000-0000000d5201'::uuid,
       'b1000001-0000-0000-0000-000000000001'::uuid,
       'a0000000-0000-0000-0000-0000000d5201'::uuid,
       'primary', 'verified', now()
where exists (
  select 1 from public.mock_question_bank
  where id = 'b1000001-0000-0000-0000-000000000001'::uuid
)
on conflict (question_id, heuristic_id) do update
  set reviewer_status = 'verified', reviewed_at = now();

commit;
