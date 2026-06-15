-- pilot_content_ssc_cgl_banking.sql
-- PILOT content seed — SSC CGL + Banking exam prep material.
--
-- Covers the initial topic / resource set agreed for Phase 1 rollout:
--
--   Quant    : Percentage, Ratio & Proportion, Profit & Loss, Time & Work
--   Reasoning: Syllogism, Seating Arrangement, Blood Relation
--   English  : Error Spotting, Cloze Test, Vocabulary
--   GK/CA    : PIB weekly digest (current_affairs_digest), scheme cards
--
-- All community_resources rows carry reviewer_status='verified' and
-- usable_for_mock_generation=false.
--
-- ══════════════════════════════════════════════════════════════════════════════
-- MOCK-EXPANSION GATE
-- ══════════════════════════════════════════════════════════════════════════════
-- Full mock expansion (usable_for_mock_generation=true on community_resources
-- and reviewer_status='live' on mock_question_bank rows) is LOCKED until
-- the following threshold is met:
--
--   ≥ 200 mock_question_bank rows with
--       subject_id = '55555555-5555-5555-5555-555555555551'   (Quantitative Aptitude)
--     AND reviewer_status = 'verified'
--
-- This file seeds the pilot batch (< 200 Quant questions). No row in this
-- file sets usable_for_mock_generation=true or reviewer_status='live'.
-- The CI test test_content_safety_gate.py asserts these invariants on the
-- seed data.
-- ══════════════════════════════════════════════════════════════════════════════
--
-- Depends on:
--   exam_intelligence_demo_ssc_cgl.sql   (exam/subject/topic UUIDs)
--   156_resource_extension.sql           (community_resources new columns)
--   156_exam_subject_resources.sql       (exam_subject_resources table)
--   156_exam_documents.sql               (exam_documents table)
--   135_mock_engine_core.sql             (mock_question_bank table)
--   156_mock_question_provenance.sql     (reviewer_status 'verified' value)
--
-- Safe to re-run: all inserts use ON CONFLICT (id) DO NOTHING.
-- Apply: psql "$DATABASE_URL" -f pilot_content_ssc_cgl_banking.sql
--
-- UUID blocks used in this file (all deterministic):
--   Topics        cccccc01-…  through cccccc0a-…
--   ESR rows      d0000001-…  through d000000e-…
--   Docs          e0000001-…  through e0000004-…
--   CR rows       f0000001-…  through f0000016-…
--   MQB questions b1000001-…  through b100001e-…  (30 pilot Quant questions)
--   MQB options   b2000001-…  through b200007b-…

begin;

-- ── Shared UUIDs from exam_intelligence_demo_ssc_cgl.sql ────────────────────
-- exam_id          : 22222222-2222-2222-2222-222222222222
-- exam_cycle_id    : 33333333-3333-3333-3333-333333333333
-- exam_phase_id T1 : 44444444-4444-4444-4444-444444444441
-- subject Quant    : 55555555-5555-5555-5555-555555555551
-- subject English  : 55555555-5555-5555-5555-555555555552
-- subject Reasoning: 55555555-5555-5555-5555-555555555553
-- topic Percentage : 66666666-6666-6666-6666-666666666661
-- topic Profit&Loss: 66666666-6666-6666-6666-666666666662
-- topic TimeWork   : 66666666-6666-6666-6666-666666666664
-- topic Vocabulary : 66666666-6666-6666-6666-666666666666

-- ── New topics ───────────────────────────────────────────────────────────────
insert into public.topics (id, subject_id, slug, name, level, default_difficulty_level) values
  ('cccccc01-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555551',
   'ratio-and-proportion', 'Ratio & Proportion', 'topic', 'medium'),
  ('cccccc02-0000-0000-0000-000000000002', '55555555-5555-5555-5555-555555555553',
   'syllogism', 'Syllogism', 'topic', 'medium'),
  ('cccccc03-0000-0000-0000-000000000003', '55555555-5555-5555-5555-555555555553',
   'seating-arrangement', 'Seating Arrangement', 'topic', 'medium_high'),
  ('cccccc04-0000-0000-0000-000000000004', '55555555-5555-5555-5555-555555555553',
   'blood-relation', 'Blood Relation', 'topic', 'medium'),
  ('cccccc05-0000-0000-0000-000000000005', '55555555-5555-5555-5555-555555555552',
   'error-spotting', 'Error Spotting', 'topic', 'medium'),
  ('cccccc06-0000-0000-0000-000000000006', '55555555-5555-5555-5555-555555555552',
   'cloze-test', 'Cloze Test', 'topic', 'medium')
