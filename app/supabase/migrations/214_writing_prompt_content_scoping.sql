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
--      to a single exam. `writing_prompts.exam_id` therefore becomes NULLABLE
--      (mirrors the shared-content semantics already used by the mock question
--      bank, `136_mock_question_workflow.sql`, where
--      `exam_id uuid references exams(id) on delete set null`).
--
--   2. APPLICABILITY = exam / family / phase-scoped, via the NEW mapping
--      table `public.writing_prompt_targets`. One prompt may apply to many
--      exams / families / phases with no content duplication. Precedence
--      when resolving which prompts apply to an exam+phase context:
--
--        phase-specific  >  exam-specific  >  exam-family  >  globally-applicable
--        (a prompt with NO target rows is globally applicable to every exam)
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
-- MIGRATION NUMBER — VERIFY DB / reconcile-at-apply.
-- The filesystem max migration on `main` is 213, so this file is numbered 214
-- (the CI `validate` guard enforces filesystem contiguity vs main). The live
-- `select max(version)::int + 1 from schema_migrations` CANNOT be run in this
-- container and MUST be reconciled/renamed at apply time (OPERATOR PENDING),
-- per the standard EWP-9 fallback in AGENTS.md.
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
-- No data backfill (the ~270-item prompt bank is not seeded yet). DDL only.
-- No AI writes. No writes beyond DDL.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Canonical content is subject-scoped: exam_id becomes optional.
-- ----------------------------------------------------------------------------
-- A canonical prompt need not belong to any exam. subject_id / topic_id /
-- microtopic_id (from migration 205) remain NOT NULL / as-declared and carry
-- canonical identity.
ALTER TABLE public.writing_prompts
  ALTER COLUMN exam_id DROP NOT NULL;

-- The landed migration-205 partial unique/verified index on
-- (exam_id, exercise_type) WHERE reviewer_status='verified' AND is_active=true
-- still functions with a NULL exam_id: NULLs are simply not indexed for
-- uniqueness, so subject-scoped prompts with no exam do not collide. That index
-- is intentionally NOT dropped or recreated here (migration 205 is immutable).

-- ----------------------------------------------------------------------------
-- 2. Applicability mapping table (exam / family / phase-scoped).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_prompt_targets (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id            uuid NOT NULL
                         REFERENCES public.writing_prompts(id) ON DELETE CASCADE,
  -- At least one scope must be set (enforced by the CHECK below). The resolver
  -- reads phase > exam > family precedence; a prompt with NO target rows is
  -- globally applicable.
  exam_family_id       uuid REFERENCES public.exam_families(id),
  exam_id              uuid REFERENCES public.exams(id) ON DELETE CASCADE,
  exam_phase_id        uuid REFERENCES public.exam_phases(id),
  applicability_status text NOT NULL DEFAULT 'active'
                         CHECK (applicability_status IN ('active','excluded','pending_review')),
  -- Optional operator-set tiebreak within a precedence band; the resolver's
  -- primary ordering is the phase>exam>family>global precedence — this only
  -- breaks ties inside a band.
  priority_score       numeric,
  -- Provenance of the assignment (e.g. 'operator', 'notification', 'import').
  source_basis         text,
  metadata             jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at           timestamptz NOT NULL DEFAULT now(),

  -- A target row must name at least one applicability scope. A NULL cycle is
  -- intentional and is not a scope (applicability is evergreen).
  CONSTRAINT writing_prompt_targets_scope_present
    CHECK (
      exam_family_id IS NOT NULL
      OR exam_id IS NOT NULL
      OR exam_phase_id IS NOT NULL
    )
);

COMMENT ON TABLE public.writing_prompt_targets IS
  'Exam/family/phase applicability mapping for canonical (subject-scoped) '
  'writing_prompts. Precedence: phase > exam > family > global (no target row). '
  'Evergreen: intentionally no exam_cycle_id — cycle rules live in '
  'exam_descriptive_requirements. Service-role-managed (see migration header).';

-- ----------------------------------------------------------------------------
-- 3. Resolver indexes.
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
