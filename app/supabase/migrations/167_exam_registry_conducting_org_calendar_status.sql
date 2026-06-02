-- 167_exam_registry_conducting_org_calendar_status.sql
-- Two additive columns to support bulk workbook import of State PSC exam registry:
--
-- 1. exams.conducting_organization_id  — nullable FK to organizations so an exam
--    can record which body runs it without coupling to the recruitment pipeline.
--    The recruitment pipeline's organizations rows coexist; no existing data changes.
--
-- 2. organizations.calendar_status — body-level signal for whether the conducting
--    body publishes an annual exam calendar.  Placed on organizations (not exam_cycles)
--    because it describes the body's publishing behaviour, which is stable across
--    cycles and would drift badly if replicated per-cycle.
--    Enum: published | tentative | partial | needs_review
--
-- Both columns are nullable with no defaults so pre-existing rows are untouched.
-- Re-runnable (if not exists / add column if not exists).

alter table public.exams
  add column if not exists conducting_organization_id uuid
    references public.organizations(id) on delete set null;

alter table public.organizations
  add column if not exists calendar_status text
    check (calendar_status in ('published', 'tentative', 'partial', 'needs_review'));

create index if not exists idx_exams_conducting_org
  on public.exams(conducting_organization_id);

notify pgrst, 'reload schema';
