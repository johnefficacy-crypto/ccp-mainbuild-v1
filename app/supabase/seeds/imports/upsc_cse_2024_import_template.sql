-- =============================================================================
-- UPSC CSE 2024 — Production-safe import template
-- =============================================================================
--
-- HARD RULES (read before editing):
--   1. Replace every <placeholder> with a real, verified value before applying.
--   2. Do NOT fabricate official URLs, notification dates, vacancy counts,
--      cutoffs, PYQ question text, or answer keys.
--   3. All rows default to draft/pending trust states. Never set reviewer_status
--      to 'verified' or 'locked' in this file — promote via PATCH after review.
--   4. exam_topic_coverage.reviewer_status MUST be 'pending_review' (not
--      'pending', not 'verified', not 'locked'). Constraint is in migration 030.
--   5. exam_policy_updates: affects_* flags must all be false here. Only
--      source_type='official' AND reviewer_status='verified' may carry
--      affects_* = true, and only via PATCH after explicit reviewer approval.
--   6. This file is idempotent: all inserts use ON CONFLICT (id) DO NOTHING
--      with explicit UUIDs so re-runs are safe.
--   7. Do not edit the demo seed (exam_intelligence_demo_upsc_cse.sql).
--      That file is for local/dev exercise only.
--
-- UUID INSTRUCTIONS:
--   Generate one stable UUID per entity with: python3 -c "import uuid; print(uuid.uuid4())"
--   or psql: select gen_random_uuid();
--   Write the chosen UUIDs into the placeholders below and keep a local record.
--
-- INSERT ORDER (foreign key dependency order — do not reorder):
--   1  exam_families            9  exam_phase_sections
--   2  exams                   10  syllabus_documents
--   3  exam_cycles             11  syllabus_topic_mentions
--   4  exam_phases             12  pyq_sources
--   5  subjects                13  pyq_papers
--   6  topics                  14  pyq_questions
--   7  topic_aliases           15  pyq_options
--   8  topic_prerequisites     16  pyq_question_topic_tags
--                              17  exam_topic_coverage
--                              18  exam_competition_metrics
--                              19  exam_policy_updates
-- =============================================================================

begin;

-- ---------------------------------------------------------------------------
-- 1. exam_families
-- ---------------------------------------------------------------------------
insert into public.exam_families (id, slug, name, description)
values (
  '<upsc-family-uuid>',                -- replace with generated UUID
  'upsc',
  'Union Public Service Commission',
  'Central government examinations conducted by UPSC'
)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 2. exams
-- ---------------------------------------------------------------------------
-- exam_type CHECK enforces ('recruitment','academic','certification','entrance',
-- 'competitive','other') — see migration for current list.
insert into public.exams (
  id, exam_family_id, slug, name, exam_type,
  default_difficulty_level, description, is_active
) values (
  '<upsc-cse-exam-uuid>',              -- replace with generated UUID
  '<upsc-family-uuid>',
  'upsc-cse',
  'UPSC Civil Services Examination',
  'recruitment',
  'hard',
  'Three-stage competitive examination for central civil services and IAS/IPS/IFS cadres.',
  true                                 -- set false until all stages are reviewed
)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 3. exam_cycles
-- ---------------------------------------------------------------------------
-- status CHECK: 'expected','open','active','closed','completed','cancelled'
-- All date fields and source_url MUST come from the official UPSC notification.
-- Do NOT fabricate dates — leave as placeholder until you have the source URL.
insert into public.exam_cycles (
  id, exam_id, year, cycle_name, status,
  notification_date, application_start, application_end,
  exam_start, exam_end, source_url
) values (
  '<upsc-cse-2024-cycle-uuid>',        -- replace with generated UUID
  '<upsc-cse-exam-uuid>',
  2024,
  'UPSC CSE 2024',
  'expected',                          -- promote after confirming official status
  '<YYYY-MM-DD>',                      -- official notification date from upsc.gov.in
  '<YYYY-MM-DD>',                      -- application window start
  '<YYYY-MM-DD>',                      -- application window end
  '<YYYY-MM-DD>',                      -- Prelims date (GS Paper I)
  '<YYYY-MM-DD>',                      -- Mains/Interview end date (estimated if not yet announced)
  '<https://upsc.gov.in/...>'          -- MUST be the official UPSC notification URL
)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 4. exam_phases
-- ---------------------------------------------------------------------------
-- UPSC CSE has three stages: Prelims, Mains, Interview (Personality Test).
-- Add one row per stage. mode CHECK: 'cbt','pen_paper','oral','practical','hybrid'
-- negative_marking is a text note field (no numeric constraint).

