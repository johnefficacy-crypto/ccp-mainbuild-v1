-- Regression for migration 306, run on an ephemeral PG16.
--
-- Repo convention (see regression_244_*.sql, regression_305_*.sql): CI has no
-- live-DB migration harness, so the Python tests assert against the migration
-- TEXT and this file carries the behaviour — apply, two applies, additivity,
-- and migration 270's tag-level resolution compared before and after.
--
-- Run:
--   psql -v ON_ERROR_STOP=1 -f app/supabase/tests/regression_306_gir_english_item_type_gaps.sql
--
-- The fixture is the live tree in miniature: both subjects, the three macros
-- the new leaves land under, the four anchor leaves, and the `Logical Order`
-- row with a tag on it — the row the brief says must NOT move.

\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE public.subjects (
  id uuid PRIMARY KEY,
  slug text NOT NULL UNIQUE,
  name text NOT NULL
);

CREATE TABLE public.topics (
  id uuid PRIMARY KEY,
  subject_id uuid NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  parent_topic_id uuid REFERENCES public.topics(id) ON DELETE CASCADE,
  slug text NOT NULL,
  name text NOT NULL,
  level text NOT NULL DEFAULT 'topic'
    CHECK (level IN ('topic', 'microtopic', 'concept')),
  default_difficulty_level text,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (subject_id, parent_topic_id, slug)
);

CREATE TABLE public.pyq_question_topic_tags (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id uuid NOT NULL,
  topic_id uuid NOT NULL REFERENCES public.topics(id),
  tag_role text NOT NULL,
  reviewer_status text NOT NULL
);

-- ── the fixture ───────────────────────────────────────────────────────────

INSERT INTO public.subjects (id, slug, name) VALUES
  ('55555555-5555-5555-5555-555555555553', 'general-intelligence-reasoning',
   'General Intelligence and Reasoning'),
  ('55555555-5555-5555-5555-555555555552', 'english-language', 'English Language'),
  -- A third subject that must not gain or lose a row.
  ('55555555-5555-5555-5555-555555555551', 'quantitative-aptitude', 'Quantitative Aptitude');

INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level, metadata) VALUES
  -- GIR macros
  ('aaaa0000-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555553',
   NULL, 'reas-series-00000001', 'Series', 'topic', '{"catalogue": "shared-qre"}'::jsonb),
  ('aaaa0000-0000-0000-0000-000000000002', '55555555-5555-5555-5555-555555555553',
   NULL, 'reas-machine-input-output-00000002', 'Machine input-output', 'topic',
   '{"catalogue": "shared-qre"}'::jsonb),
  -- English macros: the item-type one the new leaves join, and the
  -- writing-assessment one `Logical Order` lives in and must stay in.
  ('bbbb0000-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555552',
   NULL, 'eng-grammar-and-usage-00000003', 'Grammar and usage', 'topic',
   '{"catalogue": "shared-qre"}'::jsonb),
  ('bbbb0000-0000-0000-0000-000000000002', '55555555-5555-5555-5555-555555555552',
   NULL, 'eng-sentence-improvement-00000004', 'Sentence improvement', 'topic',
   '{"catalogue": "shared-qre"}'::jsonb),
  ('bbbb0000-0000-0000-0000-000000000003', '55555555-5555-5555-5555-555555555552',
   NULL, 'eng-written-composition-00000005', 'Written composition', 'topic',
   '{"catalogue": "shared-qre"}'::jsonb),
  -- QA macro, untouched
  ('cccc0000-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555551',
   NULL, 'qa-arithmetic-00000006', 'Arithmetic', 'topic', '{"catalogue": "shared-qre"}'::jsonb);

INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level, metadata) VALUES
  -- The four anchors, at the ids the live catalogue carries.
  ('7d5a08c1-a3ac-4337-8f3e-28b5762b1857', '55555555-5555-5555-5555-555555555553',
   'aaaa0000-0000-0000-0000-000000000001',
   'reas-alphabet-series-b3b70d39', 'Alphabet series', 'microtopic',
   '{"catalogue": "shared-qre"}'::jsonb),
  ('dad69132-676d-4a7b-be3d-1da364bd36f9', '55555555-5555-5555-5555-555555555553',
   'aaaa0000-0000-0000-0000-000000000002',
   'reas-arithmetic-operation-machine-258cf421', 'Arithmetic operation machine',
   'microtopic', '{"catalogue": "shared-qre"}'::jsonb),
  ('f146f9b5-b13d-47c0-8aca-c80a6566b4fe', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000001',
   'eng-tense-and-sequence-of-tenses-7e82f0cb', 'Tense and sequence of tenses',
   'microtopic', '{"catalogue": "shared-qre"}'::jsonb),
  ('3ab068c5-397c-4189-913f-0d26569b3899', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000002',
   'eng-word-order-and-modifier-placement-1b73c44c',
   'Word order and modifier placement', 'microtopic',
   '{"catalogue": "shared-qre"}'::jsonb),
  -- `Logical Order`, at its live id, under the WRITING macro. The five para
  -- jumbles sit here today; this migration must not move the row.
  ('b2b889f0-5310-23a4-a50c-daa504f0afe7', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000003', 'logical-order', 'Logical Order',
   'microtopic', '{"catalogue": "shared-qre"}'::jsonb),
  -- One of the duplicate pairs the PR reports on but does not touch.
  ('b9facc82-38d7-f725-7c97-8b5894c157f0', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000001', 'subject-verb-agreement',
   'Subject-Verb Agreement', 'microtopic', '{"catalogue": "shared-qre"}'::jsonb),
  ('7c71b869-e50a-4ebd-aea1-fe291dbee5ed', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000001', 'eng-subject-verb-agreement-07be8ac5',
   'Subject-verb agreement', 'microtopic', '{"catalogue": "shared-qre"}'::jsonb),
  -- A QA leaf, to prove the third subject is untouched.
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-555555555551',
   'cccc0000-0000-0000-0000-000000000001', 'qa-averages-simple-and-weighted-1f479970',
   'Averages — simple and weighted', 'microtopic', '{"catalogue": "shared-qre"}'::jsonb);

