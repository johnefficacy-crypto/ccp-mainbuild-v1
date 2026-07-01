-- Migration 206: English Writing Practice (EWP-2) — atomic runtime RPCs.
--
-- The practice write paths (create session, submit unit, reopen unit) must be
-- single transactions with the canonical lock order (§8.0: session row, then
-- ALL required units ascending), optimistic version CAS, and an in-transaction
-- session rollup so session status can never lag a committed unit transition.
-- Discrete service-role client calls cannot provide this. These SECURITY
-- DEFINER RPCs are the only supported write path; the backend calls them via
-- PostgREST rpc().
--
-- Legal unit transitions and submittable-status guards are enforced in-DB so a
-- buggy or hostile caller cannot bypass the state machine (§4.4b). The version
-- CAS token is MANDATORY: every submission must name the version it expects to
-- create, which rejects stale and duplicate submissions.
--
-- Finalization (session/unit rollup) is owned by ewp_private.ewp_apply_session_
-- rollup and runs INSIDE the same transaction while the canonical locks are
-- held — at the tail of submit/reopen, and via the transactional
-- ewp_finalize_writing_session RPC after the authoritative coverage row is
-- written. Required-word coverage is read authoritatively in-DB: the current
-- version_set_hash is recomputed under lock (byte-for-byte identical to the
-- backend helper, §4.5a) and a coverage row is trusted only when its pinned
-- hash still matches — the two-check contract (§4.7a) holds under concurrency.
--
-- Migration number: highest on main is 205, so this is 206 (the CI contiguity
-- guard requires 206 here). NOTE: PR #828 also adds a 206 on its own branch;
-- whichever of the two merges SECOND must renumber to 207 via the guard's
-- rename-exemption path (a rename that resolves a duplicate-on-main is allowed).
-- VERIFY DB against schema_migrations before apply (OPERATOR).

-- ===========================================================================
-- Private helpers (ewp_private is NOT exposed via PostgREST — no RPC oracle).
-- ewp_private is created in migration 205; guard defensively so this migration
-- also applies cleanly if run in isolation.
-- ===========================================================================
CREATE SCHEMA IF NOT EXISTS ewp_private;

-- Monotonic outcome ranking (worst -> best); NULL/unknown ranks lowest.
CREATE OR REPLACE FUNCTION ewp_private.ewp_outcome_rank(p_outcome text)
RETURNS int
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE p_outcome
    WHEN 'fully_evaluated'    THEN 2
    WHEN 'deterministic_only' THEN 1
    WHEN 'unscored'           THEN 0
    ELSE -1
  END;
$$;

-- version_set_hash recomputed in-DB, byte-for-byte identical to
-- app.study_os.writing_practice.version_set_hash.compute_version_set_hash:
--   domain "WPS_VERSION_SET_V1\x00" || uint32-be count, then per unit (only
--   units that have at least one version), sorted by unit_number:
--   uint32-be unit_number || 16-byte uuid(unit) || 16-byte uuid(version) ||
--   32 raw bytes of the content hash. int4send/uuid_send give big-endian /
--   RFC-4122 network-order bytes; sha256() is the PG 11+ builtin.
CREATE OR REPLACE FUNCTION ewp_private.ewp_version_set_hash(p_session uuid)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_payload bytea;
  v_count   int;
  rec       record;
BEGIN
  SELECT count(*) INTO v_count
  FROM public.writing_session_units u
  WHERE u.session_id = p_session
    AND EXISTS (SELECT 1 FROM public.writing_unit_versions v WHERE v.unit_id = u.id);

  v_payload := convert_to('WPS_VERSION_SET_V1', 'UTF8') || '\x00'::bytea || int4send(v_count);

  FOR rec IN
    SELECT u.unit_number, u.id AS unit_id, lv.version_id, lv.content_hash
    FROM public.writing_session_units u
    JOIN LATERAL (
      SELECT v.id AS version_id, v.content_hash
      FROM public.writing_unit_versions v
      WHERE v.unit_id = u.id
      ORDER BY v.version_number DESC
      LIMIT 1
    ) lv ON TRUE
    WHERE u.session_id = p_session
    ORDER BY u.unit_number
  LOOP
    v_payload := v_payload
      || int4send(rec.unit_number)
      || uuid_send(rec.unit_id)
      || uuid_send(rec.version_id)
      || decode(lower(btrim(rec.content_hash)), 'hex');
  END LOOP;

  RETURN encode(sha256(v_payload), 'hex');
