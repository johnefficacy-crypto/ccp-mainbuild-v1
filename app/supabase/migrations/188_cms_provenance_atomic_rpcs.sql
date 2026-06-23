-- Migration 188: Atomic provenance-mutation RPCs
--
-- set_pyq_paper_provenance() and link_document_to_pyq_paper() previously
-- performed an UPDATE on pyq_papers followed by a best-effort _audit() call
-- in Python.  A failure on the audit INSERT left the paper mutated (including
-- verified→pending demotion) with no durable audit trail while still returning
-- ok:true.  These SECURITY DEFINER functions perform the pyq_papers UPDATE and
-- the admin_audit_logs INSERT in a single transaction so both succeed or
-- neither commits.

-- ─── Part A: cms_set_pyq_paper_provenance ─────────────────────────────────────

CREATE OR REPLACE FUNCTION public.cms_set_pyq_paper_provenance(
    p_paper_id            text,
    p_actor_id            text,
    p_actor_email         text,
    p_patch               jsonb,   -- subset of {source_url, source_type, source_document_id}
    p_reason              text,
    p_previous_provenance jsonb,
    p_was_verified        boolean
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_audit_id  uuid;
BEGIN
    -- Update only the provenance fields present in the patch.
    -- p_was_verified controls whether trust_status is demoted to 'pending'.
    UPDATE public.pyq_papers
    SET
        source_url         = CASE WHEN p_patch ? 'source_url'
                                   THEN p_patch->>'source_url'
                                   ELSE source_url         END,
        source_type        = CASE WHEN p_patch ? 'source_type'
                                   THEN p_patch->>'source_type'
                                   ELSE source_type        END,
        source_document_id = CASE WHEN p_patch ? 'source_document_id'
                                   THEN (p_patch->>'source_document_id')::uuid
                                   ELSE source_document_id END,
        trust_status       = CASE WHEN p_was_verified THEN 'pending' ELSE trust_status END,
        updated_at         = now()
    WHERE id = p_paper_id::uuid;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: paper % does not exist', p_paper_id
            USING ERRCODE = 'P0404';
    END IF;

    -- Audit INSERT is in the same transaction. If it fails for any reason
    -- (constraint violation, etc.) the UPDATE above is rolled back atomically.
    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, action, entity_type, entity_id, new_value, notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'exam_intel.cms.pyq_paper.set_provenance',
        'pyq_paper',
        p_paper_id,
        jsonb_build_object(
            'reason',                p_reason,
            'patch',                 p_patch,
            'previous_provenance',   p_previous_provenance,
            'demoted_from_verified', p_was_verified
        ),
        'admin_exam_intel_cms'
    )
    RETURNING id INTO v_audit_id;

    RETURN jsonb_build_object(
        'audit_id',              v_audit_id,
        'demoted_from_verified', p_was_verified
    );
END;
$$;

REVOKE ALL ON FUNCTION public.cms_set_pyq_paper_provenance FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION public.cms_set_pyq_paper_provenance TO service_role;

-- ─── Part B: cms_link_document_to_pyq_paper ───────────────────────────────────

CREATE OR REPLACE FUNCTION public.cms_link_document_to_pyq_paper(
    p_document_id  text,
    p_paper_id     text,
    p_actor_id     text,
    p_actor_email  text,
    p_reason       text,
    p_was_verified boolean
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_audit_id  uuid;
BEGIN
    -- Set source_document_id; demote verified papers to pending so they must
    -- be re-reviewed before the projection RPC can run.
    UPDATE public.pyq_papers
    SET
        source_document_id = p_document_id::uuid,
        trust_status       = CASE WHEN p_was_verified THEN 'pending' ELSE trust_status END,
        updated_at         = now()
    WHERE id = p_paper_id::uuid;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: paper % does not exist', p_paper_id
            USING ERRCODE = 'P0404';
    END IF;

    -- Audit INSERT in the same transaction.
    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, action, entity_type, entity_id, new_value, notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'exam_intel.cms.document.link_pyq_paper',
        'pyq_paper',
        p_paper_id,
        jsonb_build_object(
            'reason',                p_reason,
            'document_asset_id',     p_document_id,
            'demoted_from_verified', p_was_verified
        ),
        'admin_exam_intel_cms'
    )
    RETURNING id INTO v_audit_id;

    RETURN jsonb_build_object(
        'audit_id',              v_audit_id,
        'demoted_from_verified', p_was_verified
    );
END;
$$;

REVOKE ALL ON FUNCTION public.cms_link_document_to_pyq_paper FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION public.cms_link_document_to_pyq_paper TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
