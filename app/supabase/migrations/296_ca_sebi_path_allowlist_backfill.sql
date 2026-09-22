-- 296_ca_sebi_path_allowlist_backfill.sql
--
-- CA-RSS-02 — retire the SEBI item documents that the CA-RSS-01 first pass
-- snapshotted before the publisher URL-path allow-list existed.
--
-- Contract: docs/architecture/current-affairs-pipeline.md §4 (ingestion; every
-- exclusion records a machine-readable reason). Builds on migration 294
-- (canonical_item_url + item-split ingest) and 247 (generation jobs).
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 296 = MAX(filesystem)+1 at write time.
-- Confirm with: SELECT MAX(version) FROM schema_migrations; before applying.
--
-- WHAT THIS DOES
-- --------------
-- The SEBI feed's first item-split pass produced 30 documents. 15 were caught by
-- the title deny-list. Of the 15 snapshotted, 14 are /enforcement/orders/...
-- (party-specific RTI appeals and interim orders — no examinable general-awareness
-- claim) and 1 is a press release whose stored body is page chrome only, because
-- SEBI embeds the real document as a PDF the CA-RSS-01 extractor never reached.
--
-- A. Path-excluded backfill — SEBI documents whose canonical_item_url path is
--    OUTSIDE the allow-list now enforced in app/current_affairs/sources.py
--    (_PATH_ALLOWLIST["SEBI"]) become ingestion_status='deprioritised' with
--    reason 'publisher_path_excluded:/<seg1>/<seg2>', matching what the ingest
--    records going forward. Their pending/running ca_generation jobs move to the
--    existing terminal 'failed' status with the same reason.
-- B. Thin-body backfill — SEBI documents INSIDE the allow-list whose raw_text is
--    shorter than the 800-char PDF-fallback threshold are chrome-only snapshots.
--    They become 'deprioritised' with reason 'thin_body_pre_rss02', jobs likewise
--    terminal.
--
-- KNOWN LIMITATION (stated, not worked around): 294's partial unique index
-- uq_cad_source_canonical_item (source_id, canonical_item_url) means a
-- deprioritised item link can never be re-snapshotted by a later pass — the row
-- holds that item's slot. The thin-body rows (expected: 1) therefore stay
-- deprioritised until an operator deletes them so the improved extractor can
-- re-ingest. Rows are NOT deleted here: documents are immutable evidence, and
-- deleting live rows from a migration is not a decision this migration may make.
--
-- Nothing is deleted. published_at is NOT backfilled: metadata.raw_pub_date did
-- not exist before this change, so there is no stored raw value to re-parse for
-- these rows — the date is only recoverable by re-crawling, which is out of scope.
--
-- EXPECTED SCOPE (live, after the CA-RSS-01 first pass, 2026-09-21):
-- 14 path-excluded documents and 1 thin-body document. The predicates are
-- structural (publisher marker + URL path + body length), never a hardcoded id
-- list; the DO block RAISES NOTICE with the actual counts so the operator can
-- reconcile against that expectation at apply time.
--
-- No LLM, no learner surface, no frontend. Migrations are immutable once merged.

begin;

do $$
declare
  v_path_docs int;
  v_path_jobs int;
  v_thin_docs int;
  v_thin_jobs int;
begin
  -- SEBI item documents from the item-split ingest, split by whether their path
  -- is inside the allow-list. regexp_replace strips scheme+host so the prefix
  -- test runs on the path alone, exactly as sources.path_allowed does.
  create temporary table _sebi_items on commit drop as
  select
    d.id,
    regexp_replace(d.canonical_item_url, '^https?://[^/]+', '') as item_path,
    length(coalesce(d.raw_text, ''))                            as body_chars
  from public.current_affairs_documents d
  join public.current_affairs_sources s on s.id = d.source_id
  where s.adapter_config->>'publisher' = 'SEBI'
    and d.canonical_item_url is not null
    and d.ingestion_status = 'snapshotted';

  create temporary table _sebi_path_excluded on commit drop as
  select id, item_path
  from _sebi_items
  where item_path not like '/media-and-notifications/press-releases/%'
    and item_path not like '/legal/circulars/%'
    and item_path not like '/legal/master-circulars/%'
    and item_path not like '/legal/regulations/%'
    and item_path not like '/reports-and-statistics/reports/%';

  -- ── A. path-excluded ─────────────────────────────────────────────────────
  update public.current_affairs_documents d
  set ingestion_status = 'deprioritised',
      metadata = coalesce(d.metadata, '{}'::jsonb)
                 || jsonb_build_object(
                      'prefilter_reason',
                      'publisher_path_excluded:/'
                        || split_part(x.item_path, '/', 2)
                        || case when split_part(x.item_path, '/', 3) <> ''
                                then '/' || split_part(x.item_path, '/', 3)
                                else '' end)
  from _sebi_path_excluded x
  where d.id = x.id;
  get diagnostics v_path_docs = row_count;

  update public.current_affairs_generation_jobs j
  set status = 'failed',
      locked_at = null,
      claim_token = null,
      last_error = 'publisher_path_excluded',
      updated_at = now()
  where j.job_kind = 'ca_generation'
    and j.status in ('pending', 'running')
    and j.document_id in (select id from _sebi_path_excluded);
  get diagnostics v_path_jobs = row_count;

  -- ── B. thin body inside the allow-list ───────────────────────────────────
  create temporary table _sebi_thin on commit drop as
  select i.id
  from _sebi_items i
  where i.id not in (select id from _sebi_path_excluded)
    and i.body_chars < 800;

  update public.current_affairs_documents d
  set ingestion_status = 'deprioritised',
      metadata = coalesce(d.metadata, '{}'::jsonb)
                 || jsonb_build_object('prefilter_reason', 'thin_body_pre_rss02')
  from _sebi_thin t
  where d.id = t.id;
  get diagnostics v_thin_docs = row_count;

  update public.current_affairs_generation_jobs j
  set status = 'failed',
      locked_at = null,
      claim_token = null,
      last_error = 'thin_body_pre_rss02',
      updated_at = now()
  where j.job_kind = 'ca_generation'
    and j.status in ('pending', 'running')
    and j.document_id in (select id from _sebi_thin);
  get diagnostics v_thin_jobs = row_count;

  raise notice 'CA-RSS-02: path-excluded % doc(s) / % job(s); thin-body % doc(s) / % job(s) (expected 14 and 1 doc(s) as of 2026-09-21)',
    v_path_docs, v_path_jobs, v_thin_docs, v_thin_jobs;
end $$;

commit;

notify pgrst, 'reload schema';