-- Phase 1: Preliminary Examination
insert into public.exam_phases (
  id, exam_id, exam_cycle_id, phase_name, phase_slug, phase_order,
  mode, duration_mins, total_questions, total_marks, negative_marking, status
) values (
  '<upsc-cse-2024-prelims-uuid>',      -- replace with generated UUID
  '<upsc-cse-exam-uuid>',
  '<upsc-cse-2024-cycle-uuid>',
  'Preliminary Examination',
  'prelims',
  1,
  'pen_paper',
  120,                                 -- GS Paper I: 2 hours; CSAT also 2 hours
  100,                                 -- GS Paper I question count (verify from official)
  200,                                 -- GS Paper I total marks (verify from official)
  '1/3 negative marking per wrong answer (verify from official notification)',
  'expected'
)
on conflict (id) do nothing;

-- Phase 2: Main Examination (add remaining Mains papers as needed)
insert into public.exam_phases (
  id, exam_id, exam_cycle_id, phase_name, phase_slug, phase_order,
  mode, duration_mins, total_questions, total_marks, negative_marking, status
) values (
  '<upsc-cse-2024-mains-uuid>',        -- replace with generated UUID
  '<upsc-cse-exam-uuid>',
  '<upsc-cse-2024-cycle-uuid>',
  'Main Examination',
  'mains',
  2,
  'pen_paper',
  180,                                 -- per GS paper (3 hours); verify per paper
  null,                                -- descriptive papers; not MCQ count
  1750,                                -- GS I–IV total (verify from official)
  'No negative marking in Mains (verify from official notification)',
  'expected'
)
on conflict (id) do nothing;

-- Phase 3: Personality Test (Interview)
insert into public.exam_phases (
  id, exam_id, exam_cycle_id, phase_name, phase_slug, phase_order,
  mode, duration_mins, total_questions, total_marks, negative_marking, status
) values (
  '<upsc-cse-2024-interview-uuid>',    -- replace with generated UUID
  '<upsc-cse-exam-uuid>',
  '<upsc-cse-2024-cycle-uuid>',
  'Personality Test',
  'interview',
  3,
  'oral',
  null,
  null,
  275,                                 -- verify from official notification
  'No negative marking',
  'expected'
)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 5. subjects
-- ---------------------------------------------------------------------------
-- Add one row per broad subject area. Extend as needed for your taxonomy.
-- subject_group has no DB CHECK — use a consistent controlled vocabulary.

insert into public.subjects (id, slug, name, subject_group, default_difficulty_level, is_active) values
  ('<subj-history-uuid>',       'history',          'History',                    'humanities',  'medium', true),
  ('<subj-geography-uuid>',     'geography',         'Geography',                  'social',      'medium', true),
  ('<subj-polity-uuid>',        'polity',            'Polity & Governance',        'social',      'medium', true),
  ('<subj-economy-uuid>',       'economy',           'Economy',                    'social',      'medium', true),
  ('<subj-environment-uuid>',   'environment',       'Environment & Ecology',      'science',     'medium', true),
  ('<subj-science-uuid>',       'general-science',   'General Science & Tech',     'science',     'medium', true),
  ('<subj-current-uuid>',       'current-affairs',   'Current Affairs',            'current',     'medium', true),
  ('<subj-csat-uuid>',          'csat',              'CSAT (Civil Services Aptitude Test)', 'aptitude', 'medium', true)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 6. topics
-- ---------------------------------------------------------------------------
-- Only a representative sample is shown. Add all topics from the official
-- UPSC syllabus document before running in production.
-- level CHECK: 'topic','microtopic','concept'

