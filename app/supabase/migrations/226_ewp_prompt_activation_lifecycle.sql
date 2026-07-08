-- Migration 226: EWP prompt activation lifecycle (Content Studio).
--
-- Adds the DELIBERATELY-OMITTED activation path that migration 215 left out
-- (215 header §"ACTIVATION IS DELIBERATELY OMITTED"). Migration 214's activation
-- gate deactivated every prompt and blocked reactivation until the applicability
-- resolver + a server-owned runtime-readiness gate could enforce fail-closed
-- activation. Those now exist, so this migration adds TWO atomic, service-role-only
-- SECURITY DEFINER RPCs:
--
--   cms_activate_writing_prompt   — NOT a boolean toggle. Under a row lock it
--     verifies ALL preconditions; on ANY failure it returns a structured
--     {eligible:false, blockers:[...]} result and writes NOTHING. Only when every
--     precondition passes does it set is_active=true, bump updated_at, and audit
--     old→new. The RPC is the SOLE authority that computes eligibility — the API
--     and frontend must NEVER compute it (determinism > heuristics).
--   cms_deactivate_writing_prompt — CAS + reason + audit; sets is_active=false.
--
-- Activation is a NEW authority (content_studio.activate) SEPARATE from authoring
-- (content_studio.author) and review (content_studio.review): making verified
-- content live to aspirants is a distinct, higher-trust act. The router enforces
-- the permission tier; these RPCs enforce the precondition machine + CAS.
--
-- SERVER-OWNED READINESS SIGNALS (constants surfaced to SQL as IMMUTABLE
-- functions — no client-writable settings row, no heuristic):
--   cms_writing_runtime_ready_types()   — the runtime-safe exercise-type allowlist.
--     Starts with ONLY sentence_construction; correction/rewrite/vocab/paragraph
--     stay OUT until their evaluator/rubric gates clear.
--   cms_writing_source_dependent_types()— types whose scoring must consume the
--     source_text (semantic evaluator). Gated by the semantic_evaluator flag.
--   cms_writing_paragraph_types()       — rubric-scored long-form types. Gated by
--     an approved rubric_id AND the paragraph (EWP-6) release gate.
--   cms_writing_gate_open(gate_key)     — the server-side gate flag. Both gates
--     are CLOSED (false) here and fail closed; opening one is a FUTURE migration
--     (CREATE OR REPLACE), never a runtime write — keeps activation deterministic
--     and immutable-once-merged. This is how FF_WRITING_LLM_EVAL "live" state is
--     surfaced to SQL without an AI/heuristic read path.
--
-- Precondition → blocker code (all collected; the caller sees the FULL set):
--   reviewer_status<>'verified'                   -> prompt_not_verified
--   is_active already true                        -> already_active
--   no EFFECTIVE active applicability target       -> no_active_applicability_target
--   exercise_type not in runtime allowlist        -> exercise_type_not_runtime_ready
--   source-dependent type + semantic gate closed  -> semantic_evaluator_not_live
--   paragraph type + rubric_id missing            -> rubric_missing
--   paragraph type + paragraph release gate closed-> paragraph_gate_closed
--   taxonomy/provenance no longer valid           -> invalid_scope
--   p_reason absent / not 8..500 chars            -> reason_required
-- CAS (hard errors, NOT blockers — mapped to HTTP by the router):
--   p_expected_updated_at NULL or mismatched      -> P0409 concurrent_modification (stale_prompt)
--   prompt does not exist                         -> P0404 not_found
--   p_actor_user_id NULL                          -> P0422 missing_actor_id
--
-- Eligibility-blocked returns a NORMAL result row {eligible:false, blockers}
-- (HTTP 200 at the router) — it is a valid answer, not an error. Only CAS/not-
-- found/malformed are exceptions.
--
-- No new tables (RPCs + IMMUTABLE constant functions on existing tables), so no
-- RLS surface is introduced. All functions REVOKE FROM PUBLIC/anon/authenticated
-- and GRANT TO service_role only.
--
-- Migration number: originally authored as 224 but RENUMBERED to 226 — PR #894
-- landed 224_pyq_bulk_import_v2_uniqueness.sql first (and 225_pyq_stimuli_service_
-- role_grant.sql), so 224/225 were taken; 226 is the contiguous MAX+1 slot
-- (.github/workflows/migration-numbers.yml). Apply after 215. Live
-- schema_migrations reconciliation is OPERATOR PENDING.

-- ---------------------------------------------------------------------------
-- Server-owned readiness constants (IMMUTABLE — surfaced to SQL, no client row).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cms_writing_runtime_ready_types()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
    -- Runtime-safe today: deterministic mock runtime fully scores this type.
    SELECT ARRAY['sentence_construction']::text[];
$$;

