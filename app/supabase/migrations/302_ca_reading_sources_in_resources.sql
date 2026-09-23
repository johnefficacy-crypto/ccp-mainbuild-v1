-- 302_ca_reading_sources_in_resources.sql
--
-- CA-RES-01 — current-affairs reading sources in the Resources library.
--
-- Contract: docs/architecture/current-affairs-pipeline.md §2 (source authority),
-- ADR 0007. Locked IA rule: no new top-level surface — these rows land in the
-- EXISTING Current Affairs lane of /app/resources.
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 302 = MAX(filesystem)+1 at write time.
-- Confirm with: SELECT MAX(version) FROM schema_migrations; before applying.
--
-- WHAT THIS DOES
-- --------------
-- A. resource_type CHECK gains 'reading_source' (a standing publication to read,
--    as opposed to 'current_affairs_digest', which is one dated compilation).
-- B. source_trust CHECK gains 'publication' — a named editorial outlet that is
--    neither a government/official source nor user-contributed.
-- C. community_resources.ca_source_id -> current_affairs_sources(id), so a
--    reading source the ingest already crawls is linked to its pipeline row.
--    Nullable and ON DELETE SET NULL: most of these are read-only references the
--    pipeline does not ingest, and retiring a CA source must not delete a
--    reading-list entry.
-- D. Seeds approved reading_source rows, ONE PER (source x exam).
--
-- exam FORMAT: the exam SLUG (upsc-cse, ibps-po, ...), with exam_id resolved
-- from exams.slug by subquery — never a hardcoded uuid. The API expands a
-- family key (upsc, banking, regulatory_bodies, ssc) to its slugs, so a user
-- whose goal_exams[0] is a family still matches these rows.
--
-- Idempotency key is (source_url, exam, resource_type, TITLE). Title is part of
-- the key because Yojana and Kurukshetra are published from the same journals
-- URL; without it the second would be treated as a duplicate of the first.
--
-- A slug that does not exist in public.exams simply seeds nothing for that exam
-- (the join drops it). That would be silent, so the DO block at the end reports
-- every expected slug that is missing along with the seeded row count.
--
-- Nothing is updated or deleted. No live rows existed before this (operator
-- confirmed community_resources was empty), so there is no legacy normalisation.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A + B. Constraint extensions
-- ═════════════════════════════════════════════════════════════════════════

alter table public.community_resources
  drop constraint if exists community_resources_resource_type_check;
alter table public.community_resources
  add constraint community_resources_resource_type_check
    check (resource_type in (
      'pyq_paper','notes','strategy_guide','video_link','course_link','book',
      'concept_note','formula_sheet','grammar_sheet','vocabulary_sheet',
      'drill_set','practice_set','current_affairs_digest','scheme_card',
      'pyq_solution','mindmap','revision_sheet','reading_source'
    ));

alter table public.community_resources
  drop constraint if exists community_resources_source_trust_check;
alter table public.community_resources
  add constraint community_resources_source_trust_check
    check (source_trust in ('official','community','coaching','unknown','publication'));

-- ═════════════════════════════════════════════════════════════════════════
-- C. Link to the current-affairs source registry
-- ═════════════════════════════════════════════════════════════════════════

alter table public.community_resources
  add column if not exists ca_source_id uuid
    references public.current_affairs_sources(id) on delete set null;

create index if not exists idx_community_resources_ca_source
  on public.community_resources(ca_source_id)
  where ca_source_id is not null;

-- Idempotency at the DB level, not just in the insert's NOT EXISTS: a curated
-- reading source is unique per (url, exam, title). Title is in the key because
-- Yojana and Kurukshetra share one journals URL. Partial, so ordinary
-- user-contributed rows are not constrained by it.
create unique index if not exists uq_community_resources_reading_source
  on public.community_resources(source_url, exam, resource_type, title)
  where resource_type = 'reading_source';

comment on column public.community_resources.ca_source_id is
  'The current_affairs_sources row this reading source corresponds to, when the ingest crawls it. NULL for references the pipeline does not ingest.';

-- ═════════════════════════════════════════════════════════════════════════
-- D. Seed reading sources, one row per (source x exam)
-- ═════════════════════════════════════════════════════════════════════════

