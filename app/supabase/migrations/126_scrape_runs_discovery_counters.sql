-- 126_scrape_runs_discovery_counters.sql
-- Separate counters for discovery-adapter (SerpApi) output on a scrape run.
--
-- Discovery leads land in aggregator_listings with status
-- needs_official_source — they are NOT scrape_queue items, so the existing
-- items_found / items_new counters (which mean "queue items") stayed 0 even
-- after a 25-lead SerpApi run, making the admin UI look broken. These three
-- columns surface discovery work without muddying the queue-item meaning.
-- lifecycle is tracked separately so we can see how many leads were routed to
-- recruitment_events (admit cards / results / corrigenda) vs persisted as new
-- discovery listings.

-- up
alter table public.scrape_runs
  add column if not exists discovery_items_found int not null default 0,
  add column if not exists discovery_items_new int not null default 0,
  add column if not exists discovery_items_lifecycle int not null default 0;
