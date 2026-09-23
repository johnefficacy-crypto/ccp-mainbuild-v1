-- Migration 306: six microtopics two SSC CGL 2024 Tier I tagging passes had no
-- leaf for, in `general-intelligence-reasoning` and `english-language`.
--
-- Follows migration 305, which did the same for `quantitative-aptitude`. Same
-- shape, same guards, same reason: these three catalogues were grown from
-- regulator and banking corpora, and SSC tests item types those papers do not.
-- 122 questions were tagged by hand across two passes
-- (`workbench/audit/ssc_cgl/drafts/`) and the gaps below are what the operator
-- could not place without forcing a wrong tag.
--
-- ADDITIVE ONLY. Nothing here renames, re-parents, deactivates or deletes a
-- row. The 1,428 existing primary tags point at microtopics this file does not
-- touch, and migration 270 resolves a tag's level from `parent_topic_id`, which
-- no existing row's value changes. The assertion at the end of this transaction
-- proves it rather than asserting it in a comment.
--
-- BODY-AGNOSTIC. Both subjects are shared with RBI Phase I, CSAT and the
-- regulators, and their rows carry NO `topics.metadata.exams` key; the tooling
-- reads them with `--any-body` and a body filter empties every candidate set
-- (`workbench/audit/ssc_cgl/README.md`). No `exams` key is added here.
--
-- PARENT RESOLUTION, as 277 and 305 established: each row hangs off a named
-- ANCHOR resolved by slug at run time, and inherits the anchor's `subject_id`,
-- `parent_topic_id` and `metadata`. These trees exist only on the live database,
-- so a hardcoded parent id is what made 269 abort every clean
-- `supabase db reset`; here an absent tree is a no-op.
--
-- IDS: md5('ccp:topic:' || slug)::uuid. SLUG SUFFIX: left(md5(name), 8) — the
-- convention 273 set, 277 and 305 followed. The live siblings' 8-hex suffix is
-- opaque and not derivable from the name, so these match the SHAPE of their
-- siblings and not their generator.
--
-- NAMES CARRY NO SUBJECT MARKER. The brief writes "Number series (GIR)" to say
-- WHICH subject's leaf is meant; the row is named `Number series`, because not
-- one of the 127 rows in these two subjects carries a parenthetical subject tag
-- and the `reas-` slug prefix plus `subject_id` already say which subject it is.
--
-- ── THE SIX, AND WHY EACH ANCHOR ────────────────────────────────────────────
--
-- GIR. Evidence: 2 of 34 sampled questions came back unmapped, both plain
-- number series ("25, 30, 40, 55, 75, ?" and "16, 36, 64, ?, ?, 196, 256,
-- 324"). The subject has `Alphabet series` and `Alphanumeric and mixed series`
-- and nothing for a series of numbers. Quantitative aptitude's number-series
-- leaves are a DIFFERENT SUBJECT: a reasoning question tagged into QA is
-- mis-filed, not approximately filed, and `build_candidates` would never offer
-- it anyway because the subject filter runs first.
--
--   Number series               <- Alphabet series
--   Wrong-number series         <- Alphabet series
--
-- Two leaves, not one, mirroring the pair the catalogue already keeps
-- elsewhere: finding the next term and finding the term that does not belong
-- are different tasks with different error modes, which is why QA carries both
-- `Number series — …` and `Wrong-term series`.
--
--   Mathematical operations — sign interchange
--                               <- Arithmetic operation machine
--
-- Three distinct mechanics currently land on `Arithmetic operation machine`:
-- an operation chain applied to an input, the interchange of two SIGNS in a
-- given equation, and BODMAS evaluated with symbols swapped. Sign interchange
-- appeared 4 times in 34 sampled questions — the most frequent single item type
-- in the sample with no leaf of its own. The other two stay where they are;
-- this migration splits off the one with evidence, not all three.
--
-- English. Evidence from 50 sampled questions.
--
--   Active and passive voice       <- Tense and sequence of tenses
--   Direct and indirect narration  <- Tense and sequence of tenses
--
-- 4 occurrences of voice, and no leaf for it at all. Narration has no leaf
-- either and is standard SSC; it is added alongside because both are verb-form
-- TRANSFORMATIONS of a given sentence, which is what the anchor is, and a
-- transformation question reaching for "Tense" is the same near-miss voice was.
--
--   Sentence rearrangement (para jumble)
--                               <- Word order and modifier placement
--
-- 5 occurrences, currently parked on `Logical Order`
-- (b2b889f0-5310-23a4-a50c-daa504f0afe7) — a WRITING-ASSESSMENT leaf sitting
-- with Cohesion, Topic Sentence and Word Limit, which are things a marker judges
-- in a candidate's own prose. A para jumble is an MCQ with one right answer, so
-- it belongs under the item-type macro. Anchored on `Word order and modifier
-- placement` because ordering is exactly what both test, one scale apart: words
-- within a sentence there, sentences within a paragraph here.
--
-- `Logical Order` is NOT retired, renamed or re-parented by this file. The five
-- questions sitting on it are re-tagged by a reviewed worksheet, not by a
-- migration — see the SSC runbook.
--
-- ── ONE THING A READER SHOULD KNOW ABOUT THE TWO ENGLISH ANCHORS ────────────
--
-- Both are the MODERN member of a legacy/modern duplicate pair: `tense` and
-- `modifiers` still exist alongside them under the original naming convention.
-- That is reported, with a merge plan, in
-- `workbench/reports/ENGLISH-CATALOGUE-DUPLICATE-PAIRS-2026-09-23.md`; nothing
-- is merged here. It does not couple this migration to that decision, because
-- the rows below inherit `a.parent_topic_id` — the anchor's MACRO — and are
-- therefore the anchor's SIBLINGS. Deactivating an anchor in a later merge
-- neither orphans nor moves them.
--
-- Guarded twice: WHERE NOT EXISTS on the slug makes a re-run insert nothing,
-- and the anchor join makes an absent tree a no-op.

BEGIN;

-- The pre-existing catalogue, captured before anything is inserted. "Additive"
-- is a claim about every column of every row, so every column of every row is
-- what the assertion at the bottom checks.
CREATE TEMP TABLE _topics_before_306 ON COMMIT DROP AS
SELECT id, subject_id, parent_topic_id, slug, name, level, is_active, metadata
  FROM public.topics;

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
  COALESCE(a.metadata, '{}'::jsonb) || jsonb_build_object(
    'ssc_cgl_tier1_area', v.area,
    'source', 'operator tagging passes over SSC CGL 2024 Tier I, 122 questions; workbench/audit/ssc_cgl/drafts/',
    'added_by_migration', '306'
  )
FROM (VALUES

  -- ── general-intelligence-reasoning ──────────────────────────────────────

  -- "25, 30, 40, 55, 75, ?" — the next term of a numeric progression. Unmapped
  -- in the sample, twice.
  ('reas-alphabet-series-b3b70d39',
   'reas-number-series-6232574a',
   'Number series',
   'General Intelligence and Reasoning — Series'),

  -- "16, 36, 64, ?, ?, 196, 256, 324" with one term wrong: find the intruder,
  -- not the next term.
  ('reas-alphabet-series-b3b70d39',
   'reas-wrong-number-series-31e436e6',
   'Wrong-number series',
   'General Intelligence and Reasoning — Series'),

  -- Two signs in a given equation are swapped and the equation must be made
  -- true. Distinct from an operation CHAIN applied to an input, which is what
  -- the anchor is, and from BODMAS with substituted symbols.
  ('reas-arithmetic-operation-machine-258cf421',
   'reas-mathematical-operations-sign-interchange-3d6288ea',
   'Mathematical operations — sign interchange',
   'General Intelligence and Reasoning — Mathematical operations'),

  -- ── english-language ────────────────────────────────────────────────────

  -- "Select the passive form of: The gardener waters the plants." A
  -- transformation of a given sentence, four occurrences, no leaf at all.
  ('eng-tense-and-sequence-of-tenses-7e82f0cb',
   'eng-active-and-passive-voice-e6437f9d',
   'Active and passive voice',
   'English Comprehension — Grammar transformations'),

  -- "He said, ''I am tired''" -> reported speech. The other half of the
  -- transformation pair, standard SSC, absent from the catalogue.
  ('eng-tense-and-sequence-of-tenses-7e82f0cb',
   'eng-direct-and-indirect-narration-1d250c23',
   'Direct and indirect narration',
   'English Comprehension — Grammar transformations'),

  -- Labelled parts A-D to be put in order. Five occurrences, currently on a
  -- writing-assessment leaf; see the header for why that is the wrong macro.
  ('eng-word-order-and-modifier-placement-1b73c44c',
   'eng-sentence-rearrangement-para-jumble-66cc898f',
   'Sentence rearrangement (para jumble)',
   'English Comprehension — Sentence ordering')

) AS v(anchor_slug, slug, name, area)
JOIN public.topics a ON a.slug = v.anchor_slug
WHERE NOT EXISTS (
  SELECT 1 FROM public.topics t WHERE t.slug = v.slug
);

-- ── prove the claim in the header ─────────────────────────────────────────

DO $$
DECLARE
  changed bigint;
  removed bigint;
BEGIN
  SELECT count(*) INTO removed
  FROM _topics_before_306 b
  WHERE NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.id = b.id);
  IF removed > 0 THEN
    RAISE EXCEPTION 'migration 306 is additive only, but % existing topic row(s) disappeared', removed;
  END IF;

  SELECT count(*) INTO changed
  FROM _topics_before_306 b
  JOIN public.topics t ON t.id = b.id
  WHERE (t.subject_id, t.parent_topic_id, t.slug, t.name, t.level, t.is_active, t.metadata)
     IS DISTINCT FROM
        (b.subject_id, b.parent_topic_id, b.slug, b.name, b.level, b.is_active, b.metadata);
  IF changed > 0 THEN
    RAISE EXCEPTION 'migration 306 is additive only, but % existing topic row(s) changed', changed;
  END IF;
END $$;

NOTIFY pgrst, 'reload schema';

COMMIT;
