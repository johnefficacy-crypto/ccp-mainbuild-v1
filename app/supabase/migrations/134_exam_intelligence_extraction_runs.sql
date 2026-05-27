-- 134_exam_intelligence_extraction_runs.sql
-- Exam Intelligence Extraction v1: provenance layer.
--
-- Adds:
--   1. public.extraction_runs  -- audit log for extractor runs (admin/service only).
--   2. source_kind column      -- on 7 existing CMS tables: tracks how each row
--                                 was created (manual, bulk_import, auto_extracted).
--   3. Provenance columns      -- source_document_id, source_page, source_regions,
--                                 extraction_run_id, extractor_version,
--                                 idempotency_key, content_hash, confidence_by_field.
--
-- Target tables for (2) and (3):
--   pyq_questions, pyq_options, pyq_question_topic_tags, syllabus_topic_mentions,
--   exam_topic_coverage, exam_policy_updates, exam_competition_metrics.
--
-- All new columns on existing tables are NULLABLE with defaults that cannot
-- break current INSERT statements. No router, service, or model code is wired
-- here. Safe to roll back: see DOWN MIGRATION comment at the bottom.
--
-- Verified against repo before writing:
--   * document_assets.id                    -> migration 111
--   * pyq_questions, pyq_options,
--     pyq_question_topic_tags               -> migration 032
--   * syllabus_topic_mentions               -> migration 031
--   * exam_topic_coverage                   -> migration 029
--   * exam_policy_updates                   -> migration 056
--   * exam_competition_metrics              -> migration 055
--   * RLS for above tables (admin_all loop) -> migrations 035, 057

-- ── 1. extraction_runs ───────────────────────────────────────────────────────

create table if not exists public.extraction_runs (
  id                uuid         primary key default gen_random_uuid(),
  document_id       uuid         not null references public.document_assets(id) on delete cascade,
  extractor_name    text         not null,
  extractor_version text         not null,
  model_version     text,
  prompt_version    text,
  status            text         not null default 'running'
    check (status in ('running', 'completed', 'failed', 'killed')),
  started_at        timestamptz  not null default now(),
  completed_at      timestamptz,
  killed_at         timestamptz,
  killed_by         uuid         references auth.users(id) on delete set null,
  killed_reason     text,
  input_hash        text,
  row_count         int          not null default 0 check (row_count >= 0),
  error_count       int          not null default 0 check (error_count >= 0),
  confidence_p50    numeric(4,3) check (confidence_p50 is null or (confidence_p50 >= 0 and confidence_p50 <= 1)),
  confidence_p90    numeric(4,3) check (confidence_p90 is null or (confidence_p90 >= 0 and confidence_p90 <= 1)),
  error_log         jsonb,
  metadata          jsonb        not null default '{}'::jsonb,
  created_at        timestamptz  not null default now()
);

comment on column public.extraction_runs.document_id       is 'Source document this run extracted from.';
comment on column public.extraction_runs.extractor_name    is 'Logical name of the extractor, e.g. upsc_pyq_question_extractor.';
comment on column public.extraction_runs.extractor_version is 'Semver of the extractor code, e.g. 1.0.0.';
comment on column public.extraction_runs.model_version     is 'Model identifier used, e.g. claude-3-5-sonnet-20241022. NULL for rule-based extractors.';
comment on column public.extraction_runs.prompt_version    is 'Hash or tag of the prompt template. NULL for rule-based extractors.';
comment on column public.extraction_runs.status            is 'Run lifecycle: running -> completed | failed | killed.';
comment on column public.extraction_runs.started_at        is 'Wall-clock start of the run.';
comment on column public.extraction_runs.completed_at      is 'Set when status transitions to completed or failed.';
comment on column public.extraction_runs.killed_at         is 'Set when an admin manually kills the run.';
comment on column public.extraction_runs.killed_by         is 'Admin user who killed the run.';
comment on column public.extraction_runs.killed_reason     is 'Free-text reason for the kill.';
comment on column public.extraction_runs.input_hash        is 'SHA-256 of the serialized input payload, for dedup detection.';
comment on column public.extraction_runs.row_count         is 'Count of rows successfully written by this run.';
comment on column public.extraction_runs.error_count       is 'Count of rows that failed or were skipped due to errors.';
comment on column public.extraction_runs.confidence_p50    is 'Median confidence across extracted rows [0..1].';
comment on column public.extraction_runs.confidence_p90    is '90th-percentile confidence across extracted rows [0..1].';
comment on column public.extraction_runs.error_log         is 'Structured error details keyed by question number or region.';
comment on column public.extraction_runs.metadata          is 'Free-form run metadata (flags, timing breakdown, etc.).';

