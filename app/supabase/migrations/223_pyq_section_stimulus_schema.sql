-- 223_pyq_section_stimulus_schema.sql
-- PYQ Intelligence v2 delivery order, PR-1: schema fidelity for section
-- linkage, printed-order preservation, variable option counts, and shared
-- text/table stimuli (passages, caselets, DI tables) grouping multiple
-- questions.
--
-- Scope note: this PR is a text/shared-grouping scaffold only. `pyq_stimuli`
-- stores content_text + metadata; it does NOT add a first-class asset
-- (image/chart binary) reference, page/region locator, or accessibility/
-- alt-text contract. First-class media storage (FK to document_assets,
-- locators, alt-text) is explicitly deferred to PR-11 (advanced question
-- types and media) per docs/status/career-copilot-checklist.md.
--
-- Additive only: every new column is nullable and every existing importer
-- contract (pyq_bulk_import.py's fixed A-D option write path) continues to
-- work unchanged. Downstream consumers (importer v2, admin review, mock
-- projection, learner PYQ practice) are separate PRs — see the checklist.
--
-- Checkpost review (PR #892) fixes in this revision:
--   P0-1 cross-parent integrity: pyq_questions.section_id, pyq_stimuli.section_id
--        and pyq_question_stimuli links previously only checked FK existence, so
--        a section/stimulus/question from a different exam/phase/paper could be
--        linked. Triggers below enforce phase/paper agreement on insert, update,
--        and on the parent row being moved after links already exist.
--   P0-2 stimuli trust lifecycle: pyq_stimuli now carries reviewer_status/
--        reviewed_by/reviewed_at, mirroring pyq_questions/pyq_options (migration
--        103/155), so a later projection PR can gate on verified stimulus content.
--   P1   deterministic ordering: display_order columns now reject non-positive
--        values and are unique within their correct parent scope (paper questions,
--        question options, paper stimuli, question-stimulus links).

-- ── pyq_questions: section linkage + printed-order preservation ─────────────

alter table public.pyq_questions
  add column if not exists section_id uuid references public.exam_phase_sections(id) on delete set null,
  add column if not exists source_question_ref text,
  add column if not exists display_order integer;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.pyq_questions'::regclass
      and conname = 'pyq_questions_display_order_positive_chk'
  ) then
    alter table public.pyq_questions
      add constraint pyq_questions_display_order_positive_chk
      check (display_order is null or display_order >= 1);
  end if;
end $$;

create index if not exists idx_pyq_questions_section
  on public.pyq_questions(section_id) where section_id is not null;

create unique index if not exists pyq_questions_paper_display_order_uidx
  on public.pyq_questions(pyq_paper_id, display_order) where display_order is not null;

-- ── pyq_options: printed label + explicit display order ─────────────────────
-- option_label remains the normalized answer-matching key (A/B/C/D/1/2/...);
-- source_label preserves the as-printed form ("(a)", "IV", etc).

alter table public.pyq_options
  add column if not exists display_order integer,
  add column if not exists source_label text;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.pyq_options'::regclass
      and conname = 'pyq_options_display_order_positive_chk'
  ) then
    alter table public.pyq_options
      add constraint pyq_options_display_order_positive_chk
      check (display_order is null or display_order >= 1);
  end if;
end $$;

create unique index if not exists pyq_options_question_display_order_uidx
  on public.pyq_options(question_id, display_order) where display_order is not null;

-- ── pyq_stimuli: shared passages / caselets / DI tables ─────────────────────
-- Stored once per paper (or section) and linked to N questions through
-- pyq_question_stimuli, so a shared reading passage or data set is not
-- duplicated into every question row. Carries the same pending -> verified /
-- rejected / needs_correction review lifecycle as pyq_questions/pyq_options
-- so downstream projection can require verified stimulus content.

