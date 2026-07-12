-- 242_financial_regulatory_family_identity_seed.sql
--
-- Lane R (Financial Regulatory & Development Institutions) — §6 core-tier
-- IDENTITY seed. Contract: docs/architecture/financial-regulatory-development-family.md
-- §1 (portfolio matrix) + §6 (evidence matrix). Reworked per the PR #962
-- checkpost review to use the canonical hierarchy the product actually reads.
--
-- Canonical model (checkpost P0):
--   * ONE umbrella exam_family 'financial-regulatory'. Family-scoped
--     applicability resolves by exact exams.exam_family_id equality
--     (study_os/writing_practice/applicability.py) — NOT metadata — so every
--     portfolio exam points at the single umbrella family. The institution
--     dimension is carried by exams.conducting_organization_id -> organizations,
--     never by one family per body. Legacy RBI/SEBI family links from 110 are
--     REPARENTED onto the umbrella.
--   * Portfolio lane is the canonical exams.management_mode (core/light/
--     index_only) + cadence, NOT metadata. Metadata only mirrors for display.
--   * Draft identities are is_active=false so they cannot leak into GET /exams
--     (which exposes every is_active=true row and does not inspect metadata,
--     app/backend/app/api/exams.py). Already-live RBI/SEBI keep their live
--     is_active (explicit disposition), and gain the canonical family/org/lane.
--   * Convergent, not merely idempotent: ON CONFLICT DO UPDATE normalizes the
--     family/org/lane on any pre-existing same-slug row (is_active is left
--     untouched so a live row is never silently retired or promoted).
--
-- Governance: nothing here is aspirant-verified. Draft exams are is_active=false
-- with metadata.provenance='draft'; streams carry provenance='draft'. IFSCA and
-- unverified specialist stream vocabularies stay blocked until the official
-- advertisement is ingested and reviewed. No cycles / cycle-stream availability /
-- phases / eligibility (per-cycle operator work — deferred to the §4 PR).

-- ─── 1. Single umbrella family ───────────────────────────────────────────
insert into public.exam_families (slug, name, metadata)
values ('financial-regulatory',
        'Financial Regulatory & Development Institutions',
        jsonb_build_object('sector', 'financial-regulatory'))
on conflict (slug) do update
  set name = excluded.name,
      metadata = public.exam_families.metadata || excluded.metadata;

-- ─── 2. Institution dimension: organizations (idempotent by name) ────────
insert into public.organizations (name, type)
select v.name, v.type
from (values
  ('Reserve Bank of India',                                      'regulator'),
  ('Securities and Exchange Board of India',                     'regulator'),
  ('National Bank for Agriculture and Rural Development',        'development_finance'),
  ('Insurance Regulatory and Development Authority of India',    'regulator'),
  ('Pension Fund Regulatory and Development Authority',          'regulator'),
  ('International Financial Services Centres Authority',          'regulator'),
  ('Small Industries Development Bank of India',                 'development_finance'),
  ('National Housing Bank',                                      'development_finance'),
  ('Export-Import Bank of India',                                'development_finance'),
  ('National Bank for Financing Infrastructure and Development', 'development_finance'),
  ('National Pension System Trust',                              'pension'),
  ('Employees'' Provident Fund Organisation',                   'provident_fund'),
  ('ECGC Limited',                                               'export_credit'),
  ('Insolvency and Bankruptcy Board of India',                  'regulator')
) as v(name, type)
where not exists (select 1 from public.organizations o where o.name = v.name);

-- ─── 3. Exam identities — one umbrella family, org ownership, canonical lane ─
-- New drafts: is_active=false. ON CONFLICT DO UPDATE converges family/org/lane
-- on any pre-existing same-slug row but never touches is_active (so live
-- RBI/SEBI keep their disposition and new drafts stay hidden).
insert into public.exams
  (slug, name, exam_type, exam_family_id, conducting_organization_id,
   management_mode, cadence, is_active, description, metadata)
select v.slug, v.name, 'recruitment', fam.id, org.id,
       v.mode, 'unknown', false, v.description,
       jsonb_build_object('sector', 'financial-regulatory', 'tier', v.mode) || v.extra
