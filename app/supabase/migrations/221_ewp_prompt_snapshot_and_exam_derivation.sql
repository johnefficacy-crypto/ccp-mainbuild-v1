-- 221_ewp_prompt_snapshot_and_exam_derivation.sql
-- Fix EWP pipeline breakage from migration 214 (dropped writing_prompts.exam_id).
-- v_prompt.exam_id/exercise_type/topic_id/rubric_id reads in ewp_claim_evaluation_job,
-- ewp_claim_mastery_outbox, ewp_private.ewp_outbox_evidence_context now RAISE.
--
-- Fix: pin an immutable per-session context at creation time.
--   * writing_sessions.prompt_snapshot jsonb: {schema_version, exercise_type,
--     topic_id, prompt_text, source_text, required_words, required_sentence_count,
--     difficulty_level, min_words, max_words, rubric_dimensions}. Runtime
--     (claim RPCs + writing_practice.py resume/submit) reads scope/content from
--     here — never the live prompt — so a later prompt edit cannot retro-change
--     an in-flight/historical session.
--   * writing_sessions.exam_id / exam_phase_id: resolved ONCE from the study
--     task at creation (the same context validated for applicability at
--     launch) and pinned — not re-derived from mutable study_tasks at each
--     async stage (claim/drain), which could otherwise attribute evidence to a
--     different exam if the task's exam_id changes or the task is deleted
--     (ON DELETE SET NULL) between launch and drain.
--   * Both are guarded immutable by ewp_guard_session_snapshot() (extended;
--     same trigger, CREATE OR REPLACE of the function body only).
-- Evidence-key exclusion of exam_id (evidence_deriver/ewp_compute_evidence_key)
-- is unaffected; idempotency holds regardless of exam provenance.
--
-- No landed migration edited. 205/209/214 untouched; forward CREATE OR REPLACE
-- only. Signatures unchanged so ACLs are preserved (re-issued for the record).

-- 1. Pinned immutable session context.
ALTER TABLE public.writing_sessions
  ADD COLUMN IF NOT EXISTS prompt_snapshot jsonb,
  ADD COLUMN IF NOT EXISTS exam_id uuid REFERENCES public.exams(id),
  ADD COLUMN IF NOT EXISTS exam_phase_id uuid REFERENCES public.exam_phases(id);

COMMENT ON COLUMN public.writing_sessions.prompt_snapshot IS
  'Immutable copy of prompt scope/content/constraints captured at session '
  'creation (schema_version, exercise_type, topic_id, prompt_text, source_text, '
  'required_words, required_sentence_count, difficulty_level, min_words, '
  'max_words, rubric_dimensions). Runtime reads from here, never the live '
  'prompt. Guarded immutable by ewp_guard_session_snapshot().';
COMMENT ON COLUMN public.writing_sessions.exam_id IS
  'Exam context resolved from the launch study_task ONCE at creation and '
  'pinned — not re-derived from study_tasks at claim/drain time. Guarded '
  'immutable by ewp_guard_session_snapshot().';

-- Backfill existing sessions from their current prompt + study task.
UPDATE public.writing_sessions s
SET prompt_snapshot = jsonb_build_object(
      'schema_version', 1,
      'exercise_type', p.exercise_type,
      'topic_id', p.topic_id,
      'prompt_text', p.prompt_text,
      'source_text', p.source_text,
      'required_words', COALESCE(p.required_words, '[]'::jsonb),
      'required_sentence_count', p.required_sentence_count,
      'difficulty_level', p.difficulty_level,
      'min_words', p.min_words,
      'max_words', p.max_words,
      'rubric_dimensions', COALESCE(
        (SELECT r.dimensions FROM public.writing_rubrics r WHERE r.id = p.rubric_id),
        '[]'::jsonb))
FROM public.writing_prompts p
WHERE p.id = s.prompt_id
  AND s.prompt_snapshot IS NULL;

UPDATE public.writing_sessions s
SET exam_id = st.exam_id, exam_phase_id = st.exam_phase_id
FROM public.study_tasks st
WHERE st.id = s.study_task_id
  AND s.study_task_id IS NOT NULL
  AND s.exam_id IS NULL;

ALTER TABLE public.writing_sessions
  ALTER COLUMN prompt_snapshot SET NOT NULL;

-- 2. Extend the session-snapshot guard to cover the new pinned fields. Same
--    trigger (CREATE TRIGGER ... EXECUTE FUNCTION ...) picks up the new body
--    automatically — CREATE OR REPLACE preserves the function's oid.
CREATE OR REPLACE FUNCTION public.ewp_guard_session_snapshot()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.projection_revision IS DISTINCT FROM OLD.projection_revision
     OR NEW.feedback_release_policy IS DISTINCT FROM OLD.feedback_release_policy
     OR NEW.feedback_release_delay_seconds IS DISTINCT FROM OLD.feedback_release_delay_seconds THEN
    RAISE EXCEPTION 'session_snapshot_immutable: projection_revision / feedback_release_policy / feedback_release_delay_seconds cannot change after creation';
  END IF;
  IF NEW.prompt_snapshot IS DISTINCT FROM OLD.prompt_snapshot THEN
    RAISE EXCEPTION 'session_snapshot_immutable: prompt_snapshot cannot change after creation';
  END IF;
  IF NEW.exam_id IS DISTINCT FROM OLD.exam_id
     OR NEW.exam_phase_id IS DISTINCT FROM OLD.exam_phase_id THEN
    RAISE EXCEPTION 'session_snapshot_immutable: exam_id / exam_phase_id cannot change after creation';
  END IF;
  RETURN NEW;
