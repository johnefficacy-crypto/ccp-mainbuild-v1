-- 293_descriptive_attempts.sql
-- Descriptive answer-writing practice — the aspirant's own attempts.
--
-- ~12k verified descriptive PYQ rows exist (`pyq_questions.question_type =
-- 'descriptive'`), mostly UPSC CSE Mains optionals. The mock engine is MCQ-only
-- and cannot host them: a descriptive answer is prose, judged by the aspirant
-- against a rubric, not scored against an option key.
--
-- One row per attempt at ONE question. Practice is question-level on purpose —
-- a Mains paper is three hours and a fifth of the corpus has no marks value, so
-- a paper-level runtime would be a timer with nothing to time.
--
-- HUMAN DECISION AUTHORITY: `self_scores` is the aspirant's own rubric
-- judgement, 0..2 per criterion. Nothing in this table is machine-scored, and
-- v1 adds no AI evaluation of any kind. `self_total` is a stored sum, not a
-- grade.

create table if not exists public.descriptive_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  pyq_question_id uuid not null references public.pyq_questions(id) on delete cascade,

  status text not null default 'draft'
    check (status in ('draft', 'submitted')),

  -- `not null default ''` rather than nullable: an attempt with no text yet is
  -- an empty answer, not an unknown one, and the word count below is computed
  -- from it on every save.
  answer_text text not null default '',
  word_count integer not null default 0 check (word_count >= 0),

  time_spent_seconds integer not null default 0 check (time_spent_seconds >= 0),
  -- Derived from the question's marks when it has one (~13% of rows do), null
  -- otherwise. Advisory: the UI shows it and never enforces it.
  timer_target_seconds integer null check (timer_target_seconds is null or timer_target_seconds > 0),

  -- {structure, relevance, coverage, examples, conclusion, within_limit}, each
  -- 0..2. Shape is validated in the API rather than by a CHECK so a future
  -- rubric revision does not need an immutable migration edited.
  self_scores jsonb null,
  self_total integer null check (self_total is null or (self_total >= 0 and self_total <= 12)),
  notes text null,

  started_at timestamptz not null default now(),
  submitted_at timestamptz null,
  updated_at timestamptz not null default now(),

  -- A submitted attempt must carry its submission time, and a draft must not.
  constraint descriptive_attempts_submitted_at_matches_status
    check (
      (status = 'submitted' and submitted_at is not null)
      or (status = 'draft' and submitted_at is null)
    )
);

create index if not exists idx_descriptive_attempts_user_question
  on public.descriptive_attempts(user_id, pyq_question_id);

create index if not exists idx_descriptive_attempts_user_submitted
  on public.descriptive_attempts(user_id, submitted_at desc);

-- One OPEN draft per user per question. Submitted attempts are unconstrained,
-- so an aspirant can answer the same question again after submitting — which is
-- the whole point of revisiting a PYQ — but cannot accumulate parallel drafts of
-- the same question across two tabs.
create unique index if not exists uq_descriptive_attempts_open_draft
  on public.descriptive_attempts(user_id, pyq_question_id)
  where status = 'draft';

-- ── RLS ──────────────────────────────────────────────────────────────────
-- Pattern A (user-owned data): the aspirant reads and writes their own rows
-- directly, mirroring the owner policies used by user_study_plan_preferences.
-- The FastAPI layer additionally scopes every query by user_id, because it runs
-- on service_role and RLS does not constrain it.
alter table public.descriptive_attempts enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'descriptive_attempts'
      and policyname = 'descriptive_attempts_owner_select'
  ) then
    create policy descriptive_attempts_owner_select
      on public.descriptive_attempts
      for select to authenticated using (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'descriptive_attempts'
      and policyname = 'descriptive_attempts_owner_insert'
  ) then
    create policy descriptive_attempts_owner_insert
      on public.descriptive_attempts
      for insert to authenticated with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'descriptive_attempts'
      and policyname = 'descriptive_attempts_owner_update'
  ) then
    create policy descriptive_attempts_owner_update
      on public.descriptive_attempts
      for update to authenticated
      using (auth.uid() = user_id)
      with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'descriptive_attempts'
      and policyname = 'descriptive_attempts_owner_delete'
  ) then
    create policy descriptive_attempts_owner_delete
      on public.descriptive_attempts
      for delete to authenticated
      using (auth.uid() = user_id);
  end if;
end $$;

notify pgrst, 'reload schema';
