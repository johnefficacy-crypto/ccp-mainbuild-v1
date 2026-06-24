-- Migration 189: Lock document_assets in provenance mutation RPCs
--
-- Round-4 fix for PR #756: migration 188's cms_set_pyq_paper_provenance() and
-- cms_link_document_to_pyq_paper() performed the six document invariant checks
-- only in Python before calling the RPC.  A concurrent archive/status/storage
-- change on document_assets between the Python precheck and the SQL UPDATE left
-- a window where source_document_id could end up pointing at an invalid document.
--
-- Fix: both RPCs now SELECT ... FOR UPDATE the paper row (and conditionally /
-- unconditionally the document_assets row) and re-run all six invariants inside
-- the same transaction, exactly as review_pyq_paper() does (migration 187 step 6c).

-- ─── Part A: cms_set_pyq_paper_provenance — paper lock + conditional doc lock ─

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
    v_paper    record;
    v_doc      record;
    v_doc_id   uuid;
    v_blocking text[];
    v_audit_id uuid;
BEGIN
    -- Lock the paper row for the duration of this transaction.
    SELECT id, exam_id INTO v_paper
    FROM public.pyq_papers
    WHERE id = p_paper_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: paper % does not exist', p_paper_id
            USING ERRCODE = 'P0404';
    END IF;

    -- When source_document_id is being set to a non-null value, lock and
    -- validate the document_assets row inside this transaction.  This closes
    -- the race window between the Python precheck and the SQL mutation that
    -- migration 188 left open.
    IF (p_patch ? 'source_document_id') AND (p_patch->>'source_document_id') IS NOT NULL THEN
        v_doc_id   := (p_patch->>'source_document_id')::uuid;
        v_blocking := ARRAY[]::text[];

        SELECT * INTO v_doc
        FROM public.document_assets
        WHERE id = v_doc_id
        FOR UPDATE;

        IF NOT FOUND THEN
            v_blocking := array_append(v_blocking, 'source_document_id_not_found');
        ELSE
            IF v_doc.scope != 'admin_exam_intelligence' THEN
                v_blocking := array_append(v_blocking, 'source_document_id_wrong_scope');
            END IF;
            IF v_doc.document_kind != 'pyq_paper' THEN
                v_blocking := array_append(v_blocking, 'source_document_id_wrong_kind');
            END IF;
            IF v_doc.status IN ('failed', 'archived') THEN
                v_blocking := array_append(v_blocking, 'source_document_id_bad_status');
            END IF;
            IF coalesce(trim(v_doc.storage_bucket), '') = ''
               OR coalesce(trim(v_doc.storage_path), '') = '' THEN
                v_blocking := array_append(v_blocking, 'source_document_id_no_storage');
            END IF;
            IF (v_doc.metadata->>'exam_id') IS NOT NULL
               AND (v_doc.metadata->>'exam_id') != ''
               AND (v_doc.metadata->>'exam_id') IS DISTINCT FROM v_paper.exam_id::text THEN
                v_blocking := array_append(v_blocking, 'source_document_id_exam_mismatch');
            END IF;
        END IF;

        IF array_length(v_blocking, 1) > 0 THEN
            RAISE EXCEPTION 'provenance_incomplete: blocking_fields=%',
                array_to_string(v_blocking, ',')
                USING ERRCODE = 'P0422';
        END IF;
    END IF;

    -- Update only the provenance fields present in the patch.
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
        RAISE EXCEPTION 'not_found: paper % does not exist after lock', p_paper_id
            USING ERRCODE = 'P0404';
    END IF;

    -- Audit INSERT is in the same transaction.
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

-- ─── Part B: cms_link_document_to_pyq_paper — paper lock + unconditional doc lock

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
    v_paper    record;
    v_doc      record;
    v_blocking text[];
    v_audit_id uuid;
BEGIN
    -- Lock the paper row for the duration of this transaction.
    SELECT id, exam_id INTO v_paper
    FROM public.pyq_papers
    WHERE id = p_paper_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: paper % does not exist', p_paper_id
            USING ERRCODE = 'P0404';
    END IF;

    -- Always lock and validate the document_assets row inside this transaction.
    -- This closes the race window that migration 188 left between Python precheck
    -- and the SQL mutation.
    v_blocking := ARRAY[]::text[];

    SELECT * INTO v_doc
    FROM public.document_assets
    WHERE id = p_document_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        v_blocking := array_append(v_blocking, 'source_document_id_not_found');
    ELSE
        IF v_doc.scope != 'admin_exam_intelligence' THEN
            v_blocking := array_append(v_blocking, 'source_document_id_wrong_scope');
        END IF;
        IF v_doc.document_kind != 'pyq_paper' THEN
            v_blocking := array_append(v_blocking, 'source_document_id_wrong_kind');
        END IF;
        IF v_doc.status IN ('failed', 'archived') THEN
            v_blocking := array_append(v_blocking, 'source_document_id_bad_status');
        END IF;
        IF coalesce(trim(v_doc.storage_bucket), '') = ''
           OR coalesce(trim(v_doc.storage_path), '') = '' THEN
            v_blocking := array_append(v_blocking, 'source_document_id_no_storage');
        END IF;
        IF (v_doc.metadata->>'exam_id') IS NOT NULL
           AND (v_doc.metadata->>'exam_id') != ''
           AND (v_doc.metadata->>'exam_id') IS DISTINCT FROM v_paper.exam_id::text THEN
            v_blocking := array_append(v_blocking, 'source_document_id_exam_mismatch');
        END IF;
    END IF;

    IF array_length(v_blocking, 1) > 0 THEN
        RAISE EXCEPTION 'document_not_linkable: blocking_fields=%',
            array_to_string(v_blocking, ',')
            USING ERRCODE = 'P0422';
    END IF;

    -- Set source_document_id; demote verified papers to pending.
    UPDATE public.pyq_papers
    SET
        source_document_id = p_document_id::uuid,
        trust_status       = CASE WHEN p_was_verified THEN 'pending' ELSE trust_status END,
        updated_at         = now()
    WHERE id = p_paper_id::uuid;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: paper % does not exist after lock', p_paper_id
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
