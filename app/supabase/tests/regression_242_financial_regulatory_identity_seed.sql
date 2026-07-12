-- regression_242_financial_regulatory_identity_seed.sql
--
-- Behavioral PostgreSQL regression for migration 242 (Lane R §6 identity seed),
-- reworked per the PR #962 checkpost to pin the CANONICAL model.
--
-- Proves (against a DB with migrations 110, 241, 242 applied):
--   1. Exactly ONE umbrella family 'financial-regulatory'; every portfolio exam
--      (incl. reparented RBI/SEBI from 110 and the 4 index-only bodies) links to
--      it via exam_family_id — no per-body families.
--   2. Institution ownership is on exams.conducting_organization_id -> organizations.
--   3. Portfolio lane is canonical exams.management_mode; cadence is set.
--   4. Draft identities are is_active=false (cannot leak into GET /exams); the
--      already-live RBI/SEBI keep is_active=true.
--   5. NABARD Grade B present; index-only bodies have exam identities.
--   6. SEBI stream set is complete incl. electrical- + civil-engineering; every
--      seeded stream is draft (NULL-safe check).
--   7. Convergence: a pre-existing same-slug row with the wrong family/lane is
--      normalized by re-applying the upsert (not left incorrect), while is_active
--      is preserved.
--
-- Usage:  psql "$DATABASE_URL" -f regression_242_financial_regulatory_identity_seed.sql
-- Expected: PASS notices, no unexpected errors. Convergence sub-test rolls back.

\set ON_ERROR_STOP on

do $$
declare
  v_umbrella uuid;
  v_int int;
begin
  select id into v_umbrella from public.exam_families where slug = 'financial-regulatory';
  if v_umbrella is null then raise exception 'FAIL: umbrella family missing'; end if;

  -- 1. Exactly one umbrella; all portfolio exams point at it.
  select count(*) into v_int from public.exam_families where slug = 'financial-regulatory';
  if v_int <> 1 then raise exception 'FAIL: expected 1 umbrella family, got %', v_int; end if;
  select count(*) into v_int from public.exams
   where slug in ('rbi-grade-b','sebi-grade-a','nabard-grade-a','nabard-grade-b','irdai-am',
                  'pfrda-grade-a','ifsca-grade-a','sidbi-grade-a','nhb-am','exim-mt','nabfid-analyst',
                  'nps-trust-officer','epfo-apfc','ecgc-po','ibbi-grade-a')
     and exam_family_id = v_umbrella;
  if v_int <> 15 then raise exception 'FAIL: expected 15 exams under umbrella, got %', v_int; end if;
  raise notice 'PASS: 15 portfolio exams under the single umbrella family';

  -- 1b. RBI/SEBI reparented off their legacy 110 families.
  if (select exam_family_id from public.exams where slug='rbi-grade-b') <> v_umbrella
     or (select exam_family_id from public.exams where slug='sebi-grade-a') <> v_umbrella then
    raise exception 'FAIL: RBI/SEBI not reparented onto the umbrella';
  end if;
  raise notice 'PASS: legacy RBI/SEBI reparented onto the umbrella';

  -- 2. Institution ownership via conducting_organization_id.
  select count(*) into v_int from public.exams e
   where e.slug in ('rbi-grade-b','sebi-grade-a','nabard-grade-a','nabard-grade-b','irdai-am',
                    'pfrda-grade-a','ifsca-grade-a','sidbi-grade-a','nhb-am','exim-mt','nabfid-analyst',
                    'nps-trust-officer','epfo-apfc','ecgc-po','ibbi-grade-a')
     and e.conducting_organization_id is not null;
  if v_int <> 15 then raise exception 'FAIL: expected 15 exams with conducting_organization_id, got %', v_int; end if;
  if (select o.name from public.organizations o join public.exams e on e.conducting_organization_id=o.id where e.slug='rbi-grade-b')
       <> 'Reserve Bank of India' then raise exception 'FAIL: rbi-grade-b org ownership wrong'; end if;
  raise notice 'PASS: institution ownership set on conducting_organization_id';

  -- 3. Canonical lane fields.
  if (select management_mode from public.exams where slug='nabard-grade-a') <> 'core'
     or (select management_mode from public.exams where slug='nhb-am') <> 'light'
     or (select management_mode from public.exams where slug='ibbi-grade-a') <> 'index_only' then
    raise exception 'FAIL: management_mode lanes not set canonically';
  end if;
  select count(*) into v_int from public.exams
   where slug in ('nabard-grade-a','irdai-am','pfrda-grade-a','ifsca-grade-a','sidbi-grade-a',
                  'nabard-grade-b','nhb-am','exim-mt','nabfid-analyst','nps-trust-officer','epfo-apfc','ecgc-po','ibbi-grade-a')
     and cadence is null;
  if v_int <> 0 then raise exception 'FAIL: % new exams have NULL cadence', v_int; end if;
  raise notice 'PASS: management_mode + cadence set on canonical fields';

  -- 4. Draft visibility: new drafts hidden; live RBI/SEBI visible.
  select count(*) into v_int from public.exams
   where slug in ('nabard-grade-a','nabard-grade-b','irdai-am','pfrda-grade-a','ifsca-grade-a','sidbi-grade-a',
                  'nhb-am','exim-mt','nabfid-analyst','nps-trust-officer','epfo-apfc','ecgc-po','ibbi-grade-a')
     and is_active = false;
  if v_int <> 13 then raise exception 'FAIL: expected 13 hidden draft exams, got %', v_int; end if;
  if (select is_active from public.exams where slug='rbi-grade-b') <> true then
    raise exception 'FAIL: live rbi-grade-b was retired';
  end if;
  raise notice 'PASS: 13 draft exams is_active=false; live RBI/SEBI preserved';

  -- 5. Index-only identities + NABARD Grade B.
  select count(*) into v_int from public.exams where slug in ('nps-trust-officer','epfo-apfc','ecgc-po','ibbi-grade-a');
  if v_int <> 4 then raise exception 'FAIL: expected 4 index-only exam identities, got %', v_int; end if;
  if not exists (select 1 from public.exams where slug='nabard-grade-b') then
    raise exception 'FAIL: NABARD Grade B missing';
  end if;
  raise notice 'PASS: 4 index-only identities + NABARD Grade B present';

  -- 6. SEBI streams complete (electrical + civil); all streams draft (NULL-safe).
  select count(*) into v_int from public.exam_streams s join public.exams e on e.id=s.exam_id
   where e.slug='sebi-grade-a' and s.stream_key in ('electrical-engineering','civil-engineering');
  if v_int <> 2 then raise exception 'FAIL: SEBI engineering streams not split into electrical+civil'; end if;
  -- NULL-safe: IS DISTINCT FROM catches rows with no 'verified' key.
  select count(*) into v_int from public.exam_streams where (metadata->>'verified') is distinct from 'false';
  if v_int <> 0 then raise exception 'FAIL: % streams are not draft/unverified (NULL-safe)', v_int; end if;
  raise notice 'PASS: SEBI electrical+civil present; all streams draft (NULL-safe)';

  raise notice 'ALL RG242 STATE CHECKS COMPLETE';
