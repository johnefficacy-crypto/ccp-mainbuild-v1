-- Regression for migration 308, run on an ephemeral PG16.
--
-- Repo convention (see regression_305_*.sql, regression_306_*.sql): CI has no
-- live-DB migration harness, so the Python tests assert against the migration
-- TEXT and this file carries the behaviour.
--
-- Run:
--   psql -v ON_ERROR_STOP=1 -f app/supabase/tests/regression_308_venn_and_english_retire_audit.sql
--
-- The fixture is built so that every branch of the audit fires at least once,
-- including the DELETE branch — a regression where nothing is ever deletable
-- would pass while the delete was broken:
--
--   subject-verb-agreement  referenced by a NO ACTION FK        -> skipped
--   tense                   referenced by a CASCADE FK          -> skipped
--   articles                referenced by a NO ACTION FK        -> skipped
--   prepositions            no refs, but HAS A CHILD topic      -> skipped
--   modifiers               referenced through a COMPOSITE FK   -> skipped
--   pronoun-reference       nothing points at it                -> RETIRED
--   redundancy              not in the fixture at all           -> absent

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
  is_active boolean NOT NULL DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (subject_id, parent_topic_id, slug),
  -- Needed only so the fixture can carry a composite FK, as migration 274
  -- describes one in the EWP schema.
  UNIQUE (subject_id, id)
);

-- The EWP map: migration 205 §17. NOT NULL, and no ON DELETE clause, so a
-- delete of a mapped microtopic raises rather than cascading.
CREATE TABLE public.writing_issue_type_microtopic_map (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_type text NOT NULL,
  microtopic_id uuid NOT NULL REFERENCES public.topics(id),
  is_active boolean NOT NULL DEFAULT true
);

-- A cascading FK: the hazard the audit exists to prevent. Deleting a topic
-- here destroys a learner's mastery row without raising anything.
CREATE TABLE public.user_topic_mastery (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  topic_id uuid NOT NULL REFERENCES public.topics(id) ON DELETE CASCADE,
  score numeric NOT NULL DEFAULT 0
);

-- A composite FK whose topic column is NOT first: the alignment case.
CREATE TABLE public.writing_prompts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id uuid NOT NULL,
  microtopic_id uuid NOT NULL,
  FOREIGN KEY (subject_id, microtopic_id)
    REFERENCES public.topics (subject_id, id)
);

-- The PYQ tag table, so "zero tags" is a fact in the fixture too.
CREATE TABLE public.pyq_question_topic_tags (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id uuid NOT NULL,
  topic_id uuid NOT NULL REFERENCES public.topics(id) ON DELETE RESTRICT,
  tag_role text NOT NULL,
  reviewer_status text NOT NULL
);

-- ── the fixture ───────────────────────────────────────────────────────────

INSERT INTO public.subjects (id, slug, name) VALUES
  ('55555555-5555-5555-5555-555555555553', 'general-intelligence-reasoning',
   'General Intelligence and Reasoning'),
  ('55555555-5555-5555-5555-555555555552', 'english-language', 'English Language');

-- GIR: the macro the syllogism leaves live under, and the anchor.
INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level, metadata) VALUES
  ('aaaa0000-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555553',
   NULL, 'reas-syllogism-and-statement-sets-00000001', 'Syllogism and statement sets',
   'topic', '{"catalogue": "shared-qre"}'::jsonb),
  ('7f650350-0000-4000-8000-000000000001', '55555555-5555-5555-5555-555555555553',
   'aaaa0000-0000-0000-0000-000000000001', 'reas-two-statement-syllogism-7f65e035',
   'Two-statement syllogism', 'microtopic', '{"catalogue": "shared-qre"}'::jsonb),
  ('e8800438-0000-4000-8000-000000000001', '55555555-5555-5555-5555-555555555553',
   'aaaa0000-0000-0000-0000-000000000001',
   'reas-three-or-more-statement-syllogism-e8800438',
   'Three or more statement syllogism', 'microtopic', '{"catalogue": "shared-qre"}'::jsonb),
  -- A second GIR macro that must not gain the new leaf.
  ('aaaa0000-0000-0000-0000-000000000002', '55555555-5555-5555-5555-555555555553',
   NULL, 'reas-counting-00000002', 'Counting', 'topic', '{"catalogue": "shared-qre"}'::jsonb);

