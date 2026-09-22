-- validate_ca_rss03_pib_english.sql — CA-RSS-03 VERIFY DB.
--
-- Exercises migrations 299 + 300 against a real Postgres: the 'discovery_only'
-- ingestion status, the metadata.source_url_hi lookup index, seed idempotency,
-- the Hindi-backfill predicate, the guarantee that no retired document keeps a
-- claimable generation job, and that an English re-resolution row does not
-- collide with the legacy Hindi row's canonical-link slot. Wrapped in a
-- rollback-only transaction — leaves no data.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_rss03_pib_english.sql
--
-- Every RAISE NOTICE 'PASS ...' must print and the script must reach 'ALL PASS'.

begin;

-- ── 299 A: 'discovery_only' is an accepted ingestion status ───────────────
insert into public.current_affairs_sources
  (id, name, authority_level, adapter_type, rss_url, adapter_config, default_language)
values
  ('eeeeeeee-0000-0000-0000-000000000001', 'VERIFY PIB', 'primary_official', 'rss',
   'https://verify-pib.test/rss', '{"publisher": "PIB"}'::jsonb, 'en'),
  ('eeeeeeee-0000-0000-0000-000000000002', 'VERIFY NEWS', 'discovery_only', 'rss',
   'https://verify-news.test/rss', '{"publisher": "VERIFY_NEWS"}'::jsonb, 'en');

insert into public.current_affairs_documents
  (id, source_id, source_url, canonical_item_url, title, raw_text, content_hash,
   ingestion_status, metadata)
values
  ('eeeeeeee-3000-0000-0000-000000000001', 'eeeeeeee-0000-0000-0000-000000000002',
   'https://verify-news.test/a', 'https://verify-news.test/a', 'Headline', null,
   'vh-discovery-1', 'discovery_only', '{"prefilter_reason": "discovery_only"}'::jsonb);

do $$ begin
  raise notice 'PASS 299-A discovery_only status accepted';
end $$;

do $$ begin
  begin
    insert into public.current_affairs_documents (source_id, source_url, ingestion_status)
    values ('eeeeeeee-0000-0000-0000-000000000002', 'https://verify-news.test/x', 'bogus');
    raise exception 'FAIL 299-A an unknown ingestion_status was accepted';
  exception when check_violation then
    raise notice 'PASS 299-A unknown ingestion_status still rejected';
  end;
end $$;

-- ── 299 B: the source_url_hi index exists ─────────────────────────────────
do $$ begin
  if not exists (select 1 from pg_indexes
                 where schemaname = 'public' and indexname = 'idx_cad_source_url_hi') then
    raise exception 'FAIL 299-B idx_cad_source_url_hi missing';
  end if;
  raise notice 'PASS 299-B idx_cad_source_url_hi present';
end $$;

-- ── 299 C: seeds are present exactly once and are idempotent on re-insert ──
do $$
declare v int;
begin
  select count(*) into v from public.current_affairs_sources
  where rss_url in ('https://www.rbi.org.in/notifications_rss.xml',
                    'https://www.rbi.org.in/speeches_rss.xml',
                    'https://whc.unesco.org/en/news/rss/',
                    'https://www.thehindu.com/news/national/feeder/default.rss');
  if v <> 4 then
    raise exception 'FAIL 299-C expected 4 wave-1 sources, found %', v;
  end if;

  -- Replay one seed statement: WHERE NOT EXISTS must make it a no-op.
  insert into public.current_affairs_sources
    (name, authority_level, publisher_type, adapter_type, official_url, rss_url,
     default_category, default_language, adapter_config, crawl_schedule)
  select 'Reserve Bank of India — Speeches', 'primary_official', 'statutory_regulator', 'rss',
         'https://www.rbi.org.in/', 'https://www.rbi.org.in/speeches_rss.xml', 'economy', 'en',
         '{"publisher": "RBI", "feed": "speeches"}'::jsonb, '{"interval_hours": 48}'::jsonb
  where not exists (select 1 from public.current_affairs_sources
                    where rss_url = 'https://www.rbi.org.in/speeches_rss.xml');
  select count(*) into v from public.current_affairs_sources
  where rss_url = 'https://www.rbi.org.in/speeches_rss.xml';
  if v <> 1 then
    raise exception 'FAIL 299-C seed not idempotent (% rows)', v;
  end if;

  select count(*) into v from public.current_affairs_sources
  where adapter_config->>'publisher' = 'RBI';
  if v < 3 then
    raise exception 'FAIL 299-C expected >= 3 RBI sources (press releases + 2 wave-1), found %', v;
  end if;

  if (select authority_level from public.current_affairs_sources
      where rss_url = 'https://www.thehindu.com/news/national/feeder/default.rss') <> 'discovery_only' then
    raise exception 'FAIL 299-C The Hindu must be discovery_only';
  end if;
  raise notice 'PASS 299-C wave-1 seeds present once, idempotent, multi-RBI';
end $$;

-- ── 300: Hindi backfill predicate ─────────────────────────────────────────
insert into public.current_affairs_documents
  (id, source_id, source_url, canonical_item_url, title, raw_text, content_hash,
   ingestion_status, metadata)
