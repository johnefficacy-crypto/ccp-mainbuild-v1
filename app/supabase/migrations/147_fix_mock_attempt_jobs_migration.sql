-- Migration 145 statement 3 fails on instances where
-- mock_attempt_derivation_retry (migration 141) was never applied.
-- Statements 1, 2, and 4 of migration 145 already succeeded on those
-- instances, so this migration completes only the skipped data copy.
DO $migration$
BEGIN
  IF EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name   = 'mock_attempt_derivation_retry'
  ) THEN
    INSERT INTO public.mock_attempt_jobs
      (job_kind, attempt_id, scheduled_for, attempts, last_error, status)
    SELECT
      'analytics_retry',
      r.attempt_id,
      r.next_retry_at,
      coalesce(r.attempts, 0),
      r.last_error,
      'pending'
    FROM public.mock_attempt_derivation_retry r
    WHERE EXISTS (
      SELECT 1 FROM public.mock_attempts a WHERE a.id = r.attempt_id
    )
    ON CONFLICT DO NOTHING;
  END IF;
END
$migration$;
