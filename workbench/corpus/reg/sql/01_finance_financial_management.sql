-- REG-CORPUS: Finance -> "Financial management" topic + 11 microtopics (corporate finance gap).
-- Operator runs live. Idempotent: NOT EXISTS guards (unique index treats NULL parent as distinct, so no ON CONFLICT).
-- Slugs are hardcoded to match workbench/corpus/reg/lists/finance.C.tsv exactly (builder tags depend on them).
BEGIN;

INSERT INTO public.topics (subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT s.id, NULL, 'fin-financial-management-4a7d77e9', 'Financial management', 'topic', true,
       '{"tier":"official","exams":["sebi","pfrda","ifsca"]}'::jsonb
FROM public.subjects s
WHERE s.slug = 'finance'
  AND NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.subject_id = s.id AND t.slug = 'fin-financial-management-4a7d77e9');

INSERT INTO public.topics (subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT p.subject_id, p.id, v.slug, v.name, 'microtopic', true,
       '{"tier":"official","exams":["sebi","pfrda","ifsca"]}'::jsonb
FROM public.topics p
CROSS JOIN (VALUES
  ('fin-cost-of-capital-debt-preference-and-equity-a02970f8', 'Cost of capital — debt, preference and equity'),
  ('fin-weighted-average-and-marginal-cost-of-capital-6b18c6d9', 'Weighted average and marginal cost of capital'),
  ('fin-capm-beta-and-the-security-market-line-3e220793', 'CAPM, beta and the security market line'),
  ('fin-capital-budgeting-payback-and-discounted-payback-608f2476', 'Capital budgeting — payback and discounted payback'),
  ('fin-capital-budgeting-npv-irr-pi-and-mirr-f6de825a', 'Capital budgeting — NPV, IRR, PI and MIRR'),
  ('fin-npv-vs-irr-conflict-and-capital-rationing-70c6c5e7', 'NPV vs IRR conflict and capital rationing'),
  ('fin-capital-budgeting-under-risk-e5bb15ad', 'Capital budgeting under risk'),
  ('fin-leverage-operating-financial-and-combined-713084e6', 'Leverage — operating, financial and combined'),
  ('fin-ebit-eps-analysis-and-financial-indifference-point-22346f43', 'EBIT–EPS analysis and financial indifference point'),
  ('fin-capital-structure-theories-ni-noi-traditional-and-mm-1e092ca9', 'Capital structure theories — NI, NOI, traditional and MM'),
  ('fin-dividend-policy-models-walter-gordon-and-mm-c3d39d63', 'Dividend policy models — Walter, Gordon and MM')
) AS v(slug, name)
WHERE p.slug = 'fin-financial-management-4a7d77e9'
  AND NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.subject_id = p.subject_id AND t.slug = v.slug);

-- verify: expect 1 topic + 11 microtopics, all with exams
SELECT t.level, count(*), count(*) FILTER (WHERE t.metadata ? 'exams') AS with_exams
FROM public.topics t
WHERE t.slug = 'fin-financial-management-4a7d77e9'
   OR t.parent_topic_id = (SELECT id FROM public.topics WHERE slug = 'fin-financial-management-4a7d77e9')
GROUP BY 1;

COMMIT;
