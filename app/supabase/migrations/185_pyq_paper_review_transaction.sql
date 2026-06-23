-- Migration 185: Atomic PYQ-paper review transaction (authoritative validation)
--
-- The review endpoint previously performed two independent PostgREST writes:
-- (1) INSERT admin_audit_logs; (2) UPDATE pyq_papers.  A failed UPDATE left
-- a false audit row.  This migration adds a SECURITY DEFINER function that wraps
-- both writes in one transaction AND performs all business-rule validation on
-- the *locked* row so:
--
--   • A concurrent CMS edit that changes source_url/source_type while
--     trust_status stays 'pending' is caught by the provenance re-check after
--     SELECT … FOR UPDATE (Python's pre-validation SELECT saw stale values).
--   • A direct service-role call with an illegal target status, bad transition,
--     or short reason is rejected at the DB level — not just at the Python layer.
--
-- Error ERRCODE tokens the Python endpoint maps to HTTP status codes:
--   P0404 → 404  (not_found)
--   P0409 → 409  (concurrent_modification)
--   P0422 → 422  (transition_not_allowed | provenance_incomplete | invalid_reason |
--                  invalid_target_status)

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
    v_audit_id       uuid;
    v_updated        pyq_papers%ROWTYPE;
    v_reason_trimmed text;
    v_blocking       text[];
BEGIN
    -- 1. Validate reason length before touching the DB.
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

    -- 3. Lock the row for the duration of this transaction so no concurrent
    --    writer can mutate trust_status or provenance fields between the checks
    --    below and the UPDATE at the end.
    SELECT * INTO v_paper
    FROM public.pyq_papers
    WHERE id = p_paper_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: paper % does not exist', p_paper_id
            USING ERRCODE = 'P0404';
    END IF;

    -- 4. Concurrent-modification guard: the caller's pre-validation SELECT may
    --    have seen a different status than the now-locked row.
    IF v_paper.trust_status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION 'concurrent_modification: expected trust_status=% but found %. Re-fetch and retry.',
            p_expected_status, v_paper.trust_status
            USING ERRCODE = 'P0409';
    END IF;

    -- 5. Validate transition using the locked row's actual current status.
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
    --    A concurrent CMS edit may have cleared source_url/source_type after
    --    Python's pre-validation SELECT passed but before this lock was acquired.
    IF v_paper.trust_status = 'pending' AND p_target_status = 'verified' THEN
        v_blocking := ARRAY[]::text[];
        IF v_paper.source_url IS NULL OR trim(v_paper.source_url) = '' THEN
            v_blocking := v_blocking || ARRAY['source_url'];
        END IF;
        IF v_paper.source_type IS NULL OR v_paper.source_type = 'unknown' THEN
            v_blocking := v_blocking || ARRAY['source_type'];
        END IF;
        IF array_length(v_blocking, 1) > 0 THEN
            RAISE EXCEPTION 'provenance_incomplete: blocking_fields=%',
                array_to_string(v_blocking, ',')
                USING ERRCODE = 'P0422';
        END IF;
    END IF;

    -- 7. Insert audit row within the same transaction.
    --    If this fails, neither the audit row nor the status change will persist.
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
            'reason',      p_reason,
            'reviewed_by', p_actor_email,
            'reviewed_at', now()::text
        ),
        'admin_exam_intel_cms'
    )
    RETURNING id INTO v_audit_id;

    -- 8. Update paper status (belt-and-suspenders WHERE given the FOR UPDATE lock).
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

-- Only the service_role backend can call this; deny anon and authenticated.
REVOKE EXECUTE ON FUNCTION review_pyq_paper(text, text, text, text, text, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION review_pyq_paper(text, text, text, text, text, text) FROM anon;
REVOKE EXECUTE ON FUNCTION review_pyq_paper(text, text, text, text, text, text) FROM authenticated;
GRANT  EXECUTE ON FUNCTION review_pyq_paper(text, text, text, text, text, text) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