from (values
  ('rbi-grade-b',     'RBI Grade B Officer',                      'core',       'Reserve Bank of India',                                      'RBI Grade B officer (General/DEPR/DSIM).',                       '{"disposition":"pre-existing-live"}'::jsonb),
  ('sebi-grade-a',    'SEBI Grade A Officer',                     'core',       'Securities and Exchange Board of India',                     'SEBI Grade A officer across streams.',                          '{"disposition":"pre-existing-live"}'::jsonb),
  ('nabard-grade-a',  'NABARD Grade A (Assistant Manager, RDBS)', 'core',       'National Bank for Agriculture and Rural Development',        'NABARD Grade A generalist + specialist RDBS officer.',          '{"provenance":"draft","verified":false,"specialist_streams":"blocked_on_notification"}'::jsonb),
  ('nabard-grade-b',  'NABARD Grade B (Manager, RDBS)',           'core',       'National Bank for Agriculture and Rural Development',        'NABARD Grade B manager (RDBS).',                                '{"provenance":"draft","verified":false,"specialist_streams":"blocked_on_notification"}'::jsonb),
  ('irdai-am',        'IRDAI Assistant Manager',                  'core',       'Insurance Regulatory and Development Authority of India',    'IRDAI Assistant Manager (six streams).',                        '{"provenance":"draft","verified":false}'::jsonb),
  ('pfrda-grade-a',   'PFRDA Grade A Officer',                    'core',       'Pension Fund Regulatory and Development Authority',          'PFRDA Grade A officer (seven streams).',                        '{"provenance":"draft","verified":false}'::jsonb),
  ('ifsca-grade-a',   'IFSCA Grade A Officer',                    'core',       'International Financial Services Centres Authority',          'IFSCA Grade A officer (cross-regulatory IFSC remit).',          '{"provenance":"draft","verified":false,"status":"blocked_on_advertisement_pdf"}'::jsonb),
  ('sidbi-grade-a',   'SIDBI Grade A (Assistant Manager)',        'core',       'Small Industries Development Bank of India',                 'SIDBI Grade A / Assistant Manager officer.',                    '{"provenance":"draft","verified":false,"specialist_streams":"blocked_on_notification"}'::jsonb),
  ('nhb-am',          'NHB Assistant Manager',                    'light',      'National Housing Bank',                                      'National Housing Bank Assistant Manager.',                      '{"provenance":"draft","verified":false}'::jsonb),
  ('exim-mt',         'EXIM Bank Management Trainee',             'light',      'Export-Import Bank of India',                                'Export-Import Bank Management Trainee / specialist officer.',    '{"provenance":"draft","verified":false}'::jsonb),
  ('nabfid-analyst',  'NaBFID Analyst',                           'light',      'National Bank for Financing Infrastructure and Development', 'NaBFID analyst / officer.',                                     '{"provenance":"draft","verified":false}'::jsonb),
  ('nps-trust-officer','NPS Trust Officer',                       'index_only', 'National Pension System Trust',                              'NPS Trust officer cadres (index-only: identity + notifications).', '{"provenance":"draft","verified":false}'::jsonb),
  ('epfo-apfc',       'EPFO Assistant Provident Fund Commissioner','index_only','Employees'' Provident Fund Organisation',                   'EPFO APFC / SSA (index-only: identity + notifications).',       '{"provenance":"draft","verified":false}'::jsonb),
  ('ecgc-po',         'ECGC Probationary Officer',                'index_only', 'ECGC Limited',                                               'ECGC PO / specialist (index-only: identity + notifications).',  '{"provenance":"draft","verified":false}'::jsonb),
  ('ibbi-grade-a',    'IBBI Grade A Officer',                     'index_only', 'Insolvency and Bankruptcy Board of India',                   'IBBI Grade A / research (index-only: identity + notifications).', '{"provenance":"draft","verified":false}'::jsonb)
) as v(slug, name, mode, org_name, description, extra)
join public.exam_families fam on fam.slug = 'financial-regulatory'
join public.organizations org on org.name = v.org_name
on conflict (slug) do update
  set exam_family_id = excluded.exam_family_id,
      conducting_organization_id = excluded.conducting_organization_id,
      management_mode = excluded.management_mode,
      cadence = coalesce(public.exams.cadence, excluded.cadence),
      metadata = public.exams.metadata || excluded.metadata;
-- NB: is_active is deliberately NOT in the DO UPDATE set — a pre-existing live
-- row keeps its visibility; new draft rows insert as is_active=false.

