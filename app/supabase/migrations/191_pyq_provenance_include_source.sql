-- Migration 191: Extend cms_set_pyq_paper_provenance to include pyq_source_id
--
-- The atomic provenance mutation (migration 189) only covered three fields:
-- source_url, source_type, source_document_id.  pyq_source_id was in _PAPER_FIELDS
-- (patchable via PATCH) but was never part of _PROVENANCE_FIELDS, creating two gaps:
--
-- 1. A pyq_source_id-only PATCH on a verified paper was not blocked by the
--    _PROVENANCE_FIELDS guard in update_pyq_paper(), bypassing the re-review gate.
-- 2. set-provenance did not pass pyq_source_id through the atomic RPC, so it could
--    not be set atomically alongside source_type / source_url / source_document_id.
--
-- Fix: extend cms_set_pyq_paper_provenance to accept pyq_source_id in p_patch,
-- validate it against pyq_sources (existence + exam_id match), apply it in the
-- UPDATE, and include it in the previous_provenance audit snapshot.
-- The Python caller adds "pyq_source_id" to _PROVENANCE_FIELDS, which automatically
-- routes pyq_source_id-only PATCHes on verified papers through set-provenance too.

CREATE OR REPLACE FUNCTION public.cms_set_pyq_paper_provenance(
    p_paper_id            text,
    p_actor_id            text,
    p_actor_email         text,
    p_patch               jsonb,   -- subset of {source_url, source_type, source_document_id, pyq_source_id}
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
    v_paper       record;
    v_doc         record;
    v_source      record;
    v_doc_id      uuid;
    v_source_id   uuid;
    v_blocking    text[];
    v_audit_id    uuid;
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
    -- validate the document_assets row inside this transaction.
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

    -- When pyq_source_id is being set to a non-null value, validate it
    -- against pyq_sources: must exist and belong to the same exam.
    IF (p_patch ? 'pyq_source_id') AND (p_patch->>'pyq_source_id') IS NOT NULL THEN
        v_source_id := (p_patch->>'pyq_source_id')::uuid;
        v_blocking  := ARRAY[]::text[];

        SELECT id, exam_id INTO v_source
        FROM public.pyq_sources
        WHERE id = v_source_id;

        IF NOT FOUND THEN
            v_blocking := array_append(v_blocking, 'pyq_source_id_not_found');
        ELSE
            IF v_source.exam_id IS DISTINCT FROM v_paper.exam_id THEN
                v_blocking := array_append(v_blocking, 'pyq_source_id_exam_mismatch');
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
        pyq_source_id      = CASE WHEN p_patch ? 'pyq_source_id'
                                   THEN (p_patch->>'pyq_source_id')::uuid
                                   ELSE pyq_source_id      END,
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

-- Apply the same full REVOKE/GRANT pattern as migration 190 to ensure
-- anon and authenticated roles never gain direct RPC access.
REVOKE ALL      ON FUNCTION public.cms_set_pyq_paper_provenance(text,text,text,jsonb,text,jsonb,boolean) FROM PUBLIC;
REVOKE EXECUTE  ON FUNCTION public.cms_set_pyq_paper_provenance(text,text,text,jsonb,text,jsonb,boolean) FROM anon;
REVOKE EXECUTE  ON FUNCTION public.cms_set_pyq_paper_provenance(text,text,text,jsonb,text,jsonb,boolean) FROM authenticated;
GRANT  EXECUTE  ON FUNCTION public.cms_set_pyq_paper_provenance(text,text,text,jsonb,text,jsonb,boolean) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
