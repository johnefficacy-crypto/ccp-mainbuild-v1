-- 223_pyq_section_stimulus_schema.sql
-- PYQ Intelligence v2 delivery order, PR-1: schema fidelity for section
-- linkage, printed-order preservation, variable option counts, and shared
-- stimuli (passages/caselets/tables/images) grouping multiple questions.
--
-- Additive only: every new column is nullable and every existing importer
-- contract (pyq_bulk_import.py's fixed A-D option write path) continues to
-- work unchanged. Downstream consumers (importer v2, admin review, mock
-- projection, learner PYQ practice) are separate PRs per
-- docs/architecture/pyq-intelligence-v2.md delivery order.

-- ── pyq_questions: section linkage + printed-order preservation ─────────────

alter table public.pyq_questions
  add column if not exists section_id uuid references public.exam_phase_sections(id) on delete set null,
  add column if not exists source_question_ref text,
  add column if not exists display_order integer;

create index if not exists idx_pyq_questions_section
  on public.pyq_questions(section_id) where section_id is not null;

-- ── pyq_options: printed label + explicit display order ─────────────────────
-- option_label remains the normalized answer-matching key (A/B/C/D/1/2/...);
-- source_label preserves the as-printed form ("(a)", "IV", etc).

alter table public.pyq_options
  add column if not exists display_order integer,
  add column if not exists source_label text;

-- ── pyq_stimuli: shared passages / caselets / DI tables / images ────────────
-- Stored once per paper (or section) and linked to N questions through
-- pyq_question_stimuli, so a shared reading passage or data set is not
-- duplicated into every question row.

create table if not exists public.pyq_stimuli (
  id uuid primary key default gen_random_uuid(),
  pyq_paper_id uuid not null references public.pyq_papers(id) on delete cascade,
  section_id uuid references public.exam_phase_sections(id) on delete set null,
  stimulus_type text not null default 'passage'
    check (stimulus_type in ('passage', 'caselet', 'table', 'chart', 'image', 'diagram', 'other')),
  content_text text,
  language text,
  display_order integer,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_pyq_stimuli_paper
  on public.pyq_stimuli(pyq_paper_id);

create index if not exists idx_pyq_stimuli_section
  on public.pyq_stimuli(section_id) where section_id is not null;

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

-- ── pyq_question_stimuli: question ↔ stimulus link (many-to-many) ──────────
-- A stimulus can back multiple questions (e.g. one passage, five questions);
-- a question can reference multiple stimuli (e.g. a passage plus a chart).

create table if not exists public.pyq_question_stimuli (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.pyq_questions(id) on delete cascade,
  stimulus_id uuid not null references public.pyq_stimuli(id) on delete cascade,
  display_order integer,
  created_at timestamptz not null default now(),
  unique(question_id, stimulus_id)
);

create index if not exists idx_pyq_question_stimuli_question
  on public.pyq_question_stimuli(question_id);

create index if not exists idx_pyq_question_stimuli_stimulus
  on public.pyq_question_stimuli(stimulus_id);

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
