-- Migration 185: Atomic PYQ-paper review transaction
--
-- The review endpoint previously performed two independent PostgREST writes:
-- (1) INSERT admin_audit_logs; (2) UPDATE pyq_papers.  This means a failed
-- UPDATE (e.g. concurrent modification → WHERE clause matches nothing) left
-- a false audit row recording a transition that never happened.
--
-- This migration adds a SECURITY DEFINER function that wraps both writes in a
-- single transaction, so they succeed or rollback together.
--
-- The Python endpoint calls this via supabase.rpc("review_pyq_paper", {...}).
-- A concurrent modification between the endpoint's pre-validation SELECT and
-- the RPC is detected by SELECT … FOR UPDATE + expected-status guard; the
-- entire transaction is aborted and ERRCODE P0409 is raised.

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
    v_paper     pyq_papers%ROWTYPE;
    v_audit_id  uuid;
    v_updated   pyq_papers%ROWTYPE;
BEGIN
    -- Lock the row for the duration of this transaction so no concurrent writer
    -- can change trust_status between the guard check and the UPDATE below.
    SELECT * INTO v_paper
    FROM public.pyq_papers
    WHERE id = p_paper_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: paper % does not exist', p_paper_id
            USING ERRCODE = 'P0404';
    END IF;

    -- Concurrent-modification guard: verify the status the caller saw is still
    -- the current status.  FOR UPDATE prevents a second writer from sneaking in
    -- after this check and before the UPDATE below.
    IF v_paper.trust_status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION 'concurrent_modification: expected trust_status=% but found %. Re-fetch and retry.',
            p_expected_status, v_paper.trust_status
            USING ERRCODE = 'P0409';
    END IF;

    -- Insert the audit row FIRST within the same transaction.
    -- If this fails, neither the audit row nor the status change will persist.
    INSERT INTO public.admin_audit_logs (
        actor_id,
        actor_email,
        action,
        entity_type,
        entity_id,
        new_value,
        notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'exam_intel.cms.pyq_paper.review',
        'pyq_paper',
        p_paper_id,
        jsonb_build_object(
            'from_status',  p_expected_status,
            'to_status',    p_target_status,
            'reason',       p_reason,
            'reviewed_by',  p_actor_email,
            'reviewed_at',  now()::text
        ),
        'admin_exam_intel_cms'
    )
    RETURNING id INTO v_audit_id;

    -- Update paper status.  The WHERE clause on trust_status is belt-and-suspenders
    -- given the FOR UPDATE lock above; if somehow zero rows match the transaction
    -- rolls back.
    UPDATE public.pyq_papers
    SET    trust_status = p_target_status,
           updated_at   = now()
    WHERE  id           = p_paper_id::uuid
    AND    trust_status = p_expected_status
    RETURNING * INTO v_updated;

    IF NOT FOUND THEN
        -- Should be unreachable given the FOR UPDATE lock, but guard defensively.
        RAISE EXCEPTION 'concurrent_modification: zero rows updated after lock — status changed under FOR UPDATE'
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

-- Notify PostgREST to reload schema cache.
SELECT pg_notify('pgrst', 'reload schema');
