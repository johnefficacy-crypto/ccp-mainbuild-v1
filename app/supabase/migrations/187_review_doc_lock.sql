-- Migration 187: lock document_assets during review; revalidate provenance in projection
--
-- Blocker 3 of PR #756 review: review_pyq_paper() locked pyq_papers but read
-- document_assets without a lock.  A concurrent UPDATE on document_assets
-- (e.g. status → failed, storage cleared) between the pyq_papers lock acquisition
-- and the document SELECT could race the provenance gate.
--
-- Changes:
--   A. review_pyq_paper()              — adds FOR UPDATE to document_assets SELECT (step 6c)
--   B. project_pyq_question_to_mock_bank() — adds step 2a: revalidate source_document_id
--        before projecting (defence-in-depth: prevents a projection from running if the
--        document was archived after the paper was verified)

-- ── A. review_pyq_paper() — document row lock ──────────────────────────────────

CREATE OR REPLACE FUNCTION review_pyq_paper(
    p_paper_id        text,
    p_expected_status text,
    p_target_status   text,
    p_reason          text,
    p_actor_id        text,
    p_actor_email     text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_paper          pyq_papers%ROWTYPE;
    v_doc            document_assets%ROWTYPE;
    v_audit_id       uuid;
    v_updated        pyq_papers%ROWTYPE;
    v_reason_trimmed text;
    v_blocking       text[];
BEGIN
    -- 1. Validate reason length before touching the DB.
    IF p_reason IS NULL THEN
        RAISE EXCEPTION 'invalid_reason: reason must not be null'
            USING ERRCODE = 'P0422';
    END IF;
    v_reason_trimmed := trim(p_reason);
    IF length(v_reason_trimmed) < 8 OR length(v_reason_trimmed) > 500 THEN
        RAISE EXCEPTION 'invalid_reason: reason must be 8-500 characters (got %)',
            length(v_reason_trimmed)
            USING ERRCODE = 'P0422';
    END IF;

    -- 2. Validate target status is a known value.
    IF p_target_status NOT IN ('verified', 'rejected', 'pending') THEN
        RAISE EXCEPTION 'invalid_target_status: % is not a recognised trust_status',
            p_target_status
            USING ERRCODE = 'P0422';
    END IF;

    -- 3. Lock the paper row for the duration of this transaction.
    SELECT * INTO v_paper
    FROM public.pyq_papers
    WHERE id = p_paper_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: paper % does not exist', p_paper_id
            USING ERRCODE = 'P0404';
    END IF;

    -- 4. Concurrent-modification guard.
    IF v_paper.trust_status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION 'concurrent_modification: expected trust_status=% but found %. Re-fetch and retry.',
            p_expected_status, v_paper.trust_status
            USING ERRCODE = 'P0409';
    END IF;

    -- 5. Validate transition.
    IF NOT (
           (v_paper.trust_status = 'pending'  AND p_target_status IN ('verified', 'rejected'))
        OR (v_paper.trust_status = 'verified' AND p_target_status = 'rejected')
        OR (v_paper.trust_status = 'rejected' AND p_target_status = 'pending')
    ) THEN
        RAISE EXCEPTION 'transition_not_allowed: % -> % is not a permitted transition',
            v_paper.trust_status, p_target_status
            USING ERRCODE = 'P0422';
    END IF;

    -- 6. Provenance gate re-validated on the locked row.
    IF v_paper.trust_status = 'pending' AND p_target_status = 'verified' THEN
        v_blocking := ARRAY[]::text[];

        -- (a) source_type must be known
        IF v_paper.source_type IS NULL OR v_paper.source_type = 'unknown' THEN
            v_blocking := v_blocking || ARRAY['source_type'];
        END IF;

        -- (b) at least one provenance anchor required
        IF (v_paper.source_url IS NULL OR trim(v_paper.source_url) = '')
           AND v_paper.source_document_id IS NULL THEN
            v_blocking := v_blocking || ARRAY['source_url'];
        END IF;

        -- (c) validate + LOCK attached document when present.
        --     FOR UPDATE ensures a concurrent document status/storage change
        --     cannot race the validation below.
        IF v_paper.source_document_id IS NOT NULL THEN
            SELECT * INTO v_doc
            FROM public.document_assets
            WHERE id = v_paper.source_document_id
            FOR UPDATE;

            IF NOT FOUND THEN
                v_blocking := v_blocking || ARRAY['source_document_id_not_found'];
            ELSE
                IF v_doc.scope != 'admin_exam_intelligence' THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_wrong_scope'];
                END IF;
                IF v_doc.document_kind != 'pyq_paper' THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_wrong_kind'];
                END IF;
                IF v_doc.status IN ('failed', 'archived') THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_bad_status'];
                END IF;
                IF coalesce(trim(v_doc.storage_bucket), '') = ''
                   OR coalesce(trim(v_doc.storage_path), '') = '' THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_no_storage'];
                END IF;
                IF (v_doc.metadata->>'exam_id') IS NOT NULL
                   AND (v_doc.metadata->>'exam_id') != ''
                   AND (v_doc.metadata->>'exam_id') IS DISTINCT FROM v_paper.exam_id::text THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_exam_mismatch'];
                END IF;
            END IF;
        END IF;

        IF array_length(v_blocking, 1) > 0 THEN
            RAISE EXCEPTION 'provenance_incomplete: blocking_fields=%',
                array_to_string(v_blocking, ',')
                USING ERRCODE = 'P0422';
        END IF;
    END IF;

    -- 7. Insert audit row within the same transaction.
    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, action, entity_type, entity_id,
        new_value, notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'exam_intel.cms.pyq_paper.review',
        'pyq_paper',
        p_paper_id,
        jsonb_build_object(
            'from_status', p_expected_status,
            'to_status',   p_target_status,
            'reason',      v_reason_trimmed,
            'reviewed_by', p_actor_email,
            'reviewed_at', now()::text
        ),
        'admin_exam_intel_cms'
    )
    RETURNING id INTO v_audit_id;

    -- 8. Update paper status.
    UPDATE public.pyq_papers
    SET    trust_status = p_target_status,
           updated_at   = now()
    WHERE  id           = p_paper_id::uuid
    AND    trust_status = p_expected_status
    RETURNING * INTO v_updated;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: zero rows updated after lock'
            USING ERRCODE = 'P0409';
    END IF;

    RETURN jsonb_build_object(
        'ok',       true,
        'audit_id', v_audit_id,
        'row',      to_jsonb(v_updated)
    );
