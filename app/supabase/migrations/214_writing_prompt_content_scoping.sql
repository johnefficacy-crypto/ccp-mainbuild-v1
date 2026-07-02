-- ============================================================================
-- 214_writing_prompt_content_scoping.sql
--
-- English Writing Practice — content-scoping architecture revision.
-- Encodes the three-scope model that separates canonical content from
-- exam applicability and from official exam requirements:
--
--   1. CONTENT (canonical) = SUBJECT-scoped.
--      A writing prompt's canonical identity is subject_id / topic_id /
--      microtopic_id. It is reusable across many exams — it does NOT belong
--      to a single exam. The dual-authority exam-scope columns on
--      `writing_prompts` (`exam_id`, `exam_cycle_id`, `exam_phase_id`) are
--      therefore DROPPED (see §2 below): applicability is now carried SOLELY
--      by `writing_prompt_targets`. There is no longer any exam-scope column
--      on `writing_prompts` that could contradict a target row.
--
--   2. APPLICABILITY = exam / family / phase-scoped, via the NEW mapping
--      table `public.writing_prompt_targets`. One prompt may apply to many
--      exams / families / phases with no content duplication. Precedence
--      when resolving which prompts apply to an exam+phase context:
--
--        phase-specific  >  exam-specific  >  exam-family  >  globally-applicable
--
--      Global-with-exclusions semantics (BASELINE + OVERRIDES — the single,
--      precise rule; supersedes any "no rows = global" vs "excluded rows
--      exist" ambiguity):
--        * A prompt is GLOBALLY applicable as its baseline when it has no
--          `applicability_status='active'` target row that RESTRICTS it to a
--          narrower scope (i.e. no active family/exam/phase target). "No target
--          rows at all" is the trivial case of this baseline.
--        * An `applicability_status='excluded'` row for exam/family/phase X is
--          an OVERRIDE that removes the prompt from X only, while leaving the
--          global baseline intact everywhere else. Thus a globally-applicable
--          prompt can still carry `excluded` rows without contradiction: the
--          excluded rows subtract specific scopes from an otherwise-global set.
--        * The resolver applies overrides within their precedence band: a more
--          specific `excluded` (phase) beats a broader `active` (exam/family),
--          and vice-versa, per the phase>exam>family>global ordering.
--
--      NOTE: applicability is deliberately EVERGREEN — it carries no
--      `exam_cycle_id`. Canonical content survives cycles; a cycle-specific
--      rule belongs in `exam_descriptive_requirements`, not here.
--
--   3. REQUIREMENTS = exam / cycle / phase-scoped, UNCHANGED. Word limits,
--      marks, duration, format rules, sections, and feedback policy continue
--      to live in `public.exam_descriptive_requirements` (migration 205 §4.2).
--      This migration does NOT touch that table.
--
-- Ownership: canonical prompts are authored and governed in the shared
-- **Content Studio** admin surface, NOT in the exam-scoped Exam Workspace.
-- See docs/architecture/content-studio.md and the revised §17 of
-- docs/architecture/english-writing-practice.md.
--
-- ----------------------------------------------------------------------------
-- MIGRATION NUMBER + OPERATOR APPLY ORDER (concrete — no reconcile-rename).
--   * Filesystem max migration on `main` is 213
--     (`213_english_writing_practice_error_lab_read_model.sql`), so 214 is the
--     only contiguous slot. The CI `validate` guard enforces this filesystem
--     contiguity; the filename is CORRECT and MUST NOT be renamed.
--   * The LIVE `schema_migrations` max is 212 — merged migration 213 (Error Lab
--     read model) has NOT been applied to the live DB yet. Therefore the
--     OPERATOR must apply in order:
--         1) apply pending 213 (Error Lab read model)   — OPERATOR PENDING
--         2) then apply 214 (this migration)            — OPERATOR PENDING
--     Do NOT apply 214 before 213. No renumber/rename is required or permitted.
--
-- ----------------------------------------------------------------------------
-- RLS posture (CLAUDE.md: every new table needs an RLS policy):
--   `writing_prompt_targets` is operator/service-managed applicability data.
--   The backend applicability resolver runs under the SERVICE ROLE, so this
--   table is treated like the §12.2 service-role-only tables of migration 205:
--   RLS is ENABLED with NO anon/authenticated allow policy (a deliberate
--   zero-client-policy posture — the resolver reads via service_role, which
--   bypasses RLS). Writes are service-role only. This keeps applicability an
--   implementation detail of verified-only reads: aspirant surfaces never read
--   raw target rows; they receive the resolver's already-filtered result.
--   Verification (OPERATOR / VERIFY DB):
--     SELECT * FROM pg_policies WHERE tablename = 'writing_prompt_targets';
--   must show RLS enabled and NO authenticated/anon policy.
--
-- IDEMPOTENCY: this migration is safe to re-apply. The backfill uses
-- `ON CONFLICT DO NOTHING` against the null-safe unique identity; the column
-- drops are `IF EXISTS`; the index drops/creates are `IF EXISTS`/`IF NOT
-- EXISTS`. No AI writes. Writes are limited to the one-time legacy backfill.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Applicability mapping table (exam / family / phase-scoped).
--    Created BEFORE the backfill (§1b) and BEFORE the column drops (§2), so the
--    legacy exam scope on writing_prompts can be captured as target rows first.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_prompt_targets (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id            uuid NOT NULL
                         REFERENCES public.writing_prompts(id) ON DELETE CASCADE,
  -- EXACTLY ONE scope must be set (enforced by the CHECK below). A single
  -- target row names a single scope kind (family OR exam OR phase); a prompt
  -- that applies to several scopes gets several rows. This makes the
  -- (prompt_id, scope) identity deterministic and lets the null-safe unique
  -- index below reject duplicates.
  exam_family_id       uuid REFERENCES public.exam_families(id),
  exam_id              uuid REFERENCES public.exams(id) ON DELETE CASCADE,
  exam_phase_id        uuid REFERENCES public.exam_phases(id),
  applicability_status text NOT NULL DEFAULT 'active'
                         CHECK (applicability_status IN ('active','excluded','pending_review')),
  -- Optional operator-set tiebreak. Because (prompt_id, scope) is UNIQUE, a
  -- given prompt maps to AT MOST ONE row per scope — so status is never
  -- self-contradictory for a prompt+scope. priority_score (then created_at)
  -- only ever tie-breaks ACROSS DIFFERENT prompts competing within the same
  -- precedence band, never between two statuses of one prompt+scope.
  priority_score       numeric,
  -- Provenance of the assignment (e.g. 'operator', 'notification', 'import',
  -- 'legacy_backfill').
  source_basis         text,
  metadata             jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at           timestamptz NOT NULL DEFAULT now(),

  -- EXACTLY ONE applicability scope per row. A NULL cycle is intentional and is
  -- not a scope (applicability is evergreen). num_nonnulls collapses the
  -- three-way choice to a single deterministic invariant.
  CONSTRAINT writing_prompt_targets_scope_exactly_one
    CHECK (num_nonnulls(exam_family_id, exam_id, exam_phase_id) = 1)
);

