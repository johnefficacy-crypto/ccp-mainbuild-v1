-- 241_current_affairs_source_evidence.sql
--
-- GQR-G2 — Current-Affairs source + evidence authority (GA lane).
--
-- Contract: docs/architecture/current-affairs-pipeline.md §2 (source authority),
-- §3 (evidence + event model). ADR 0006 (human gate before automation), ADR 0007
-- (aggregators discovery-only).
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 241 = MAX(filesystem)+1 as of the rebase
-- onto main after 240_ewp_rollup_submitted_at.sql landed. Confirm with:
--   SELECT MAX(version) FROM schema_migrations;
-- before applying to any environment.
--
-- WHAT THIS DOES
-- --------------
-- A. current_affairs_sources — a SEPARATE source authority. It is deliberately
--    NOT source_registry: every active source_registry row is consumed by the
--    recruitment runner (scraping/runner.py), so CA rows there would be dragged
--    into recruitment classify/extract/promote. authority_level maps onto
--    ADR 0007 — a discovery_only source may never be sole evidence.
-- B. current_affairs_documents — immutable evidence snapshots; a changed doc
--    creates a NEW row (supersedes_document_id lineage). Content dedup via a
--    unique (source_id, content_hash).
-- C. current_affairs_events / _claims / _claim_evidence — the event + claim
--    graph with three DISTINCT validity axes kept separate (factual_status vs
--    relevance_until vs bundle availability — the last lands with bundles).
-- D. Wire the mock_question_bank.current_affairs_item_id soft column (migration
--    159 left it FK-less "until the table exists") to current_affairs_events.
--    The column is all-NULL today (no promotion path exists yet), so the FK is
--    free to add now and prevents dangling links once GQR-G4 promotion lands.
-- E. Seed the first two primary_official sources: PIB and RBI.
--
-- Posture: service-role (FastAPI/admin) only. No authenticated/anon policy —
-- there is NO learner-facing UI in this PR (that lands in GQR-G5 on its own
-- CA attempts table). All new tables get RLS per AGENTS.md app-metadata role
-- convention; only service_role is granted DML.
--
-- No LLM, no learner UI, no scheduler wiring in this PR (ca:ingest job lands
-- with GQR-G5 per the pipeline doc §9).
--
-- Migrations are immutable once merged.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. Source authority (separate from source_registry — see header)
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.current_affairs_sources (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  authority_level text not null default 'official_secondary'
    check (authority_level in ('primary_official', 'official_secondary', 'discovery_only')),
  publisher_type text,
  adapter_type text not null default 'html'
    check (adapter_type in ('html', 'rss', 'api', 'pdf', 'sitemap')),
  official_url text,
  crawl_url text,
  rss_url text,
  api_url text,
  pdf_bulletin_url text,
  adapter_config jsonb not null default '{}'::jsonb,
  parser_config jsonb not null default '{}'::jsonb,
  default_category text,
  default_language text not null default 'en',
  -- Config consumed by the ca:ingest job (pipeline §9), NOT an APScheduler cron
  -- by itself. e.g. {"interval_hours": 24, "priority": "high"}.
  crawl_schedule jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  -- Source health (pipeline §4): the ingest job updates these so operators can
  -- triage a silently-failing source. Not authority — purely operational.
  last_fetch_at timestamptz,
  last_success_at timestamptz,
  last_status text,
  consecutive_failures integer not null default 0,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.current_affairs_sources is
  'Current-affairs source authority. SEPARATE from source_registry (which the recruitment runner consumes). authority_level maps onto ADR 0007: discovery_only may never be sole evidence.';
comment on column public.current_affairs_sources.crawl_schedule is
  'Ingest cadence config consumed by the ca:ingest job (pipeline §9); NOT an APScheduler cron.';

-- ═════════════════════════════════════════════════════════════════════════
-- B. Immutable document snapshots
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.current_affairs_documents (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.current_affairs_sources(id) on delete cascade,
  source_url text not null,
  final_url text,
  title text,
  document_type text,
  published_at timestamptz,
  fetched_at timestamptz not null default now(),
  content_hash text,
  etag text,
  last_modified text,
  raw_text text,
  metadata jsonb not null default '{}'::jsonb,
  supersedes_document_id uuid references public.current_affairs_documents(id) on delete set null,
  ingestion_status text not null default 'snapshotted'
    check (ingestion_status in ('snapshotted', 'duplicate', 'superseded', 'rejected', 'deprioritised')),
  created_at timestamptz not null default now()
);

comment on table public.current_affairs_documents is
  'Immutable evidence snapshots. A changed document creates a NEW row (supersedes_document_id lineage); rows are never mutated in place.';

-- Content dedup: the same source publishing byte-identical content twice must
-- collapse to one snapshot. content_hash is nullable (a fetch may 304 before a
-- body), so the unique index is partial on non-null hashes.
create unique index if not exists uq_cad_source_content_hash
  on public.current_affairs_documents(source_id, content_hash)
  where content_hash is not null;
create index if not exists idx_cad_source on public.current_affairs_documents(source_id);
create index if not exists idx_cad_final_url on public.current_affairs_documents(final_url);
create index if not exists idx_cad_ingestion_status on public.current_affairs_documents(ingestion_status);
create index if not exists idx_cad_published_at on public.current_affairs_documents(published_at);

-- ═════════════════════════════════════════════════════════════════════════
-- C. Event + claim graph (three distinct validity axes — do not collapse)
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.current_affairs_events (
  id uuid primary key default gen_random_uuid(),
  canonical_title text not null,
  event_date date,
  category text,
  primary_topic_id uuid references public.topics(id) on delete set null,
  event_fingerprint text unique,
  editorial_importance text not null default 'normal'
    check (editorial_importance in ('low', 'normal', 'high', 'critical')),
  -- relevance_* is the EDITORIAL currency axis (should this event still be
  -- selected for CA practice) — distinct from a claim's factual_status and from
  -- a bundle's available_until.
  relevance_from date,
  relevance_until date,
  status text not null default 'active'
    check (status in ('active', 'superseded', 'demoted', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on column public.current_affairs_events.relevance_until is
  'Editorial currency axis (still selectable for CA practice). Distinct from claim.factual_status and bundle.available_until.';

create index if not exists idx_cae_category on public.current_affairs_events(category);
create index if not exists idx_cae_status on public.current_affairs_events(status);
create index if not exists idx_cae_relevance_until on public.current_affairs_events(relevance_until);
create index if not exists idx_cae_primary_topic on public.current_affairs_events(primary_topic_id);

create table if not exists public.current_affairs_claims (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.current_affairs_events(id) on delete cascade,
  claim_text text not null,
  claim_fingerprint text,
  -- Factual-correctness axis (is the fact still true) — distinct from the
  -- event's editorial relevance window.
  factual_status text not null default 'current'
    check (factual_status in ('current', 'superseded', 'corrected', 'disputed')),
  valid_from timestamptz,
  superseded_at timestamptz,
  superseded_by_claim_id uuid references public.current_affairs_claims(id) on delete set null,
  reviewer_status text not null default 'pending'
    check (reviewer_status in ('pending', 'verified', 'rejected')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_cac_event on public.current_affairs_claims(event_id);
create index if not exists idx_cac_fingerprint on public.current_affairs_claims(claim_fingerprint);
create index if not exists idx_cac_factual_status on public.current_affairs_claims(factual_status);
create index if not exists idx_cac_reviewer_status on public.current_affairs_claims(reviewer_status);

create table if not exists public.current_affairs_claim_evidence (
  id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references public.current_affairs_claims(id) on delete cascade,
  document_id uuid not null references public.current_affairs_documents(id) on delete cascade,
  evidence_text text,
  start_offset integer,
  end_offset integer,
  evidence_role text not null default 'supporting'
    check (evidence_role in ('primary', 'supporting', 'corroborating')),
  created_at timestamptz not null default now(),
  -- Same (claim, document, span) evidence must not be linked twice.
  unique (claim_id, document_id, start_offset, end_offset)
);

create index if not exists idx_cace_claim on public.current_affairs_claim_evidence(claim_id);
create index if not exists idx_cace_document on public.current_affairs_claim_evidence(document_id);

-- ═════════════════════════════════════════════════════════════════════════
-- D. Wire the soft mock_question_bank.current_affairs_item_id FK (migration 159)
-- ═════════════════════════════════════════════════════════════════════════
-- 159 stored current_affairs_item_id as a plain uuid because the target table
-- did not yet exist. It now does. The column is all-NULL today (no promotion
-- path lands until GQR-G4), so adding the FK cannot fail on existing data and
-- keeps future promoted rows from pointing at a non-existent event.
do $$ begin
  alter table public.mock_question_bank
    add constraint mqb_current_affairs_event_fk
      foreign key (current_affairs_item_id)
      references public.current_affairs_events(id) on delete set null;
exception when duplicate_object then null; end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- E. RLS — service-role only (no learner UI in this PR)
-- ═════════════════════════════════════════════════════════════════════════

alter table public.current_affairs_sources        enable row level security;
alter table public.current_affairs_documents      enable row level security;
alter table public.current_affairs_events         enable row level security;
alter table public.current_affairs_claims         enable row level security;
alter table public.current_affairs_claim_evidence enable row level security;

do $$
declare t text;
begin
  foreach t in array array[
    'current_affairs_sources',
    'current_affairs_documents',
    'current_affairs_events',
    'current_affairs_claims',
    'current_affairs_claim_evidence'
  ]
  loop
    execute format('revoke all on public.%I from public', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke all on public.%I from authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
    -- Admin/service-role only. The ingest/generation/review paths run through
    -- FastAPI service-role; there is no direct client read of CA tables until
    -- the learner runtime (GQR-G5) exposes its own frozen attempt surface.
  end loop;
end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- F. Seed the first primary_official sources (PIB, RBI)
-- ═════════════════════════════════════════════════════════════════════════
-- adapter_config carries the fetcher/adapter knobs (pipeline §2); seeded
-- inactive-free so the ingest job can pick them up once GQR-G5 wires ca:ingest.
insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
values
  ('Press Information Bureau', 'primary_official', 'government_pib', 'rss',
   'https://pib.gov.in/', 'https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3',
   'national', 'en',
   '{"publisher": "PIB"}'::jsonb, '{"interval_hours": 12, "priority": "high"}'::jsonb),
  ('Reserve Bank of India', 'primary_official', 'statutory_regulator', 'rss',
   'https://www.rbi.org.in/', 'https://www.rbi.org.in/pressreleases_rss.xml',
   'economy', 'en',
   '{"publisher": "RBI"}'::jsonb, '{"interval_hours": 24, "priority": "high"}'::jsonb)
on conflict do nothing;

commit;
