-- Migration 215: Content Studio — writing-prompt operations (subject-scoped)
--
-- Follows the content-scoping architecture locked by migration 214
-- (`214_writing_prompt_content_scoping.sql`) + docs/architecture/content-studio.md:
--   * CONTENT (writing_prompts) is SUBJECT-scoped — no exam columns (214 dropped
--     exam_id/exam_cycle_id/exam_phase_id). Authored/governed in Content Studio.
--   * APPLICABILITY is carried by writing_prompt_targets (214), default-deny.
--
-- This migration adds the operator write path for Content Studio, all as atomic
-- SECURITY DEFINER service-role-only RPCs (audit + mutation in one txn):
--   1. idempotency index for bulk import — SUBJECT-scoped external_key.
--   2. activation-integrity CHECK (is_active ⇒ verified).
--   3. ewp_validate_prompt_scope() — subject/topic/microtopic + source_document
--      provenance (no exam scope — prompts are subject-scoped now).
--   4. cms_create_writing_prompt / cms_review_writing_prompt /
--      cms_update_writing_prompt / cms_bulk_upsert_writing_prompts.
--   5. cms_set_writing_prompt_target / cms_remove_writing_prompt_target — the
--      Exam Assignments write path over writing_prompt_targets.
--
-- ACTIVATION IS DELIBERATELY OMITTED. Migration 214's activation gate
-- deactivated every prompt and blocks REACTIVATION until the applicability
-- resolver + session/planner enforcement + writing_prompts_public_read
-- replacement land (a later PR). Adding an activate path here would reopen the
-- exact fail-open bypass 214 closed, so create/review keep is_active=false and
-- there is no cms_set_writing_prompt_active in this migration.
--
-- Migration number: filesystem max on main is 214 → 215 is the contiguous slot
-- (CI `validate`). The live schema_migrations max is operator-attested at 212;
-- OPERATOR apply order: pending 213 → 214 → 215. No rename permitted.
--
-- Error ERRCODE tokens → HTTP:
--   P0404 → 404, P0409 → 409,
--   P0422 → 422 (invalid_reason | invalid_scope | invalid_target_status |
--                transition_not_allowed | prompt_verified_locked | missing_actor_id)

