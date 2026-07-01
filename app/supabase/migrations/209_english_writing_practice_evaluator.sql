-- Migration 209: English Writing Practice (EWP-2B) — async evaluator worker RPCs.
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
-- Migration number: highest on main is 208 (208_topic_prerequisite_lifecycle landed); this is 209.
-- VERIFY DB against schema_migrations before apply (OPERATOR).

CREATE SCHEMA IF NOT EXISTS ewp_private;  -- created in 205; defensive for isolation.

-- Fencing token for the mastery-outbox lease (§8.3): a claimed row carries a
-- token; completion/failure must present it, so a stale worker whose lease was
-- swept and reclaimed cannot double-apply. (writing_mastery_outbox is from 205.)
ALTER TABLE public.writing_mastery_outbox ADD COLUMN IF NOT EXISTS claim_token uuid;

-- ===========================================================================
-- Canonical error-type projection (§6). The mapping is FREQUENCY-DEPENDENT:
-- p_prior_count = 0 is a FIRST occurrence, > 0 is a REPEATED occurrence for the
-- same (user, microtopic, issue_type). Implements the §6 table EXACTLY:
--   article/preposition/modifier/pronoun_reference : first careless → repeat concept_gap
--   subject_verb_agreement/tense/sentence_fragment/run_on_sentence/cohesion/
--     logical_order                                  : concept_gap (both)
--   spelling                                         : first careless → repeat memory_gap
--   word_choice/collocation/redundancy/informal_usage: memory_gap (both)
--   punctuation                                      : first careless → repeat concept_gap
--   off_topic                                        : first misread_question → repeat concept_gap
--   word_limit                                       : time_management (both)
--   format_violation                                 : concept_gap (both)
--   anything else / unknown                          : NULL (never force a projection)
-- ===========================================================================
CREATE OR REPLACE FUNCTION ewp_private.ewp_canonical_error_type(p_issue_type text, p_prior_count int)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE p_issue_type
    WHEN 'article'            THEN CASE WHEN p_prior_count > 0 THEN 'concept_gap' ELSE 'careless' END
    WHEN 'preposition'        THEN CASE WHEN p_prior_count > 0 THEN 'concept_gap' ELSE 'careless' END
    WHEN 'modifier'           THEN CASE WHEN p_prior_count > 0 THEN 'concept_gap' ELSE 'careless' END
    WHEN 'pronoun_reference'  THEN CASE WHEN p_prior_count > 0 THEN 'concept_gap' ELSE 'careless' END
    WHEN 'subject_verb_agreement' THEN 'concept_gap'
    WHEN 'tense'              THEN 'concept_gap'
    WHEN 'sentence_fragment'  THEN 'concept_gap'
    WHEN 'run_on_sentence'    THEN 'concept_gap'
    WHEN 'cohesion'           THEN 'concept_gap'
    WHEN 'logical_order'      THEN 'concept_gap'
    WHEN 'spelling'           THEN CASE WHEN p_prior_count > 0 THEN 'memory_gap' ELSE 'careless' END
    WHEN 'word_choice'        THEN 'memory_gap'
    WHEN 'collocation'        THEN 'memory_gap'
    WHEN 'redundancy'         THEN 'memory_gap'
    WHEN 'informal_usage'     THEN 'memory_gap'
    WHEN 'punctuation'        THEN CASE WHEN p_prior_count > 0 THEN 'concept_gap' ELSE 'careless' END
    WHEN 'off_topic'          THEN CASE WHEN p_prior_count > 0 THEN 'concept_gap' ELSE 'misread_question' END
    WHEN 'word_limit'         THEN 'time_management'
    WHEN 'format_violation'   THEN 'concept_gap'
    ELSE NULL
  END