create table if not exists public.pyq_stimuli (
  id uuid primary key default gen_random_uuid(),
  pyq_paper_id uuid not null references public.pyq_papers(id) on delete cascade,
  section_id uuid references public.exam_phase_sections(id) on delete set null,
  stimulus_type text not null default 'passage'
    check (stimulus_type in ('passage', 'caselet', 'table', 'chart', 'image', 'diagram', 'other')),
  content_text text,
  language text,
  display_order integer,
  reviewer_status text not null default 'pending'
    check (reviewer_status in ('pending', 'verified', 'rejected', 'needs_correction')),
  reviewed_by uuid references public.profiles(id) on delete set null,
  reviewed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint pyq_stimuli_display_order_positive_chk
    check (display_order is null or display_order >= 1)
);

create index if not exists idx_pyq_stimuli_paper
  on public.pyq_stimuli(pyq_paper_id);

create index if not exists idx_pyq_stimuli_section
  on public.pyq_stimuli(section_id) where section_id is not null;

create index if not exists idx_pyq_stimuli_review
  on public.pyq_stimuli(reviewer_status);

create unique index if not exists pyq_stimuli_paper_display_order_uidx
  on public.pyq_stimuli(pyq_paper_id, display_order) where display_order is not null;

do $$
begin
  if not exists (
    select 1 from pg_trigger
    where tgname = 'trg_pyq_stimuli_updated_at'
      and tgrelid = 'public.pyq_stimuli'::regclass
  ) then
    create trigger trg_pyq_stimuli_updated_at
      before update on public.pyq_stimuli
      for each row execute function public.tg_set_updated_at();
  end if;
end $$;

-- ── pyq_question_stimuli: question <-> stimulus link (many-to-many) ────────
-- A stimulus can back multiple questions (e.g. one passage, five questions);
-- a question can reference multiple stimuli (e.g. a passage plus a chart).

create table if not exists public.pyq_question_stimuli (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.pyq_questions(id) on delete cascade,
  stimulus_id uuid not null references public.pyq_stimuli(id) on delete cascade,
  display_order integer,
  created_at timestamptz not null default now(),
  unique(question_id, stimulus_id),
  constraint pyq_question_stimuli_display_order_positive_chk
    check (display_order is null or display_order >= 1)
);

create index if not exists idx_pyq_question_stimuli_question
  on public.pyq_question_stimuli(question_id);

create index if not exists idx_pyq_question_stimuli_stimulus
  on public.pyq_question_stimuli(stimulus_id);

create unique index if not exists pyq_question_stimuli_question_display_order_uidx
  on public.pyq_question_stimuli(question_id, display_order) where display_order is not null;

-- ── Cross-parent integrity (checkpost P0-1) ─────────────────────────────────
-- FKs alone only prove a referenced row exists, not that it belongs to the
-- same exam phase / paper. These triggers close that gap on every write path
-- that can introduce or hide a mismatch: the child row's own insert/update,
-- and the parent row (section, paper, question, stimulus) being moved after
-- links already exist.

-- 1. pyq_questions.section_id must share its paper's exam_phase_id.
create or replace function public.pyq_validate_question_section()
returns trigger
language plpgsql
as $$
declare
  v_paper_phase uuid;
  v_section_phase uuid;
begin
  if new.section_id is null then
    return new;
  end if;

  select exam_phase_id into v_paper_phase
    from public.pyq_papers where id = new.pyq_paper_id;
  select exam_phase_id into v_section_phase
    from public.exam_phase_sections where id = new.section_id;

  if v_paper_phase is null or v_section_phase is null or v_paper_phase <> v_section_phase then
    raise exception
      'pyq_questions.section_id (%) exam_phase does not match pyq_paper_id (%) exam_phase',
      new.section_id, new.pyq_paper_id;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_pyq_questions_validate_section on public.pyq_questions;
create trigger trg_pyq_questions_validate_section
  before insert or update of section_id, pyq_paper_id on public.pyq_questions
  for each row execute function public.pyq_validate_question_section();

-- 2. pyq_stimuli.section_id must share its paper's exam_phase_id.
create or replace function public.pyq_validate_stimulus_section()
returns trigger
language plpgsql
as $$
declare
  v_paper_phase uuid;
  v_section_phase uuid;
