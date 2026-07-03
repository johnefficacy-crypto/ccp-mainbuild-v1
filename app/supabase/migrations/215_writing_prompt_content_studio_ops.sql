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
--      provenance (no exam scope — prompts are subject-scoped now). Topic must be
--      ACTIVE and level='topic'; microtopic ACTIVE, level='microtopic', child.
--   4. cms_create_writing_prompt / cms_review_writing_prompt /
--      cms_update_writing_prompt / cms_bulk_upsert_writing_prompts.
--   5. Exam Assignments write path over writing_prompt_targets, split by the
--      LOCKED J2 authority separation (see below):
--        cms_propose_writing_prompt_target  (manage: create INERT pending_review)
--        cms_review_writing_prompt_target   (review: pending_review→active|excluded)
--        cms_remove_writing_prompt_target   (review: CAS-guarded removal)
--
-- J2 AUTHORITY SEPARATION (locked, docs/status/Manage-Exam-Operational-Editors-
-- Gate-2026-07-01.md §D). `exam_intelligence.manage` NEVER promotes lifecycle /
-- activation / coverage state; `exam_intelligence.review` owns trust/lifecycle
-- transitions. content-studio.md assigns applicability OWNERSHIP to Manage Exam
-- but does NOT supersede that lifecycle split — so making an assignment EFFECTIVE
-- (active|excluded) is a review-authority transition. manage may only PROPOSE an
-- inert `pending_review` assignment (default-deny keeps it inapplicable); review
-- promotes it. This mirrors the topic_prerequisites manage(propose)/review(approve)
-- split already shipped in admin_exam_intel_manage. The router enforces the
-- permission tier; the RPCs enforce the state machine + CAS.
--
-- CONCURRENCY / CAS (authoritative, in-DB — not merely at the API layer):
--   * Prompt review/curation require a NON-NULL `p_expected_updated_at` CAS token
--     and fail closed (409) when omitted — the service-role RPC contract itself
--     cannot bypass the optimistic-lock invariant.
--   * writing_prompt_targets gains an `updated_at` revision token; propose is
--     INSERT-ONLY (a duplicate (prompt,scope) → 409, never a silent overwrite);
--     review/remove take the target's `updated_at` and reject stale writes (409),
--     auditing the EXACT old and new rows (never old_value=NULL on an update).
--   * bulk import takes a per-(subject,external_key) transaction advisory lock so
--     two concurrent FIRST imports of the same key serialize into create-then-
--     unchanged/update instead of one aborting on the unique index.
--
-- Review RE-VALIDATES taxonomy/provenance inside the locked transaction before
-- 'verified' — a topic/document that went inactive/archived after authoring can
-- never be verified.
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
--   P0404 → 404, P0409 → 409 (concurrent_modification | target_exists),
--   P0422 → 422 (invalid_reason | invalid_scope | invalid_target_status |
--                transition_not_allowed | prompt_verified_locked |
--                target_effective_locked | missing_actor_id)

-- ---------------------------------------------------------------------------
-- 1. Idempotency key for bulk import — SUBJECT-scoped (content is reusable
--    across exams; external_key is unique within a subject).
-- ---------------------------------------------------------------------------
-- Preflight: the table + metadata predate this migration, so refuse to create the
-- unique index if live data already holds duplicate (subject_id, external_key)
-- groups — a silent index-creation failure on live would leave the idempotency
-- contract unenforced. Fail loud so the operator dedupes first.
DO $preflight$
DECLARE v_dups int;
BEGIN
    SELECT count(*) INTO v_dups FROM (
        SELECT subject_id, metadata->>'external_key' AS k
        FROM public.writing_prompts
        WHERE (metadata->>'external_key') IS NOT NULL
        GROUP BY subject_id, (metadata->>'external_key')
        HAVING count(*) > 1
    ) d;
    IF v_dups > 0 THEN
        RAISE EXCEPTION 'migration 215 preflight: % duplicate (subject_id, external_key) group(s) exist; dedupe before applying', v_dups
            USING ERRCODE = 'P0422';
    END IF;
END
$preflight$;

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
-- 2b. Applicability revision token (CAS for the Exam Assignments write path).
--     214's writing_prompt_targets has only created_at; add updated_at so
--     status/priority changes are optimistic-lock-guarded and auditable.
-- ---------------------------------------------------------------------------
ALTER TABLE public.writing_prompt_targets
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

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

