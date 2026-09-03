-- Migration 271: review_pyq_paper() blocks verifying a paper with no questions.
--
-- WHY
-- The 2026-08-25 audit added a pyq_questions count to the pending -> verified
-- blocking-fields list in `admin_exam_intel_cms.py` (:1596-1606, appended as
-- 'questions'). The DB function `public.review_pyq_paper` re-validates the same
-- provenance rules on the LOCKED row in its step 6 — source_type, the provenance
-- anchor, the attached document — but never gained the count check.
--
-- Both paths are reachable. The endpoint is not the only way in: a caller with
-- service_role can invoke /rpc/review_pyq_paper directly and skip the Python
-- gate entirely. That is not hypothetical — paper b06305ad was verified with
-- zero questions on 2026-08-25, and c82f3e64 the same way.
--
-- A verified-but-empty paper is not inert. `verified_pyq_papers()` lists it,
-- `difficulty_heatmap()` counts it as a verified paper with no questions, and
-- the projection bridge treats its trust_status as the gate it passes. The
-- function is where the rule belongs: it holds the row lock, and it is the
-- floor under every caller rather than one of them.
--
-- WHAT CHANGED
-- Exactly one thing: step 6 gains check (d), appending 'no_questions' to
-- v_blocking when no pyq_questions row references this paper. Checks (a), (b)
-- and (c), the transition table, the reason-length gate, the concurrent-
-- modification guards, the audit INSERT and the return shape are byte-for-byte
-- migration 187's. The signature is unchanged, so existing grants survive the
-- replace; they are re-asserted below anyway, matching 187.
--
-- NAMING NOTE: this appends 'no_questions' while the Python path appends
-- 'questions' for the same condition. Two labels for one rule is a wart; it is
-- left alone here rather than changed, because renaming the Python one is an
-- API-visible change to `blocking_fields` and belongs in its own PR. See the
-- PR body.
--
-- NOT ADDRESSED HERE: this gate is forward-looking only. It stops the NEXT
-- empty verify; it does not touch b06305ad, c82f3e64, or any other paper
-- already sitting at trust_status='verified' with no questions. Finding and
-- correcting those is an operator task, and the transition table makes it
-- awkward — see the PR body.

BEGIN;

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

        -- (d) the paper must actually carry questions.
        --     Added by migration 271. The Python endpoint has counted
        --     pyq_questions since the 2026-08-25 audit, but this function did
        --     not, and both paths reach a verify: a direct /rpc/ call bypassed
        --     the endpoint's check entirely. Papers b06305ad and c82f3e64 were
        --     verified empty that way. Not locked — a concurrent insert can
        --     only ADD questions, which cannot turn a passing check into a
        --     failing one, and blocking inserts for the length of a review
        --     would cost more than the race is worth.
        IF NOT EXISTS (
            SELECT 1
            FROM public.pyq_questions
            WHERE pyq_paper_id = p_paper_id::uuid
        ) THEN
            v_blocking := v_blocking || ARRAY['no_questions'];
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

COMMIT;