-- ---------------------------------------------------------------------------
-- 1. Idempotency key for bulk import — SUBJECT-scoped (content is reusable
--    across exams; external_key is unique within a subject).
-- ---------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS uq_writing_prompts_external_key
  ON public.writing_prompts (subject_id, (metadata->>'external_key'))
  WHERE (metadata->>'external_key') IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 2. Activation integrity (compatible with 214's fail-closed deactivation).
-- ---------------------------------------------------------------------------
ALTER TABLE public.writing_prompts
  DROP CONSTRAINT IF EXISTS writing_prompts_active_requires_verified;
ALTER TABLE public.writing_prompts
  ADD CONSTRAINT writing_prompts_active_requires_verified
  CHECK (is_active = false OR reviewer_status = 'verified');

-- ---------------------------------------------------------------------------
-- Shared helpers.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ewp_assert_reason(p_reason text)
RETURNS void LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    IF p_reason IS NULL OR length(btrim(p_reason)) < 8 OR length(btrim(p_reason)) > 500 THEN
        RAISE EXCEPTION 'invalid_reason: reason must be 8-500 characters' USING ERRCODE = 'P0422';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION ewp_writing_prompt_content_differs(
    a public.writing_prompts, b public.writing_prompts)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
    SELECT a.subject_id IS DISTINCT FROM b.subject_id
        OR a.topic_id IS DISTINCT FROM b.topic_id
        OR a.microtopic_id IS DISTINCT FROM b.microtopic_id
        OR a.exercise_type IS DISTINCT FROM b.exercise_type
        OR a.prompt_text IS DISTINCT FROM b.prompt_text
        OR a.source_text IS DISTINCT FROM b.source_text
        OR a.required_words IS DISTINCT FROM b.required_words
        OR a.required_sentence_count IS DISTINCT FROM b.required_sentence_count
        OR a.difficulty_level IS DISTINCT FROM b.difficulty_level
        OR a.min_words IS DISTINCT FROM b.min_words
        OR a.max_words IS DISTINCT FROM b.max_words
        OR coalesce(a.max_rewrite_attempts, 3) IS DISTINCT FROM coalesce(b.max_rewrite_attempts, 3)
        OR a.rubric_id IS DISTINCT FROM b.rubric_id
        OR a.source_document_id IS DISTINCT FROM b.source_document_id
        OR a.metadata IS DISTINCT FROM b.metadata;
$$;

-- Subject-scoped canonical validation (NO exam scope — prompts are reusable).
CREATE OR REPLACE FUNCTION ewp_validate_prompt_scope(
    p_subject uuid, p_topic uuid, p_microtopic uuid, p_document uuid DEFAULT NULL
)
RETURNS void LANGUAGE plpgsql STABLE SET search_path = public AS $$
DECLARE
    v_subj  public.subjects%ROWTYPE;
    v_topic public.topics%ROWTYPE;
    v_micro public.topics%ROWTYPE;
    v_doc   public.document_assets%ROWTYPE;
BEGIN
    SELECT * INTO v_subj FROM public.subjects WHERE id = p_subject;
    IF NOT FOUND OR v_subj.is_active IS NOT TRUE OR v_subj.slug <> 'english-language' THEN
        RAISE EXCEPTION 'invalid_scope: subject % must be the active english-language subject', p_subject
            USING ERRCODE = 'P0422';
    END IF;
    SELECT * INTO v_topic FROM public.topics WHERE id = p_topic;
    IF NOT FOUND OR v_topic.subject_id IS DISTINCT FROM p_subject THEN
        RAISE EXCEPTION 'invalid_scope: topic % does not belong to subject %', p_topic, p_subject
            USING ERRCODE = 'P0422';
    END IF;
    IF p_microtopic IS NOT NULL THEN
        SELECT * INTO v_micro FROM public.topics WHERE id = p_microtopic;
        IF NOT FOUND OR v_micro.is_active IS NOT TRUE OR v_micro.level <> 'microtopic'
           OR v_micro.parent_topic_id IS DISTINCT FROM p_topic
           OR v_micro.subject_id IS DISTINCT FROM p_subject THEN
            RAISE EXCEPTION 'invalid_scope: microtopic % must be active, level=microtopic and a child of topic %',
                p_microtopic, p_topic USING ERRCODE = 'P0422';
        END IF;
    END IF;
    IF p_document IS NOT NULL THEN
        SELECT * INTO v_doc FROM public.document_assets WHERE id = p_document;
        IF NOT FOUND
           OR v_doc.scope <> 'admin_exam_intelligence'
           OR v_doc.document_kind NOT IN ('syllabus','notification','corrigendum','pyq_paper','answer_key','other')
           OR v_doc.status IN ('failed','archived')
           OR coalesce(btrim(v_doc.storage_bucket), '') = ''
           OR coalesce(btrim(v_doc.storage_path), '') = '' THEN
            RAISE EXCEPTION 'invalid_scope: source_document_id % is not a valid admin exam-intelligence document', p_document
                USING ERRCODE = 'P0422';
        END IF;
    END IF;
END;
$$;

-- ---------------------------------------------------------------------------
-- 3. Atomic create (insert + audit; forced pending/inactive).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cms_create_writing_prompt(
    p_payload jsonb, p_reason text, p_actor_user_id uuid, p_actor_email text
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_rec public.writing_prompts%ROWTYPE;
    v_new public.writing_prompts%ROWTYPE;
    v_audit_id uuid;
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    PERFORM ewp_assert_reason(p_reason);
    v_rec := jsonb_populate_record(NULL::public.writing_prompts,
        (coalesce(p_payload, '{}'::jsonb) - 'id' - 'created_at' - 'updated_at'
         - 'reviewer_status' - 'is_active'));
    PERFORM ewp_validate_prompt_scope(v_rec.subject_id, v_rec.topic_id, v_rec.microtopic_id, v_rec.source_document_id);

    INSERT INTO public.writing_prompts (
        subject_id, topic_id, microtopic_id, exercise_type, prompt_text, source_text,
        required_words, required_sentence_count, difficulty_level, min_words, max_words,
        max_rewrite_attempts, rubric_id, reviewer_status, is_active, source_document_id, metadata)
    VALUES (
        v_rec.subject_id, v_rec.topic_id, v_rec.microtopic_id, v_rec.exercise_type, v_rec.prompt_text,
        v_rec.source_text, v_rec.required_words, v_rec.required_sentence_count, v_rec.difficulty_level,
        v_rec.min_words, v_rec.max_words, coalesce(v_rec.max_rewrite_attempts, 3), v_rec.rubric_id,
        'pending', false, v_rec.source_document_id, coalesce(v_rec.metadata, '{}'::jsonb))
    RETURNING * INTO v_new;

    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_create', 'writing_prompt', v_new.id::text,
            NULL, jsonb_build_object('row', to_jsonb(v_new), 'reason', p_reason), p_reason)
    RETURNING id INTO v_audit_id;

    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'prompt_id', v_new.id, 'row', to_jsonb(v_new));
