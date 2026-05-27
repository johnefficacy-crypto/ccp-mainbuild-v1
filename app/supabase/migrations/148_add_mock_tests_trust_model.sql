-- SUPERSEDED: This migration was broken (referenced non-existent `metadata` column).
-- It is marked applied in the tracker but was never executed.
-- See migration 150 for the actual schema change.
-- DO NOT attempt to re-run this migration.

-- 148: Mock trust model — platform-verified vs self-reported
--
-- Option B (trust-aware coexistence): both manual logs and platform attempts
-- continue to exist in mock_tests, distinguished by source_type / trust_level.
-- See docs/architecture/mock_trust_model.md.

alter table public.mock_tests
  add column if not exists source_type text not null default 'manual_log'
    check (source_type in ('manual_log', 'platform_attempt', 'imported_result')),
  add column if not exists trust_level text not null default 'self_reported'
    check (trust_level in ('self_reported', 'platform_verified', 'admin_verified')),
  add column if not exists mock_attempt_id uuid references public.mock_attempts(id);

create index if not exists mock_tests_source_attempt on public.mock_tests(mock_attempt_id)
  where mock_attempt_id is not null;

-- Backfill: rows that carry metadata->>'mock_attempt_id' are platform attempts
-- written by mock_engine._emit_mock_tests_row (see migration 135 + mock_engine.py).
update public.mock_tests
set source_type    = 'platform_attempt',
    trust_level    = 'platform_verified',
    mock_attempt_id = (metadata->>'mock_attempt_id')::uuid
where metadata ? 'mock_attempt_id'
  and (metadata->>'mock_attempt_id') is not null
  and (metadata->>'mock_attempt_id') <> ''
  and (metadata->>'mock_attempt_id') ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Extend shadow table to carry trust metadata for weighted-vs-unweighted reporting.
-- proposed_delta_db already holds the trust-weighted delta written by the writer;
-- proposed_delta_db_unweighted preserves the pre-weight value for analysis.
alter table public.mock_mastery_shadow
  add column if not exists trust_level text not null default 'platform_verified',
  add column if not exists proposed_delta_db_unweighted numeric(5,2);