END;
$$;

REVOKE EXECUTE ON FUNCTION review_pyq_paper(text, text, text, text, text, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION review_pyq_paper(text, text, text, text, text, text) FROM anon;
REVOKE EXECUTE ON FUNCTION review_pyq_paper(text, text, text, text, text, text) FROM authenticated;
GRANT  EXECUTE ON FUNCTION review_pyq_paper(text, text, text, text, text, text) TO service_role;


-- ── B. project_pyq_question_to_mock_bank() — provenance revalidation ───────────
--
-- New step 2a: if source_document_id is set on the paper, verify the document
-- is still in a signable state before creating or updating the projection.
-- This prevents a projection from being written if the document was archived
-- after the paper was verified.

CREATE OR REPLACE FUNCTION public.project_pyq_question_to_mock_bank(
    p_pyq_question_id uuid,
    p_actor_id        uuid,
    p_audit_reason    text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $fn$
DECLARE
    v_q           record;
    v_primary_tag record;
    v_topic       record;

    v_content_hash        text;
    v_correct_count       integer;
    v_option_count        integer;
    v_verified_opt_count  integer;
    v_empty_opt_count     integer;
    v_primary_tag_count   integer;

    v_projection record;
    v_mock_q_id  uuid;
    v_is_new     boolean := false;
    v_outcome    text;

    v_correct_opt_id uuid;

    v_opt_row    record;
    v_new_opt_id uuid;
BEGIN
    IF p_audit_reason IS NULL OR length(trim(p_audit_reason)) < 8 THEN
        RETURN jsonb_build_object(
            'outcome', 'error',
            'error',   'audit_reason_required',
            'detail',  'p_audit_reason must be at least 8 non-blank characters'
        );
    END IF;

    -- 1. Load and lock canonical source rows
    SELECT
        q.id,
        q.pyq_paper_id,
        q.question_number,
        q.question_text,
        q.question_type,
        q.correct_option_id     AS pyq_correct_option_id,
        q.explanation_text,
        q.observed_difficulty,
        q.expected_solve_time_sec,
        q.language,
        q.reviewer_status       AS q_reviewer_status,
        q.metadata              AS q_metadata,
        p.exam_id,
        p.year                  AS paper_year,
        p.trust_status          AS paper_trust_status,
        p.source_url            AS paper_source_url,
        p.source_type           AS paper_source_type,
        p.source_document_id    AS paper_source_document_id
    INTO v_q
    FROM public.pyq_questions q
    JOIN public.pyq_papers    p ON p.id = q.pyq_paper_id
    WHERE q.id = p_pyq_question_id
    FOR UPDATE OF q, p;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'outcome',         'error',
            'error',           'question_not_found',
            'pyq_question_id', p_pyq_question_id
        );
    END IF;

    -- 2. Eligibility checks

    IF v_q.paper_trust_status != 'verified' THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'paper_not_verified');
        RETURN jsonb_build_object(
            'outcome',            'blocked',
            'reason',             'paper_not_verified',
            'paper_trust_status', v_q.paper_trust_status,
            'pyq_question_id',    p_pyq_question_id
        );
    END IF;

    -- 2a. Revalidate source_document_id when present (defence-in-depth).
    --     review_pyq_paper() validates under lock at verification time; this
    --     step catches documents that were archived after the paper was verified.
    IF v_q.paper_source_document_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.document_assets
            WHERE id            = v_q.paper_source_document_id
              AND scope         = 'admin_exam_intelligence'
              AND document_kind = 'pyq_paper'
              AND status        NOT IN ('failed', 'archived')
              AND coalesce(trim(storage_bucket), '') != ''
              AND coalesce(trim(storage_path),  '') != ''
        ) THEN
            PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'source_document_invalid');
            RETURN jsonb_build_object(
                'outcome',            'blocked',
                'reason',             'source_document_invalid',
                'source_document_id', v_q.paper_source_document_id,
                'pyq_question_id',    p_pyq_question_id
            );
        END IF;
    END IF;

    IF v_q.q_reviewer_status != 'verified' THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'question_not_verified');
        RETURN jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'question_not_verified',
            'reviewer_status', v_q.q_reviewer_status,
            'pyq_question_id', p_pyq_question_id
        );
    END IF;

    IF v_q.question_type != 'mcq' THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'not_mcq');
        RETURN jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'not_mcq',
            'question_type',   v_q.question_type,
            'pyq_question_id', p_pyq_question_id
        );
    END IF;

    IF coalesce(trim(v_q.question_text), '') = '' THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'empty_question_text');
        RETURN jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'empty_question_text',
            'pyq_question_id', p_pyq_question_id
        );
    END IF;

    SELECT
        count(*)                                                                AS total,
        count(*) FILTER (WHERE reviewer_status = 'verified')                   AS verified_count,
        count(*) FILTER (WHERE reviewer_status = 'verified' AND is_correct)    AS correct_verified_count,
        count(*) FILTER (
            WHERE reviewer_status = 'verified'
              AND coalesce(trim(option_text), '') = ''
        )                                                                       AS empty_text_count
    INTO v_option_count, v_verified_opt_count, v_correct_count, v_empty_opt_count
    FROM public.pyq_options
    WHERE question_id = p_pyq_question_id;

    IF v_verified_opt_count < 2 THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'insufficient_verified_options');
        RETURN jsonb_build_object(
            'outcome',               'blocked',
            'reason',                'insufficient_verified_options',
            'verified_option_count', v_verified_opt_count,
            'pyq_question_id',       p_pyq_question_id
        );
    END IF;

    IF v_empty_opt_count > 0 THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'empty_verified_option_text');
        RETURN jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'empty_verified_option_text',
            'empty_opt_count', v_empty_opt_count,
            'pyq_question_id', p_pyq_question_id
        );
    END IF;

    IF v_correct_count != 1 THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'not_exactly_one_verified_correct_option');
        RETURN jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'not_exactly_one_verified_correct_option',
            'correct_count',   v_correct_count,
            'pyq_question_id', p_pyq_question_id
        );
    END IF;

    IF v_q.pyq_correct_option_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.pyq_options
            WHERE question_id     = p_pyq_question_id
              AND reviewer_status = 'verified'
              AND is_correct      = true
              AND id              = v_q.pyq_correct_option_id
        ) THEN
            PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'correct_option_id_mismatch');
            RETURN jsonb_build_object(
                'outcome',           'blocked',
                'reason',            'correct_option_id_mismatch',
                'stated_correct_id', v_q.pyq_correct_option_id,
                'pyq_question_id',   p_pyq_question_id
            );
        END IF;
    END IF;

    SELECT count(*)
    INTO v_primary_tag_count
    FROM public.pyq_question_topic_tags
    WHERE question_id     = p_pyq_question_id
      AND tag_role        = 'primary'
      AND reviewer_status = 'verified';

    IF v_primary_tag_count != 1 THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'primary_topic_tag_count_not_one');
        RETURN jsonb_build_object(
            'outcome',           'blocked',
            'reason',            'primary_topic_tag_count_not_one',
            'primary_tag_count', v_primary_tag_count,
            'pyq_question_id',   p_pyq_question_id
        );
    END IF;

    SELECT t.*
    INTO v_primary_tag
    FROM public.pyq_question_topic_tags t
    WHERE t.question_id     = p_pyq_question_id
      AND t.tag_role        = 'primary'
      AND t.reviewer_status = 'verified'
    LIMIT 1;

    SELECT s.*
    INTO v_topic
    FROM public.topics s
    WHERE s.id = v_primary_tag.topic_id
      AND s.is_active = true
    LIMIT 1;

    IF NOT FOUND THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'primary_topic_invalid_or_inactive');
        RETURN jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'primary_topic_invalid_or_inactive',
            'topic_id',        v_primary_tag.topic_id,
            'pyq_question_id', p_pyq_question_id
        );
    END IF;

    IF v_topic.subject_id IS NULL THEN
        PERFORM public.fn_block_projection_for_question(p_pyq_question_id, 'primary_topic_has_no_subject');
        RETURN jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'primary_topic_has_no_subject',
            'topic_id',        v_primary_tag.topic_id,
            'pyq_question_id', p_pyq_question_id
        );
    END IF;

    -- 3. Compute source content hash
    SELECT encode(
        sha256((
            coalesce(lower(trim(v_q.question_text)), '') || chr(0) ||
            coalesce(lower(trim(v_q.explanation_text)), '') || chr(0) ||
            (CASE WHEN lower(trim(coalesce(v_q.observed_difficulty, ''))) IN ('easy','medium','hard')
                  THEN lower(trim(v_q.observed_difficulty)) ELSE 'medium' END) || chr(0) ||
            coalesce(nullif(lower(trim(coalesce(v_q.language, ''))), ''), 'en') || chr(0) ||
            coalesce(v_q.expected_solve_time_sec::text, '') || chr(0) ||
            coalesce(v_q.pyq_paper_id::text, '') || chr(0) ||
            coalesce(v_q.paper_year::text, '') || chr(0) ||
            coalesce(v_q.exam_id::text, '') || chr(0) ||
            coalesce(v_q.paper_source_url, '') || chr(0) ||
            coalesce(v_q.paper_source_type, '') || chr(0) ||
            coalesce(v_q.paper_source_document_id::text, '') || chr(0) ||
            coalesce((
                SELECT string_agg(
                    coalesce(lower(o.option_label), '') || chr(30) ||
                    coalesce(lower(trim(o.option_text)), ''),
                    chr(31) ORDER BY coalesce(lower(o.option_label), ''), o.id
                )
                FROM public.pyq_options o
                WHERE o.question_id     = p_pyq_question_id
                  AND o.reviewer_status = 'verified'
            ), '') || chr(0) ||
            coalesce((
                SELECT lower(trim(c.option_text))
                FROM public.pyq_options c
                WHERE c.question_id     = p_pyq_question_id
                  AND c.reviewer_status = 'verified'
                  AND c.is_correct      = true
                LIMIT 1
            ), '') || chr(0) ||
            coalesce((
                SELECT string_agg(
                    coalesce(t.topic_id::text, '') || chr(30) ||
                    coalesce(t.tag_role, ''),
                    chr(31) ORDER BY t.topic_id, t.tag_role
                )
                FROM public.pyq_question_topic_tags t
                WHERE t.question_id     = p_pyq_question_id
                  AND t.reviewer_status = 'verified'
            ), '')
        )::bytea),
        'hex'
    ) INTO v_content_hash;

    -- 4. Look up existing projection
    SELECT * INTO v_projection
    FROM public.pyq_mock_question_projections
    WHERE pyq_question_id = p_pyq_question_id
    FOR UPDATE;

    IF FOUND THEN
        v_mock_q_id := v_projection.mock_question_id;

        DECLARE
            v_existing_pyq_q_id uuid;
        BEGIN
            SELECT pyq_question_id
            INTO v_existing_pyq_q_id
            FROM public.mock_question_bank
            WHERE id = v_mock_q_id;

            IF NOT FOUND THEN
                UPDATE public.pyq_mock_question_projections
                SET sync_status = 'archived', updated_at = now()
                WHERE pyq_question_id = p_pyq_question_id;
                v_mock_q_id  := null;
                v_projection := null;
                v_is_new     := true;
            ELSIF v_existing_pyq_q_id IS NOT NULL
                  AND v_existing_pyq_q_id != p_pyq_question_id THEN
                RETURN jsonb_build_object(
                    'outcome',            'conflict',
                    'error',              'mock_question_linked_to_different_pyq',
                    'mock_question_id',   v_mock_q_id,
                    'conflicting_pyq_id', v_existing_pyq_q_id,
                    'pyq_question_id',    p_pyq_question_id
                );
            END IF;
        END;

        IF v_projection IS NOT NULL
           AND v_projection.sync_status = 'active'
           AND v_projection.source_content_hash = v_content_hash THEN
            v_outcome := 'unchanged';
        ELSE
            v_outcome := 'updated';
        END IF;
    ELSE
        v_is_new    := true;
        v_mock_q_id := gen_random_uuid();
        v_outcome   := 'created';
    END IF;

    IF v_outcome = 'unchanged' THEN
        UPDATE public.pyq_mock_question_projections
        SET updated_at       = now(),
            last_sync_result = jsonb_build_object(
                'outcome',      'unchanged',
                'checked_at',   now()::text,
                'content_hash', v_content_hash
            )
        WHERE pyq_question_id = p_pyq_question_id;

        RETURN jsonb_build_object(
            'outcome',          'unchanged',
            'mock_question_id', v_mock_q_id,
            'pyq_question_id',  p_pyq_question_id,
            'content_hash',     v_content_hash
        );
    END IF;

    -- 5. Upsert mock_question_bank
    IF v_is_new THEN
        INSERT INTO public.mock_question_bank (
            id, exam_id, subject_id, topic_id, question_text, question_type,
            difficulty, explanation, language, reviewer_status, published_at,
            source_type, source_kind, question_fingerprint, pyq_question_id,
            pyq_paper_id, pyq_year, expected_time_sec, created_by, created_at, updated_at
        ) VALUES (
            v_mock_q_id, v_q.exam_id, v_topic.subject_id, v_primary_tag.topic_id,
            v_q.question_text, 'mcq',
            CASE WHEN lower(v_q.observed_difficulty) IN ('easy','medium','hard')
                 THEN lower(v_q.observed_difficulty) ELSE 'medium' END,
            v_q.explanation_text, coalesce(v_q.language, 'en'), 'published', now(),
            'pyq', 'pyq', v_content_hash, p_pyq_question_id,
            v_q.pyq_paper_id, v_q.paper_year, v_q.expected_solve_time_sec,
            p_actor_id, now(), now()
        );
    ELSE
        UPDATE public.mock_question_bank SET
            exam_id              = v_q.exam_id,
            subject_id           = v_topic.subject_id,
            topic_id             = v_primary_tag.topic_id,
            question_text        = v_q.question_text,
            question_type        = 'mcq',
            difficulty           = CASE WHEN lower(v_q.observed_difficulty) IN ('easy','medium','hard')
                                       THEN lower(v_q.observed_difficulty) ELSE 'medium' END,
            explanation          = v_q.explanation_text,
            language             = coalesce(v_q.language, 'en'),
            reviewer_status      = 'published',
            published_at         = coalesce(
                                       (SELECT published_at FROM public.mock_question_bank WHERE id = v_mock_q_id),
                                       now()
                                   ),
            source_type          = 'pyq',
            source_kind          = 'pyq',
            question_fingerprint = v_content_hash,
            pyq_question_id      = p_pyq_question_id,
            pyq_paper_id         = v_q.pyq_paper_id,
            pyq_year             = v_q.paper_year,
            expected_time_sec    = v_q.expected_solve_time_sec,
            updated_at           = now()
        WHERE id = v_mock_q_id;
    END IF;

    -- 6. Replace mock_question_options atomically
    DELETE FROM public.mock_question_options WHERE question_id = v_mock_q_id;

    v_correct_opt_id := null;

    FOR v_opt_row IN
        SELECT id, option_text, option_label, is_correct,
               row_number() OVER (ORDER BY option_label, id) - 1 AS opt_idx
        FROM public.pyq_options
        WHERE question_id     = p_pyq_question_id
          AND reviewer_status = 'verified'
        ORDER BY option_label, id
    LOOP
        INSERT INTO public.mock_question_options (
            question_id, option_text, option_index, is_correct
        ) VALUES (
            v_mock_q_id, v_opt_row.option_text, v_opt_row.opt_idx, v_opt_row.is_correct
        )
        RETURNING id INTO v_new_opt_id;

        IF v_opt_row.is_correct THEN
            v_correct_opt_id := v_new_opt_id;
        END IF;
    END LOOP;

    UPDATE public.mock_question_bank
    SET correct_option_id = v_correct_opt_id, updated_at = now()
    WHERE id = v_mock_q_id;

    -- 7. Replace mock_question_topic_tags
    DELETE FROM public.mock_question_topic_tags WHERE question_id = v_mock_q_id;

    INSERT INTO public.mock_question_topic_tags (question_id, topic_id, role)
    SELECT v_mock_q_id, t.topic_id, t.tag_role
    FROM public.pyq_question_topic_tags t
    WHERE t.question_id     = p_pyq_question_id
      AND t.reviewer_status = 'verified';

    -- 8. Upsert mock_question_sources (provenance)
    DELETE FROM public.mock_question_sources WHERE question_id = v_mock_q_id;

    INSERT INTO public.mock_question_sources (
        question_id, source_kind, source_trust,
        source_url, pyq_paper_id, pyq_year, evidence_text, source_document_id
    ) VALUES (
        v_mock_q_id,
        'pyq',
        'verified',
        v_q.paper_source_url,
        v_q.pyq_paper_id,
        v_q.paper_year,
        'projected_from_pyq_question_id:' || p_pyq_question_id::text,
        v_q.paper_source_document_id
    );

    -- 9. Upsert pyq_mock_question_projections
    INSERT INTO public.pyq_mock_question_projections (
        pyq_question_id, mock_question_id, source_content_hash, sync_status,
        last_sync_result, projected_by, projected_at, updated_at
    ) VALUES (
        p_pyq_question_id, v_mock_q_id, v_content_hash, 'active',
        jsonb_build_object('outcome', v_outcome, 'projected_at', now()::text),
        p_actor_id, now(), now()
    )
    ON CONFLICT (pyq_question_id) DO UPDATE
      SET mock_question_id    = EXCLUDED.mock_question_id,
          source_content_hash = EXCLUDED.source_content_hash,
          sync_status         = 'active',
          last_sync_result    = EXCLUDED.last_sync_result,
          projected_by        = EXCLUDED.projected_by,
          projected_at        = CASE
              WHEN pyq_mock_question_projections.projected_at IS NULL
              THEN EXCLUDED.projected_at
              ELSE pyq_mock_question_projections.projected_at
          END,
          updated_at          = now();

    -- 10. Audit log
    INSERT INTO public.admin_audit_logs (
        actor_id, action, entity_type, entity_id, new_value, notes
    ) VALUES (
        p_actor_id,
        'pyq_mock_projection_sync',
        'mock_question_bank',
        v_mock_q_id::text,
        jsonb_build_object(
            'outcome',         v_outcome,
            'pyq_question_id', p_pyq_question_id,
            'pyq_paper_id',    v_q.pyq_paper_id,
            'exam_id',         v_q.exam_id,
            'pyq_year',        v_q.paper_year,
            'content_hash',    v_content_hash,
            'topic_id',        v_primary_tag.topic_id,
            'subject_id',      v_topic.subject_id
        ),
        p_audit_reason
    );

    RETURN jsonb_build_object(
        'outcome',          v_outcome,
        'mock_question_id', v_mock_q_id,
        'pyq_question_id',  p_pyq_question_id,
        'content_hash',     v_content_hash,
        'is_new',           v_is_new
    );
END;
$fn$;

REVOKE EXECUTE ON FUNCTION public.project_pyq_question_to_mock_bank(uuid, uuid, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.project_pyq_question_to_mock_bank(uuid, uuid, text) FROM anon;
REVOKE EXECUTE ON FUNCTION public.project_pyq_question_to_mock_bank(uuid, uuid, text) FROM authenticated;
GRANT  EXECUTE ON FUNCTION public.project_pyq_question_to_mock_bank(uuid, uuid, text) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
