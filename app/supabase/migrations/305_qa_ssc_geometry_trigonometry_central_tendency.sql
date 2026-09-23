-- Migration 305: the SSC CGL Tier I geometry, trigonometry and central-tendency
-- areas that the shared `quantitative-aptitude` catalogue has no leaf for.
--
-- WHY THE GAP EXISTS. That catalogue was grown from regulator and banking
-- corpora (RBI Phase I, SEBI, PFRDA, IFSCA, NABARD), whose quantitative papers
-- are arithmetic, algebra and data interpretation. SSC CGL Tier I tests plane
-- geometry and trigonometry in roughly ten of its twenty-five QA questions, and
-- the catalogue's entire geometry provision is five leaves about AREA and
-- VOLUME:
--
--   qa-area-and-perimeter-rectangle-square-triangle-e23db61d
--   qa-circle-area-circumference-and-sectors-e98b662b
--   qa-reshaping-and-equal-perimeter-problems-ef477223
--   qa-volume-and-surface-area-of-solids-42588cef
--   qa-coordinate-and-line-geometry-eb041f58
--
-- Nothing there is a theorem. A question about the angle in a semicircle, the
-- ratio in which a centroid divides a median, or the value of sin^2 + cos^2 has
-- no defensible leaf, so tagging the 850-question SSC CGL 2024 corpus against
-- today's catalogue would force a wrong tag on every one of them — the same
-- failure migration 277 repaired for NABARD, before it happens.
--
-- ADDITIVE ONLY. Nothing here renames, re-parents, deactivates or deletes a
-- row. The 1,428 existing primary tags point at microtopics that this file does
-- not touch, and migration 270 resolves a tag's level from `parent_topic_id`,
-- which no existing row's value changes. The assertion at the end of this
-- transaction proves it rather than asserting it in a comment.
--
-- BODY-AGNOSTIC. `quantitative-aptitude` is shared with RBI Phase I, CSAT and
-- the regulators, and its rows carry NO `topics.metadata.exams` key; the
-- tooling reads it with `--any-body` and a body filter empties every candidate
-- set (workbench/audit/ssc_cgl/README.md). So no `exams` key is added here. The
-- rows do carry `ssc_cgl_tier1_area`, which names the syllabus area each leaf
-- serves and is not read by any filter.
--
-- PROVENANCE OF THE AREA NAMES. The official SSC notice at ssc.gov.in is not
-- reachable from the build environment (egress proxy), so no line of it is
-- quoted here and `ssc_cgl_tier1_area` carries an area NAME, not a quotation.
-- The names come from the operator brief of 2026-09-23, recorded verbatim in
-- `metadata.source`. Anyone adding the notice text later should append it; this
-- file deliberately does not invent it.
--
-- PARENT RESOLUTION, as migration 277 established. These subject trees were
-- created outside the migration set and exist only in the live database, so a
-- hardcoded parent id is what made migration 269 abort every clean
-- `supabase db reset`. Each row hangs off a named ANCHOR resolved by slug at
-- run time; the join yields zero rows on a database without the tree instead of
-- raising topics_parent_topic_id_fkey. `subject_id` and `metadata` are copied
-- from the anchor for the same reason: this file cannot disagree with the live
-- tree about which subject a row belongs to.
--
-- THE ANCHOR IS THE SEMANTIC CLAIM — "put this beside that":
--   Lines and angles, triangle centres, congruence, circle theorems,
--   quadrilaterals        <- Coordinate and line geometry (the one existing
--                            leaf that is about figures rather than about
--                            measuring them)
--   Median and mode       <- Averages — simple and weighted
--   Trigonometry (macro)  <- the PARENT of Coordinate and line geometry, whose
--                            subject and metadata shape a new macro must match
--
-- TWO CALLS, STATED RATHER THAN BURIED:
--
-- 1. TRIGONOMETRY IS A NEW MACRO. There is no existing macro it could sit
--    under: ratios, identities, complementary angles and heights-and-distances
--    are not mensuration and not coordinate geometry, and hanging them off the
--    geometry macro would make that macro mean two different things.
--
-- 2. STATISTICS IS *NOT* A NEW MACRO. The existing Data Interpretation macro
--    covers reading a table, a pie chart, a bar/line graph and a caselet, and
--    `qa-averages-simple-and-weighted-1f479970` already covers the mean. What
--    is genuinely absent is the median and the mode, which are central
--    tendency — the same idea as an average, not a second kind of chart. So one
--    leaf, `Median and mode`, goes beside Averages.
--
--    The leaf is deliberately NOT named "Mean, median and mode": a plain-mean
--    question would then match two leaves equally well, and an ambiguous
--    candidate set is how a tagging pass produces a tag_conflict instead of a
--    tag. A Statistics macro can be added later if SSC Tier I turns out to test
--    dispersion (standard deviation, mean deviation) as well; nothing in this
--    corpus says it does, and a macro with one child earns nothing.
--
-- IDS ARE DETERMINISTIC: md5('ccp:topic:' || slug)::uuid, not
-- gen_random_uuid(), so a worksheet can name a target topic id before this
-- migration runs. These rows exist nowhere yet, so a migration-built database
-- and the live one converge on the same id.
--
-- SLUG SUFFIX: left(md5(name), 8), the convention migration 273 established and
-- 277 followed. The live QA siblings carry an opaque 8-hex suffix that is NOT
-- md5 of the name (verified: 'Number series — arithmetic and difference
-- patterns' is ...-130693e5 live, ...-4fee191e under md5). These slugs
-- therefore match the SHAPE of their siblings, not their generator — a
-- reproducible slug is worth more than a cosmetic match.
--
-- Guarded twice: WHERE NOT EXISTS on the slug makes a re-run insert nothing,
-- and the anchor join makes an absent tree a no-op.

BEGIN;

-- The pre-existing catalogue, captured before anything is inserted. The
-- assertion at the bottom compares against it: "additive" is a claim about
-- every column of every row, so every column of every row is what is checked.
CREATE TEMP TABLE _topics_before ON COMMIT DROP AS
SELECT id, subject_id, parent_topic_id, slug, name, level, is_active, metadata
  FROM public.topics;


-- ── 1. the Trigonometry macro ─────────────────────────────────────────────
--
-- parent_topic_id IS NULL, level 'topic': that is what makes migration 270
-- resolve a tag on one of its children to (topic_id = this row, microtopic_id =
-- the child) rather than double-counting.

INSERT INTO public.topics
  (id, subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT
  md5('ccp:topic:qa-trigonometry-be895874')::uuid,
  parent.subject_id,
  NULL,
  'qa-trigonometry-be895874',
  'Trigonometry',
  'topic',
  true,
  COALESCE(parent.metadata, '{}'::jsonb) || jsonb_build_object(
    'ssc_cgl_tier1_area', 'Quantitative Aptitude — Trigonometry',
    'source', 'operator brief 2026-09-23; SSC notice text not retrievable in build environment',
    'added_by_migration', '305'
  )
FROM public.topics anchor
JOIN public.topics parent ON parent.id = anchor.parent_topic_id
WHERE anchor.slug = 'qa-coordinate-and-line-geometry-eb041f58'
  AND NOT EXISTS (
    SELECT 1 FROM public.topics t WHERE t.slug = 'qa-trigonometry-be895874'
  );


-- ── 2. microtopics beside an existing leaf ────────────────────────────────

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
    'source', 'operator brief 2026-09-23; SSC notice text not retrievable in build environment',
    'added_by_migration', '305'
  )
FROM (VALUES

  -- Angle pairs on intersecting and parallel lines: vertically opposite,
  -- linear pair, alternate and corresponding angles, and the transversal.
  -- Nothing in the catalogue asks for an angle; the five geometry leaves all
  -- ask for an area, a perimeter or a volume.
  ('qa-coordinate-and-line-geometry-eb041f58',
   'qa-lines-and-angles-f48e31c3',
   'Lines and angles',
   'Quantitative Aptitude — Geometry'),

  -- Centroid, incentre, circumcentre and orthocentre, the medians and the
  -- angle-bisector ratio. "Area and perimeter — rectangle, square, triangle"
  -- is a mensuration leaf and cannot carry a question about where a median
  -- meets another.
  ('qa-coordinate-and-line-geometry-eb041f58',
   'qa-triangle-properties-and-centres-b1451b8f',
   'Triangle properties and centres',
   'Quantitative Aptitude — Geometry'),

  -- SSS/SAS/ASA/RHS, similar triangles, the basic proportionality theorem and
  -- the ratio of areas of similar figures.
  ('qa-coordinate-and-line-geometry-eb041f58',
   'qa-congruence-and-similarity-19870cbb',
   'Congruence and similarity',
   'Quantitative Aptitude — Geometry'),

  -- Equal chords, the perpendicular from the centre, tangent-radius and
  -- tangent-secant, the angle in a semicircle, and cyclic quadrilaterals.
  -- `Circle — area, circumference and sectors` measures a circle; this one
  -- reasons about it.
  ('qa-coordinate-and-line-geometry-eb041f58',
   'qa-circle-theorems-chords-tangents-and-cyclic-quadrilaterals-3a6cb205',
   'Circle theorems — chords, tangents and cyclic quadrilaterals',
   'Quantitative Aptitude — Geometry'),

  -- Properties of parallelograms, rhombi and trapezia, and interior/exterior
  -- angle sums of a regular polygon.
  ('qa-coordinate-and-line-geometry-eb041f58',
   'qa-quadrilaterals-and-polygons-4a164691',
   'Quadrilaterals and polygons',
   'Quantitative Aptitude — Geometry'),

  -- The median and the mode of a list or a frequency distribution. See call 2
  -- in the header for why this is one leaf beside Averages and not a
  -- Statistics macro, and why the mean is not named here.
  ('qa-averages-simple-and-weighted-1f479970',
   'qa-median-and-mode-9fcb6443',
   'Median and mode',
   'Quantitative Aptitude — Central tendency')

) AS v(anchor_slug, slug, name, area)
JOIN public.topics a ON a.slug = v.anchor_slug
WHERE NOT EXISTS (
  SELECT 1 FROM public.topics t WHERE t.slug = v.slug
);


-- ── 3. microtopics under the new Trigonometry macro ───────────────────────
--
-- Anchored on the macro this migration inserted above, by slug like every
-- other anchor here. On a database where step 1 inserted nothing — because the
-- tree is absent — this join finds no parent and inserts nothing either.

INSERT INTO public.topics
  (id, subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT
  md5('ccp:topic:' || v.slug)::uuid,
  m.subject_id,
  m.id,
  v.slug,
  v.name,
  'microtopic',
  true,
  COALESCE(m.metadata, '{}'::jsonb) || jsonb_build_object(
    'ssc_cgl_tier1_area', 'Quantitative Aptitude — Trigonometry',
    'source', 'operator brief 2026-09-23; SSC notice text not retrievable in build environment',
    'added_by_migration', '305'
  )
FROM (VALUES

  -- sin/cos/tan and their reciprocals, the Pythagorean identities, and values
  -- at the standard angles.
  ('qa-trigonometric-ratios-and-identities-179e3e31',
   'Trigonometric ratios and identities'),

  -- sin(90 - x) = cos x and the rest of the pair, which SSC tests as its own
  -- item type rather than as a step inside an identity question.
  ('qa-complementary-angles-c7318569',
   'Complementary angles'),

  -- Angle of elevation and depression, the observer and the tower. The
  -- reasoning catalogue's `Shortest distance by Pythagoras` is a different
  -- subject and cannot serve a QA question.
  ('qa-heights-and-distances-7268e06f',
   'Heights and distances')

) AS v(slug, name)
JOIN public.topics m ON m.slug = 'qa-trigonometry-be895874'
WHERE NOT EXISTS (
  SELECT 1 FROM public.topics t WHERE t.slug = v.slug
);


-- ── 4. prove the claim in the header ──────────────────────────────────────
--
-- Every row that existed before this transaction must still exist, unchanged
-- in every column. A rename, a re-parent, a deactivation or a delete fails the
-- migration here rather than being discovered later as a broken tag.

DO $$
DECLARE
  changed bigint;
  removed bigint;
BEGIN
  SELECT count(*) INTO removed
  FROM _topics_before b
  WHERE NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.id = b.id);
  IF removed > 0 THEN
    RAISE EXCEPTION 'migration 305 is additive only, but % existing topic row(s) disappeared', removed;
  END IF;

  SELECT count(*) INTO changed
  FROM _topics_before b
  JOIN public.topics t ON t.id = b.id
  WHERE (t.subject_id, t.parent_topic_id, t.slug, t.name, t.level, t.is_active, t.metadata)
     IS DISTINCT FROM
        (b.subject_id, b.parent_topic_id, b.slug, b.name, b.level, b.is_active, b.metadata);
  IF changed > 0 THEN
    RAISE EXCEPTION 'migration 305 is additive only, but % existing topic row(s) changed', changed;
  END IF;
END $$;

NOTIFY pgrst, 'reload schema';

COMMIT;
