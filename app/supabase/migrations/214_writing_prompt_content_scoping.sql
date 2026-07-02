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
--   2. APPLICABILITY = global / exam / family / phase-scoped, via the NEW
--      mapping table `public.writing_prompt_targets`. One prompt may apply to
--      many exams / families / phases with no content duplication. Precedence
--      when resolving which prompts apply to an exam+phase context:
--
--        phase-specific  >  exam-specific  >  exam-family  >  global
--
--      DEFAULT-DENY semantics (the single, precise rule — supersedes and
--      REPLACES any earlier "no rows = global" / "no active restrictive target
--      = global" phrasing, which was fail-open and is now forbidden):
--        * "Global" is an EXPLICIT capability, carried by a target row with
--          `is_global = true` (and all three scope columns NULL). It is NOT an
--          implicit default. A prompt is applicable to an exam/phase context
--          IFF it has an ACTIVE matching target row:
--            - an ACTIVE `is_global` target (applies everywhere), OR
--            - an ACTIVE family/exam/phase target that matches the context,
--              resolved by the phase > exam > family precedence above.
--        * NO active target row  ⇒  the prompt is NOT applicable (UNASSIGNED).
--          Never global. Deleting, cascading-away, or leaving a prompt without
--          an active target REMOVES it from every surface — it can never widen
--          access. This is fail-CLOSED.
--        * `applicability_status='excluded'` is an OVERRIDE that subtracts a
--          narrower scope FROM an explicit active broader scope (e.g. exclude
--          one exam/phase from an active `is_global` or active family target).
--          An excluded row confers NO applicability on its own.
--        * `applicability_status='pending_review'` targets do NOT confer
--          applicability — they are inert until an operator promotes them to
--          `active`. (Used by the legacy-cycle quarantine backfill; see §1b.)
--
--      NOTE: applicability is deliberately EVERGREEN — it carries no
--      `exam_cycle_id`. Canonical content survives cycles; a cycle-specific
--      rule belongs in `exam_descriptive_requirements`, not here. Legacy rows
--      that DID carry an exam_cycle_id are QUARANTINED (pending_review) rather
--      than converted to evergreen applicability — see §1b.
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
--   * OPERATOR-ATTESTED EVIDENCE (VERIFY DB, 2026-07-02): the operator attests
--     that `SELECT max(version) FROM supabase_migrations.schema_migrations` on
--     the live DB returns 212. This is operator-attested (not self-derived: the
--     live query cannot be run from the CI container). Recorded in the checklist
--     migration-number row. If a later live query contradicts 212, re-open the
--     apply-order note above before applying 214.
--
-- ----------------------------------------------------------------------------
-- ACTIVATION GATE (FAIL-CLOSED — enforced by THIS migration, not prose).
--   The resolver, the session/planner enforcement, and the replacement of the
--   `writing_prompts_public_read` RLS policy (which today still lets any
--   verified+active prompt be read/launched, bypassing writing_prompt_targets)
--   do NOT exist yet. While `writing_prompt_targets` is declared the SOLE
--   applicability authority but is not yet enforced on the read path, an active
--   writing_prompt would remain launchable through that known bypass. So §5 of
--   this migration DEACTIVATES every currently-active writing_prompts row
--   (is_active=false). Reactivation is GATED on the resolver + session/planner
--   enforcement + public-read-policy-replacement PR. No prompt bank is seeded
--   yet, so this is low-impact and safe.
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
-- EXISTS`. The §5 deactivation is a no-op on the second apply (no rows remain
-- active once run). No AI writes. Writes are limited to the one-time legacy
-- backfill and the one-time activation-gate deactivation.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Applicability mapping table (global / exam / family / phase-scoped).
--    Created BEFORE the backfill (§1b) and BEFORE the column drops (§2), so the
--    legacy exam scope on writing_prompts can be captured as target rows first.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_prompt_targets (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id            uuid NOT NULL
                         REFERENCES public.writing_prompts(id) ON DELETE CASCADE,
  -- EXACTLY ONE scope must be set (enforced by the CHECK below): one of
  -- {global, family, exam, phase}. A single target row names a single scope
  -- kind; a prompt that applies to several scopes gets several rows. This makes
  -- the (prompt_id, scope) identity deterministic and lets the null-safe unique
  -- index below reject duplicates.
  --
  -- is_global is the EXPLICIT global capability (DEFAULT-DENY design): a global
  -- target row sets is_global=true with all three scope columns NULL. There is
  -- no implicit "no rows = global" — a prompt with no active target is NOT
  -- applicable anywhere. Defaults to false so a scoped row need not mention it.
  is_global            boolean NOT NULL DEFAULT false,
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

  -- EXACTLY ONE applicability scope per row, chosen from {global, family, exam,
  -- phase}. A NULL cycle is intentional and is not a scope (applicability is
  -- evergreen). num_nonnulls counts the set scope columns; (is_global)::int adds
  -- the explicit-global choice, so the invariant is: precisely one of the four.
  CONSTRAINT writing_prompt_targets_scope_exactly_one
    CHECK (num_nonnulls(exam_family_id, exam_id, exam_phase_id) + (is_global)::int = 1)
);

COMMENT ON TABLE public.writing_prompt_targets IS
  'Global/exam/family/phase applicability mapping for canonical (subject-scoped) '
  'writing_prompts (sole applicability authority — writing_prompts has no exam '
  'scope columns). DEFAULT-DENY: a prompt is applicable IFF it has an ACTIVE '
  'matching target; no active target => not applicable (never global). Exactly '
  'one scope per row: is_global OR family OR exam OR phase. Precedence: phase > '
  'exam > family > global. applicability_status=excluded subtracts a narrower '
  'scope from an explicit active broader scope; pending_review confers no '
  'applicability. Evergreen: no exam_cycle_id (cycle rules live in '
  'exam_descriptive_requirements; legacy cycle rows are quarantined as '
  'pending_review). Service-role-managed (see migration header).';

-- Null-safe UNIQUE identity: the same prompt cannot have two rows for the same
-- scope. is_global is part of the identity so a prompt cannot carry two
-- identical global rows (both is_global=true, all scope columns NULL collide).
-- Postgres 16 `NULLS NOT DISTINCT` treats the NULL scope columns of any given
-- row as EQUAL, so (prompt, is_global=t, NULL,NULL,NULL) collides with a second
-- identical global row, and (prompt, is_global=f, exam=X, NULL, NULL) collides
-- with a second identical exam row but not with (prompt, family=Y, ...). CI
-- Postgres is 16, so this is the clean, index-native way to express it.
CREATE UNIQUE INDEX IF NOT EXISTS uq_writing_prompt_targets_scope
  ON public.writing_prompt_targets
     (prompt_id, is_global, exam_family_id, exam_id, exam_phase_id)
  NULLS NOT DISTINCT;

-- ----------------------------------------------------------------------------
-- 1b. Backfill BEFORE dropping the legacy exam-scope columns (idempotent).
--     For every existing writing_prompts row that names an exam, capture its
--     scope as a target row. Prefer the MOST SPECIFIC scope: if exam_phase_id
--     is present -> a phase-scoped target; else an exam-scoped target. We do
--     NOT carry exam_cycle_id as evergreen applicability.
--
--     LEGACY CYCLE QUARANTINE (do NOT silently drop cycle scope): a legacy row
--     with exam_cycle_id IS NOT NULL was cycle-specific content, which does NOT
--     map cleanly to evergreen applicability. Converting it to an evergreen
--     active exam target would silently WIDEN it across all cycles. Instead we
--     QUARANTINE it: a target with applicability_status='pending_review'
--     (default-deny keeps it inapplicable until an operator dispositions it),
--     scoped to the most specific surviving legacy scope (phase, else exam, else
--     the explicit is_global slot when neither survives), carrying the original
--     cycle/exam/phase in metadata and source_basis='legacy_cycle_quarantine'.
--     Cycle-scoped content is preserved for operator disposition, not lost.
--     Non-cycle legacy rows (cycle NULL) keep the ACTIVE exam/phase backfill.
--
--     ON CONFLICT DO NOTHING against the null-safe unique index makes
--     re-application a no-op. Guarded by an information_schema column-existence
--     check so a SECOND apply (after the columns are already dropped in §2) is a
--     clean no-op rather than an error on the missing columns.
-- ----------------------------------------------------------------------------
DO $backfill$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name  = 'writing_prompts'
      AND column_name = 'exam_id'
  ) THEN
    -- Legacy CYCLE-scoped rows -> QUARANTINE (pending_review), provenance kept.
    -- pending_review + default-deny keeps the row inapplicable regardless of its
    -- scope column, so the scope only needs to satisfy the exactly-one CHECK. We
    -- pick the most specific surviving legacy scope: phase, else exam, else (no
    -- exam/phase at all) the explicit is_global slot. ALL legacy scope info
    -- (cycle + exam + phase) is preserved in metadata for operator disposition.
    EXECUTE $sql$
      INSERT INTO public.writing_prompt_targets
        (prompt_id, is_global, exam_phase_id, exam_id,
         applicability_status, source_basis, metadata)
      SELECT wp.id,
             (wp.exam_phase_id IS NULL AND wp.exam_id IS NULL)          AS is_global,
             CASE WHEN wp.exam_phase_id IS NOT NULL THEN wp.exam_phase_id END,
             CASE WHEN wp.exam_phase_id IS NULL     THEN wp.exam_id     END,
             'pending_review', 'legacy_cycle_quarantine',
             jsonb_build_object(
               'legacy_exam_cycle_id', wp.exam_cycle_id,
               'legacy_exam_id',       wp.exam_id,
               'legacy_exam_phase_id', wp.exam_phase_id
             )
      FROM public.writing_prompts wp
      WHERE wp.exam_cycle_id IS NOT NULL
      ON CONFLICT DO NOTHING
    $sql$;

    -- Phase-scoped where a phase is named and NO cycle (most specific, active).
    EXECUTE $sql$
      INSERT INTO public.writing_prompt_targets
        (prompt_id, exam_phase_id, applicability_status, source_basis)
      SELECT wp.id, wp.exam_phase_id, 'active', 'legacy_backfill'
      FROM public.writing_prompts wp
      WHERE wp.exam_id IS NOT NULL
        AND wp.exam_cycle_id IS NULL
        AND wp.exam_phase_id IS NOT NULL
      ON CONFLICT DO NOTHING
    $sql$;

    -- Exam-scoped where no phase and NO cycle (active).
    EXECUTE $sql$
      INSERT INTO public.writing_prompt_targets
        (prompt_id, exam_id, applicability_status, source_basis)
      SELECT wp.id, wp.exam_id, 'active', 'legacy_backfill'
      FROM public.writing_prompts wp
      WHERE wp.exam_id IS NOT NULL
        AND wp.exam_cycle_id IS NULL
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

-- ----------------------------------------------------------------------------
-- 5. ACTIVATION GATE — FAIL CLOSED (see header). writing_prompt_targets is now
--    the sole applicability authority, but the resolver, session/planner
--    enforcement, and the writing_prompts_public_read policy replacement do NOT
--    exist yet — an active prompt would still be launchable through that known
--    read-path bypass. Deactivate every currently-active writing_prompts row so
--    none is launchable while enforcement is incomplete. Reactivation is gated
--    on the resolver + enforcement + public-read-policy-replacement PR. This is
--    a one-time write; the second apply is a no-op (no rows remain active).
--    No prompt bank is seeded yet, so this is low-impact and safe.
-- ----------------------------------------------------------------------------
UPDATE public.writing_prompts SET is_active = false WHERE is_active = true;
