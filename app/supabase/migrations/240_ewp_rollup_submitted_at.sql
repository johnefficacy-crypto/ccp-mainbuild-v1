-- 240_ewp_rollup_submitted_at.sql
--
-- Writes the session SUBMISSION timestamp the rollup has never persisted.
--
-- Gap: `public.writing_sessions.submitted_at` has existed since the schema
-- migration (205:206) but no code path ever writes it. Migration 238 wired
-- `completed_at` into `ewp_private.ewp_apply_session_rollup` and explicitly left
-- `submitted_at` untouched ("a rollup-owned value for it would be arbitrary").
-- This migration adopts a concrete, non-arbitrary definition (owner-approved):
-- the CLEARED-PARALLEL invariant, mirroring `completed_at` in the same function.
--
-- Definition / invariant maintained:
--   submitted_at IS NULL      ⇔  status = 'active'   (session still drafting)
--   submitted_at IS NOT NULL  ⇔  status has left drafting
--                                 (status ∈ evaluation_pending | evaluation_incomplete
--                                  | rewrite_required | completed)
-- i.e. `submitted_at` is stamped the first time every unit has a submitted
-- version (the session leaves 'active'), and is cleared on a learning-mode reopen
-- that returns the session to 'active'. Like `completed_at`, the stamp is
-- monotonic WHILE past-drafting (an existing stamp is kept on a re-roll) and is
-- re-stamped with a fresh now() only after a reopen→active→resubmit cycle. This
-- is deliberately parallel to `completed_at`'s cleared-on-reopen invariant rather
-- than a first-submission-preserving value.
--
-- Fix: CREATE OR REPLACE the rollup (byte-for-byte identical to migration 238
-- except the submitted_at read, the v_new_submitted_at computation, and the two
-- lines added to the final UPDATE). Same signature, SECURITY DEFINER, and no-op
-- guard, so no grant/caller changes (CREATE OR REPLACE preserves privileges).
--
-- NOT retroactive: only affects rollup transitions AFTER apply (and any session
-- re-finalized after apply). Already past-drafting rows written before this
-- migration keep `submitted_at = NULL` until re-finalized; a one-off operator
-- backfill is out of scope here.
--
-- MIGRATION NUMBER: 240 is the next free FILESYSTEM slot (238/239 taken). Per
-- AGENTS.md, the authoritative number is MAX(live `schema_migrations`) + 1 — the
-- operator must verify the live max before applying and renumber if it collides.