create index if not exists idx_extraction_runs_document
  on public.extraction_runs(document_id, started_at desc);
create index if not exists idx_extraction_runs_status
  on public.extraction_runs(status, started_at desc);

alter table public.extraction_runs enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'extraction_runs'
      and policyname = 'extraction_runs_admin_all'
  ) then
    create policy extraction_runs_admin_all on public.extraction_runs
      for all to authenticated
      using (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true))
      with check (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true));
  end if;

  -- Service role (extractor backend) bypasses RLS for writes.
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'extraction_runs'
      and policyname = 'extraction_runs_service_role_all'
  ) then
    create policy extraction_runs_service_role_all on public.extraction_runs
      for all to service_role using (true) with check (true);
  end if;
end $$;

-- ── 2. source_kind column on 7 CMS tables ────────────────────────────────────
-- Nullable with default 'manual' so all existing INSERT statements are unaffected.
-- CHECK allows NULL because the planner already filters on reviewer_status.

alter table public.pyq_questions
  add column if not exists source_kind text default 'manual'
    check (source_kind in ('manual', 'bulk_import', 'auto_extracted'));
alter table public.pyq_options
  add column if not exists source_kind text default 'manual'
    check (source_kind in ('manual', 'bulk_import', 'auto_extracted'));
alter table public.pyq_question_topic_tags
  add column if not exists source_kind text default 'manual'
    check (source_kind in ('manual', 'bulk_import', 'auto_extracted'));
alter table public.syllabus_topic_mentions
  add column if not exists source_kind text default 'manual'
    check (source_kind in ('manual', 'bulk_import', 'auto_extracted'));
alter table public.exam_topic_coverage
  add column if not exists source_kind text default 'manual'
    check (source_kind in ('manual', 'bulk_import', 'auto_extracted'));
alter table public.exam_policy_updates
  add column if not exists source_kind text default 'manual'
    check (source_kind in ('manual', 'bulk_import', 'auto_extracted'));
alter table public.exam_competition_metrics
  add column if not exists source_kind text default 'manual'
    check (source_kind in ('manual', 'bulk_import', 'auto_extracted'));

-- Backfill: PG 11+ ADD COLUMN ... DEFAULT already fills existing rows, but
-- this explicit UPDATE covers any rows that somehow arrive as NULL (e.g.
-- via direct-SQL inserts before this migration on a live DB).
update public.pyq_questions            set source_kind = 'manual' where source_kind is null;
update public.pyq_options              set source_kind = 'manual' where source_kind is null;
update public.pyq_question_topic_tags  set source_kind = 'manual' where source_kind is null;
update public.syllabus_topic_mentions  set source_kind = 'manual' where source_kind is null;
update public.exam_topic_coverage      set source_kind = 'manual' where source_kind is null;
update public.exam_policy_updates      set source_kind = 'manual' where source_kind is null;
update public.exam_competition_metrics set source_kind = 'manual' where source_kind is null;

