-- 242_financial_regulatory_family_identity_seed.sql
--
-- Lane R (Financial Regulatory & Development Institutions) — §6 core-tier
-- IDENTITY seed. Contract: docs/architecture/financial-regulatory-development-family.md
-- §1 (portfolio matrix) + §6 (evidence matrix).
--
-- Scope — identity only, and intentionally bounded:
--   * exam_families for the financial-regulatory bodies, tagged with a queryable
--     metadata `sector`/`tier` so surfaces can group the "development family"
--     WITHOUT a schema change (no new table; the family model already exists).
--   * Core exam identities and their exam_streams (migration 241).
--
-- NOT seeded here (deliberately, per governance):
--   * Cycles, cycle-stream availability, phases, sections, eligibility rules or
--     any dates/vacancies — these are notification-specific and per-cycle
--     operator-verified. All rows below are marked `provenance:'draft'`,
--     `verified:false`; NOTHING here is aspirant-verified. Per §6 every fact
--     stays draft until the official advertisement is ingested as a
--     document_assets row and reviewed; IFSCA is blocked on its PDF.
--   * Full specialist stream lists for NABARD/IRDAI/PFRDA/IFSCA/SIDBI — these
--     vary per cycle, so only the stable generalist stream is seeded and
--     specialist streams are authored per cycle (metadata note on each exam).
--     RBI (General/DEPR/DSIM) and SEBI (six streams) are structurally stable
--     and seeded in full.
--
-- Idempotent: re-running merges family metadata and skips existing exams/streams.

-- ─── 1. Bodies as exam_families + sector/tier grouping metadata ───────────
-- Merges sector/tier onto existing rbi/sebi (110) without touching their name.
insert into public.exam_families (slug, name, metadata)
select v.slug, v.name,
       jsonb_build_object('sector', 'financial-regulatory', 'tier', v.tier, 'provenance', 'draft')
from (values
  ('rbi',       'Reserve Bank of India',                                        'core'),
  ('sebi',      'Securities and Exchange Board of India',                       'core'),
  ('nabard',    'National Bank for Agriculture and Rural Development',          'core'),
  ('irdai',     'Insurance Regulatory and Development Authority of India',      'core'),
  ('pfrda',     'Pension Fund Regulatory and Development Authority',            'core'),
  ('ifsca',     'International Financial Services Centres Authority',           'core'),
  ('sidbi',     'Small Industries Development Bank of India',                   'core'),
  ('nhb',       'National Housing Bank',                                        'light'),
  ('exim',      'Export-Import Bank of India',                                  'light'),
  ('nabfid',    'National Bank for Financing Infrastructure and Development',   'light'),
  ('nps-trust', 'National Pension System Trust',                               'index_only'),
  ('epfo',      'Employees'' Provident Fund Organisation',                     'index_only'),
  ('ecgc',      'ECGC Limited',                                                 'index_only'),
  ('ibbi',      'Insolvency and Bankruptcy Board of India',                     'index_only')
) as v(slug, name, tier)
on conflict (slug) do update
  set metadata = public.exam_families.metadata || excluded.metadata;

-- ─── 2. Core + light exam identities ─────────────────────────────────────
-- rbi-grade-b / sebi-grade-a already exist (110): tag their sector/tier.
update public.exams
  set metadata = metadata || jsonb_build_object('sector', 'financial-regulatory', 'tier', 'core')
  where slug in ('rbi-grade-b', 'sebi-grade-a');

insert into public.exams (slug, name, exam_type, exam_family_id, description, metadata)
select v.slug, v.name, 'recruitment', f.id, v.description,
       jsonb_build_object(
         'sector', 'financial-regulatory', 'tier', v.tier,
         'provenance', 'draft', 'verified', false,
         'specialist_streams', 'deferred — authored per cycle from the official advertisement'
       ) || v.extra
from (values
  ('nabard-grade-a', 'NABARD Grade A (Assistant Manager, RDBS)', 'nabard', 'core',  'NABARD Grade A generalist + specialist RDBS officer recruitment.', '{}'::jsonb),
  ('irdai-am',       'IRDAI Assistant Manager',                  'irdai',  'core',  'IRDAI Assistant Manager (Generalist + Actuarial/Finance/Law/IT/Research streams).', '{}'::jsonb),
  ('pfrda-grade-a',  'PFRDA Grade A Officer',                    'pfrda',  'core',  'PFRDA Grade A officer recruitment across pension-sector streams.', '{}'::jsonb),
  ('ifsca-grade-a',  'IFSCA Grade A Officer',                    'ifsca',  'core',  'IFSCA Grade A officer recruitment (cross-regulatory IFSC remit).', jsonb_build_object('status', 'blocked_on_advertisement_pdf')),
  ('sidbi-grade-a',  'SIDBI Grade A (Assistant Manager)',        'sidbi',  'core',  'SIDBI Grade A / Assistant Manager officer recruitment.', '{}'::jsonb),
  ('nhb-am',         'NHB Assistant Manager',                    'nhb',    'light', 'National Housing Bank Assistant Manager recruitment.', '{}'::jsonb),
  ('exim-mt',        'EXIM Bank Management Trainee',             'exim',   'light', 'Export-Import Bank of India Management Trainee / specialist officer.', '{}'::jsonb),
  ('nabfid-analyst', 'NaBFID Analyst',                           'nabfid', 'light', 'NaBFID analyst / officer recruitment.', '{}'::jsonb)
) as v(slug, name, family_slug, tier, description, extra)
join public.exam_families f on f.slug = v.family_slug
on conflict (slug) do nothing;

-- ─── 3. Streams (migration 241) — RBI/SEBI in full; others generalist ────
insert into public.exam_streams (exam_id, stream_key, name, metadata)
select e.id, v.stream_key, v.name, jsonb_build_object('provenance', 'draft', 'verified', false)
from (values
  ('rbi-grade-b',   'general',           'General'),
  ('rbi-grade-b',   'depr',              'DEPR — Economic Policy & Research'),
  ('rbi-grade-b',   'dsim',              'DSIM — Statistics & Information Management'),
  ('sebi-grade-a',  'general',           'General'),
  ('sebi-grade-a',  'legal',             'Legal'),
  ('sebi-grade-a',  'it',                'Information Technology'),
  ('sebi-grade-a',  'research',          'Research'),
  ('sebi-grade-a',  'official-language', 'Official Language'),
  ('sebi-grade-a',  'engineering',       'Engineering'),
  ('nabard-grade-a','rdbs-general',      'Generalist (RDBS)'),
  ('irdai-am',      'generalist',        'Generalist'),
  ('pfrda-grade-a', 'general',           'General'),
  ('ifsca-grade-a', 'general',           'General'),
  ('sidbi-grade-a', 'general',           'General')
) as v(exam_slug, stream_key, name)
join public.exams e on e.slug = v.exam_slug
on conflict (exam_id, stream_key) do nothing;

notify pgrst, 'reload schema';
