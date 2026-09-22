-- 297_ca_rss03_language_follow_and_wave1_sources.sql
--
-- CA-RSS-03 — PIB English-version follow, discovery_only enforcement, wave-1
-- current-affairs sources.
--
-- Contract: docs/architecture/current-affairs-pipeline.md §2 (source authority),
-- §4 (ingestion). ADR 0007 (aggregators / news media are discovery-only).
-- Builds on 241 (sources + documents), 294 (item-split ingest) and 296.
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 297 = MAX(filesystem)+1 at write time.
-- Confirm with: SELECT MAX(version) FROM schema_migrations; before applying.
--
-- WHAT THIS DOES
-- --------------
-- A. ingestion_status gains 'discovery_only'. A discovery_only source's feed
--    entry is stored as title + link + feed summary (raw_text NULL) under this
--    status. It is neither 'snapshotted' (the only status the ingest pass
--    enqueues for generation) nor 'deprioritised' (which means "fetched, then
--    filtered out") — it was never evidence to begin with.
-- B. Expression index on (source_id, metadata->>'source_url_hi'). A PIB row
--    stores the ENGLISH release, so its canonical_item_url is the English URL;
--    the Hindi feed link it was resolved from is kept in metadata.source_url_hi
--    and is what the next pass looks up to skip that feed item WITHOUT a fetch.
--    No new table: the document row already is the resolution record, and a
--    side table would be a second source of truth for the same fact.
-- C. Wave-1 sources (idempotent, WHERE NOT EXISTS on rss_url):
--      RBI Notifications, RBI Speeches   — primary_official statutory_regulator
--      UNESCO World Heritage Centre      — primary_official international_body
--      The Hindu (national)              — discovery_only news_media
--    The RBI rows share adapter_config.publisher='RBI' with the 241 press-release
--    row; they are told apart by adapter_config.feed. Nothing in the ingest keys
--    a single source on the publisher marker — every lookup is by source_id.
--
-- No LLM, no learner surface, no frontend. Migrations are immutable once merged.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. 'discovery_only' ingestion status
-- ═════════════════════════════════════════════════════════════════════════
-- 241 declared the CHECK inline, so its name is Postgres-generated. Drop every
-- CHECK on the table that constrains ingestion_status, then add a named one.

do $$
declare
  v_name text;
begin
  for v_name in
    select c.conname
    from pg_constraint c
    where c.conrelid = 'public.current_affairs_documents'::regclass
      and c.contype = 'c'
      and pg_get_constraintdef(c.oid) ilike '%ingestion_status%'
  loop
    execute format('alter table public.current_affairs_documents drop constraint %I', v_name);
  end loop;
end $$;

alter table public.current_affairs_documents
  add constraint current_affairs_documents_ingestion_status_check
  check (ingestion_status in
    ('snapshotted', 'duplicate', 'superseded', 'rejected', 'deprioritised', 'discovery_only'));

-- ═════════════════════════════════════════════════════════════════════════
-- B. Resolved-feed-link lookup for language-follow publishers (PIB)
-- ═════════════════════════════════════════════════════════════════════════

create index if not exists idx_cad_source_url_hi
  on public.current_affairs_documents (source_id, (metadata->>'source_url_hi'));

comment on index public.idx_cad_source_url_hi is
  'CA-RSS-03: PIB rows store the English release; metadata.source_url_hi is the Hindi feed link it was resolved from. The ingest skips an already-resolved feed item by this key without fetching.';

-- ═════════════════════════════════════════════════════════════════════════
-- C. Wave-1 sources
-- ═════════════════════════════════════════════════════════════════════════

insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'Reserve Bank of India — Notifications', 'primary_official', 'statutory_regulator', 'rss',
       'https://www.rbi.org.in/', 'https://www.rbi.org.in/notifications_rss.xml',
       'economy', 'en',
       '{"publisher": "RBI", "feed": "notifications"}'::jsonb,
       '{"interval_hours": 24, "priority": "high"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://www.rbi.org.in/notifications_rss.xml'
);

insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'Reserve Bank of India — Speeches', 'primary_official', 'statutory_regulator', 'rss',
       'https://www.rbi.org.in/', 'https://www.rbi.org.in/speeches_rss.xml',
       'economy', 'en',
       '{"publisher": "RBI", "feed": "speeches"}'::jsonb,
       '{"interval_hours": 48, "priority": "high"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://www.rbi.org.in/speeches_rss.xml'
);

insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'UNESCO World Heritage Centre', 'primary_official', 'international_body', 'rss',
       'https://whc.unesco.org/', 'https://whc.unesco.org/en/news/rss/',
       'culture', 'en',
       '{"publisher": "UNESCO_WHC"}'::jsonb,
       '{"interval_hours": 48, "priority": "normal"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://whc.unesco.org/en/news/rss/'
);

-- ADR 0007: news media is discovery-only — title + link + feed summary, never
-- article text, never a generation job, never sole evidence.
insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'The Hindu — National', 'discovery_only', 'news_media', 'rss',
       'https://www.thehindu.com/', 'https://www.thehindu.com/news/national/feeder/default.rss',
       'general', 'en',
       '{"publisher": "THE_HINDU"}'::jsonb,
       '{"interval_hours": 12, "priority": "normal"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://www.thehindu.com/news/national/feeder/default.rss'
);

commit;

notify pgrst, 'reload schema';
