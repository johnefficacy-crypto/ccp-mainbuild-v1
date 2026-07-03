-- =============================================================================
-- J3 PR 4 — Evidence-Coverage derivation: exam_topic_coverage source_basis
-- extension + exam-wide unique index.
--
-- Landed after J3 PR 1 (Competition structure, migration 216) and its
-- follow-up fix (#869), ahead of J3 PR 2 (Applied-vs-Appeared), per explicit
-- operator direction overriding the original PR1 -> PR2 -> PR4 sequencing
-- documented in J3-Implementation-Checklist-2026-07-02.md. See
-- docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md for the
-- landing-sequence deviation note and PR #867 for the operator decision.
--
-- Authority: docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md
-- Section F; docs/status/J3-OD-Resolutions-Locked-2026-07-02.md §5.3/§5.5;
-- docs/status/J3-Implementation-Checklist-2026-07-02.md "PR 4" section.
--
-- Contents (one atomic migration per §5.5 -- no benefit to splitting):
--   1. Extend exam_topic_coverage.source_basis CHECK with 'evidence_derived'
--      (OD-1). It is a text CHECK constraint today, not a PG enum.
--   2. Add the exam-wide partial UNIQUE index on
--      (exam_id, topic_id) WHERE exam_cycle_id IS NULL AND exam_phase_id IS NULL
--      (OD-5a / §5.3). Existing indexes only constrain cycle+phase and
--      phase-only scopes; the all-NULL exam-wide scope is unconstrained today.
--   3. A fail-closed DO block that RAISES if any exam-wide (exam_id, topic_id)
--      duplicate already exists. Duplicate resolution is MANUAL/OPERATOR ONLY
--      -- this migration never auto-resolves; see the runbook at the bottom.
--
-- No new table is created by this migration, so no new RLS policy is
-- required (confirmed: nothing in J3 PR 1 changed exam_topic_coverage).
-- =============================================================================
begin;

-- ── 1. Preflight: fail-closed duplicate detection (§5.3) ───────────────────
-- Detect-and-fail only. Never auto-pick a "latest reviewed_at" row — latest
-- is not necessarily correct (e.g. a manual row vs. a stale evidence_derived
-- row). If this block raises, an operator must run the runbook below BEFORE
-- this migration can be re-attempted.
do $$
declare
  dup_count integer;
  dup_report text;
begin
  select count(*) into dup_count
  from (
    select exam_id, topic_id
    from public.exam_topic_coverage
    where exam_cycle_id is null
      and exam_phase_id is null
    group by exam_id, topic_id
    having count(*) > 1
  ) dups;

  if dup_count > 0 then
    select string_agg(
      format(
        '(exam_id=%s, topic_id=%s, row_count=%s)',
        exam_id, topic_id, cnt
      ),
      ', '
    )
    into dup_report
    from (
      select exam_id, topic_id, count(*) as cnt
      from public.exam_topic_coverage
      where exam_cycle_id is null
        and exam_phase_id is null
      group by exam_id, topic_id
      having count(*) > 1
      limit 50
    ) sample;

    raise exception
      'exam_topic_coverage: % exam-wide (exam_id, topic_id) duplicate group(s) found — '
      'cannot add the exam-wide unique index until an operator resolves them manually. '
      'Sample: %. See the operator runbook at the bottom of this migration file '
      '(J3-OD-Resolutions-Locked-2026-07-02.md §5.3).',
      dup_count, dup_report;
  end if;
end $$;

-- ── 2. Extend source_basis CHECK (OD-1) ─────────────────────────────────────
-- source_basis is a text CHECK constraint (migration 030), not a PG enum.
-- Adding a value means dropping and recreating the CHECK — this is additive
-- (widens the allowed set), never a breaking change to existing rows.
alter table public.exam_topic_coverage
  drop constraint if exists exam_topic_coverage_source_basis_check;

alter table public.exam_topic_coverage
  add constraint exam_topic_coverage_source_basis_check
  check (source_basis in (
    'official_syllabus',
    'pyq_analysis',
    'admin_review',
    'hybrid',
    'manual',
    'model_generated',
    'evidence_derived'   -- NEW (OD-1): derivation-owned rows only
  ));

-- ── 3. Exam-wide partial unique index (OD-5a / §5.3) ────────────────────────
-- NULL-safe by construction: the predicate pins BOTH exam_cycle_id and
-- exam_phase_id to IS NULL, so every indexed row shares the same NULL
-- values for those columns and Postgres compares the (exam_id, topic_id)
-- key normally (no NULL-in-index-key ambiguity).
create unique index if not exists exam_topic_coverage_exam_wide_uq
  on public.exam_topic_coverage (exam_id, topic_id)
  where exam_cycle_id is null and exam_phase_id is null;

commit;

-- =============================================================================
-- OPERATOR RUNBOOK — resolving an exam-wide (exam_id, topic_id) duplicate
-- (required only if the fail-closed DO block above raises)
-- =============================================================================
--
-- 1. Preflight report — run this BEFORE touching any row:
--
--      select id, exam_id, topic_id, reviewer_status, source_basis,
--             exam_priority_score, is_high_yield, confidence_score,
--             reviewed_at, metadata
--      from public.exam_topic_coverage
--      where exam_cycle_id is null and exam_phase_id is null
--        and (exam_id, topic_id) in (
--          select exam_id, topic_id
--          from public.exam_topic_coverage
--          where exam_cycle_id is null and exam_phase_id is null
--          group by exam_id, topic_id
--          having count(*) > 1
--        )
--      order by exam_id, topic_id, reviewed_at desc nulls last;
--
-- 2. Operator selects the canonical row per (exam_id, topic_id) group.
--    NEVER auto-keep "latest reviewed_at" — a manual row can be older than
--    a stale evidence_derived duplicate and still be the correct one.
--
-- 3. Merge any legitimate evidence/notes from the non-canonical row(s) into
--    the canonical row (e.g. append to `metadata.merged_from`).
--
-- 4. Audited repair: delete or re-scope the non-canonical duplicate row(s)
--    via the admin CMS surface (so the write goes through `_audit()` and
--    lands in admin_audit_logs), NOT a raw DELETE outside the app.
--
-- 5. Record pre/post row counts and the selected canonical row id(s) as
--    migration evidence (attach to the PR / ops ticket that applies this
--    migration).
--
-- 6. Re-run this migration. The DO block above will pass once no duplicate
--    group remains, and the unique index will apply cleanly.
-- =============================================================================