CREATE OR REPLACE FUNCTION ewp_private.ewp_apply_session_rollup(p_session uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_total          int;
  v_has_active     boolean;
  v_has_pending    boolean;
  v_has_failed     boolean;   -- evaluation_failed with recovery exhausted
  v_has_rewrite    boolean;
  v_all_terminal_units boolean;  -- non-empty AND every unit in {ready,completed}
  v_any_nonterm    boolean;   -- any unit whose latest eval is non-terminal
  v_has_unscored   boolean;
  v_has_detonly    boolean;
  v_has_versions   boolean;
  v_coverage_ok    boolean;
  v_must_fix       boolean;
  v_hash           text;
  v_status         text;
  v_agg            text;
  v_cur_outcome    text;
  v_new_outcome    text;
  v_cur_completed_at timestamptz;   -- persisted completion stamp (monotonic in-completed)
  v_new_completed_at timestamptz;   -- stamp to write for the recomputed status
  v_cur_submitted_at timestamptz;   -- persisted submission stamp (monotonic while past-drafting)
  v_new_submitted_at timestamptz;   -- stamp to write for the recomputed status
BEGIN
  SELECT evaluation_outcome, completed_at, submitted_at
    INTO v_cur_outcome, v_cur_completed_at, v_cur_submitted_at
  FROM public.writing_sessions WHERE id = p_session;

  WITH unit_view AS (
    SELECT u.id, u.unit_number, u.status,
           le.overall_status, le.eval_id
    FROM public.writing_session_units u
    LEFT JOIN LATERAL (
      SELECT v.id AS version_id
      FROM public.writing_unit_versions v
      WHERE v.unit_id = u.id
      ORDER BY v.version_number DESC LIMIT 1
    ) lv ON TRUE
    LEFT JOIN LATERAL (
      SELECT e.id AS eval_id, e.overall_status
      FROM public.writing_evaluations e
      WHERE e.unit_version_id = lv.version_id
      ORDER BY e.evaluation_revision DESC LIMIT 1
    ) le ON TRUE
    WHERE u.session_id = p_session
  )
  SELECT
    count(*),
    bool_or(status IN ('not_started','draft')),
    bool_or(status = 'evaluation_pending'
            OR (status = 'evaluation_failed' AND ewp_private.ewp_recovery_available(eval_id))),
    bool_or(status = 'evaluation_failed' AND NOT ewp_private.ewp_recovery_available(eval_id)),
    bool_or(status = 'rewrite_required'),
    (count(*) > 0 AND bool_and(status IN ('ready','completed'))),
    bool_or(overall_status IS NULL
            OR overall_status NOT IN ('completed','terminal_partial','failed')),
    bool_or(overall_status = 'failed'),
    bool_or(overall_status = 'terminal_partial')
  INTO v_total, v_has_active, v_has_pending, v_has_failed, v_has_rewrite,
       v_all_terminal_units, v_any_nonterm, v_has_unscored, v_has_detonly
  FROM unit_view;

  -- Authoritative coverage (§4.7a): trust the latest coverage row only while
  -- its pinned version_set_hash still equals the current, lock-consistent hash.
  SELECT EXISTS (
    SELECT 1 FROM public.writing_unit_versions v
    JOIN public.writing_session_units u ON u.id = v.unit_id
    WHERE u.session_id = p_session
  ) INTO v_has_versions;

  IF NOT COALESCE(v_has_versions, FALSE) THEN
    v_coverage_ok := FALSE;
  ELSE
    v_hash := ewp_private.ewp_version_set_hash(p_session);
    SELECT (c.passed AND c.version_set_hash = v_hash)
    INTO v_coverage_ok
    FROM public.writing_session_checks c
    WHERE c.session_id = p_session AND c.check_type = 'required_word_coverage'
    ORDER BY c.created_at DESC LIMIT 1;
    v_coverage_ok := COALESCE(v_coverage_ok, FALSE);
  END IF;

  v_must_fix := ewp_private.ewp_has_unresolved_must_fix(p_session);

  -- Session status by the locked priority order (§4.3b), first match wins.
  IF COALESCE(v_has_active, FALSE) THEN
    v_status := 'active';
  ELSIF COALESCE(v_has_pending, FALSE) THEN
    v_status := 'evaluation_pending';
  ELSIF COALESCE(v_has_failed, FALSE) THEN
    v_status := 'evaluation_incomplete';
  ELSIF COALESCE(v_has_rewrite, FALSE) THEN
    v_status := 'rewrite_required';
  ELSIF COALESCE(v_all_terminal_units, FALSE) THEN
    -- §4.6c completion gate: coverage passes AND no unresolved must_fix.
    IF v_coverage_ok AND NOT v_must_fix THEN
      v_status := 'completed';
    ELSE
      v_status := 'rewrite_required';
    END IF;
  ELSE
    v_status := 'active';
  END IF;

  -- Aggregate outcome (§9.1a): null while any unit non-terminal, else worst-of.
  IF v_total = 0 OR COALESCE(v_any_nonterm, FALSE) THEN
    v_agg := NULL;
  ELSIF COALESCE(v_has_unscored, FALSE) THEN
    v_agg := 'unscored';
  ELSIF COALESCE(v_has_detonly, FALSE) THEN
    v_agg := 'deterministic_only';
  ELSE
    v_agg := 'fully_evaluated';
  END IF;

  -- Monotonic: never downgrade a persisted outcome.
  v_new_outcome := CASE
    WHEN v_agg IS NULL THEN v_cur_outcome
    WHEN ewp_private.ewp_outcome_rank(v_agg) > ewp_private.ewp_outcome_rank(v_cur_outcome)
      THEN v_agg
    ELSE v_cur_outcome
  END;

  -- Completion timestamp invariant: completed_at IS NOT NULL ⇔ status='completed'.
  -- Into completed → stamp once (monotonic: keep an existing stamp on re-roll).
  -- Out of completed (e.g. learning-mode reopen) → clear back to NULL.
  v_new_completed_at := CASE
    WHEN v_status = 'completed' THEN COALESCE(v_cur_completed_at, now())
    ELSE NULL
  END;

  -- Submission timestamp invariant (cleared-parallel, mirrors completed_at):
  -- submitted_at IS NOT NULL ⇔ status has left drafting (status <> 'active').
  -- Into a past-drafting status → stamp once (monotonic while past-drafting).
  -- Back to 'active' (learning-mode reopen) → clear back to NULL.
  v_new_submitted_at := CASE
    WHEN v_status <> 'active' THEN COALESCE(v_cur_submitted_at, now())
    ELSE NULL
  END;

  UPDATE public.writing_sessions
  SET status = v_status,
      evaluation_outcome = v_new_outcome,
      completed_at = v_new_completed_at,
      submitted_at = v_new_submitted_at
  WHERE id = p_session
    AND (status IS DISTINCT FROM v_status
         OR evaluation_outcome IS DISTINCT FROM v_new_outcome
         OR completed_at IS DISTINCT FROM v_new_completed_at
         OR submitted_at IS DISTINCT FROM v_new_submitted_at);

  RETURN jsonb_build_object('status', v_status, 'evaluation_outcome', v_new_outcome);
END;
$$;

SELECT pg_notify('pgrst', 'reload schema');
