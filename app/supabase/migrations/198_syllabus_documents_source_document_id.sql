-- Migration 198: add source_document_id to syllabus_documents
--
-- Stores the document_assets.id that backed a syllabus_documents row so that
-- propose_syllabus_mentions() can look up extracted document_pages via the
-- correct asset ID rather than the syllabus_documents.id (which is a
-- different UUID).

alter table public.syllabus_documents
  add column if not exists source_document_id uuid
    references public.document_assets(id) on delete set null;

comment on column public.syllabus_documents.source_document_id is
  'FK to the document_assets row whose extracted pages should be used by the syllabus proposer.';

create index if not exists idx_syllabus_documents_source_document_id
  on public.syllabus_documents(source_document_id)
  where source_document_id is not null;

-- Backfill existing linked syllabus_documents rows by matching storage_path
-- to document_assets.  Only writes source_document_id when exactly one
-- admin_exam_intelligence asset shares the same storage_path (no ambiguity).
-- Rows with duplicate-path matches are left as NULL so an operator can resolve
-- them manually.
update public.syllabus_documents sd
set    source_document_id = da.id
from   public.document_assets da
where  sd.source_document_id is null
  and  sd.storage_path is not null
  and  da.storage_path = sd.storage_path
  and  da.scope        = 'admin_exam_intelligence'
  and  (
    select count(*)
    from   public.document_assets da2
    where  da2.storage_path = sd.storage_path
      and  da2.scope        = 'admin_exam_intelligence'
  ) = 1;

-- Emit a notice listing any syllabus_documents that remain un-backfilled so
-- operators can resolve ambiguous or missing asset links manually.
do $$
declare
  unlinked_count integer;
begin
  select count(*) into unlinked_count
  from   public.syllabus_documents
  where  source_document_id is null
    and  storage_path is not null;

  if unlinked_count > 0 then
    raise notice
      'migration 195: % syllabus_documents row(s) still have source_document_id=NULL '
      'after backfill (ambiguous or missing document_assets match). '
      'Run: SELECT id, storage_path FROM syllabus_documents WHERE source_document_id IS NULL AND storage_path IS NOT NULL;',
      unlinked_count;
  end if;
end $$;
