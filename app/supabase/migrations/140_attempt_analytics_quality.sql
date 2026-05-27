-- 140_attempt_analytics_quality.sql
-- Follow-up to 137_attempt_analytics.sql (PR4a-owned analytics base tables):
-- adds operational quality metadata without altering scoring semantics.
alter table if exists public.mock_attempt_summary
  add column if not exists analytics_quality jsonb not null default '{}'::jsonb;
