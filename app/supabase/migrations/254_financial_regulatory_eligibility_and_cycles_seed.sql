-- 254_financial_regulatory_eligibility_and_cycles_seed.sql
--
-- Lane R R1 data — seed recent cycles and per-stream baseline eligibility rules
-- for the core Financial Regulatory & Development Institutions exams whose
-- streams were seeded in migration 244 (SEBI Grade A, PFRDA Grade A, IRDAI
-- Assistant Manager). Turns the built stream-aware evaluator (PR #973) and the
-- Compass surface (PR #975) from empty scaffolding into a reviewable vertical.
--
-- GOVERNANCE — everything here is seeded reviewer_status='draft' (unverified),
-- matching migration 244's `{"provenance":"draft","verified":false}` posture and
-- the Tier-A rule (official proof + human review before user-facing verdicts).
-- The evaluator reads only reviewer_status='verified' rows, so NONE of this is
-- aspirant-visible until a reviewer (admin_exam_eligibility) promotes it. Values
-- carry a source_url + source_notes citing the cycle they are drawn from; they
-- are researched, not officially ingested, and are staged for review — do NOT
-- flip to 'verified' from code.
--
-- Why draft is also the only thing that applies on `main` today: migration 248's
-- `exam_eligibility_rules_verified_supported_check` forbids reviewer_status
-- ='verified' for the new rule_types (discipline / min_percentage /
-- certification / qualification_combination / stream_availability). PR #973 drops
-- that guard once the evaluator interprets them; verification of these rows is a
-- post-#973 review step, not part of this seed.
--
-- Idempotent: ON CONFLICT DO NOTHING against the stream-aware unique key
-- (exam_id, stream_id, scope, rule_type) from migration 248 and the
-- (exam_id, year, cycle_name) key on exam_cycles.
--
-- Migration number: highest existing file is 252; 253 is claimed by an open PR
-- and #973 lands in the 251 range. The authoritative number is
-- `select max(version)::int + 1 from schema_migrations` — VERIFY DB and rename
-- on the migration-numbers check if the live ledger disagrees. OPERATOR PENDING.

-- ─── 1. Recent cycles (draft; official dates pending advertisement ingestion) ─
insert into public.exam_cycles (exam_id, year, cycle_name, status, source_url, metadata)
select e.id, v.year, v.cycle_name, v.status, v.source_url, v.meta
from (values
  ('sebi-grade-a',  2025, 'SEBI Grade A 2025',              'completed',
     'https://www.sebi.gov.in/', '{"provenance":"draft","verified":false}'::jsonb),
  ('pfrda-grade-a', 2025, 'PFRDA Grade A 2025',             'completed',
     'https://www.pfrda.org.in/', '{"provenance":"draft","verified":false}'::jsonb),
  ('irdai-am',      2024, 'IRDAI Assistant Manager 2024',   'completed',
     'https://irdai.gov.in/', '{"provenance":"draft","verified":false}'::jsonb)
) as v(slug, year, cycle_name, status, source_url, meta)
join public.exams e on e.slug = v.slug
on conflict (exam_id, year, cycle_name) do nothing;

-- ─── 2. Exam-wide baseline (stream_id NULL) for PFRDA and IRDAI ───────────────
-- SEBI Grade A baseline is already seeded (migration 110). These use existing
-- rule_types but stay 'draft' to honour 244's unverified posture.
insert into public.exam_eligibility_rules
  (exam_id, stream_id, scope, rule_type, value_num, value_text, source_url, source_notes, reviewer_status)
select e.id, null, r.scope, r.rule_type, r.value_num, r.value_text, r.source_url, r.source_notes, 'draft'
from (values
  -- PFRDA Grade A (age band + graduation baseline)
  ('pfrda-grade-a', 'all',     'age_min',             21::numeric, null::text,   'https://www.pfrda.org.in/', 'PFRDA Grade A 2025: minimum age 21.'),
  ('pfrda-grade-a', 'general', 'age_max',             30::numeric, null,          'https://www.pfrda.org.in/', 'PFRDA Grade A 2025: general upper age 30.'),
  ('pfrda-grade-a', 'obc',     'age_max',             33::numeric, null,          'https://www.pfrda.org.in/', 'PFRDA Grade A 2025: OBC relaxation +3.'),
  ('pfrda-grade-a', 'sc',      'age_max',             35::numeric, null,          'https://www.pfrda.org.in/', 'PFRDA Grade A 2025: SC relaxation +5.'),
  ('pfrda-grade-a', 'st',      'age_max',             35::numeric, null,          'https://www.pfrda.org.in/', 'PFRDA Grade A 2025: ST relaxation +5.'),
  ('pfrda-grade-a', 'all',     'education_min_level', null,        'graduation',  'https://www.pfrda.org.in/', 'PFRDA Grade A: graduation baseline.'),
  ('pfrda-grade-a', 'all',     'nationality',         null,        'Indian',      'https://www.pfrda.org.in/', 'PFRDA Grade A: Indian nationals.'),
  -- IRDAI Assistant Manager (21-30 band + graduation baseline)
  ('irdai-am',      'all',     'age_min',             21::numeric, null,          'https://irdai.gov.in/', 'IRDAI AM 2024: minimum age 21.'),
  ('irdai-am',      'general', 'age_max',             30::numeric, null,          'https://irdai.gov.in/', 'IRDAI AM 2024: general upper age 30.'),
  ('irdai-am',      'obc',     'age_max',             33::numeric, null,          'https://irdai.gov.in/', 'IRDAI AM 2024: OBC relaxation +3.'),
  ('irdai-am',      'sc',      'age_max',             35::numeric, null,          'https://irdai.gov.in/', 'IRDAI AM 2024: SC relaxation +5.'),
  ('irdai-am',      'st',      'age_max',             35::numeric, null,          'https://irdai.gov.in/', 'IRDAI AM 2024: ST relaxation +5.'),
  ('irdai-am',      'all',     'education_min_level', null,        'graduation',  'https://irdai.gov.in/', 'IRDAI AM: graduation baseline.'),
  ('irdai-am',      'all',     'nationality',         null,        'Indian',      'https://irdai.gov.in/', 'IRDAI AM: Indian nationals.')
) as r(exam_slug, scope, rule_type, value_num, value_text, source_url, source_notes)
join public.exams e on e.slug = r.exam_slug
on conflict do nothing;

-- ─── 3. Per-stream eligibility rules (draft; stream_id set) ───────────────────
-- Stream-stable qualification facts. Multi-condition rules use the migration-248
-- qualification_combination grammar {op, clauses}. Discipline matching is the
-- evaluator's token-containment; reviewers refine to a curated synonym set.
insert into public.exam_eligibility_rules
  (exam_id, stream_id, scope, rule_type, value_num, value_text, value_json, is_knockout, source_url, source_notes, reviewer_status)
select e.id, s.id, r.scope, r.rule_type, r.value_num, r.value_text, r.value_json, r.is_knockout, r.source_url, r.source_notes, 'draft'
from (values
  -- SEBI Grade A 2025 (stream-dependent qualifications)
  ('sebi-grade-a', 'legal',                  'all', 'discipline',               null::numeric, 'law'::text, null::jsonb, true,
     'https://www.sebi.gov.in/', 'SEBI Grade A 2025 Legal stream requires a law degree.'),
  ('sebi-grade-a', 'electrical-engineering', 'all', 'discipline',               null, 'electrical', null, true,
     'https://www.sebi.gov.in/', 'SEBI Grade A 2025 Electrical Engineering stream.'),
  ('sebi-grade-a', 'civil-engineering',      'all', 'discipline',               null, 'civil', null, true,
     'https://www.sebi.gov.in/', 'SEBI Grade A 2025 Civil Engineering stream.'),
  ('sebi-grade-a', 'information-technology',  'all', 'qualification_combination', null, null,
     '{"op":"or","clauses":[{"rule_type":"discipline","value_text":"computer"},{"rule_type":"discipline","value_text":"information technology"},{"rule_type":"discipline","value_text":"electronics"}]}'::jsonb,
     true, 'https://www.sebi.gov.in/', 'SEBI IT stream: engineering / PG in computing / IT / electronics.'),
  ('sebi-grade-a', 'research',                'all', 'qualification_combination', null, null,
     '{"op":"or","clauses":[{"rule_type":"discipline","value_text":"economics"},{"rule_type":"discipline","value_text":"statistics"},{"rule_type":"discipline","value_text":"finance"}]}'::jsonb,
     true, 'https://www.sebi.gov.in/', 'SEBI Research stream: economics / statistics / finance PG.'),

  -- PFRDA Grade A 2025
  ('pfrda-grade-a', 'legal',                        'all', 'discipline',               null, 'law', null, true,
     'https://www.pfrda.org.in/', 'PFRDA Grade A 2025 Legal stream requires a law degree.'),
  ('pfrda-grade-a', 'actuarial',                    'all', 'certification',            null, 'actuarial', null, true,
     'https://www.pfrda.org.in/', 'PFRDA Actuarial stream requires an actuarial qualification.'),
  ('pfrda-grade-a', 'research-economics-statistics','all', 'qualification_combination', null, null,
     '{"op":"or","clauses":[{"rule_type":"discipline","value_text":"economics"},{"rule_type":"discipline","value_text":"statistics"}]}'::jsonb,
     true, 'https://www.pfrda.org.in/', 'PFRDA Research stream: economics / statistics PG.'),
  ('pfrda-grade-a', 'information-technology',        'all', 'qualification_combination', null, null,
     '{"op":"or","clauses":[{"rule_type":"discipline","value_text":"computer"},{"rule_type":"discipline","value_text":"information technology"}]}'::jsonb,
     true, 'https://www.pfrda.org.in/', 'PFRDA IT stream: computing / IT qualification.'),

  -- IRDAI Assistant Manager 2024 (all streams 60%; stream-specific quals)
  ('irdai-am', 'generalist', 'all', 'min_percentage',            60::numeric, null, null, true,
     'https://irdai.gov.in/', 'IRDAI Generalist: graduation with 60%.'),
  ('irdai-am', 'law',        'all', 'qualification_combination', null, null,
     '{"op":"and","clauses":[{"rule_type":"discipline","value_text":"law"},{"rule_type":"min_percentage","value_num":60}]}'::jsonb,
     true, 'https://irdai.gov.in/', 'IRDAI Law: LLB with 60%.'),
  ('irdai-am', 'actuarial',  'all', 'qualification_combination', null, null,
     '{"op":"and","clauses":[{"rule_type":"min_percentage","value_num":60},{"rule_type":"certification","value_text":"actuarial"}]}'::jsonb,
     true, 'https://irdai.gov.in/', 'IRDAI Actuarial: graduation 60% + seven IAI papers.'),
  ('irdai-am', 'finance',    'all', 'qualification_combination', null, null,
     '{"op":"and","clauses":[{"rule_type":"min_percentage","value_num":60},{"rule_type":"certification","value_text":"finance"}]}'::jsonb,
     true, 'https://irdai.gov.in/', 'IRDAI Finance: graduation 60% + specified professional qualification.'),
  ('irdai-am', 'research',   'all', 'qualification_combination', null, null,
     '{"op":"and","clauses":[{"op":"or","clauses":[{"rule_type":"discipline","value_text":"economics"},{"rule_type":"discipline","value_text":"statistics"}]},{"rule_type":"min_percentage","value_num":60}]}'::jsonb,
     true, 'https://irdai.gov.in/', 'IRDAI Research: PG economics / statistics with 60%.')
) as r(exam_slug, stream_key, scope, rule_type, value_num, value_text, value_json, is_knockout, source_url, source_notes)
join public.exams e on e.slug = r.exam_slug
join public.exam_streams s on s.exam_id = e.id and s.stream_key = r.stream_key
on conflict do nothing;

notify pgrst, 'reload schema';