on conflict (id) do nothing;

-- ── Banking exam family ───────────────────────────────────────────────────────
do $$
declare
  ibps_family_id uuid;
  ibps_exam_id uuid;
begin
  insert into public.exam_families (id, slug, name, description) values
    ('bbbbbb01-0000-0000-0000-000000000001', 'ibps',
     'Institute of Banking Personnel Selection',
     'Central body conducting recruitment for public sector banks.')
  on conflict (slug) do update
    set name = excluded.name,
        description = excluded.description
  returning id into ibps_family_id;

  insert into public.exams (id, exam_family_id, slug, name, exam_type, default_difficulty_level, description) values
    ('bbbbbb02-0000-0000-0000-000000000002', ibps_family_id,
     'ibps-po', 'IBPS PO', 'recruitment', 'medium_high',
     'Probationary Officer recruitment conducted by IBPS for public sector banks.')
  on conflict (slug) do update
    set exam_family_id = excluded.exam_family_id,
        name = excluded.name,
        exam_type = excluded.exam_type,
        default_difficulty_level = excluded.default_difficulty_level,
        description = excluded.description
  returning id into ibps_exam_id;

  if ibps_exam_id <> 'bbbbbb02-0000-0000-0000-000000000002'::uuid then
    raise exception 'IBPS PO seed expected canonical exam id %, but slug ibps-po resolved to %. Repair exam identity before re-running this seed.',
      'bbbbbb02-0000-0000-0000-000000000002'::uuid,
      ibps_exam_id;
  end if;
end $$;

insert into public.exam_cycles
  (id, exam_id, year, cycle_name, status, notification_date,
   application_start, application_end, exam_start, exam_end, source_url) values
  ('bbbbbb03-0000-0000-0000-000000000003', 'bbbbbb02-0000-0000-0000-000000000002',
   2026, 'IBPS PO 2026', 'upcoming', '2026-07-01', '2026-07-05', '2026-07-31',
   '2026-10-11', '2026-10-19', 'https://ibps.in/')
on conflict (id) do nothing;

insert into public.exam_phases
  (id, exam_id, exam_cycle_id, phase_name, phase_slug, phase_order, mode,
   duration_mins, total_questions, total_marks, negative_marking, status) values
  ('bbbbbb04-0000-0000-0000-000000000004', 'bbbbbb02-0000-0000-0000-000000000002',
   'bbbbbb03-0000-0000-0000-000000000003', 'Prelims', 'prelims', 1, 'cbt',
   60, 100, 100, '0.25 per wrong answer', 'expected')
on conflict (id) do nothing;

