-- 129_scrape_queue_trust_contract_repair.sql
-- Codifies a scrape_queue trust/evidence contract repair that was applied
-- manually in the Supabase SQL editor (no prior migration captured it).
--
-- Idempotent: on a clean DB (where migration 023 already declared
-- evidence_required / extraction_status as NOT NULL with defaults) the
-- backfills update zero rows and the ALTERs are no-ops. On the live DB it
-- re-asserts the defaults/NOT NULL and re-runs the host-applicable repair so
-- the state cannot regress.
--
-- Verified against repo before writing:
--   * scrape_queue.evidence_required / extraction_status  -> migration 023
--   * scrape_queue.official_source_resolved / _host        -> migration 011
--   * scrape_queue.source_id / extracted_data / status     -> migration 011
--   * scrape_queue.is_dry_run                              -> migration 122
--   * source_registry.source_type free-text values
--       ('official_html','official_pdf','aggregator')      -> migration 028,
--       app/backend/app/scraping/runner.py:HOST_APPLICABLE_TYPES,
--       app/backend/app/api/admin_trust.py allowlist

-- 1. Backfill nulls before tightening NOT NULL.
update public.scrape_queue
   set evidence_required = true
 where evidence_required is null;

update public.scrape_queue
   set extraction_status = 'unverified'
 where extraction_status is null;

-- 2. Tighten the contract: defaults + NOT NULL.
alter table public.scrape_queue
  alter column evidence_required set default true,
  alter column evidence_required set not null,
  alter column extraction_status set default 'unverified',
  alter column extraction_status set not null;

-- 3a. Repair pending rows that already carry the runner's
--     ``resolved_without_host_blocked`` warning but were never forced to
--     require evidence. (extracted_data->_meta->warnings is a jsonb array.)
update public.scrape_queue
   set evidence_required = true
 where status = 'pending'
   and (extracted_data #> '{_meta,warnings}') @> '["resolved_without_host_blocked"]'::jsonb
   and evidence_required is distinct from true;

-- 3b. Host-applicable repair: a pending, non-dry-run row whose source is a
--     host-applicable type but which claims an official source with no host
--     has not actually proven anything. Flip it back to unresolved, require
--     evidence, and route it to admin review.
update public.scrape_queue as sq
   set official_source_resolved = false,
       evidence_required        = true,
       extraction_status        = 'needs_review'
  from public.source_registry as sr
 where sq.source_id = sr.id
   and sq.status = 'pending'
   and sq.is_dry_run is not true
   and sr.source_type in ('official_html', 'official_pdf', 'aggregator')
   and sq.official_source_resolved = true
   and sq.official_source_host is null;

notify pgrst, 'reload schema';