-- Tags, including five on `Logical Order` — the para jumbles the brief says are
-- re-tagged by a reviewed worksheet and NOT by this migration.
INSERT INTO public.pyq_question_topic_tags (question_id, topic_id, tag_role, reviewer_status)
SELECT ('dddd0000-0000-0000-0000-' || lpad(g::text, 12, '0'))::uuid,
       'b2b889f0-5310-23a4-a50c-daa504f0afe7', 'primary', 'verified'
  FROM generate_series(1, 5) g;
INSERT INTO public.pyq_question_topic_tags (question_id, topic_id, tag_role, reviewer_status) VALUES
  ('dddd0000-0000-0000-0000-000000000101', '7d5a08c1-a3ac-4337-8f3e-28b5762b1857',
   'primary', 'verified'),
  ('dddd0000-0000-0000-0000-000000000102', 'dad69132-676d-4a7b-be3d-1da364bd36f9',
   'primary', 'verified'),
  ('dddd0000-0000-0000-0000-000000000103', 'f146f9b5-b13d-47c0-8aca-c80a6566b4fe',
   'primary', 'verified'),
  -- A tag on a top-level topic, which 270 resolves the other way.
  ('dddd0000-0000-0000-0000-000000000104', 'bbbb0000-0000-0000-0000-000000000003',
   'primary', 'verified');

-- Migration 270's resolution, as a view, so "unchanged" is compared rather
-- than described.
CREATE VIEW tag_resolution AS
SELECT g.question_id,
       CASE WHEN t.parent_topic_id IS NULL THEN t.id ELSE t.parent_topic_id END AS topic_id,
       CASE WHEN t.parent_topic_id IS NULL THEN NULL ELSE t.id END            AS microtopic_id
  FROM public.pyq_question_topic_tags g
  JOIN public.topics t ON t.id = g.topic_id
 WHERE g.tag_role = 'primary' AND g.reviewer_status = 'verified';

CREATE TABLE snap_topics_before AS SELECT * FROM public.topics;
CREATE TABLE snap_resolution_before AS SELECT * FROM tag_resolution;

COMMIT;

-- ── apply, twice ──────────────────────────────────────────────────────────

\i app/supabase/migrations/306_gir_english_ssc_item_type_gaps.sql
\i app/supabase/migrations/306_gir_english_ssc_item_type_gaps.sql

-- ── assertions ────────────────────────────────────────────────────────────