insert into public.topics (id, subject_id, slug, name, level, default_difficulty_level, is_active) values
  ('<topic-ancient-history-uuid>',  '<subj-history-uuid>',    'ancient-history',          'Ancient History',              'topic', 'medium', true),
  ('<topic-medieval-history-uuid>', '<subj-history-uuid>',    'medieval-history',         'Medieval History',             'topic', 'medium', true),
  ('<topic-modern-history-uuid>',   '<subj-history-uuid>',    'modern-history',           'Modern History',               'topic', 'medium', true),
  ('<topic-physical-geo-uuid>',     '<subj-geography-uuid>',  'physical-geography',       'Physical Geography',           'topic', 'medium', true),
  ('<topic-indian-geo-uuid>',       '<subj-geography-uuid>',  'indian-geography',         'Indian Geography',             'topic', 'medium', true),
  ('<topic-constitution-uuid>',     '<subj-polity-uuid>',     'constitution',             'Indian Constitution',          'topic', 'medium', true),
  ('<topic-parliament-uuid>',       '<subj-polity-uuid>',     'parliament',               'Parliament & Legislatures',    'topic', 'medium', true),
  ('<topic-indian-economy-uuid>',   '<subj-economy-uuid>',    'indian-economy',           'Indian Economy',               'topic', 'medium', true),
  ('<topic-biodiversity-uuid>',     '<subj-environment-uuid>','biodiversity',             'Biodiversity',                 'topic', 'medium', true),
  ('<topic-climate-uuid>',          '<subj-environment-uuid>','climate-change',           'Climate Change',               'topic', 'medium', true),
  ('<topic-space-uuid>',            '<subj-science-uuid>',    'space-technology',         'Space Technology',             'topic', 'medium', true),
  ('<topic-comprehension-uuid>',    '<subj-csat-uuid>',       'comprehension',            'Comprehension',                'topic', 'medium', true),
  ('<topic-logical-reasoning-uuid>','<subj-csat-uuid>',       'logical-reasoning',        'Logical Reasoning',            'topic', 'medium', true)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 7. topic_aliases
-- ---------------------------------------------------------------------------
insert into public.topic_aliases (id, topic_id, alias, normalized_alias, source_context) values
  ('<alias-art-culture-uuid>',  '<topic-ancient-history-uuid>',  'Art and Culture',           'art and culture',           'upsc_syllabus'),
  ('<alias-freedom-uuid>',      '<topic-modern-history-uuid>',   'Freedom Struggle',          'freedom struggle',          'upsc_syllabus'),
  ('<alias-preamble-uuid>',     '<topic-constitution-uuid>',     'Preamble',                  'preamble',                  'upsc_syllabus'),
  ('<alias-env-bio-uuid>',      '<topic-biodiversity-uuid>',     'Environment and Ecology',   'environment and ecology',   'upsc_syllabus')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 8. topic_prerequisites
-- ---------------------------------------------------------------------------
-- relation_type CHECK: 'requires','recommended_before','supports','foundation_for'
insert into public.topic_prerequisites (
  id, topic_id, prerequisite_topic_id, relation_type, strength, source_basis, metadata
) values (
  '<prereq-modern-needs-medieval-uuid>',
  '<topic-modern-history-uuid>',
  '<topic-medieval-history-uuid>',
  'recommended_before',
  0.6,
  'admin_review',
  '{"notes": "Medieval context aids understanding of pre-colonial transition — admin judgment"}'::jsonb
)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 9. exam_phase_sections
-- ---------------------------------------------------------------------------
-- One section per subject area within a phase. Weightage from official syllabus only.
insert into public.exam_phase_sections (
  id, exam_phase_id, subject_id, section_label, question_count, marks, weightage_percent, sort_order
) values
  ('<sect-prelims-gs1-uuid>',     '<upsc-cse-2024-prelims-uuid>',  '<subj-history-uuid>',    'History (GS Paper I)',         '<count>', '<marks>', null, 1),
  ('<sect-prelims-gs-geo-uuid>',  '<upsc-cse-2024-prelims-uuid>',  '<subj-geography-uuid>',  'Geography (GS Paper I)',       '<count>', '<marks>', null, 2),
  ('<sect-prelims-gs-pol-uuid>',  '<upsc-cse-2024-prelims-uuid>',  '<subj-polity-uuid>',     'Polity (GS Paper I)',          '<count>', '<marks>', null, 3),
  ('<sect-prelims-gs-eco-uuid>',  '<upsc-cse-2024-prelims-uuid>',  '<subj-economy-uuid>',    'Economy (GS Paper I)',         '<count>', '<marks>', null, 4),
  ('<sect-prelims-gs-env-uuid>',  '<upsc-cse-2024-prelims-uuid>',  '<subj-environment-uuid>','Environment (GS Paper I)',     '<count>', '<marks>', null, 5),
  ('<sect-prelims-gs-sci-uuid>',  '<upsc-cse-2024-prelims-uuid>',  '<subj-science-uuid>',    'Science & Tech (GS Paper I)', '<count>', '<marks>', null, 6),
  ('<sect-prelims-gs-cur-uuid>',  '<upsc-cse-2024-prelims-uuid>',  '<subj-current-uuid>',    'Current Affairs (GS Paper I)','<count>', '<marks>', null, 7),
  ('<sect-prelims-csat-uuid>',    '<upsc-cse-2024-prelims-uuid>',  '<subj-csat-uuid>',       'CSAT (GS Paper II)',           '<count>', '<marks>', null, 8)
