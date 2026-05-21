-- 133_purge_dry_run_scrape_queue_rows.sql
-- One-time cleanup: delete synthetic dry-run rows from scrape_queue.
--
-- Background: a 2026-05-16 dry-run scrape pass left ~210 rows with
-- is_dry_run=true in scrape_queue (some mis-statused 'pending'/'duplicate'
-- instead of the terminal 'dry_run' that migration 122 intended). They are
-- non-promotable (the promotion gate hard-blocks is_dry_run=true) and serve
-- no production purpose, so they are purged here.
--
-- Scope: every row with is_dry_run = true. is_dry_run is the durable synthetic
-- flag (migration 122); real scraped rows are is_dry_run = false and are NOT
-- touched. This is a one-time data purge — it does not affect future dry-run
-- rows created after it runs.
--
-- Referential integrity (verified against migrations): every FK pointing at
-- scrape_queue is ON DELETE CASCADE or SET NULL, so children are handled by
-- Postgres automatically and no manual child-delete ordering is needed:
--   * extracted_field_evidence.scrape_queue_id            -> CASCADE (023)
--   * recruitment_verification_reports.scrape_queue_id    -> CASCADE (075)
--   * official_resolution_attempts.scrape_queue_id        -> CASCADE (077)
--   * recruitment_verification_conflicts.scrape_queue_id  -> CASCADE (087)
--   * candidate_observations.scrape_queue_id              -> SET NULL (038)
--   * recruitment_events.scrape_queue_id                  -> SET NULL (020)
--   * scrape_queue.duplicate_of (self)                    -> SET NULL (011)
-- Nulling recruitment_events.scrape_queue_id does NOT change its event_hash
-- (that generated key is over source_id, migration 125), so there is no
-- dedup-unique collision risk.
--
-- Idempotent: re-running deletes nothing once the rows are gone, and a clean
-- DB built from migrations has no dry-run rows, so this is a no-op there.

do $$
declare
  cnt bigint;
begin
  select count(*) into cnt from public.scrape_queue where is_dry_run = true;
  raise notice 'purge dry-run scrape_queue rows: % rows will be deleted', cnt;
end $$;

delete from public.scrape_queue
 where is_dry_run = true;

notify pgrst, 'reload schema';