comment on column public.pyq_questions.source_kind            is 'How this row was created: manual CMS entry, bulk import, or auto-extracted by an extractor run.';
comment on column public.pyq_options.source_kind              is 'How this row was created: manual CMS entry, bulk import, or auto-extracted by an extractor run.';
comment on column public.pyq_question_topic_tags.source_kind  is 'How this row was created: manual CMS entry, bulk import, or auto-extracted by an extractor run.';
comment on column public.syllabus_topic_mentions.source_kind  is 'How this row was created: manual CMS entry, bulk import, or auto-extracted by an extractor run.';
comment on column public.exam_topic_coverage.source_kind      is 'How this row was created: manual CMS entry, bulk import, or auto-extracted by an extractor run.';
comment on column public.exam_policy_updates.source_kind      is 'How this row was created: manual CMS entry, bulk import, or auto-extracted by an extractor run.';
comment on column public.exam_competition_metrics.source_kind is 'How this row was created: manual CMS entry, bulk import, or auto-extracted by an extractor run.';

create index if not exists idx_pyq_questions_source_kind
  on public.pyq_questions(source_kind);
create index if not exists idx_pyq_options_source_kind
  on public.pyq_options(source_kind);
create index if not exists idx_pyq_question_topic_tags_source_kind
  on public.pyq_question_topic_tags(source_kind);
create index if not exists idx_syllabus_topic_mentions_source_kind
  on public.syllabus_topic_mentions(source_kind);
create index if not exists idx_exam_topic_coverage_source_kind
  on public.exam_topic_coverage(source_kind);
create index if not exists idx_exam_policy_updates_source_kind
  on public.exam_policy_updates(source_kind);
create index if not exists idx_exam_competition_metrics_source_kind
  on public.exam_competition_metrics(source_kind);

-- ── 3. Provenance columns on same 7 tables ───────────────────────────────────
-- All columns are nullable so no existing INSERT is broken.

-- pyq_questions ---------------------------------------------------------------
alter table public.pyq_questions
  add column if not exists source_document_id  uuid references public.document_assets(id) on delete set null,
  add column if not exists source_page          int,
  add column if not exists source_regions       jsonb,
  add column if not exists extraction_run_id    uuid references public.extraction_runs(id) on delete set null,
  add column if not exists extractor_version    text,
  add column if not exists idempotency_key      text,
  add column if not exists content_hash         text,
  add column if not exists confidence_by_field  jsonb;

comment on column public.pyq_questions.source_document_id  is 'FK to document_assets: PDF this question was extracted from.';
comment on column public.pyq_questions.source_page         is 'Page number (1-indexed) in the source PDF where the question appears.';
comment on column public.pyq_questions.source_regions      is 'Normalized bbox array [[xmin,ymin,xmax,ymax],...] within source_page, top-left origin [0..1].';
comment on column public.pyq_questions.extraction_run_id   is 'FK to extraction_runs: the run that produced this row. NULL for manual rows.';
comment on column public.pyq_questions.extractor_version   is 'Extractor semver at time of extraction. NULL for manual rows.';
comment on column public.pyq_questions.idempotency_key     is 'sha256(document_id||page||regions_hash||extractor_version). NULL for manual rows.';
comment on column public.pyq_questions.content_hash        is 'sha256(normalize(question_text)); stable content fingerprint across re-runs.';
comment on column public.pyq_questions.confidence_by_field is 'Per-field extractor confidence, e.g. {"question_text": 0.95, "question_number": 1.0}.';

-- pyq_options -----------------------------------------------------------------
alter table public.pyq_options
  add column if not exists source_document_id  uuid references public.document_assets(id) on delete set null,
  add column if not exists source_page          int,
  add column if not exists source_regions       jsonb,
  add column if not exists extraction_run_id    uuid references public.extraction_runs(id) on delete set null,
  add column if not exists extractor_version    text,
  add column if not exists idempotency_key      text,
  add column if not exists content_hash         text,
  add column if not exists confidence_by_field  jsonb;

