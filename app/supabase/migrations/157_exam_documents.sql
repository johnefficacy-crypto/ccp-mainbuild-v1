-- 157_exam_documents.sql
-- Aspirant-facing document store: notifications, syllabi, corrigenda, PYQ PDFs,
-- answer keys, cutoff PDFs, and admit cards, keyed by exam and optional phase.

create table if not exists public.exam_documents (
  id               uuid        primary key default gen_random_uuid(),
  exam_id          uuid        not null references public.exams(id) on delete cascade,
  exam_phase_id    uuid        references public.exam_phases(id) on delete set null,
  doc_type         text        not null
    check (doc_type in (
      'notification', 'syllabus', 'corrigendum',
      'pyq_pdf', 'answer_key', 'cutoff_pdf', 'admit_card'
    )),
  title            text        not null,
  url              text        not null,
  cycle_year       int,
  source_kind      text        not null default 'manual'
    check (source_kind in ('manual', 'bulk_import', 'auto_extracted')),
  reviewer_status  text        not null default 'unverified'
    check (reviewer_status in ('unverified', 'reviewed', 'locked', 'rejected')),
  valid_from       date,
  valid_until      date,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

comment on table  public.exam_documents                is 'Aspirant-facing official documents (notifications, syllabi, PYQs, etc.) attached to an exam or exam phase.';
comment on column public.exam_documents.doc_type       is 'Document category: notification | syllabus | corrigendum | pyq_pdf | answer_key | cutoff_pdf | admit_card.';
comment on column public.exam_documents.cycle_year     is 'Exam cycle year this document belongs to (e.g. 2024). NULL when not cycle-specific.';
comment on column public.exam_documents.source_kind    is 'How this row was created: manual CMS entry, bulk import, or auto-extracted.';
comment on column public.exam_documents.reviewer_status is 'Trust gate: unverified | reviewed | locked | rejected. Aspirants see reviewed/locked rows only.';
comment on column public.exam_documents.valid_from     is 'Inclusive date from which the document is considered current. NULL = no lower bound.';
comment on column public.exam_documents.valid_until    is 'Inclusive date until which the document is considered current. NULL = no expiry.';

create index if not exists idx_exam_documents_exam_type_year
  on public.exam_documents(exam_id, doc_type, cycle_year);

create index if not exists idx_exam_documents_phase
  on public.exam_documents(exam_phase_id)
  where exam_phase_id is not null;

alter table public.exam_documents enable row level security;
alter table public.exam_documents force row level security;

do $$
begin
  -- Aspirants: read rows that a reviewer has signed off on.
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'exam_documents'
      and policyname = 'exam_documents_read_reviewed'
  ) then
    create policy exam_documents_read_reviewed on public.exam_documents
      for select to authenticated
      using (
        reviewer_status in ('reviewed', 'locked')
        or public.is_admin(auth.uid())
      );
  end if;

  -- Admins: full write access via service_role or admin JWT.
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'exam_documents'
      and policyname = 'exam_documents_admin_all'
  ) then
    create policy exam_documents_admin_all on public.exam_documents
      for all to authenticated
      using     (public.is_admin(auth.uid()))
      with check (public.is_admin(auth.uid()));
  end if;

  -- Service role (backend scrapers/importers) bypasses RLS.
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'exam_documents'
      and policyname = 'exam_documents_service_role_all'
  ) then
    create policy exam_documents_service_role_all on public.exam_documents
      for all to service_role using (true) with check (true);
  end if;
end $$;

notify pgrst, 'reload schema';