-- Reject the DROPPED dual-authority scope columns if smuggled back through
-- free-form metadata (exam_id / exam_cycle_id / exam_phase_id) — applicability is
-- writing_prompt_targets' job alone. (external_key is guarded separately: the bulk
-- RPC legitimately sets it; create/update reject it.)
CREATE OR REPLACE FUNCTION ewp_assert_no_scope_metadata(p_metadata jsonb)
RETURNS void LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    IF p_metadata IS NOT NULL
       AND (p_metadata ? 'exam_id' OR p_metadata ? 'exam_cycle_id' OR p_metadata ? 'exam_phase_id') THEN
        RAISE EXCEPTION 'reserved_metadata_key: metadata may not carry exam scope keys (use writing_prompt_targets)' USING ERRCODE = 'P0422';
    END IF;
END;
$$;

-- Coarse in-DB guard for prompt_text + required_words (defense-in-depth behind the
-- API canonicalizer): reject a blank/whitespace prompt, and any required word that
-- is blank, whitespace-only, multi-token (contains whitespace), or a
-- case-insensitive duplicate — content the deterministic runtime can never satisfy.
CREATE OR REPLACE FUNCTION ewp_assert_prompt_content(p_prompt_text text, p_required_words jsonb)
RETURNS void LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE w text; seen text[] := '{}'; k text;
BEGIN
    IF p_prompt_text IS NULL OR btrim(p_prompt_text) = '' THEN
        RAISE EXCEPTION 'invalid_content: prompt_text must not be blank' USING ERRCODE = 'P0422';
    END IF;
    IF p_required_words IS NOT NULL AND p_required_words <> 'null'::jsonb THEN
        IF jsonb_typeof(p_required_words) <> 'array' THEN
            RAISE EXCEPTION 'invalid_content: required_words must be a JSON array' USING ERRCODE = 'P0422';
        END IF;
        FOR w IN SELECT jsonb_array_elements_text(p_required_words) LOOP
            IF w IS NULL OR btrim(w) = '' THEN
                RAISE EXCEPTION 'invalid_content: required_words entries must be non-blank' USING ERRCODE = 'P0422';
            END IF;
            IF btrim(w) ~ '\s' THEN
                RAISE EXCEPTION 'invalid_content: required word % must be a single token', w USING ERRCODE = 'P0422';
            END IF;
            k := lower(btrim(w));
            IF k = ANY(seen) THEN
                RAISE EXCEPTION 'invalid_content: duplicate required word (case-insensitive): %', w USING ERRCODE = 'P0422';
            END IF;
            seen := array_append(seen, k);
        END LOOP;
    END IF;
END;
$$;

