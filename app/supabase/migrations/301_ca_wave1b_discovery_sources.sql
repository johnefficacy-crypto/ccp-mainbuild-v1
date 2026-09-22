-- 301_ca_wave1b_discovery_sources.sql
--
-- CA-SRC-01 — wave-1b discovery_only sources (6 seeds).
--
-- Contract: docs/architecture/current-affairs-pipeline.md §2 (source authority),
-- ADR 0007 (aggregators discovery-only). Builds on migration 299, which added
-- the 'discovery_only' ingestion status and seeded the first such source
-- (The Hindu — National).
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 301 = MAX(filesystem)+1 at write time.
-- Confirm with: SELECT MAX(version) FROM schema_migrations; before applying.
--
-- WHAT THIS DOES
-- --------------
-- Seeds six news-media / think-tank feeds as authority_level='discovery_only'.
-- Per ADR 0007 such a source contributes a title + link + capped feed summary
-- and NOTHING else: the ingest never fetches the item page, never stores
-- raw_text, writes ingestion_status='discovery_only', and therefore never
-- enqueues a generation job. The guard keys on authority_level alone, so these
-- rows cannot opt back into article capture through adapter_config.
--
-- FEED FORMAT — determined from the committed fixtures, NOT from the URL.
-- All six are RSS 2.0. This contradicts the wave-1b brief for three of them, so
-- it is recorded here against the evidence:
--   * Bar & Bench was expected to be Atom. Its root is <rss version="2.0">; it
--     only DECLARES xmlns:atom for an <atom:link> self-reference.
--   * LiveLaw and IndiaSpend serve from a path named google_feeds.xml but are
--     plain RSS 2.0 — no <urlset>, no news: namespace anywhere.
-- adapter_config.feed_format is therefore 'rss' on every row. The parser detects
-- the shape from the root element at run time regardless; this field records
-- what was observed, so a later format change shows up as a mismatch rather
-- than silently altering what is ingested.
--
-- IndiaSpend -> ISignal rebrand (confirmed by the repo owner 2026-09-22): same
-- organisation, same team, new masthead. The feed captured from
-- https://www.indiaspend.com/google_feeds.xml carries channel title
-- "ISignal: India's Data Desk", <link>https://www.isignal.in</link> and
-- isignal.in item links. The row is therefore seeded as
-- "ISignal (formerly IndiaSpend)" with publisher key ISIGNAL, while rss_url
-- stays on the indiaspend.com path because that is what serves the feed today.
-- The test fixture keeps its indiaspend.xml filename — it records where the
-- capture came from, not who publishes it now.
--
-- publisher_type has no CHECK constraint (plain text since migration 241), so
-- 'think_tank' and 'news_media' need no constraint change. Verified at write time.
--
-- Idempotent: every insert is guarded WHERE NOT EXISTS on rss_url, so a second
-- apply adds nothing. Nothing is updated or deleted.
--
-- No LLM, no learner surface, no frontend. Migrations are immutable once merged.

begin;

-- ── Mongabay India — environment reporting ─────────────────────────────────
insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'Mongabay India', 'discovery_only', 'news_media', 'rss',
       'https://india.mongabay.com/', 'https://india.mongabay.com/feed/',
       'environment', 'en',
       '{"publisher": "MONGABAY_INDIA", "feed_format": "rss"}'::jsonb,
       '{"interval_hours": 12, "priority": "normal"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://india.mongabay.com/feed/'
);

-- ── Vidhi Centre for Legal Policy — legal/policy research ──────────────────
insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'Vidhi Centre for Legal Policy', 'discovery_only', 'think_tank', 'rss',
       'https://vidhilegalpolicy.in/', 'https://vidhilegalpolicy.in/feed/',
       'polity', 'en',
       '{"publisher": "VIDHI", "feed_format": "rss"}'::jsonb,
       '{"interval_hours": 24, "priority": "normal"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://vidhilegalpolicy.in/feed/'
);

-- ── Centre for Policy Research — governance research (low volume) ──────────
-- NOTE: this feed ships whitespace before its <?xml?> declaration. The parser
-- strips the prologue (CA-SRC-01); before that fix the feed parsed to zero
-- entries and would have red-flagged the source on every pass.
insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'Centre for Policy Research (CPR India)', 'discovery_only', 'think_tank', 'rss',
       'https://cprindia.org/', 'https://cprindia.org/feed/',
       'governance', 'en',
       '{"publisher": "CPR_INDIA", "feed_format": "rss"}'::jsonb,
       '{"interval_hours": 48, "priority": "normal"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://cprindia.org/feed/'
);

-- ── Bar & Bench — legal news (RSS, despite the Atom expectation) ───────────
insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'Bar & Bench', 'discovery_only', 'news_media', 'rss',
       'https://www.barandbench.com/', 'https://www.barandbench.com/feed',
       'polity', 'en',
       '{"publisher": "BAR_AND_BENCH", "feed_format": "rss"}'::jsonb,
       '{"interval_hours": 12, "priority": "normal"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://www.barandbench.com/feed'
);

-- ── LiveLaw — legal news (RSS, despite the google_feeds.xml path) ──────────
insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'LiveLaw', 'discovery_only', 'news_media', 'rss',
       'https://www.livelaw.in/', 'https://www.livelaw.in/google_feeds.xml',
       'polity', 'en',
       '{"publisher": "LIVELAW", "feed_format": "rss"}'::jsonb,
       '{"interval_hours": 12, "priority": "normal"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://www.livelaw.in/google_feeds.xml'
);

-- ── ISignal (formerly IndiaSpend) — data journalism; see the header note ──
insert into public.current_affairs_sources
  (name, authority_level, publisher_type, adapter_type,
   official_url, rss_url, default_category, default_language,
   adapter_config, crawl_schedule)
select 'ISignal (formerly IndiaSpend)', 'discovery_only', 'news_media', 'rss',
       'https://www.isignal.in/', 'https://www.indiaspend.com/google_feeds.xml',
       'social', 'en',
       '{"publisher": "ISIGNAL", "feed_format": "rss"}'::jsonb,
       '{"interval_hours": 24, "priority": "normal"}'::jsonb
where not exists (
  select 1 from public.current_affairs_sources
  where rss_url = 'https://www.indiaspend.com/google_feeds.xml'
);

do $$
declare v_seeded int;
begin
  select count(*) into v_seeded
  from public.current_affairs_sources
  where adapter_config->>'publisher' in (
    'MONGABAY_INDIA', 'VIDHI', 'CPR_INDIA', 'BAR_AND_BENCH', 'LIVELAW', 'ISIGNAL');
  raise notice 'CA-SRC-01: % wave-1b discovery source(s) present (expected 6)', v_seeded;

  if exists (
    select 1 from public.current_affairs_sources
    where adapter_config->>'publisher' in (
      'MONGABAY_INDIA', 'VIDHI', 'CPR_INDIA', 'BAR_AND_BENCH', 'LIVELAW', 'ISIGNAL')
      and authority_level <> 'discovery_only'
  ) then
    raise exception 'CA-SRC-01: a wave-1b source is not discovery_only';
  end if;
end $$;

commit;

notify pgrst, 'reload schema';
