-- Plan timeline report (/api/study/reports/plan-timeline) reads a user's
-- mastery audit ordered by `at` within a rolling window. Without an index the
-- query degrades to a per-user scan as history grows; this keeps the p95
-- under target for users with 90 days of plan history.
create index if not exists user_topic_mastery_audit_user_at
  on public.user_topic_mastery_audit (user_id, at desc);