begin
  if new.section_id is null then
    return new;
  end if;

  select exam_phase_id into v_paper_phase
    from public.pyq_papers where id = new.pyq_paper_id;
  select exam_phase_id into v_section_phase
    from public.exam_phase_sections where id = new.section_id;

  if v_paper_phase is null or v_section_phase is null or v_paper_phase <> v_section_phase then
    raise exception
      'pyq_stimuli.section_id (%) exam_phase does not match pyq_paper_id (%) exam_phase',
      new.section_id, new.pyq_paper_id;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_pyq_stimuli_validate_section on public.pyq_stimuli;
create trigger trg_pyq_stimuli_validate_section
  before insert or update of section_id, pyq_paper_id on public.pyq_stimuli
  for each row execute function public.pyq_validate_stimulus_section();

-- 3. pyq_question_stimuli must link within the same paper and, when both
--    sides carry a section, the same section.
create or replace function public.pyq_validate_question_stimulus_link()
returns trigger
language plpgsql
as $$
declare
  v_question_paper uuid;
  v_question_section uuid;
  v_stimulus_paper uuid;
  v_stimulus_section uuid;
begin
  select pyq_paper_id, section_id into v_question_paper, v_question_section
    from public.pyq_questions where id = new.question_id;
  select pyq_paper_id, section_id into v_stimulus_paper, v_stimulus_section
    from public.pyq_stimuli where id = new.stimulus_id;

  if v_question_paper is null or v_stimulus_paper is null or v_question_paper <> v_stimulus_paper then
    raise exception
      'pyq_question_stimuli links question % (paper %) to stimulus % (paper %) across papers',
      new.question_id, v_question_paper, new.stimulus_id, v_stimulus_paper;
  end if;

  if v_question_section is not null and v_stimulus_section is not null
     and v_question_section <> v_stimulus_section then
    raise exception
      'pyq_question_stimuli links question % (section %) to stimulus % (section %) across sections',
      new.question_id, v_question_section, new.stimulus_id, v_stimulus_section;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_pyq_question_stimuli_validate_link on public.pyq_question_stimuli;
create trigger trg_pyq_question_stimuli_validate_link
  before insert or update of question_id, stimulus_id on public.pyq_question_stimuli
  for each row execute function public.pyq_validate_question_stimulus_link();

-- 4. Re-validate dependants when a parent row moves after links already exist.

-- 4a. exam_phase_sections.exam_phase_id changes -> re-check dependent
--     pyq_questions / pyq_stimuli that reference this section.
create or replace function public.pyq_revalidate_section_move()
returns trigger
language plpgsql
as $$
begin
  if new.exam_phase_id is not distinct from old.exam_phase_id then
    return new;
  end if;

  if exists (
    select 1
    from public.pyq_questions q
    join public.pyq_papers p on p.id = q.pyq_paper_id
    where q.section_id = new.id and p.exam_phase_id <> new.exam_phase_id
  ) then
    raise exception
      'exam_phase_sections % move to exam_phase % would break pyq_questions.section_id integrity',
      new.id, new.exam_phase_id;
  end if;

  if exists (
    select 1
    from public.pyq_stimuli s
    join public.pyq_papers p on p.id = s.pyq_paper_id
    where s.section_id = new.id and p.exam_phase_id <> new.exam_phase_id
  ) then
    raise exception
      'exam_phase_sections % move to exam_phase % would break pyq_stimuli.section_id integrity',
      new.id, new.exam_phase_id;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_exam_phase_sections_revalidate_move on public.exam_phase_sections;
create trigger trg_exam_phase_sections_revalidate_move
  before update of exam_phase_id on public.exam_phase_sections
  for each row execute function public.pyq_revalidate_section_move();