DO $$
DECLARE n bigint; m bigint;
BEGIN
  -- 1. Six leaves, no macros. Counted exactly.
  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '306';
  IF n <> 6 THEN RAISE EXCEPTION 'expected 6 new rows, got %', n; END IF;

  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '306' AND level <> 'microtopic';
  IF n <> 0 THEN RAISE EXCEPTION '% new row(s) are not microtopics', n; END IF;

  -- 2. IDEMPOTENT: the second apply added nothing.
  SELECT count(*) INTO n FROM (
    SELECT slug FROM public.topics GROUP BY slug HAVING count(*) > 1
  ) d;
  IF n <> 0 THEN RAISE EXCEPTION '% duplicated slug(s) after two applies', n; END IF;

  -- 3. ADDITIVE: every pre-existing row survives, unchanged in every column.
  SELECT count(*) INTO n FROM snap_topics_before b
   WHERE NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.id = b.id);
  IF n <> 0 THEN RAISE EXCEPTION '% pre-existing topic(s) disappeared', n; END IF;

  SELECT count(*) INTO n FROM snap_topics_before b
    JOIN public.topics t ON t.id = b.id
   WHERE (t.subject_id, t.parent_topic_id, t.slug, t.name, t.level, t.is_active, t.metadata)
      IS DISTINCT FROM
         (b.subject_id, b.parent_topic_id, b.slug, b.name, b.level, b.is_active, b.metadata);
  IF n <> 0 THEN RAISE EXCEPTION '% pre-existing topic(s) changed', n; END IF;

  -- 4. TAG RESOLUTION UNCHANGED, including the five on `Logical Order`.
  SELECT count(*) INTO n FROM (
    SELECT * FROM snap_resolution_before EXCEPT SELECT * FROM tag_resolution) d;
  SELECT count(*) INTO m FROM (
    SELECT * FROM tag_resolution EXCEPT SELECT * FROM snap_resolution_before) d;
  IF n <> 0 OR m <> 0 THEN
    RAISE EXCEPTION 'tag resolution changed: % lost, % gained', n, m;
  END IF;

  -- 5. `Logical Order` is exactly where it was, in the WRITING macro, with its
  --    five tags. The brief says a worksheet moves those questions, not this.
  SELECT count(*) INTO n FROM public.topics
   WHERE id = 'b2b889f0-5310-23a4-a50c-daa504f0afe7'
     AND slug = 'logical-order' AND name = 'Logical Order'
     AND parent_topic_id = 'bbbb0000-0000-0000-0000-000000000003'
     AND is_active;
  IF n <> 1 THEN RAISE EXCEPTION 'Logical Order was altered'; END IF;

  SELECT count(*) INTO n FROM public.pyq_question_topic_tags
   WHERE topic_id = 'b2b889f0-5310-23a4-a50c-daa504f0afe7';
  IF n <> 5 THEN RAISE EXCEPTION 'Logical Order lost tags: %', n; END IF;

  -- 6. Each leaf landed under its anchor's macro, in its anchor's subject.
  SELECT count(*) INTO n FROM public.topics
   WHERE slug IN ('reas-number-series-6232574a', 'reas-wrong-number-series-31e436e6')
     AND parent_topic_id = 'aaaa0000-0000-0000-0000-000000000001'
     AND subject_id = '55555555-5555-5555-5555-555555555553';
  IF n <> 2 THEN RAISE EXCEPTION 'series leaves are not under the Series macro: %', n; END IF;

  SELECT count(*) INTO n FROM public.topics
   WHERE slug = 'reas-mathematical-operations-sign-interchange-3d6288ea'
     AND parent_topic_id = 'aaaa0000-0000-0000-0000-000000000002';
  IF n <> 1 THEN RAISE EXCEPTION 'sign interchange is not under the machine macro'; END IF;

  SELECT count(*) INTO n FROM public.topics
   WHERE slug IN ('eng-active-and-passive-voice-e6437f9d',
                  'eng-direct-and-indirect-narration-1d250c23')
     AND parent_topic_id = 'bbbb0000-0000-0000-0000-000000000001';
  IF n <> 2 THEN RAISE EXCEPTION 'voice/narration are not under Grammar and usage: %', n; END IF;

  -- The point of the para-jumble row: the item-type macro, NOT the writing one.
  SELECT count(*) INTO n FROM public.topics
   WHERE slug = 'eng-sentence-rearrangement-para-jumble-66cc898f'
     AND parent_topic_id = 'bbbb0000-0000-0000-0000-000000000002';
  IF n <> 1 THEN RAISE EXCEPTION 'para jumble did not land in the item-type macro'; END IF;

  SELECT count(*) INTO n FROM public.topics
   WHERE slug = 'eng-sentence-rearrangement-para-jumble-66cc898f'
     AND parent_topic_id = 'bbbb0000-0000-0000-0000-000000000003';
  IF n <> 0 THEN RAISE EXCEPTION 'para jumble landed in the writing macro'; END IF;

  -- 7. NO `exams` key: both subjects are body-agnostic.
  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '306' AND metadata ? 'exams';
  IF n <> 0 THEN RAISE EXCEPTION '% new row(s) carry an exams key', n; END IF;

  -- 8. Sibling metadata inherited, not replaced.
  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '306'
     AND metadata->>'catalogue' IS DISTINCT FROM 'shared-qre';
  IF n <> 0 THEN RAISE EXCEPTION '% new row(s) lost the sibling catalogue key', n; END IF;

  -- 9. The third subject is untouched.
  SELECT count(*) INTO n FROM public.topics
   WHERE subject_id = '55555555-5555-5555-5555-555555555551';
  IF n <> 2 THEN RAISE EXCEPTION 'quantitative-aptitude changed row count: %', n; END IF;

  -- 10. The duplicate pair this PR only REPORTS on is still a pair.
  SELECT count(*) INTO n FROM public.topics
   WHERE slug IN ('subject-verb-agreement', 'eng-subject-verb-agreement-07be8ac5');
  IF n <> 2 THEN RAISE EXCEPTION 'a reported duplicate pair was altered: %', n; END IF;

  RAISE NOTICE 'regression 306: all assertions passed';
END $$;

-- ── the absent-tree case: a clean `supabase db reset` must not abort ──────

BEGIN;
DELETE FROM public.pyq_question_topic_tags;
DELETE FROM public.topics;
COMMIT;

\i app/supabase/migrations/306_gir_english_ssc_item_type_gaps.sql

DO $$
DECLARE n bigint;
BEGIN
  SELECT count(*) INTO n FROM public.topics;
  IF n <> 0 THEN
    RAISE EXCEPTION 'migration inserted % row(s) against an absent tree', n;
  END IF;
  RAISE NOTICE 'regression 306: absent-tree apply is a no-op';
END $$;
