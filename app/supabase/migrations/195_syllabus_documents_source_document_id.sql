-- Migration 195: add source_document_id to syllabus_documents
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