END;
$$;

-- 3. Capture the pinned snapshot + exam context at session creation.
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
  v_exam_id uuid;
  v_exam_phase_id uuid;
  i int;
BEGIN
  IF p_mode <> 'learning' THEN
    RAISE EXCEPTION 'ewp_mode_unsupported: mode % is not available in EWP-2', p_mode;
  END IF;

  SELECT jsonb_build_object(
           'schema_version', 1,
           'exercise_type', p.exercise_type,
           'topic_id', p.topic_id,
           'prompt_text', p.prompt_text,
           'source_text', p.source_text,
           'required_words', COALESCE(p.required_words, '[]'::jsonb),
           'required_sentence_count', p.required_sentence_count,
           'difficulty_level', p.difficulty_level,
           'min_words', p.min_words,
           'max_words', p.max_words,
           'rubric_dimensions', COALESCE(
             (SELECT r.dimensions FROM public.writing_rubrics r WHERE r.id = p.rubric_id),
             '[]'::jsonb))
    INTO v_snapshot
    FROM public.writing_prompts p
    WHERE p.id = p_prompt;
  IF v_snapshot IS NULL THEN
    RAISE EXCEPTION 'ewp_prompt_not_found: %', p_prompt;
  END IF;

  -- Pin the exam context ONCE, from the same study task the caller validated
  -- prompt applicability against at launch (§17). NULL for ad-hoc sessions.
  IF p_study_task IS NOT NULL THEN
    SELECT st.exam_id, st.exam_phase_id INTO v_exam_id, v_exam_phase_id
      FROM public.study_tasks st WHERE st.id = p_study_task;
  END IF;

  INSERT INTO public.writing_sessions(
    user_id, study_task_id, prompt_id, mode, status, projection_revision,
    feedback_release_policy, feedback_release_delay_seconds, prompt_snapshot,
    exam_id, exam_phase_id)
  VALUES (p_user, p_study_task, p_prompt, p_mode, 'active', p_projection_revision,
          p_policy, p_delay, v_snapshot, v_exam_id, v_exam_phase_id)
  RETURNING id INTO v_session;

  FOR i IN 1 .. GREATEST(p_unit_count, 1) LOOP
    INSERT INTO public.writing_session_units(
      session_id, unit_number, practice_microtopic_id, unit_constraints, status)
    VALUES (v_session, i, p_microtopic, COALESCE(p_constraints, '{"schema_version":1}'::jsonb), 'not_started');
  END LOOP;

  RETURN (SELECT to_jsonb(s.*) FROM public.writing_sessions s WHERE s.id = v_session);
END;
$$;

-- 4. Claim an evaluation job — read scope from the snapshot, exam from the
--    PINNED session column (not a live study_tasks re-derivation).
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
    RETURN NULL;
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

  SELECT MAX(version_number) INTO v_maxver
  FROM public.writing_unit_versions WHERE unit_id = v_unit.id;
  v_is_current := (v_ver.version_number = v_maxver);

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
    'microtopic_id',    v_unit.practice_microtopic_id,
    'session_id',       v_session.id,
    'user_id',          v_session.user_id,
    'mode',             v_session.mode,
    'projection_revision', v_session.projection_revision,
    'exercise_type',    v_snap->>'exercise_type',
    'topic_id',         (v_snap->>'topic_id')::uuid,
    'exam_id',          v_session.exam_id,
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

-- 5. Claim a mastery-outbox row — exam from the PINNED session column.
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

  v_must_fix := EXISTS (
    SELECT 1 FROM public.writing_issue_events i
    WHERE i.evaluation_id = v_eval.id AND i.severity = 'must_fix' AND i.affects_current_state = TRUE);
  SELECT count(*)::int INTO v_resolved FROM public.writing_issue_resolution_events r
  WHERE r.resolving_evaluation_id = v_eval.id AND r.outcome = 'resolved';

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
    'topic_id', (v_snap->>'topic_id')::uuid, 'exam_id', v_session.exam_id,
    'exercise_type', v_snap->>'exercise_type',
    'microtopic_id', v_unit.practice_microtopic_id, 'source_entity_id', v_session.id,
    'has_unresolved_must_fix', v_must_fix, 'resolved_issue_count', v_resolved,
    'issue_projections', v_projs);
END;
$$;

-- 6. Server-side re-derived outbox context — exam from the PINNED session
--    column (no study_tasks join needed anymore).
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
         s.exam_id,
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
  WHERE o.id = p_outbox;
$$;

-- Grants — preserved from migrations 207/209 (service_role only).
REVOKE ALL ON FUNCTION public.ewp_create_writing_session(uuid,uuid,uuid,text,int,text,int,int,uuid,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_create_writing_session(uuid,uuid,uuid,text,int,text,int,int,uuid,jsonb) TO service_role;

REVOKE ALL ON FUNCTION public.ewp_claim_evaluation_job(int, text[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_claim_evaluation_job(int, text[]) TO service_role;

REVOKE ALL ON FUNCTION public.ewp_claim_mastery_outbox(int) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_claim_mastery_outbox(int) TO service_role;

REVOKE ALL ON FUNCTION ewp_private.ewp_outbox_evidence_context(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ewp_private.ewp_outbox_evidence_context(uuid) TO service_role;
