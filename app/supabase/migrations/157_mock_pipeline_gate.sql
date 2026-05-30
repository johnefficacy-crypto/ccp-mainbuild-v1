-- =============================================================================
-- 157_mock_pipeline_gate.sql
-- Controlled Mock Pipeline — reviewer_status gate
--
-- Adds 'reviewed' and 'live' to the reviewer_status check constraint so the
-- simplified pipeline (draft → reviewed → verified) introduced in
-- 156_mock_question_provenance can write valid rows.
--
-- Also adds source_kind column to mock_question_bank for in-row provenance
-- (supplements the existing mock_question_sources join table — both coexist).
--
-- RLS policy (recreated): end-user PostgREST reads gate on
--   reviewer_status IN ('verified', 'live', 'published')
-- Service-role (FastAPI) bypasses RLS; the application enforces the same gate
-- in the template selector before building a question_snapshot.
-- =============================================================================

-- ── 1. Extend reviewer_status check constraint ────────────────────────────────

alter table public.mock_question_bank
  drop constraint if exists mock_question_bank_reviewer_status_check;

alter table public.mock_question_bank
  add constraint mock_question_bank_reviewer_status_check
  check (
    reviewer_status in (
      'draft',
      'reviewed',
      'in_review',
      'needs_changes',
      'verified',
      'published',
      'live',
      'archived'
    )
  );

-- ── 2. source_kind on mock_question_bank (in-row fast filter) ─────────────────

alter table public.mock_question_bank
  add column if not exists source_kind text
    check (source_kind in (
      'pyq', 'official_syllabus', 'standard_source',
      'current_event', 'authored', 'archive', 'sme'
    ));

-- ── 3. RLS: end-users see verified / live / published rows only ───────────────
-- Drop any previous variant of this policy so we get the updated predicate.
drop policy if exists "mock_question_bank_read_reviewed" on public.mock_question_bank;
drop policy if exists "mock_question_bank_read_published" on public.mock_question_bank;

create policy "mock_question_bank_read_verified"
  on public.mock_question_bank for select
  using (reviewer_status in ('verified', 'live', 'published'));

notify pgrst, 'reload schema';
