-- =============================================================================
-- 158_fix_mock_question_provenance_enum.sql
-- Repair migration for 156_mock_question_provenance.sql.
--
-- 156 assumed mock_reviewer_status already existed (created by
-- 135_mock_engine_core.sql).  In environments where 135 did not run, or
-- where the enum was not yet committed to the search-path schema, 156 aborts
-- at statement 0 and leaves mock_question_bank unchanged.
--
-- This migration is fully idempotent and safe to apply whether 156 succeeded,
-- partially failed, or was never run.
-- =============================================================================

-- ── 1. Ensure the enum exists with all five lifecycle values ───────────────────
do $$ begin
  create type public.mock_reviewer_status as enum
    ('draft', 'reviewed', 'locked', 'verified', 'live');
exception when duplicate_object then null; end $$;

-- Add values that may be absent if the enum was created by migration 135
-- with only (draft, reviewed, locked).
do $$ begin
  alter type public.mock_reviewer_status add value if not exists 'verified';
exception when others then null; end $$;

do $$ begin
  alter type public.mock_reviewer_status add value if not exists 'live';
exception when others then null; end $$;

-- ── 2. Ensure provenance columns exist (idempotent) ───────────────────────────
alter table public.mock_question_bank
  add column if not exists is_conceptual      boolean not null default false,
  add column if not exists is_factual         boolean not null default false,
  add column if not exists is_current_based   boolean not null default false,
  add column if not exists source_url         text,
  add column if not exists common_trap        text;

alter table public.mock_question_bank
  add column if not exists event_anchor_date       date,
  add column if not exists valid_from              date,
  add column if not exists valid_until             date,
  add column if not exists current_affairs_item_id uuid;

-- ── 3. Ensure index exists ─────────────────────────────────────────────────────
create index if not exists idx_mqb_reviewer_status
  on public.mock_question_bank(reviewer_status);

-- ── 4. Enforce RLS gate ────────────────────────────────────────────────────────
drop policy if exists "mock_question_bank_read_reviewed" on public.mock_question_bank;

create policy "mock_question_bank_read_reviewed"
  on public.mock_question_bank for select
  using (reviewer_status in ('verified', 'live'));

notify pgrst, 'reload schema';
