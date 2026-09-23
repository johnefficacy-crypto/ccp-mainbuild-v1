-- Regression for migration 305, run on an ephemeral PG16.
--
-- Repo convention (see regression_244_*.sql): CI has no live-DB migration
-- harness, so the Python tests assert against the migration TEXT and this file
-- carries the behaviour — apply, idempotency, additivity, and the one thing a
-- text assertion cannot reach: that migration 270's level resolution still
-- returns the same answer for every tag that existed before.
--
-- Run:
--   psql -v ON_ERROR_STOP=1 -f app/supabase/tests/regression_305_qa_ssc_geometry_trigonometry.sql
--
-- The fixture is the live tree in miniature: the QA subject, the geometry
-- macro with its five measuring leaves, the arithmetic macro with Averages,
-- and a second subject whose rows must not move. Two of the tags point at
-- leaves this migration anchors on, which is the case most likely to break.

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
  ('55555555-5555-5555-5555-555555555551', 'quantitative-aptitude', 'Quantitative Aptitude'),
  ('55555555-5555-5555-5555-555555555553', 'general-intelligence-reasoning', 'General Intelligence and Reasoning');

-- Macros. `metadata` carries a shape the new macro must inherit rather than
-- invent, which is why the migration copies it from a real one.
INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level, metadata) VALUES
  ('aaaa0000-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555551', NULL,
   'qa-geometry-and-mensuration-00000001', 'Geometry and mensuration', 'topic',
   '{"catalogue": "shared-qre", "weight": 4}'::jsonb),
  ('aaaa0000-0000-0000-0000-000000000002', '55555555-5555-5555-5555-555555555551', NULL,
   'qa-arithmetic-00000002', 'Arithmetic', 'topic',
   '{"catalogue": "shared-qre", "weight": 9}'::jsonb),
  ('bbbb0000-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555553', NULL,
   'reas-coding-decoding-00000003', 'Coding and decoding', 'topic',
   '{"catalogue": "shared-qre"}'::jsonb);

-- Leaves, including the two anchors this migration names.
INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level, metadata) VALUES
  ('cccc0000-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555551',
   'aaaa0000-0000-0000-0000-000000000001',
   'qa-coordinate-and-line-geometry-eb041f58', 'Coordinate and line geometry', 'microtopic',
   '{"catalogue": "shared-qre"}'::jsonb),
  ('cccc0000-0000-0000-0000-000000000002', '55555555-5555-5555-5555-555555555551',
   'aaaa0000-0000-0000-0000-000000000001',
   'qa-circle-area-circumference-and-sectors-e98b662b', 'Circle — area, circumference and sectors', 'microtopic',
   '{"catalogue": "shared-qre"}'::jsonb),
  ('cccc0000-0000-0000-0000-000000000003', '55555555-5555-5555-5555-555555555551',
   'aaaa0000-0000-0000-0000-000000000002',
   'qa-averages-simple-and-weighted-1f479970', 'Averages — simple and weighted', 'microtopic',
   '{"catalogue": "shared-qre"}'::jsonb),
  ('cccc0000-0000-0000-0000-000000000004', '55555555-5555-5555-5555-555555555553',
   'bbbb0000-0000-0000-0000-000000000001',
   'reas-letter-to-symbol-coding-35896380', 'Letter-to-symbol coding', 'microtopic',
   '{"catalogue": "shared-qre"}'::jsonb);

-- Existing primary tags, two of them on the anchors.
INSERT INTO public.pyq_question_topic_tags (question_id, topic_id, tag_role, reviewer_status) VALUES
  ('dddd0000-0000-0000-0000-000000000001', 'cccc0000-0000-0000-0000-000000000001', 'primary', 'verified'),
  ('dddd0000-0000-0000-0000-000000000002', 'cccc0000-0000-0000-0000-000000000003', 'primary', 'verified'),
  ('dddd0000-0000-0000-0000-000000000003', 'cccc0000-0000-0000-0000-000000000004', 'primary', 'verified'),
  ('dddd0000-0000-0000-0000-000000000004', 'aaaa0000-0000-0000-0000-000000000001', 'primary', 'verified');

-- Migration 270's resolution, as a view, so "unchanged" can be compared
-- before and after rather than described.
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

\i app/supabase/migrations/305_qa_ssc_geometry_trigonometry_central_tendency.sql
\i app/supabase/migrations/305_qa_ssc_geometry_trigonometry_central_tendency.sql

-- ── assertions ────────────────────────────────────────────────────────────

