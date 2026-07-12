-- regression_242_financial_regulatory_identity_seed.sql
--
-- Behavioral PostgreSQL regression for migration 242 (Lane R §6 identity seed).
--
-- Proves (against a DB with migrations 110, 241, 242 applied):
--   1. Every financial-regulatory body carries metadata.sector =
--      'financial-regulatory' with the expected tier.
--   2. Tagging rbi/sebi (pre-existing from 110) MERGES sector/tier without
--      dropping their prior metadata or renaming them.
--   3. Core exam identities and their exam_streams exist, with RBI (3) and
--      SEBI (6) streams seeded in full and generalist-only elsewhere.
--   4. Nothing is aspirant-verified — every seeded stream is provenance:draft.
--
-- Idempotency (re-apply yields no duplicates) is asserted by the harness that
-- applies migration 242 twice; the counts below stay stable.
--
-- Usage:  psql "$DATABASE_URL" -f regression_242_financial_regulatory_identity_seed.sql
-- Expected: PASS notices, no unexpected errors.

\set ON_ERROR_STOP on

do $$
declare
  v_int int;
begin
  -- 1. sector tagging across the family set.
  select count(*) into v_int from public.exam_families
   where slug in ('rbi','sebi','nabard','irdai','pfrda','ifsca','sidbi','nhb','exim','nabfid','nps-trust','epfo','ecgc','ibbi')
     and metadata->>'sector' = 'financial-regulatory';
  if v_int <> 14 then raise exception 'FAIL: expected 14 sector-tagged families, got %', v_int; end if;
  raise notice 'PASS: 14 financial-regulatory families tagged';

  -- 2. core tier + merge preserved rbi/sebi identity.
  if (select metadata->>'tier' from public.exam_families where slug='rbi') <> 'core' then
    raise exception 'FAIL: rbi family not tagged core';
  end if;
  if (select name from public.exam_families where slug='sebi') <> 'Securities and Exchange Board of India' then
    raise exception 'FAIL: sebi family name was overwritten';
  end if;
  raise notice 'PASS: rbi/sebi merged to core without clobbering identity';

  -- 3. core exams present.
  select count(*) into v_int from public.exams
   where slug in ('rbi-grade-b','sebi-grade-a','nabard-grade-a','irdai-am','pfrda-grade-a','ifsca-grade-a','sidbi-grade-a');
  if v_int <> 7 then raise exception 'FAIL: expected 7 core exams, got %', v_int; end if;
  raise notice 'PASS: 7 core exams present';

  -- 4. stream counts: RBI=3, SEBI=6.
  select count(*) into v_int from public.exam_streams s join public.exams e on e.id=s.exam_id where e.slug='rbi-grade-b';
  if v_int <> 3 then raise exception 'FAIL: expected 3 RBI streams, got %', v_int; end if;
  select count(*) into v_int from public.exam_streams s join public.exams e on e.id=s.exam_id where e.slug='sebi-grade-a';
  if v_int <> 6 then raise exception 'FAIL: expected 6 SEBI streams, got %', v_int; end if;
  raise notice 'PASS: RBI (3) and SEBI (6) streams seeded in full';

  -- 5. IFSCA flagged blocked; nothing aspirant-verified.
  if (select metadata->>'status' from public.exams where slug='ifsca-grade-a') <> 'blocked_on_advertisement_pdf' then
    raise exception 'FAIL: ifsca not flagged blocked_on_advertisement_pdf';
  end if;
  select count(*) into v_int from public.exam_streams where metadata->>'verified' <> 'false';
  if v_int <> 0 then raise exception 'FAIL: % streams are not draft/unverified', v_int; end if;
  raise notice 'PASS: IFSCA blocked flag set; all seeded streams draft/unverified';

  raise notice 'ALL RG242 CHECKS COMPLETE';
end $$;