END;
$$;

-- ---------------------------------------------------------------------------
-- 4. Atomic reviewer-status transition (§4.1b; mandatory reason; content-CAS).
--    is_active is only ever cleared here (never set) — activation is gated.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cms_review_writing_prompt(
    p_prompt_id uuid, p_expected_status text, p_expected_updated_at timestamptz,
    p_new_status text, p_reason text, p_reviewer_notes text,
    p_actor_user_id uuid, p_actor_email text
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_prompt public.writing_prompts%ROWTYPE;
    v_audit_id uuid;
    v_new_active boolean;
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    PERFORM ewp_assert_reason(p_reason);
    IF p_new_status NOT IN ('pending','verified','rejected','needs_correction') THEN
        RAISE EXCEPTION 'invalid_target_status: %', p_new_status USING ERRCODE = 'P0422';
    END IF;
    SELECT * INTO v_prompt FROM public.writing_prompts WHERE id = p_prompt_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: writing_prompt % does not exist', p_prompt_id USING ERRCODE = 'P0404';
    END IF;
    IF v_prompt.reviewer_status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION 'concurrent_modification: expected reviewer_status=% found %', p_expected_status, v_prompt.reviewer_status USING ERRCODE = 'P0409';
    END IF;
    IF p_expected_updated_at IS NOT NULL AND v_prompt.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'concurrent_modification: prompt content changed since read' USING ERRCODE = 'P0409';
    END IF;
    IF NOT (
           (v_prompt.reviewer_status = 'pending'          AND p_new_status IN ('verified','rejected','needs_correction'))
        OR (v_prompt.reviewer_status = 'needs_correction' AND p_new_status IN ('verified','rejected','pending'))
        OR (v_prompt.reviewer_status = 'verified'         AND p_new_status IN ('rejected','needs_correction'))
    ) THEN
        RAISE EXCEPTION 'transition_not_allowed: % -> %', v_prompt.reviewer_status, p_new_status USING ERRCODE = 'P0422';
    END IF;
    v_new_active := CASE WHEN p_new_status = 'verified' THEN v_prompt.is_active ELSE false END;

    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_status_transition', 'writing_prompt', p_prompt_id::text,
            jsonb_build_object('reviewer_status', p_expected_status, 'is_active', v_prompt.is_active),
            jsonb_build_object('reviewer_status', p_new_status, 'is_active', v_new_active, 'reason', p_reason, 'reviewer_notes', p_reviewer_notes),
            p_reason)
    RETURNING id INTO v_audit_id;

    UPDATE public.writing_prompts SET reviewer_status = p_new_status, is_active = v_new_active, updated_at = now()
    WHERE id = p_prompt_id AND reviewer_status = p_expected_status;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: zero rows updated after lock' USING ERRCODE = 'P0409';
    END IF;
    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'prompt_id', p_prompt_id,
        'prev_status', p_expected_status, 'new_status', p_new_status, 'is_active', v_new_active);
END;
$$;