DO $$
DECLARE n bigint; m bigint;
BEGIN
  -- 1. Ten rows added: one macro and nine microtopics (five geometry, three
  --    trigonometry, one central tendency). Counted exactly, so a row added or
  --    dropped from the VALUES list without updating the diff table fails here.
  SELECT count(*) INTO n FROM public.topics WHERE metadata->>'added_by_migration' = '305';
  IF n <> 10 THEN RAISE EXCEPTION 'expected 10 new rows, got %', n; END IF;

  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '305' AND level = 'topic';
  IF n <> 1 THEN RAISE EXCEPTION 'expected exactly 1 new macro, got %', n; END IF;

  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '305' AND level = 'microtopic';
  IF n <> 9 THEN RAISE EXCEPTION 'expected 9 new microtopics, got %', n; END IF;

  -- 2. IDEMPOTENT: the second apply above added nothing. Proven by the counts
  --    being what one apply produces, and by no duplicate slug existing.
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

  -- 4. TAG RESOLUTION UNCHANGED: migration 270 reads parent_topic_id, so a
  --    re-parented row would silently move a tagged question's rollup.
  SELECT count(*) INTO n FROM (
    SELECT * FROM snap_resolution_before
    EXCEPT SELECT * FROM tag_resolution
  ) d;
  SELECT count(*) INTO m FROM (
    SELECT * FROM tag_resolution
    EXCEPT SELECT * FROM snap_resolution_before
  ) d;
  IF n <> 0 OR m <> 0 THEN
    RAISE EXCEPTION 'tag resolution changed: % lost, % gained', n, m;
  END IF;

  -- 5. The new macro is a real top-level row in the right subject, so 270
  --    resolves its children to (topic = macro, microtopic = leaf).
  SELECT count(*) INTO n FROM public.topics
   WHERE slug = 'qa-trigonometry-be895874'
     AND level = 'topic' AND parent_topic_id IS NULL
     AND subject_id = '55555555-5555-5555-5555-555555555551';
  IF n <> 1 THEN RAISE EXCEPTION 'Trigonometry macro is not a top-level QA row'; END IF;

  SELECT count(*) INTO n FROM public.topics t
    JOIN public.topics p ON p.id = t.parent_topic_id
   WHERE p.slug = 'qa-trigonometry-be895874' AND t.level = 'microtopic';
  IF n <> 3 THEN RAISE EXCEPTION 'expected 3 trigonometry leaves, got %', n; END IF;

  -- 6. The geometry leaves landed beside the anchor, under ITS macro.
  SELECT count(*) INTO n FROM public.topics t
   WHERE t.metadata->>'ssc_cgl_tier1_area' = 'Quantitative Aptitude — Geometry'
     AND t.parent_topic_id = 'aaaa0000-0000-0000-0000-000000000001'
     AND t.level = 'microtopic';
  IF n <> 5 THEN RAISE EXCEPTION 'expected 5 geometry leaves under the geometry macro, got %', n; END IF;

  -- 7. Median and mode sits beside Averages, under the ARITHMETIC macro.
  SELECT count(*) INTO n FROM public.topics
   WHERE slug = 'qa-median-and-mode-9fcb6443'
     AND parent_topic_id = 'aaaa0000-0000-0000-0000-000000000002';
  IF n <> 1 THEN RAISE EXCEPTION 'Median and mode did not land beside Averages'; END IF;

  -- 8. NO `exams` KEY. These subjects are body-agnostic and the tooling runs
  --    --any-body; one exams key here empties every candidate set.
  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '305' AND metadata ? 'exams';
  IF n <> 0 THEN RAISE EXCEPTION '% new row(s) carry an exams key', n; END IF;

  -- 9. Sibling metadata is inherited, not replaced.
  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '305'
     AND metadata->>'catalogue' IS DISTINCT FROM 'shared-qre';
  IF n <> 0 THEN RAISE EXCEPTION '% new row(s) lost the sibling catalogue key', n; END IF;

  -- 10. The other subject is untouched.
  SELECT count(*) INTO n FROM public.topics
   WHERE subject_id = '55555555-5555-5555-5555-555555555553';
  IF n <> 2 THEN RAISE EXCEPTION 'reasoning subject gained or lost rows: %', n; END IF;

  RAISE NOTICE 'regression 305: all assertions passed';
END $$;

-- ── the absent-tree case: a clean `supabase db reset` must not abort ──────

BEGIN;
DELETE FROM public.pyq_question_topic_tags;
DELETE FROM public.topics WHERE parent_topic_id IS NOT NULL;
DELETE FROM public.topics;
COMMIT;

\i app/supabase/migrations/305_qa_ssc_geometry_trigonometry_central_tendency.sql

DO $$
DECLARE n bigint;
BEGIN
  SELECT count(*) INTO n FROM public.topics;
  IF n <> 0 THEN
    RAISE EXCEPTION 'migration inserted % row(s) against an absent tree', n;
  END IF;
  RAISE NOTICE 'regression 305: absent-tree apply is a no-op';
END $$;