-- Subject-scoped canonical validation (NO exam scope — prompts are reusable).
-- Topic must be ACTIVE + level='topic'; microtopic ACTIVE + level='microtopic' +
-- child-of-topic; source document must be a live admin exam-intelligence asset.
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
    IF NOT FOUND OR v_topic.subject_id IS DISTINCT FROM p_subject
       OR v_topic.is_active IS NOT TRUE OR v_topic.level <> 'topic' THEN
        RAISE EXCEPTION 'invalid_scope: topic % must be an active level=topic topic of subject %', p_topic, p_subject
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
        -- NULL-safe positive validation: a NULL scope/kind/status must FAIL (not
        -- fall open through three-valued logic). `IS DISTINCT FROM` + explicit
        -- IS NULL guards ensure an unclassified row can never pass provenance.
        IF NOT FOUND
           OR v_doc.scope IS DISTINCT FROM 'admin_exam_intelligence'
           OR v_doc.document_kind IS NULL
           OR v_doc.document_kind NOT IN ('syllabus','notification','corrigendum','pyq_paper','answer_key','other')
           OR v_doc.status IS NULL
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
    -- external_key is the SYSTEM-OWNED bulk-import identity — a manual create must
    -- never claim one (else it could hijack/collide with a later import).
    IF coalesce(p_payload->'metadata', '{}'::jsonb) ? 'external_key' THEN
        RAISE EXCEPTION 'reserved_metadata_key: metadata.external_key is system-owned (bulk import only)' USING ERRCODE = 'P0422';
    END IF;
    PERFORM ewp_assert_no_scope_metadata(p_payload->'metadata');
    v_rec := jsonb_populate_record(NULL::public.writing_prompts,
        (coalesce(p_payload, '{}'::jsonb) - 'id' - 'created_at' - 'updated_at'
         - 'reviewer_status' - 'is_active'));
    PERFORM ewp_validate_prompt_scope(v_rec.subject_id, v_rec.topic_id, v_rec.microtopic_id, v_rec.source_document_id);
    PERFORM ewp_assert_prompt_content(v_rec.prompt_text, v_rec.required_words);

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
-- 4. Atomic reviewer-status transition (§4.1b; mandatory reason; mandatory
--    content-CAS; scope re-validated before 'verified').
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
    -- Optimistic-lock token is MANDATORY at the authoritative boundary.
    IF p_expected_updated_at IS NULL THEN
        RAISE EXCEPTION 'concurrent_modification: p_expected_updated_at (CAS token) is required' USING ERRCODE = 'P0409';
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
    IF v_prompt.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'concurrent_modification: prompt content changed since read' USING ERRCODE = 'P0409';
    END IF;
    IF NOT (
           (v_prompt.reviewer_status = 'pending'          AND p_new_status IN ('verified','rejected','needs_correction'))
        OR (v_prompt.reviewer_status = 'needs_correction' AND p_new_status IN ('verified','rejected','pending'))
        OR (v_prompt.reviewer_status = 'verified'         AND p_new_status IN ('rejected','needs_correction'))
    ) THEN
        RAISE EXCEPTION 'transition_not_allowed: % -> %', v_prompt.reviewer_status, p_new_status USING ERRCODE = 'P0422';
    END IF;
    -- Re-validate taxonomy/provenance inside the locked txn before verifying:
    -- a topic/document that went inactive/archived after authoring must not verify.
    IF p_new_status = 'verified' THEN
        PERFORM ewp_validate_prompt_scope(v_prompt.subject_id, v_prompt.topic_id, v_prompt.microtopic_id, v_prompt.source_document_id);
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
-- 5. Atomic curation (verified-locked; mandatory updated_at CAS; scope re-validated).
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
    IF p_expected_updated_at IS NULL THEN
        RAISE EXCEPTION 'concurrent_modification: p_expected_updated_at (CAS token) is required' USING ERRCODE = 'P0409';
    END IF;
    PERFORM ewp_assert_reason(p_reason);
    SELECT * INTO v_existing FROM public.writing_prompts WHERE id = p_prompt_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: writing_prompt % does not exist', p_prompt_id USING ERRCODE = 'P0404';
    END IF;
    IF v_existing.reviewer_status = 'verified' THEN
        RAISE EXCEPTION 'prompt_verified_locked: demote via review first' USING ERRCODE = 'P0422';
    END IF;
    IF v_existing.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'concurrent_modification: prompt changed since read' USING ERRCODE = 'P0409';
    END IF;
    v_patch := coalesce(p_patch, '{}'::jsonb) - 'id' - 'reviewer_status' - 'is_active' - 'created_at' - 'updated_at';
    -- external_key is the immutable system-owned import identity: a patch may not
    -- set it to a NEW value, and if the row already has one it is PRESERVED across
    -- a metadata edit (so a curation edit can't orphan the row from a re-import).
    IF v_patch ? 'metadata' THEN
        IF (v_patch->'metadata' ? 'external_key')
           AND (v_patch->'metadata'->>'external_key') IS DISTINCT FROM (v_existing.metadata->>'external_key') THEN
            RAISE EXCEPTION 'reserved_metadata_key: metadata.external_key is system-owned and cannot be changed' USING ERRCODE = 'P0422';
        END IF;
        IF (v_existing.metadata ? 'external_key') THEN
            v_patch := jsonb_set(v_patch, '{metadata,external_key}', v_existing.metadata->'external_key');
        END IF;
        PERFORM ewp_assert_no_scope_metadata(v_patch->'metadata');
    END IF;
    v_new := jsonb_populate_record(v_existing, v_patch);
    PERFORM ewp_validate_prompt_scope(v_new.subject_id, v_new.topic_id, v_new.microtopic_id, v_new.source_document_id);
    PERFORM ewp_assert_prompt_content(v_new.prompt_text, v_new.required_words);

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
--    A per-(subject, external_key) advisory xact lock makes a concurrent first
--    import of the same key serialize (create-then-unchanged/update) rather than
--    one caller aborting on the unique index.
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
        -- Serialize concurrent first-imports of the SAME (subject, key): the lock
        -- is held to txn end, so a racing caller waits and then observes the row.
        PERFORM pg_advisory_xact_lock(hashtext(p_subject_id::text), hashtext(v_ext));
        PERFORM ewp_assert_no_scope_metadata(v_elem->'metadata');
        v_meta := coalesce(v_elem->'metadata', '{}'::jsonb) || jsonb_build_object('external_key', v_ext);
        v_incoming := jsonb_populate_record(NULL::public.writing_prompts,
            (v_elem - 'external_key' - 'id' - 'created_at' - 'updated_at')
            || jsonb_build_object('subject_id', p_subject_id, 'reviewer_status', 'pending', 'is_active', false, 'metadata', v_meta));
        v_incoming.max_rewrite_attempts := coalesce(v_incoming.max_rewrite_attempts, 3);
        PERFORM ewp_validate_prompt_scope(v_incoming.subject_id, v_incoming.topic_id, v_incoming.microtopic_id, v_incoming.source_document_id);
        PERFORM ewp_assert_prompt_content(v_incoming.prompt_text, v_incoming.required_words);

        SELECT * INTO v_existing FROM public.writing_prompts
        WHERE subject_id = p_subject_id AND metadata->>'external_key' = v_ext FOR UPDATE;

        -- On update, MERGE over the existing metadata (incoming wins per-key) so a
        -- re-import refreshes import fields without erasing unrelated provenance
        -- keys the row already carries. external_key is identical on both sides.
        IF v_existing.id IS NOT NULL THEN
            v_incoming.metadata := coalesce(v_existing.metadata, '{}'::jsonb) || v_incoming.metadata;
        END IF;

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
--    J2 authority split: manage PROPOSES inert pending_review; review PROMOTES to
--    active|excluded and REMOVES. See migration header.
-- ---------------------------------------------------------------------------

-- Drop the earlier single-RPC draft (never merged) if a dev applied it.
DROP FUNCTION IF EXISTS cms_set_writing_prompt_target(uuid, boolean, uuid, uuid, uuid, text, numeric, text, uuid, text);

-- 7a. PROPOSE (manage authority, router-gated): INSERT-ONLY inert pending_review
--     assignment. A duplicate (prompt, scope) is a 409 (never a silent overwrite);
--     changing an existing assignment goes through review/remove.
CREATE OR REPLACE FUNCTION cms_propose_writing_prompt_target(
    p_prompt_id uuid, p_is_global boolean, p_exam_family_id uuid, p_exam_id uuid, p_exam_phase_id uuid,
    p_priority numeric, p_reason text, p_actor_user_id uuid, p_actor_email text
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

    -- Reject a duplicate (prompt, scope) up front so the response is a clean 409
    -- with the existing target's id/status rather than a unique-violation.
    SELECT * INTO v_target FROM public.writing_prompt_targets
    WHERE prompt_id = p_prompt_id
      AND is_global = coalesce(p_is_global,false)
      AND exam_family_id IS NOT DISTINCT FROM p_exam_family_id
      AND exam_id IS NOT DISTINCT FROM p_exam_id
      AND exam_phase_id IS NOT DISTINCT FROM p_exam_phase_id
    FOR UPDATE;
    IF FOUND THEN
        RAISE EXCEPTION 'target_exists: an assignment for this (prompt, scope) already exists (id=%, status=%) — review or remove it', v_target.id, v_target.applicability_status USING ERRCODE = 'P0409';
    END IF;

    INSERT INTO public.writing_prompt_targets (prompt_id, is_global, exam_family_id, exam_id, exam_phase_id, applicability_status, priority_score, source_basis, updated_at)
    VALUES (p_prompt_id, coalesce(p_is_global,false), p_exam_family_id, p_exam_id, p_exam_phase_id, 'pending_review', p_priority, 'operator', now())
    RETURNING * INTO v_target;

    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_target_propose', 'writing_prompt_target', v_target.id::text, NULL, to_jsonb(v_target), p_reason)
    RETURNING id INTO v_audit_id;
    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'target_id', v_target.id, 'row', to_jsonb(v_target));
END;
$$;

-- 7b. REVIEW (review authority, router-gated): promote pending_review to an
--     EFFECTIVE state (active|excluded), or flip between them. Mandatory CAS on
--     updated_at; audits exact old and new rows. A global target can never be
--     'excluded' (no broader scope to subtract from).
CREATE OR REPLACE FUNCTION cms_review_writing_prompt_target(
    p_target_id uuid, p_expected_updated_at timestamptz, p_new_status text,
    p_priority numeric, p_reason text, p_actor_user_id uuid, p_actor_email text
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_old public.writing_prompt_targets%ROWTYPE;
    v_new public.writing_prompt_targets%ROWTYPE;
    v_audit_id uuid;
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    IF p_expected_updated_at IS NULL THEN
        RAISE EXCEPTION 'concurrent_modification: p_expected_updated_at (CAS token) is required' USING ERRCODE = 'P0409';
    END IF;
    PERFORM ewp_assert_reason(p_reason);
    IF p_new_status NOT IN ('active','excluded') THEN
        RAISE EXCEPTION 'invalid_target_status: review may only set active|excluded, got %', p_new_status USING ERRCODE = 'P0422';
    END IF;
    SELECT * INTO v_old FROM public.writing_prompt_targets WHERE id = p_target_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: writing_prompt_target % does not exist', p_target_id USING ERRCODE = 'P0404';
    END IF;
    IF v_old.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'concurrent_modification: target changed since read' USING ERRCODE = 'P0409';
    END IF;
    IF p_new_status = 'excluded' AND v_old.is_global THEN
        RAISE EXCEPTION 'invalid_scope: a global assignment cannot be excluded (no broader scope to subtract from)' USING ERRCODE = 'P0422';
    END IF;
    IF v_old.applicability_status NOT IN ('pending_review','active','excluded') THEN
        RAISE EXCEPTION 'transition_not_allowed: % -> %', v_old.applicability_status, p_new_status USING ERRCODE = 'P0422';
    END IF;

    UPDATE public.writing_prompt_targets
       SET applicability_status = p_new_status,
           priority_score = coalesce(p_priority, priority_score),
           source_basis = 'operator',
           updated_at = now()
     WHERE id = p_target_id AND updated_at = p_expected_updated_at
    RETURNING * INTO v_new;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: zero rows updated after lock' USING ERRCODE = 'P0409';
    END IF;

    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_target_review', 'writing_prompt_target', p_target_id::text, to_jsonb(v_old), to_jsonb(v_new), p_reason)
    RETURNING id INTO v_audit_id;
    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'target_id', p_target_id, 'row', to_jsonb(v_new));
END;
$$;

-- 7c. REMOVE (review authority, router-gated): CAS-guarded delete that audits the
--     EXACT removed row (old_value is never NULL on removal).
CREATE OR REPLACE FUNCTION cms_remove_writing_prompt_target(
    p_target_id uuid, p_expected_updated_at timestamptz, p_reason text, p_actor_user_id uuid, p_actor_email text
)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_target public.writing_prompt_targets%ROWTYPE;
    v_audit_id uuid;
    v_deleted int;
BEGIN
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL' USING ERRCODE = 'P0422';
    END IF;
    IF p_expected_updated_at IS NULL THEN
        RAISE EXCEPTION 'concurrent_modification: p_expected_updated_at (CAS token) is required' USING ERRCODE = 'P0409';
    END IF;
    PERFORM ewp_assert_reason(p_reason);
    SELECT * INTO v_target FROM public.writing_prompt_targets WHERE id = p_target_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: writing_prompt_target % does not exist', p_target_id USING ERRCODE = 'P0404';
    END IF;
    IF v_target.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'concurrent_modification: target changed since read' USING ERRCODE = 'P0409';
    END IF;

    INSERT INTO public.admin_audit_logs (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
    VALUES (p_actor_user_id, p_actor_email, p_actor_user_id, 'writing_prompt_target_remove', 'writing_prompt_target', p_target_id::text, to_jsonb(v_target), NULL, p_reason)
    RETURNING id INTO v_audit_id;

    DELETE FROM public.writing_prompt_targets WHERE id = p_target_id AND updated_at = p_expected_updated_at;
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    IF v_deleted = 0 THEN
        RAISE EXCEPTION 'concurrent_modification: target changed before delete' USING ERRCODE = 'P0409';
    END IF;
    RETURN jsonb_build_object('ok', true, 'audit_id', v_audit_id, 'target_id', p_target_id);
END;
$$;

-- Deny all non-service-role access.
REVOKE EXECUTE ON FUNCTION ewp_assert_reason(text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION ewp_assert_reason(text) TO service_role;
REVOKE EXECUTE ON FUNCTION ewp_assert_prompt_content(text, jsonb) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION ewp_assert_prompt_content(text, jsonb) TO service_role;
REVOKE EXECUTE ON FUNCTION ewp_assert_no_scope_metadata(jsonb) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION ewp_assert_no_scope_metadata(jsonb) TO service_role;
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
REVOKE EXECUTE ON FUNCTION cms_propose_writing_prompt_target(uuid, boolean, uuid, uuid, uuid, numeric, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_propose_writing_prompt_target(uuid, boolean, uuid, uuid, uuid, numeric, text, uuid, text) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_review_writing_prompt_target(uuid, timestamptz, text, numeric, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_review_writing_prompt_target(uuid, timestamptz, text, numeric, text, uuid, text) TO service_role;
REVOKE EXECUTE ON FUNCTION cms_remove_writing_prompt_target(uuid, timestamptz, text, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION cms_remove_writing_prompt_target(uuid, timestamptz, text, uuid, text) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
