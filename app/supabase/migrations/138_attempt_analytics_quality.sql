-- 138_attempt_analytics_quality.sql
alter table if exists public.mock_attempt_summary
  add column if not exists analytics_quality jsonb not null default '{}'::jsonb;
