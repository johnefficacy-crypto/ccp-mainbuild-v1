-- REG-CORPUS-03: make the authored regulatory corpus VISIBLE to SEBI / PFRDA / IFSCA learners.
-- Operator runs live, AFTER 01_finance_financial_management.sql and 02_financial_sector_acts.sql
-- and migrations 309/310. Written, not executed, by the PR that adds it. Idempotent (NOT EXISTS).
--
-- Why: topics.metadata.exams only makes authored rows ELIGIBLE. The Subject Hub, topic tree,
-- planner and subject-practice launch list only topics with a LOCKED exam_topic_coverage row
-- for the exam (study_os/subjects.py locked_topic_ids_for_subject -> planner.load_scoped_coverage).
-- Coverage derive never creates these rows (authored questions are not evidence for it), so
-- they are written here, in the shape REG-CORPUS-02 (#1216) documents:
--   exam_cycle_id NULL, exam_phase_id NULL (exam-wide), section_id NULL, reviewer_status 'locked'.
-- Exam-wide rows are covered by exam_topic_coverage_exam_wide_uq (migration 217).
--
-- Rows: {sebi-grade-a, pfrda-grade-a, ifsca-grade-a}
--   x (every topic AND microtopic of subject financial-sector-acts: 21 + 105)
--   + (Finance > "Financial management" fin-financial-management-4a7d77e9 and its 11 microtopics)
-- = 3 x 138 = 414 rows when nothing exists yet. A pair is written only when the topic's
-- metadata.exams carries the exam's key (sebi|pfrda|ifsca), the same predicate the authored
-- pool uses, so no exam gets a coverage row for a topic whose questions it cannot see.
-- A pair that already has ANY coverage row (any phase, any status) is left alone: this script
-- never overrides a reviewer's rejected or phase-scoped row. The verify SELECT lists such pairs.
--
-- Priority/depth: coverage_depth 'normal', exam_priority_score 0, confidence_score 0 (defaults).
-- These topics have no PYQ evidence to rank them; a reviewer may re-score them in the CMS.

BEGIN;

-- Preconditions: fail loudly instead of silently inserting nothing.
DO $$
DECLARE
  n_exams int;
  n_fsa int;
  n_fm int;
BEGIN
  SELECT count(*) INTO n_exams FROM public.exams
  WHERE slug IN ('sebi-grade-a', 'pfrda-grade-a', 'ifsca-grade-a');
  IF n_exams <> 3 THEN
    RAISE EXCEPTION 'REG-CORPUS-03: expected 3 regulator exams, found %', n_exams;
  END IF;

  SELECT count(*) INTO n_fsa
  FROM public.topics t JOIN public.subjects s ON s.id = t.subject_id
  WHERE s.slug = 'financial-sector-acts';
  IF n_fsa <> 126 THEN
    RAISE EXCEPTION 'REG-CORPUS-03: expected 126 financial-sector-acts topics (21 + 105), found % — run 02_financial_sector_acts.sql first', n_fsa;
  END IF;

  SELECT count(*) INTO n_fm
  FROM public.topics t
  WHERE t.slug = 'fin-financial-management-4a7d77e9'
     OR t.parent_topic_id = (SELECT id FROM public.topics WHERE slug = 'fin-financial-management-4a7d77e9');
  IF n_fm <> 12 THEN
    RAISE EXCEPTION 'REG-CORPUS-03: expected Financial management + 11 microtopics (12), found % — run 01_finance_financial_management.sql first', n_fm;
  END IF;
END $$;

WITH target_topics AS (
  SELECT t.id, t.metadata
  FROM public.topics t
  JOIN public.subjects s ON s.id = t.subject_id
  WHERE s.slug = 'financial-sector-acts'
  UNION
  SELECT t.id, t.metadata
  FROM public.topics t
  WHERE t.slug = 'fin-financial-management-4a7d77e9'
     OR t.parent_topic_id = (SELECT id FROM public.topics WHERE slug = 'fin-financial-management-4a7d77e9')
)
INSERT INTO public.exam_topic_coverage
  (exam_id, exam_cycle_id, exam_phase_id, section_id, topic_id,
   coverage_depth, source_basis, reviewer_status, reviewed_at, review_notes, metadata)
SELECT e.id, NULL, NULL, NULL, tt.id,
       'normal', 'admin_review', 'locked', now(),
       'REG-CORPUS-03: authored regulatory corpus scope (topics.metadata.exams)',
       '{"source":"REG-CORPUS-03","basis":"authored_corpus"}'::jsonb
FROM public.exams e
CROSS JOIN target_topics tt
WHERE e.slug IN ('sebi-grade-a', 'pfrda-grade-a', 'ifsca-grade-a')
  AND tt.metadata -> 'exams' ? split_part(e.slug, '-', 1)
  AND NOT EXISTS (
    SELECT 1 FROM public.exam_topic_coverage c
    WHERE c.exam_id = e.id AND c.topic_id = tt.id
  );

-- verify 1: expect locked = 126 (acts) and 12 (fin-mgmt) for each of the three exams.
SELECT e.slug AS exam,
       CASE WHEN s.slug = 'financial-sector-acts' THEN 'acts' ELSE 'fin-mgmt' END AS scope,
       count(*) FILTER (WHERE c.reviewer_status = 'locked')  AS locked,
       count(*) FILTER (WHERE c.reviewer_status <> 'locked') AS not_locked
FROM public.exam_topic_coverage c
JOIN public.exams e    ON e.id = c.exam_id
JOIN public.topics t   ON t.id = c.topic_id
JOIN public.subjects s ON s.id = t.subject_id
WHERE e.slug IN ('sebi-grade-a', 'pfrda-grade-a', 'ifsca-grade-a')
  AND (s.slug = 'financial-sector-acts'
       OR t.slug = 'fin-financial-management-4a7d77e9'
       OR t.parent_topic_id = (SELECT id FROM public.topics WHERE slug = 'fin-financial-management-4a7d77e9'))
GROUP BY 1, 2
ORDER BY 1, 2;

-- verify 2: pairs that are still NOT visible (no locked row). Expect 0 rows; any row here is a
-- pre-existing coverage row this script deliberately did not touch — resolve it in the CMS.
SELECT e.slug AS exam, t.slug AS topic, t.level,
       (SELECT string_agg(c.reviewer_status || coalesce('@phase:' || c.exam_phase_id::text, ''), ', ')
        FROM public.exam_topic_coverage c
        WHERE c.exam_id = e.id AND c.topic_id = t.id) AS existing
FROM public.exams e
CROSS JOIN public.topics t
LEFT JOIN public.subjects s ON s.id = t.subject_id
WHERE e.slug IN ('sebi-grade-a', 'pfrda-grade-a', 'ifsca-grade-a')
  AND (s.slug = 'financial-sector-acts'
       OR t.slug = 'fin-financial-management-4a7d77e9'
       OR t.parent_topic_id = (SELECT id FROM public.topics WHERE slug = 'fin-financial-management-4a7d77e9'))
  AND t.metadata -> 'exams' ? split_part(e.slug, '-', 1)
  AND NOT EXISTS (
    SELECT 1 FROM public.exam_topic_coverage c
    WHERE c.exam_id = e.id AND c.topic_id = t.id AND c.reviewer_status = 'locked'
  )
ORDER BY 1, 2;

COMMIT;


-- ════════════════════════════════════════════════════════════════════════════════════════
-- OPERATOR DECISION — NOT RUN. exam_phase_sections for GENERATED MOCKS.
--
-- Needed? YES for the Acts, NO for Financial management:
--   * Generated mocks take pool rows per section by exam_phase_sections.subject_id
--     (study_os/mock_blueprint_selection.py: `eligible = [r for r in base_pool
--     if r.get("subject_id") == subject_id]`). financial-sector-acts is a NEW subject, so no
--     existing section carries it and Acts questions can never enter a generated mock, however
--     much coverage they have. Topic practice, subject practice, the Subject Hub and the
--     planner do NOT need sections — the coverage rows above are enough for those.
--   * Financial management sits under the existing `finance` subject; its authored rows enter
--     a generated mock wherever that exam already has a finance section. Nothing to add.
--
-- Which phase examines the Acts, the section label and its question count are product decisions
-- (adding a section changes the mock's length and marks). Fill the three phase ids and uncomment.
-- Unique key: (exam_phase_id, stream_id, subject_id, section_label), NULLS NOT DISTINCT (mig 242).
--
-- BEGIN;
-- INSERT INTO public.exam_phase_sections
--   (exam_phase_id, subject_id, section_label, question_count, sort_order, metadata)
-- SELECT v.exam_phase_id::uuid, s.id, 'Financial Sector Acts', v.question_count, v.sort_order,
--        '{"source":"REG-CORPUS-03"}'::jsonb
-- FROM (VALUES
--   ('<SEBI_PHASE_ID>',  20, 90),   -- e.g. SEBI Grade A Phase II Paper 2
--   ('<PFRDA_PHASE_ID>', 20, 90),
--   ('<IFSCA_PHASE_ID>', 20, 90)
-- ) AS v(exam_phase_id, question_count, sort_order)
-- JOIN public.subjects s ON s.slug = 'financial-sector-acts'
-- WHERE NOT EXISTS (
--   SELECT 1 FROM public.exam_phase_sections x
--   WHERE x.exam_phase_id = v.exam_phase_id::uuid AND x.subject_id = s.id
-- );
--
-- -- verify: one Acts section per chosen phase, with the right exam
-- SELECT e.slug, p.id AS phase_id, x.section_label, x.question_count
-- FROM public.exam_phase_sections x
-- JOIN public.exam_phases p ON p.id = x.exam_phase_id
-- JOIN public.exams e ON e.id = p.exam_id
-- JOIN public.subjects s ON s.id = x.subject_id
-- WHERE s.slug = 'financial-sector-acts';
-- COMMIT;
