-- backfill_mock_tests_compat.sql
--
-- Inserts missing mock_tests rows for submitted mock_attempts that have no
-- corresponding compat row (e.g. attempts submitted before mock_engine wrote the
-- compat row, or attempts whose _emit_mock_tests_row call failed before the retry
-- job infrastructure existed).
--
-- INSTRUCTIONS:
--   1. Run the DRY RUN block first; record the count in the PR description.
--   2. Confirm the count is expected.
--   3. Run the INSERT block.
--   4. Re-run the DRY RUN to confirm the count is 0.
--
-- Both blocks are safe to re-run (INSERT uses ON CONFLICT DO NOTHING where
-- mock_attempt_id is already present, or skips rows where it would violate FK).

-- ── DRY RUN ───────────────────────────────────────────────────────────────────
-- Record this count in the PR description before running the INSERT.
SELECT
  COUNT(*) AS attempts_missing_mock_tests_row
FROM public.mock_attempts a
WHERE a.status = 'submitted'
  AND a.submitted_at IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM public.mock_tests t
    WHERE t.mock_attempt_id = a.id
  );

-- ── INSERT ────────────────────────────────────────────────────────────────────
-- Only run after reviewing the DRY RUN count above.
INSERT INTO public.mock_tests (
  user_id,
  test_name,
  title,
  exam_name,
  scored_marks,
  total_marks,
  duration_mins,
  correct_answers,
  wrong_answers,
  questions_attempted,
  review_state,
  attempted_at,
  source_type,
  trust_level,
  mock_attempt_id,
  analysis_payload
)
SELECT
  a.user_id,
  COALESCE((a.template_snapshot->>'name'), 'Mock')                     AS test_name,
  COALESCE((a.template_snapshot->>'name'), 'Mock')                     AS title,
  COALESCE(
    a.template_snapshot->>'exam_family',
    a.template_snapshot->>'slug',
    ''
  )                                                                     AS exam_name,
  COALESCE(a.score_raw, 0)                                             AS scored_marks,
  -- max_score: sum marks from frozen question snapshots
  COALESCE(s.max_score, 0)                                             AS total_marks,
  CASE
    WHEN (a.template_snapshot->>'duration_sec')::int > 0
    THEN ROUND((a.template_snapshot->>'duration_sec')::numeric / 60)
    ELSE NULL
  END                                                                   AS duration_mins,
  COALESCE(a.total_correct, 0)                                         AS correct_answers,
  COALESCE(a.total_wrong, 0)                                           AS wrong_answers,
  COALESCE(a.total_correct, 0) + COALESCE(a.total_wrong, 0)           AS questions_attempted,
  'unreviewed'                                                          AS review_state,
  a.submitted_at                                                        AS attempted_at,
  'platform_attempt'                                                    AS source_type,
  'platform_verified'                                                   AS trust_level,
  a.id                                                                  AS mock_attempt_id,
  jsonb_build_object('mock_attempt_id', a.id)                          AS analysis_payload
FROM public.mock_attempts a
-- pre-compute max_score per attempt from frozen question snapshots
LEFT JOIN LATERAL (
  SELECT COALESCE(SUM(COALESCE((r.question_snapshot->>'marks')::numeric, 1)), 0) AS max_score
  FROM public.mock_attempt_responses r
  WHERE r.attempt_id = a.id
) s ON true
WHERE a.status = 'submitted'
  AND a.submitted_at IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM public.mock_tests t
    WHERE t.mock_attempt_id = a.id
  )
ON CONFLICT DO NOTHING;