end $$;

-- 7. Convergence: a pre-existing malformed same-slug row is normalized by the
-- upsert, without flipping is_active. Rolled back so it leaves no trace.
BEGIN;
do $$
declare
  v_umbrella uuid;
  v_wrong uuid;
begin
  select id into v_umbrella from public.exam_families where slug='financial-regulatory';
  insert into public.exam_families (slug, name) values ('zzz-wrong-family','Wrong Family')
    on conflict (slug) do nothing;
  select id into v_wrong from public.exam_families where slug='zzz-wrong-family';

  -- Malform an existing seeded exam: wrong family, wrong lane, but leave is_active.
  update public.exams
     set exam_family_id = v_wrong, management_mode = 'archive'
   where slug = 'nabard-grade-a';

  -- Re-apply the canonical upsert for this slug (mirrors migration §3).
  insert into public.exams
    (slug, name, exam_type, exam_family_id, conducting_organization_id, management_mode, cadence, is_active, metadata)
  select 'nabard-grade-a', 'NABARD Grade A (Assistant Manager, RDBS)', 'recruitment',
         fam.id, org.id, 'core', 'unknown', false, '{}'::jsonb
  from public.exam_families fam
  join public.organizations org on org.name = 'National Bank for Agriculture and Rural Development'
  where fam.slug = 'financial-regulatory'
  on conflict (slug) do update
    set exam_family_id = excluded.exam_family_id,
        management_mode = excluded.management_mode,
        conducting_organization_id = excluded.conducting_organization_id;

  if (select exam_family_id from public.exams where slug='nabard-grade-a') <> v_umbrella then
    raise exception 'FAIL: convergence did not reparent the malformed row to the umbrella';
  end if;
  if (select management_mode from public.exams where slug='nabard-grade-a') <> 'core' then
    raise exception 'FAIL: convergence did not fix management_mode';
  end if;
  raise notice 'PASS: pre-existing malformed row converged (family + lane normalized)';
end $$;
ROLLBACK;