comment on column public.pyq_options.source_document_id  is 'FK to document_assets: PDF this option was extracted from.';
comment on column public.pyq_options.source_page         is 'Page number (1-indexed) in the source PDF where the option appears.';
comment on column public.pyq_options.source_regions      is 'Normalized bbox array [[xmin,ymin,xmax,ymax],...] within source_page, top-left origin [0..1].';
comment on column public.pyq_options.extraction_run_id   is 'FK to extraction_runs: the run that produced this row. NULL for manual rows.';
comment on column public.pyq_options.extractor_version   is 'Extractor semver at time of extraction. NULL for manual rows.';
comment on column public.pyq_options.idempotency_key     is 'sha256(document_id||page||regions_hash||extractor_version). NULL for manual rows.';
comment on column public.pyq_options.content_hash        is 'sha256(normalize(option_text)); stable content fingerprint across re-runs.';
comment on column public.pyq_options.confidence_by_field is 'Per-field extractor confidence, e.g. {"option_text": 0.92}.';

-- pyq_question_topic_tags -----------------------------------------------------
alter table public.pyq_question_topic_tags
  add column if not exists source_document_id  uuid references public.document_assets(id) on delete set null,
  add column if not exists source_page          int,
  add column if not exists source_regions       jsonb,
  add column if not exists extraction_run_id    uuid references public.extraction_runs(id) on delete set null,
  add column if not exists extractor_version    text,
  add column if not exists idempotency_key      text,
  add column if not exists content_hash         text,
  add column if not exists confidence_by_field  jsonb;

comment on column public.pyq_question_topic_tags.source_document_id  is 'FK to document_assets: source PDF.';
comment on column public.pyq_question_topic_tags.source_page         is 'Page number in source PDF.';
comment on column public.pyq_question_topic_tags.source_regions      is 'Normalized bbox array within source_page.';
comment on column public.pyq_question_topic_tags.extraction_run_id   is 'FK to extraction_runs. NULL for manual rows.';
comment on column public.pyq_question_topic_tags.extractor_version   is 'Extractor semver. NULL for manual rows.';
comment on column public.pyq_question_topic_tags.idempotency_key     is 'sha256(document_id||page||regions_hash||extractor_version). NULL for manual rows.';
comment on column public.pyq_question_topic_tags.content_hash        is 'Stable hash of the tag key for dedup.';
comment on column public.pyq_question_topic_tags.confidence_by_field is 'Per-field extractor confidence scores.';

-- syllabus_topic_mentions -----------------------------------------------------
alter table public.syllabus_topic_mentions
  add column if not exists source_document_id  uuid references public.document_assets(id) on delete set null,
  add column if not exists source_page          int,
  add column if not exists source_regions       jsonb,
  add column if not exists extraction_run_id    uuid references public.extraction_runs(id) on delete set null,
  add column if not exists extractor_version    text,
  add column if not exists idempotency_key      text,
  add column if not exists content_hash         text,
  add column if not exists confidence_by_field  jsonb;

comment on column public.syllabus_topic_mentions.source_document_id  is 'FK to document_assets: syllabus PDF this mention was extracted from.';
comment on column public.syllabus_topic_mentions.source_page         is 'Page number in source PDF.';
comment on column public.syllabus_topic_mentions.source_regions      is 'Normalized bbox array within source_page.';
comment on column public.syllabus_topic_mentions.extraction_run_id   is 'FK to extraction_runs. NULL for manual rows.';
comment on column public.syllabus_topic_mentions.extractor_version   is 'Extractor semver. NULL for manual rows.';
comment on column public.syllabus_topic_mentions.idempotency_key     is 'sha256(document_id||page||regions_hash||extractor_version). NULL for manual rows.';
comment on column public.syllabus_topic_mentions.content_hash        is 'Stable hash of the mention text.';
comment on column public.syllabus_topic_mentions.confidence_by_field is 'Per-field extractor confidence scores.';

-- exam_topic_coverage ---------------------------------------------------------
alter table public.exam_topic_coverage
  add column if not exists source_document_id  uuid references public.document_assets(id) on delete set null,
  add column if not exists source_page          int,
  add column if not exists source_regions       jsonb,
  add column if not exists extraction_run_id    uuid references public.extraction_runs(id) on delete set null,
  add column if not exists extractor_version    text,
  add column if not exists idempotency_key      text,
  add column if not exists content_hash         text,
  add column if not exists confidence_by_field  jsonb;

