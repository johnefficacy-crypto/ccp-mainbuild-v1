-- =============================================================================
-- 136_mock_question_workflow.sql
-- Mock Engine PR2: Admin question bank — authoring → review → publish workflow.
--
-- Changes to mock_question_bank:
--   • reviewer_status changed from mock_reviewer_status enum to text (new values)
--   • marks / negative_marks dropped (template-bound, not question-bound)
--   • Cognitive flags, TTL columns, group linkage, fingerprint, audit columns added
--
-- New tables:
--   mock_question_groups       — bilingual pairing registry
--   mock_question_topic_tags   — per-question topic roles
--   mock_question_sources      — provenance evidence
--   mock_question_review_log   — immutable audit trail
--
-- Selector hardening in RLS:
--   Users see only reviewer_status = 'published' AND
--   (valid_until IS NULL OR valid_until > now())
--
-- Backfill:
--   PR1's 20 seeded questions → reviewer_status='published', published_at=created_at,
--   inferred cognitive tags, synthesized fingerprints.
--
-- Idempotent: safe on fresh DB and re-runnable on existing.
-- =============================================================================

-- ── 0. Extensions ─────────────────────────────────────────────────────────────
create extension if not exists pg_trgm;
create extension if not exists pgcrypto;

-- ── 1. mock_question_groups ───────────────────────────────────────────────────
create table if not exists public.mock_question_groups (
  id             uuid primary key default gen_random_uuid(),
  exam_id        uuid references public.exams(id) on delete set null,
  canonical_slug text not null unique,
  created_at     timestamptz not null default now()
);

alter table public.mock_question_groups enable row level security;

drop policy if exists "mqg_admin_all" on public.mock_question_groups;
create policy "mqg_admin_all"
  on public.mock_question_groups for all
  using (true)
  with check (true);

-- ── 2. ALTER mock_question_bank ───────────────────────────────────────────────

-- 2a. Change reviewer_status from enum to text
--     Existing enum values: draft → draft, reviewed → published, locked → published
do $$
begin
  -- Drop default so we can alter the column type freely
  alter table public.mock_question_bank alter column reviewer_status drop default;

  -- Cast enum → text. Postgres allows this via USING.
  alter table public.mock_question_bank
    alter column reviewer_status type text
    using reviewer_status::text;

  -- Backfill old enum values to new status labels
  update public.mock_question_bank
    set reviewer_status = 'published'
    where reviewer_status in ('reviewed', 'locked');

  -- Ensure any stale values get a safe default
  update public.mock_question_bank
    set reviewer_status = 'draft'
    where reviewer_status not in ('draft','in_review','needs_changes','verified','published','archived');

  -- Set new default
  alter table public.mock_question_bank
    alter column reviewer_status set default 'draft';

exception when others then
  -- Column may already be text (re-run scenario); skip
  null;
end $$;

-- Drop the old enum type if it still exists (idempotent)
drop type if exists mock_reviewer_status cascade;

-- 2b. Add check constraint (idempotent guard)
do $$
begin
  alter table public.mock_question_bank
    add constraint mock_question_bank_reviewer_status_check
    check (reviewer_status in ('draft','in_review','needs_changes','verified','published','archived'));
exception when duplicate_object then null;
end $$;

-- 2c. difficulty constraint — update 'difficult' → 'hard', tighten constraint
update public.mock_question_bank set difficulty = 'hard' where difficulty = 'difficult';

do $$
begin
  alter table public.mock_question_bank
    drop constraint if exists mock_question_bank_difficulty_check;
  alter table public.mock_question_bank
    add constraint mock_question_bank_difficulty_check
    check (difficulty in ('easy','medium','hard'));
exception when others then null;
end $$;

-- 2d. Drop marks / negative_marks (template-bound; frozen in question_snapshot)
alter table public.mock_question_bank drop column if exists marks;
alter table public.mock_question_bank drop column if exists negative_marks;