values
  -- legacy Hindi row: in scope
  ('eeeeeeee-1000-0000-0000-000000000001', 'eeeeeeee-0000-0000-0000-000000000001',
   'https://pib.gov.in/PressReleaseIframePage.aspx?PRID=900001',
   'https://pib.gov.in/PressReleaseIframePage.aspx?PRID=900001',
   'हिन्दी शीर्षक', repeat('डीआरआई ने मादक पदार्थों की तस्करी ', 20), 'vh-hi-1', 'snapshotted',
   '{"publisher": "PIB"}'::jsonb),
  -- English row already written by CA-RSS-03: out of scope (has source_url_hi)
  ('eeeeeeee-2000-0000-0000-000000000001', 'eeeeeeee-0000-0000-0000-000000000001',
   'https://pib.gov.in/PressReleasePage.aspx?PRID=900100&lang=1',
   'https://pib.gov.in/PressReleasePage.aspx?PRID=900100&lang=1',
   'English title', repeat('DRI seizes contraband drugs. ', 30), 'vh-en-1', 'snapshotted',
   '{"publisher": "PIB", "source_url_hi": "https://pib.gov.in/PressReleaseIframePage.aspx?PRID=900002"}'::jsonb),
  -- legacy PIB row whose body is English: out of scope (not Devanagari-dominant)
  ('eeeeeeee-2000-0000-0000-000000000002', 'eeeeeeee-0000-0000-0000-000000000001',
   'https://pib.gov.in/PressReleaseIframePage.aspx?PRID=900003',
   'https://pib.gov.in/PressReleaseIframePage.aspx?PRID=900003',
   'Legacy English', repeat('Cabinet approves the scheme. ', 30), 'vh-en-legacy', 'snapshotted',
   '{"publisher": "PIB"}'::jsonb);

insert into public.current_affairs_generation_jobs (document_id, job_kind, generation, status)
values
  ('eeeeeeee-1000-0000-0000-000000000001', 'ca_generation', 1, 'pending'),
  ('eeeeeeee-2000-0000-0000-000000000001', 'ca_generation', 1, 'pending');

do $$
declare
  v_docs int;
begin
  create temporary table _v_hi on commit drop as
  select x.id
  from (
    select d.id,
           length(regexp_replace(d.raw_text, '[^' || chr(2304) || '-' || chr(2431) || ']', '', 'g')) as dev_chars,
           length(regexp_replace(d.raw_text, '[^A-Za-z]', '', 'g')) as lat_chars
    from public.current_affairs_documents d
    join public.current_affairs_sources s on s.id = d.source_id
    where s.adapter_config->>'publisher' = 'PIB'
      and d.ingestion_status = 'snapshotted'
      and d.raw_text is not null
      and (d.metadata->>'source_url_hi') is null
      and d.source_id = 'eeeeeeee-0000-0000-0000-000000000001'
  ) x
  where x.dev_chars + x.lat_chars >= 40 and x.dev_chars >= x.lat_chars;

  select count(*) into v_docs from _v_hi;
  if v_docs <> 1 or not exists (select 1 from _v_hi where id = 'eeeeeeee-1000-0000-0000-000000000001') then
    raise exception 'FAIL 300 predicate matched % rows, expected exactly the legacy Hindi row', v_docs;
  end if;

  update public.current_affairs_documents d
  set ingestion_status = 'deprioritised',
      metadata = d.metadata || jsonb_build_object(
        'prefilter_reason', 'language_mismatch_pre_rss03', 'detected_language', 'hi')
  where d.id in (select id from _v_hi);

  update public.current_affairs_generation_jobs j
  set status = 'failed', locked_at = null, claim_token = null,
      last_error = 'language_mismatch_pre_rss03', updated_at = now()
  where j.job_kind = 'ca_generation' and j.status in ('pending', 'running')
    and j.document_id in (select id from _v_hi);

  if exists (select 1 from public.current_affairs_generation_jobs
             where document_id = 'eeeeeeee-1000-0000-0000-000000000001'
               and status in ('pending', 'running')) then
    raise exception 'FAIL 300 retired Hindi document still has a claimable job';
  end if;
  if not exists (select 1 from public.current_affairs_generation_jobs
                 where document_id = 'eeeeeeee-2000-0000-0000-000000000001' and status = 'pending') then
    raise exception 'FAIL 300 an out-of-scope English document lost its job';
  end if;
  raise notice 'PASS 300 backfill predicate + job termination scoped correctly';
end $$;

-- ── Re-resolution: the English row for the legacy Hindi item does not collide ──
do $$ begin
  insert into public.current_affairs_documents
    (source_id, source_url, canonical_item_url, title, raw_text, content_hash,
     ingestion_status, metadata)
  values
    ('eeeeeeee-0000-0000-0000-000000000001',
     'https://pib.gov.in/PressReleasePage.aspx?PRID=900200&lang=1',
     'https://pib.gov.in/PressReleasePage.aspx?PRID=900200&lang=1',
     'English release', repeat('DRI seizes contraband drugs. ', 30), 'vh-en-2', 'snapshotted',
     '{"source_url_hi": "https://pib.gov.in/PressReleaseIframePage.aspx?PRID=900001", "source_prid_hi": "900001"}'::jsonb);

  if not exists (
    select 1 from public.current_affairs_documents
    where source_id = 'eeeeeeee-0000-0000-0000-000000000001'
      and metadata->>'source_url_hi' = 'https://pib.gov.in/PressReleaseIframePage.aspx?PRID=900001'
  ) then
    raise exception 'FAIL re-resolution row not findable by source_url_hi';
  end if;
  raise notice 'PASS re-resolution row coexists with the legacy Hindi row';
end $$;

do $$ begin raise notice 'ALL PASS'; end $$;

rollback;
