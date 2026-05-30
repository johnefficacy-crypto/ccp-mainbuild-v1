-- =============================================================================
-- 156_mock_question_provenance.sql
-- Mock Question Provenance + Review Gate
--
-- Adds provenance metadata and a 5-state reviewer lifecycle to
-- mock_question_bank.  Only rows with reviewer_status = 'verified' (or 'live')
-- are exposed via RLS to end-users, enforcing the rule:
--   "arbitrary upload never becomes live."
--
-- Columns that already existed in 135_mock_engine_core.sql (SKIPPED):
--   source_type, reviewer_status, expected_time_sec
--
-- Enum additions: 'verified' and 'live' appended to mock_reviewer_status.
--   Full lifecycle: draft → reviewed → verified → live  (reject → draft)
--
-- current_affairs_item_id is stored as a plain uuid (no FK) because the
-- current_affairs_items table does not yet exist.  When that table is created,
-- a forward migration should add the FK constraint.
--
-- DB-level live-mock guard: the RLS policy
--   mock_question_bank_read_reviewed  (recreated below)
-- restricts all PostgREST / client reads to reviewer_status IN ('verified','live').
-- Service-role (FastAPI) bypasses RLS for admin writes; it must enforce the
-- same gate in application logic before building a template snapshot.
-- =============================================================================

-- ── 1. Extend the reviewer-status enum ────────────────────────────────────────
-- ALTER TYPE … ADD VALUE is transactional in Postgres 12+; wrap in DO blocks
-- to stay idempotent (duplicate_object is not raised, but we guard anyway).
do $$ begin
  alter type public.mock_reviewer_status add value if not exists 'verified';
exception when duplicate_object then null; end $$;

do $$ begin
  alter type public.mock_reviewer_status add value if not exists 'live';
exception when duplicate_object then null; end $$;

-- ── 2. Add provenance + classification columns ─────────────────────────────────

alter table public.mock_question_bank
  add column if not exists is_conceptual      boolean not null default false,
  add column if not exists is_factual         boolean not null default false,
  add column if not exists is_current_based   boolean not null default false,
  add column if not exists source_url         text,
  add column if not exists common_trap        text;

-- ── 3. Current-affairs temporal columns ───────────────────────────────────────

alter table public.mock_question_bank
  add column if not exists event_anchor_date       date,
  add column if not exists valid_from              date,
  add column if not exists valid_until             date,
  -- No FK until current_affairs_items table exists; see header note.
  add column if not exists current_affairs_item_id uuid;

comment on column public.mock_question_bank.current_affairs_item_id is
  'Soft-link to current_affairs_items(id). FK to be added in a later migration once that table is created.';

comment on column public.mock_question_bank.valid_from is
  'Earliest date this question is considered accurate (current-affairs questions only).';

comment on column public.mock_question_bank.valid_until is
  'Latest date this question is considered accurate; NULL means no expiry.';

-- ── 4. Index on reviewer_status for fast template-selector queries ─────────────
create index if not exists idx_mqb_reviewer_status
  on public.mock_question_bank(reviewer_status);

-- ── 5. Recreate RLS gate: only verified/live rows reach clients ────────────────
-- Drop and recreate so the predicate is correct regardless of the previous
-- migration's definition.
drop policy if exists "mock_question_bank_read_reviewed" on public.mock_question_bank;

create policy "mock_question_bank_read_reviewed"
  on public.mock_question_bank for select
  using (reviewer_status in ('verified', 'live'));

-- Document the guard as a table comment for discoverability.
comment on table public.mock_question_bank is
  'Mock exam question registry.  Live-mock gate: only rows with '
  'reviewer_status IN (''verified'', ''live'') are readable by '
  'authenticated clients (RLS policy mock_question_bank_read_reviewed).  '
  'Admin writes via service_role must also enforce this gate before '
  'including a question_id in a template snapshot.';

notify pgrst, 'reload schema';