-- Replace <count> and <marks> with values from the official notification only.
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 10. syllabus_documents
-- ---------------------------------------------------------------------------
-- trust_status has no DB CHECK in migration 031 — use consistent vocabulary.
-- source_url MUST point to the official upsc.gov.in syllabus PDF.
insert into public.syllabus_documents (
  id, exam_id, exam_cycle_id, document_type, title, source_url,
  trust_status, published_at, metadata
) values (
  '<upsc-cse-2024-syllabus-doc-uuid>',
  '<upsc-cse-exam-uuid>',
  '<upsc-cse-2024-cycle-uuid>',
  'syllabus_pdf',
  'UPSC CSE 2024 Official Syllabus',
  '<https://upsc.gov.in/...>',         -- official UPSC syllabus URL; do NOT fabricate
  'pending',
  '<ISO-8601 published timestamp>',
  '{
    "fetched_at":    "<ISO-8601>",
    "content_hash":  "<sha256 of downloaded PDF or null>",
    "review_notes":  "Replace with: fetcher name, date verified, hash confirmed"
  }'::jsonb
)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 11. syllabus_topic_mentions
-- ---------------------------------------------------------------------------
-- reviewer_status has no DB CHECK in migration 031 — keep 'pending'.
-- raw_text MUST be a verbatim fragment from the syllabus document above.
-- Do not paraphrase or invent mention text.
-- Extend with one row per topic–document pair found in the official syllabus.

insert into public.syllabus_topic_mentions (
  id, syllabus_document_id, exam_id, exam_cycle_id, exam_phase_id, topic_id,
  raw_text, normalized_text, mention_type, confidence_score,
  reviewer_status, reviewed_at, reviewer_notes
) values
  (
    '<mention-ancient-history-uuid>',
    '<upsc-cse-2024-syllabus-doc-uuid>',
    '<upsc-cse-exam-uuid>',
    '<upsc-cse-2024-cycle-uuid>',
    '<upsc-cse-2024-prelims-uuid>',
    '<topic-ancient-history-uuid>',
    '<verbatim text from syllabus PDF>',   -- copy exact phrase; do NOT paraphrase
    '<normalized version>',
    'explicit',
    0.85,
    'pending', null,
    '<Reviewer: cite page/section in syllabus doc>'
  ),
  (
    '<mention-constitution-uuid>',
    '<upsc-cse-2024-syllabus-doc-uuid>',
    '<upsc-cse-exam-uuid>',
    '<upsc-cse-2024-cycle-uuid>',
    '<upsc-cse-2024-prelims-uuid>',
    '<topic-constitution-uuid>',
    '<verbatim text from syllabus PDF>',
    '<normalized version>',
    'explicit',
    0.9,
    'pending', null,
    '<Reviewer: cite page/section in syllabus doc>'
  )
