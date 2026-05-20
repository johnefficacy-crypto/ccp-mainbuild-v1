-- SerpApi discovery sources — one row per engine.
--
-- SerpApi is discovery-only: both rows feed candidate URLs into
-- aggregator_listings with status 'needs_official_source' and never write to
-- recruitments directly (discovery_only + requires_official_confirmation).
-- The API key is NEVER stored here — it is read from the SERPAPI_API_KEY env
-- var by app/backend/app/scraping/serpapi_discovery.py.
--
-- Free tier is 250 searches/month total. The combined daily cap of 7 across
-- both rows (3 jobs + 4 web) leaves ~40/month buffer for manual tests.
-- Fixed UUIDs + on-conflict make this seed idempotent.

-- Government discovery via Google Search + site: operators
insert into public.source_registry (
  id,
  source_name, source_type, adapter_type, is_active,
  discovery_only, requires_official_confirmation, is_official_source,
  official_url, adapter_config, scrape_config, parser_config
) values (
  'd9a1f2b3-7c4e-4a1d-9f01-5e2a3b4c5d6e',
  'SerpApi Google Web — Government Discovery',
  'aggregator',
  'serpapi_web',
  true, true, true, false,
  'https://serpapi.com/search-api',
  jsonb_build_object(
    'location', 'India',
    'queries', jsonb_build_array(
      'site:rbi.org.in recruitment notification 2026 filetype:pdf',
      'site:ssc.gov.in notification 2026',
      'site:upsc.gov.in notification 2026 filetype:pdf',
      'site:ibps.in recruitment 2026',
      'site:rrbcdg.gov.in CEN 2026'
    )
  ),
  jsonb_build_object('max_items_per_run', 10, 'monthly_search_cap', 120, 'daily_search_cap', 4),
  '{}'::jsonb
)
on conflict (id) do update set
  source_name = excluded.source_name,
  source_type = excluded.source_type,
  adapter_type = excluded.adapter_type,
  is_active = excluded.is_active,
  discovery_only = excluded.discovery_only,
  requires_official_confirmation = excluded.requires_official_confirmation,
  is_official_source = excluded.is_official_source,
  official_url = excluded.official_url,
  adapter_config = excluded.adapter_config,
  scrape_config = excluded.scrape_config,
  parser_config = excluded.parser_config,
  updated_at = now();

-- Corporate / PSU discovery via Google Jobs (schema-marked listings)
insert into public.source_registry (
  id,
  source_name, source_type, adapter_type, is_active,
  discovery_only, requires_official_confirmation, is_official_source,
  official_url, adapter_config, scrape_config, parser_config
) values (
  'e8b2c3d4-6d5f-4b2e-8a02-6f3b4c5d6e7f',
  'SerpApi Google Jobs — PSU/Corporate Discovery',
  'aggregator',
  'serpapi_jobs',
  true, true, true, false,
  'https://serpapi.com/google-jobs-api',
  jsonb_build_object(
    'location', 'India',
    'queries', jsonb_build_array(
      'PSU recruitment India 2026',
      'ISRO BHEL ONGC engineer recruitment',
      'public sector bank officer recruitment India'
    )
  ),
  jsonb_build_object('max_items_per_run', 10, 'monthly_search_cap', 80, 'daily_search_cap', 3),
  '{}'::jsonb
)
on conflict (id) do update set
  source_name = excluded.source_name,
  source_type = excluded.source_type,
  adapter_type = excluded.adapter_type,
  is_active = excluded.is_active,
  discovery_only = excluded.discovery_only,
  requires_official_confirmation = excluded.requires_official_confirmation,
  is_official_source = excluded.is_official_source,
  official_url = excluded.official_url,
  adapter_config = excluded.adapter_config,
  scrape_config = excluded.scrape_config,
  parser_config = excluded.parser_config,
  updated_at = now();