-- ---------------------------------------------------------------------------
-- 5. Atomic curation (verified-locked; updated_at CAS; scope re-validated).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cms_update_writing_prompt(
    p_prompt_id uuid, p_expected_updated_at timestamptz, p_patch jsonb,
    p_reason text, p_actor_user_id uuid, p_actor_email text
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_existing public.writing_prompts%ROWTYPE;
    v_new public.writing_prompts%ROWTYPE;
    v_patch jsonb;
    v_audit_id uuid;
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    PERFORM ewp_assert_reason(p_reason);
    SELECT * INTO v_existing FROM public.writing_prompts WHERE id = p_prompt_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: writing_prompt % does not exist', p_prompt_id USING ERRCODE = 'P0404';
    END IF;
    IF v_existing.reviewer_status = 'verified' THEN
        RAISE EXCEPTION 'prompt_verified_locked: demote via review first' USING ERRCODE = 'P0422';
    END IF;
    IF p_expected_updated_at IS NOT NULL AND v_existing.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'concurrent_modification: prompt changed since read' USING ERRCODE = 'P0409';
    END IF;
    v_patch := coalesce(p_patch, '{}'::jsonb) - 'id' - 'reviewer_status' - 'is_active' - 'created_at' - 'updated_at';
    v_new := jsonb_populate_record(v_existing, v_patch);
    PERFORM ewp_validate_prompt_scope(v_new.subject_id, v_new.topic_id, v_new.microtopic_id, v_new.source_document_id);

    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_update', 'writing_prompt', p_prompt_id::text,
            to_jsonb(v_existing), jsonb_build_object('patch', v_patch, 'reason', p_reason), p_reason)
    RETURNING id INTO v_audit_id;

    UPDATE public.writing_prompts SET
        subject_id = v_new.subject_id, topic_id = v_new.topic_id, microtopic_id = v_new.microtopic_id,
        exercise_type = v_new.exercise_type, prompt_text = v_new.prompt_text, source_text = v_new.source_text,
        required_words = v_new.required_words, required_sentence_count = v_new.required_sentence_count,
        difficulty_level = v_new.difficulty_level, min_words = v_new.min_words, max_words = v_new.max_words,
        max_rewrite_attempts = v_new.max_rewrite_attempts, rubric_id = v_new.rubric_id,
        source_document_id = v_new.source_document_id, metadata = v_new.metadata, updated_at = now()
    WHERE id = p_prompt_id AND reviewer_status <> 'verified';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: prompt became verified after lock' USING ERRCODE = 'P0409';
    END IF;
    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'prompt_id', p_prompt_id);
END;
$$;