-- ── Booklist (exam_subject_resources) ────────────────────────────────────────
-- SSC CGL — Quantitative Aptitude
insert into public.exam_subject_resources
  (id, exam_id, exam_phase_id, subject_id, topic_id,
   resource_type, title, author, provider, url,
   priority_order, recommended_for, reviewer_status) values
  ('d0000001-0000-0000-0000-000000000001',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555551', null,
   'book', 'Quantitative Aptitude for Competitive Examinations',
   'R.S. Aggarwal', 'S. Chand', null,
   1, 'beginner', 'verified'),

  ('d0000002-0000-0000-0000-000000000002',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555551', null,
   'book', 'Fast Track Objective Arithmetic',
   'Rajesh Verma', 'Arihant', null,
   2, 'intermediate', 'verified'),

  -- SSC CGL — General Intelligence & Reasoning
  ('d0000003-0000-0000-0000-000000000003',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555553', null,
   'book', 'A Modern Approach to Verbal & Non-Verbal Reasoning',
   'R.S. Aggarwal', 'S. Chand', null,
   1, 'beginner', 'verified'),

  -- SSC CGL — English
  ('d0000004-0000-0000-0000-000000000004',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555552', null,
   'book', 'Objective General English',
   'S.P. Bakshi', 'Arihant', null,
   1, 'beginner', 'verified'),

  ('d0000005-0000-0000-0000-000000000005',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555552',
   '66666666-6666-6666-6666-666666666666',
   'book', 'Word Power Made Easy',
   'Norman Lewis', 'Pocket Books', null,
   2, 'intermediate', 'verified'),

  -- IBPS PO — Quantitative Aptitude
  ('d0000006-0000-0000-0000-000000000006',
   'bbbbbb02-0000-0000-0000-000000000002',
   'bbbbbb04-0000-0000-0000-000000000004',
   '55555555-5555-5555-5555-555555555551', null,
   'book', 'Data Interpretation & Data Sufficiency',
   'Ananta Ashisha', 'Arihant', null,
   1, 'intermediate', 'verified'),

  -- IBPS PO — English
  ('d0000007-0000-0000-0000-000000000007',
   'bbbbbb02-0000-0000-0000-000000000002',
   'bbbbbb04-0000-0000-0000-000000000004',
   '55555555-5555-5555-5555-555555555552', null,
   'book', 'High School English Grammar & Composition',
   'Wren & Martin', 'S. Chand', null,
   1, 'beginner', 'verified')
on conflict (id) do nothing;

-- ── Exam documents ────────────────────────────────────────────────────────────
insert into public.exam_documents
  (id, exam_id, exam_phase_id, doc_type, title, url, cycle_year,
   source_kind, reviewer_status) values
  ('e0000001-0000-0000-0000-000000000001',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   'syllabus', 'SSC CGL 2026 Tier 1 Official Syllabus',
   'https://ssc.gov.in/cgl-2026-syllabus.pdf',
   2026, 'manual', 'reviewed'),

  ('e0000002-0000-0000-0000-000000000002',
   '22222222-2222-2222-2222-222222222222',
   null,
   'notification', 'SSC CGL 2026 Official Notification',
   'https://ssc.gov.in/cgl-2026-notification.pdf',
   2026, 'manual', 'reviewed'),

  ('e0000003-0000-0000-0000-000000000003',
   'bbbbbb02-0000-0000-0000-000000000002',
   'bbbbbb04-0000-0000-0000-000000000004',
   'syllabus', 'IBPS PO 2026 Prelims Syllabus',
   'https://ibps.in/po-2026-syllabus.pdf',
   2026, 'manual', 'reviewed'),

  ('e0000004-0000-0000-0000-000000000004',
   'bbbbbb02-0000-0000-0000-000000000002',
   null,
   'notification', 'IBPS PO 2026 Official Notification',
   'https://ibps.in/po-2026-notification.pdf',
   2026, 'manual', 'reviewed')
on conflict (id) do nothing;

-- ── Community resources ───────────────────────────────────────────────────────
-- All rows: reviewer_status='verified', usable_for_mock_generation=false (gate not yet met).