comment on column public.exam_topic_coverage.source_document_id  is 'FK to document_assets: source PDF.';
comment on column public.exam_topic_coverage.source_page         is 'Page number in source PDF.';
comment on column public.exam_topic_coverage.source_regions      is 'Normalized bbox array within source_page.';
comment on column public.exam_topic_coverage.extraction_run_id   is 'FK to extraction_runs. NULL for manual rows.';
comment on column public.exam_topic_coverage.extractor_version   is 'Extractor semver. NULL for manual rows.';
comment on column public.exam_topic_coverage.idempotency_key     is 'sha256(document_id||page||regions_hash||extractor_version). NULL for manual rows.';
comment on column public.exam_topic_coverage.content_hash        is 'Stable hash of the coverage key.';
comment on column public.exam_topic_coverage.confidence_by_field is 'Per-field extractor confidence scores.';

-- exam_policy_updates ---------------------------------------------------------
alter table public.exam_policy_updates
  add column if not exists source_document_id  uuid references public.document_assets(id) on delete set null,
  add column if not exists source_page          int,
  add column if not exists source_regions       jsonb,
  add column if not exists extraction_run_id    uuid references public.extraction_runs(id) on delete set null,
  add column if not exists extractor_version    text,
  add column if not exists idempotency_key      text,
  add column if not exists content_hash         text,
  add column if not exists confidence_by_field  jsonb;

comment on column public.exam_policy_updates.source_document_id  is 'FK to document_assets: notification PDF this update was extracted from.';
comment on column public.exam_policy_updates.source_page         is 'Page number in source PDF.';
comment on column public.exam_policy_updates.source_regions      is 'Normalized bbox array within source_page.';
comment on column public.exam_policy_updates.extraction_run_id   is 'FK to extraction_runs. NULL for manual rows.';
comment on column public.exam_policy_updates.extractor_version   is 'Extractor semver. NULL for manual rows.';
comment on column public.exam_policy_updates.idempotency_key     is 'sha256(document_id||page||regions_hash||extractor_version). NULL for manual rows.';
comment on column public.exam_policy_updates.content_hash        is 'Stable hash of the policy update content.';
comment on column public.exam_policy_updates.confidence_by_field is 'Per-field extractor confidence scores.';

-- exam_competition_metrics ----------------------------------------------------
alter table public.exam_competition_metrics
  add column if not exists source_document_id  uuid references public.document_assets(id) on delete set null,
  add column if not exists source_page          int,
  add column if not exists source_regions       jsonb,
  add column if not exists extraction_run_id    uuid references public.extraction_runs(id) on delete set null,
  add column if not exists extractor_version    text,
  add column if not exists idempotency_key      text,
  add column if not exists content_hash         text,
  add column if not exists confidence_by_field  jsonb;

comment on column public.exam_competition_metrics.source_document_id  is 'FK to document_assets: source PDF.';
comment on column public.exam_competition_metrics.source_page         is 'Page number in source PDF.';
comment on column public.exam_competition_metrics.source_regions      is 'Normalized bbox array within source_page.';
comment on column public.exam_competition_metrics.extraction_run_id   is 'FK to extraction_runs. NULL for manual rows.';
comment on column public.exam_competition_metrics.extractor_version   is 'Extractor semver. NULL for manual rows.';
comment on column public.exam_competition_metrics.idempotency_key     is 'sha256(document_id||page||regions_hash||extractor_version). NULL for manual rows.';
comment on column public.exam_competition_metrics.content_hash        is 'Stable hash of the metrics key.';
comment on column public.exam_competition_metrics.confidence_by_field is 'Per-field extractor confidence scores.';

-- ── 4. Indexes on provenance columns ─────────────────────────────────────────

-- extraction_run_id (partial: only rows with a run, for joins)
create index if not exists idx_pyq_questions_extraction_run
  on public.pyq_questions(extraction_run_id) where extraction_run_id is not null;