-- ---------------------------------------------------------------------------
-- 6. Transactional, lifecycle-safe bulk upsert (subject-scoped external_key).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cms_bulk_upsert_writing_prompts(
    p_subject_id uuid, p_rows jsonb, p_reason text, p_actor_user_id uuid, p_actor_email text
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_elem jsonb; v_ext text; v_meta jsonb;
    v_incoming public.writing_prompts%ROWTYPE;
    v_existing public.writing_prompts%ROWTYPE;
    v_created int := 0; v_updated int := 0; v_unchanged int := 0;
    v_audit_id uuid; v_seen text[] := '{}';
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    PERFORM ewp_assert_reason(p_reason);
    IF p_subject_id IS NULL THEN
        RAISE EXCEPTION 'invalid_target_status: p_subject_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    IF jsonb_typeof(p_rows) <> 'array' OR jsonb_array_length(p_rows) = 0 THEN
        RAISE EXCEPTION 'invalid_target_status: p_rows must be a non-empty array' USING ERRCODE = 'P0422';
    END IF;

    FOR v_elem IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
        v_ext := nullif(btrim(coalesce(v_elem->>'external_key', '')), '');
        IF v_ext IS NULL THEN
            RAISE EXCEPTION 'invalid_target_status: every bulk row requires a non-blank external_key' USING ERRCODE = 'P0422';
        END IF;
        IF v_ext = ANY(v_seen) THEN
            RAISE EXCEPTION 'invalid_target_status: duplicate external_key in batch: %', v_ext USING ERRCODE = 'P0422';
        END IF;
        v_seen := array_append(v_seen, v_ext);
        v_meta := coalesce(v_elem->'metadata', '{}'::jsonb) || jsonb_build_object('external_key', v_ext);
        v_incoming := jsonb_populate_record(NULL::public.writing_prompts,
            (v_elem - 'external_key' - 'id' - 'created_at' - 'updated_at')
            || jsonb_build_object('subject_id', p_subject_id, 'reviewer_status', 'pending', 'is_active', false, 'metadata', v_meta));
        v_incoming.max_rewrite_attempts := coalesce(v_incoming.max_rewrite_attempts, 3);
        PERFORM ewp_validate_prompt_scope(v_incoming.subject_id, v_incoming.topic_id, v_incoming.microtopic_id, v_incoming.source_document_id);

        SELECT * INTO v_existing FROM public.writing_prompts
        WHERE subject_id = p_subject_id AND metadata->>'external_key' = v_ext FOR UPDATE;

        IF v_existing.id IS NULL THEN
            INSERT INTO public.writing_prompts (
                subject_id, topic_id, microtopic_id, exercise_type, prompt_text, source_text,
                required_words, required_sentence_count, difficulty_level, min_words, max_words,
                max_rewrite_attempts, rubric_id, reviewer_status, is_active, source_document_id, metadata)
            VALUES (
                p_subject_id, v_incoming.topic_id, v_incoming.microtopic_id, v_incoming.exercise_type, v_incoming.prompt_text,
                v_incoming.source_text, v_incoming.required_words, v_incoming.required_sentence_count, v_incoming.difficulty_level,
                v_incoming.min_words, v_incoming.max_words, v_incoming.max_rewrite_attempts, v_incoming.rubric_id,
                'pending', false, v_incoming.source_document_id, v_incoming.metadata);
            v_created := v_created + 1;
        ELSIF NOT ewp_writing_prompt_content_differs(v_existing, v_incoming) THEN
            v_unchanged := v_unchanged + 1;
        ELSIF v_existing.reviewer_status IN ('pending', 'needs_correction') THEN
            UPDATE public.writing_prompts SET
                topic_id = v_incoming.topic_id, microtopic_id = v_incoming.microtopic_id,
                exercise_type = v_incoming.exercise_type, prompt_text = v_incoming.prompt_text, source_text = v_incoming.source_text,
                required_words = v_incoming.required_words, required_sentence_count = v_incoming.required_sentence_count,
                difficulty_level = v_incoming.difficulty_level, min_words = v_incoming.min_words, max_words = v_incoming.max_words,
                max_rewrite_attempts = v_incoming.max_rewrite_attempts, rubric_id = v_incoming.rubric_id,
                source_document_id = v_incoming.source_document_id, metadata = v_incoming.metadata,
                reviewer_status = 'pending', is_active = false, updated_at = now()
            WHERE id = v_existing.id;
            v_updated := v_updated + 1;
        ELSE
            RAISE EXCEPTION 'bulk_locked_row: external_key % is % — changed content needs explicit review/clone', v_ext, v_existing.reviewer_status USING ERRCODE = 'P0422';
        END IF;
    END LOOP;

    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_bulk_upsert', 'writing_prompt', p_subject_id::text, NULL,
            jsonb_build_object('subject_id', p_subject_id, 'created', v_created, 'updated', v_updated, 'unchanged', v_unchanged, 'reason', p_reason), p_reason)
    RETURNING id INTO v_audit_id;
    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'created', v_created, 'updated', v_updated, 'unchanged', v_unchanged);
END;
$$;

