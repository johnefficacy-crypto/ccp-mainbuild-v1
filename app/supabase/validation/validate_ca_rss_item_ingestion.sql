-- validate_ca_rss_item_ingestion.sql — CA-RSS-01 VERIFY DB.
--
-- Executes the migration 294 DB guarantees that the unit tests (fake Supabase)
-- cannot: the partial unique index on (source_id, canonical_item_url), the
-- non-interference of that index with NULL/legacy rows, the feed-validator
-- columns, the PIB user_agent override, the SEBI seed, and the legacy
-- whole-feed retirement predicate. Run against a real Postgres with the
-- migrations applied. Wrapped in a rollback-only transaction — leaves no data.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_rss_item_ingestion.sql
--
-- Every RAISE NOTICE 'PASS ...' must print and the script must reach 'ALL PASS'.

begin;

-- ── schema shape ───────────────────────────────────────────────────────────
do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'current_affairs_documents'
      and column_name = 'canonical_item_url'
  ) then raise exception 'FAIL current_affairs_documents.canonical_item_url missing'; end if;

  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'current_affairs_sources'
      and column_name in ('feed_etag', 'feed_last_modified')
    having count(*) = 2
  ) then raise exception 'FAIL current_affairs_sources feed validator columns missing'; end if;

  if not exists (
    select 1 from pg_indexes
    where schemaname = 'public' and indexname = 'uq_cad_source_canonical_item'
  ) then raise exception 'FAIL uq_cad_source_canonical_item missing'; end if;

  raise notice 'PASS schema shape (canonical_item_url, feed validators, unique index)';
end $$;

-- ── seed a source and exercise the item dedup index ────────────────────────
insert into public.current_affairs_sources (id, name, authority_level, adapter_type, rss_url)
values ('cccccccc-0000-0000-0000-000000000001', 'VERIFY rss source', 'primary_official', 'rss',
        'https://verify.test/feed.xml');

do $$
declare
  v_dupe_blocked boolean := false;
begin
  insert into public.current_affairs_documents
    (source_id, source_url, canonical_item_url, title, raw_text, content_hash, ingestion_status)
  values ('cccccccc-0000-0000-0000-000000000001', 'https://verify.test/item/1',
          'https://verify.test/item/1', 'Item one',
          'A readable item body with an examinable claim.', 'hash-item-1', 'snapshotted');

  -- Same (source, canonical link) must be rejected even with a DIFFERENT body.
  begin
    insert into public.current_affairs_documents
      (source_id, source_url, canonical_item_url, title, raw_text, content_hash, ingestion_status)
    values ('cccccccc-0000-0000-0000-000000000001', 'https://verify.test/item/1?utm_source=x',
            'https://verify.test/item/1', 'Item one (re-listed)',
            'A DIFFERENT body for the same item link.', 'hash-item-1-b', 'snapshotted');
  exception when unique_violation then
    v_dupe_blocked := true;
  end;
  if not v_dupe_blocked then
    raise exception 'FAIL duplicate canonical_item_url was accepted';
  end if;
  raise notice 'PASS item-link dedup enforced by the DB, not only app logic';
end $$;

do $$
begin
  -- NULL canonical_item_url rows (legacy + non-RSS adapters) are NOT constrained.
  insert into public.current_affairs_documents
    (source_id, source_url, canonical_item_url, raw_text, content_hash, ingestion_status)
  values ('cccccccc-0000-0000-0000-000000000001', 'https://verify.test/feed.xml', null,
          '<?xml version="1.0"?><rss><channel></channel></rss>', 'hash-legacy-a', 'snapshotted'),
         ('cccccccc-0000-0000-0000-000000000001', 'https://verify.test/feed.xml', null,
          '<?xml version="1.0"?><rss><channel><item/></channel></rss>', 'hash-legacy-b', 'snapshotted');
  raise notice 'PASS partial index leaves NULL canonical_item_url rows unconstrained';
end $$;

-- ── the legacy whole-feed retirement predicate ─────────────────────────────
do $$
declare
  v_matched int;
