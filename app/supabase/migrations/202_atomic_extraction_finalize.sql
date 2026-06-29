-- Migration 202: Atomic document extraction finalization
--
-- Adds finalize_document_extraction(), a single SECURITY DEFINER transaction
-- that atomically:
--   1. Locks the document_assets row with SELECT … FOR UPDATE.
--   2. Aborts (returns ok=false, reason=archived) if the document has been
--      archived — page rows are NOT written and the job is NOT updated.
--   3. Replaces document_pages (inline logic from replace_document_pages so
--      both writes share one transaction snapshot).
--   4. Flips the document_processing_jobs row to the terminal status supplied
--      by the caller ('succeeded' | 'failed') with a finished_at timestamp.
--   5. Updates document_assets.status ('processed' | 'failed').
--   6. Returns {"ok": true} on success.
--
-- This closes the TOCTOU race described in Issue #780 where a document could
-- be archived between the extraction worker reading the document and writing
-- the resulting pages + job state.
--
-- Applied version: 202 = MAX(main)+1 on the filesystem (current max is 201).
--
-- Mirrors the SECURITY DEFINER structure, SET search_path = public, FOR UPDATE
-- row locks, and the REVOKE-from-anon/authenticated + GRANT-to-service_role
-- grant pattern of migrations 188–192.

CREATE OR REPLACE FUNCTION public.finalize_document_extraction(
    p_job_id         uuid,
    p_document_id    uuid,
    p_pages          jsonb,         -- array of {page_number, text_content, char_count, extraction_status, metadata}
    p_status         text,          -- 'succeeded' | 'failed'
    p_error_code     text    DEFAULT NULL,
    p_error_message  text    DEFAULT NULL,
    p_metrics        jsonb   DEFAULT NULL,
    p_parser_engine  text    DEFAULT NULL,
    p_parser_version text    DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_doc    document_assets%ROWTYPE;
    v_now    timestamptz := now();
BEGIN
    -- 1. Lock the document row.  FOR UPDATE serialises concurrent archive /
    --    extraction-finalize calls on the same document.
    SELECT * INTO v_doc
      FROM public.document_assets
     WHERE id = p_document_id
       FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('ok', false, 'reason', 'document_missing');
    END IF;

    -- 2. Abort if the document has been archived — preserve the archived state.
    IF v_doc.status = 'archived' THEN
        RETURN jsonb_build_object('ok', false, 'reason', 'archived');
    END IF;

    -- 3. Inline replace_document_pages logic: delete existing rows then insert
    --    the new page set.  Shares this transaction so both writes are atomic.
    DELETE FROM public.document_pages WHERE document_id = p_document_id;

    IF p_pages IS NOT NULL AND jsonb_array_length(p_pages) > 0 THEN
        INSERT INTO public.document_pages
            (document_id, page_number, text_content, char_count,
             extraction_status, parser_engine, parser_version, metadata)
        SELECT
            p_document_id,
            (p ->> 'page_number')::int,
            coalesce(p ->> 'text_content', ''),
            coalesce((p ->> 'char_count')::int, 0),
            coalesce(p ->> 'extraction_status', 'extracted'),
            p_parser_engine,
            p_parser_version,
            coalesce((p -> 'metadata')::jsonb, '{}'::jsonb)
        FROM jsonb_array_elements(p_pages) AS p;
    END IF;

    -- 4. Update the job terminal state.
    UPDATE public.document_processing_jobs
       SET status        = p_status,
           finished_at   = v_now,
           error_code    = p_error_code,
           error_message = p_error_message,
           metrics       = coalesce(p_metrics, '{}'::jsonb)
     WHERE id = p_job_id;

    -- 5. Update the document status (never overwrite 'archived').
    UPDATE public.document_assets
       SET status = CASE WHEN p_status = 'succeeded' THEN 'processed' ELSE 'failed' END
     WHERE id = p_document_id
       AND status != 'archived';

    RETURN jsonb_build_object('ok', true);
END;
$$;

REVOKE ALL ON FUNCTION public.finalize_document_extraction(
    uuid, uuid, jsonb, text, text, text, jsonb, text, text
) FROM public, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.finalize_document_extraction(
    uuid, uuid, jsonb, text, text, text, jsonb, text, text
) TO service_role;

notify pgrst, 'reload schema';
