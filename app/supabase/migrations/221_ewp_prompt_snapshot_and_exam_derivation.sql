-- 221_ewp_prompt_snapshot_and_exam_derivation.sql
-- =============================================================================
-- Fix the EWP evaluation/mastery pipeline after migration 214 dropped the
-- exam-scope columns from public.writing_prompts.
--
-- Migration 209 defined four runtime functions that read scope directly off the
-- prompt row (v_prompt.exam_id / v_prompt.exercise_type / v_prompt.topic_id /
-- v_prompt.rubric_id). Migration 214 then dropped writing_prompts.exam_id
-- (canonical identity is now subject/topic/microtopic; applicability lives in
-- writing_prompt_targets). The 209 bodies were never updated, so every one of
-- them now RAISES at runtime — `record "v_prompt" has no field "exam_id"` — the
-- moment a job or outbox row is claimed. That breaks the whole async pipeline:
--   * ewp_claim_evaluation_job            (worker can't claim a language job)
--   * ewp_claim_mastery_outbox            (mastery drain can't claim a row)
--   * ewp_private.ewp_outbox_evidence_context (completion can't re-derive context)
--
-- Two coupled fixes:
--   1. Immutable per-session prompt snapshot. A session's scope/content must not
--      shift if the underlying prompt is later edited. We capture
--      {exercise_type, topic_id, prompt_text, source_text, rubric_dimensions}
--      into writing_sessions.prompt_snapshot at session creation, backfill every
--      existing session from the current prompt, and read scope from the snapshot
--      thereafter. This also SURFACES prompt_text/source_text on the claim
--      payload (the RPC half of the documented "source_text not delivered to the
--      evaluator" blocker — the worker's consumption of it stays a separate,
--      design-gated slice).
--   2. exam_id is no longer a prompt attribute. The exam a practice belongs to is
--      a property of the STUDY TASK the session was created for
--      (study_tasks.exam_id, added in migration 034), so we derive it from
--      writing_sessions.study_task_id. It is NULL for ad-hoc sessions with no
--      study task — which is correct, and safe: the mastery evidence key
--      (ewp_compute_evidence_key / evidence_deriver) deliberately EXCLUDES
--      exam_id, so idempotency is unaffected, and every exam_id consumer already
--      uses NULL-safe IS DISTINCT FROM / NULLIF comparisons.
--
-- No landed migration is edited. 205/209/214 stay immutable; this is a forward
-- CREATE OR REPLACE of the three broken functions plus ewp_create_writing_session
-- (to capture the snapshot). Signatures are unchanged, so REPLACE is legal and
-- existing ACLs are preserved (we re-issue the grants anyway, for the record).
-- =============================================================================

-- ----------------------------------------------------------------------------
-- 1. Immutable prompt snapshot on the session.
-- ----------------------------------------------------------------------------
ALTER TABLE public.writing_sessions
  ADD COLUMN IF NOT EXISTS prompt_snapshot jsonb;

COMMENT ON COLUMN public.writing_sessions.prompt_snapshot IS
  'Immutable copy of the prompt scope/content captured at session creation '
  '(schema_version, exercise_type, topic_id, prompt_text, source_text, '
  'rubric_dimensions). The evaluation/mastery pipeline reads scope from here, '
  'never from the live prompt, so later prompt edits cannot retro-change a '
  'session. exam_id is NOT snapshotted — it is derived from study_tasks.exam_id.';

-- Backfill every existing session from its current prompt. prompt_id is
-- NOT NULL + FK, so a matching prompt is guaranteed for every row → the backfill
-- is total and the subsequent SET NOT NULL is safe.
UPDATE public.writing_sessions s
SET prompt_snapshot = jsonb_build_object(
      'schema_version', 1,
      'exercise_type', p.exercise_type,
      'topic_id', p.topic_id,
      'prompt_text', p.prompt_text,
      'source_text', p.source_text,
      'rubric_dimensions', COALESCE(
        (SELECT r.dimensions FROM public.writing_rubrics r WHERE r.id = p.rubric_id),
        '[]'::jsonb))
FROM public.writing_prompts p
WHERE p.id = s.prompt_id
  AND s.prompt_snapshot IS NULL;

ALTER TABLE public.writing_sessions
  ALTER COLUMN prompt_snapshot SET NOT NULL;

-- ----------------------------------------------------------------------------
-- 2. Capture the snapshot at session creation (was: no snapshot).
--    Signature unchanged from migration 207.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.ewp_create_writing_session(
  p_user uuid,
  p_prompt uuid,
  p_study_task uuid,
  p_mode text,
  p_projection_revision int,
  p_policy text,
  p_delay int,
  p_unit_count int,
  p_microtopic uuid,
  p_constraints jsonb
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_session uuid;
  v_snapshot jsonb;
  i int;
BEGIN
  IF p_mode <> 'learning' THEN
    -- EWP-2 ships learning mode only; exam runtime is a later slice (§9.2).
    RAISE EXCEPTION 'ewp_mode_unsupported: mode % is not available in EWP-2', p_mode;
  END IF;

  -- Freeze the prompt's scope + content into an immutable per-session snapshot.
  -- The evaluation/mastery pipeline reads scope from here (never the live prompt),
  -- so a later prompt edit cannot retro-change an in-flight or historical session.
  SELECT jsonb_build_object(
           'schema_version', 1,
           'exercise_type', p.exercise_type,
           'topic_id', p.topic_id,
           'prompt_text', p.prompt_text,
           'source_text', p.source_text,
           'rubric_dimensions', COALESCE(
             (SELECT r.dimensions FROM public.writing_rubrics r WHERE r.id = p.rubric_id),
             '[]'::jsonb))
    INTO v_snapshot
    FROM public.writing_prompts p
    WHERE p.id = p_prompt;
  IF v_snapshot IS NULL THEN
    RAISE EXCEPTION 'ewp_prompt_not_found: %', p_prompt;
  END IF;

  INSERT INTO public.writing_sessions(
    user_id, study_task_id, prompt_id, mode, status, projection_revision,
    feedback_release_policy, feedback_release_delay_seconds, prompt_snapshot)
  VALUES (p_user, p_study_task, p_prompt, p_mode, 'active', p_projection_revision,
          p_policy, p_delay, v_snapshot)
  RETURNING id INTO v_session;

  FOR i IN 1 .. GREATEST(p_unit_count, 1) LOOP
    INSERT INTO public.writing_session_units(
      session_id, unit_number, practice_microtopic_id, unit_constraints, status)
    VALUES (v_session, i, p_microtopic, COALESCE(p_constraints, '{"schema_version":1}'::jsonb), 'not_started');
  END LOOP;

  RETURN (SELECT to_jsonb(s.*) FROM public.writing_sessions s WHERE s.id = v_session);
END;
$$;

-- ----------------------------------------------------------------------------
-- 3. Claim an evaluation job — read scope from the session snapshot, derive exam
--    from the study task, and surface prompt_text/source_text to the worker.
--    Signature unchanged from migration 209.
-- ----------------------------------------------------------------------------
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
  v_snap    jsonb;
  v_exam_id uuid;
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
  v_snap := v_session.prompt_snapshot;

  -- exam is a property of the STUDY TASK (study_tasks.exam_id), not the prompt.
  -- NULL for ad-hoc sessions with no study task — safe: the evidence key excludes
  -- exam_id, and every consumer compares it NULL-safely.
  SELECT st.exam_id INTO v_exam_id
    FROM public.study_tasks st WHERE st.id = v_session.study_task_id;

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
    -- Scope + content from the IMMUTABLE session snapshot (not the live prompt).
    'exercise_type',    v_snap->>'exercise_type',
    'topic_id',         (v_snap->>'topic_id')::uuid,
    'exam_id',          v_exam_id,
    'prompt_text',      v_snap->>'prompt_text',
    'source_text',      v_snap->>'source_text',
    'rubric_dimensions', COALESCE(v_snap->'rubric_dimensions', '[]'::jsonb),
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

-- ----------------------------------------------------------------------------
-- 4. Claim a mastery-outbox row — read scope from the session snapshot, derive
--    exam from the study task. Signature unchanged from migration 209.
-- ----------------------------------------------------------------------------
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
  v_snap    jsonb;
  v_exam_id uuid;
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
  v_snap := v_session.prompt_snapshot;

  SELECT st.exam_id INTO v_exam_id
    FROM public.study_tasks st WHERE st.id = v_session.study_task_id;

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
    'topic_id', (v_snap->>'topic_id')::uuid, 'exam_id', v_exam_id,
    'exercise_type', v_snap->>'exercise_type',
    'microtopic_id', v_unit.practice_microtopic_id, 'source_entity_id', v_session.id,
    'has_unresolved_must_fix', v_must_fix, 'resolved_issue_count', v_resolved,
    'issue_projections', v_projs);
END;
$$;

-- ----------------------------------------------------------------------------
-- 5. Server-side re-derived outbox context — read topic/exercise_type from the
--    session snapshot, exam from the study task (LEFT JOIN → NULL when none).
--    RETURNS-TABLE signature unchanged from migration 209 (REPLACE is legal).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ewp_private.ewp_outbox_evidence_context(p_outbox uuid)
RETURNS TABLE(user_id uuid, evaluation_id uuid, topic_id uuid, microtopic_id uuid,
              exam_id uuid, source_type text, source_entity_id uuid)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT o.user_id, e.id,
         (s.prompt_snapshot->>'topic_id')::uuid,
         u.practice_microtopic_id,
         st.exam_id,
         CASE
           WHEN s.prompt_snapshot->>'exercise_type' IN ('sentence_construction','sentence_correction',
                'sentence_rewrite','sentence_reconstruction','vocabulary_in_context')
             THEN 'sentence_drill'
           WHEN s.prompt_snapshot->>'exercise_type' IN ('paragraph_writing','summary_writing',
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
  LEFT JOIN public.study_tasks st ON st.id = s.study_task_id
  WHERE o.id = p_outbox;
$$;

-- ----------------------------------------------------------------------------
-- Grants — preserved from migrations 207/209 (service_role only; private helper
-- stays private). CREATE OR REPLACE already retains ACLs; re-issued for record.
-- ----------------------------------------------------------------------------
REVOKE ALL ON FUNCTION public.ewp_create_writing_session(uuid,uuid,uuid,text,int,text,int,int,uuid,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_create_writing_session(uuid,uuid,uuid,text,int,text,int,int,uuid,jsonb) TO service_role;

REVOKE ALL ON FUNCTION public.ewp_claim_evaluation_job(int, text[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_claim_evaluation_job(int, text[]) TO service_role;

REVOKE ALL ON FUNCTION public.ewp_claim_mastery_outbox(int) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_claim_mastery_outbox(int) TO service_role;

REVOKE ALL ON FUNCTION ewp_private.ewp_outbox_evidence_context(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ewp_private.ewp_outbox_evidence_context(uuid) TO service_role;