-- Add one row per topic mentioned in the official syllabus.
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 12. pyq_sources
-- ---------------------------------------------------------------------------
-- source_type CHECK: 'official','memory_based','coaching','community','aggregator','unknown'
-- trust_status: no DB CHECK — use consistent vocabulary.
-- source_url MUST be official UPSC or a clearly identified PYQ repository.
-- Do not create rows for question text you cannot cite to a verified source.
insert into public.pyq_sources (
  id, exam_id, source_type, source_url, title, trust_status, metadata
) values (
  '<upsc-cse-pyq-source-uuid>',
  '<upsc-cse-exam-uuid>',
  'official',
  '<https://upsc.gov.in/...>',         -- official UPSC PYQ or question paper URL
  'UPSC CSE Official Question Papers',
  'pending',
  '{
    "fetched_at":   "<ISO-8601>",
    "review_notes": "Reviewer must confirm URL resolves to official question papers"
  }'::jsonb
)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 13. pyq_papers
-- ---------------------------------------------------------------------------
-- source_type CHECK: same as pyq_sources above.
-- Insert one row per paper per year. 2024 Prelims GS Paper I shown as example.
insert into public.pyq_papers (
  id, pyq_source_id, exam_id, exam_phase_id, year, paper_date, shift,
  source_type, trust_status, metadata
) values (
  '<upsc-cse-2024-prelims-gs1-paper-uuid>',
  '<upsc-cse-pyq-source-uuid>',
  '<upsc-cse-exam-uuid>',
  '<upsc-cse-2024-prelims-uuid>',
  2024,
  '<YYYY-MM-DD>',                      -- official Prelims date; do NOT fabricate
  'Morning',                           -- verify shift from official schedule
  'official',
  'pending',
  '{"notes": "Pending official verification"}'::jsonb
)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 14. pyq_questions
-- ---------------------------------------------------------------------------
-- Do NOT add question rows until you have a verified source for the question text.
-- question_type CHECK: 'mcq','numerical','descriptive','caselet','matching','other'
-- reviewer_status CHECK: 'pending','verified','rejected','needs_correction' — migration 032.
-- Review notes ride on metadata.jsonb (no review_notes column on this table).
--
-- EXAMPLE ROW (commented out — uncomment only when you have a verified source):
--
-- insert into public.pyq_questions (
--   id, pyq_paper_id, question_number, question_text, question_type,
--   observed_difficulty, expected_solve_time_sec, reviewer_status, metadata
-- ) values (
--   '<pyq-q1-uuid>',
--   '<upsc-cse-2024-prelims-gs1-paper-uuid>',
--   1,
--   '<Exact question text copied from verified official source>',
--   'mcq',
--   'moderate',
--   90,
--   'pending',
--   '{"review_notes": "<Source: page X of official paper; verified by <name> on <date>>"}'::jsonb
-- )
-- on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 15. pyq_options
-- ---------------------------------------------------------------------------
-- Add options ONLY when the corresponding pyq_question row is inserted.
-- is_correct MUST come from the official UPSC answer key — never guess.
-- Option provenance rides on metadata.jsonb (no source_basis column — migration 032).
--
-- EXAMPLE (commented out — uncomment with question row above):
--
-- insert into public.pyq_options (id, question_id, option_label, option_text, is_correct, metadata) values
--   ('<opt-a-uuid>', '<pyq-q1-uuid>', 'A', '<Option A text>', false, '{"source_basis":"official_answer_key"}'::jsonb),
--   ('<opt-b-uuid>', '<pyq-q1-uuid>', 'B', '<Option B text>', false, '{"source_basis":"official_answer_key"}'::jsonb),
--   ('<opt-c-uuid>', '<pyq-q1-uuid>', 'C', '<Option C text>', true,  '{"source_basis":"official_answer_key"}'::jsonb),
--   ('<opt-d-uuid>', '<pyq-q1-uuid>', 'D', '<Option D text>', false, '{"source_basis":"official_answer_key"}'::jsonb)
-- on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 16. pyq_question_topic_tags
-- ---------------------------------------------------------------------------
-- Add tags ONLY when the question row exists and the topic mapping is verified.
-- tag_role CHECK: 'primary','secondary','prerequisite','trap','calculation_layer','conceptual_layer'
-- tagging_source CHECK: 'manual','admin','ai','rule','imported'
-- reviewer_status CHECK: 'pending','verified','rejected','needs_correction' — migration 032.
-- Mapping evidence rides on metadata.jsonb (no review_notes column — migration 032).
--
-- EXAMPLE (commented out — uncomment with question rows above):
--
-- insert into public.pyq_question_topic_tags (
--   id, question_id, topic_id, tag_weight, tag_role, tagging_source,
--   confidence_score, reviewer_status, reviewed_at, metadata
-- ) values (
--   '<tag-q1-uuid>',
--   '<pyq-q1-uuid>',
--   '<topic-constitution-uuid>',
--   1.0, 'primary', 'admin', 0.8, 'pending', null,
--   '{"review_notes": "<Mapping rationale; reviewer name + date>"}'::jsonb
-- )
-- on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 17. exam_topic_coverage
-- ---------------------------------------------------------------------------
-- reviewer_status CHECK (migration 030):
--   'draft' | 'pending_review' | 'reviewed' | 'locked' | 'rejected'
-- Use 'pending_review' here. DO NOT use 'pending' (wrong lifecycle) or 'locked'.
-- Promote to 'reviewed' → 'locked' only after reviewer confirms evidence chain.
-- review_notes (not reviewer_notes) — see migration 030 column name note in runbook.
-- source_basis CHECK: 'official_syllabus','pyq_analysis','admin_review','hybrid','manual','model_generated'