CREATE OR REPLACE FUNCTION cms_writing_source_dependent_types()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
    -- Scoring must consume source_text (meaning-preserving correction/rewrite);
    -- inactive until the semantic evaluator gate is live.
    SELECT ARRAY[
        'sentence_correction', 'sentence_rewrite', 'sentence_reconstruction',
        'vocabulary_in_context'
    ]::text[];
$$;

CREATE OR REPLACE FUNCTION cms_writing_paragraph_types()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
    -- Rubric-scored long-form; gated by an approved rubric_id + EWP-6 release gate.
    SELECT ARRAY[
        'paragraph_writing', 'summary_writing', 'precis_practice',
        'essay_practice', 'letter_practice'
    ]::text[];
$$;

-- Server-side gate flags. CLOSED here and fail closed; opening a gate is a FUTURE
-- migration (CREATE OR REPLACE), never a runtime write.
CREATE OR REPLACE FUNCTION cms_writing_gate_open(p_gate text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_gate
        WHEN 'semantic_evaluator' THEN false  -- FF_WRITING_LLM_EVAL not live
        WHEN 'paragraph_release'  THEN false  -- EWP-6 §16 release gate not cleared
        ELSE false                            -- unknown gate fails closed
    END;
$$;

-- ---------------------------------------------------------------------------
-- cms_activate_writing_prompt — precondition machine (all blockers collected).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cms_activate_writing_prompt(
    p_prompt_id uuid,
    p_expected_updated_at timestamptz,
    p_reason text,
    p_exercise_runtime_allowlist text[] DEFAULT NULL,
    p_actor_user_id uuid DEFAULT NULL,
    p_actor_email text DEFAULT NULL
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_prompt public.writing_prompts%ROWTYPE;
    v_blockers text[] := '{}';
    v_effective_allowlist text[];
    v_audit_id uuid;
    v_has_active_target boolean;
    v_is_source_dependent boolean;
    v_is_paragraph boolean;
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    -- Optimistic-lock token is MANDATORY and fails closed on NULL (a service-role
    -- caller cannot bypass the invariant). CAS is a HARD error, never a blocker.
    IF p_expected_updated_at IS NULL THEN
        RAISE EXCEPTION 'concurrent_modification: stale_prompt — p_expected_updated_at (CAS token) is required' USING ERRCODE = 'P0409';
    END IF;

    SELECT * INTO v_prompt FROM public.writing_prompts WHERE id = p_prompt_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: writing_prompt % does not exist', p_prompt_id USING ERRCODE = 'P0404';
    END IF;
    IF v_prompt.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'concurrent_modification: stale_prompt — prompt changed since read' USING ERRCODE = 'P0409';
    END IF;

    -- ---- collect ALL blockers (no short-circuit) --------------------------
    IF p_reason IS NULL OR length(btrim(p_reason)) < 8 OR length(btrim(p_reason)) > 500 THEN
        v_blockers := array_append(v_blockers, 'reason_required');
    END IF;

    IF v_prompt.reviewer_status IS DISTINCT FROM 'verified' THEN
        v_blockers := array_append(v_blockers, 'prompt_not_verified');
    END IF;

    IF v_prompt.is_active IS TRUE THEN
        v_blockers := array_append(v_blockers, 'already_active');
    END IF;

    -- Default-deny applicability (resolver semantics): a prompt with no ACTIVE
    -- target is UNASSIGNED and can never be launched, so it must not activate.
    SELECT EXISTS (
        SELECT 1 FROM public.writing_prompt_targets
        WHERE prompt_id = p_prompt_id AND applicability_status = 'active'
    ) INTO v_has_active_target;
    IF NOT v_has_active_target THEN
        v_blockers := array_append(v_blockers, 'no_active_applicability_target');
    END IF;

    -- Runtime-readiness allowlist is SERVER-OWNED. An optional caller allowlist
    -- may only NARROW it (intersection) — it can never widen the server set.
    v_effective_allowlist := cms_writing_runtime_ready_types();
    IF p_exercise_runtime_allowlist IS NOT NULL THEN
        SELECT coalesce(array_agg(t), '{}') INTO v_effective_allowlist
        FROM unnest(v_effective_allowlist) t
        WHERE t = ANY(p_exercise_runtime_allowlist);
    END IF;
    IF NOT (v_prompt.exercise_type = ANY(v_effective_allowlist)) THEN
        v_blockers := array_append(v_blockers, 'exercise_type_not_runtime_ready');
    END IF;

    v_is_source_dependent := v_prompt.exercise_type = ANY(cms_writing_source_dependent_types());
    v_is_paragraph := v_prompt.exercise_type = ANY(cms_writing_paragraph_types());

    -- Source-dependent types cannot be scored until the semantic evaluator is live.
    IF v_is_source_dependent AND NOT cms_writing_gate_open('semantic_evaluator') THEN
        v_blockers := array_append(v_blockers, 'semantic_evaluator_not_live');
    END IF;

    -- Paragraph types need an approved rubric AND the EWP-6 release gate.
    IF v_is_paragraph THEN
        IF v_prompt.rubric_id IS NULL THEN
            v_blockers := array_append(v_blockers, 'rubric_missing');
        END IF;
        IF NOT cms_writing_gate_open('paragraph_release') THEN
            v_blockers := array_append(v_blockers, 'paragraph_gate_closed');
        END IF;
    END IF;

    -- Taxonomy / provenance must STILL be valid (a topic/document that went
    -- inactive/archived after verification must not activate). ewp_validate_prompt_scope
    -- RAISES on failure; capture it as a blocker instead of aborting.
    BEGIN
        PERFORM ewp_validate_prompt_scope(
            v_prompt.subject_id, v_prompt.topic_id, v_prompt.microtopic_id, v_prompt.source_document_id);
    EXCEPTION WHEN OTHERS THEN
        v_blockers := array_append(v_blockers, 'invalid_scope');
    END;

    -- ---- fail closed: on ANY blocker, write NOTHING -----------------------
    IF array_length(v_blockers, 1) IS NOT NULL THEN
        RETURN jsonb_build_object('eligible', false, 'prompt_id', p_prompt_id, 'blockers', to_jsonb(v_blockers));
    END IF;

    -- ---- all preconditions pass: activate + audit old→new -----------------
    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_activate', 'writing_prompt', p_prompt_id::text,
            jsonb_build_object('is_active', v_prompt.is_active, 'reviewer_status', v_prompt.reviewer_status),
            jsonb_build_object('is_active', true, 'reviewer_status', v_prompt.reviewer_status, 'reason', p_reason),
            p_reason)
    RETURNING id INTO v_audit_id;

    UPDATE public.writing_prompts SET is_active = true, updated_at = now()
    WHERE id = p_prompt_id AND updated_at = p_expected_updated_at AND reviewer_status = 'verified';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: stale_prompt — zero rows updated after lock' USING ERRCODE = 'P0409';
    END IF;

    RETURN jsonb_build_object('eligible', true, 'ok', true, 'audit_id', v_audit_id, 'prompt_id', p_prompt_id, 'is_active', true);
END;
$$;

-- ---------------------------------------------------------------------------
-- cms_deactivate_writing_prompt — CAS + reason + audit; sets is_active=false.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cms_deactivate_writing_prompt(
    p_prompt_id uuid,
    p_expected_updated_at timestamptz,
    p_reason text,
    p_actor_user_id uuid DEFAULT NULL,
    p_actor_email text DEFAULT NULL
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_prompt public.writing_prompts%ROWTYPE;
    v_audit_id uuid;
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    IF p_expected_updated_at IS NULL THEN
        RAISE EXCEPTION 'concurrent_modification: stale_prompt — p_expected_updated_at (CAS token) is required' USING ERRCODE = 'P0409';
    END IF;
    PERFORM ewp_assert_reason(p_reason);

    SELECT * INTO v_prompt FROM public.writing_prompts WHERE id = p_prompt_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: writing_prompt % does not exist', p_prompt_id USING ERRCODE = 'P0404';
    END IF;
    IF v_prompt.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'concurrent_modification: stale_prompt — prompt changed since read' USING ERRCODE = 'P0409';
    END IF;

    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_deactivate', 'writing_prompt', p_prompt_id::text,
            jsonb_build_object('is_active', v_prompt.is_active, 'reviewer_status', v_prompt.reviewer_status),
            jsonb_build_object('is_active', false, 'reviewer_status', v_prompt.reviewer_status, 'reason', p_reason),
            p_reason)
    RETURNING id INTO v_audit_id;

    UPDATE public.writing_prompts SET is_active = false, updated_at = now()
    WHERE id = p_prompt_id AND updated_at = p_expected_updated_at;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: stale_prompt — zero rows updated after lock' USING ERRCODE = 'P0409';
    END IF;

    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'prompt_id', p_prompt_id, 'is_active', false);
END;
$$;

-- ---------------------------------------------------------------------------
-- Service-role-only privilege matrix.
-- ---------------------------------------------------------------------------
REVOKE EXECUTE ON FUNCTION cms_writing_runtime_ready_types() FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_writing_runtime_ready_types() TO service_role;
REVOKE EXECUTE ON FUNCTION cms_writing_source_dependent_types() FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_writing_source_dependent_types() TO service_role;
REVOKE EXECUTE ON FUNCTION cms_writing_paragraph_types() FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_writing_paragraph_types() TO service_role;
REVOKE EXECUTE ON FUNCTION cms_writing_gate_open(text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_writing_gate_open(text) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_activate_writing_prompt(uuid, timestamptz, text, text[], uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_activate_writing_prompt(uuid, timestamptz, text, text[], uuid, text) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_deactivate_writing_prompt(uuid, timestamptz, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_deactivate_writing_prompt(uuid, timestamptz, text, uuid, text) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
