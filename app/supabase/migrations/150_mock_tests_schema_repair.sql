-- 150: Mock tests schema repair — supersedes broken migration 148.
--
-- Migration 148 was marked applied in the tracker but never executed because its
-- UPDATE backfill referenced the non-existent `metadata` column. This migration
-- does the actual work, referencing `analysis_payload` (the column that exists).
--
-- Safe to run on instances where 148 partially applied (ADD COLUMN only) because
-- every DDL step uses IF NOT EXISTS / IF EXISTS guards.

-- ── 1. mock_tests columns ─────────────────────────────────────────────────────
ALTER TABLE public.mock_tests
  ADD COLUMN IF NOT EXISTS source_type text NOT NULL DEFAULT 'manual_log'
    CHECK (source_type IN ('manual_log', 'platform_attempt', 'imported_result')),
  ADD COLUMN IF NOT EXISTS trust_level text NOT NULL DEFAULT 'self_reported'
    CHECK (trust_level IN ('self_reported', 'platform_verified', 'admin_verified')),
  ADD COLUMN IF NOT EXISTS mock_attempt_id uuid REFERENCES public.mock_attempts(id);

CREATE INDEX IF NOT EXISTS mock_tests_source_attempt
  ON public.mock_tests(mock_attempt_id)
  WHERE mock_attempt_id IS NOT NULL;

-- ── 2. backfill from analysis_payload (the column that actually exists) ───────
-- Rows written by mock_engine._emit_mock_tests_row carry analysis_payload with
-- a 'mock_attempt_id' key. migration 148 incorrectly read from `metadata` instead.
UPDATE public.mock_tests
SET source_type     = 'platform_attempt',
    trust_level     = 'platform_verified',
    mock_attempt_id = (analysis_payload->>'mock_attempt_id')::uuid
WHERE analysis_payload ? 'mock_attempt_id'
  AND mock_attempt_id IS NULL
  AND (analysis_payload->>'mock_attempt_id') ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- ── 3. mock_mastery_shadow columns (also blocked by 148 failure) ──────────────
ALTER TABLE public.mock_mastery_shadow
  ADD COLUMN IF NOT EXISTS trust_level text NOT NULL DEFAULT 'platform_verified',
  ADD COLUMN IF NOT EXISTS proposed_delta_db_unweighted numeric(5,2);

-- ── 4. extend mock_attempt_jobs to allow mock_tests_retry jobs ────────────────
-- The check constraint name is auto-generated; use the catalog for a robust lookup
-- rather than hard-coding the name.
DO $$
DECLARE
  v_conname text;
BEGIN
  SELECT c.conname INTO v_conname
  FROM pg_constraint c
  JOIN pg_class r ON r.oid = c.conrelid
  JOIN pg_namespace n ON n.oid = r.relnamespace
  WHERE n.nspname = 'public'
    AND r.relname = 'mock_attempt_jobs'
    AND c.contype = 'c'
    AND c.conname LIKE '%job_kind%';

  IF v_conname IS NOT NULL THEN
    EXECUTE format('ALTER TABLE public.mock_attempt_jobs DROP CONSTRAINT %I', v_conname);
  END IF;

  ALTER TABLE public.mock_attempt_jobs
    ADD CONSTRAINT mock_attempt_jobs_job_kind_check
    CHECK (job_kind IN ('auto_submit', 'analytics_retry', 'mastery_retry', 'mock_tests_retry'));
END;
$$;

-- ── 5. notify PostgREST to reload schema cache ────────────────────────────────
NOTIFY pgrst, 'reload schema';
