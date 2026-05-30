-- =============================================================================
-- 156_exam_subject_resources.sql
-- Verified subjectwise booklist mapping.
--
-- Table: exam_subject_resources
--   Links an exam + phase + subject (+ optional topic) to a curated resource
--   (book, free_pdf, course, notes, website).  marketplace_resource_id is an
--   optional soft-link to marketplace_assets — only populate when a hosted
--   asset already exists; do not create marketplace rows to satisfy this FK.
--
-- Idempotent: safe on fresh DB and re-runnable on existing.
-- =============================================================================

create table if not exists public.exam_subject_resources (
  id                      uuid        primary key default gen_random_uuid(),

  exam_id                 uuid        not null
                            references public.exams(id) on delete cascade,
  exam_phase_id           uuid
                            references public.exam_phases(id) on delete set null,
  subject_id              uuid        not null
                            references public.subjects(id) on delete cascade,
  topic_id                uuid
                            references public.topics(id) on delete set null,

  resource_type           text        not null
                            check (resource_type in ('book','free_pdf','course','notes','website')),

  title                   text        not null,
  author                  text,
  provider                text,
  url                     text,

  -- optional link to an existing marketplace asset; never force-create one
  marketplace_resource_id uuid
                            references public.marketplace_assets(id) on delete set null,

  priority_order          int         not null default 0,

  recommended_for         text        not null default 'beginner'
                            check (recommended_for in ('beginner','intermediate','advanced','revision')),

  reviewer_status         mock_reviewer_status not null default 'draft',

  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

-- Primary access pattern: all resources for an exam × subject, ordered
create index if not exists idx_exam_subject_resources_exam_subject_priority
  on public.exam_subject_resources(exam_id, subject_id, priority_order);

-- Supporting lookups
create index if not exists idx_exam_subject_resources_phase
  on public.exam_subject_resources(exam_phase_id);

create index if not exists idx_exam_subject_resources_topic
  on public.exam_subject_resources(topic_id);

create index if not exists idx_exam_subject_resources_type
  on public.exam_subject_resources(resource_type);

create index if not exists idx_exam_subject_resources_reviewer_status
  on public.exam_subject_resources(reviewer_status);

create trigger trg_exam_subject_resources_updated_at
  before update on public.exam_subject_resources
  for each row execute function public.tg_set_updated_at();

notify pgrst, 'reload schema';