-- ─── 4. Canonical stream vocabulary (241), as draft rows ─────────────────
-- Enumerated streams come from the contract §1/§6. Bodies whose specialist
-- vocabulary is not yet verifiable (NABARD, SIDBI) get the generalist stream
-- only; their exam metadata flags specialist_streams as blocked_on_notification.
-- IFSCA seeds a single provisional 'general' stream, blocked until its PDF.
insert into public.exam_streams (exam_id, stream_key, name, metadata)
select e.id, v.stream_key, v.name, v.meta
from (values
  ('rbi-grade-b',   'general',                      'General',                              '{"provenance":"draft","verified":false}'::jsonb),
  ('rbi-grade-b',   'depr',                         'DEPR — Economic Policy & Research',    '{"provenance":"draft","verified":false}'::jsonb),
  ('rbi-grade-b',   'dsim',                         'DSIM — Statistics & Information Mgmt',  '{"provenance":"draft","verified":false}'::jsonb),
  ('sebi-grade-a',  'general',                      'General',                              '{"provenance":"draft","verified":false}'::jsonb),
  ('sebi-grade-a',  'legal',                        'Legal',                                '{"provenance":"draft","verified":false}'::jsonb),
  ('sebi-grade-a',  'information-technology',       'Information Technology',               '{"provenance":"draft","verified":false}'::jsonb),
  ('sebi-grade-a',  'research',                     'Research',                             '{"provenance":"draft","verified":false}'::jsonb),
  ('sebi-grade-a',  'official-language',            'Official Language',                    '{"provenance":"draft","verified":false}'::jsonb),
  ('sebi-grade-a',  'electrical-engineering',       'Electrical Engineering',               '{"provenance":"draft","verified":false}'::jsonb),
  ('sebi-grade-a',  'civil-engineering',            'Civil Engineering',                    '{"provenance":"draft","verified":false}'::jsonb),
  ('irdai-am',      'generalist',                   'Generalist',                           '{"provenance":"draft","verified":false}'::jsonb),
  ('irdai-am',      'actuarial',                    'Actuarial',                            '{"provenance":"draft","verified":false}'::jsonb),
  ('irdai-am',      'finance',                      'Finance',                              '{"provenance":"draft","verified":false}'::jsonb),
  ('irdai-am',      'law',                          'Law',                                  '{"provenance":"draft","verified":false}'::jsonb),
  ('irdai-am',      'information-technology',       'Information Technology',               '{"provenance":"draft","verified":false}'::jsonb),
  ('irdai-am',      'research',                     'Research',                             '{"provenance":"draft","verified":false}'::jsonb),
  ('pfrda-grade-a', 'general',                      'General',                              '{"provenance":"draft","verified":false}'::jsonb),
  ('pfrda-grade-a', 'finance-accounts',            'Finance & Accounts',                   '{"provenance":"draft","verified":false}'::jsonb),
  ('pfrda-grade-a', 'information-technology',       'Information Technology',               '{"provenance":"draft","verified":false}'::jsonb),
  ('pfrda-grade-a', 'research-economics-statistics','Research (Economics/Statistics)',      '{"provenance":"draft","verified":false}'::jsonb),
  ('pfrda-grade-a', 'actuarial',                    'Actuarial',                            '{"provenance":"draft","verified":false}'::jsonb),
  ('pfrda-grade-a', 'legal',                        'Legal',                                '{"provenance":"draft","verified":false}'::jsonb),
  ('pfrda-grade-a', 'official-language',            'Official Language',                    '{"provenance":"draft","verified":false}'::jsonb),
  ('ifsca-grade-a', 'general',                      'General (provisional)',                '{"provenance":"draft","verified":false,"status":"blocked_on_advertisement_pdf"}'::jsonb),
  ('nabard-grade-a','rdbs-generalist',              'Generalist (RDBS)',                    '{"provenance":"draft","verified":false}'::jsonb),
  ('nabard-grade-b','rdbs-generalist',              'Generalist (RDBS)',                    '{"provenance":"draft","verified":false}'::jsonb),
  ('sidbi-grade-a', 'general',                      'General',                              '{"provenance":"draft","verified":false}'::jsonb)
) as v(exam_slug, stream_key, name, meta)
join public.exams e on e.slug = v.exam_slug
on conflict (exam_id, stream_key) do update
  set name = excluded.name,
      metadata = public.exam_streams.metadata || excluded.metadata;

notify pgrst, 'reload schema';