insert into public.exam_topic_coverage (
  id, exam_id, exam_cycle_id, exam_phase_id, topic_id,
  coverage_depth, expected_difficulty, exam_priority_score,
  is_high_yield, confidence_score, source_basis,
  reviewer_status, reviewed_at, review_notes
) values
  (
    '<cov-ancient-history-uuid>',
    '<upsc-cse-exam-uuid>', '<upsc-cse-2024-cycle-uuid>', '<upsc-cse-2024-prelims-uuid>',
    '<topic-ancient-history-uuid>',
    'normal', 'medium', 60, true, 0.7,
    'official_syllabus',
    'pending_review', null,           -- DO NOT change to 'locked' here
    '<Reviewer: cite syllabus section; confirm PYQ evidence if available>'
  ),
  (
    '<cov-modern-history-uuid>',
    '<upsc-cse-exam-uuid>', '<upsc-cse-2024-cycle-uuid>', '<upsc-cse-2024-prelims-uuid>',
    '<topic-modern-history-uuid>',
    'deep', 'medium', 75, true, 0.75,
    'official_syllabus',
    'pending_review', null,
    '<Reviewer: cite syllabus section; confirm PYQ evidence if available>'
  ),
  (
    '<cov-constitution-uuid>',
    '<upsc-cse-exam-uuid>', '<upsc-cse-2024-cycle-uuid>', '<upsc-cse-2024-prelims-uuid>',
    '<topic-constitution-uuid>',
    'core', 'medium', 85, true, 0.8,
    'official_syllabus',
    'pending_review', null,
    '<Reviewer: cite syllabus section; confirm PYQ evidence if available>'
  ),
  (
    '<cov-geography-uuid>',
    '<upsc-cse-exam-uuid>', '<upsc-cse-2024-cycle-uuid>', '<upsc-cse-2024-prelims-uuid>',
    '<topic-indian-geo-uuid>',
    'normal', 'medium', 65, true, 0.7,
    'official_syllabus',
    'pending_review', null,
    '<Reviewer: cite syllabus section>'
  ),
  (
    '<cov-economy-uuid>',
    '<upsc-cse-exam-uuid>', '<upsc-cse-2024-cycle-uuid>', '<upsc-cse-2024-prelims-uuid>',
    '<topic-indian-economy-uuid>',
    'deep', 'hard', 80, true, 0.75,
    'official_syllabus',
    'pending_review', null,
    '<Reviewer: cite syllabus section>'
  ),
  (
    '<cov-environment-uuid>',
    '<upsc-cse-exam-uuid>', '<upsc-cse-2024-cycle-uuid>', '<upsc-cse-2024-prelims-uuid>',
    '<topic-biodiversity-uuid>',
    'normal', 'medium', 65, true, 0.7,
    'official_syllabus',
    'pending_review', null,
    '<Reviewer: cite syllabus section>'
  )
