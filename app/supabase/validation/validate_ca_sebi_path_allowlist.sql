-- validate_ca_sebi_path_allowlist.sql — CA-RSS-02 VERIFY DB.
--
-- Exercises the migration 296 backfill predicates against a real Postgres: the
-- path-allow-list split, the reason strings the ingest will also write, the
-- thin-body rule, and the guarantee that no retired document leaves a claimable
-- generation job behind. Wrapped in a rollback-only transaction — leaves no data.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_sebi_path_allowlist.sql
--
-- Every RAISE NOTICE 'PASS ...' must print and the script must reach 'ALL PASS'.

begin;

-- ── a disposable SEBI-shaped source + one document per case ────────────────
insert into public.current_affairs_sources
  (id, name, authority_level, adapter_type, rss_url, adapter_config)
values ('dddddddd-0000-0000-0000-000000000001', 'VERIFY SEBI', 'primary_official', 'rss',
        'https://verify-sebi.test/rss.xml', '{"publisher": "SEBI"}'::jsonb);

insert into public.current_affairs_documents
  (id, source_id, source_url, canonical_item_url, title, raw_text, content_hash, ingestion_status)
values
  -- excluded: enforcement order
  ('dddddddd-1000-0000-0000-000000000001', 'dddddddd-0000-0000-0000-000000000001',
   'https://verify-sebi.test/enforcement/orders/sep-2026/appeal-1',
   'https://verify-sebi.test/enforcement/orders/sep-2026/appeal-1',
   'Appeal No. 4321 filed by Someone', repeat('x', 1200), 'vh-excluded-1', 'snapshotted'),
  -- excluded: a second section, to prove the reason carries ITS OWN segments
  ('dddddddd-1000-0000-0000-000000000002', 'dddddddd-0000-0000-0000-000000000001',
   'https://verify-sebi.test/filings/reports/x',
   'https://verify-sebi.test/filings/reports/x',
   'Some filing', repeat('x', 1200), 'vh-excluded-2', 'snapshotted'),
  -- allowed + substantial: must be left completely alone
  ('dddddddd-2000-0000-0000-000000000001', 'dddddddd-0000-0000-0000-000000000001',
   'https://verify-sebi.test/media-and-notifications/press-releases/pr-1',
   'https://verify-sebi.test/media-and-notifications/press-releases/pr-1',
   'SEBI board meeting outcomes', repeat('y', 2000), 'vh-allowed-1', 'snapshotted'),
  -- allowed but chrome-only: thin-body backfill
  ('dddddddd-2000-0000-0000-000000000002', 'dddddddd-0000-0000-0000-000000000001',
   'https://verify-sebi.test/legal/circulars/c-1',
   'https://verify-sebi.test/legal/circulars/c-1',
   'Circular on KYC norms', repeat('z', 300), 'vh-thin-1', 'snapshotted');

insert into public.current_affairs_generation_jobs (document_id, job_kind, generation, status)
values
  ('dddddddd-1000-0000-0000-000000000001', 'ca_generation', 1, 'pending'),
  ('dddddddd-2000-0000-0000-000000000002', 'ca_generation', 1, 'pending'),
  ('dddddddd-2000-0000-0000-000000000001', 'ca_generation', 1, 'pending');

-- ── replay the migration's predicates ──────────────────────────────────────
do $$
declare
  v_path_docs int;
  v_thin_docs int;