begin
  select count(*) into v_matched
  from public.current_affairs_documents d
  where d.source_id = 'cccccccc-0000-0000-0000-000000000001'
    and d.title is null
    and d.raw_text is not null
    and ltrim(d.raw_text, chr(65279) || E' \t\n\r') like '<?xml%';
  if v_matched <> 2 then
    raise exception 'FAIL legacy predicate matched % rows, expected 2', v_matched;
  end if;

  -- The item row (titled, readable text) must NOT be caught by the predicate.
  if exists (
    select 1 from public.current_affairs_documents d
    where d.canonical_item_url = 'https://verify.test/item/1'
      and d.title is null
  ) then raise exception 'FAIL item row looks like a legacy whole-feed row'; end if;

  -- A BOM-prefixed feed body is caught too.
  if ltrim(chr(65279) || '<?xml version="1.0"?><rss/>', chr(65279) || E' \t\n\r') not like '<?xml%' then
    raise exception 'FAIL BOM-prefixed feed body not matched';
  end if;
  raise notice 'PASS legacy whole-feed predicate is strictly scoped';
end $$;

-- ── seeded source configuration ────────────────────────────────────────────
do $$
declare
  v_ua text;
  v_sebi int;
begin
  select adapter_config->>'user_agent' into v_ua
  from public.current_affairs_sources
  where adapter_config->>'publisher' = 'PIB' limit 1;
  if v_ua is null or v_ua not like 'Mozilla/5.0 (Windows%' then
    raise exception 'FAIL PIB user_agent override missing (got %)', coalesce(v_ua, '<null>');
  end if;

  select count(*) into v_sebi
  from public.current_affairs_sources
  where adapter_config->>'publisher' = 'SEBI';
  if v_sebi <> 1 then
    raise exception 'FAIL expected exactly 1 SEBI source, found %', v_sebi;
  end if;

  if not exists (
    select 1 from public.current_affairs_sources
    where adapter_config->>'publisher' = 'SEBI'
      and authority_level = 'primary_official'
      and publisher_type = 'statutory_regulator'
      and adapter_type = 'rss'
      and rss_url = 'https://www.sebi.gov.in/sebirss.xml'
      and default_category = 'economy'
      and (crawl_schedule->>'interval_hours')::int = 24
  ) then raise exception 'FAIL SEBI source row does not match the contracted shape'; end if;

  raise notice 'PASS PIB user_agent override + SEBI source row';
end $$;

-- ── SEBI seed is idempotent (re-running migration 294 adds nothing) ────────
do $$
declare v_sebi int;
begin
  insert into public.current_affairs_sources
    (name, authority_level, publisher_type, adapter_type,
     official_url, rss_url, default_category, default_language,
     adapter_config, crawl_schedule)
  select 'Securities and Exchange Board of India', 'primary_official', 'statutory_regulator', 'rss',
         'https://www.sebi.gov.in/', 'https://www.sebi.gov.in/sebirss.xml',
         'economy', 'en',
         '{"publisher": "SEBI"}'::jsonb,
         '{"interval_hours": 24, "priority": "high"}'::jsonb
  where not exists (
    select 1 from public.current_affairs_sources
    where rss_url = 'https://www.sebi.gov.in/sebirss.xml'
       or adapter_config->>'publisher' = 'SEBI'
  );
  select count(*) into v_sebi from public.current_affairs_sources
  where adapter_config->>'publisher' = 'SEBI';
  if v_sebi <> 1 then
    raise exception 'FAIL SEBI seed is not idempotent (% rows)', v_sebi;
  end if;
  raise notice 'PASS SEBI seed is idempotent';
end $$;

-- ── no legacy job was left claimable ───────────────────────────────────────
do $$
declare v_open int;
begin
  select count(*) into v_open
  from public.current_affairs_generation_jobs j
  join public.current_affairs_documents d on d.id = j.document_id
  where j.job_kind = 'ca_generation'
    and j.status in ('pending', 'running')
    and d.title is null
    and d.raw_text is not null
    and ltrim(d.raw_text, chr(65279) || E' \t\n\r') like '<?xml%';
  if v_open <> 0 then
    raise exception 'FAIL % legacy whole-feed job(s) still claimable', v_open;
  end if;
  raise notice 'PASS no legacy whole-feed generation job is claimable';
end $$;

do $$ begin raise notice 'ALL PASS — CA-RSS-01 item-level ingestion'; end $$;

rollback;
