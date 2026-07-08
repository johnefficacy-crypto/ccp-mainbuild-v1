-- 236_ewp_complete_evaluation_safeupdate_fix.sql
--
-- Fixes a live writing-practice e2e failure: every call to
-- public.ewp_complete_language_evaluation() (migration 209) returns HTTP 400
-- with body {"message": "DELETE requires a WHERE clause", "code": "21000"}.
--
-- Root cause: Supabase's local/managed Postgres image runs the SECURITY
-- DEFINER function's owning role (postgres) with the pg_safeupdate extension
-- active, which rejects ANY unqualified UPDATE/DELETE statement — including
-- one issued from inside a plpgsql function body, not just raw client SQL.
-- Migration 209's function resets its per-call temp table with an unqualified
-- `DELETE FROM _ewp_regressions;` (intended to clear ALL rows — the table is
-- ON COMMIT DROP and scoped to one function invocation, so there is no
-- narrower predicate to add); pg_safeupdate blocks it every time, so the
-- worker's evaluation-completion RPC has never once succeeded end-to-end.
--
-- Fix: CREATE OR REPLACE the identical function body with the single DELETE
-- changed to `DELETE FROM _ewp_regressions WHERE true;` — functionally
-- identical (still deletes every row) but satisfies pg_safeupdate's syntactic
-- WHERE-clause requirement. Same signature, so no caller/grant changes needed
-- (CREATE OR REPLACE preserves existing privileges on signature match).

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
  -- WHERE true (not a bare DELETE): the Supabase-managed `postgres` role runs
  -- with pg_safeupdate active, which rejects any unqualified DELETE/UPDATE —
  -- including ones issued from inside this SECURITY DEFINER function body.
  -- This table is scoped to one function call and must be fully cleared, so
  -- WHERE true is the correct (not merely syntactic) predicate.
  DELETE FROM _ewp_regressions WHERE true;
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

notify pgrst, 'reload schema';
