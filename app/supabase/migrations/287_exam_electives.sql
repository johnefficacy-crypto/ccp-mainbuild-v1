-- Migration 287: elective sections + the user's chosen elective (OPT-CHOICE-01 Q4/Q1)
--
-- Twelve optional-paper subjects went live with the thematic load (48cca21) and
-- immediately widened every derived-from-coverage surface: onboarding calibration
-- began demanding 16 subjects, the Subject Practice Hub rendered twelve optional
-- cards, and the planner started ranking a PSIR aspirant's week against
-- Anthropology Paper-II. All three share one cause — nothing in the schema says
-- which sections a user must study and which they CHOOSE.
--
-- The asymmetry is not "GS versus optionals"; it is compulsory versus elective,
-- which is a property of the exam's structure. Marking it here means no code ever
-- pattern-matches a slug to decide scope, and Essay, CSAT and every other exam's
-- electives get the right answer for free.
--
-- Scope rule this enables, in one sentence: a subject is in scope if its section
-- is 'compulsory', OR it is 'elective' and its subject id is in the user's choice
-- for that elective group.

-- ─── A. Mark the electives on the exam structure ──────────────────────────
--
-- DEFAULT 'compulsory' is the safety property: every section that exists today
-- stays in scope for every user, so adding these columns alone changes nothing.
-- Only the explicit backfill in section C moves rows out of the default.

alter table public.exam_phase_sections
  add column if not exists selection_kind text not null default 'compulsory',
  add column if not exists elective_group text;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'exam_phase_sections_selection_kind_check'
      and conrelid = 'public.exam_phase_sections'::regclass
  ) then
    alter table public.exam_phase_sections
      add constraint exam_phase_sections_selection_kind_check
      check (selection_kind in ('compulsory', 'elective'));
  end if;
end $$;

-- An elective section without a group cannot be matched against any user choice,
-- so it would be silently unreachable. Require the pair.
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'exam_phase_sections_elective_group_check'
      and conrelid = 'public.exam_phase_sections'::regclass
  ) then
    alter table public.exam_phase_sections
      add constraint exam_phase_sections_elective_group_check
      check (selection_kind = 'compulsory' or elective_group is not null);
  end if;
end $$;

create index if not exists idx_exam_phase_sections_selection
  on public.exam_phase_sections(selection_kind, elective_group);

comment on column public.exam_phase_sections.selection_kind is
  'compulsory = every candidate sits it; elective = the candidate chooses. Scope '
  'filtering keys on THIS, never on a subject slug or name.';
comment on column public.exam_phase_sections.elective_group is
  'Names the choice an elective section belongs to (e.g. upsc-cse-optional). NULL '
  'for compulsory sections; required for elective ones.';

-- ─── B. The user's choice ─────────────────────────────────────────────────
--
-- Per-exam, mirroring user_exam_calibration (migration 199) and user_exam_goals
-- (065). Not the profile (single-valued target_exam) and not the plan (plans
-- regenerate; an enrolment fact must not).
--
-- subject_ids is an array because on this exam a chosen optional is TWO subjects
-- — paper is subject. It carries no FK: the API validates each id against the
-- exam's elective sections before writing, and an EMPTY array is the legitimate
-- "still choosing, or my optional is not in the corpus" state — not an error.

create table if not exists public.user_exam_electives (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  exam_id uuid not null references public.exams(id) on delete cascade,
  elective_group text not null,
  choice_key text,
  subject_ids uuid[] not null default '{}'::uuid[],
  chosen_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists uq_user_exam_electives
  on public.user_exam_electives(user_id, exam_id, elective_group);
create index if not exists idx_user_exam_electives_user
  on public.user_exam_electives(user_id);

alter table public.user_exam_electives enable row level security;

-- Writes are service-role-only — the backend validates subject ids against the
-- exam's elective sections before persisting, so a client must not write direct.
-- Mirrors migration 199: a SELECT policy only; the absence of INSERT/UPDATE/DELETE
-- policies means authenticated/anon cannot write.
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'user_exam_electives'
      and policyname = 'owner_select'
  ) then
    create policy "owner_select" on public.user_exam_electives
      for select using (user_id = auth.uid());
  end if;
end $$;

comment on table public.user_exam_electives is
  'The elective a user chose for one exam. No row, or an empty subject_ids, means '
  'undecided — which scopes Study OS to compulsory sections only. That is a valid '
  'state, never an error.';

-- ─── C. Backfill: mark the twelve UPSC optional-paper sections ────────────
--
-- Keyed on subjects.subject_group = 'upsc-optional', the governed subject-family
-- key the load script set (OPT-LOAD-03_subjects_sections.ps1:28) — NOT on the
-- slug or the display name. This is a one-time data classification; after it,
-- runtime scope reads selection_kind and never inspects a subject's identity.
--
-- Idempotent: re-running matches the same rows and rewrites the same values.
-- Every section NOT matched here keeps the 'compulsory' default and stays visible.

update public.exam_phase_sections s
   set selection_kind = 'elective',
       elective_group = 'upsc-cse-optional',
       updated_at = now()
  from public.subjects sub
 where sub.id = s.subject_id
   and sub.subject_group = 'upsc-optional'
   and (s.selection_kind is distinct from 'elective'
        or s.elective_group is distinct from 'upsc-cse-optional');
