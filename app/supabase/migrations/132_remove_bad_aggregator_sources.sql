-- 132_remove_bad_aggregator_sources.sql
-- Codifies a bad-aggregator-source purge that was executed live in the
-- Supabase SQL editor. On a clean DB this is a NO-OP (zero rows match).
--
-- Matching strategy mirrors exactly what was run live: a per-row
-- ``to_jsonb(t)::text ilike any (...)`` match against the bad hosts. This
-- deliberately does NOT name host/url columns (source_registry.source_url was
-- dropped in migration 074; recruitment_events stores URLs inside payload
-- jsonb), so it is robust to schema differences across these tables.
--
-- Hosts purged:
--   jagranjosh.com, indgovtjobs.net, freejobalert.com,
--   www.careerjyoti.in, careerjyoti.in   (the last two via %careerjyoti.in%)
--
-- Delete order (child -> parent) is the order that worked live and is
-- required for referential integrity. recruitment_events MUST be deleted
-- BEFORE source_registry: recruitment_events.source_id is ON DELETE SET NULL
-- (migration 020) and event_hash is a STORED generated column over source_id
-- with a UNIQUE index (migration 125), so nulling source_id on delete could
-- collide with an existing event_hash. Deleting the events first avoids that.
--
-- Idempotent: re-running matches nothing once the rows are gone.

-- ── Preview (read-only): row counts that WILL be deleted, per table ─────────
do $$
declare
  tbl       text;
  cnt       bigint;
  patterns  text[] := array[
    '%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%'
  ];
begin
  foreach tbl in array array[
    'recruitment_events',
    'official_resolution_attempts',
    'recruitment_verification_conflicts',
    'recruitment_verification_reports',
    'extracted_field_evidence',
    'candidate_observations',
    'listing_observations',
    'aggregator_listings',
    'notification_documents',
    'scrape_queue',
    'source_registry'
  ]
  loop
    execute format(
      'select count(*) from public.%I t where to_jsonb(t)::text ilike any ($1)', tbl
    ) into cnt using patterns;
    raise notice 'bad-aggregator-purge preview: % rows match in public.%', cnt, tbl;
  end loop;
end $$;

-- ── Deletes (child -> parent). recruitment_events FIRST. ────────────────────
delete from public.recruitment_events t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.official_resolution_attempts t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.recruitment_verification_conflicts t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.recruitment_verification_reports t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.extracted_field_evidence t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.candidate_observations t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.listing_observations t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.aggregator_listings t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.notification_documents t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.scrape_queue t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

delete from public.source_registry t
 where to_jsonb(t)::text ilike any (array['%jagranjosh.com%', '%indgovtjobs.net%', '%freejobalert.com%', '%careerjyoti.in%']);

notify pgrst, 'reload schema';
