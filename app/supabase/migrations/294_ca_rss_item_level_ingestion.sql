-- 294_ca_rss_item_level_ingestion.sql
--
-- CA-RSS-01 — item-level RSS ingestion for current affairs.
--
-- Contract: docs/architecture/current-affairs-pipeline.md §2 (source authority),
-- §3 (evidence model), §4 (ingestion + machine-readable exclusion reasons).
-- Builds on migration 241 (sources + documents) and 247 (generation jobs).
--
-- Applied version must be reconciled against the deployed schema_migrations state
-- at apply time (operator step); 294 = MAX(filesystem)+1 at write time. Confirm
-- with: SELECT MAX(version) FROM schema_migrations; before applying anywhere.
--
-- WHAT THIS DOES
-- --------------
-- A. current_affairs_documents.canonical_item_url — the per-item dedup identity
--    for the RSS item-split ingest, with a PARTIAL unique index on
--    (source_id, canonical_item_url). Partial because every pre-item-split row
--    (and every non-RSS adapter row) leaves it NULL; the index therefore cannot
--    collide with existing data, and app-level link dedup is no longer the only
--    guard against a double snapshot.
-- B. current_affairs_sources.feed_etag / feed_last_modified — feed-level
--    conditional-fetch validators. They used to be read off the source's most
--    recent document row; with one feed fetch now producing MANY item rows (whose
--    etag belongs to the ITEM page), the feed validators need their own home.
-- C. PIB gets a browser User-Agent in adapter_config. The PIB source has 42
--    consecutive http_403 against the default bot UA; a browser UA returns 200.
--    Scoped to the PIB row only — the recruitment scraper's identity is untouched.
-- D. SEBI seeded as a primary_official statutory-regulator RSS source (idempotent).
-- E. Legacy whole-feed document rows retired: before the item split, an RSS pass
--    snapshotted the ENTIRE feed body as one title-less raw-XML document, and
--    re-snapshotted it whenever the feed shifted. Those rows carry no single
--    examinable claim. They are set to ingestion_status='deprioritised' with
--    reason 'legacy_whole_feed' (NOT deleted — documents are immutable evidence),
--    and their pending/running ca_generation jobs are moved to the existing
--    terminal 'failed' status so the worker never runs them.
--
--    EXPECTED SCOPE (verified live 2026-09-21): 22 RBI whole-feed documents and
--    22 pending ca_generation jobs. The predicate is structural (title IS NULL
--    AND the body starts with an XML prolog, optionally BOM-prefixed) rather than
--    a hardcoded id list; the DO block below RAISES NOTICE with the actual counts
--    so the operator can reconcile against that expectation at apply time.
--
-- No LLM, no learner surface, no frontend. Migrations are immutable once merged.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. Per-item dedup identity on document snapshots
-- ═════════════════════════════════════════════════════════════════════════

alter table public.current_affairs_documents
  add column if not exists canonical_item_url text;

comment on column public.current_affairs_documents.canonical_item_url is
  'Canonical link of the RSS feed ENTRY this snapshot came from (scheme/host lowercased, www and fragment dropped, tracking params stripped). NULL for non-RSS adapters and for pre-item-split rows. Dedup identity for the item-split ingest.';

-- Item dedup, enforced by the DB rather than only by app logic: the same feed
-- entry must never produce a second snapshot for the same source. Partial on
-- non-null so legacy/non-RSS rows are unaffected.
create unique index if not exists uq_cad_source_canonical_item
  on public.current_affairs_documents(source_id, canonical_item_url)
  where canonical_item_url is not null;

-- ═════════════════════════════════════════════════════════════════════════
-- B. Feed-level conditional-fetch validators on the SOURCE
-- ═════════════════════════════════════════════════════════════════════════

alter table public.current_affairs_sources
  add column if not exists feed_etag text,
  add column if not exists feed_last_modified text;

comment on column public.current_affairs_sources.feed_etag is
  'ETag of the last FEED fetch (item-split ingest). Distinct from a document row''s etag, which belongs to that item''s own page.';
comment on column public.current_affairs_sources.feed_last_modified is
  'Last-Modified of the last FEED fetch (item-split ingest).';

-- ═════════════════════════════════════════════════════════════════════════
-- C. Per-source User-Agent override for PIB (bot UA ⇒ http_403)
-- ═════════════════════════════════════════════════════════════════════════

update public.current_affairs_sources
set adapter_config = adapter_config || jsonb_build_object(
      'user_agent',
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'),
    updated_at = now()
where adapter_config->>'publisher' = 'PIB'
  and adapter_config->>'user_agent' is null;

-- ═════════════════════════════════════════════════════════════════════════
-- D. SEBI source row (idempotent)
-- ═════════════════════════════════════════════════════════════════════════

insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'Securities and Exchange Board of India', 'primary_official', 'statutory_regulator', 'rss',
       'https://www.sebi.gov.in/', 'https://www.sebi.gov.in/sebirss.xml',
       'economy', 'en',
       '{"publisher": "SEBI"}'::jsonb,
       '{"interval_hours": 24, "priority": "high"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://www.sebi.gov.in/sebirss.xml'
     or adapter_config->>'publisher' = 'SEBI'
);

-- ═════════════════════════════════════════════════════════════════════════
-- E. Retire legacy whole-feed document snapshots + their pending jobs
-- ═════════════════════════════════════════════════════════════════════════
-- Scope predicate (strict): a document with NO title whose body starts with an
-- XML prolog — i.e. a raw feed body, never an item page. ltrim() strips a UTF-8
-- BOM (chr(65279)) and leading whitespace before the comparison.

do $$
declare
  v_docs int;
  v_jobs int;
begin
  create temporary table _legacy_whole_feed_docs on commit drop as
  select d.id
  from public.current_affairs_documents d
  where d.title is null
    and d.raw_text is not null
    and ltrim(d.raw_text, chr(65279) || E' \t\n\r') like '<?xml%';

  update public.current_affairs_documents d
  set ingestion_status = 'deprioritised',
      metadata = coalesce(d.metadata, '{}'::jsonb)
                 || jsonb_build_object('prefilter_reason', 'legacy_whole_feed')
  where d.id in (select id from _legacy_whole_feed_docs)
    and d.ingestion_status is distinct from 'deprioritised';
  get diagnostics v_docs = row_count;

  -- Terminal, non-run status from the EXISTING enum (247 CHECK allows
  -- pending/running/done/failed). 'done' would falsely claim generation output;
  -- 'failed' is the honest terminal state and the worker never claims it.
  update public.current_affairs_generation_jobs j
  set status = 'failed',
      locked_at = null,
      claim_token = null,
      last_error = 'legacy_whole_feed',
      updated_at = now()
  where j.job_kind = 'ca_generation'
    and j.status in ('pending', 'running')
    and j.document_id in (select id from _legacy_whole_feed_docs);
  get diagnostics v_jobs = row_count;

  raise notice 'CA-RSS-01: deprioritised % legacy whole-feed document(s), terminated % pending generation job(s) (expected 22 / 22 as of 2026-09-21)', v_docs, v_jobs;
end $$;

commit;

notify pgrst, 'reload schema';