-- English: the EWP macros from migration 205, and the MCQ item-type macro.
INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level, metadata) VALUES
  ('bbbb0000-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555552',
   NULL, 'grammar', 'Grammar', 'topic', '{}'::jsonb),
  ('bbbb0000-0000-0000-0000-000000000002', '55555555-5555-5555-5555-555555555552',
   NULL, 'vocabulary-in-context', 'Vocabulary in Context', 'topic', '{}'::jsonb),
  ('bbbb0000-0000-0000-0000-000000000003', '55555555-5555-5555-5555-555555555552',
   NULL, 'eng-grammar-and-usage-00000003', 'Grammar and usage', 'topic',
   '{"catalogue": "shared-qre"}'::jsonb);

-- The EWP leaves the report proposed retiring.
INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level) VALUES
  ('b9facc82-38d7-f725-7c97-8b5894c157f0', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000001', 'subject-verb-agreement',
   'Subject-Verb Agreement', 'microtopic'),
  ('aa680736-24d9-abb2-d7f2-ad3bcb2acb77', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000001', 'tense', 'Tense', 'microtopic'),
  ('b790ab2c-17e8-9025-f313-2c44d24dac8d', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000001', 'articles', 'Articles', 'microtopic'),
  ('5db857e5-5b9d-2f80-0046-1978c199ed85', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000001', 'prepositions', 'Prepositions', 'microtopic'),
  ('c6beb287-3fef-397f-e204-57f8e4053328', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000001', 'pronoun-reference', 'Pronoun Reference',
   'microtopic'),
  ('aca53761-13fc-65c9-bd3c-9f324e9a589f', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000001', 'modifiers', 'Modifiers', 'microtopic');
-- `redundancy` is deliberately NOT inserted: the absent branch.

-- A child under `prepositions`, so the child branch has something to find.
INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level) VALUES
  ('5db857e5-0000-4000-8000-000000000009', '55555555-5555-5555-5555-555555555552',
   '5db857e5-5b9d-2f80-0046-1978c199ed85', 'prepositions-of-time',
   'Prepositions of time', 'concept');

-- The modern MCQ rows, which keep every PYQ tag and must not be touched.
INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level, metadata) VALUES
  ('7c71b869-e50a-4ebd-aea1-fe291dbee5ed', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000003', 'eng-subject-verb-agreement-07be8ac5',
   'Subject-verb agreement', 'microtopic', '{"catalogue": "shared-qre"}'::jsonb),
  ('f146f9b5-b13d-47c0-8aca-c80a6566b4fe', '55555555-5555-5555-5555-555555555552',
   'bbbb0000-0000-0000-0000-000000000003', 'eng-tense-and-sequence-of-tenses-7e82f0cb',
   'Tense and sequence of tenses', 'microtopic', '{"catalogue": "shared-qre"}'::jsonb);

-- The five PYQ tags the live counts put on the modern row.
INSERT INTO public.pyq_question_topic_tags (question_id, topic_id, tag_role, reviewer_status)
SELECT ('dddd0000-0000-0000-0000-' || lpad(g::text, 12, '0'))::uuid,
       '7c71b869-e50a-4ebd-aea1-fe291dbee5ed', 'primary', 'verified'
  FROM generate_series(1, 5) g;

-- EWP references. This is the whole point: no PYQ tag, but not unreferenced.
INSERT INTO public.writing_issue_type_microtopic_map (issue_type, microtopic_id) VALUES
  ('subject_verb_agreement', 'b9facc82-38d7-f725-7c97-8b5894c157f0'),
  ('article',                'b790ab2c-17e8-9025-f313-2c44d24dac8d');
INSERT INTO public.user_topic_mastery (user_id, topic_id, score) VALUES
  ('eeee0000-0000-4000-8000-000000000001', 'aa680736-24d9-abb2-d7f2-ad3bcb2acb77', 0.4);
INSERT INTO public.writing_prompts (subject_id, microtopic_id) VALUES
  ('55555555-5555-5555-5555-555555555552', 'aca53761-13fc-65c9-bd3c-9f324e9a589f');

CREATE TABLE snap_topics_before AS SELECT * FROM public.topics;
CREATE TABLE snap_mastery_before AS SELECT * FROM public.user_topic_mastery;

COMMIT;

-- ── apply, twice ──────────────────────────────────────────────────────────

\i app/supabase/migrations/308_gir_venn_diagram_and_english_duplicate_audit.sql
\i app/supabase/migrations/308_gir_venn_diagram_and_english_duplicate_audit.sql

-- ── assertions ────────────────────────────────────────────────────────────

DO $$
DECLARE n bigint;
BEGIN
  -- 1. Exactly one new row, a microtopic, under the SYLLOGISM macro.
  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '308';
  IF n <> 1 THEN RAISE EXCEPTION 'expected 1 new row, got %', n; END IF;

  SELECT count(*) INTO n FROM public.topics
   WHERE slug = 'reas-venn-diagram-360f6cdd'
     AND level = 'microtopic'
     AND subject_id = '55555555-5555-5555-5555-555555555553'
     AND parent_topic_id = 'aaaa0000-0000-0000-0000-000000000001'
     AND is_active;
  IF n <> 1 THEN RAISE EXCEPTION 'Venn diagram is not a live microtopic under the syllogism macro'; END IF;

  -- It is the anchor's SIBLING, not its child.
  SELECT count(*) INTO n FROM public.topics
   WHERE slug = 'reas-venn-diagram-360f6cdd'
     AND parent_topic_id = '7f650350-0000-4000-8000-000000000001';
  IF n <> 0 THEN RAISE EXCEPTION 'Venn diagram was made a child of the anchor'; END IF;

  -- Not in the other macro.
  SELECT count(*) INTO n FROM public.topics
   WHERE slug = 'reas-venn-diagram-360f6cdd'
     AND parent_topic_id = 'aaaa0000-0000-0000-0000-000000000002';
  IF n <> 0 THEN RAISE EXCEPTION 'Venn diagram landed in the Counting macro'; END IF;

  -- 2. IDEMPOTENT: two applies, one row.
  SELECT count(*) INTO n FROM (
    SELECT slug FROM public.topics GROUP BY slug HAVING count(*) > 1) d;
  IF n <> 0 THEN RAISE EXCEPTION '% duplicated slug(s) after two applies', n; END IF;

  -- 3. The audit kept every REFERENCED row. This is the finding the migration
  --    exists to record: no PYQ tag does not mean unreferenced.
  SELECT count(*) INTO n FROM public.topics
   WHERE subject_id = '55555555-5555-5555-5555-555555555552'
     AND slug IN ('subject-verb-agreement', 'tense', 'articles', 'prepositions', 'modifiers');
  IF n <> 5 THEN RAISE EXCEPTION 'the audit removed a referenced EWP row: % of 5 left', n; END IF;

  -- 4. The one genuinely unreferenced row WAS retired — the delete branch runs.
  SELECT count(*) INTO n FROM public.topics
   WHERE subject_id = '55555555-5555-5555-5555-555555555552' AND slug = 'pronoun-reference';
  IF n <> 0 THEN RAISE EXCEPTION 'pronoun-reference had no references and was not retired'; END IF;

  -- 5. A CASCADE FK did not silently eat a learner's row.
  SELECT count(*) INTO n FROM (
    SELECT * FROM snap_mastery_before EXCEPT SELECT * FROM public.user_topic_mastery) d;
  IF n <> 0 THEN RAISE EXCEPTION '% mastery row(s) were cascaded away', n; END IF;

  -- 6. The EWP map still resolves every issue type it did before.
  SELECT count(*) INTO n FROM public.writing_issue_type_microtopic_map m
   WHERE NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.id = m.microtopic_id);
  IF n <> 0 THEN RAISE EXCEPTION '% EWP mapping(s) now dangle', n; END IF;

  -- 7. The child under `prepositions` survives, and `prepositions` with it.
  SELECT count(*) INTO n FROM public.topics WHERE slug = 'prepositions-of-time';
  IF n <> 1 THEN RAISE EXCEPTION 'the child topic was cascaded away'; END IF;

  -- 8. The composite FK was read on its TOPIC column, not its first column.
  --    If the alignment were wrong, `modifiers` would have counted 0 and been
  --    deleted, and this row would be gone with it.
  SELECT count(*) INTO n FROM public.writing_prompts;
  IF n <> 1 THEN RAISE EXCEPTION 'the composite-FK row was lost'; END IF;

  -- 9. Every surviving pre-existing row is unchanged in every column.
  SELECT count(*) INTO n FROM snap_topics_before b
    JOIN public.topics t ON t.id = b.id
   WHERE (t.subject_id, t.parent_topic_id, t.slug, t.name, t.level, t.is_active, t.metadata)
      IS DISTINCT FROM
         (b.subject_id, b.parent_topic_id, b.slug, b.name, b.level, b.is_active, b.metadata);
  IF n <> 0 THEN RAISE EXCEPTION '% pre-existing topic(s) changed', n; END IF;

  -- 10. Exactly one pre-existing row is gone, and it is the retired one.
  SELECT count(*) INTO n FROM snap_topics_before b
   WHERE NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.id = b.id);
  IF n <> 1 THEN RAISE EXCEPTION 'expected exactly 1 retired row, got %', n; END IF;

  -- 11. The modern rows and their tags are untouched.
  SELECT count(*) INTO n FROM public.pyq_question_topic_tags
   WHERE topic_id = '7c71b869-e50a-4ebd-aea1-fe291dbee5ed';
  IF n <> 5 THEN RAISE EXCEPTION 'the modern row lost tags: %', n; END IF;

  -- 12. No `exams` key on the new row.
  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '308' AND metadata ? 'exams';
  IF n <> 0 THEN RAISE EXCEPTION 'the new row carries an exams key'; END IF;

  -- 13. Sibling metadata inherited.
  SELECT count(*) INTO n FROM public.topics
   WHERE metadata->>'added_by_migration' = '308'
     AND metadata->>'catalogue' IS DISTINCT FROM 'shared-qre';
  IF n <> 0 THEN RAISE EXCEPTION 'the new row lost the sibling catalogue key'; END IF;

  RAISE NOTICE 'regression 308: all assertions passed';
END $$;

-- ── the absent-tree case: a clean `supabase db reset` must not abort ──────

BEGIN;
DELETE FROM public.writing_issue_type_microtopic_map;
DELETE FROM public.writing_prompts;
DELETE FROM public.user_topic_mastery;
DELETE FROM public.pyq_question_topic_tags;
DELETE FROM public.topics;
COMMIT;

\i app/supabase/migrations/308_gir_venn_diagram_and_english_duplicate_audit.sql

DO $$
DECLARE n bigint;
BEGIN
  SELECT count(*) INTO n FROM public.topics;
  IF n <> 0 THEN
    RAISE EXCEPTION 'migration inserted % row(s) against an absent tree', n;
  END IF;
  RAISE NOTICE 'regression 308: absent-tree apply is a no-op';
END $$;