-- 4b. pyq_papers.exam_phase_id changes -> re-check dependent
--     pyq_questions / pyq_stimuli with a non-null section_id under this paper.
create or replace function public.pyq_revalidate_paper_phase_move()
returns trigger
language plpgsql
as $$
begin
  if new.exam_phase_id is not distinct from old.exam_phase_id then
    return new;
  end if;

  if exists (
    select 1
    from public.pyq_questions q
    join public.exam_phase_sections s on s.id = q.section_id
    where q.pyq_paper_id = new.id and s.exam_phase_id <> new.exam_phase_id
  ) then
    raise exception
      'pyq_papers % move to exam_phase % would break pyq_questions.section_id integrity',
      new.id, new.exam_phase_id;
  end if;

  if exists (
    select 1
    from public.pyq_stimuli st
    join public.exam_phase_sections s on s.id = st.section_id
    where st.pyq_paper_id = new.id and s.exam_phase_id <> new.exam_phase_id
  ) then
    raise exception
      'pyq_papers % move to exam_phase % would break pyq_stimuli.section_id integrity',
      new.id, new.exam_phase_id;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_pyq_papers_revalidate_phase_move on public.pyq_papers;
create trigger trg_pyq_papers_revalidate_phase_move
  before update of exam_phase_id on public.pyq_papers
  for each row execute function public.pyq_revalidate_paper_phase_move();

-- 4c. pyq_questions.pyq_paper_id changes -> re-check existing question<->stimulus
--     links for this question against the new paper.
create or replace function public.pyq_revalidate_question_paper_move()
returns trigger
language plpgsql
as $$
begin
  if new.pyq_paper_id is not distinct from old.pyq_paper_id then
    return new;
  end if;

  if exists (
    select 1
    from public.pyq_question_stimuli qs
    join public.pyq_stimuli st on st.id = qs.stimulus_id
    where qs.question_id = new.id and st.pyq_paper_id <> new.pyq_paper_id
  ) then
    raise exception
      'pyq_questions % move to paper % would break pyq_question_stimuli cross-paper integrity',
      new.id, new.pyq_paper_id;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_pyq_questions_revalidate_paper_move on public.pyq_questions;
create trigger trg_pyq_questions_revalidate_paper_move
  before update of pyq_paper_id on public.pyq_questions
  for each row execute function public.pyq_revalidate_question_paper_move();

-- 4d. pyq_stimuli.pyq_paper_id changes -> re-check existing question<->stimulus
--     links for this stimulus against the new paper.
create or replace function public.pyq_revalidate_stimulus_paper_move()
returns trigger
language plpgsql
as $$
begin
  if new.pyq_paper_id is not distinct from old.pyq_paper_id then
    return new;
  end if;

  if exists (
    select 1
    from public.pyq_question_stimuli qs
    join public.pyq_questions q on q.id = qs.question_id
    where qs.stimulus_id = new.id and q.pyq_paper_id <> new.pyq_paper_id
  ) then
    raise exception
      'pyq_stimuli % move to paper % would break pyq_question_stimuli cross-paper integrity',
      new.id, new.pyq_paper_id;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_pyq_stimuli_revalidate_paper_move on public.pyq_stimuli;
create trigger trg_pyq_stimuli_revalidate_paper_move
  before update of pyq_paper_id on public.pyq_stimuli
  for each row execute function public.pyq_revalidate_stimulus_paper_move();

-- ── RLS ──────────────────────────────────────────────────────────────────────
-- Mirrors the existing pyq_papers/pyq_questions/pyq_options posture (migration
-- 035 + repointed in 195): admin/service-role only. Aspirant-facing reads
-- continue to flow through the reviewed mock_question_bank projection, not
-- direct canonical-table access.

alter table public.pyq_stimuli enable row level security;
alter table public.pyq_question_stimuli enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'pyq_stimuli' and policyname = 'pyq_stimuli_admin_all'
  ) then
    create policy pyq_stimuli_admin_all on public.pyq_stimuli
      for all to authenticated
      using (public.is_admin(auth.uid()))
      with check (public.is_admin(auth.uid()));
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'pyq_question_stimuli' and policyname = 'pyq_question_stimuli_admin_all'
  ) then
    create policy pyq_question_stimuli_admin_all on public.pyq_question_stimuli
      for all to authenticated
      using (public.is_admin(auth.uid()))
      with check (public.is_admin(auth.uid()));
  end if;
end $$;

notify pgrst, 'reload schema';