COMMENT ON TABLE public.writing_prompt_targets IS
  'Exam/family/phase applicability mapping for canonical (subject-scoped) '
  'writing_prompts (sole applicability authority — writing_prompts has no exam '
  'scope columns). Exactly one scope per row. Precedence: phase > exam > '
  'family > global (baseline). applicability_status=excluded is a per-scope '
  'override that subtracts a scope from an otherwise-global prompt. Evergreen: '
  'no exam_cycle_id (cycle rules live in exam_descriptive_requirements). '
  'Service-role-managed (see migration header).';

-- Null-safe UNIQUE identity: the same prompt cannot have two rows for the same
-- scope. Postgres 16 `NULLS NOT DISTINCT` treats the two NULL scope columns of
-- any given row as EQUAL, so (prompt, exam=X, family=NULL, phase=NULL) collides
-- with a second identical row but not with (prompt, family=Y, ...). CI Postgres
-- is 16, so this is the clean, index-native way to express the constraint.
CREATE UNIQUE INDEX IF NOT EXISTS uq_writing_prompt_targets_scope
  ON public.writing_prompt_targets
     (prompt_id, exam_family_id, exam_id, exam_phase_id)
  NULLS NOT DISTINCT;

-- ----------------------------------------------------------------------------
-- 1b. Backfill BEFORE dropping the legacy exam-scope columns (idempotent).
--     For every existing writing_prompts row that names an exam, capture its
--     scope as a target row. Prefer the MOST SPECIFIC scope: if exam_phase_id
--     is present -> a phase-scoped target; else an exam-scoped target. We do
--     NOT carry exam_cycle_id (evergreen). ON CONFLICT DO NOTHING against the
--     null-safe unique index makes re-application a no-op.
--
--     Guarded by an information_schema column-existence check so a SECOND apply
--     (after the columns are already dropped in §2) is a clean no-op rather
--     than an error on the missing columns.
-- ----------------------------------------------------------------------------
DO $backfill$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name  = 'writing_prompts'
      AND column_name = 'exam_id'
  ) THEN
    -- Phase-scoped where a phase is named (most specific).
    EXECUTE $sql$
      INSERT INTO public.writing_prompt_targets
        (prompt_id, exam_phase_id, applicability_status, source_basis)
      SELECT wp.id, wp.exam_phase_id, 'active', 'legacy_backfill'
      FROM public.writing_prompts wp
      WHERE wp.exam_id IS NOT NULL
        AND wp.exam_phase_id IS NOT NULL
      ON CONFLICT DO NOTHING
    $sql$;

    -- Exam-scoped where no phase is named.
    EXECUTE $sql$
      INSERT INTO public.writing_prompt_targets
        (prompt_id, exam_id, applicability_status, source_basis)
      SELECT wp.id, wp.exam_id, 'active', 'legacy_backfill'
      FROM public.writing_prompts wp
      WHERE wp.exam_id IS NOT NULL
        AND wp.exam_phase_id IS NULL
      ON CONFLICT DO NOTHING
    $sql$;
  END IF;
