-- Migration 206: English Writing Practice (EWP-2) — atomic runtime RPCs.
--
-- The practice write paths (create session, submit unit, reopen unit) must be
-- single transactions with the canonical lock order (§8.0: session row, then
-- ALL required units ascending) and optimistic version CAS. Discrete
-- service-role client calls cannot provide this. These SECURITY DEFINER RPCs
-- are the only supported write path; the backend calls them via PostgREST rpc().
--
-- Legal unit transitions and submittable-status guards are enforced in-DB so a
-- buggy caller cannot bypass the state machine (§4.4b).
--
-- Migration number: highest existing is 205; this is 206. VERIFY DB against
-- schema_migrations before apply (OPERATOR).

-- ---------------------------------------------------------------------------
-- create session + units atomically
-- ---------------------------------------------------------------------------
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
  i int;
BEGIN
  IF p_mode <> 'learning' THEN
    -- EWP-2 ships learning mode only; exam runtime is a later slice (§9.2).
    RAISE EXCEPTION 'ewp_mode_unsupported: mode % is not available in EWP-2', p_mode;
  END IF;

  INSERT INTO public.writing_sessions(
    user_id, study_task_id, prompt_id, mode, status, projection_revision,
    feedback_release_policy, feedback_release_delay_seconds)
  VALUES (p_user, p_study_task, p_prompt, p_mode, 'active', p_projection_revision,
          p_policy, p_delay)
  RETURNING id INTO v_session;

  FOR i IN 1 .. GREATEST(p_unit_count, 1) LOOP
    INSERT INTO public.writing_session_units(
      session_id, unit_number, practice_microtopic_id, unit_constraints, status)
    VALUES (v_session, i, p_microtopic, COALESCE(p_constraints, '{"schema_version":1}'::jsonb), 'not_started');
  END LOOP;

  RETURN (SELECT to_jsonb(s.*) FROM public.writing_sessions s WHERE s.id = v_session);
END;
$$;

-- ---------------------------------------------------------------------------
-- submit a unit answer atomically (version CAS + evaluation + job + unit state)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.ewp_submit_writing_unit(
  p_user uuid,
  p_session uuid,
  p_unit_number int,
  p_answer text,
  p_client_wc int,
  p_server_wc int,
  p_content_hash text,
  p_expected_version int,
  p_det_result jsonb,
  p_det_version text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_session_row  public.writing_sessions%ROWTYPE;
  v_unit         public.writing_session_units%ROWTYPE;
  v_next_version int;
  v_version_id   uuid;
  v_evaluation   uuid;
BEGIN
  -- Canonical lock order: session row FIRST, then ALL units ascending.
  SELECT * INTO v_session_row FROM public.writing_sessions
    WHERE id = p_session AND user_id = p_user FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ewp_not_found: session % not found for user', p_session;
  END IF;
  IF v_session_row.status IN ('completed','abandoned') THEN
    RAISE EXCEPTION 'ewp_session_closed: session is not open for submission';
  END IF;

  PERFORM 1 FROM public.writing_session_units
    WHERE session_id = p_session ORDER BY unit_number FOR UPDATE;

  SELECT * INTO v_unit FROM public.writing_session_units
    WHERE session_id = p_session AND unit_number = p_unit_number;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ewp_not_found: unit % not found', p_unit_number;
  END IF;
  IF v_unit.status NOT IN ('not_started','draft','rewrite_required','evaluation_pending') THEN
    RAISE EXCEPTION 'ewp_not_submittable: unit status % cannot accept a submission', v_unit.status;
  END IF;

  SELECT COALESCE(MAX(version_number), 0) + 1 INTO v_next_version
    FROM public.writing_unit_versions WHERE unit_id = v_unit.id;
  -- Optimistic concurrency: caller's expected version must match (rejects stale
  -- or duplicate submissions racing on the same next version).
  IF p_expected_version IS NOT NULL AND p_expected_version <> v_next_version THEN
    RAISE EXCEPTION 'ewp_stale_version: expected % but next is %', p_expected_version, v_next_version;
  END IF;

  INSERT INTO public.writing_unit_versions(
    unit_id, version_number, answer_text, client_word_count, server_word_count,
    submission_kind, content_hash)
  VALUES (v_unit.id, v_next_version, p_answer, p_client_wc, p_server_wc, 'user', p_content_hash)
  RETURNING id INTO v_version_id;

  INSERT INTO public.writing_evaluations(
    unit_version_id, evaluation_revision, deterministic_evaluator_version,
    deterministic_status, language_status, overall_status, deterministic_result)
  VALUES (v_version_id, 1, p_det_version, 'completed', 'queued', 'partial', p_det_result)
  RETURNING id INTO v_evaluation;

  INSERT INTO public.writing_evaluation_jobs(evaluation_id, job_kind, generation, status)
  VALUES (v_evaluation, 'language_evaluation', 1, 'pending');

  -- Legal transition -> evaluation_pending (§4.4b).
  UPDATE public.writing_session_units SET status = 'evaluation_pending' WHERE id = v_unit.id;

  RETURN jsonb_build_object(
    'evaluation', (SELECT to_jsonb(e.*) FROM public.writing_evaluations e WHERE e.id = v_evaluation),
    'version_id', v_version_id,
    'version_number', v_next_version
  );
