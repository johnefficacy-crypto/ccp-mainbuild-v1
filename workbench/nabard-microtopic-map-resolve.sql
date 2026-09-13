-- Resolve the question_id column of workbench/nabard-microtopic-map.csv.
--
-- The map is keyed on (paper_code, source_question_ref) because nabard_blocks.json
-- has no question ids -- those were assigned by Postgres at load time. Both columns
-- are load identity: paper_code is unique across all 49 blocks, and
-- (pyq_paper_id, source_question_ref) is unique per paper.
--
-- Load the CSV into a staging table, then:

SELECT s.source_question_ref,
       s.paper_code,
       s.microtopic_slug,
       q.id AS question_id
  FROM nabard_microtopic_map_stage s
  JOIN public.pyq_papers    p ON p.paper_code = s.paper_code
  JOIN public.pyq_questions q ON q.pyq_paper_id = p.id
                             AND q.source_question_ref = s.source_question_ref;

-- Expect exactly 694 rows. Any shortfall is a load gap, not a mapping gap --
-- reconcile before tagging. Verify the microtopics resolve too:

SELECT s.microtopic_slug
  FROM nabard_microtopic_map_stage s
  LEFT JOIN public.topics t ON t.slug = s.microtopic_slug AND t.level = 'microtopic'
 WHERE t.id IS NULL;
-- Expect zero rows once migration 275 has been applied.