-- 2e. Add new columns (all idempotent)
alter table public.mock_question_bank
  add column if not exists is_conceptual       bool not null default false,
  add column if not exists is_factual          bool not null default false,
  add column if not exists is_current          bool not null default false,
  add column if not exists valid_from          timestamptz,
  add column if not exists valid_until         timestamptz,
  add column if not exists event_anchor_date   date,
  add column if not exists question_group_id   uuid references public.mock_question_groups(id) on delete set null,
  add column if not exists question_fingerprint text,
  add column if not exists created_by          uuid references auth.users(id) on delete set null,
  add column if not exists last_reviewed_by    uuid references auth.users(id) on delete set null,
  add column if not exists last_reviewed_at    timestamptz,
  add column if not exists published_at        timestamptz;

-- ── 3. Fingerprint function + trigger ─────────────────────────────────────────
--
-- Full fingerprint (used by service layer, also computable in SQL):
--   sha256( lower(trim(regexp_replace(question_text,'\s+',' ','g')))
--           || '|' || <sorted option texts>
--           || '|' || <correct option index> )
--
-- The trigger fires BEFORE INSERT OR UPDATE on mock_question_bank.
-- Since options live in a separate table, the trigger computes a
-- partial fingerprint from question_text + correct_option_id only
-- when question_fingerprint is NULL. The service layer always
-- computes and passes the full fingerprint (including options).

create or replace function public.fn_mock_question_fingerprint()
returns trigger language plpgsql as $$
declare
  norm_text text;
  fp        text;
begin
  -- If the service already supplied a fingerprint, honour it.
  if new.question_fingerprint is not null and new.question_fingerprint <> '' then
    return new;
  end if;

  -- Partial fallback: question_text + correct_option_id (options not yet available).
  norm_text := lower(trim(regexp_replace(coalesce(new.question_text,''), '\s+', ' ', 'g')));
  fp := encode(
    sha256((norm_text || '|' || coalesce(new.correct_option_id::text,'') || '|partial')::bytea),
    'hex'
  );
  new.question_fingerprint := fp;
  return new;
end $$;

drop trigger if exists tg_mock_question_fingerprint on public.mock_question_bank;
create trigger tg_mock_question_fingerprint
  before insert or update on public.mock_question_bank
  for each row execute function public.fn_mock_question_fingerprint();

-- Unique constraint on fingerprint (dedup gate)
do $$
begin
  alter table public.mock_question_bank
    add constraint mock_question_bank_fp_uniq unique (question_fingerprint);
exception when duplicate_object then null;
end $$;

-- ── 4. mock_question_topic_tags ───────────────────────────────────────────────
create table if not exists public.mock_question_topic_tags (
  question_id uuid not null references public.mock_question_bank(id) on delete cascade,
  topic_id    uuid not null references public.topics(id) on delete cascade,
  role        text not null check (role in ('primary','secondary','prerequisite','trap','calculation_layer','conceptual_layer')),
  primary key (question_id, topic_id, role)
);

alter table public.mock_question_topic_tags enable row level security;
drop policy if exists "mqtt_admin_all" on public.mock_question_topic_tags;
create policy "mqtt_admin_all" on public.mock_question_topic_tags for all using (true) with check (true);

-- ── 5. mock_question_sources ──────────────────────────────────────────────────
create table if not exists public.mock_question_sources (
  id            uuid primary key default gen_random_uuid(),
  question_id   uuid not null references public.mock_question_bank(id) on delete cascade,
  source_kind   text not null check (source_kind in ('pyq','official_syllabus','standard_source','current_event','authored')),
  source_trust  text not null default 'unverified' check (source_trust in ('verified','provisional','unverified')),
  source_url    text,
  pyq_paper_id  uuid references public.pyq_papers(id) on delete set null,
  pyq_year      int,
  evidence_text text,
  created_at    timestamptz not null default now()
);

alter table public.mock_question_sources enable row level security;
drop policy if exists "mqs_admin_all" on public.mock_question_sources;
create policy "mqs_admin_all" on public.mock_question_sources for all using (true) with check (true);

