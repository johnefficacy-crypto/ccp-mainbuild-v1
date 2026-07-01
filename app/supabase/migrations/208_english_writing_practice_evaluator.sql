-- Migration 208: English Writing Practice (EWP-2B) — async evaluator worker RPCs.
--
-- The async language/rubric evaluator runs OUTSIDE the DB (the model/mock call
-- must not hold a transaction, §8.1 step 3). The claim, the atomic terminal
-- write, the retry/fail path, the stale-lease sweep, and the post-commit
-- mastery-outbox drain are all SECURITY DEFINER RPCs so the worker never issues
-- non-atomic multi-statement writes.
--
-- Invariants enforced here (§8.1/§8.3/§14):
--   * Claim uses FOR UPDATE SKIP LOCKED; a claimed job holds a lease
--     (locked_at) + a fencing token (claim_token).
--   * The terminal write re-reads the job FOR UPDATE and asserts the caller's
--     claim_token still matches (fencing) — a stale worker whose lease expired
--     and was reclaimed cannot double-apply side effects.
--   * Replay guard: if the evaluation envelope is already terminal, the job is
--     acknowledged without reprocessing.
--   * Canonical lock order (§8.0): session row, then ALL units ascending, taken
--     BEFORE any write, so the in-transaction session rollup is consistent.
--   * Issue lineage + microtopic mapping + automatic projections are assigned
--     in-DB; the evaluator only supplies issue_type + spans (§4.8a, §5.3).
--   * append-only tables are INSERTed, never UPDATEd (immutability triggers).
--   * Mastery side effects go through the transactional outbox (§8.2); the drain
--     writes evidence + shadow idempotently (shadow-only until Lane A clears).
--
-- Migration number: highest on main is 207; this is 208.
-- VERIFY DB against schema_migrations before apply (OPERATOR).

CREATE SCHEMA IF NOT EXISTS ewp_private;  -- created in 205; defensive for isolation.

-- ===========================================================================
-- Private helper: active (unresolved) issues of a unit's PRIOR version (N-1).
-- Returns issue_event rows the evaluator maps its rewrite against (§4.8a).
-- ===========================================================================
CREATE OR REPLACE FUNCTION ewp_private.ewp_prior_active_issues(p_unit uuid, p_version_number int)
RETURNS TABLE (issue_event_id uuid, issue_type text, lineage_id uuid, quoted_text text)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  WITH prior_ver AS (
    SELECT id FROM public.writing_unit_versions
    WHERE unit_id = p_unit AND version_number = p_version_number - 1
    LIMIT 1
  ),
  prior_eval AS (
    SELECT e.id FROM public.writing_evaluations e
    WHERE e.unit_version_id IN (SELECT id FROM prior_ver)
    ORDER BY e.evaluation_revision DESC LIMIT 1
  )
  SELECT i.id, i.issue_type, i.lineage_id, i.quoted_text
  FROM public.writing_issue_events i
  WHERE i.evaluation_id IN (SELECT id FROM prior_eval)
    AND i.affects_current_state = TRUE
    AND NOT EXISTS (
      SELECT 1 FROM public.writing_issue_resolution_events r
      WHERE r.issue_event_id = i.id
    )
    -- exclude issues withdrawn by review (§4.10); no-op until EWP-3 reviews exist.
    AND NOT ewp_private.ewp_issue_effectively_invalidated(i.id);
$$;