begin
  create temporary table _v_items on commit drop as
  select d.id,
         regexp_replace(d.canonical_item_url, '^https?://[^/]+', '') as item_path,
         length(coalesce(d.raw_text, '')) as body_chars
  from public.current_affairs_documents d
  join public.current_affairs_sources s on s.id = d.source_id
  where s.adapter_config->>'publisher' = 'SEBI'
    and d.canonical_item_url is not null
    and d.ingestion_status = 'snapshotted';

  create temporary table _v_excluded on commit drop as
  select id, item_path from _v_items
  where item_path not like '/media-and-notifications/press-releases/%'
    and item_path not like '/legal/circulars/%'
    and item_path not like '/legal/master-circulars/%'
    and item_path not like '/legal/regulations/%'
    and item_path not like '/reports-and-statistics/reports/%';

  select count(*) into v_path_docs from _v_excluded;
  if v_path_docs <> 2 then
    raise exception 'FAIL path predicate matched % rows, expected 2', v_path_docs;
  end if;

  update public.current_affairs_documents d
  set ingestion_status = 'deprioritised',
      metadata = coalesce(d.metadata, '{}'::jsonb)
                 || jsonb_build_object(
                      'prefilter_reason',
                      'publisher_path_excluded:/' || split_part(x.item_path, '/', 2)
                        || case when split_part(x.item_path, '/', 3) <> ''
                                then '/' || split_part(x.item_path, '/', 3)
                                else '' end)
  from _v_excluded x
  where d.id = x.id;

  create temporary table _v_thin on commit drop as
  select i.id from _v_items i
  where i.id not in (select id from _v_excluded) and i.body_chars < 800;

  select count(*) into v_thin_docs from _v_thin;
  if v_thin_docs <> 1 then
    raise exception 'FAIL thin-body predicate matched % rows, expected 1', v_thin_docs;
  end if;

  update public.current_affairs_documents d
  set ingestion_status = 'deprioritised',
      metadata = coalesce(d.metadata, '{}'::jsonb)
                 || jsonb_build_object('prefilter_reason', 'thin_body_pre_rss02')
  from _v_thin t
  where d.id = t.id;

  update public.current_affairs_generation_jobs j
  set status = 'failed', locked_at = null, claim_token = null,
      last_error = 'retired_by_296', updated_at = now()
  where j.job_kind = 'ca_generation'
    and j.status in ('pending', 'running')
    and (j.document_id in (select id from _v_excluded)
         or j.document_id in (select id from _v_thin));

  raise notice 'PASS backfill predicates select exactly the intended rows';
end $$;

-- ── the reasons written must match what the ingest writes going forward ────
do $$
declare v_reason text;
begin
  select metadata->>'prefilter_reason' into v_reason
  from public.current_affairs_documents
  where id = 'dddddddd-1000-0000-0000-000000000001';
  if v_reason is distinct from 'publisher_path_excluded:/enforcement/orders' then
    raise exception 'FAIL enforcement reason was % ', coalesce(v_reason, '<null>');
  end if;

  select metadata->>'prefilter_reason' into v_reason
  from public.current_affairs_documents
  where id = 'dddddddd-1000-0000-0000-000000000002';
  if v_reason is distinct from 'publisher_path_excluded:/filings/reports' then
    raise exception 'FAIL filings reason was %', coalesce(v_reason, '<null>');
  end if;

  select metadata->>'prefilter_reason' into v_reason
  from public.current_affairs_documents
  where id = 'dddddddd-2000-0000-0000-000000000002';
  if v_reason is distinct from 'thin_body_pre_rss02' then
    raise exception 'FAIL thin-body reason was %', coalesce(v_reason, '<null>');
  end if;
  raise notice 'PASS reasons are machine-readable and carry their own path section';
end $$;

-- ── the good row is untouched, and nothing retired stays claimable ─────────
do $$
declare
  v_status text;
  v_open int;
begin
  select ingestion_status into v_status from public.current_affairs_documents
  where id = 'dddddddd-2000-0000-0000-000000000001';
  if v_status is distinct from 'snapshotted' then
    raise exception 'FAIL the allowed substantial row was changed to %', v_status;
  end if;

  if not exists (
    select 1 from public.current_affairs_generation_jobs
    where document_id = 'dddddddd-2000-0000-0000-000000000001' and status = 'pending'
  ) then raise exception 'FAIL the allowed row lost its pending generation job'; end if;

  select count(*) into v_open
  from public.current_affairs_generation_jobs j
  join public.current_affairs_documents d on d.id = j.document_id
  where j.job_kind = 'ca_generation'
    and j.status in ('pending', 'running')
    and d.ingestion_status = 'deprioritised';
  if v_open <> 0 then
    raise exception 'FAIL % retired document(s) still have a claimable job', v_open;
  end if;
  raise notice 'PASS allowed row untouched; no retired document is claimable';
end $$;

-- ── nothing was deleted ────────────────────────────────────────────────────
do $$
declare v_total int;
begin
  select count(*) into v_total from public.current_affairs_documents
  where source_id = 'dddddddd-0000-0000-0000-000000000001';
  if v_total <> 4 then
    raise exception 'FAIL expected 4 documents to survive, found %', v_total;
  end if;
  raise notice 'PASS evidence rows are retired in place, never deleted';
end $$;

do $$ begin raise notice 'ALL PASS — CA-RSS-02 SEBI path allow-list backfill'; end $$;

rollback;