with groups(grp, exam_slug) as (
  values
    -- ALL: the eight exams plus the two SSC papers whose GA section draws on
    -- PIB / Budget / Economic Survey / MoSPI.
    ('ALL', 'upsc-cse'),
    ('ALL', 'rbi-grade-b'),
    ('ALL', 'sebi-grade-a'),
    ('ALL', 'national-nabard-grade-a'),
    ('ALL', 'pfrda-grade-a'),
    ('ALL', 'ifsca-grade-a'),
    ('ALL', 'ibps-po'),
    ('ALL', 'sbi-po'),
    ('ALL', 'national-ssc-combined-graduate-level-cgl'),
    ('ALL', 'national-ssc-combined-higher-secondary-level-chsl'),
    ('UPSC', 'upsc-cse'),
    ('BANK', 'ibps-po'),
    ('BANK', 'sbi-po'),
    ('REG', 'rbi-grade-b'),
    ('REG', 'sebi-grade-a'),
    ('REG', 'national-nabard-grade-a'),
    ('REG', 'pfrda-grade-a'),
    ('REG', 'ifsca-grade-a')
),
seed(title, source_url, trust, subject, grp, why) as (
  values
    ('PIB — Press releases', 'https://pib.gov.in/', 'official', 'General', 'ALL',
     'Primary government announcement wire; the origin of most scheme, appointment and policy questions.'),
    ('RBI — Press releases, notifications, speeches', 'https://www.rbi.org.in/', 'official', 'Economy & Banking', 'REG',
     'Monetary policy, regulation and banking-sector notifications in their authoritative form.'),
    ('RBI — Press releases, notifications, speeches', 'https://www.rbi.org.in/', 'official', 'Economy & Banking', 'BANK',
     'Monetary policy, regulation and banking-sector notifications in their authoritative form.'),
    ('RBI — Press releases, notifications, speeches', 'https://www.rbi.org.in/', 'official', 'Economy & Banking', 'UPSC',
     'Monetary policy, regulation and banking-sector notifications in their authoritative form.'),
    ('SEBI — Press releases & circulars', 'https://www.sebi.gov.in/', 'official', 'Economy & Banking', 'REG',
     'Securities-market regulation: circulars and board decisions as issued.'),
    ('SEBI — Press releases & circulars', 'https://www.sebi.gov.in/', 'official', 'Economy & Banking', 'UPSC',
     'Securities-market regulation: circulars and board decisions as issued.'),
    ('Economic Survey', 'https://www.indiabudget.gov.in/economicsurvey/', 'official', 'Economy & Banking', 'ALL',
     'The government''s own annual read of the economy; a recurring source of data and framing.'),
    ('Union Budget', 'https://www.indiabudget.gov.in/', 'official', 'Economy & Banking', 'ALL',
     'Allocations, tax changes and scheme outlays in primary form.'),
    ('NABARD', 'https://www.nabard.org/', 'official', 'Economy & Banking', 'REG',
     'Rural and agricultural credit policy, the core of NABARD and banking rural-development sections.'),
    ('NABARD', 'https://www.nabard.org/', 'official', 'Economy & Banking', 'BANK',
     'Rural and agricultural credit policy, the core of NABARD and banking rural-development sections.'),
    ('IRDAI', 'https://irdai.gov.in/', 'official', 'Economy & Banking', 'REG',
     'Insurance regulation and sector circulars.'),
    ('PFRDA', 'https://www.pfrda.org.in/', 'official', 'Economy & Banking', 'REG',
     'Pension regulation, NPS and APY changes at source.'),
    ('IFSCA', 'https://ifsca.gov.in/', 'official', 'Economy & Banking', 'REG',
     'GIFT-City and international financial services regulation.'),
    ('MoSPI (GDP, CPI, PLFS)', 'https://mospi.gov.in/', 'official', 'Economy & Banking', 'ALL',
     'The release point for GDP, CPI and PLFS — the numbers quantitative questions are built from.'),
    ('MEA — Press releases', 'https://www.mea.gov.in/', 'official', 'International Relations', 'UPSC',
     'Bilateral visits, agreements and India''s stated positions, unmediated.'),
    ('Supreme Court of India — Judgments', 'https://www.sci.gov.in/', 'official', 'Polity & Governance', 'UPSC',
     'Judgments in full text, rather than a secondary summary of them.'),
    ('Election Commission of India', 'https://www.eci.gov.in/', 'official', 'Polity & Governance', 'UPSC',
     'Electoral process, schedules and reform notifications.'),
    ('PRS Legislative Research', 'https://prsindia.org/', 'publication', 'Polity & Governance', 'UPSC',
     'Bill tracking and legislative briefs — the clearest account of what a law actually changes.'),
    ('Supreme Court Observer', 'https://www.scobserver.in/', 'publication', 'Polity & Governance', 'UPSC',
     'Constitution-bench case tracking with the issues stated plainly.'),
    ('Vidhi Centre for Legal Policy', 'https://vidhilegalpolicy.in/', 'publication', 'Polity & Governance', 'UPSC',
     'Legal-policy research on governance and regulatory design.'),
    ('Centre for Policy Research', 'https://cprindia.org/', 'publication', 'Polity & Governance', 'UPSC',
     'Governance, urbanisation and federalism research.'),
    ('LiveLaw', 'https://www.livelaw.in/', 'publication', 'Polity & Governance', 'UPSC',
     'Court reporting fast enough to catch judgments while they are current.'),
    ('Bar & Bench', 'https://www.barandbench.com/', 'publication', 'Polity & Governance', 'UPSC',
     'Court and legal-profession reporting alongside LiveLaw.'),
    ('ORF', 'https://www.orfonline.org/', 'publication', 'International Relations', 'UPSC',
     'Foreign-policy and strategic-affairs commentary for essay and interview framing.'),
    ('MP-IDSA', 'https://www.idsa.in/', 'publication', 'Security', 'UPSC',
     'Defence and internal-security analysis, a thin area in general reporting.'),
    ('NGT orders', 'https://greentribunal.gov.in/', 'official', 'Environment & Ecology', 'UPSC',
     'Environmental adjudication as issued, not as summarised.'),
    ('Down To Earth (CSE)', 'https://www.downtoearth.org.in/', 'publication', 'Environment & Ecology', 'UPSC',
     'Environment and development reporting with the science kept intact.'),
    ('Mongabay India', 'https://india.mongabay.com/', 'publication', 'Environment & Ecology', 'UPSC',
     'Biodiversity and conservation reporting from the field.'),
    ('UNESCO World Heritage Centre', 'https://whc.unesco.org/', 'official', 'History & Culture', 'UPSC',
     'Inscriptions and tentative-list changes, a reliable factual question source.'),
    ('Yojana', 'https://www.publicationsdivision.nic.in/journals', 'official', 'General', 'UPSC',
     'Monthly government perspective on development themes.'),
    ('Kurukshetra', 'https://www.publicationsdivision.nic.in/journals', 'official', 'Rural Development', 'UPSC',
     'Monthly rural-development counterpart to Yojana.'),
    ('Science Reporter (CSIR-NIScPR)', 'https://niscpr.res.in/', 'official', 'Science & Technology', 'UPSC',
     'Indian science and technology coverage pitched at a general reader.'),
    ('The Hindu — National', 'https://www.thehindu.com/news/national/', 'publication', 'General', 'UPSC',
     'Daily national coverage; the standard reading spine for the general-studies paper.'),
    ('ISignal (formerly IndiaSpend)', 'https://www.isignal.in/', 'publication', 'Society', 'UPSC',
     'Data journalism on health, education and employment.')
)
insert into public.community_resources (
  title, resource_type, exam, exam_id, subject, source_url, source_trust,
  contributed_by, size_label, status, verified_by_topper, verification_notes,
  source_kind, ca_source_id
)
select
  s.title,
  'reading_source',
  g.exam_slug,
  e.id,
  s.subject,
  s.source_url,
  s.trust,
  null,                       -- contributed_by: curated, not user-contributed
  'link',
  'approved',
  false,
  s.why,
  'ca_reading_list',
  (
    -- The pipeline row this reading source corresponds to, when one exists.
    -- Matched on official_url, with a name fallback for sources whose reading
    -- URL is a section rather than the site root (The Hindu). RBI has three
    -- feed rows behind one official_url, so this is deterministically the
    -- earliest of them rather than an arbitrary pick.
    select cas.id
    from public.current_affairs_sources cas
    where cas.official_url = s.source_url or cas.name = s.title
    order by cas.created_at, cas.id
    limit 1
  )