-- Quant: Percentage — concept note + formula sheet
insert into public.community_resources
  (id, title, resource_type, exam, subject, source_url, source_trust,
   status, exam_id, exam_phase_id, subject_id, topic_id,
   reviewer_status, usable_for_mock_generation) values
  ('f0000001-0000-0000-0000-000000000001',
   'Percentage – Core Concepts & Shortcuts',
   'concept_note', 'SSC CGL', 'Quantitative Aptitude',
   'https://internal.ccp/resources/percentage-concepts',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'verified', false),

  ('f0000002-0000-0000-0000-000000000002',
   'Percentage – Formula Sheet',
   'formula_sheet', 'SSC CGL', 'Quantitative Aptitude',
   'https://internal.ccp/resources/percentage-formulas',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'verified', false),

  -- Quant: Ratio & Proportion
  ('f0000003-0000-0000-0000-000000000003',
   'Ratio & Proportion – Concept Note',
   'concept_note', 'SSC CGL', 'Quantitative Aptitude',
   'https://internal.ccp/resources/ratio-concepts',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555551',
   'cccccc01-0000-0000-0000-000000000001',
   'verified', false),

  -- Quant: Profit & Loss
  ('f0000004-0000-0000-0000-000000000004',
   'Profit & Loss – Formula Sheet',
   'formula_sheet', 'SSC CGL', 'Quantitative Aptitude',
   'https://internal.ccp/resources/profit-loss-formulas',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666662',
   'verified', false),

  -- Quant: Time & Work
  ('f0000005-0000-0000-0000-000000000005',
   'Time & Work – Drill Set (20 questions)',
   'drill_set', 'SSC CGL', 'Quantitative Aptitude',
   'https://internal.ccp/resources/time-work-drills',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666664',
   'verified', false),

  -- Reasoning: Syllogism
  ('f0000006-0000-0000-0000-000000000006',
   'Syllogism – Concept Note & Venn Diagram Approach',
   'concept_note', 'SSC CGL', 'General Intelligence & Reasoning',
   'https://internal.ccp/resources/syllogism-concepts',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555553',
   'cccccc02-0000-0000-0000-000000000002',
   'verified', false),

  -- Reasoning: Seating Arrangement
  ('f0000007-0000-0000-0000-000000000007',
   'Seating Arrangement – Linear & Circular Practice Set',
   'practice_set', 'SSC CGL', 'General Intelligence & Reasoning',
   'https://internal.ccp/resources/seating-arrangement-practice',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555553',
   'cccccc03-0000-0000-0000-000000000003',
   'verified', false),

  -- Reasoning: Blood Relation
  ('f0000008-0000-0000-0000-000000000008',
   'Blood Relation – Concept Note with Family Tree Method',
   'concept_note', 'SSC CGL', 'General Intelligence & Reasoning',
   'https://internal.ccp/resources/blood-relation-concepts',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555553',
   'cccccc04-0000-0000-0000-000000000004',
   'verified', false),

  -- English: Error Spotting
  ('f0000009-0000-0000-0000-000000000009',
   'Error Spotting – Grammar Rules Cheat Sheet',
   'grammar_sheet', 'SSC CGL', 'English Language',
   'https://internal.ccp/resources/error-spotting-grammar',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555552',
   'cccccc05-0000-0000-0000-000000000005',
   'verified', false),

  ('f000000a-0000-0000-0000-00000000000a',
   'Error Spotting – 30 Practice Sentences',
   'drill_set', 'SSC CGL', 'English Language',
   'https://internal.ccp/resources/error-spotting-drills',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555552',
   'cccccc05-0000-0000-0000-000000000005',
   'verified', false),

  -- English: Cloze Test
  ('f000000b-0000-0000-0000-00000000000b',
   'Cloze Test – Strategy Guide & 5 Practice Passages',
   'strategy_guide', 'SSC CGL', 'English Language',
   'https://internal.ccp/resources/cloze-test-strategy',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555552',
   'cccccc06-0000-0000-0000-000000000006',
   'verified', false),

  -- English: Vocabulary
  ('f000000c-0000-0000-0000-00000000000c',
   'High-Frequency Vocabulary for SSC CGL',
   'vocabulary_sheet', 'SSC CGL', 'English Language',
   'https://internal.ccp/resources/ssc-cgl-vocabulary',
   'coaching', 'approved',
   '22222222-2222-2222-2222-222222222222',
   '44444444-4444-4444-4444-444444444441',
   '55555555-5555-5555-5555-555555555552',
   '66666666-6666-6666-6666-666666666666',
   'verified', false),

  -- Current Affairs: PIB Weekly Digest (2026-W21)
  ('f000000d-0000-0000-0000-00000000000d',
   'PIB Weekly Digest — Week 21, 2026 (19–25 May)',
   'current_affairs_digest', 'SSC CGL', 'General Awareness',
   'https://pib.gov.in/digest/week21-2026',
   'official', 'approved',
   '22222222-2222-2222-2222-222222222222',
   null, null, null,
   'verified', false),

  -- Current Affairs: PIB Weekly Digest (2026-W20)
  ('f000000e-0000-0000-0000-00000000000e',
   'PIB Weekly Digest — Week 20, 2026 (12–18 May)',
   'current_affairs_digest', 'SSC CGL', 'General Awareness',
   'https://pib.gov.in/digest/week20-2026',
   'official', 'approved',
   '22222222-2222-2222-2222-222222222222',
   null, null, null,
   'verified', false),

  -- Current Affairs: PIB Weekly Digest (2026-W19)
  ('f000000f-0000-0000-0000-00000000000f',
   'PIB Weekly Digest — Week 19, 2026 (5–11 May)',
   'current_affairs_digest', 'SSC CGL', 'General Awareness',
   'https://pib.gov.in/digest/week19-2026',
   'official', 'approved',
   '22222222-2222-2222-2222-222222222222',
   null, null, null,
   'verified', false),

  -- Current Affairs: Scheme Cards
  ('f0000010-0000-0000-0000-000000000010',
   'PM Vishwakarma Yojana — Scheme Card',
   'scheme_card', 'SSC CGL', 'General Awareness',
   'https://pmvishwakarma.gov.in/scheme-card',
   'official', 'approved',
   '22222222-2222-2222-2222-222222222222',
   null, null, null,
   'verified', false),

  ('f0000011-0000-0000-0000-000000000011',
   'PM Surya Ghar Muft Bijli Yojana — Scheme Card',
   'scheme_card', 'SSC CGL', 'General Awareness',
   'https://pmsuryaghar.gov.in/scheme-card',
   'official', 'approved',
   '22222222-2222-2222-2222-222222222222',
   null, null, null,
   'verified', false),

  ('f0000012-0000-0000-0000-000000000012',
   'Ayushman Bharat PM-JAY — Scheme Card',
   'scheme_card', 'SSC CGL', 'General Awareness',
   'https://pmjay.gov.in/scheme-card',
   'official', 'approved',
   '22222222-2222-2222-2222-222222222222',
   null, null, null,
   'verified', false),

  -- Banking: IBPS PO — Quant formula sheet (cross-exam resource)
  ('f0000013-0000-0000-0000-000000000013',
   'IBPS PO Quant – Number Series & Simplification Formula Sheet',
   'formula_sheet', 'IBPS PO', 'Quantitative Aptitude',
   'https://internal.ccp/resources/ibps-po-quant-formulas',
   'coaching', 'approved',
   'bbbbbb02-0000-0000-0000-000000000002',
   'bbbbbb04-0000-0000-0000-000000000004',
   '55555555-5555-5555-5555-555555555551', null,
   'verified', false),

  -- Banking: IBPS PO — Reasoning concept note
  ('f0000014-0000-0000-0000-000000000014',
   'IBPS PO Reasoning – Puzzle & Seating Arrangement Guide',
   'concept_note', 'IBPS PO', 'General Intelligence & Reasoning',
   'https://internal.ccp/resources/ibps-po-reasoning',
   'coaching', 'approved',
   'bbbbbb02-0000-0000-0000-000000000002',
   'bbbbbb04-0000-0000-0000-000000000004',
   '55555555-5555-5555-5555-555555555553',
   'cccccc03-0000-0000-0000-000000000003',
   'verified', false),

  -- Banking: IBPS PO — English grammar sheet
  ('f0000015-0000-0000-0000-000000000015',
   'IBPS PO English – Error Detection & Cloze Passage Sheet',
   'grammar_sheet', 'IBPS PO', 'English Language',
   'https://internal.ccp/resources/ibps-po-english',
   'coaching', 'approved',
   'bbbbbb02-0000-0000-0000-000000000002',
   'bbbbbb04-0000-0000-0000-000000000004',
   '55555555-5555-5555-5555-555555555552', null,
   'verified', false),

  -- Banking: PIB Weekly Digest (shared with SSC CGL vertical)
  ('f0000016-0000-0000-0000-000000000016',
   'PIB Weekly Digest — Week 21, 2026 (19–25 May)',
   'current_affairs_digest', 'IBPS PO', 'General Awareness',
   'https://pib.gov.in/digest/week21-2026',
   'official', 'approved',
   'bbbbbb02-0000-0000-0000-000000000002',
   null, null, null,
   'verified', false)