-- Add one row per topic per phase. Extend for Mains phases using their phase UUID.
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 18. exam_competition_metrics
-- ---------------------------------------------------------------------------
-- reviewer_status CHECK (migration 055): 'draft','pending_review','reviewed','locked','rejected'
-- source_basis CHECK: 'manual','official','reviewed_analysis','derived','model_generated'
-- vacancy_total and applicant_count MUST come from the official UPSC notification/annual report.
-- Do NOT populate numeric fields until you have verified official figures.
-- reviewer_notes column (not review_notes) — see migration 055.
insert into public.exam_competition_metrics (
  id, exam_id, exam_cycle_id, exam_phase_id,
  vacancy_total, applicant_count, selection_ratio,
  cutoff_trend, difficulty_trend, competition_pressure_score,
  source_basis, confidence_score, evidence_count,
  reviewer_status, reviewed_at, reviewer_notes
) values (
  '<upsc-cse-2024-competition-uuid>',
  '<upsc-cse-exam-uuid>', '<upsc-cse-2024-cycle-uuid>', '<upsc-cse-2024-prelims-uuid>',
  null,                                -- vacancy_total: populate from official notification only
  null,                                -- applicant_count: from UPSC annual report only
  null,                                -- derived from above; null until both are verified
  '{}'::jsonb,                         -- cutoff_trend: add after multi-year verified data
  '{}'::jsonb,                         -- difficulty_trend: same
  null,                                -- do not estimate
  'manual',
  0.0,
  0,
  'pending_review', null,
  '<Reviewer: paste official URL + publication date for vacancy count and applicant figure>'
)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 19. exam_policy_updates
-- ---------------------------------------------------------------------------
-- reviewer_status CHECK (migration 056): 'pending','verified','rejected','needs_correction'
-- source_type CHECK: 'official','aggregator','research','opportunity','unknown'
-- update_type CHECK: 'notification_change','cycle_change','date_change','syllabus_change',
--   'pattern_change','vacancy_change','eligibility_change','reservation_change',
--   'document_rule_change','other'
-- claim_status CHECK: 'unverified','official_confirmed','superseded'
--
-- RULE: affects_* flags MUST ALL be false here.
-- Only source_type='official' AND reviewer_status='verified' may carry affects_* = true,
-- and only set via PATCH after explicit reviewer approval — never in this template.
--
-- Row A: placeholder for the official 2024 notification (non-impacting until verified).
insert into public.exam_policy_updates (
  id, exam_id, exam_cycle_id, exam_phase_id,
  update_type, title, summary,
  source_url, source_type, claim_status, reviewer_status,
  affects_plan, affects_deadline, affects_eligibility,
  affects_documents, affects_syllabus, affects_vacancy,
  published_at, effective_from, reviewer_notes
) values (
  '<upsc-cse-2024-notification-update-uuid>',
  '<upsc-cse-exam-uuid>', '<upsc-cse-2024-cycle-uuid>', null,
  'notification_change',
  'UPSC CSE 2024 Official Notification',
  'Placeholder for the official notification. Reviewer must confirm details before setting affects_*.',
  '<https://upsc.gov.in/...>',         -- official notification URL; do NOT fabricate
  'official',
  'unverified',
  'pending',                           -- promote to 'verified' only after human review
  false, false, false, false, false, false,
  '<ISO-8601>',                        -- official publication date from the notification
  '<ISO-8601>',                        -- effective date from the notification
  '<Reviewer: confirm URL, fetch date, hash; then promote claim_status and set affects_* via PATCH>'
)
on conflict (id) do nothing;

commit;

-- =============================================================================
-- NEXT STEPS after applying this file
-- =============================================================================
-- 1. Validate (non-strict — prints PASS/WARN/FAIL, exits 0):
--      python app/backend/scripts/validate_exam_intelligence_seed.py --exam-slug upsc-cse
--
-- 2. Validate (strict — exits non-zero on hard failures):
--      python app/backend/scripts/validate_exam_intelligence_seed.py --exam-slug upsc-cse --strict
--    Expected result BEFORE any locks: WARN on coverage (pending_review, not locked).
--    The validator will FAIL --strict until topic coverage is promoted to 'locked'.
--
-- 3. Review each section in the Exam Workspace UI:
--    /admin/exam-intelligence/workspace/<upsc-cse-exam-uuid>
--    Use ReviewActivatePanel readiness checklist to see per-section blockers.
--
-- 4. Promote coverage via PATCH (after human review, not before):
--    PATCH /api/admin/exam-intelligence/topic-coverage/<id>/review
--    Body: {"reviewer_status": "reviewed"}   -- or "locked" when ready for planner
--
-- 5. Promote policy updates (official-only, after evidence confirmed):
--    PATCH /api/admin/exam-intelligence/policy-updates/<id>/review
--    Body: {"reviewer_status": "verified"}
--    Then and only then set affects_* = true via a second PATCH if appropriate.
--
-- 6. Re-run strict validator — should pass once coverage is locked + evidence verified.
--
-- 7. Verify endpoints:
--    GET /api/exams                         → upsc-cse in list (is_active=true)
--    GET /api/exams/upsc-cse                → exam detail
--    GET /api/exam-intelligence/exams/upsc-cse → returns partial/empty gracefully pre-review
--    GET /api/study/exams                   → upsc-cse listed for aspirants
-- =============================================================================