from seed s
join groups g on g.grp = s.grp
join public.exams e on e.slug = g.exam_slug
where not exists (
  select 1 from public.community_resources cr
  where cr.source_url = s.source_url
    and cr.exam = g.exam_slug
    and cr.resource_type = 'reading_source'
    and cr.title = s.title
);

do $$
declare
  v_rows int;
  v_missing text;
begin
  select count(*) into v_rows
  from public.community_resources
  where resource_type = 'reading_source' and source_kind = 'ca_reading_list';

  select string_agg(slug, ', ' order by slug) into v_missing
  from (
    values
      ('upsc-cse'), ('rbi-grade-b'), ('sebi-grade-a'), ('national-nabard-grade-a'),
      ('pfrda-grade-a'), ('ifsca-grade-a'), ('ibps-po'), ('sbi-po'),
      ('national-ssc-combined-graduate-level-cgl'),
      ('national-ssc-combined-higher-secondary-level-chsl')
  ) as expected(slug)
  where not exists (select 1 from public.exams e where e.slug = expected.slug);

  if v_missing is not null then
    -- Not fatal: the rest of the seed is still correct. But a missing slug means
    -- that exam silently got no reading list, so it must not pass unnoticed.
    raise warning 'CA-RES-01: no exams row for slug(s): % — those exams were not seeded', v_missing;
  end if;

  raise notice 'CA-RES-01: % reading_source row(s) present (expected 96 with all 10 exam slugs present)', v_rows;
end $$;

commit;

notify pgrst, 'reload schema';