create index if not exists idx_pyq_options_extraction_run
  on public.pyq_options(extraction_run_id) where extraction_run_id is not null;
create index if not exists idx_pyq_question_topic_tags_extraction_run
  on public.pyq_question_topic_tags(extraction_run_id) where extraction_run_id is not null;
create index if not exists idx_syllabus_topic_mentions_extraction_run
  on public.syllabus_topic_mentions(extraction_run_id) where extraction_run_id is not null;
create index if not exists idx_exam_topic_coverage_extraction_run
  on public.exam_topic_coverage(extraction_run_id) where extraction_run_id is not null;
create index if not exists idx_exam_policy_updates_extraction_run
  on public.exam_policy_updates(extraction_run_id) where extraction_run_id is not null;
create index if not exists idx_exam_competition_metrics_extraction_run
  on public.exam_competition_metrics(extraction_run_id) where extraction_run_id is not null;

-- content_hash (partial: only extracted rows carry a hash)
create index if not exists idx_pyq_questions_content_hash
  on public.pyq_questions(content_hash) where content_hash is not null;
create index if not exists idx_pyq_options_content_hash
  on public.pyq_options(content_hash) where content_hash is not null;
create index if not exists idx_pyq_question_topic_tags_content_hash
  on public.pyq_question_topic_tags(content_hash) where content_hash is not null;
create index if not exists idx_syllabus_topic_mentions_content_hash
  on public.syllabus_topic_mentions(content_hash) where content_hash is not null;
create index if not exists idx_exam_topic_coverage_content_hash
  on public.exam_topic_coverage(content_hash) where content_hash is not null;
create index if not exists idx_exam_policy_updates_content_hash
  on public.exam_policy_updates(content_hash) where content_hash is not null;
create index if not exists idx_exam_competition_metrics_content_hash
  on public.exam_competition_metrics(content_hash) where content_hash is not null;

-- idempotency_key (unique partial: enforces no double-write from the same run)
create unique index if not exists uq_pyq_questions_idempotency_key
  on public.pyq_questions(idempotency_key) where idempotency_key is not null;
create unique index if not exists uq_pyq_options_idempotency_key
  on public.pyq_options(idempotency_key) where idempotency_key is not null;
create unique index if not exists uq_pyq_question_topic_tags_idempotency_key
  on public.pyq_question_topic_tags(idempotency_key) where idempotency_key is not null;
create unique index if not exists uq_syllabus_topic_mentions_idempotency_key
  on public.syllabus_topic_mentions(idempotency_key) where idempotency_key is not null;
create unique index if not exists uq_exam_topic_coverage_idempotency_key
  on public.exam_topic_coverage(idempotency_key) where idempotency_key is not null;
create unique index if not exists uq_exam_policy_updates_idempotency_key
  on public.exam_policy_updates(idempotency_key) where idempotency_key is not null;
create unique index if not exists uq_exam_competition_metrics_idempotency_key
  on public.exam_competition_metrics(idempotency_key) where idempotency_key is not null;

notify pgrst, 'reload schema';