-- ---------------------------------------------------------------------------
-- 7. Exam Assignments — writing_prompt_targets write path (applicability).
--    Upsert a single (prompt, scope) row; status active|excluded|pending_review.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cms_set_writing_prompt_target(
    p_prompt_id uuid, p_is_global boolean, p_exam_family_id uuid, p_exam_id uuid, p_exam_phase_id uuid,
    p_status text, p_priority numeric, p_reason text, p_actor_user_id uuid, p_actor_email text
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_target public.writing_prompt_targets%ROWTYPE;
    v_audit_id uuid;
    v_scope_count int;
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    PERFORM ewp_assert_reason(p_reason);
    IF coalesce(p_status, 'active') NOT IN ('active','excluded','pending_review') THEN
        RAISE EXCEPTION 'invalid_target_status: %', p_status USING ERRCODE = 'P0422';
    END IF;
    -- exactly one scope (mirror the table CHECK so we can give a clean 422)
    v_scope_count := (CASE WHEN coalesce(p_is_global,false) THEN 1 ELSE 0 END)
                   + (CASE WHEN p_exam_family_id IS NOT NULL THEN 1 ELSE 0 END)
                   + (CASE WHEN p_exam_id IS NOT NULL THEN 1 ELSE 0 END)
                   + (CASE WHEN p_exam_phase_id IS NOT NULL THEN 1 ELSE 0 END);
    IF v_scope_count <> 1 THEN
        RAISE EXCEPTION 'invalid_scope: exactly one of {is_global, exam_family_id, exam_id, exam_phase_id} required' USING ERRCODE = 'P0422';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.writing_prompts WHERE id = p_prompt_id) THEN
        RAISE EXCEPTION 'not_found: writing_prompt % does not exist', p_prompt_id USING ERRCODE = 'P0404';
    END IF;
    IF p_exam_family_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.exam_families WHERE id = p_exam_family_id) THEN
        RAISE EXCEPTION 'invalid_scope: exam_family % does not exist', p_exam_family_id USING ERRCODE = 'P0422';
    END IF;
    IF p_exam_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.exams WHERE id = p_exam_id) THEN
        RAISE EXCEPTION 'invalid_scope: exam % does not exist', p_exam_id USING ERRCODE = 'P0422';
    END IF;
    IF p_exam_phase_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.exam_phases WHERE id = p_exam_phase_id) THEN
        RAISE EXCEPTION 'invalid_scope: exam_phase % does not exist', p_exam_phase_id USING ERRCODE = 'P0422';
    END IF;

    INSERT INTO public.writing_prompt_targets (prompt_id, is_global, exam_family_id, exam_id, exam_phase_id, applicability_status, priority_score, source_basis)
    VALUES (p_prompt_id, coalesce(p_is_global,false), p_exam_family_id, p_exam_id, p_exam_phase_id, coalesce(p_status,'active'), p_priority, 'operator')
    ON CONFLICT (prompt_id, is_global, exam_family_id, exam_id, exam_phase_id)
    DO UPDATE SET applicability_status = EXCLUDED.applicability_status, priority_score = EXCLUDED.priority_score, source_basis = 'operator'
    RETURNING * INTO v_target;

    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_target_set', 'writing_prompt_target', v_target.id::text, NULL, to_jsonb(v_target), p_reason)
    RETURNING id INTO v_audit_id;
    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'target_id', v_target.id, 'row', to_jsonb(v_target));
END;
$$;

CREATE OR REPLACE FUNCTION cms_remove_writing_prompt_target(
    p_target_id uuid, p_reason text, p_actor_user_id uuid, p_actor_email text
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_target public.writing_prompt_targets%ROWTYPE;
    v_audit_id uuid;
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    PERFORM ewp_assert_reason(p_reason);
    SELECT * INTO v_target FROM public.writing_prompt_targets WHERE id = p_target_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: writing_prompt_target % does not exist', p_target_id USING ERRCODE = 'P0404';
    END IF;
    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_target_remove', 'writing_prompt_target', p_target_id::text, to_jsonb(v_target), NULL, p_reason)
    RETURNING id INTO v_audit_id;
    DELETE FROM public.writing_prompt_targets WHERE id = p_target_id;
    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'target_id', p_target_id);
END;
$$;

-- Deny all non-service-role access.
REVOKE EXECUTE ON FUNCTION ewp_assert_reason(text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION ewp_assert_reason(text) TO service_role;
REVOKE EXECUTE ON FUNCTION ewp_writing_prompt_content_differs(public.writing_prompts, public.writing_prompts) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION ewp_writing_prompt_content_differs(public.writing_prompts, public.writing_prompts) TO service_role;
REVOKE EXECUTE ON FUNCTION ewp_validate_prompt_scope(uuid, uuid, uuid, uuid) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION ewp_validate_prompt_scope(uuid, uuid, uuid, uuid) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_create_writing_prompt(jsonb, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_create_writing_prompt(jsonb, text, uuid, text) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_review_writing_prompt(uuid, text, timestamptz, text, text, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_review_writing_prompt(uuid, text, timestamptz, text, text, text, uuid, text) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_update_writing_prompt(uuid, timestamptz, jsonb, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_update_writing_prompt(uuid, timestamptz, jsonb, text, uuid, text) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_bulk_upsert_writing_prompts(uuid, jsonb, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_bulk_upsert_writing_prompts(uuid, jsonb, text, uuid, text) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_set_writing_prompt_target(uuid, boolean, uuid, uuid, uuid, text, numeric, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_set_writing_prompt_target(uuid, boolean, uuid, uuid, uuid, text, numeric, text, uuid, text) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_remove_writing_prompt_target(uuid, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_remove_writing_prompt_target(uuid, text, uuid, text) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