-- ── 6. mock_question_review_log ───────────────────────────────────────────────
create table if not exists public.mock_question_review_log (
  id           uuid primary key default gen_random_uuid(),
  question_id  uuid not null references public.mock_question_bank(id) on delete cascade,
  actor_id     uuid references auth.users(id) on delete set null,
  from_status  text,
  to_status    text,
  action       text not null check (action in (
    'create','edit','submit','approve','request_changes',
    'publish','archive','restore','force','unauthorized','import'
  )),
  notes        text,
  diff         jsonb,
  at           timestamptz not null default now()
);

alter table public.mock_question_review_log enable row level security;
drop policy if exists "mqrl_admin_all" on public.mock_question_review_log;
create policy "mqrl_admin_all" on public.mock_question_review_log for all using (true) with check (true);

-- ── 7. Indexes ────────────────────────────────────────────────────────────────
create index if not exists idx_mqb_reviewer_status_exam
  on public.mock_question_bank(reviewer_status, exam_id);

create index if not exists idx_mqb_group
  on public.mock_question_bank(question_group_id);

create index if not exists idx_mqb_created_by
  on public.mock_question_bank(created_by);

create index if not exists idx_mqrl_question
  on public.mock_question_review_log(question_id, at desc);

create index if not exists idx_mqrl_actor
  on public.mock_question_review_log(actor_id);

-- GIN trigram index for fuzzy question-text search
create index if not exists idx_mqb_question_text_trgm
  on public.mock_question_bank using gin(question_text gin_trgm_ops);

-- ── 8. RLS: harden user-visible question policy ───────────────────────────────
-- Drop the PR1 policy (reviewed|locked) and replace with published + TTL guard.
drop policy if exists "mock_question_bank_read_reviewed" on public.mock_question_bank;

drop policy if exists "mock_question_bank_read_published" on public.mock_question_bank;
create policy "mock_question_bank_read_published"
  on public.mock_question_bank for select
  using (
    reviewer_status = 'published'
    and (valid_until is null or valid_until > now())
  );

-- Admin (service-role) bypass for all operations (author/reviewer/publisher paths)
drop policy if exists "mock_question_bank_admin_all" on public.mock_question_bank;
create policy "mock_question_bank_admin_all"
  on public.mock_question_bank for all
  using (
    (select (auth.jwt() ->> 'role') in ('service_role'))
    or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
  )
  with check (
    (select (auth.jwt() ->> 'role') in ('service_role'))
    or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
  );

-- ── 9. Backfill PR1's 20 questions ────────────────────────────────────────────
-- They were seeded with reviewer_status='reviewed'/'locked' (now 'published').
-- Set published_at, infer cognitive tags, synthesize full fingerprints.

-- published_at = created_at for all rows without one
update public.mock_question_bank
  set published_at = created_at
  where reviewer_status = 'published'
    and published_at is null;

-- Infer cognitive flags from existing metadata
update public.mock_question_bank
  set
    is_factual    = true,
    is_conceptual = (difficulty in ('medium','hard'))
  where reviewer_status = 'published'
    and is_factual = false
    and is_conceptual = false
    and is_current = false;

-- Synthesize full fingerprints using options (run after options are available)
-- For each question without a fingerprint, compute from question_text + sorted options.
do $$
declare
  rec record;
  norm_text  text;
  opts_text  text;
  correct_idx int;
  fp         text;
begin
  for rec in
    select q.id, q.question_text, q.correct_option_id
    from public.mock_question_bank q
    where q.question_fingerprint is null or q.question_fingerprint like '%partial%'
  loop
    norm_text := lower(trim(regexp_replace(coalesce(rec.question_text,''), '\s+', ' ', 'g')));

    -- Sorted option texts
    select string_agg(o.option_text, '|' order by o.option_text)
    into opts_text
    from public.mock_question_options o
    where o.question_id = rec.id;

    -- Correct option index
    select o.option_index
    into correct_idx
    from public.mock_question_options o
    where o.id = rec.correct_option_id
    limit 1;

    fp := encode(
      sha256((
        norm_text || '|'
        || coalesce(opts_text, '') || '|'
        || coalesce(correct_idx::text, '')
      )::bytea),
      'hex'
    );

    update public.mock_question_bank
      set question_fingerprint = fp
      where id = rec.id;
  end loop;
end $$;