END;
$$;

-- A failed unit is recoverable while a job for its evaluation can still retry
-- (mirror of session_finalizer._recovery_available; keyed on evaluation_id).
CREATE OR REPLACE FUNCTION ewp_private.ewp_recovery_available(p_evaluation uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT CASE
    WHEN p_evaluation IS NULL THEN TRUE
    WHEN NOT EXISTS (
      SELECT 1 FROM public.writing_evaluation_jobs j WHERE j.evaluation_id = p_evaluation
    ) THEN TRUE
    ELSE EXISTS (
      SELECT 1 FROM public.writing_evaluation_jobs j
      WHERE j.evaluation_id = p_evaluation
        AND COALESCE(j.attempts, 0) < COALESCE(j.max_attempts, 0)
    )
  END;
$$;

-- Whether any effective, unresolved must_fix issue exists on a latest version
-- (§4.6c). Empty until EWP-2B produces language issues; forward-compatible.
CREATE OR REPLACE FUNCTION ewp_private.ewp_has_unresolved_must_fix(p_session uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  WITH latest_ver AS (
    SELECT DISTINCT ON (v.unit_id) v.id
    FROM public.writing_unit_versions v
    JOIN public.writing_session_units u ON u.id = v.unit_id
    WHERE u.session_id = p_session
    ORDER BY v.unit_id, v.version_number DESC
  ),
  ev AS (
    SELECT e.id FROM public.writing_evaluations e
    WHERE e.unit_version_id IN (SELECT id FROM latest_ver)
  ),
  ie AS (
    SELECT i.id FROM public.writing_issue_events i
    WHERE i.evaluation_id IN (SELECT id FROM ev)
      AND i.severity = 'must_fix'
      AND i.affects_current_state = TRUE
  )
  SELECT EXISTS (
    SELECT 1 FROM ie
    WHERE ie.id NOT IN (
      SELECT r.issue_event_id FROM public.writing_issue_resolution_events r
      WHERE r.issue_event_id IN (SELECT id FROM ie) AND r.outcome = 'resolved'
    )
  );
$$;

-- Owner of the session/unit rollup write (§4.3b priority, §9.1a outcome,
-- §4.6c gate). Assumes the CALLER already holds the canonical locks (session
-- row + all units); it performs no locking of its own so it can run at the
-- tail of submit/reopen inside the same transaction, and behind the lock the
-- public ewp_finalize_writing_session RPC acquires. Idempotent + monotonic.
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
BEGIN
  SELECT evaluation_outcome INTO v_cur_outcome
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

  UPDATE public.writing_sessions
  SET status = v_status, evaluation_outcome = v_new_outcome
  WHERE id = p_session
    AND (status IS DISTINCT FROM v_status
         OR evaluation_outcome IS DISTINCT FROM v_new_outcome);

  RETURN jsonb_build_object('status', v_status, 'evaluation_outcome', v_new_outcome);
END;
$$;

-- ===========================================================================
-- create session + units atomically
-- ===========================================================================
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

-- ===========================================================================
-- submit a unit answer atomically (version CAS + evaluation + job + unit state
-- + in-transaction session rollup)
-- ===========================================================================
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

  -- Only legal submit source states (§4.4b): not_started -> draft ->
  -- evaluation_pending and rewrite_required -> evaluation_pending. An already
  -- evaluation_pending unit is NOT resubmittable (a duplicate/retry request
  -- cannot mint another immutable version while an evaluation is in flight).
  IF v_unit.status NOT IN ('not_started','draft','rewrite_required') THEN
    RAISE EXCEPTION 'ewp_not_submittable: unit status % cannot accept a submission', v_unit.status;
  END IF;

  SELECT COALESCE(MAX(version_number), 0) + 1 INTO v_next_version
    FROM public.writing_unit_versions WHERE unit_id = v_unit.id;
  -- Mandatory optimistic concurrency: the caller MUST name the version it
  -- expects to create. A missing token, or a stale/duplicate one, is rejected.
  IF p_expected_version IS NULL THEN
    RAISE EXCEPTION 'ewp_stale_version: expected_version is required (got null; next is %)', v_next_version;
  END IF;
  IF p_expected_version <> v_next_version THEN
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

  -- Walk the legal transition path (§4.4b) — no direct not_started ->
  -- evaluation_pending edge. A first submission is persisted through draft
  -- (not_started -> draft), then every submittable state advances
  -- (draft | rewrite_required) -> evaluation_pending. Both edges are written.
  IF v_unit.status = 'not_started' THEN
    UPDATE public.writing_session_units SET status = 'draft' WHERE id = v_unit.id;
  END IF;
  UPDATE public.writing_session_units SET status = 'evaluation_pending' WHERE id = v_unit.id;

  -- In-transaction rollup: session status can never lag this committed unit
  -- transition (locks are held; §8.0).
  PERFORM ewp_private.ewp_apply_session_rollup(p_session);

  RETURN jsonb_build_object(
    'evaluation', (SELECT to_jsonb(e.*) FROM public.writing_evaluations e WHERE e.id = v_evaluation),
    'version_id', v_version_id,
    'version_number', v_next_version
  );
END;
$$;

-- ===========================================================================
-- reopen a ready unit atomically (optimistic version check + ready->draft +
-- in-transaction session rollup)
-- ===========================================================================
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
  IF v_session_row.status NOT IN ('rewrite_required','active','completed') THEN
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

  -- In-transaction rollup: a reopened unit immediately reflects in session
  -- status (e.g. completed -> active), never leaving a stale completed session.
  PERFORM ewp_private.ewp_apply_session_rollup(p_session);

  RETURN jsonb_build_object('unit_id', p_unit, 'status', 'draft');
END;
$$;

-- ===========================================================================
-- transactional finalizer: acquire canonical locks, then roll up. Called by
-- the backend after the authoritative coverage row is written, so the
-- coverage-informed completion gate is evaluated under the same locks.
-- ===========================================================================
CREATE OR REPLACE FUNCTION public.ewp_finalize_writing_session(
  p_user uuid,
  p_session uuid
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_owner uuid;
BEGIN
  SELECT user_id INTO v_owner FROM public.writing_sessions
    WHERE id = p_session FOR UPDATE;
  IF NOT FOUND OR v_owner <> p_user THEN
    RAISE EXCEPTION 'ewp_not_found: session % not found for user', p_session;
  END IF;

  PERFORM 1 FROM public.writing_session_units
    WHERE session_id = p_session ORDER BY unit_number FOR UPDATE;

  RETURN ewp_private.ewp_apply_session_rollup(p_session);
END;
$$;

-- ===========================================================================
-- grants — service_role only for the public RPCs; private helpers stay private.
-- ===========================================================================
REVOKE ALL ON FUNCTION public.ewp_create_writing_session(uuid,uuid,uuid,text,int,text,int,int,uuid,jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_submit_writing_unit(uuid,uuid,int,text,int,int,text,int,jsonb,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_reopen_writing_unit(uuid,uuid,uuid,uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.ewp_finalize_writing_session(uuid,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_create_writing_session(uuid,uuid,uuid,text,int,text,int,int,uuid,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_submit_writing_unit(uuid,uuid,int,text,int,int,text,int,jsonb,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_reopen_writing_unit(uuid,uuid,uuid,uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.ewp_finalize_writing_session(uuid,uuid) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
