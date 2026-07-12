-- 242_exam_streams_schema.sql
-- (renumbered from 241 → 242 to resolve a duplicate-version collision on main:
--  241_current_affairs_source_evidence.sql already claimed 241. Content is
--  unchanged from the original 241 file.)
--
-- Lane R (Financial Regulatory & Development Institutions) — stream schema
-- contract, P0. Contract: docs/architecture/financial-regulatory-development-family.md §3.
--
-- Why a full contract and not just a `stream_id` on sections:
--   * exam_phases owns duration / total_questions / total_marks /
--     negative_marking (030_exam_registry_cycles_phases.sql:50-67), so a
--     stream that runs a different Phase-II paper needs its OWN phase row.
--   * The section uniqueness key (exam_phase_id, subject_id, section_label)
--     (030:92) and the phase uniqueness keys (030:69-75) reject the same
--     slug / subject-label across streams.
--
-- This migration is ADDITIVE and never edits the merged 030 migration.
--
-- Integrity posture (checkpost P0/P1): foreign keys alone allow contradictory
-- cross-parent rows (a cycle of exam A paired with a stream of exam B, a
-- section whose stream differs from its phase, …). The repo already treats
-- independent-FK parent consistency as a required DB-level invariant enforced
-- by triggers (219 `_ecc_check_scope`, 223), NOT by FKs. This migration takes
-- the same fail-closed posture for INSERT and UPDATE (parent reassignment
-- included) via the `_exam_stream_*` trigger functions below.
--
-- Null-safe uniqueness: a NULL `stream_id` means "common row shared by all
-- streams". Uniqueness uses `NULLS NOT DISTINCT` (PG15+, as in migration 219)
-- so a single common row coexists with one row per stream WITHOUT relying on a
-- magic sentinel UUID that a service-role insert could forge.
--
-- Retire, don't destroy: references TO the canonical stream identity use
-- ON DELETE RESTRICT — streams are retired via `is_active=false`, never hard
-- deleted out from under historical phases/sections/coverage. CASCADE is kept
-- only where the parent EXAM or CYCLE is itself intentionally removed.
--
-- NOT in scope (documented follow-ups, tracked in the Lane R checklist):
--   * Reconciling the loose `stream_key text` on exam_descriptive_requirements
--     (205:136) into an exam_streams FK — needs seeded streams (§6) and touches
--     Lane H (EWP).
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
-- exam_cycle_id cascades from its cycle; stream_id RESTRICTs (retire the
-- stream via is_active instead of deleting it).
create table if not exists public.exam_cycle_streams (
  id uuid primary key default gen_random_uuid(),
  exam_cycle_id uuid not null references public.exam_cycles(id) on delete cascade,
  stream_id uuid not null references public.exam_streams(id) on delete restrict,
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
-- is a stream-specific variant. RESTRICT (not CASCADE) so retiring/removing a
-- stream cannot silently erase historical phases/sections/coverage.
alter table public.exam_phases
  add column if not exists stream_id uuid references public.exam_streams(id) on delete restrict;
alter table public.exam_phase_sections
  add column if not exists stream_id uuid references public.exam_streams(id) on delete restrict;
alter table public.exam_topic_coverage
  add column if not exists stream_id uuid references public.exam_streams(id) on delete restrict;

create index if not exists idx_exam_phases_stream
  on public.exam_phases(stream_id);
create index if not exists idx_exam_phase_sections_stream
  on public.exam_phase_sections(stream_id);
create index if not exists idx_exam_topic_coverage_stream
  on public.exam_topic_coverage(stream_id);

-- ─── 4. Stream-aware uniqueness (NULLS NOT DISTINCT) ─────────────────────
-- Phases: replace the two partial unique indexes from 030:69-75.
drop index if exists public.exam_phases_exam_cycle_slug_uidx;
drop index if exists public.exam_phases_exam_slug_no_cycle_uidx;

create unique index if not exists exam_phases_exam_cycle_stream_slug_uidx
  on public.exam_phases(exam_id, exam_cycle_id, stream_id, phase_slug)
  nulls not distinct
  where exam_cycle_id is not null;

create unique index if not exists exam_phases_exam_stream_slug_no_cycle_uidx
  on public.exam_phases(exam_id, stream_id, phase_slug)
  nulls not distinct
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
  on public.exam_phase_sections(exam_phase_id, stream_id, subject_id, section_label)
  nulls not distinct;

-- Coverage: replace the two partial unique indexes from 030:124-130.
drop index if exists public.exam_topic_coverage_cycle_phase_topic_uidx;
drop index if exists public.exam_topic_coverage_exam_phase_topic_uidx;

create unique index if not exists exam_topic_coverage_cycle_phase_stream_topic_uidx
  on public.exam_topic_coverage(exam_id, exam_cycle_id, exam_phase_id, stream_id, topic_id)
  nulls not distinct
  where exam_cycle_id is not null and exam_phase_id is not null;

create unique index if not exists exam_topic_coverage_exam_phase_stream_topic_uidx
  on public.exam_topic_coverage(exam_id, exam_phase_id, stream_id, topic_id)
  nulls not distinct
  where exam_cycle_id is null and exam_phase_id is not null;

-- ─── 5. Cross-parent integrity (fail-closed, BOTH directions) ────────────
-- FKs cannot express "same exam across two independent parents". These
-- triggers reject contradictory rows for every writer (including raw
-- service-role inserts). Parent reads take FOR SHARE locks so a concurrent
-- parent move cannot slip between the check and the commit (223 posture).
-- Child triggers guard INSERT/UPDATE of the child; parent-side triggers
-- (§5f) guard the parent move / cycle-stream demotion / delete so the
-- invariant cannot be broken from either side.

-- Shared helper: is (cycle, stream) an offered/expected pair for that cycle?
create or replace function public._exam_cycle_stream_available(p_cycle uuid, p_stream uuid)
returns boolean language sql stable as $fn$
  select exists (
    select 1 from public.exam_cycle_streams ecs
    where ecs.exam_cycle_id = p_cycle
      and ecs.stream_id = p_stream
      and ecs.availability in ('offered', 'expected')
  );
$fn$;

-- Shared helper: does a cycle-bound stream phase depend on this (cycle, stream)?
create or replace function public._exam_cycle_stream_has_dependents(p_cycle uuid, p_stream uuid)
returns boolean language sql stable as $fn$
  select exists (
    select 1 from public.exam_phases p
    where p.exam_cycle_id = p_cycle and p.stream_id = p_stream
  );
$fn$;

-- 5a. exam_cycle_streams: the cycle and the stream must belong to one exam.
create or replace function public._exam_cycle_streams_check_parent() returns trigger
language plpgsql as $fn$
declare
  v_cycle_exam uuid;
  v_stream_exam uuid;
begin
  select exam_id into v_cycle_exam from public.exam_cycles where id = new.exam_cycle_id for share;
  select exam_id into v_stream_exam from public.exam_streams where id = new.stream_id for share;
  if v_cycle_exam is distinct from v_stream_exam then
    raise exception 'exam_cycle_streams: cycle % (exam %) and stream % (exam %) belong to different exams',
      new.exam_cycle_id, v_cycle_exam, new.stream_id, v_stream_exam using errcode = 'P0422';
  end if;

  -- Demotion / pair-move guard: a cycle-bound stream phase must keep an
  -- offered/expected pair. Reject demoting availability, or moving the pair
  -- identity, out from under existing dependent phases.
  if tg_op = 'UPDATE' then
    if old.availability in ('offered', 'expected')
       and new.availability not in ('offered', 'expected')
       and public._exam_cycle_stream_has_dependents(old.exam_cycle_id, old.stream_id) then
      raise exception 'exam_cycle_streams: cannot demote availability to % — cycle-bound stream phases depend on the offered/expected (cycle=%, stream=%) pair',
        new.availability, old.exam_cycle_id, old.stream_id using errcode = 'P0422';
    end if;
    if (new.exam_cycle_id, new.stream_id) is distinct from (old.exam_cycle_id, old.stream_id)
       and public._exam_cycle_stream_has_dependents(old.exam_cycle_id, old.stream_id) then
      raise exception 'exam_cycle_streams: cannot move the (cycle=%, stream=%) pair — cycle-bound stream phases depend on it',
        old.exam_cycle_id, old.stream_id using errcode = 'P0422';
    end if;
  end if;

  return new;
end;
$fn$;

drop trigger if exists trg_exam_cycle_streams_check_parent on public.exam_cycle_streams;
create trigger trg_exam_cycle_streams_check_parent
  before insert or update on public.exam_cycle_streams
  for each row execute function public._exam_cycle_streams_check_parent();

-- 5a'. exam_cycle_streams DELETE guard: no FK protects the (cycle, stream)
-- pairing that phases depend on, so block the delete explicitly.
create or replace function public._exam_cycle_streams_guard_delete() returns trigger
language plpgsql as $fn$
begin
  if public._exam_cycle_stream_has_dependents(old.exam_cycle_id, old.stream_id) then
    raise exception 'exam_cycle_streams: cannot delete the (cycle=%, stream=%) pair — cycle-bound stream phases depend on it',
      old.exam_cycle_id, old.stream_id using errcode = 'P0422';
  end if;
  return old;
end;
$fn$;

drop trigger if exists trg_exam_cycle_streams_guard_delete on public.exam_cycle_streams;
create trigger trg_exam_cycle_streams_guard_delete
  before delete on public.exam_cycle_streams
  for each row execute function public._exam_cycle_streams_guard_delete();

-- 5b. exam_phases: a stream-scoped phase must reference a stream of the SAME
-- exam; a cycle-bound phase must reference a cycle of the same exam; and a
-- cycle-bound stream phase requires an offered/expected exam_cycle_streams pair.
create or replace function public._exam_phases_check_stream() returns trigger
language plpgsql as $fn$
declare
  v_stream_exam uuid;
  v_cycle_exam uuid;
begin
  if new.stream_id is not null then
    select exam_id into v_stream_exam from public.exam_streams where id = new.stream_id for share;
    if v_stream_exam is distinct from new.exam_id then
      raise exception 'exam_phases: stream % (exam %) does not belong to phase exam %',
        new.stream_id, v_stream_exam, new.exam_id using errcode = 'P0422';
    end if;
  end if;

  if new.exam_cycle_id is not null then
    select exam_id into v_cycle_exam from public.exam_cycles where id = new.exam_cycle_id for share;
    if v_cycle_exam is distinct from new.exam_id then
      raise exception 'exam_phases: cycle % (exam %) does not belong to phase exam %',
        new.exam_cycle_id, v_cycle_exam, new.exam_id using errcode = 'P0422';
    end if;

    if new.stream_id is not null
       and not public._exam_cycle_stream_available(new.exam_cycle_id, new.stream_id) then
      raise exception 'exam_phases: cycle-bound stream phase requires an offered/expected exam_cycle_streams(cycle=%, stream=%) row',
        new.exam_cycle_id, new.stream_id using errcode = 'P0422';
    end if;
  end if;

  return new;
end;
$fn$;

drop trigger if exists trg_exam_phases_check_stream on public.exam_phases;
create trigger trg_exam_phases_check_stream
  before insert or update on public.exam_phases
  for each row execute function public._exam_phases_check_stream();

-- 5c. exam_phase_sections: a stream-scoped section must reference a stream of
-- the SAME exam as its phase, must not conflict with a stream-specific parent
-- phase (NULL = inherit), and — when the parent phase is cycle-bound — the
-- section's effective stream must itself be offered/expected for that cycle.
create or replace function public._exam_phase_sections_check_stream() returns trigger
language plpgsql as $fn$
declare
  v_phase_exam uuid;
  v_phase_cycle uuid;
  v_phase_stream uuid;
  v_stream_exam uuid;
begin
  if new.stream_id is not null then
    select p.exam_id, p.exam_cycle_id, p.stream_id
      into v_phase_exam, v_phase_cycle, v_phase_stream
    from public.exam_phases p where p.id = new.exam_phase_id for share;

    select exam_id into v_stream_exam from public.exam_streams where id = new.stream_id for share;
    if v_stream_exam is distinct from v_phase_exam then
      raise exception 'exam_phase_sections: stream % (exam %) does not belong to the section phase exam %',
        new.stream_id, v_stream_exam, v_phase_exam using errcode = 'P0422';
    end if;

    if v_phase_stream is not null and new.stream_id <> v_phase_stream then
      raise exception 'exam_phase_sections: section stream % conflicts with stream-specific parent phase stream %',
        new.stream_id, v_phase_stream using errcode = 'P0422';
    end if;

    if v_phase_cycle is not null
       and not public._exam_cycle_stream_available(v_phase_cycle, new.stream_id) then
      raise exception 'exam_phase_sections: stream-scoped section requires an offered/expected exam_cycle_streams(cycle=%, stream=%) row for the phase cycle',
        v_phase_cycle, new.stream_id using errcode = 'P0422';
    end if;
  end if;

  return new;
end;
$fn$;

drop trigger if exists trg_exam_phase_sections_check_stream on public.exam_phase_sections;
create trigger trg_exam_phase_sections_check_stream
  before insert or update on public.exam_phase_sections
  for each row execute function public._exam_phase_sections_check_stream();

-- 5d. exam_topic_coverage: full scope consistency — cycle↔exam, stream↔exam,
-- phase↔exam, section (always resolved through its phase, even when the
-- coverage phase is NULL), stream non-conflict, and cycle-bound availability.
create or replace function public._exam_topic_coverage_check_stream() returns trigger
language plpgsql as $fn$
declare
  v_stream_exam uuid;
  v_cycle_exam uuid;
  v_phase_exam uuid;
  v_phase_cycle uuid;
  v_phase_stream uuid;
  v_sec_phase uuid;
  v_sec_stream uuid;
  v_secphase_exam uuid;
  v_secphase_cycle uuid;
begin
  if new.exam_cycle_id is not null then
    select exam_id into v_cycle_exam from public.exam_cycles where id = new.exam_cycle_id for share;
    if v_cycle_exam is distinct from new.exam_id then
      raise exception 'exam_topic_coverage: cycle % (exam %) does not belong to coverage exam %',
        new.exam_cycle_id, v_cycle_exam, new.exam_id using errcode = 'P0422';
    end if;
  end if;

  if new.stream_id is not null then
    select exam_id into v_stream_exam from public.exam_streams where id = new.stream_id for share;
    if v_stream_exam is distinct from new.exam_id then
      raise exception 'exam_topic_coverage: stream % (exam %) does not belong to coverage exam %',
        new.stream_id, v_stream_exam, new.exam_id using errcode = 'P0422';
    end if;
    -- Cycle-scoped stream coverage must reference an offered/expected pair.
    if new.exam_cycle_id is not null
       and not public._exam_cycle_stream_available(new.exam_cycle_id, new.stream_id) then
      raise exception 'exam_topic_coverage: cycle-scoped stream coverage requires an offered/expected exam_cycle_streams(cycle=%, stream=%) row',
        new.exam_cycle_id, new.stream_id using errcode = 'P0422';
    end if;
  end if;

  if new.exam_phase_id is not null then
    select exam_id, exam_cycle_id, stream_id into v_phase_exam, v_phase_cycle, v_phase_stream
    from public.exam_phases where id = new.exam_phase_id for share;
    if v_phase_exam is distinct from new.exam_id then
      raise exception 'exam_topic_coverage: phase % (exam %) does not belong to coverage exam %',
        new.exam_phase_id, v_phase_exam, new.exam_id using errcode = 'P0422';
    end if;
    if v_phase_cycle is not null and new.exam_cycle_id is not null
       and v_phase_cycle is distinct from new.exam_cycle_id then
      raise exception 'exam_topic_coverage: phase % cycle % does not match coverage cycle %',
        new.exam_phase_id, v_phase_cycle, new.exam_cycle_id using errcode = 'P0422';
    end if;
    if v_phase_stream is not null and new.stream_id is not null and new.stream_id <> v_phase_stream then
      raise exception 'exam_topic_coverage: stream % conflicts with stream-specific phase stream %',
        new.stream_id, v_phase_stream using errcode = 'P0422';
    end if;
  end if;

  -- Section is ALWAYS resolved through its phase to the coverage exam/cycle,
  -- even when new.exam_phase_id IS NULL (the check-bypass the review flagged).
  if new.section_id is not null then
    select exam_phase_id, stream_id into v_sec_phase, v_sec_stream
    from public.exam_phase_sections where id = new.section_id for share;
    select exam_id, exam_cycle_id into v_secphase_exam, v_secphase_cycle
    from public.exam_phases where id = v_sec_phase for share;

    if v_secphase_exam is distinct from new.exam_id then
      raise exception 'exam_topic_coverage: section % (exam %) does not belong to coverage exam %',
        new.section_id, v_secphase_exam, new.exam_id using errcode = 'P0422';
    end if;
    if new.exam_phase_id is not null and v_sec_phase is distinct from new.exam_phase_id then
      raise exception 'exam_topic_coverage: section % does not belong to coverage phase %',
        new.section_id, new.exam_phase_id using errcode = 'P0422';
    end if;
    if new.exam_cycle_id is not null and v_secphase_cycle is not null
       and v_secphase_cycle is distinct from new.exam_cycle_id then
      raise exception 'exam_topic_coverage: section % cycle % does not match coverage cycle %',
        new.section_id, v_secphase_cycle, new.exam_cycle_id using errcode = 'P0422';
    end if;
    if v_sec_stream is not null and new.stream_id is not null and new.stream_id <> v_sec_stream then
      raise exception 'exam_topic_coverage: stream % conflicts with stream-specific section stream %',
        new.stream_id, v_sec_stream using errcode = 'P0422';
    end if;
  end if;

  return new;
end;
$fn$;

drop trigger if exists trg_exam_topic_coverage_check_stream on public.exam_topic_coverage;
create trigger trg_exam_topic_coverage_check_stream
  before insert or update on public.exam_topic_coverage
  for each row execute function public._exam_topic_coverage_check_stream();

-- 5f. Parent-side revalidation: the invariant must survive a parent move.
-- Reassigning an exam_streams / exam_cycles parent to a different exam after
-- dependents already reference it would strand cross-exam rows. FKs cannot
-- express this, so reject the parent move while dependents exist.
create or replace function public._exam_streams_guard_exam_move() returns trigger
language plpgsql as $fn$
begin
  if new.exam_id is distinct from old.exam_id and exists (
      select 1 from public.exam_cycle_streams cs where cs.stream_id = old.id
      union all select 1 from public.exam_phases p where p.stream_id = old.id
      union all select 1 from public.exam_phase_sections s where s.stream_id = old.id
      union all select 1 from public.exam_topic_coverage c where c.stream_id = old.id
  ) then
    raise exception 'exam_streams: cannot reassign stream % to exam % — dependent cycle-streams/phases/sections/coverage exist',
      old.id, new.exam_id using errcode = 'P0422';
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_exam_streams_guard_exam_move on public.exam_streams;
create trigger trg_exam_streams_guard_exam_move
  before update of exam_id on public.exam_streams
  for each row execute function public._exam_streams_guard_exam_move();

create or replace function public._exam_cycles_guard_exam_move() returns trigger
language plpgsql as $fn$
begin
  if new.exam_id is distinct from old.exam_id and exists (
      select 1 from public.exam_cycle_streams cs where cs.exam_cycle_id = old.id
      union all select 1 from public.exam_phases p where p.exam_cycle_id = old.id
      union all select 1 from public.exam_topic_coverage c where c.exam_cycle_id = old.id
  ) then
    raise exception 'exam_cycles: cannot reassign cycle % to exam % — dependent cycle-streams/phases/coverage exist',
      old.id, new.exam_id using errcode = 'P0422';
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_exam_cycles_guard_exam_move on public.exam_cycles;
create trigger trg_exam_cycles_guard_exam_move
  before update of exam_id on public.exam_cycles
  for each row execute function public._exam_cycles_guard_exam_move();

-- ─── 6. RLS ──────────────────────────────────────────────────────────────
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

-- ─── 7. updated_at triggers ──────────────────────────────────────────────
drop trigger if exists exam_streams_updated_at on public.exam_streams;
create trigger exam_streams_updated_at
  before update on public.exam_streams
  for each row execute function public.tg_set_updated_at();

drop trigger if exists exam_cycle_streams_updated_at on public.exam_cycle_streams;
create trigger exam_cycle_streams_updated_at
  before update on public.exam_cycle_streams
  for each row execute function public.tg_set_updated_at();

notify pgrst, 'reload schema';
