-- 241_exam_streams_schema.sql
--
-- Lane R (Financial Regulatory & Development Institutions) — stream schema
-- contract, P0. Contract: docs/architecture/financial-regulatory-development-family.md §3.
--
-- Why a full contract and not just a `stream_id` on sections:
--   * exam_phases owns duration / total_questions / total_marks /
--     negative_marking (030_exam_registry_cycles_phases.sql:50-67), so a
--     stream that runs a different Phase-II paper needs its OWN phase row,
--     not just a section tag.
--   * The existing section uniqueness key (exam_phase_id, subject_id,
--     section_label) (030:92) rejects the same subject/label across streams.
--   * The phase uniqueness keys (030:69-75) reject the same phase_slug across
--     streams.
--
-- This migration is ADDITIVE and never edits the merged 030 migration. It:
--   1. Adds canonical `exam_streams` + per-cycle `exam_cycle_streams`.
--   2. Adds a nullable `stream_id` to exam_phases / exam_phase_sections /
--      exam_topic_coverage. NULL = a common row that applies to all streams.
--   3. Replaces the phase/section/coverage uniqueness with stream-aware keys
--      that COALESCE(stream_id, zero-uuid) so common and per-stream rows coexist.
--
-- NOT in scope (documented follow-ups, tracked in the Lane R checklist):
--   * Reconciling the loose `stream_key text` on
--     exam_descriptive_requirements (205:136) into an exam_streams FK — needs
--     seeded streams first (Lane R identity seed, §6) and touches Lane H (EWP).
--   * Seeding actual stream rows for RBI/SEBI/NABARD/IRDAI/PFRDA/IFSCA/SIDBI.

-- ─── 1. Canonical stream identity ────────────────────────────────────────
create table if not exists public.exam_streams (
  id uuid primary key default gen_random_uuid(),
  exam_id uuid not null references public.exams(id) on delete cascade,
  stream_key text not null,
  name text not null,
  description text,
  is_active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (exam_id, stream_key)
);

create index if not exists idx_exam_streams_exam
  on public.exam_streams(exam_id);
create index if not exists idx_exam_streams_active
  on public.exam_streams(is_active);