on conflict (id) do nothing;

-- ── Pilot mock_question_bank (30 Quant questions, reviewer_status='verified') ─
-- These are the first 30 of the 200 required to unlock full mock expansion.
-- usable_for_mock_generation is a community_resources column; here we simply
-- ensure reviewer_status stays 'verified' (not 'live') until the gate is met.

insert into public.mock_question_bank
  (id, exam_id, subject_id, topic_id,
   question_text, question_type, difficulty,
   marks, negative_marks, language, source_type,
   reviewer_status, expected_time_sec,
   is_conceptual, is_factual) values

  -- Percentage (10 questions)
  ('b1000001-0000-0000-0000-000000000001',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'A number is increased by 20% and then decreased by 20%. The net percentage change is:',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 45, true, false),

  ('b1000002-0000-0000-0000-000000000002',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'If 30% of a number is 90, what is 60% of the same number?',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 40, true, false),

  ('b1000003-0000-0000-0000-000000000003',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'A student scored 72 marks out of 90. What is the percentage score?',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 35, true, false),

  ('b1000004-0000-0000-0000-000000000004',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'Price of an item increased from Rs 200 to Rs 250. What is the percentage increase?',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 40, true, false),

  ('b1000005-0000-0000-0000-000000000005',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'What number is 15% more than 80?',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 35, true, false),

  ('b1000006-0000-0000-0000-000000000006',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'A town''s population grew by 10% in year 1 and 10% in year 2. What is the net percentage increase?',
   'mcq', 'medium', 2, 0.5, 'en', 'admin_authored', 'verified', 50, true, false),

  ('b1000007-0000-0000-0000-000000000007',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   '40 is what percent of 160?',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 30, true, false),

  ('b1000008-0000-0000-0000-000000000008',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'A salary of Rs 12,000 is reduced by 15%. Find the new salary.',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 40, true, false),

  ('b1000009-0000-0000-0000-000000000009',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'If x% of y equals y% of z, then z equals:',
   'mcq', 'medium', 2, 0.5, 'en', 'admin_authored', 'verified', 55, true, false),

  ('b100000a-0000-0000-0000-00000000000a',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'A number when increased by 25% gives 100. Find the original number.',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 40, true, false),

  -- Ratio & Proportion (5 questions)
  ('b100000b-0000-0000-0000-00000000000b',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   'cccccc01-0000-0000-0000-000000000001',
   'If A : B = 3 : 4 and B : C = 5 : 6, find A : C.',
   'mcq', 'medium', 2, 0.5, 'en', 'admin_authored', 'verified', 60, true, false),

  ('b100000c-0000-0000-0000-00000000000c',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   'cccccc01-0000-0000-0000-000000000001',
   'Divide Rs 1200 among A, B, and C in the ratio 3 : 4 : 5. Find A''s share.',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 45, true, false),

  ('b100000d-0000-0000-0000-00000000000d',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   'cccccc01-0000-0000-0000-000000000001',
   'The ratio of boys to girls in a class is 7 : 5. If there are 36 students, how many are boys?',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 40, true, false),

  ('b100000e-0000-0000-0000-00000000000e',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   'cccccc01-0000-0000-0000-000000000001',
   'Two numbers are in ratio 5 : 8. If their sum is 117, find the larger number.',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 45, true, false),

  ('b100000f-0000-0000-0000-00000000000f',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   'cccccc01-0000-0000-0000-000000000001',
   'If 4 : 5 :: x : 35, find x.',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 35, true, false),

  -- Profit & Loss (5 questions)
  ('b1000010-0000-0000-0000-000000000010',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666662',
   'An article is bought for Rs 400 and sold for Rs 480. Find the profit percent.',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 40, true, false),

  ('b1000011-0000-0000-0000-000000000011',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666662',
   'Two successive discounts of 10% and 20% are equivalent to a single discount of:',
   'mcq', 'medium', 2, 0.5, 'en', 'admin_authored', 'verified', 55, true, false),

  ('b1000012-0000-0000-0000-000000000012',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666662',
   'A shopkeeper marks his goods 40% above cost and allows a 15% discount. Find the profit percent.',
   'mcq', 'medium', 2, 0.5, 'en', 'admin_authored', 'verified', 65, true, false),

  ('b1000013-0000-0000-0000-000000000013',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666662',
   'An article sold at Rs 680 incurs a loss of 15%. Find the cost price.',
   'mcq', 'medium', 2, 0.5, 'en', 'admin_authored', 'verified', 55, true, false),

  ('b1000014-0000-0000-0000-000000000014',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666662',
   'A trader cheats by using a 900g weight for 1 kg. What is the profit percent?',
   'mcq', 'hard', 2, 0.5, 'en', 'admin_authored', 'verified', 70, true, false),

  -- Time & Work (5 questions)
  ('b1000015-0000-0000-0000-000000000015',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666664',
   'A can do a piece of work in 12 days, B in 18 days. Together, in how many days?',
   'mcq', 'easy', 2, 0.5, 'en', 'admin_authored', 'verified', 50, true, false),

  ('b1000016-0000-0000-0000-000000000016',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666664',
   'A and B together can complete work in 8 days; A alone takes 12 days. How long does B take alone?',
   'mcq', 'medium', 2, 0.5, 'en', 'admin_authored', 'verified', 55, true, false),

  ('b1000017-0000-0000-0000-000000000017',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666664',
   '15 workers can complete a job in 10 days. How many workers are needed to finish in 6 days?',
   'mcq', 'medium', 2, 0.5, 'en', 'admin_authored', 'verified', 50, true, false),

  ('b1000018-0000-0000-0000-000000000018',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666664',
   'A tap fills a tank in 6 hours; another empties it in 8 hours. If both open together, in how long is the tank filled?',
   'mcq', 'hard', 2, 0.5, 'en', 'admin_authored', 'verified', 70, true, false),

  ('b1000019-0000-0000-0000-000000000019',
   '22222222-2222-2222-2222-222222222222',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666664',
   'A alone can do a work in 15 days and B alone in 20 days. They work together for 4 days, then A leaves. In how many more days will B finish?',
   'mcq', 'hard', 2, 0.5, 'en', 'admin_authored', 'verified', 80, true, false),

  -- Banking Quant (IBPS PO, 5 questions)
  ('b100001a-0000-0000-0000-00000000001a',
   'bbbbbb02-0000-0000-0000-000000000002',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'Simple interest on Rs 5,000 at 8% p.a. for 3 years is:',
   'mcq', 'easy', 1, 0.25, 'en', 'admin_authored', 'verified', 40, true, false),

  ('b100001b-0000-0000-0000-00000000001b',
   'bbbbbb02-0000-0000-0000-000000000002',
   '55555555-5555-5555-5555-555555555551',
   'cccccc01-0000-0000-0000-000000000001',
   'A sum of Rs 2,400 is divided in ratio 3 : 5. Find the larger part.',
   'mcq', 'easy', 1, 0.25, 'en', 'admin_authored', 'verified', 40, true, false),

  ('b100001c-0000-0000-0000-00000000001c',
   'bbbbbb02-0000-0000-0000-000000000002',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666662',
   'A book is sold at a 20% profit on cost price of Rs 250. Find the selling price.',
   'mcq', 'easy', 1, 0.25, 'en', 'admin_authored', 'verified', 40, true, false),

  ('b100001d-0000-0000-0000-00000000001d',
   'bbbbbb02-0000-0000-0000-000000000002',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666664',
   'X can do a task in 20 days and Y in 30 days. They work together for 5 days, then X leaves. Find the total days to complete.',
   'mcq', 'hard', 1, 0.25, 'en', 'admin_authored', 'verified', 80, true, false),

  ('b100001e-0000-0000-0000-00000000001e',
   'bbbbbb02-0000-0000-0000-000000000002',
   '55555555-5555-5555-5555-555555555551',
   '66666666-6666-6666-6666-666666666661',
   'In a class, 35% of students passed in Maths, 40% in English, and 15% in both. What percent failed in both?',
   'mcq', 'medium', 1, 0.25, 'en', 'admin_authored', 'verified', 65, true, false)
on conflict (id) do nothing;

commit;
