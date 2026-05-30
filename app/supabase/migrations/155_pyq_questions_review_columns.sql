-- Add reviewer audit columns to pyq_questions to match the generic review handler
-- in admin_exam_intelligence.py which always patches reviewed_by + reviewed_at.
alter table public.pyq_questions
    add column if not exists reviewed_by  uuid        references public.profiles(id) on delete set null,
    add column if not exists reviewed_at  timestamptz;

create index if not exists pyq_questions_reviewed_by_idx on public.pyq_questions(reviewed_by);

notify pgrst, 'reload schema';
