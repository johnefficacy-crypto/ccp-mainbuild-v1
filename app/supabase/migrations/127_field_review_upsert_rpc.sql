-- 127_field_review_upsert_rpc.sql
-- Atomic, idempotent field-review upsert.
--
-- admin_scrape._upsert_field_review() used to write extracted_field_evidence
-- as a separate INSERT-or-UPDATE after several reads. A mid-sequence Supabase
-- disconnect left partial state, and a retry of a bare INSERT could 23505 (or
-- duplicate) instead of recovering cleanly. This RPC collapses the evidence
-- write to one statement keyed on the natural review scope, so the runner can
-- safely retry it through _execute_with_retry.
--
-- SCOPE / CONFLICT TARGET: the existing unique index is
--   uq_evidence_entity_scoped(scrape_queue_id, entity_type, coalesce(entity_key,''), field_name)
-- (migration 005). It uses coalesce(entity_key,'') so the common
-- recruitment-scoped rows (entity_key IS NULL) collapse to a single row.
-- The ON CONFLICT below targets that exact expression — NOT a raw-column
-- tuple, which would treat NULL entity_keys as distinct and never dedup them.
--
-- COLUMNS: this matches the real table (reviewed_by / extracted_value /
-- extraction_method / corrected_value), not a reviewer_id/evidence_text shape.

-- up
begin;

-- Defensive: ensure the scope index exists (no-op if migration 005 applied).
create unique index if not exists uq_evidence_entity_scoped
  on public.extracted_field_evidence(scrape_queue_id, entity_type, coalesce(entity_key, ''), field_name);

create or replace function public.upsert_field_review(
    p_queue_id          uuid,
    p_field_name        text,
    p_entity_type       text,
    p_entity_key        text,
    p_status            text,       -- 'verified' | 'rejected' | 'corrected'
    p_reviewed_by       uuid,
    p_notes             text,
    p_corrected_value   jsonb,
    p_extracted_value   jsonb,
    p_extraction_method text,
    p_document_id       uuid
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_row public.extracted_field_evidence%rowtype;
begin
    insert into public.extracted_field_evidence (
        scrape_queue_id, field_name, entity_type, entity_key,
        reviewer_status, reviewed_by, reviewer_notes,
        corrected_value, extracted_value, extraction_method, document_id,
        reviewed_at
    ) values (
        p_queue_id, p_field_name, coalesce(p_entity_type, 'other'), p_entity_key,
        p_status, p_reviewed_by, p_notes,
        p_corrected_value, p_extracted_value, coalesce(p_extraction_method, 'manual'), p_document_id,
        now()
    )
    on conflict (scrape_queue_id, entity_type, coalesce(entity_key, ''), field_name)
    do update set
        reviewer_status   = excluded.reviewer_status,
        reviewed_by       = excluded.reviewed_by,
        reviewer_notes    = excluded.reviewer_notes,
        -- COALESCE: a null on a later call (e.g. a reject after a correct)
        -- preserves the prior correction rather than wiping it.
        corrected_value   = coalesce(excluded.corrected_value, public.extracted_field_evidence.corrected_value),
        extracted_value   = coalesce(excluded.extracted_value, public.extracted_field_evidence.extracted_value),
        extraction_method = excluded.extraction_method,
        document_id       = coalesce(excluded.document_id, public.extracted_field_evidence.document_id),
        reviewed_at       = now()
    returning * into v_row;

    return to_jsonb(v_row);
end;
$$;

grant execute on function public.upsert_field_review(
    uuid, text, text, text, text, uuid, text, jsonb, jsonb, text, uuid
) to service_role;

commit;

notify pgrst, 'reload schema';

-- rollback (manual only):
-- drop function if exists public.upsert_field_review(uuid,text,text,text,text,uuid,text,jsonb,jsonb,text,uuid);
-- (leave uq_evidence_entity_scoped — it predates this migration.)