-- ─── 2. Per-cycle stream availability / activation ───────────────────────
create table if not exists public.exam_cycle_streams (
  id uuid primary key default gen_random_uuid(),
  exam_cycle_id uuid not null references public.exam_cycles(id) on delete cascade,
  stream_id uuid not null references public.exam_streams(id) on delete cascade,
  availability text not null default 'expected'
    check (availability in ('offered', 'not_offered', 'expected')),
  vacancy_count integer,
  status text not null default 'active'
    check (status in ('expected', 'active', 'completed', 'cancelled')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (exam_cycle_id, stream_id)
);

create index if not exists idx_exam_cycle_streams_cycle
  on public.exam_cycle_streams(exam_cycle_id);
create index if not exists idx_exam_cycle_streams_stream
  on public.exam_cycle_streams(stream_id);

-- ─── 3. Stream scoping on phases / sections / coverage ───────────────────
-- NULL stream_id = a common row shared by every stream. A non-NULL stream_id
-- is a stream-specific variant carrying its own duration/marks/negative
-- marking (phase) or question_count/marks (section).
alter table public.exam_phases
  add column if not exists stream_id uuid references public.exam_streams(id) on delete cascade;
alter table public.exam_phase_sections
  add column if not exists stream_id uuid references public.exam_streams(id) on delete cascade;
alter table public.exam_topic_coverage
  add column if not exists stream_id uuid references public.exam_streams(id) on delete cascade;

create index if not exists idx_exam_phases_stream
  on public.exam_phases(stream_id);
create index if not exists idx_exam_phase_sections_stream
  on public.exam_phase_sections(stream_id);
create index if not exists idx_exam_topic_coverage_stream
  on public.exam_topic_coverage(stream_id);

-- ─── 4. Stream-aware uniqueness ──────────────────────────────────────────
-- COALESCE(stream_id, zero-uuid) lets a common row (NULL) and one row per
-- stream coexist under the same natural key. The zero UUID is never a real
-- exam_streams.id (gen_random_uuid never returns it), so it is a safe
-- sentinel for "common / no stream".

-- Phases: replace the two partial unique indexes from 030:69-75.
drop index if exists public.exam_phases_exam_cycle_slug_uidx;
drop index if exists public.exam_phases_exam_slug_no_cycle_uidx;

create unique index if not exists exam_phases_exam_cycle_stream_slug_uidx
  on public.exam_phases(
    exam_id,
    exam_cycle_id,
    coalesce(stream_id, '00000000-0000-0000-0000-000000000000'::uuid),
    phase_slug
  )
  where exam_cycle_id is not null;

create unique index if not exists exam_phases_exam_stream_slug_no_cycle_uidx
  on public.exam_phases(
    exam_id,
    coalesce(stream_id, '00000000-0000-0000-0000-000000000000'::uuid),
    phase_slug
  )
  where exam_cycle_id is null;

-- Sections: replace the inline table constraint from 030:92. Its
-- auto-generated name can vary across environments, so look it up by
-- definition rather than assuming a fixed constraint name.
do $$
declare
  cname text;
begin
  select conname into cname
  from pg_constraint
  where conrelid = 'public.exam_phase_sections'::regclass
    and contype = 'u'
    and pg_get_constraintdef(oid) ilike '%(exam_phase_id, subject_id, section_label)%';
  if cname is not null then
    execute format('alter table public.exam_phase_sections drop constraint %I', cname);
  end if;
end $$;

create unique index if not exists exam_phase_sections_phase_stream_subject_label_uidx
  on public.exam_phase_sections(
    exam_phase_id,
    coalesce(stream_id, '00000000-0000-0000-0000-000000000000'::uuid),
    subject_id,
    section_label
  );

-- Coverage: replace the two partial unique indexes from 030:124-130 so
-- stream-scoped high-yield coverage can coexist with common coverage.
drop index if exists public.exam_topic_coverage_cycle_phase_topic_uidx;
drop index if exists public.exam_topic_coverage_exam_phase_topic_uidx;

create unique index if not exists exam_topic_coverage_cycle_phase_stream_topic_uidx
  on public.exam_topic_coverage(
    exam_id,
    exam_cycle_id,
    exam_phase_id,
    coalesce(stream_id, '00000000-0000-0000-0000-000000000000'::uuid),
    topic_id
  )
  where exam_cycle_id is not null and exam_phase_id is not null;

create unique index if not exists exam_topic_coverage_exam_phase_stream_topic_uidx
  on public.exam_topic_coverage(
    exam_id,
    exam_phase_id,
    coalesce(stream_id, '00000000-0000-0000-0000-000000000000'::uuid),
    topic_id
  )
  where exam_cycle_id is null and exam_phase_id is not null;

-- ─── 5. RLS ──────────────────────────────────────────────────────────────
-- Reference data: authenticated read; writes remain service-role only,
-- matching exam_cycles / exam_phases (035_exam_intelligence_rls_indexes.sql).
alter table public.exam_streams enable row level security;
alter table public.exam_cycle_streams enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='exam_streams' and policyname='exam_streams_read_authenticated') then
    create policy exam_streams_read_authenticated on public.exam_streams
      for select to authenticated using (true);
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='exam_cycle_streams' and policyname='exam_cycle_streams_read_authenticated') then
    create policy exam_cycle_streams_read_authenticated on public.exam_cycle_streams
      for select to authenticated using (true);
  end if;
end $$;

-- ─── 6. updated_at triggers ──────────────────────────────────────────────
drop trigger if exists exam_streams_updated_at on public.exam_streams;
create trigger exam_streams_updated_at
  before update on public.exam_streams
  for each row execute function public.tg_set_updated_at();

drop trigger if exists exam_cycle_streams_updated_at on public.exam_cycle_streams;
create trigger exam_cycle_streams_updated_at
  before update on public.exam_cycle_streams
  for each row execute function public.tg_set_updated_at();

notify pgrst, 'reload schema';