END;
$$;

-- ---------------------------------------------------------------------------
-- reopen a ready unit atomically (optimistic version check + ready->draft)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.ewp_reopen_writing_unit(
  p_user uuid,
  p_session uuid,
  p_unit uuid,
  p_expected_latest_version uuid
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_session_row public.writing_sessions%ROWTYPE;
  v_unit        public.writing_session_units%ROWTYPE;
  v_latest      uuid;
BEGIN
  SELECT * INTO v_session_row FROM public.writing_sessions
    WHERE id = p_session AND user_id = p_user FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ewp_not_found: session % not found for user', p_session;
  END IF;
  IF v_session_row.mode <> 'learning' THEN
    RAISE EXCEPTION 'ewp_reopen_forbidden: reopen is learning-mode only';
  END IF;
  IF v_session_row.status NOT IN ('rewrite_required','active') THEN
    RAISE EXCEPTION 'ewp_reopen_forbidden: session is not reopenable';
  END IF;

  PERFORM 1 FROM public.writing_session_units
    WHERE session_id = p_session ORDER BY unit_number FOR UPDATE;

  SELECT * INTO v_unit FROM public.writing_session_units
    WHERE id = p_unit AND session_id = p_session;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'ewp_not_found: unit % not found', p_unit;
  END IF;
  IF v_unit.status <> 'ready' THEN
    RAISE EXCEPTION 'ewp_reopen_forbidden: only a ready unit can be reopened';
  END IF;

  SELECT id INTO v_latest FROM public.writing_unit_versions
    WHERE unit_id = p_unit ORDER BY version_number DESC LIMIT 1;
  IF v_latest IS DISTINCT FROM p_expected_latest_version THEN
    RAISE EXCEPTION 'ewp_stale_version: expected_latest_version_id is stale';
  END IF;

  UPDATE public.writing_session_units SET status = 'draft' WHERE id = p_unit;
  RETURN jsonb_build_object('unit_id', p_unit, 'status', 'draft');
END;
$$;

REVOKE ALL ON FUNCTION public.ewp_create_writing_session(uuid,uuid,uuid,text,int,text,int,int,uuid,jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_submit_writing_unit(uuid,uuid,int,text,int,int,text,int,jsonb,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_reopen_writing_unit(uuid,uuid,uuid,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_create_writing_session(uuid,uuid,uuid,text,int,text,int,int,uuid,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_submit_writing_unit(uuid,uuid,int,text,int,int,text,int,jsonb,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_reopen_writing_unit(uuid,uuid,uuid,uuid) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