-- ── DOWN MIGRATION ────────────────────────────────────────────────────────────
-- To roll back, run the following SQL in order.
--
-- Step 1: unique partial indexes on idempotency_key
-- drop index if exists public.uq_pyq_questions_idempotency_key;
-- drop index if exists public.uq_pyq_options_idempotency_key;
-- drop index if exists public.uq_pyq_question_topic_tags_idempotency_key;
-- drop index if exists public.uq_syllabus_topic_mentions_idempotency_key;
-- drop index if exists public.uq_exam_topic_coverage_idempotency_key;
-- drop index if exists public.uq_exam_policy_updates_idempotency_key;
-- drop index if exists public.uq_exam_competition_metrics_idempotency_key;
--
-- Step 2: content_hash indexes
-- drop index if exists public.idx_pyq_questions_content_hash;
-- drop index if exists public.idx_pyq_options_content_hash;
-- drop index if exists public.idx_pyq_question_topic_tags_content_hash;
-- drop index if exists public.idx_syllabus_topic_mentions_content_hash;
-- drop index if exists public.idx_exam_topic_coverage_content_hash;
-- drop index if exists public.idx_exam_policy_updates_content_hash;
-- drop index if exists public.idx_exam_competition_metrics_content_hash;
--
-- Step 3: extraction_run_id indexes
-- drop index if exists public.idx_pyq_questions_extraction_run;
-- drop index if exists public.idx_pyq_options_extraction_run;
-- drop index if exists public.idx_pyq_question_topic_tags_extraction_run;
-- drop index if exists public.idx_syllabus_topic_mentions_extraction_run;
-- drop index if exists public.idx_exam_topic_coverage_extraction_run;
-- drop index if exists public.idx_exam_policy_updates_extraction_run;
-- drop index if exists public.idx_exam_competition_metrics_extraction_run;
--
-- Step 4: source_kind indexes
-- drop index if exists public.idx_pyq_questions_source_kind;
-- drop index if exists public.idx_pyq_options_source_kind;
-- drop index if exists public.idx_pyq_question_topic_tags_source_kind;
-- drop index if exists public.idx_syllabus_topic_mentions_source_kind;
-- drop index if exists public.idx_exam_topic_coverage_source_kind;
-- drop index if exists public.idx_exam_policy_updates_source_kind;
-- drop index if exists public.idx_exam_competition_metrics_source_kind;
--
-- Step 5: extraction_runs table indexes
-- drop index if exists public.idx_extraction_runs_document;
-- drop index if exists public.idx_extraction_runs_status;
--
-- Step 6: provenance columns and source_kind from existing tables
-- (FK columns referencing extraction_runs must be dropped before step 7)
-- alter table public.pyq_questions            drop column if exists source_document_id, drop column if exists source_page, drop column if exists source_regions, drop column if exists extraction_run_id, drop column if exists extractor_version, drop column if exists idempotency_key, drop column if exists content_hash, drop column if exists confidence_by_field, drop column if exists source_kind;
-- alter table public.pyq_options              drop column if exists source_document_id, drop column if exists source_page, drop column if exists source_regions, drop column if exists extraction_run_id, drop column if exists extractor_version, drop column if exists idempotency_key, drop column if exists content_hash, drop column if exists confidence_by_field, drop column if exists source_kind;
-- alter table public.pyq_question_topic_tags  drop column if exists source_document_id, drop column if exists source_page, drop column if exists source_regions, drop column if exists extraction_run_id, drop column if exists extractor_version, drop column if exists idempotency_key, drop column if exists content_hash, drop column if exists confidence_by_field, drop column if exists source_kind;
-- alter table public.syllabus_topic_mentions  drop column if exists source_document_id, drop column if exists source_page, drop column if exists source_regions, drop column if exists extraction_run_id, drop column if exists extractor_version, drop column if exists idempotency_key, drop column if exists content_hash, drop column if exists confidence_by_field, drop column if exists source_kind;
-- alter table public.exam_topic_coverage      drop column if exists source_document_id, drop column if exists source_page, drop column if exists source_regions, drop column if exists extraction_run_id, drop column if exists extractor_version, drop column if exists idempotency_key, drop column if exists content_hash, drop column if exists confidence_by_field, drop column if exists source_kind;
-- alter table public.exam_policy_updates      drop column if exists source_document_id, drop column if exists source_page, drop column if exists source_regions, drop column if exists extraction_run_id, drop column if exists extractor_version, drop column if exists idempotency_key, drop column if exists content_hash, drop column if exists confidence_by_field, drop column if exists source_kind;
-- alter table public.exam_competition_metrics drop column if exists source_document_id, drop column if exists source_page, drop column if exists source_regions, drop column if exists extraction_run_id, drop column if exists extractor_version, drop column if exists idempotency_key, drop column if exists content_hash, drop column if exists confidence_by_field, drop column if exists source_kind;
--
-- Step 7: extraction_runs table
-- drop table if exists public.extraction_runs;