$$;
REVOKE ALL ON FUNCTION ewp_private.ewp_canonical_error_type(text, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ewp_private.ewp_canonical_error_type(text, int) TO service_role;

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
  v_canonical text;
  v_regressed_lineage uuid;
  v_regressed_pred uuid;
  v_reg record;
BEGIN
  -- Regression tracking (§4.9 'regressed'): per-issue-event ephemeral map of
  -- which newly-inserted current-version issues re-opened a previously RESOLVED
  -- lineage of THIS unit, so a resolution event with outcome 'regressed' can be
  -- emitted (successor = the new issue) after all issue rows exist.
  CREATE TEMP TABLE IF NOT EXISTS _ewp_regressions(
    new_issue_id uuid, resolved_issue_id uuid, lineage_id uuid) ON COMMIT DROP;
  DELETE FROM _ewp_regressions;
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
    v_regressed_lineage := NULL;   -- reset per iteration (see regression block below)
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
      -- No predecessor supplied. Before minting a fresh lineage, check whether
      -- this issue REGRESSES a previously-resolved lineage of THIS unit (§4.9):
      -- match by issue_type against a resolved lineage whose latest issue is not
      -- effectively invalidated and which has not already been re-opened by an
      -- earlier issue in this same evaluation. Reuse that resolved lineage id and
      -- point the predecessor at the latest resolved issue (append-only: the
      -- lineage is assigned on the new row at INSERT time).
      v_regressed_lineage := NULL;
      v_regressed_pred := NULL;
      IF v_is_current THEN
        SELECT r.lineage_id, r.latest_issue_id INTO v_regressed_lineage, v_regressed_pred
        FROM (
          SELECT i.lineage_id,
                 (array_agg(i.id ORDER BY i.created_at DESC, i.id DESC))[1] AS latest_issue_id,
                 max(i.issue_type) AS issue_type
          FROM public.writing_issue_resolution_events rr
          JOIN public.writing_issue_events i ON i.id = rr.issue_event_id
          JOIN public.writing_evaluations e2 ON e2.id = i.evaluation_id
          JOIN public.writing_unit_versions v2 ON v2.id = e2.unit_version_id
          WHERE v2.unit_id = v_unit.id AND rr.outcome = 'resolved'
            AND NOT ewp_private.ewp_issue_effectively_invalidated(i.id)
          GROUP BY i.lineage_id
        ) r
        WHERE r.issue_type = (v_issue->>'issue_type')
          AND r.lineage_id NOT IN (SELECT lineage_id FROM _ewp_regressions)
        LIMIT 1;
      END IF;

      IF v_regressed_lineage IS NOT NULL THEN
        v_lineage := v_regressed_lineage;
        v_pred := v_regressed_pred;   -- link the new issue back to the resolved one
      ELSE
        v_lineage := gen_random_uuid();
      END IF;
    END IF;

    -- Resolve microtopic via the active map, then VALIDATE the mapped target is a
    -- live English microtopic (§5.3, §4.15). The mapped topic must be level
    -- 'microtopic', active, AND inside the ENGLISH subject tree (subjects.slug =
    -- 'english-language'). A map row pointing OUTSIDE English (or at a
    -- non-microtopic / inactive topic) is not trusted → topic-level (NULL) instead
    -- of a bad id, so a mis-seeded/remapped row can never attach evidence to a
    -- foreign subject.
    SELECT m.microtopic_id INTO v_microtopic
    FROM public.writing_issue_type_microtopic_map m
    JOIN public.topics t ON t.id = m.microtopic_id
    JOIN public.subjects sub ON sub.id = t.subject_id
    WHERE m.issue_type = (v_issue->>'issue_type') AND m.is_active = TRUE
      AND t.level = 'microtopic' AND t.is_active = TRUE
      AND sub.slug = 'english-language'
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

    IF v_regressed_lineage IS NOT NULL AND v_is_current THEN
      INSERT INTO _ewp_regressions(new_issue_id, resolved_issue_id, lineage_id)
      VALUES (v_new_issue_id, v_regressed_pred, v_regressed_lineage);
    END IF;

    IF (v_issue->>'severity') = 'must_fix' AND v_is_current THEN
      v_has_must_fix := TRUE;
    END IF;

    -- Projections + prior-occurrence counting are CURRENT-STATE only: a stale
    -- (superseded) re-evaluation records the issue event (affects_current_state
    -- = false, above) but must not create projections or inflate the count (§8.1).
    IF v_is_current THEN
      -- Race-safe count: advisory xact lock on (user, microtopic, issue_type),
      -- held across read+insert; the count is scoped to the same key.
      PERFORM pg_advisory_xact_lock(
        hashtext(v_session.user_id::text || ':' ||
                 COALESCE(v_microtopic::text,'-') || ':' || (v_issue->>'issue_type')));
      -- Prior-occurrence count (§6): only CURRENT-STATE issues that are not
      -- effectively invalidated count. Stale (affects_current_state=false) rows and
      -- rows withdrawn by a review event must not inflate the first-vs-repeat count.
      SELECT count(*) INTO v_count
      FROM public.writing_issue_events i2
      JOIN public.writing_evaluations e3 ON e3.id = i2.evaluation_id
      JOIN public.writing_unit_versions v3 ON v3.id = e3.unit_version_id
      JOIN public.writing_session_units u3 ON u3.id = v3.unit_id
      JOIN public.writing_sessions s3 ON s3.id = u3.session_id
      WHERE s3.user_id = v_session.user_id
        AND i2.issue_type = (v_issue->>'issue_type')
        AND i2.microtopic_id IS NOT DISTINCT FROM v_microtopic
        AND i2.id <> v_new_issue_id
        AND i2.affects_current_state = TRUE
        AND NOT ewp_private.ewp_issue_effectively_invalidated(i2.id);

      -- Canonical error type per the §6 frequency-dependent table (first vs repeat
      -- decided by v_count). Confidence is null when the type is unprojectable.
      v_canonical := ewp_private.ewp_canonical_error_type(v_issue->>'issue_type', v_count);

      INSERT INTO public.writing_issue_projections(
        issue_event_id, projection_revision, projection_kind, prior_occurrence_count,
        canonical_error_type, projection_confidence, rationale)
      VALUES (v_new_issue_id, v_session.projection_revision, 'automatic', v_count,
              v_canonical, CASE WHEN v_canonical IS NULL THEN NULL ELSE 0.6 END,
              'auto:' || (v_issue->>'issue_type'))
      ON CONFLICT (issue_event_id, projection_revision)
        WHERE projection_kind = 'automatic' DO NOTHING;
    END IF;
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
      -- The fallback match MUST carry the SAME lineage as the prior issue: a new
      -- issue that merely shares type+quote but was minted with a fresh lineage
      -- (or re-opened a DIFFERENT resolved lineage) is NOT this issue's successor,
      -- so pointing 'persisted' at it would fork the lineage. Guarding on
      -- lineage_id keeps 'persisted' successors on the prior's lineage.
      SELECT id INTO v_new_issue FROM public.writing_issue_events
      WHERE evaluation_id = v_eval.id
        AND (predecessor_issue_event_id = v_pred
             OR (issue_type = v_pred_type AND quoted_text IS NOT DISTINCT FROM v_pred_quote
                 AND lineage_id = v_lineage))
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

    -- Regression events (§4.9 'regressed'): a lineage resolved in a PRIOR version
    -- of this unit re-appeared in this rewrite. The reappearing issue was assigned
    -- the resolved lineage id at INSERT time; here we record one resolution event
    -- with outcome 'regressed', keyed on the latest resolved issue of that lineage
    -- (issue_event_id) with the new issue as successor. Because the reappearing
    -- issue is NOT in ewp_prior_active_issues (that set is version N-1 unresolved
    -- only), the persist/resolve loop above never touched it — no double event.
    FOR v_reg IN SELECT * FROM _ewp_regressions LOOP
      INSERT INTO public.writing_issue_resolution_events(
        issue_event_id, resolving_version_id, resolving_evaluation_id,
        successor_issue_event_id, outcome, evaluator_version)
      VALUES (
        v_reg.resolved_issue_id, v_ver.id, v_eval.id, v_reg.new_issue_id,
        'regressed', p_evaluator_version)
      ON CONFLICT (issue_event_id, resolving_version_id, evaluator_version) DO NOTHING;
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
  SET status = 'done', locked_at = NULL, claim_token = NULL, updated_at = now() WHERE id = v_job.id;

  -- Finalize only for the current version. A stale (superseded) re-evaluation
  -- persisted its envelope + issue events and acked the job, but must not drive
  -- the session state, which belongs to the current version (§8.1 stale path).
  IF v_is_current THEN
    PERFORM ewp_private.ewp_apply_session_rollup(v_session.id);
  END IF;

  RETURN jsonb_build_object(
    'status', 'completed', 'overall_status', 'completed',
    'unit_status', v_unit_target, 'has_unresolved_must_fix', v_has_must_fix,
    'resolved_count', v_resolved_count);
END;
$$;

-- ===========================================================================
-- Private: terminalise a failed evaluation job. Single owner of the terminal
-- transition — called by ewp_fail_evaluation_job (attempts exhausted) and by
-- the stale-lease sweeper (a crashed job whose attempts are exhausted). Takes
-- the canonical locks itself so both callers are safe. deterministic-complete
-- → terminal_partial (unit ready), else failed (unit evaluation_failed).
-- ===========================================================================
CREATE OR REPLACE FUNCTION ewp_private.ewp_terminalize_eval_job(p_job_id uuid, p_error text)
RETURNS jsonb
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
  v_maxver  int;
  v_is_current boolean;
  v_overall text;
  v_unit_target text;
BEGIN
  SELECT * INTO v_job FROM public.writing_evaluation_jobs WHERE id = p_job_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'ewp_job_not_found: job % not found', p_job_id; END IF;
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_job.evaluation_id;
  SELECT * INTO v_ver  FROM public.writing_unit_versions WHERE id = v_eval.unit_version_id;
  SELECT * INTO v_unit FROM public.writing_session_units WHERE id = v_ver.unit_id;

  SELECT * INTO v_session FROM public.writing_sessions WHERE id = v_unit.session_id FOR UPDATE;
  PERFORM 1 FROM public.writing_session_units
    WHERE session_id = v_session.id ORDER BY unit_number FOR UPDATE;
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_job.evaluation_id FOR UPDATE;
  SELECT * INTO v_job  FROM public.writing_evaluation_jobs WHERE id = p_job_id FOR UPDATE;

  SELECT MAX(version_number) INTO v_maxver
  FROM public.writing_unit_versions WHERE unit_id = v_unit.id;
  v_is_current := (v_ver.version_number = v_maxver);

  v_overall := CASE WHEN v_eval.deterministic_status = 'completed'
                    THEN 'terminal_partial' ELSE 'failed' END;

  UPDATE public.writing_evaluations SET
    language_status = 'failed', overall_status = v_overall, updated_at = now()
  WHERE id = v_eval.id;
  UPDATE public.writing_evaluation_jobs
  SET status = 'failed', locked_at = NULL, claim_token = NULL, last_error = p_error, updated_at = now()
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
-- Private: sweep-safe requeue/terminalise of ONE stale-lease job. Acquires the
-- canonical locks SESSION-FIRST (§8.0), then RE-VALIDATES under those locks that
-- the job is still 'running' with an expired lease before acting. This makes the
-- sweeper race-safe against a completing worker and against a second sweeper
-- without holding a job-before-session lock: the pre-read that fed us this id may
-- be stale (the worker committed, or another sweeper acted) — we simply no-op.
-- Non-blocking like SKIP LOCKED: a job whose session is currently locked by a
-- committing worker will serialize behind that lock and then fail re-validation
-- (the worker moved the job to 'done'/'failed'), so we no-op — never double-act.
-- ===========================================================================
CREATE OR REPLACE FUNCTION ewp_private.ewp_requeue_stale_eval_job(p_job_id uuid, p_lease_seconds int)
RETURNS jsonb
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
BEGIN
  -- Resolve ids WITHOUT locking, then lock session-first.
  SELECT * INTO v_job FROM public.writing_evaluation_jobs WHERE id = p_job_id;
  IF NOT FOUND THEN RETURN jsonb_build_object('acted','false','reason','gone'); END IF;
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_job.evaluation_id;
  SELECT * INTO v_ver  FROM public.writing_unit_versions WHERE id = v_eval.unit_version_id;
  SELECT * INTO v_unit FROM public.writing_session_units WHERE id = v_ver.unit_id;

  SELECT * INTO v_session FROM public.writing_sessions WHERE id = v_unit.session_id FOR UPDATE;
  PERFORM 1 FROM public.writing_session_units
    WHERE session_id = v_session.id ORDER BY unit_number FOR UPDATE;
  SELECT * INTO v_job FROM public.writing_evaluation_jobs WHERE id = p_job_id FOR UPDATE;

  -- Re-validate under the session+job locks: still running with an expired lease?
  -- A racing completion (job now 'done'/'failed') or a peer sweeper that already
  -- reset it (locked_at NULL / lease fresh) fails this guard → no-op.
  IF v_job.status <> 'running'
     OR v_job.locked_at IS NULL
     OR v_job.locked_at >= now() - make_interval(secs => p_lease_seconds) THEN
    RETURN jsonb_build_object('acted','false','reason','revalidation_failed');
  END IF;

  IF v_job.attempts >= v_job.max_attempts THEN
    -- Exhausted crash: terminalise (helper re-takes the same locks re-entrantly).
    PERFORM ewp_private.ewp_terminalize_eval_job(v_job.id, 'lease_expired_exhausted');
  ELSE
    UPDATE public.writing_evaluation_jobs
    SET status = 'pending', locked_at = NULL, claim_token = NULL,
        last_error = 'lease_expired', updated_at = now()
    WHERE id = v_job.id;
    UPDATE public.writing_evaluations SET language_status = 'queued', updated_at = now()
    WHERE id = v_job.evaluation_id AND language_status = 'running';
  END IF;
  RETURN jsonb_build_object('acted','true');
END;
$$;

-- ===========================================================================
-- Fail / retry a job. Under max_attempts → back to pending with backoff.
-- At max_attempts → terminal via ewp_private.ewp_terminalize_eval_job.
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

  -- Terminal failure — the single owner of the terminal transition is the
  -- private helper (also used by the sweeper for exhausted leases).
  RETURN ewp_private.ewp_terminalize_eval_job(v_job.id, p_error);
END;
$$;

-- ===========================================================================
-- Generation+1 recovery (§4.14 / §8.3). For an evaluation whose LATEST job is
-- terminally 'failed', mint a fresh generation+1 pending job (attempts=0) and CAS
-- the evaluation's language_status failed → queued. The unique(evaluation_id,
-- job_kind, generation) + the partial-unique active-job index guarantee that two
-- racing recoverers cannot both insert; the loser's INSERT conflicts and the CAS
-- is a no-op. A completed language result is never overwritten (guarded below).
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_recover_evaluation(p_evaluation uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_eval    public.writing_evaluations%ROWTYPE;
  v_ver     public.writing_unit_versions%ROWTYPE;
  v_unit    public.writing_session_units%ROWTYPE;
  v_session public.writing_sessions%ROWTYPE;
  v_job     public.writing_evaluation_jobs%ROWTYPE;
  v_new_gen int;
  v_new_job uuid;
BEGIN
  -- Canonical lock order (§8.0): session → all units ascending → evaluation.
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = p_evaluation;
  IF NOT FOUND THEN RAISE EXCEPTION 'ewp_evaluation_not_found: %', p_evaluation; END IF;
  SELECT * INTO v_ver  FROM public.writing_unit_versions WHERE id = v_eval.unit_version_id;
  SELECT * INTO v_unit FROM public.writing_session_units WHERE id = v_ver.unit_id;
  SELECT * INTO v_session FROM public.writing_sessions WHERE id = v_unit.session_id FOR UPDATE;
  PERFORM 1 FROM public.writing_session_units
    WHERE session_id = v_session.id ORDER BY unit_number FOR UPDATE;
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = p_evaluation FOR UPDATE;

  -- A completed language result is never recovered over (§4.14).
  IF v_eval.language_status = 'completed' THEN
    RETURN jsonb_build_object('status','noop','reason','language_completed');
  END IF;

  -- The latest language job must be terminally failed to recover it.
  SELECT * INTO v_job FROM public.writing_evaluation_jobs
  WHERE evaluation_id = p_evaluation AND job_kind = 'language_evaluation'
  ORDER BY generation DESC LIMIT 1;
  IF NOT FOUND THEN RAISE EXCEPTION 'ewp_no_job: no language job for %', p_evaluation; END IF;
  IF v_job.status <> 'failed' THEN
    RETURN jsonb_build_object('status','noop','reason','latest_job_not_failed',
                              'job_status', v_job.status);
  END IF;

  v_new_gen := v_job.generation + 1;

  -- Insert the fresh generation. The unique(evaluation_id, job_kind, generation)
  -- and partial-unique active-job index protect against duplicate recovery.
  INSERT INTO public.writing_evaluation_jobs(
    evaluation_id, job_kind, generation, status, attempts, max_attempts, created_at, updated_at)
  VALUES (p_evaluation, 'language_evaluation', v_new_gen, 'pending', 0, v_job.max_attempts, now(), now())
  ON CONFLICT (evaluation_id, job_kind, generation) DO NOTHING
  RETURNING id INTO v_new_job;

  IF v_new_job IS NULL THEN
    RETURN jsonb_build_object('status','noop','reason','generation_exists','generation',v_new_gen);
  END IF;

  -- CAS language_status failed → queued (never overwrite a completed result).
  UPDATE public.writing_evaluations SET language_status = 'queued', updated_at = now()
  WHERE id = p_evaluation AND language_status = 'failed';

  RETURN jsonb_build_object('status','recovered','job_id',v_new_job,'generation',v_new_gen);
END;
$$;

-- ===========================================================================
-- CORRUPTION HARD-FAIL (§8.1 step 2 / fail-closed). When the worker recomputes
-- the stored answer's content_hash and it does NOT match the version's recorded
-- hash, the row is corrupt/tampered and must NEVER be scored. This is a DISTINCT
-- terminal path from ewp_fail_evaluation_job: a corrupt version can never become
-- a usable result. Regardless of deterministic_status it forces
-- overall_status='failed' (NOT terminal_partial/ready) and the unit to
-- 'evaluation_failed'. It does NOT count as a recoverable attempt — recovery
-- would re-read the same corrupt bytes — so the job is set 'failed' immediately
-- (attempts untouched). Fenced by claim_token like the other terminal writes.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_reject_corrupt_version(
  p_job_id uuid,
  p_claim_token uuid,
  p_error text DEFAULT 'content_hash_mismatch'
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
  v_maxver  int;
  v_is_current boolean;
  v_unit_target text;
BEGIN
  SELECT * INTO v_job FROM public.writing_evaluation_jobs WHERE id = p_job_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'ewp_job_not_found: job % not found', p_job_id; END IF;
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

  SELECT MAX(version_number) INTO v_maxver
  FROM public.writing_unit_versions WHERE unit_id = v_unit.id;
  v_is_current := (v_ver.version_number = v_maxver);

  -- Fail CLOSED regardless of deterministic_status: a corrupt version is never a
  -- usable result. overall_status='failed' (never terminal_partial), unit
  -- 'evaluation_failed' (never ready).
  UPDATE public.writing_evaluations SET
    language_status = 'failed', overall_status = 'failed', updated_at = now()
  WHERE id = v_eval.id;
  UPDATE public.writing_evaluation_jobs
  SET status = 'failed', locked_at = NULL, claim_token = NULL, last_error = p_error, updated_at = now()
  WHERE id = v_job.id;

  IF v_is_current AND v_unit.status = 'evaluation_pending' THEN
    v_unit_target := 'evaluation_failed';
    UPDATE public.writing_session_units SET status = 'evaluation_failed' WHERE id = v_unit.id;
  ELSE
    v_unit_target := v_unit.status;
  END IF;

  PERFORM ewp_private.ewp_apply_session_rollup(v_session.id);
  RETURN jsonb_build_object('status','rejected_corrupt','overall_status','failed','unit_status',v_unit_target);
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
  v_swept int := 0;
  v_id    uuid;
  v_res   jsonb;
BEGIN
  -- Select candidate stale job IDS with a PLAIN read (NO row lock). Taking a job
  -- row lock here and THEN calling a helper that locks session→units→eval→job
  -- would invert the canonical order (§8.0: session-first) and can deadlock a
  -- racing completion. Instead the per-job requeue helper acquires locks
  -- session-first and RE-VALIDATES the running+expired-lease precondition under
  -- those locks, so a concurrent completion or a second sweeper is safe (a plain
  -- pre-read that is stale by the time the lock is taken simply no-ops).
  FOR v_id IN
    SELECT id FROM public.writing_evaluation_jobs
    WHERE status = 'running'
      AND locked_at IS NOT NULL
      AND locked_at < now() - make_interval(secs => p_lease_seconds)
  LOOP
    v_res := ewp_private.ewp_requeue_stale_eval_job(v_id, p_lease_seconds);
    IF COALESCE(v_res->>'acted','false') = 'true' THEN
      v_swept := v_swept + 1;
    END IF;
  END LOOP;
  RETURN v_swept;
END;
$$;

-- ===========================================================================
-- Mastery outbox drain (post-commit, §8.2). Claim one pending EVALUATION row
-- (review-correction rows are left pending until the EWP-3 correction handler
-- exists — never falsely acked) and return the deterministic context the worker
-- re-derives evidence from. Stamps a lease + fencing token.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_claim_mastery_outbox(p_lease_seconds int DEFAULT 900)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row     public.writing_mastery_outbox%ROWTYPE;
  v_token   uuid := gen_random_uuid();
  v_eval    public.writing_evaluations%ROWTYPE;
  v_ver     public.writing_unit_versions%ROWTYPE;
  v_unit    public.writing_session_units%ROWTYPE;
  v_session public.writing_sessions%ROWTYPE;
  v_prompt  public.writing_prompts%ROWTYPE;
  v_must_fix boolean;
  v_resolved int;
  v_projs   jsonb;
BEGIN
  SELECT * INTO v_row FROM public.writing_mastery_outbox o
  WHERE o.status = 'pending' AND o.source_kind = 'evaluation'
  ORDER BY o.created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN RETURN NULL; END IF;

  UPDATE public.writing_mastery_outbox
  SET status = 'processing', locked_at = now(), claim_token = v_token, attempts = attempts + 1
  WHERE id = v_row.id;

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

  -- Per-issue projection-linked evidence context (§4.12/§4.12a/§10.1). POSITIVE
  -- tiers require the aspirant to DEMONSTRATE the tier; the mere presence of an
  -- active/unresolved error (esp. must_fix) is a WEAKNESS, not a demonstration,
  -- and MUST NOT earn positive evidence (§4.12a). The architecture defines no
  -- negative "error observation" evidence record — so an active error emits
  -- NOTHING here. The ONLY positive projection-linked row emitted for an issue is
  -- a 'correction' (§4.12a: "aspirant corrected a supplied incorrect sentence")
  -- for a lineage the aspirant actually RESOLVED in THIS evaluation — i.e. a
  -- resolution event with outcome='resolved' whose resolving_evaluation_id is
  -- this evaluation. The row is linked to the RESOLVED (prior-version) issue's
  -- automatic projection so a later false-positive review can retract/replace it
  -- (§4.12c). A resolved issue that was itself review-invalidated earns nothing.
  SELECT COALESCE(jsonb_agg(jsonb_build_object(
    'issue_projection_id', pr.id,
    'microtopic_id', ie.microtopic_id,
    'issue_type', ie.issue_type,
    'evidence_tier', 'correction'
  ) ORDER BY pr.created_at, pr.id), '[]'::jsonb) INTO v_projs
  FROM public.writing_issue_resolution_events r
  JOIN public.writing_issue_events ie ON ie.id = r.issue_event_id
  JOIN public.writing_issue_projections pr
    ON pr.issue_event_id = ie.id AND pr.projection_kind = 'automatic'
  WHERE r.resolving_evaluation_id = v_eval.id
    AND r.outcome = 'resolved'
    AND ie.affects_current_state = TRUE
    AND NOT ewp_private.ewp_issue_effectively_invalidated(ie.id);

  RETURN jsonb_build_object(
    'id', v_row.id, 'claim_token', v_token, 'evidence_op', v_row.evidence_op, 'user_id', v_row.user_id,
    'mastery_flag_state', v_row.mastery_flag_state, 'idempotency_key', v_row.idempotency_key,
    'evaluation_id', v_eval.id, 'overall_status', v_eval.overall_status,
    'topic_id', v_prompt.topic_id, 'exam_id', v_prompt.exam_id, 'exercise_type', v_prompt.exercise_type,
    'microtopic_id', v_unit.practice_microtopic_id, 'source_entity_id', v_session.id,
    'has_unresolved_must_fix', v_must_fix, 'resolved_issue_count', v_resolved,
    'issue_projections', v_projs);
END;
$$;

-- Reclaim mastery-outbox rows whose lease expired (crash after claim). Exhausted
-- rows terminalise to 'failed'; others go back to 'pending' for a fresh claim.
CREATE OR REPLACE FUNCTION public.ewp_sweep_stale_mastery_outbox(p_lease_seconds int DEFAULT 900)
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_swept int := 0;
  v_r record;
BEGIN
  FOR v_r IN
    SELECT id, attempts, max_attempts FROM public.writing_mastery_outbox
    WHERE status = 'processing' AND locked_at IS NOT NULL
      AND locked_at < now() - make_interval(secs => p_lease_seconds)
    FOR UPDATE SKIP LOCKED
  LOOP
    IF v_r.attempts >= v_r.max_attempts THEN
      UPDATE public.writing_mastery_outbox
      SET status = 'failed', locked_at = NULL, claim_token = NULL, last_error = 'lease_expired_exhausted'
      WHERE id = v_r.id;
    ELSE
      UPDATE public.writing_mastery_outbox
      SET status = 'pending', locked_at = NULL, claim_token = NULL, last_error = 'lease_expired'
      WHERE id = v_r.id;
    END IF;
    v_swept := v_swept + 1;
  END LOOP;
  RETURN v_swept;
END;
$$;

-- Evidence-key layout mirrored from Python (evidence_deriver.compute_evidence_key,
-- §4.12b): SHA-256 of the 8 identity fields joined by a single NUL byte, in order,
-- with the documented coalesce sentinels. Keeping this in SQL lets the outbox
-- completion RE-DERIVE and verify the claimed key rather than trust the worker.
CREATE OR REPLACE FUNCTION ewp_private.ewp_compute_evidence_key(
  p_evidence_op text, p_user_id uuid, p_evaluation_id uuid,
  p_issue_projection_id uuid, p_microtopic_id uuid, p_evidence_tier text,
  p_source_type text, p_review_event_id uuid)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  -- Build the payload as bytea: each field's UTF-8 bytes joined by a single NUL
  -- byte ('\x00'::bytea). A text NUL cannot be represented, so we concatenate
  -- bytea (matching Python's b"\x00".join(f.encode("utf-8") ...) exactly).
  SELECT encode(sha256(
    convert_to(p_evidence_op, 'UTF8') || '\x00'::bytea ||
    convert_to(p_user_id::text, 'UTF8') || '\x00'::bytea ||
    convert_to(p_evaluation_id::text, 'UTF8') || '\x00'::bytea ||
    convert_to(COALESCE(p_issue_projection_id::text, 'no_projection'), 'UTF8') || '\x00'::bytea ||
    convert_to(COALESCE(p_microtopic_id::text, 'no_microtopic'), 'UTF8') || '\x00'::bytea ||
    convert_to(p_evidence_tier, 'UTF8') || '\x00'::bytea ||
    convert_to(p_source_type, 'UTF8') || '\x00'::bytea ||
    convert_to(COALESCE(p_review_event_id::text, 'no_review'), 'UTF8')
  ), 'hex')
$$;

-- Canonical context for an outbox row, re-derived from the committed evaluation
-- (NOT trusted from the worker). Mirrors the ewp_claim_mastery_outbox derivation:
-- topic/microtopic/source_type/source_entity from the prompt+unit+session, so the
-- completion can assert every payload identity field equals the claimed context.
CREATE OR REPLACE FUNCTION ewp_private.ewp_outbox_evidence_context(p_outbox uuid)
RETURNS TABLE(user_id uuid, evaluation_id uuid, topic_id uuid, microtopic_id uuid,
              exam_id uuid, source_type text, source_entity_id uuid)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT o.user_id, e.id, p.topic_id, u.practice_microtopic_id, p.exam_id,
         CASE
           WHEN p.exercise_type IN ('sentence_construction','sentence_correction',
                'sentence_rewrite','sentence_reconstruction','vocabulary_in_context')
             THEN 'sentence_drill'
           WHEN p.exercise_type IN ('paragraph_writing','summary_writing',
                'precis_practice','essay_practice','letter_practice')
             THEN 'paragraph_drill'
           ELSE 'descriptive_mock'
         END,
         s.id
  FROM public.writing_mastery_outbox o
  JOIN public.writing_evaluations e ON e.id = o.evaluation_id
  JOIN public.writing_unit_versions v ON v.id = e.unit_version_id
  JOIN public.writing_session_units u ON u.id = v.unit_id
  JOIN public.writing_sessions s ON s.id = u.session_id
  JOIN public.writing_prompts p ON p.id = s.prompt_id
  WHERE o.id = p_outbox;
$$;

-- Complete a mastery outbox row: write evidence + shadow idempotently, ack.
-- Fencing (claim_token) + payload validation against the claimed row prevent a
-- stale/buggy worker from writing cross-user/eval evidence. Shadow-only until
-- Lane A clears; a 'live' flag still only writes evidence + shadow here.
CREATE OR REPLACE FUNCTION public.ewp_complete_mastery_outbox(
  p_id uuid,
  p_claim_token uuid,
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
  IF v_row.status <> 'processing' OR v_row.claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'ewp_outbox_fencing_failed: % is not owned by this claim', p_id;
  END IF;

  IF p_evidence IS NOT NULL THEN
    -- Re-derive the canonical context for this outbox row from the COMMITTED
    -- evaluation (never trusted from the worker) and bind EVERY identity field of
    -- the payload to it. topic/microtopic/source_type/source_entity/exam come from
    -- the derived context; user/evaluation/op from the claimed row; and — the
    -- strongest binding — the evidence_key is RECOMPUTED from (op, user, eval,
    -- projection, microtopic, tier, source_type) and must equal both the payload
    -- key AND the claimed idempotency_key. A buggy/hostile worker cannot smuggle a
    -- mismatched tier, projection, microtopic, source_type, or cross-entity target.
    DECLARE
      v_ctx        record;
      v_ev_op      text := COALESCE(p_evidence->>'evidence_op','assert');
      v_ev_tier    text := p_evidence->>'evidence_tier';
      v_ev_proj    uuid := NULLIF(p_evidence->>'issue_projection_id','')::uuid;
      v_ev_micro   uuid := NULLIF(p_evidence->>'microtopic_id','')::uuid;
      v_ev_review  uuid := NULLIF(p_evidence->>'review_event_id','')::uuid;
      v_derived_key text;
    BEGIN
      SELECT * INTO v_ctx FROM ewp_private.ewp_outbox_evidence_context(p_id);

      v_derived_key := ewp_private.ewp_compute_evidence_key(
        v_ev_op, v_ctx.user_id, v_ctx.evaluation_id, v_ev_proj, v_ev_micro,
        v_ev_tier, v_ctx.source_type, v_ev_review);

      IF (p_evidence->>'user_id')::uuid <> v_row.user_id
         OR (p_evidence->>'evaluation_id')::uuid IS DISTINCT FROM v_row.evaluation_id
         OR (p_evidence->>'evidence_key') <> v_row.idempotency_key
         OR v_ev_op <> v_row.evidence_op
         OR (p_shadow->>'evidence_key') <> v_row.idempotency_key
         OR (p_shadow->>'user_id')::uuid <> v_row.user_id
         -- identity fields must equal the re-derived context (not worker-asserted)
         OR (p_evidence->>'topic_id')::uuid IS DISTINCT FROM v_ctx.topic_id
         OR v_ev_micro IS DISTINCT FROM v_ctx.microtopic_id
         OR (p_evidence->>'source_type') <> v_ctx.source_type
         OR (p_evidence->>'source_entity_id')::uuid IS DISTINCT FROM v_ctx.source_entity_id
         OR NULLIF(p_evidence->>'exam_id','')::uuid IS DISTINCT FROM v_ctx.exam_id
         -- the shadow's own evaluation_id / tier must agree too
         OR (p_shadow->>'evaluation_id')::uuid IS DISTINCT FROM v_row.evaluation_id
         OR (p_shadow->>'evidence_tier') <> v_ev_tier
         OR (p_shadow->>'topic_id')::uuid IS DISTINCT FROM v_ctx.topic_id
         -- best binding: recomputed key must equal the claimed/payload key
         OR v_derived_key <> v_row.idempotency_key THEN
        RAISE EXCEPTION 'ewp_outbox_payload_mismatch: evidence/shadow does not match the claimed row %', p_id;
      END IF;
    END;

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
  p_id uuid, p_claim_token uuid, p_error text, p_backoff_seconds int DEFAULT 120
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
  IF v_row.status <> 'processing' OR v_row.claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'ewp_outbox_fencing_failed: % is not owned by this claim', p_id;
  END IF;
  IF v_row.attempts >= v_row.max_attempts THEN
    UPDATE public.writing_mastery_outbox
    SET status = 'failed', last_error = p_error, locked_at = NULL, claim_token = NULL WHERE id = p_id;
    RETURN jsonb_build_object('status','failed_terminal');
  END IF;
  UPDATE public.writing_mastery_outbox
  SET status = 'pending', locked_at = NULL, claim_token = NULL, last_error = p_error WHERE id = p_id;
  RETURN jsonb_build_object('status','requeued');
END;
$$;

-- ===========================================================================
-- Batch completion for the mastery drain (§4.12/§10.1). Writes the unit-level
-- row AND one projection-linked row per current-state automatic issue projection
-- in ONE transaction, each validated against the claimed outbox row + the
-- re-derived evaluation context (never trusted from the worker), each idempotent
-- via ON CONFLICT (evidence_key) DO NOTHING. p_pairs = jsonb array of
-- {evidence:{...}, shadow:{...}} objects; NULL/empty acks the row as a no-op.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_complete_mastery_outbox_batch(
  p_id uuid,
  p_claim_token uuid,
  p_pairs jsonb   -- array of {evidence, shadow}; NULL/[] => ack no-op
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row     public.writing_mastery_outbox%ROWTYPE;
  v_ctx     record;
  v_eval    public.writing_evaluations%ROWTYPE;
  v_must_fix boolean;
  v_resolved int;
  v_unit_tier text;
  v_pair    jsonb;
  v_ev      jsonb;
  v_sh      jsonb;
  v_op      text;
  v_tier    text;
  v_proj    uuid;
  v_micro   uuid;
  v_key     text;
  v_wrote   int := 0;
  v_expected int;
  v_exp     record;
BEGIN
  SELECT * INTO v_row FROM public.writing_mastery_outbox WHERE id = p_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'ewp_outbox_not_found: %', p_id; END IF;
  IF v_row.status <> 'processing' OR v_row.claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'ewp_outbox_fencing_failed: % is not owned by this claim', p_id;
  END IF;
  IF v_row.source_kind <> 'evaluation' THEN
    RAISE EXCEPTION 'ewp_outbox_wrong_kind: batch completion is for evaluation rows only (%)', v_row.source_kind;
  END IF;

  SELECT * INTO v_ctx FROM ewp_private.ewp_outbox_evidence_context(p_id);
  SELECT * INTO v_eval FROM public.writing_evaluations WHERE id = v_row.evaluation_id;
  v_must_fix := EXISTS (
    SELECT 1 FROM public.writing_issue_events i
    WHERE i.evaluation_id = v_row.evaluation_id AND i.severity = 'must_fix'
      AND i.affects_current_state = TRUE);
  SELECT count(*)::int INTO v_resolved FROM public.writing_issue_resolution_events r
  WHERE r.resolving_evaluation_id = v_row.evaluation_id AND r.outcome = 'resolved';

  -- SERVER-DERIVED EXPECTED SET (§4.12/§4.12a). The completion NEVER trusts the
  -- worker's row set or tiers: it derives, inside this transaction, the EXACT set
  -- of evidence rows this evaluation must produce (projection ids + microtopic +
  -- tier + key) and requires the supplied payload to match it exactly — count,
  -- uniqueness, projection ids, microtopic and tier. Omission, duplicate and
  -- forged-tier payloads are all rejected.
  CREATE TEMP TABLE IF NOT EXISTS _ewp_expected(
    proj uuid, micro uuid, tier text, key text, matched boolean) ON COMMIT DROP;
  DELETE FROM _ewp_expected;

  -- Unit-level row (projection-less): expected iff the evaluation reached a
  -- terminal-success state with NO unresolved must_fix (mirrors
  -- evidence_deriver.derive_unit_evidence). Tier = 'correction' when the aspirant
  -- resolved ≥1 prior error this evaluation, else 'production'. Its key IS the
  -- outbox idempotency_key.
  IF v_eval.overall_status IN ('completed','terminal_partial') AND NOT v_must_fix THEN
    v_unit_tier := CASE WHEN v_resolved > 0 THEN 'correction' ELSE 'production' END;
    INSERT INTO _ewp_expected(proj, micro, tier, key, matched)
    VALUES (NULL, v_ctx.microtopic_id, v_unit_tier, v_row.idempotency_key, FALSE);
  END IF;

  -- Projection-linked 'correction' rows: exactly one per lineage the aspirant
  -- RESOLVED in this evaluation (outcome='resolved'), linked to the resolved
  -- issue's automatic projection, keyed on the resolved issue's microtopic. A
  -- review-invalidated resolved issue earns nothing.
  INSERT INTO _ewp_expected(proj, micro, tier, key, matched)
  SELECT pr.id, ie.microtopic_id, 'correction',
         ewp_private.ewp_compute_evidence_key(
           'assert', v_row.user_id, v_row.evaluation_id, pr.id, ie.microtopic_id,
           'correction', v_ctx.source_type, NULL),
         FALSE
  FROM public.writing_issue_resolution_events r
  JOIN public.writing_issue_events ie ON ie.id = r.issue_event_id
  JOIN public.writing_issue_projections pr
    ON pr.issue_event_id = ie.id AND pr.projection_kind = 'automatic'
  WHERE r.resolving_evaluation_id = v_row.evaluation_id
    AND r.outcome = 'resolved'
    AND ie.affects_current_state = TRUE
    AND NOT ewp_private.ewp_issue_effectively_invalidated(ie.id);

  SELECT count(*) INTO v_expected FROM _ewp_expected;

  IF p_pairs IS NOT NULL AND jsonb_typeof(p_pairs) = 'array' THEN
    FOR v_pair IN SELECT * FROM jsonb_array_elements(p_pairs) LOOP
      v_ev := v_pair->'evidence';
      v_sh := v_pair->'shadow';
      v_op   := COALESCE(v_ev->>'evidence_op','assert');
      v_tier := v_ev->>'evidence_tier';
      v_proj := NULLIF(v_ev->>'issue_projection_id','')::uuid;
      v_micro := NULLIF(v_ev->>'microtopic_id','')::uuid;

      -- Row-independent identity binding: user / evaluation / op / eval-level
      -- context are the claimed row's, never the worker's assertion.
      IF (v_ev->>'user_id')::uuid <> v_row.user_id
         OR (v_ev->>'evaluation_id')::uuid IS DISTINCT FROM v_row.evaluation_id
         OR v_op <> v_row.evidence_op
         OR (v_ev->>'topic_id')::uuid IS DISTINCT FROM v_ctx.topic_id
         OR (v_ev->>'source_type') <> v_ctx.source_type
         OR (v_ev->>'source_entity_id')::uuid IS DISTINCT FROM v_ctx.source_entity_id
         OR NULLIF(v_ev->>'exam_id','')::uuid IS DISTINCT FROM v_ctx.exam_id
         OR (v_sh->>'evidence_key') <> (v_ev->>'evidence_key')
         OR (v_sh->>'user_id')::uuid <> v_row.user_id
         OR (v_sh->>'evaluation_id')::uuid IS DISTINCT FROM v_row.evaluation_id
         OR (v_sh->>'evidence_tier') <> v_tier
         OR (v_sh->>'topic_id')::uuid IS DISTINCT FROM v_ctx.topic_id THEN
        RAISE EXCEPTION 'ewp_outbox_payload_mismatch: pair does not match the claimed row %', p_id;
      END IF;

      -- Match this pair to an UNCONSUMED expected row keyed by projection id
      -- (NULL for the unit-level row). Tier and microtopic must match the
      -- server-derived expectation exactly; a re-supplied (duplicate) row finds
      -- no unmatched expected row and is rejected.
      SELECT * INTO v_exp FROM _ewp_expected e
      WHERE e.proj IS NOT DISTINCT FROM v_proj AND e.matched = FALSE
      LIMIT 1;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'ewp_outbox_payload_mismatch: unexpected or duplicate row for projection % (not in the server-derived expected set)', v_proj;
      END IF;
      IF v_tier <> v_exp.tier THEN
        RAISE EXCEPTION 'ewp_outbox_payload_mismatch: forged tier % (expected % for projection %)', v_tier, v_exp.tier, v_proj;
      END IF;
      IF v_micro IS DISTINCT FROM v_exp.micro THEN
        RAISE EXCEPTION 'ewp_outbox_payload_mismatch: microtopic mismatch for projection %', v_proj;
      END IF;
      -- Strongest binding: the re-derived key must equal both the server-derived
      -- expected key AND the worker-supplied evidence key.
      v_key := ewp_private.ewp_compute_evidence_key(
        v_op, v_row.user_id, v_row.evaluation_id, v_proj, v_exp.micro,
        v_tier, v_ctx.source_type, NULL);
      IF v_key <> v_exp.key OR v_key <> (v_ev->>'evidence_key') THEN
        RAISE EXCEPTION 'ewp_outbox_payload_mismatch: re-derived key does not match the expected/supplied evidence_key';
      END IF;

      UPDATE _ewp_expected SET matched = TRUE WHERE proj IS NOT DISTINCT FROM v_proj;

      INSERT INTO public.user_topic_mastery_evidence(
        user_id, exam_id, topic_id, microtopic_id, source_type, source_entity_id,
        evidence_tier, score, confidence, issue_projection_id, evidence_op,
        evidence_key, observed_at)
      VALUES (
        v_row.user_id, v_ctx.exam_id, v_ctx.topic_id, v_exp.micro,
        v_ctx.source_type, v_ctx.source_entity_id, v_tier,
        NULLIF(v_ev->>'score','')::numeric, NULLIF(v_ev->>'confidence','')::numeric,
        v_proj, v_op, v_ev->>'evidence_key', now())
      ON CONFLICT (evidence_key) DO NOTHING;

      INSERT INTO public.writing_mastery_shadow(
        user_id, exam_id, topic_id, microtopic_id, source_type, source_entity_id,
        evaluation_id, issue_projection_id, evidence_tier, score, confidence,
        delta_json, evidence_key)
      VALUES (
        v_row.user_id, v_ctx.exam_id, v_ctx.topic_id, v_exp.micro,
        v_ctx.source_type, v_ctx.source_entity_id, v_row.evaluation_id, v_proj,
        v_tier, NULLIF(v_sh->>'score','')::numeric, NULLIF(v_sh->>'confidence','')::numeric,
        COALESCE(v_sh->'delta_json','{}'::jsonb), v_sh->>'evidence_key')
      ON CONFLICT (evidence_key) DO NOTHING;

      v_wrote := v_wrote + 1;
    END LOOP;
  END IF;

  -- Set equality: every server-derived expected row must have been supplied.
  -- (Omission is rejected here; unexpected/duplicate rows were rejected above.)
  IF EXISTS (SELECT 1 FROM _ewp_expected WHERE matched = FALSE) THEN
    RAISE EXCEPTION 'ewp_outbox_payload_mismatch: payload omits % of % server-derived expected rows',
      (SELECT count(*) FROM _ewp_expected WHERE matched = FALSE), v_expected;
  END IF;

  UPDATE public.writing_mastery_outbox SET status = 'done', processed_at = now() WHERE id = p_id;
  RETURN jsonb_build_object('status','done','wrote_evidence', v_wrote > 0, 'rows', v_wrote);
END;
$$;

-- ===========================================================================
-- Correction-chain guard, ORDERED variant (§4.10a/§4.12c). Redefines the 205
-- guard function so intermediate effective transitions can be applied in order
-- (the 205 version only admitted corrections citing the LATEST review event,
-- which silently dropped every intermediate transition — e.g. an invalidate that
-- was later confirmed lost its retract→re-assert chain). The immutability rule is
-- honoured: 205 is not edited; this is a forward CREATE OR REPLACE in a new
-- migration. All other 205 invariants are preserved VERBATIM; ONLY the
-- "cited-review-must-be-latest" staleness gate is replaced by an in-ORDER gate:
-- a correction must supersede the tail produced by the IMMEDIATELY-PREVIOUS
-- review event (the tail's causing decision must equal the cited event's previous
-- effective decision). This applies every transition one step at a time in
-- (created_at, event_seq) order and still rejects skip-ahead / out-of-order
-- corrections, while allowing a non-latest event whose predecessor is already
-- applied.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_check_evidence_correction()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  pred_issue      uuid;
  pred_proj       uuid;
  root_proj       uuid;
  review_issue    uuid;
  review_decision text;
  cited_created   timestamptz;
  cited_seq       bigint;
  prev_decision   text;
  tail_decision   text;
  new_issue       uuid;
  new_kind        text;
  new_override    uuid;
  has_successor   boolean;
BEGIN
  IF NEW.supersedes_evidence_key IS NOT NULL THEN
    -- must supersede the effective tail (a row with no successor)
    SELECT EXISTS (
      SELECT 1 FROM public.user_topic_mastery_evidence s
      WHERE s.supersedes_evidence_key = NEW.supersedes_evidence_key
    ) INTO has_successor;
    IF has_successor THEN
      RAISE EXCEPTION 'evidence_correction_invalid: predecessor % already superseded (not the effective tail)', NEW.supersedes_evidence_key;
    END IF;

    -- predecessor MUST resolve to an issue via its projection; capture the
    -- predecessor's EXACT projection (retract must preserve it) AND the decision
    -- of the review event that produced the tail (original assert → 'confirmed').
    SELECT p.issue_projection_id, ie.id, COALESCE(rp.decision, 'confirmed')
      INTO pred_proj, pred_issue, tail_decision
      FROM public.user_topic_mastery_evidence p
      JOIN public.writing_issue_projections pr ON pr.id = p.issue_projection_id
      JOIN public.writing_issue_events ie ON ie.id = pr.issue_event_id
      LEFT JOIN public.writing_issue_review_events rp ON rp.id = p.review_event_id
      WHERE p.evidence_key = NEW.supersedes_evidence_key;
    IF pred_issue IS NULL THEN
      RAISE EXCEPTION 'evidence_correction_invalid: predecessor % has no issue projection to correct', NEW.supersedes_evidence_key;
    END IF;

    -- root of the supersession chain (the original assert) — re-assert must
    -- restore its EXACT automatic projection, not just any automatic one.
    WITH RECURSIVE chain AS (
      SELECT e.evidence_key, e.supersedes_evidence_key, e.issue_projection_id
        FROM public.user_topic_mastery_evidence e
        WHERE e.evidence_key = NEW.supersedes_evidence_key
      UNION ALL
      SELECT e.evidence_key, e.supersedes_evidence_key, e.issue_projection_id
        FROM public.user_topic_mastery_evidence e
        JOIN chain c ON e.evidence_key = c.supersedes_evidence_key
    )
    SELECT issue_projection_id INTO root_proj FROM chain WHERE supersedes_evidence_key IS NULL;

    -- citing review event: target issue, decision, and ordering position
    SELECT issue_event_id, decision, created_at, event_seq
      INTO review_issue, review_decision, cited_created, cited_seq
      FROM public.writing_issue_review_events WHERE id = NEW.review_event_id;
    IF review_issue IS DISTINCT FROM pred_issue THEN
      RAISE EXCEPTION 'evidence_correction_invalid: review event % targets a different issue than the predecessor', NEW.review_event_id;
    END IF;

    -- Previous effective decision for the cited event = latest event strictly
    -- before it, defaulting to 'confirmed' (active) when there is none.
    SELECT decision INTO prev_decision
      FROM public.writing_issue_review_events r2
      WHERE r2.issue_event_id = pred_issue
        AND (r2.created_at, r2.event_seq) < (cited_created, cited_seq)
      ORDER BY r2.created_at DESC, r2.event_seq DESC
      LIMIT 1;
    prev_decision := COALESCE(prev_decision, 'confirmed');

    -- ORDERED processing (replaces the 205 latest-only gate): the tail this
    -- correction supersedes must be the one produced by the cited event's
    -- immediately-previous review event. Equivalently the tail's causing decision
    -- must equal prev_decision. This forbids skipping ahead (applying a later
    -- transition before an earlier one) and re-applying an already-processed
    -- transition, without forbidding a legitimately in-order non-latest event.
    IF tail_decision IS DISTINCT FROM prev_decision THEN
      RAISE EXCEPTION 'evidence_correction_invalid: out-of-order correction (tail decision % <> previous effective decision % for the cited review %)', tail_decision, prev_decision, NEW.review_event_id;
    END IF;

    -- the decision must actually CHANGE the effective decision; an unchanged
    -- transition (confirmed->confirmed, ...) emits nothing (§4.10a).
    IF review_decision = prev_decision THEN
      RAISE EXCEPTION 'evidence_correction_invalid: review decision % is unchanged from the previous effective decision (no correction)', review_decision;
    END IF;

    -- Locked review-decision -> evidence-op mapping (§4.12c):
    --   confirmed -> assert (re-assert), invalidated -> retract, reclassified -> replace.
    IF (review_decision = 'confirmed'    AND NEW.evidence_op <> 'assert')
       OR (review_decision = 'invalidated'  AND NEW.evidence_op <> 'retract')
       OR (review_decision = 'reclassified' AND NEW.evidence_op <> 'replace') THEN
      RAISE EXCEPTION 'evidence_correction_invalid: evidence_op % does not match review decision %', NEW.evidence_op, review_decision;
    END IF;

    -- EVERY superseding row must carry a projection on the predecessor's issue.
    IF NEW.issue_projection_id IS NULL THEN
      RAISE EXCEPTION 'evidence_correction_invalid: a superseding row must carry a projection on the predecessor issue';
    END IF;
    SELECT pr.issue_event_id, pr.projection_kind, pr.override_review_event_id
      INTO new_issue, new_kind, new_override
      FROM public.writing_issue_projections pr WHERE pr.id = NEW.issue_projection_id;
    IF new_issue IS DISTINCT FROM pred_issue THEN
      RAISE EXCEPTION 'evidence_correction_invalid: projection is on a different issue than the predecessor';
    END IF;

    -- EXACT op-specific projection identity:
    --   replace  -> the review-override projection created by the cited event;
    --   re-assert-> the EXACT original automatic projection at the chain root;
    --   retract  -> the predecessor's EXACT projection (preserve).
    IF NEW.evidence_op = 'replace' THEN
      IF new_kind IS DISTINCT FROM 'review_override' OR new_override IS DISTINCT FROM NEW.review_event_id THEN
        RAISE EXCEPTION 'evidence_correction_invalid: replace must carry the review_override projection created by the cited review event';
      END IF;
    ELSIF NEW.evidence_op = 'assert' THEN
      IF new_kind IS DISTINCT FROM 'automatic' OR NEW.issue_projection_id IS DISTINCT FROM root_proj THEN
        RAISE EXCEPTION 'evidence_correction_invalid: re-assert must restore the exact original automatic projection at the chain root';
      END IF;
    ELSIF NEW.evidence_op = 'retract' THEN
      IF NEW.issue_projection_id IS DISTINCT FROM pred_proj THEN
        RAISE EXCEPTION 'evidence_correction_invalid: retract must preserve the predecessor''s exact projection';
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

-- ===========================================================================
-- Serialized review-correction pipeline (§4.12c). EWP-3 produces the review
-- events; this is the APPLY side. A review event that CHANGES the effective
-- decision for an issue, and for which a projection-linked evidence row already
-- exists, enqueues one review_correction outbox row whose op is fixed by the
-- decision (confirmed->assert re-assert, invalidated->retract, reclassified->
-- replace). The pinned mode is COPIED from the assertion's evaluation outbox
-- (§8.2/§4.12c), never re-resolved from the current flag — so a correction is
-- emitted even when the flag is now 'off'.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_enqueue_review_correction(p_review_event_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_issue     uuid;
  v_decision  text;
  v_corrected text;
  v_created   timestamptz;
  v_seq       bigint;
  v_prev      text;
  v_op        text;
  v_tail      public.user_topic_mastery_evidence%ROWTYPE;
  v_user      uuid;
  v_eval      uuid;
  v_micro     uuid;
  v_flag      text;
  v_key       text;
  v_override  uuid;
  v_canonical text;
  v_count     int;
  v_revision  int;
BEGIN
  SELECT issue_event_id, decision, corrected_issue_type, created_at, event_seq
    INTO v_issue, v_decision, v_corrected, v_created, v_seq
    FROM public.writing_issue_review_events WHERE id = p_review_event_id;
  IF v_issue IS NULL THEN RAISE EXCEPTION 'ewp_review_event_not_found: %', p_review_event_id; END IF;

  -- SERIALIZED per issue (§4.10a/§4.12c). Every review event that CHANGES the
  -- effective decision is processed — NOT latest-only — so intermediate
  -- transitions (e.g. invalidated then confirmed queued before the first drain)
  -- are never dropped: the retract→re-assert chain stays causally intact. The
  -- advisory lock serializes concurrent enqueues for one issue; the apply-side
  -- correction guard (ewp_check_evidence_correction) enforces that each
  -- correction supersedes the tail produced by the immediately-previous review
  -- event, so corrections land in (created_at, event_seq) order one step at a
  -- time regardless of enqueue/claim interleaving.
  PERFORM pg_advisory_xact_lock(hashtext('ewp_review_issue:' || v_issue::text));

  -- Previous effective decision for the CITED event = latest event strictly
  -- before it, default 'confirmed' (active). The op is this event's OWN
  -- transition (not measured against the newest event), so a non-latest event
  -- still enqueues its transition.
  SELECT decision INTO v_prev FROM public.writing_issue_review_events r2
    WHERE r2.issue_event_id = v_issue
      AND (r2.created_at, r2.event_seq) < (v_created, v_seq)
    ORDER BY r2.created_at DESC, r2.event_seq DESC LIMIT 1;
  v_prev := COALESCE(v_prev, 'confirmed');
  IF v_decision = v_prev THEN
    RETURN jsonb_build_object('status','noop','reason','no_effective_change');
  END IF;

  v_op := CASE v_decision WHEN 'confirmed' THEN 'assert'
                          WHEN 'invalidated' THEN 'retract'
                          WHEN 'reclassified' THEN 'replace' END;

  -- Effective evidence tail for this issue at enqueue time (the row nothing
  -- supersedes) — used only to confirm evidence exists to correct and to resolve
  -- the user/pinned-mode. The APPLY-side claim recomputes the tail so a correction
  -- always supersedes whatever is effective when it lands (§4.12c).
  SELECT e.* INTO v_tail
    FROM public.user_topic_mastery_evidence e
    JOIN public.writing_issue_projections pr ON pr.id = e.issue_projection_id
    WHERE pr.issue_event_id = v_issue
      AND NOT EXISTS (SELECT 1 FROM public.user_topic_mastery_evidence s
                      WHERE s.supersedes_evidence_key = e.evidence_key AND s.user_id = e.user_id)
    ORDER BY e.observed_at DESC LIMIT 1;
  IF v_tail.evidence_key IS NULL THEN
    RETURN jsonb_build_object('status','noop','reason','no_evidence_to_correct');
  END IF;
  v_user := v_tail.user_id;

  -- Pinned mode is COPIED from the assertion's evaluation outbox (§4.12c/§8.2),
  -- never re-resolved from the current flag. FAIL CLOSED: if the superseded
  -- assertion's pinned channel cannot be resolved, do NOT invent 'shadow' — skip
  -- and surface it, so a correction is never emitted on a fabricated channel.
  SELECT ie.evaluation_id, ie.microtopic_id INTO v_eval, v_micro
    FROM public.writing_issue_projections pr
    JOIN public.writing_issue_events ie ON ie.id = pr.issue_event_id
    WHERE pr.id = v_tail.issue_projection_id;
  SELECT o.mastery_flag_state INTO v_flag
    FROM public.writing_mastery_outbox o
    WHERE o.source_kind = 'evaluation' AND o.evaluation_id = v_eval
    ORDER BY o.created_at LIMIT 1;
  IF v_flag IS NULL THEN
    RETURN jsonb_build_object('status','noop','reason','unresolved_pinned_mode');
  END IF;

  -- For a reclassify, ensure the review-override projection exists (§4.11a): a
  -- human reclassification produces it at the session's pinned revision. Seeded
  -- flows may already have it; create it idempotently otherwise so 'replace' has
  -- a projection to carry. The canonical error type uses the ACTUAL transactional
  -- prior-occurrence count for (user, microtopic, corrected type) — NOT a
  -- hardcoded prior_count=1 — via ewp_canonical_error_type; an unknown/unmappable
  -- corrected type leaves canonical_error_type NULL (never forced, §6).
  IF v_decision = 'reclassified' THEN
    SELECT id INTO v_override FROM public.writing_issue_projections
      WHERE projection_kind = 'review_override' AND override_review_event_id = p_review_event_id;
    IF v_override IS NULL THEN
      SELECT projection_revision INTO v_revision FROM public.writing_issue_projections
        WHERE issue_event_id = v_issue AND projection_kind = 'automatic'
        ORDER BY projection_revision DESC LIMIT 1;
      -- Actual prior-occurrence count for the corrected type (current-state,
      -- non-invalidated, this user + the issue's microtopic), excluding this issue.
      SELECT count(*) INTO v_count
      FROM public.writing_issue_events i2
      JOIN public.writing_evaluations e3 ON e3.id = i2.evaluation_id
      JOIN public.writing_unit_versions v3 ON v3.id = e3.unit_version_id
      JOIN public.writing_session_units u3 ON u3.id = v3.unit_id
      JOIN public.writing_sessions s3 ON s3.id = u3.session_id
      WHERE s3.user_id = v_user
        AND i2.issue_type = v_corrected
        AND i2.microtopic_id IS NOT DISTINCT FROM v_micro
        AND i2.id <> v_issue
        AND i2.affects_current_state = TRUE
        AND NOT ewp_private.ewp_issue_effectively_invalidated(i2.id);
      v_canonical := CASE WHEN v_corrected IS NULL THEN NULL
                          ELSE ewp_private.ewp_canonical_error_type(v_corrected, v_count) END;
      INSERT INTO public.writing_issue_projections(
        issue_event_id, projection_revision, projection_kind, override_review_event_id,
        canonical_error_type, projection_confidence, rationale)
      VALUES (v_issue, COALESCE(v_revision, 1), 'review_override', p_review_event_id,
              v_canonical,
              CASE WHEN v_canonical IS NULL THEN NULL ELSE 0.9 END,
              'review_override:' || COALESCE(v_corrected,'reclassified'))
      RETURNING id INTO v_override;
    END IF;
  END IF;

  -- Idempotency key (§8.2): SHA-256('review' || review_event_id || evidence_op || user_id).
  v_key := encode(sha256(convert_to('review' || p_review_event_id::text || v_op || v_user::text, 'UTF8')), 'hex');

  INSERT INTO public.writing_mastery_outbox(
    source_kind, review_event_id, evidence_op, user_id, mastery_flag_state,
    idempotency_key, status)
  VALUES ('review_correction', p_review_event_id, v_op, v_user, v_flag, v_key, 'pending')
  ON CONFLICT (idempotency_key) DO NOTHING;

  RETURN jsonb_build_object('status','enqueued','evidence_op', v_op,
    'mastery_flag_state', v_flag, 'idempotency_key', v_key,
    'supersedes_evidence_key', v_tail.evidence_key);
END;
$$;

-- Shared, server-side correction context for a review_correction outbox row.
-- Re-derives (never trusts the worker): the CURRENT effective evidence tail for
-- the cited issue, the op-specific projection to carry (retract→predecessor's
-- exact projection; replace→the review-override projection; assert→the chain-root
-- automatic projection), the source evaluation, and the identity fields copied
-- from the tail (topic/microtopic/exam/source_type/source_entity/tier). Both the
-- claim RPC and the completion RPC consume THIS single derivation, so the payload
-- the worker returns is bound field-for-field to what the server independently
-- recomputes — a forged tier/topic/source/evaluation/supersedes cannot slip
-- through (§4.12c/§8.2).
CREATE OR REPLACE FUNCTION ewp_private.ewp_review_correction_context(p_outbox uuid)
RETURNS TABLE(
  review_event_id uuid, evidence_op text, user_id uuid,
  supersedes_evidence_key text, issue_projection_id uuid, evaluation_id uuid,
  topic_id uuid, microtopic_id uuid, exam_id uuid, source_type text,
  source_entity_id uuid, evidence_tier text)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row   public.writing_mastery_outbox%ROWTYPE;
  v_issue uuid;
  v_tail  public.user_topic_mastery_evidence%ROWTYPE;
  v_proj  uuid;
  v_root  uuid;
  v_eval  uuid;
BEGIN
  SELECT * INTO v_row FROM public.writing_mastery_outbox WHERE id = p_outbox;
  IF NOT FOUND OR v_row.source_kind <> 'review_correction' THEN RETURN; END IF;

  SELECT issue_event_id INTO v_issue
    FROM public.writing_issue_review_events WHERE id = v_row.review_event_id;

  SELECT e.* INTO v_tail
    FROM public.user_topic_mastery_evidence e
    JOIN public.writing_issue_projections pr ON pr.id = e.issue_projection_id
    WHERE pr.issue_event_id = v_issue
      AND NOT EXISTS (SELECT 1 FROM public.user_topic_mastery_evidence s
                      WHERE s.supersedes_evidence_key = e.evidence_key AND s.user_id = e.user_id)
    ORDER BY e.observed_at DESC LIMIT 1;
  IF v_tail.evidence_key IS NULL THEN RETURN; END IF;

  IF v_row.evidence_op = 'retract' THEN
    v_proj := v_tail.issue_projection_id;
  ELSIF v_row.evidence_op = 'replace' THEN
    SELECT id INTO v_proj FROM public.writing_issue_projections
      WHERE projection_kind = 'review_override' AND override_review_event_id = v_row.review_event_id;
  ELSE  -- assert / re-assert
    WITH RECURSIVE chain AS (
      SELECT e.evidence_key, e.supersedes_evidence_key, e.issue_projection_id
        FROM public.user_topic_mastery_evidence e WHERE e.evidence_key = v_tail.evidence_key
      UNION ALL
      SELECT e.evidence_key, e.supersedes_evidence_key, e.issue_projection_id
        FROM public.user_topic_mastery_evidence e
        JOIN chain c ON e.evidence_key = c.supersedes_evidence_key)
    SELECT c.issue_projection_id INTO v_root FROM chain c WHERE c.supersedes_evidence_key IS NULL;
    v_proj := v_root;
  END IF;

  SELECT ie.evaluation_id INTO v_eval
    FROM public.writing_issue_projections pr
    JOIN public.writing_issue_events ie ON ie.id = pr.issue_event_id
    WHERE pr.id = v_tail.issue_projection_id;

  review_event_id := v_row.review_event_id;
  evidence_op := v_row.evidence_op;
  user_id := v_row.user_id;
  supersedes_evidence_key := v_tail.evidence_key;
  issue_projection_id := v_proj;
  evaluation_id := v_eval;
  topic_id := v_tail.topic_id;
  microtopic_id := v_tail.microtopic_id;
  exam_id := v_tail.exam_id;
  source_type := v_tail.source_type;
  source_entity_id := v_tail.source_entity_id;
  evidence_tier := v_tail.evidence_tier;
  RETURN NEXT;
END;
$$;
REVOKE ALL ON FUNCTION ewp_private.ewp_review_correction_context(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ewp_private.ewp_review_correction_context(uuid) TO service_role;

-- Claim a pending review_correction outbox row (fencing token + lease) and
-- return the full context the worker needs to build the correction evidence:
-- the superseded tail, the op-specific projection to carry, and the copied
-- identity (tier/microtopic/topic/source) — all re-derived server-side.
CREATE OR REPLACE FUNCTION public.ewp_claim_review_correction_outbox(p_lease_seconds int DEFAULT 900)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row      public.writing_mastery_outbox%ROWTYPE;
  v_token    uuid := gen_random_uuid();
  v_issue    uuid;
  v_tail     public.user_topic_mastery_evidence%ROWTYPE;
  v_eval     uuid;
  v_proj     uuid;
  v_root     uuid;
BEGIN
  SELECT * INTO v_row FROM public.writing_mastery_outbox o
  WHERE o.status = 'pending' AND o.source_kind = 'review_correction'
  ORDER BY o.created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN RETURN NULL; END IF;

  UPDATE public.writing_mastery_outbox
  SET status = 'processing', locked_at = now(), claim_token = v_token, attempts = attempts + 1
  WHERE id = v_row.id;

  SELECT issue_event_id INTO v_issue FROM public.writing_issue_review_events WHERE id = v_row.review_event_id;

  -- Effective tail for the issue (the row nothing supersedes).
  SELECT e.* INTO v_tail
    FROM public.user_topic_mastery_evidence e
    JOIN public.writing_issue_projections pr ON pr.id = e.issue_projection_id
    WHERE pr.issue_event_id = v_issue
      AND NOT EXISTS (SELECT 1 FROM public.user_topic_mastery_evidence s
                      WHERE s.supersedes_evidence_key = e.evidence_key AND s.user_id = e.user_id)
    ORDER BY e.observed_at DESC LIMIT 1;

  -- Op-specific projection identity (matches ewp_check_evidence_correction):
  --   retract  -> the predecessor tail's EXACT projection (preserve);
  --   replace  -> the review-override projection created by the cited event;
  --   assert   -> the chain-root automatic projection (restore original).
  IF v_row.evidence_op = 'retract' THEN
    v_proj := v_tail.issue_projection_id;
  ELSIF v_row.evidence_op = 'replace' THEN
    SELECT id INTO v_proj FROM public.writing_issue_projections
      WHERE projection_kind = 'review_override' AND override_review_event_id = v_row.review_event_id;
  ELSE  -- assert / re-assert
    WITH RECURSIVE chain AS (
      SELECT e.evidence_key, e.supersedes_evidence_key, e.issue_projection_id
        FROM public.user_topic_mastery_evidence e WHERE e.evidence_key = v_tail.evidence_key
      UNION ALL
      SELECT e.evidence_key, e.supersedes_evidence_key, e.issue_projection_id
        FROM public.user_topic_mastery_evidence e
        JOIN chain c ON e.evidence_key = c.supersedes_evidence_key)
    SELECT issue_projection_id INTO v_root FROM chain WHERE supersedes_evidence_key IS NULL;
    v_proj := v_root;
  END IF;

  SELECT ie.evaluation_id INTO v_eval
    FROM public.writing_issue_projections pr
    JOIN public.writing_issue_events ie ON ie.id = pr.issue_event_id
    WHERE pr.id = v_tail.issue_projection_id;

  RETURN jsonb_build_object(
    'id', v_row.id, 'claim_token', v_token, 'evidence_op', v_row.evidence_op,
    'user_id', v_row.user_id, 'review_event_id', v_row.review_event_id,
    'mastery_flag_state', v_row.mastery_flag_state, 'idempotency_key', v_row.idempotency_key,
    'supersedes_evidence_key', v_tail.evidence_key,
    'issue_projection_id', v_proj, 'evaluation_id', v_eval,
    'topic_id', v_tail.topic_id, 'microtopic_id', v_tail.microtopic_id,
    'exam_id', v_tail.exam_id, 'source_type', v_tail.source_type,
    'source_entity_id', v_tail.source_entity_id, 'evidence_tier', v_tail.evidence_tier);
END;
$$;

-- Complete a review_correction: insert the correction evidence + shadow rows and
-- ack. The evidence identity is re-derived server-side and the correction op /
-- projection / supersession invariants are enforced by ewp_check_evidence_correction.
CREATE OR REPLACE FUNCTION public.ewp_complete_review_correction(
  p_id uuid, p_claim_token uuid, p_evidence jsonb, p_shadow jsonb
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row  public.writing_mastery_outbox%ROWTYPE;
  v_ctx  record;
  v_op   text;
  v_tier text;
  v_proj uuid;
  v_micro uuid;
  v_key  text;
BEGIN
  SELECT * INTO v_row FROM public.writing_mastery_outbox WHERE id = p_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'ewp_outbox_not_found: %', p_id; END IF;
  IF v_row.status <> 'processing' OR v_row.claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'ewp_outbox_fencing_failed: % is not owned by this claim', p_id;
  END IF;
  IF v_row.source_kind <> 'review_correction' THEN
    RAISE EXCEPTION 'ewp_outbox_wrong_kind: % is not a review_correction row', p_id;
  END IF;

  v_op   := COALESCE(p_evidence->>'evidence_op','assert');
  v_tier := p_evidence->>'evidence_tier';
  v_proj := NULLIF(p_evidence->>'issue_projection_id','')::uuid;
  v_micro := NULLIF(p_evidence->>'microtopic_id','')::uuid;

  -- IDENTITY BINDING (§4.12c). Re-derive the CURRENT effective tail and EVERY
  -- correction identity field server-side (never trust the worker) and require
  -- the payload to match field-for-field BEFORE insert: op, projection,
  -- evaluation, topic, microtopic, exam, source_type, source_entity, tier, AND
  -- supersedes_evidence_key (the effective tail). A forged tier/topic/source/
  -- evaluation/projection/supersedes is rejected here, not merely by the chain
  -- trigger.
  SELECT * INTO v_ctx FROM ewp_private.ewp_review_correction_context(p_id);
  IF v_ctx.review_event_id IS NULL THEN
    RAISE EXCEPTION 'ewp_outbox_payload_mismatch: no effective evidence tail to correct for %', p_id;
  END IF;

  IF v_op <> v_row.evidence_op
     OR v_op <> v_ctx.evidence_op
     OR (p_evidence->>'user_id')::uuid <> v_row.user_id
     OR (p_evidence->>'user_id')::uuid <> v_ctx.user_id
     OR (p_evidence->>'review_event_id')::uuid IS DISTINCT FROM v_row.review_event_id
     OR (p_shadow->>'evidence_key') <> (p_evidence->>'evidence_key')
     OR (p_shadow->>'user_id')::uuid <> v_row.user_id
     -- every identity field must equal the server-re-derived context
     OR v_proj IS DISTINCT FROM v_ctx.issue_projection_id
     OR NULLIF(p_evidence->>'evaluation_id','')::uuid IS DISTINCT FROM v_ctx.evaluation_id
     OR (p_evidence->>'topic_id')::uuid IS DISTINCT FROM v_ctx.topic_id
     OR v_micro IS DISTINCT FROM v_ctx.microtopic_id
     OR NULLIF(p_evidence->>'exam_id','')::uuid IS DISTINCT FROM v_ctx.exam_id
     OR (p_evidence->>'source_type') <> v_ctx.source_type
     OR (p_evidence->>'source_entity_id')::uuid IS DISTINCT FROM v_ctx.source_entity_id
     OR v_tier <> v_ctx.evidence_tier
     OR (p_evidence->>'supersedes_evidence_key') IS DISTINCT FROM v_ctx.supersedes_evidence_key
     -- shadow identity must agree too
     OR NULLIF(p_shadow->>'evaluation_id','')::uuid IS DISTINCT FROM v_ctx.evaluation_id
     OR (p_shadow->>'topic_id')::uuid IS DISTINCT FROM v_ctx.topic_id
     OR (p_shadow->>'evidence_tier') <> v_ctx.evidence_tier THEN
    RAISE EXCEPTION 'ewp_outbox_payload_mismatch: correction payload does not match the server-re-derived effective tail for %', p_id;
  END IF;

  -- Re-derive the evidence key server-side (the correction op + review_event_id
  -- are part of the §4.12b key), and require the worker-supplied key to match.
  v_key := ewp_private.ewp_compute_evidence_key(
    v_op, v_ctx.user_id, v_ctx.evaluation_id, v_ctx.issue_projection_id, v_ctx.microtopic_id,
    v_ctx.evidence_tier, v_ctx.source_type, v_row.review_event_id);
  IF v_key <> (p_evidence->>'evidence_key') THEN
    RAISE EXCEPTION 'ewp_outbox_payload_mismatch: re-derived correction key mismatch';
  END IF;

  -- The correction-chain trigger (ewp_check_evidence_correction) additionally
  -- enforces: supersedes the effective tail, in-order (not skip-ahead), decision
  -- changes, op matches decision, and the op-specific projection identity.
  INSERT INTO public.user_topic_mastery_evidence(
    user_id, exam_id, topic_id, microtopic_id, source_type, source_entity_id,
    evidence_tier, score, confidence, issue_projection_id, evidence_op,
    review_event_id, supersedes_evidence_key, evidence_key, observed_at)
  VALUES (
    v_row.user_id, NULLIF(p_evidence->>'exam_id','')::uuid,
    (p_evidence->>'topic_id')::uuid, v_micro, p_evidence->>'source_type',
    (p_evidence->>'source_entity_id')::uuid, v_tier,
    NULLIF(p_evidence->>'score','')::numeric, NULLIF(p_evidence->>'confidence','')::numeric,
    v_proj, v_op, v_row.review_event_id, p_evidence->>'supersedes_evidence_key',
    p_evidence->>'evidence_key', now())
  ON CONFLICT (evidence_key) DO NOTHING;

  INSERT INTO public.writing_mastery_shadow(
    user_id, exam_id, topic_id, microtopic_id, source_type, source_entity_id,
    evaluation_id, issue_projection_id, evidence_tier, score, confidence,
    delta_json, evidence_key)
  VALUES (
    v_row.user_id, NULLIF(p_shadow->>'exam_id','')::uuid,
    (p_shadow->>'topic_id')::uuid, v_micro, p_shadow->>'source_type',
    (p_shadow->>'source_entity_id')::uuid, (p_shadow->>'evaluation_id')::uuid,
    v_proj, v_tier, NULLIF(p_shadow->>'score','')::numeric,
    NULLIF(p_shadow->>'confidence','')::numeric,
    COALESCE(p_shadow->'delta_json','{}'::jsonb), p_shadow->>'evidence_key')
  ON CONFLICT (evidence_key) DO NOTHING;

  UPDATE public.writing_mastery_outbox SET status = 'done', processed_at = now() WHERE id = p_id;
  RETURN jsonb_build_object('status','done','evidence_op', v_op);
END;
$$;

-- ===========================================================================
-- grants — service_role only (the worker runs under the service role).
-- ===========================================================================
REVOKE ALL ON FUNCTION public.ewp_claim_evaluation_job(int, text[]) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_complete_language_evaluation(uuid,uuid,text,jsonb,jsonb,jsonb,boolean,text,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_fail_evaluation_job(uuid,uuid,text,int) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_recover_evaluation(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_reject_corrupt_version(uuid,uuid,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_sweep_stale_evaluation_jobs(int) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_claim_mastery_outbox(int) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_sweep_stale_mastery_outbox(int) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_complete_mastery_outbox(uuid,uuid,jsonb,jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_fail_mastery_outbox(uuid,uuid,text,int) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_complete_mastery_outbox_batch(uuid,uuid,jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_enqueue_review_correction(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_claim_review_correction_outbox(int) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_complete_review_correction(uuid,uuid,jsonb,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_claim_evaluation_job(int, text[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_complete_language_evaluation(uuid,uuid,text,jsonb,jsonb,jsonb,boolean,text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_fail_evaluation_job(uuid,uuid,text,int) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_recover_evaluation(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_reject_corrupt_version(uuid,uuid,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_sweep_stale_evaluation_jobs(int) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_claim_mastery_outbox(int) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_sweep_stale_mastery_outbox(int) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_complete_mastery_outbox(uuid,uuid,jsonb,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_fail_mastery_outbox(uuid,uuid,text,int) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_complete_mastery_outbox_batch(uuid,uuid,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_enqueue_review_correction(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_claim_review_correction_outbox(int) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_complete_review_correction(uuid,uuid,jsonb,jsonb) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