END
$backfill$;

-- ----------------------------------------------------------------------------
-- 2. Drop the dual-authority exam-scope columns from writing_prompts.
--    Canonical identity is subject_id / topic_id / microtopic_id (from 205,
--    left NOT NULL / as-declared). Applicability now lives ONLY in
--    writing_prompt_targets — no dual authority.
--
--    Migration 205 created two indexes that reference exam_id:
--      idx_writing_prompts_exam   ON (exam_id)
--      idx_writing_prompts_active ON (exam_id, exercise_type)
--                                 WHERE reviewer_status='verified' AND is_active=true
--    A column drop would fail (or silently cascade-drop dependent indexes) — we
--    DROP both indexes explicitly FIRST. Dropping a landed index inside a NEW
--    forward migration is allowed (migration 205 itself stays immutable / is
--    NOT edited).
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS public.idx_writing_prompts_exam;
DROP INDEX IF EXISTS public.idx_writing_prompts_active;

ALTER TABLE public.writing_prompts
  DROP COLUMN IF EXISTS exam_id,
  DROP COLUMN IF EXISTS exam_cycle_id,
  DROP COLUMN IF EXISTS exam_phase_id;

-- Replacement lookup index on the SUBJECT-scoped canonical identity for the
-- verified/active read path (mirrors the intent of the dropped
-- idx_writing_prompts_active, now keyed on canonical content instead of exam).
-- NOTE (correcting a false claim in an earlier draft): this is a NON-UNIQUE
-- partial index, and Postgres B-tree indexes DO index NULL keys — a NULL
-- microtopic_id is present in the index, not "unindexed". The partiality is the
-- WHERE predicate only (verified + active), not any NULL-key exclusion.
CREATE INDEX IF NOT EXISTS idx_writing_prompts_active_subject
  ON public.writing_prompts (subject_id, topic_id, microtopic_id, exercise_type)
  WHERE reviewer_status = 'verified' AND is_active = true;

-- ----------------------------------------------------------------------------
-- 3. Resolver indexes on the mapping table.
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_writing_prompt_targets_prompt
  ON public.writing_prompt_targets(prompt_id);

CREATE INDEX IF NOT EXISTS idx_writing_prompt_targets_exam
  ON public.writing_prompt_targets(exam_id)
  WHERE exam_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_writing_prompt_targets_family
  ON public.writing_prompt_targets(exam_family_id)
  WHERE exam_family_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_writing_prompt_targets_phase
  ON public.writing_prompt_targets(exam_phase_id)
  WHERE exam_phase_id IS NOT NULL;

-- Fast path for the common resolver filter (active applicability only).
CREATE INDEX IF NOT EXISTS idx_writing_prompt_targets_active
  ON public.writing_prompt_targets(prompt_id)
  WHERE applicability_status = 'active';

-- ----------------------------------------------------------------------------
-- 4. RLS: enabled, NO client allow policy (service-role-managed).
--    Mirrors the migration-205 §12.2 service-role-only posture. The resolver
--    reads via service_role (bypasses RLS); anon/authenticated get no rows.
-- ----------------------------------------------------------------------------
ALTER TABLE public.writing_prompt_targets ENABLE ROW LEVEL SECURITY;

-- No CREATE POLICY: the zero-client-policy posture is deliberate. Do not add a
-- SELECT/INSERT policy to this table without an explicit architecture decision
-- (same rule as migration 205 §12.2 service-role-only tables).
