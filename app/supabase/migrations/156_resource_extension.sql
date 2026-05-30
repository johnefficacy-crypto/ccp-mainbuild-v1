-- Extend community_resources for exam-prep material.
-- Adds new resource_type values and nullable FK/classification columns.
-- All new columns are nullable — zero data loss, no backfill required.

-- 1. Extend resource_type check constraint.
alter table public.community_resources
  drop constraint if exists community_resources_resource_type_check;

alter table public.community_resources
  add constraint community_resources_resource_type_check
    check (resource_type in (
      'pyq_paper','notes','strategy_guide','video_link','course_link','book',
      'concept_note','formula_sheet','grammar_sheet','vocabulary_sheet',
      'drill_set','practice_set','current_affairs_digest','scheme_card',
      'pyq_solution','mindmap','revision_sheet'
    ));

-- 2. Nullable FK columns to exam taxonomy.
alter table public.community_resources
  add column if not exists exam_id         uuid references public.exams(id)       on delete set null,
  add column if not exists exam_phase_id   uuid references public.exam_phases(id) on delete set null,
  add column if not exists subject_id      uuid references public.subjects(id)    on delete set null,
  add column if not exists topic_id        uuid references public.topics(id)      on delete set null,
  add column if not exists microtopic_id   uuid references public.topics(id)      on delete set null;

-- 3. Classification / workflow columns (all nullable except the bool default).
alter table public.community_resources
  add column if not exists difficulty               text,
  add column if not exists resource_level           text,
  add column if not exists content_format           text,
  add column if not exists source_kind              text,
  add column if not exists reviewer_status          text,
  add column if not exists valid_from               date,
  add column if not exists valid_until              date,
  add column if not exists usable_for_mock_generation boolean not null default false;

-- 4. Supporting indexes for the new FK columns.
create index if not exists idx_community_resources_exam_id
  on public.community_resources(exam_id) where exam_id is not null;
create index if not exists idx_community_resources_subject_id
  on public.community_resources(subject_id) where subject_id is not null;
create index if not exists idx_community_resources_topic_id
  on public.community_resources(topic_id) where topic_id is not null;

notify pgrst, 'reload schema';