-- ===========================================================================
-- Claim one pending evaluation job (FOR UPDATE SKIP LOCKED) and stamp a lease.
-- Returns the full evaluation context the worker needs to run the evaluator.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_claim_evaluation_job(
  p_lease_seconds int DEFAULT 900,
  p_job_kinds text[] DEFAULT ARRAY['language_evaluation','rubric_evaluation']
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_job     public.writing_evaluation_jobs%ROWTYPE;
  v_token   uuid := gen_random_uuid();
  v_eval    public.writing_evaluations%ROWTYPE;
  v_ver     public.writing_unit_versions%ROWTYPE;
  v_unit    public.writing_session_units%ROWTYPE;
  v_session public.writing_sessions%ROWTYPE;
  v_prompt  public.writing_prompts%ROWTYPE;
  v_maxver  int;
  v_is_current boolean;
BEGIN
  SELECT * INTO v_job FROM public.writing_evaluation_jobs j
  WHERE j.status = 'pending'
    AND j.job_kind = ANY(p_job_kinds)
    AND (j.scheduled_for IS NULL OR j.scheduled_for <= now())
  ORDER BY j.created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN
    RETURN NULL;  -- queue empty; worker idles
  END IF;

  UPDATE public.writing_evaluation_jobs
  SET status = 'running', locked_at = now(), claim_token = v_token,
      attempts = attempts + 1, updated_at = now()
  WHERE id = v_job.id;

  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_job.evaluation_id;
  SELECT * INTO v_ver  FROM public.writing_unit_versions WHERE id = v_eval.unit_version_id;
  SELECT * INTO v_unit FROM public.writing_session_units WHERE id = v_ver.unit_id;
  SELECT * INTO v_session FROM public.writing_sessions WHERE id = v_unit.session_id;
  SELECT * INTO v_prompt FROM public.writing_prompts WHERE id = v_session.prompt_id;

  SELECT MAX(version_number) INTO v_maxver
  FROM public.writing_unit_versions WHERE unit_id = v_unit.id;
  v_is_current := (v_ver.version_number = v_maxver);

  -- Mark the language stage running (audit trail; recovery resets to queued).
  IF v_job.job_kind = 'language_evaluation' THEN
    UPDATE public.writing_evaluations
    SET language_status = 'running', updated_at = now()
    WHERE id = v_eval.id AND language_status IN ('queued','failed','running');
  END IF;

  RETURN jsonb_build_object(
    'job_id',           v_job.id,
    'claim_token',      v_token,
    'job_kind',         v_job.job_kind,
    'generation',       v_job.generation,
    'attempts',         v_job.attempts + 1,
    'max_attempts',     v_job.max_attempts,
    'evaluation_id',    v_eval.id,
    'evaluation_revision', v_eval.evaluation_revision,
    'deterministic_status', v_eval.deterministic_status,
    'unit_version_id',  v_ver.id,
    'version_number',   v_ver.version_number,
    'is_current',       v_is_current,
    'answer_text',      v_ver.answer_text,
    'content_hash',     v_ver.content_hash,
    'unit_id',          v_unit.id,
    'unit_number',      v_unit.unit_number,
    'unit_status',      v_unit.status,
    -- Named identically to the mastery-drain payload so the worker's predicted
    -- mastery key matches the drain-derived evidence key field-for-field.
    'microtopic_id',    v_unit.practice_microtopic_id,
    'session_id',       v_session.id,
    'user_id',          v_session.user_id,
    'mode',             v_session.mode,
    'projection_revision', v_session.projection_revision,
    'exercise_type',    v_prompt.exercise_type,
    'topic_id',         v_prompt.topic_id,
    'exam_id',          v_prompt.exam_id,
    'rubric_dimensions', COALESCE((
      SELECT r.dimensions FROM public.writing_rubrics r
      WHERE r.id = v_prompt.rubric_id
    ), '[]'::jsonb),
    'active_prior_issues', COALESCE((
      SELECT jsonb_agg(jsonb_build_object(
        'issue_event_id', a.issue_event_id, 'issue_type', a.issue_type,
        'lineage_id', a.lineage_id, 'quoted_text', a.quoted_text))
      FROM ewp_private.ewp_prior_active_issues(v_unit.id, v_ver.version_number) a
    ), '[]'::jsonb),
    'resolved_prior_lineages', COALESCE((
      SELECT jsonb_agg(DISTINCT i.lineage_id)
      FROM public.writing_issue_resolution_events r
      JOIN public.writing_issue_events i ON i.id = r.issue_event_id
      JOIN public.writing_evaluations e2 ON e2.id = i.evaluation_id
      JOIN public.writing_unit_versions v2 ON v2.id = e2.unit_version_id
      WHERE v2.unit_id = v_unit.id AND r.outcome = 'resolved'
        AND NOT ewp_private.ewp_issue_effectively_invalidated(i.id)
    ), '[]'::jsonb)
  );
END;
$$;

-- ===========================================================================
-- Complete a language evaluation atomically: fencing + replay guard, insert
-- issue events (backend lineage + microtopic map), resolution events,
-- automatic projections (race-safe count), update evaluation, drive the unit
-- transition, enqueue the mastery outbox, ack the job, and roll the session up.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_complete_language_evaluation(
  p_job_id uuid,
  p_claim_token uuid,
  p_evaluator_version text,
  p_issues jsonb,                 -- array of issue objects from the evaluator
  p_language_result jsonb,
  p_dimension_scores jsonb DEFAULT NULL,
  p_needs_human_review boolean DEFAULT FALSE,
  p_mastery_flag text DEFAULT 'off',
  p_mastery_idempotency_key text DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_job      public.writing_evaluation_jobs%ROWTYPE;
  v_eval     public.writing_evaluations%ROWTYPE;
  v_ver      public.writing_unit_versions%ROWTYPE;
  v_unit     public.writing_session_units%ROWTYPE;
  v_session  public.writing_sessions%ROWTYPE;
  v_is_current boolean;
  v_maxver   int;
  v_issue    jsonb;
  v_pred     uuid;
  v_lineage  uuid;
  v_microtopic uuid;
  v_new_issue uuid;
  v_new_issue_id uuid;
  v_count    int;
  v_has_must_fix boolean := FALSE;
  v_resolved_count int := 0;
  v_unit_target text;
  v_human text := 'not_required';
  v_pred_type text;
  v_pred_quote text;
BEGIN
  -- Resolve the id chain WITHOUT locking first, so locks can be taken strictly
  -- in the canonical order (§8.0): session → all units ascending → evaluation →
  -- job. Locking the job/evaluation before the session would invert that order
  -- and risk a deadlock against submit/finalize.
  SELECT * INTO v_job FROM public.writing_evaluation_jobs WHERE id = p_job_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ewp_job_not_found: job % not found', p_job_id;
  END IF;
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_job.evaluation_id;
  SELECT * INTO v_ver  FROM public.writing_unit_versions WHERE id = v_eval.unit_version_id;
  SELECT * INTO v_unit FROM public.writing_session_units WHERE id = v_ver.unit_id;

  -- Canonical locks, top-down, then re-read the evaluation + job under lock.
  SELECT * INTO v_session FROM public.writing_sessions WHERE id = v_unit.session_id FOR UPDATE;
  PERFORM 1 FROM public.writing_session_units
    WHERE session_id = v_session.id ORDER BY unit_number FOR UPDATE;
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_job.evaluation_id FOR UPDATE;
  SELECT * INTO v_job  FROM public.writing_evaluation_jobs WHERE id = p_job_id FOR UPDATE;

  -- Fencing: the job must still be ours (status running + matching token).
  IF v_job.status <> 'running' OR v_job.claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'ewp_job_fencing_failed: job % is no longer owned by this claim', p_job_id;
  END IF;

  -- Replay guard: already-terminal envelope → ack the job, do nothing else.
  IF v_eval.overall_status IN ('completed','terminal_partial','failed') THEN
    UPDATE public.writing_evaluation_jobs
    SET status = 'done', locked_at = NULL, updated_at = now() WHERE id = v_job.id;
    RETURN jsonb_build_object('status','replayed','overall_status',v_eval.overall_status);
  END IF;

  SELECT MAX(version_number) INTO v_maxver
  FROM public.writing_unit_versions WHERE unit_id = v_unit.id;
  v_is_current := (v_ver.version_number = v_maxver);

  -- Insert issue events (backend owns lineage + microtopic resolution, §4.8a).
  FOR v_issue IN SELECT * FROM jsonb_array_elements(COALESCE(p_issues, '[]'::jsonb))
  LOOP
    v_pred := NULLIF(v_issue->>'predecessor_issue_event_id','')::uuid;
    -- A supplied predecessor must be a real prior issue of THIS unit.
    IF v_pred IS NOT NULL THEN
      -- The predecessor must be an issue of THIS unit on a STRICTLY PRIOR version
      -- (§4.8a): never the same version being written, never a later one.
      SELECT i.lineage_id INTO v_lineage
      FROM public.writing_issue_events i
      JOIN public.writing_evaluations e2 ON e2.id = i.evaluation_id
      JOIN public.writing_unit_versions v2 ON v2.id = e2.unit_version_id
      WHERE i.id = v_pred AND v2.unit_id = v_unit.id
        AND v2.version_number < v_ver.version_number;
      IF v_lineage IS NULL THEN
        RAISE EXCEPTION 'ewp_bad_predecessor: % is not a prior-version issue of this unit', v_pred;
      END IF;
    ELSE
      v_lineage := gen_random_uuid();
    END IF;

    -- Resolve microtopic via the active map; NULL (topic-level) if unmapped.
    SELECT m.microtopic_id INTO v_microtopic
    FROM public.writing_issue_type_microtopic_map m
    WHERE m.issue_type = (v_issue->>'issue_type') AND m.is_active = TRUE
    LIMIT 1;

    INSERT INTO public.writing_issue_events(
      evaluation_id, issue_type, microtopic_id, lineage_id, predecessor_issue_event_id,
      span_start_utf16, span_end_utf16, quoted_text, original_text, suggested_text,
      explanation, severity, affects_current_state)
    VALUES (
      v_eval.id, v_issue->>'issue_type', v_microtopic, v_lineage, v_pred,
      NULLIF(v_issue->>'span_start_utf16','')::int, NULLIF(v_issue->>'span_end_utf16','')::int,
      v_issue->>'quoted_text', v_issue->>'original_text', v_issue->>'suggested_text',
      v_issue->>'explanation', v_issue->>'severity', v_is_current)
    RETURNING id INTO v_new_issue_id;

    IF (v_issue->>'severity') = 'must_fix' AND v_is_current THEN
      v_has_must_fix := TRUE;
    END IF;

    -- Automatic projection with a race-safe prior-occurrence count: hold an
    -- advisory xact lock on (user, microtopic, issue_type) across read+insert.
    PERFORM pg_advisory_xact_lock(
      hashtext(v_session.user_id::text || ':' ||
               COALESCE(v_microtopic::text,'-') || ':' || (v_issue->>'issue_type')));
    SELECT count(*) INTO v_count
    FROM public.writing_issue_events i2
    JOIN public.writing_evaluations e3 ON e3.id = i2.evaluation_id
    JOIN public.writing_unit_versions v3 ON v3.id = e3.unit_version_id
    JOIN public.writing_session_units u3 ON u3.id = v3.unit_id
    JOIN public.writing_sessions s3 ON s3.id = u3.session_id
    WHERE s3.user_id = v_session.user_id
      AND i2.issue_type = (v_issue->>'issue_type')
      -- Scope the count to the SAME microtopic as the advisory-lock key (§4.11),
      -- so the lock actually serialises the readers it is meant to.
      AND i2.microtopic_id IS NOT DISTINCT FROM v_microtopic
      AND i2.id <> v_new_issue_id;

    INSERT INTO public.writing_issue_projections(
      issue_event_id, projection_revision, projection_kind, prior_occurrence_count)
    VALUES (v_new_issue_id, v_session.projection_revision, 'automatic', v_count)
    ON CONFLICT (issue_event_id, projection_revision)
      WHERE projection_kind = 'automatic' DO NOTHING;
  END LOOP;

  -- Resolution events vs the prior version's active issues (only the current
  -- rewrite resolves; stale re-evaluations do not, §4.9a).
  IF v_is_current THEN
    FOR v_pred, v_lineage, v_pred_type, v_pred_quote IN
      SELECT a.issue_event_id, a.lineage_id, a.issue_type, a.quoted_text
      FROM ewp_private.ewp_prior_active_issues(v_unit.id, v_ver.version_number) a
    LOOP
      -- A prior issue "persists" if a new issue names it as predecessor OR (as a
      -- backend-owned fallback when the evaluator drops the predecessor) matches
      -- it by issue_type + quoted_text; otherwise it is genuinely resolved.
      SELECT id INTO v_new_issue FROM public.writing_issue_events
      WHERE evaluation_id = v_eval.id
        AND (predecessor_issue_event_id = v_pred
             OR (issue_type = v_pred_type AND quoted_text IS NOT DISTINCT FROM v_pred_quote))
      LIMIT 1;
      INSERT INTO public.writing_issue_resolution_events(
        issue_event_id, resolving_version_id, resolving_evaluation_id,
        successor_issue_event_id, outcome, evaluator_version)
      VALUES (
        v_pred, v_ver.id, v_eval.id, v_new_issue,
        CASE WHEN v_new_issue IS NULL THEN 'resolved' ELSE 'persisted' END,
        p_evaluator_version)
      ON CONFLICT (issue_event_id, resolving_version_id, evaluator_version) DO NOTHING;
      IF v_new_issue IS NULL THEN v_resolved_count := v_resolved_count + 1; END IF;
    END LOOP;
  END IF;

  -- Update the evaluation envelope: language stage completed.
  IF p_needs_human_review THEN v_human := 'pending'; END IF;
  UPDATE public.writing_evaluations SET
    language_status = 'completed',
    language_evaluator_version = p_evaluator_version,
    language_result = p_language_result,
    dimension_scores = COALESCE(p_dimension_scores, dimension_scores),
    human_review_status = v_human,
    overall_status = 'completed',
    updated_at = now()
  WHERE id = v_eval.id;

  -- Drive the unit transition (only the current version; §4.4b). A pending unit
  -- with an unresolved must_fix needs a rewrite; otherwise it is ready.
  IF v_is_current AND v_unit.status = 'evaluation_pending' THEN
    v_unit_target := CASE WHEN v_has_must_fix AND v_session.mode = 'learning'
                          THEN 'rewrite_required' ELSE 'ready' END;
    UPDATE public.writing_session_units SET status = v_unit_target WHERE id = v_unit.id;
  ELSE
    v_unit_target := v_unit.status;
  END IF;

  -- Enqueue the mastery outbox (§8.2) — shadow/live only, current version only.
  IF p_mastery_flag IN ('shadow','live') AND v_is_current AND p_mastery_idempotency_key IS NOT NULL THEN
    INSERT INTO public.writing_mastery_outbox(
      source_kind, evaluation_id, evidence_op, user_id, mastery_flag_state, idempotency_key, status)
    VALUES ('evaluation', v_eval.id, 'assert', v_session.user_id, p_mastery_flag,
            p_mastery_idempotency_key, 'pending')
    ON CONFLICT (idempotency_key) DO NOTHING;
  END IF;

  -- Acknowledge the job atomically with all side effects.
  UPDATE public.writing_evaluation_jobs
  SET status = 'done', locked_at = NULL, updated_at = now() WHERE id = v_job.id;

  -- In-transaction session rollup under the held canonical locks.
  PERFORM ewp_private.ewp_apply_session_rollup(v_session.id);

  RETURN jsonb_build_object(
    'status', 'completed', 'overall_status', 'completed',
    'unit_status', v_unit_target, 'has_unresolved_must_fix', v_has_must_fix,
    'resolved_count', v_resolved_count);
END;
$$;

-- ===========================================================================
-- Fail / retry a job. Under max_attempts → back to pending with backoff.
-- At max_attempts → terminal: language failed; deterministic-complete maps to
-- terminal_partial (unit ready, deterministic_only), else failed (unit
-- evaluation_failed). Rolls the session up either way.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_fail_evaluation_job(
  p_job_id uuid,
  p_claim_token uuid,
  p_error text,
  p_backoff_seconds int DEFAULT 60
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_job     public.writing_evaluation_jobs%ROWTYPE;
  v_eval    public.writing_evaluations%ROWTYPE;
  v_ver     public.writing_unit_versions%ROWTYPE;
  v_unit    public.writing_session_units%ROWTYPE;
  v_session public.writing_sessions%ROWTYPE;
  v_is_current boolean;
  v_maxver  int;
  v_terminal boolean;
  v_overall text;
  v_unit_target text;
BEGIN
  -- Resolve ids without locking, then take the canonical lock order (§8.0):
  -- session → all units ascending → evaluation → job.
  SELECT * INTO v_job FROM public.writing_evaluation_jobs WHERE id = p_job_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ewp_job_not_found: job % not found', p_job_id;
  END IF;
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_job.evaluation_id;
  SELECT * INTO v_ver  FROM public.writing_unit_versions WHERE id = v_eval.unit_version_id;
  SELECT * INTO v_unit FROM public.writing_session_units WHERE id = v_ver.unit_id;

  SELECT * INTO v_session FROM public.writing_sessions WHERE id = v_unit.session_id FOR UPDATE;
  PERFORM 1 FROM public.writing_session_units
    WHERE session_id = v_session.id ORDER BY unit_number FOR UPDATE;
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_job.evaluation_id FOR UPDATE;
  SELECT * INTO v_job  FROM public.writing_evaluation_jobs WHERE id = p_job_id FOR UPDATE;

  IF v_job.status <> 'running' OR v_job.claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'ewp_job_fencing_failed: job % is no longer owned by this claim', p_job_id;
  END IF;

  v_terminal := (v_job.attempts >= v_job.max_attempts);

  IF NOT v_terminal THEN
    -- Retry: release the lease, requeue with backoff, reset language to queued.
    UPDATE public.writing_evaluation_jobs SET
      status = 'pending', locked_at = NULL, claim_token = NULL,
      last_error = p_error, scheduled_for = now() + make_interval(secs => p_backoff_seconds),
      updated_at = now()
    WHERE id = v_job.id;
    UPDATE public.writing_evaluations SET language_status = 'queued', updated_at = now()
    WHERE id = v_job.evaluation_id AND language_status = 'running';
    RETURN jsonb_build_object('status','requeued','attempts',v_job.attempts);
  END IF;

  -- Terminal failure.
  SELECT MAX(version_number) INTO v_maxver
  FROM public.writing_unit_versions WHERE unit_id = v_unit.id;
  v_is_current := (v_ver.version_number = v_maxver);

  -- deterministic-complete → terminal_partial (usable), else failed.
  v_overall := CASE WHEN v_eval.deterministic_status = 'completed'
                    THEN 'terminal_partial' ELSE 'failed' END;

  UPDATE public.writing_evaluations SET
    language_status = 'failed', overall_status = v_overall, updated_at = now()
  WHERE id = v_eval.id;

  UPDATE public.writing_evaluation_jobs
  SET status = 'failed', locked_at = NULL, last_error = p_error, updated_at = now()
  WHERE id = v_job.id;

  IF v_is_current AND v_unit.status = 'evaluation_pending' THEN
    v_unit_target := CASE WHEN v_overall = 'terminal_partial' THEN 'ready' ELSE 'evaluation_failed' END;
    UPDATE public.writing_session_units SET status = v_unit_target WHERE id = v_unit.id;
  ELSE
    v_unit_target := v_unit.status;
  END IF;

  PERFORM ewp_private.ewp_apply_session_rollup(v_session.id);

  RETURN jsonb_build_object('status','failed_terminal','overall_status',v_overall,'unit_status',v_unit_target);
END;
$$;

-- ===========================================================================
-- Sweep stale leases: running jobs whose lease expired go back to pending so a
-- fresh worker can reclaim them (the reclaim mints a new token, fencing out the
-- stale worker's terminal write). §8.3.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_sweep_stale_evaluation_jobs(p_lease_seconds int DEFAULT 900)
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_swept int;
BEGIN
  WITH stale AS (
    UPDATE public.writing_evaluation_jobs j
    SET status = 'pending', locked_at = NULL, claim_token = NULL,
        last_error = 'lease_expired', updated_at = now()
    WHERE j.status = 'running'
      AND j.locked_at IS NOT NULL
      AND j.locked_at < now() - make_interval(secs => p_lease_seconds)
    RETURNING j.evaluation_id
  ),
  reset AS (
    UPDATE public.writing_evaluations e SET language_status = 'queued', updated_at = now()
    WHERE e.id IN (SELECT evaluation_id FROM stale) AND e.language_status = 'running'
    RETURNING 1
  )
  SELECT count(*)::int INTO v_swept FROM stale;
  RETURN v_swept;
END;
$$;

-- ===========================================================================
-- Mastery outbox drain (post-commit, §8.2). Claim one pending row and return
-- the deterministic context the worker re-derives evidence from.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_claim_mastery_outbox(p_lease_seconds int DEFAULT 900)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row     public.writing_mastery_outbox%ROWTYPE;
  v_eval    public.writing_evaluations%ROWTYPE;
  v_ver     public.writing_unit_versions%ROWTYPE;
  v_unit    public.writing_session_units%ROWTYPE;
  v_session public.writing_sessions%ROWTYPE;
  v_prompt  public.writing_prompts%ROWTYPE;
  v_must_fix boolean;
  v_resolved int;
BEGIN
  SELECT * INTO v_row FROM public.writing_mastery_outbox o
  WHERE o.status = 'pending'
  ORDER BY o.created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN RETURN NULL; END IF;

  UPDATE public.writing_mastery_outbox
  SET status = 'processing', locked_at = now(), attempts = attempts + 1
  WHERE id = v_row.id;

  IF v_row.source_kind <> 'evaluation' THEN
    -- review-correction outbox rows are an EWP-3 concern; ack as done (no-op).
    UPDATE public.writing_mastery_outbox SET status = 'done', processed_at = now() WHERE id = v_row.id;
    RETURN jsonb_build_object('id', v_row.id, 'skipped', true);
  END IF;

  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_row.evaluation_id;
  SELECT * INTO v_ver  FROM public.writing_unit_versions WHERE id = v_eval.unit_version_id;
  SELECT * INTO v_unit FROM public.writing_session_units WHERE id = v_ver.unit_id;
  SELECT * INTO v_session FROM public.writing_sessions WHERE id = v_unit.session_id;
  SELECT * INTO v_prompt FROM public.writing_prompts WHERE id = v_session.prompt_id;

  v_must_fix := EXISTS (
    SELECT 1 FROM public.writing_issue_events i
    WHERE i.evaluation_id = v_eval.id AND i.severity = 'must_fix' AND i.affects_current_state = TRUE);
  SELECT count(*)::int INTO v_resolved FROM public.writing_issue_resolution_events r
  WHERE r.resolving_evaluation_id = v_eval.id AND r.outcome = 'resolved';

  RETURN jsonb_build_object(
    'id', v_row.id, 'evidence_op', v_row.evidence_op, 'user_id', v_row.user_id,
    'mastery_flag_state', v_row.mastery_flag_state, 'idempotency_key', v_row.idempotency_key,
    'evaluation_id', v_eval.id, 'overall_status', v_eval.overall_status,
    'topic_id', v_prompt.topic_id, 'exam_id', v_prompt.exam_id,
    'microtopic_id', v_unit.practice_microtopic_id, 'source_entity_id', v_session.id,
    'has_unresolved_must_fix', v_must_fix, 'resolved_issue_count', v_resolved);
END;
$$;

-- Complete a mastery outbox row: write evidence + shadow idempotently, ack.
-- Shadow-only until Lane A clears; a 'live' flag still only writes evidence +
-- shadow here (the unified aggregator publish is a separate, gated step).
CREATE OR REPLACE FUNCTION public.ewp_complete_mastery_outbox(
  p_id uuid,
  p_evidence jsonb,   -- NULL when no evidence is warranted (row acked as done)
  p_shadow jsonb
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row public.writing_mastery_outbox%ROWTYPE;
BEGIN
  SELECT * INTO v_row FROM public.writing_mastery_outbox WHERE id = p_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ewp_outbox_not_found: %', p_id;
  END IF;
  IF v_row.status <> 'processing' THEN
    RAISE EXCEPTION 'ewp_outbox_not_claimed: % is not processing', p_id;
  END IF;

  IF p_evidence IS NOT NULL THEN
    INSERT INTO public.user_topic_mastery_evidence(
      user_id, exam_id, topic_id, microtopic_id, source_type, source_entity_id,
      evidence_tier, score, confidence, issue_projection_id, evidence_op,
      evidence_key, observed_at)
    VALUES (
      (p_evidence->>'user_id')::uuid, NULLIF(p_evidence->>'exam_id','')::uuid,
      (p_evidence->>'topic_id')::uuid, NULLIF(p_evidence->>'microtopic_id','')::uuid,
      p_evidence->>'source_type', (p_evidence->>'source_entity_id')::uuid,
      p_evidence->>'evidence_tier', NULLIF(p_evidence->>'score','')::numeric,
      NULLIF(p_evidence->>'confidence','')::numeric,
      NULLIF(p_evidence->>'issue_projection_id','')::uuid,
      COALESCE(p_evidence->>'evidence_op','assert'), p_evidence->>'evidence_key', now())
    ON CONFLICT (evidence_key) DO NOTHING;

    INSERT INTO public.writing_mastery_shadow(
      user_id, exam_id, topic_id, microtopic_id, source_type, source_entity_id,
      evaluation_id, issue_projection_id, evidence_tier, score, confidence,
      delta_json, evidence_key)
    VALUES (
      (p_shadow->>'user_id')::uuid, NULLIF(p_shadow->>'exam_id','')::uuid,
      (p_shadow->>'topic_id')::uuid, NULLIF(p_shadow->>'microtopic_id','')::uuid,
      p_shadow->>'source_type', (p_shadow->>'source_entity_id')::uuid,
      (p_shadow->>'evaluation_id')::uuid, NULLIF(p_shadow->>'issue_projection_id','')::uuid,
      p_shadow->>'evidence_tier', NULLIF(p_shadow->>'score','')::numeric,
      NULLIF(p_shadow->>'confidence','')::numeric,
      COALESCE(p_shadow->'delta_json','{}'::jsonb), p_shadow->>'evidence_key')
    ON CONFLICT (evidence_key) DO NOTHING;
  END IF;

  UPDATE public.writing_mastery_outbox SET status = 'done', processed_at = now() WHERE id = p_id;
  RETURN jsonb_build_object('status','done','wrote_evidence', p_evidence IS NOT NULL);
END;
$$;

CREATE OR REPLACE FUNCTION public.ewp_fail_mastery_outbox(
  p_id uuid, p_error text, p_backoff_seconds int DEFAULT 120
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row public.writing_mastery_outbox%ROWTYPE;
BEGIN
  SELECT * INTO v_row FROM public.writing_mastery_outbox WHERE id = p_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'ewp_outbox_not_found: %', p_id; END IF;
  IF v_row.attempts >= v_row.max_attempts THEN
    UPDATE public.writing_mastery_outbox SET status = 'failed', last_error = p_error, locked_at = NULL WHERE id = p_id;
    RETURN jsonb_build_object('status','failed_terminal');
  END IF;
  UPDATE public.writing_mastery_outbox SET status = 'pending', locked_at = NULL, last_error = p_error WHERE id = p_id;
  RETURN jsonb_build_object('status','requeued');
END;
$$;

-- ===========================================================================
-- grants — service_role only (the worker runs under the service role).
-- ===========================================================================
REVOKE ALL ON FUNCTION public.ewp_claim_evaluation_job(int, text[]) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_complete_language_evaluation(uuid,uuid,text,jsonb,jsonb,jsonb,boolean,text,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_fail_evaluation_job(uuid,uuid,text,int) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_sweep_stale_evaluation_jobs(int) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_claim_mastery_outbox(int) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_complete_mastery_outbox(uuid,jsonb,jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_fail_mastery_outbox(uuid,text,int) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_claim_evaluation_job(int, text[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_complete_language_evaluation(uuid,uuid,text,jsonb,jsonb,jsonb,boolean,text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_fail_evaluation_job(uuid,uuid,text,int) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_sweep_stale_evaluation_jobs(int) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_claim_mastery_outbox(int) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_complete_mastery_outbox(uuid,jsonb,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_fail_mastery_outbox(uuid,text,int) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
