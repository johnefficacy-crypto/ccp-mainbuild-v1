-- Migration 277: four QRE microtopics the NABARD Grade A tagging pass had no
-- exact match for.
--
-- 24 already-tagged NABARD questions sit on defensible-but-wrong microtopics
-- because the QRE catalogue has no leaf for their item type. The catalogue
-- serves five exams (RBI, SEBI, PFRDA, IFSCA, NABARD), so each gap recurs
-- rather than being a NABARD artefact. Evidence, by NABARD paper and printed
-- question number, is in the trailing comment on each row.
--
--   Word-substitution message coding             9 questions
--   Data sufficiency with numbered statements    6
--   Sentence completion with a missing part      5
--   Correct and incorrect usage of a word        4
--
-- workbench/nabard-qre-gap-retag.csv carries the question_id -> new microtopic
-- mapping. Nothing here tags a question; that is a separate, reviewed step, and
-- it needs the 24 existing primary tags removed first — see
-- workbench/nabard-qre-gap-retag.README.md for why and in what order.
--
-- PARENT RESOLUTION. Each new leaf hangs off the same parent as a named
-- ANCHOR SIBLING, resolved by slug at run time rather than by a hardcoded
-- parent id. The QRE subject tree was created outside the migration set and
-- exists only in the production database, exactly like the six sections
-- migration 273 hangs off; hardcoding a parent no migration creates is what
-- made 269 abort every clean `supabase db reset`. The join below yields zero
-- rows on a database without the anchor instead of raising
-- topics_parent_topic_id_fkey. subject_id and metadata are copied from the
-- anchor for the same reason: this file cannot disagree with the live tree.
--
-- The anchor is also the semantic claim. "Put X beside Y" is what is being
-- asserted, and Y is in each case the microtopic those questions are wrongly
-- sitting on now, or its nearest neighbour:
--   Word-substitution message coding          <- Letter-to-symbol coding
--   Data sufficiency with numbered statements <- Floor puzzle
--   Sentence completion with a missing part   <- Connector-based completion
--   Correct and incorrect usage of a word     <- Single-word contextual fit
--
-- IDS ARE DETERMINISTIC: md5('ccp:topic:' || slug)::uuid, not gen_random_uuid().
-- The re-tag CSV has to name the target topic ids before this migration runs,
-- and pyq_question_review.py validates every assign_topic_id against a topic
-- catalogue. Migration 274's warning about deterministic md5 ids does not apply
-- here: that divergence came from seeding an id for a row that already existed
-- on the live database under a different id. These four rows exist nowhere yet,
-- so both a migration-built and the live database converge on the same id.
--
-- SLUG SUFFIX: left(md5(name), 8), the convention migration 273 established.
-- The live QRE siblings carry an opaque 8-hex suffix that is NOT derivable from
-- the name (verified against all 178 rows of workbench/catalogs/
-- topic_catalog_qre.json — zero match under md5 of the name, the slug body, or
-- either combined with the subject). The new slugs therefore match the SHAPE of
-- their siblings but not their generator. Left as-is rather than inventing a
-- random suffix: a reproducible slug is worth more than a cosmetic match.
--
-- Guarded twice: WHERE NOT EXISTS on the slug makes a re-run a no-op, and the
-- anchor join makes an absent tree a no-op.

BEGIN;

INSERT INTO public.topics
  (id, subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT
  md5('ccp:topic:' || v.slug)::uuid,
  a.subject_id,
  a.parent_topic_id,
  v.slug,
  v.name,
  'microtopic',
  true,
  a.metadata
FROM (VALUES

  -- Reasoning. Whole words, not letters, are substituted: a set of sample
  -- sentences and their codes is given and the mapping must be solved by
  -- intersection. Letter-to-symbol coding is a different mechanism.
  -- NABARD P1 Reasoning 2020 Q15-17, 2021 Q16-17, 2022 (2nd paper) Q13-16.
  ('reas-letter-to-symbol-coding-35896380',
   'reas-word-substitution-message-coding-fe3dbcfc',
   'Word-substitution message coding'),

  -- Reasoning. A question followed by numbered statements, answered by which
  -- statements suffice rather than by solving the setup. The underlying setup
  -- varies (floor, box stack, ordering, city matching), so tagging by setup
  -- loses the skill being tested. `Data sufficiency` exists only under
  -- quantitative-aptitude.
  -- NABARD P1 Reasoning 2020 Q6-7, 2022 (2nd paper) Q19-20, 2023 Q14-15.
  ('reas-floor-puzzle-1df93898',
   'reas-data-sufficiency-with-numbered-statements-cb6e8f2a',
   'Data sufficiency with numbered statements'),

  -- English. A statement with a part missing, where the five options differ
  -- only in grammatical form (tense, non-finite, relative clause) rather than
  -- in vocabulary or connector.
  -- NABARD P1 English 2020 Q59-60, 2022 (evening) Q26-28.
  ('eng-connector-based-completion-cbecd4db',
   'eng-sentence-completion-with-a-missing-part-71b4f9ef',
   'Sentence completion with a missing part'),

  -- English. One word shown in several sentences, or several words in one
  -- sentence, judged for appropriate use — the answer is the WRONG usage.
  -- Single-word contextual fit asks the inverse and gives a blank to fill.
  -- NABARD P1 English 2022 (evening) Q34-35, 2023 Q20-21.
  ('eng-single-word-contextual-fit-601cbc5c',
   'eng-correct-and-incorrect-usage-of-a-word-e7d37216',
   'Correct and incorrect usage of a word')

) AS v(anchor_slug, slug, name)
JOIN public.topics a ON a.slug = v.anchor_slug
WHERE NOT EXISTS (
  SELECT 1 FROM public.topics t WHERE t.slug = v.slug
);

COMMIT;
