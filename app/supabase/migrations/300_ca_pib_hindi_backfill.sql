-- 300_ca_pib_hindi_backfill.sql
--
-- CA-RSS-03 — retire the Hindi PIB documents snapshotted before the English
-- follow existed.
--
-- Contract: docs/architecture/current-affairs-pipeline.md §4 (every exclusion
-- records a machine-readable reason). Builds on 294 (item-split ingest), 247
-- (generation jobs) and 299 (metadata.source_url_hi lookup index).
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 300 = MAX(filesystem)+1 at write time.
-- Confirm with: SELECT MAX(version) FROM schema_migrations; before applying.
-- RENUMBERED: landed in #1135 as 298, colliding with #1134's
-- 298_descriptive_attempt_pages.sql (duplicate schema_migrations version broke
-- the E2E Supabase start on main). Never applied anywhere under 298, so the
-- file was renamed rather than superseded; the SQL body is unchanged.
-- Apply BEFORE deploying the CA-RSS-03 ingest code: the new code re-resolves
-- these items to English on its first pass, and the Hindi rows must already be
-- out of the generation queue by then.
--
-- WHAT THIS DOES
-- --------------
-- PIB's only non-empty feed is Hindi, so every PIB item the CA-RSS-01/02 ingest
-- snapshotted is a Hindi body on a source declared default_language='en'. Those
-- documents become ingestion_status='deprioritised' with reason
-- 'language_mismatch_pre_rss03' and metadata.detected_language='hi'; their
-- pending/running ca_generation jobs move to the existing terminal 'failed'
-- status with the same reason.
--
-- Scope predicate (structural, no id list): PIB source + 'snapshotted' + no
-- metadata.source_url_hi (i.e. written before CA-RSS-03) + Devanagari-dominant
-- body. "Devanagari-dominant" is the same rule as sources.detect_language:
-- at least 40 script-bearing characters and Devanagari >= Latin.
--
-- RE-RESOLUTION (why nothing else is needed): these rows' canonical_item_url is
-- the Hindi feed link (PressReleaseIframePage.aspx?PRID=<hi>). The CA-RSS-03
-- ingest keys "already handled" for PIB on metadata.source_url_hi, which these
-- rows do not carry, so the next pass follows each Hindi item to its English
-- release and writes a NEW row whose canonical_item_url is the English URL — no
-- collision with uq_cad_source_canonical_item. A mismatch row keys on the Hindi
-- FULL page (PressReleasePage.aspx), which also never equals the Iframe link.
--
-- EXPECTED SCOPE (live, 2026-09-21): ~20 PIB Hindi documents and ~20 pending
-- ca_generation jobs. The DO block RAISES NOTICE with the actual counts so the
-- operator can reconcile against that expectation at apply time.
--
-- Nothing is deleted. No LLM, no learner surface, no frontend. Migrations are
-- immutable once merged.

begin;

do $$
declare
  v_docs int;
  v_jobs int;
begin
  create temporary table _pib_hindi_docs on commit drop as
  select x.id
  from (
    select
      d.id,
      length(regexp_replace(d.raw_text, '[^' || chr(2304) || '-' || chr(2431) || ']', '', 'g')) as dev_chars,
      length(regexp_replace(d.raw_text, '[^A-Za-z]', '', 'g'))                                     as lat_chars
    from public.current_affairs_documents d
    join public.current_affairs_sources s on s.id = d.source_id
    where s.adapter_config->>'publisher' = 'PIB'
      and d.ingestion_status = 'snapshotted'
      and d.raw_text is not null
      and (d.metadata->>'source_url_hi') is null
  ) x
  where x.dev_chars + x.lat_chars >= 40
    and x.dev_chars >= x.lat_chars;

  update public.current_affairs_documents d
  set ingestion_status = 'deprioritised',
      metadata = coalesce(d.metadata, '{}'::jsonb)
                 || jsonb_build_object(
                      'prefilter_reason', 'language_mismatch_pre_rss03',
                      'detected_language', 'hi')
  where d.id in (select id from _pib_hindi_docs);
  get diagnostics v_docs = row_count;

  -- 'failed' is the existing terminal status (247 CHECK); 'done' would falsely
  -- claim generation output. The worker never claims a failed job.
  update public.current_affairs_generation_jobs j
  set status = 'failed',
      locked_at = null,
      claim_token = null,
      last_error = 'language_mismatch_pre_rss03',
      updated_at = now()
  where j.job_kind = 'ca_generation'
    and j.status in ('pending', 'running')
    and j.document_id in (select id from _pib_hindi_docs);
  get diagnostics v_jobs = row_count;

  raise notice 'CA-RSS-03: deprioritised % PIB Hindi document(s), terminated % generation job(s) (expected ~20 / ~20 as of 2026-09-21)',
    v_docs, v_jobs;
end $$;

commit;

notify pgrst, 'reload schema';
