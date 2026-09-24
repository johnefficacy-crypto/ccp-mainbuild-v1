-- Migration 308: one reasoning leaf SSC CGL 2024 Tier I needs, and the
-- reference audit that decides whether the `english-language` bare-slug rows
-- can be retired.
--
-- Follows 305 (QA) and 306 (GIR + English item types). Same guards, same
-- conventions, same body-agnostic subjects.
--
-- ── PART 1: ADD `Venn diagram` to general-intelligence-reasoning ────────────
--
-- Evidence: 5 occurrences across the SSC CGL 2024 Tier I corpus — papers
-- 3d903cdf (x2), 55571471, 64b4c673 (x2) — of two- and three-set counting
-- questions ("In a group of 50, 30 play cricket, 25 hockey, 10 both; how many
-- play neither"). No leaf exists: the subject has two syllogism leaves and a
-- `Letter and digit pair counting` leaf, and neither is a set-cardinality
-- question.
--
--   Venn diagram   <- Two-statement syllogism (reas-two-statement-syllogism-7f65e035)
--
-- ANCHORED ON THE SYLLOGISM LEAF, deliberately. The Venn diagram is the
-- syllogism family's representation: both are questions about the regions of
-- overlapping sets, one with quantifiers ("all A are B") and one with
-- cardinalities ("30 play cricket"). The alternative anchors are worse — the
-- counting leaf is about letter/digit pairs inside a word, and the arrangement
-- leaves are about seats and positions.
--
-- THE MACRO. This row inherits `a.parent_topic_id`, so it lands in the same
-- macro as the syllogism leaves and is their sibling, not their child. That
-- macro's NAME is not in this repository: the QRE subject tree was created
-- outside the migration set (see 277's header), and the committed catalogue
-- export carries leaves only. To print it after applying:
--
--   SELECT parent.slug, parent.name
--     FROM public.topics t
--     JOIN public.topics parent ON parent.id = t.parent_topic_id
--    WHERE t.slug = 'reas-venn-diagram-360f6cdd';
--
-- ── PART 2: the `english-language` bare-slug rows are NOT retired ───────────
--
-- `workbench/reports/ENGLISH-CATALOGUE-DUPLICATE-PAIRS-2026-09-23.md` reported
-- seven bare-slug rows as the legacy halves of duplicate pairs, and the live tag
-- counts taken on demo 2026-09-23 show every PYQ tag sitting on the `eng-*` row:
--
--   eng-subject-verb-agreement-07be8ac5           5 | subject-verb-agreement 0
--   eng-preposition-and-article-errors-000b76d8   1 | prepositions 0, articles 0
--   eng-word-order-and-modifier-placement-1b73c44c 3 | modifiers 0
--   eng-pronoun-reference-and-agreement-d6412298  0 | pronoun-reference 0
--   eng-redundancy-and-wordiness-1787d0ac         0 | redundancy 0
--   eng-tense-and-sequence-of-tenses-7e82f0cb     0 | tense 0
--
-- THAT READING WAS WRONG, AND THE REPORT IS CORRECTED BY THIS FILE. The seven
-- bare-slug rows carry no PYQ tags because they are not PYQ rows. They are the
-- ENGLISH WRITING PRACTICE taxonomy, seeded by migration 205 under the EWP
-- macros `grammar`, `sentence-construction`, `vocabulary-in-context` and
-- `paragraph-writing`, and every one of them is the live target of a row in
-- `public.writing_issue_type_microtopic_map` (205 §17, seeded at 205's `maps`
-- array, read at runtime by 209's evaluator and 213's Error Lab read model):
--
--   issue_type `subject_verb_agreement` -> subject-verb-agreement
--   issue_type `tense`                  -> tense
--   issue_type `article`                -> articles
--   issue_type `preposition`            -> prepositions
--   issue_type `pronoun_reference`      -> pronoun-reference
--   issue_type `modifier`               -> modifiers
--   issue_type `redundancy`             -> redundancy
--
-- `writing_issue_type_microtopic_map.microtopic_id` is `NOT NULL REFERENCES
-- public.topics(id)` with no ON DELETE clause, i.e. NO ACTION. So the retirement
-- the report proposed is not a cleanup that loses a duplicate — it would either
-- raise a foreign-key violation or, on the seventeen FK columns that cascade,
-- silently delete a learner's mastery and error history.
--
-- `english-language` holds TWO TREES IN ONE SUBJECT, not one tree with
-- duplicates: EWP's writing-assessment criteria (bare slugs, what a marker
-- judges in a candidate's own prose) and the MCQ item-type catalogue (`eng-*`
-- slugs, what a four-option question tests). 306 already acted on exactly this
-- distinction for `Logical Order`. It holds for the whole grammar block.
--
-- WHAT THIS FILE DOES INSTEAD. It runs the audit the brief asked for, over
-- EVERY foreign key that points at `public.topics(id)` — discovered from
-- `pg_constraint` at run time, not from a list in this file, so a table added
-- after this migration is still covered, and composite FKs are covered by
-- aligning `conkey` with the `confkey` position of `topics.id`. For each
-- candidate it prints the referencing tables and counts, deletes ONLY a row with
-- zero references and zero child topics, and SKIPS any row that is referenced,
-- naming it and why. The migration does not abort: an un-retirable row is the
-- expected outcome, not an error.
--
-- On demo and production all seven are expected to be SKIPPED, each referenced
-- by at least `writing_issue_type_microtopic_map`. On a database with no EWP
-- taxonomy the rows do not exist and each is reported ABSENT. Both are fine.
--
-- `articles` SPECIFICALLY. The report flagged `prepositions`/`articles` as a 2:2
-- split on a different axis from the modern pair, and proposed a per-question
-- worksheet before any merge. That worksheet is moot: `articles` is EWP's
-- `article` issue type, so it is not the legacy half of anything and there is
-- nothing to merge. It is audited here like the rest and skipped for the same
-- reason.
--
-- ── shared guards ──────────────────────────────────────────────────────────
--
-- Additive except for the audited deletes, and the assertion at the bottom
-- proves it: every pre-existing row is unchanged in every column, and the only
-- rows permitted to be missing are candidates the audit deleted after finding
-- them unreferenced. IDS md5('ccp:topic:' || slug)::uuid. SLUG SUFFIX
-- left(md5(name), 8). No `metadata.exams` key — these subjects are shared with
-- RBI Phase I, CSAT and the regulators and the tooling runs `--any-body`.
-- Idempotent: the insert is guarded on the slug, and a second apply finds the
-- candidates already gone (or still referenced) and reports it.

BEGIN;

CREATE TEMP TABLE _topics_before_308 ON COMMIT DROP AS
SELECT id, subject_id, parent_topic_id, slug, name, level, is_active, metadata
  FROM public.topics;

-- ── part 1 ────────────────────────────────────────────────────────────────

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
    'source', 'SSC CGL 2024 Tier I corpus, 5 occurrences; papers 3d903cdf x2, 55571471, 64b4c673 x2',
    'added_by_migration', '308'
  )
FROM (VALUES
  ('reas-two-statement-syllogism-7f65e035',
   'reas-venn-diagram-360f6cdd',
   'Venn diagram',
   'General Intelligence and Reasoning — Venn diagram and set counting')
) AS v(anchor_slug, slug, name, area)
JOIN public.topics a ON a.slug = v.anchor_slug
WHERE NOT EXISTS (
  SELECT 1 FROM public.topics t WHERE t.slug = v.slug
);

-- ── part 2: the reference audit ───────────────────────────────────────────

CREATE TEMP TABLE _retire_audit_308 (
  slug        text PRIMARY KEY,
  topic_id    uuid,
  verdict     text NOT NULL,   -- retired | skipped | absent
  children    bigint NOT NULL DEFAULT 0,
  refs        bigint NOT NULL DEFAULT 0,
  referenced_by text
) ON COMMIT DROP;

DO $$
DECLARE
  v_subject   uuid;
  cand        text;
  v_id        uuid;
  v_children  bigint;
  v_total     bigint;
  v_n         bigint;
  v_detail    text[];
  fk          record;
  -- The seven rows the duplicate-pair report proposed retiring. `articles` is
  -- included because the report named it, not because it was ever a pair.
  candidates  text[] := ARRAY[
    'subject-verb-agreement', 'tense', 'articles', 'prepositions',
    'pronoun-reference', 'modifiers', 'redundancy'
  ];
BEGIN
  SELECT id INTO v_subject FROM public.subjects WHERE slug = 'english-language';
  IF v_subject IS NULL THEN
    RAISE NOTICE 'migration 308: no english-language subject; audit skipped';
    RETURN;
  END IF;

  FOREACH cand IN ARRAY candidates LOOP
    SELECT id INTO v_id
      FROM public.topics
     WHERE subject_id = v_subject AND slug = cand;

    IF v_id IS NULL THEN
      INSERT INTO _retire_audit_308 (slug, topic_id, verdict) VALUES (cand, NULL, 'absent');
      RAISE NOTICE 'migration 308: % is ABSENT in english-language; nothing to retire', cand;
      CONTINUE;
    END IF;

    -- Child topics. A parent with children cannot be removed whatever else is
    -- true: the children would be cascaded away with it.
    SELECT count(*) INTO v_children
      FROM public.topics WHERE parent_topic_id = v_id;

    -- Every FK that points at public.topics(id), read from the catalog rather
    -- than listed here. `generate_subscripts` over `confkey` aligns each
    -- referencing column with the referenced one, so a composite FK is counted
    -- on its topic column and not on its first column.
    v_total  := 0;
    v_detail := ARRAY[]::text[];
    FOR fk IN
      SELECT c.conrelid::regclass::text AS tbl,
             a.attname                  AS col,
             c.confdeltype              AS del
        FROM pg_constraint c
        CROSS JOIN LATERAL generate_subscripts(c.confkey, 1) AS s(i)
        JOIN pg_attribute fa ON fa.attrelid = c.confrelid AND fa.attnum = c.confkey[s.i]
        JOIN pg_attribute a  ON a.attrelid  = c.conrelid  AND a.attnum  = c.conkey[s.i]
       WHERE c.contype = 'f'
         AND c.confrelid = 'public.topics'::regclass
         AND fa.attname  = 'id'
         -- topics.parent_topic_id is the child check above, counted separately.
         AND NOT (c.conrelid = 'public.topics'::regclass AND a.attname = 'parent_topic_id')
       ORDER BY 1, 2
    LOOP
      EXECUTE format('SELECT count(*) FROM %s WHERE %I = $1', fk.tbl, fk.col)
        INTO v_n USING v_id;
      IF v_n > 0 THEN
        v_total  := v_total + v_n;
        -- `confdeltype` is "char", so every arm is cast to text: a CASE that
        -- unified on "char" would truncate 'CASCADE' to 'C'.
        v_detail := v_detail || format('%s.%s=%s (on delete %s)', fk.tbl, fk.col, v_n,
          CASE fk.del WHEN 'a' THEN 'no action'::text WHEN 'r' THEN 'restrict'::text
                      WHEN 'c' THEN 'CASCADE'::text   WHEN 'n' THEN 'set null'::text
                      WHEN 'd' THEN 'set default'::text ELSE fk.del::text END);
      END IF;
    END LOOP;

    IF v_total = 0 AND v_children = 0 THEN
      DELETE FROM public.topics WHERE id = v_id;
      INSERT INTO _retire_audit_308 (slug, topic_id, verdict) VALUES (cand, v_id, 'retired');
      RAISE NOTICE 'migration 308: % (%) RETIRED — zero references, zero children', cand, v_id;
    ELSE
      INSERT INTO _retire_audit_308 (slug, topic_id, verdict, children, refs, referenced_by)
      VALUES (cand, v_id, 'skipped', v_children, v_total,
              array_to_string(v_detail, ', '));
      RAISE NOTICE 'migration 308: % (%) KEPT — % child topic(s), % referencing row(s)%',
        cand, v_id, v_children, v_total,
        CASE WHEN v_detail = ARRAY[]::text[] THEN ''
             ELSE ' in ' || array_to_string(v_detail, ', ') END;
    END IF;
  END LOOP;

  RAISE NOTICE 'migration 308 audit: % retired, % kept, % absent',
    (SELECT count(*) FROM _retire_audit_308 WHERE verdict = 'retired'),
    (SELECT count(*) FROM _retire_audit_308 WHERE verdict = 'skipped'),
    (SELECT count(*) FROM _retire_audit_308 WHERE verdict = 'absent');
END $$;

-- ── prove nothing unintended changed ──────────────────────────────────────

DO $$
DECLARE
  changed    bigint;
  removed    bigint;
  stray      text;
  added      bigint;
BEGIN
  -- Every pre-existing row still present is unchanged in every column.
  SELECT count(*) INTO changed
  FROM _topics_before_308 b
  JOIN public.topics t ON t.id = b.id
  WHERE (t.subject_id, t.parent_topic_id, t.slug, t.name, t.level, t.is_active, t.metadata)
     IS DISTINCT FROM
        (b.subject_id, b.parent_topic_id, b.slug, b.name, b.level, b.is_active, b.metadata);
  IF changed > 0 THEN
    RAISE EXCEPTION 'migration 308 changed % existing topic row(s); it may only add and retire', changed;
  END IF;

  -- The only rows allowed to be gone are ones the audit retired.
  SELECT count(*) INTO removed
  FROM _topics_before_308 b
  WHERE NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.id = b.id);

  SELECT string_agg(b.slug, ', ') INTO stray
  FROM _topics_before_308 b
  WHERE NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.id = b.id)
    AND NOT EXISTS (SELECT 1 FROM _retire_audit_308 r
                     WHERE r.topic_id = b.id AND r.verdict = 'retired');
  IF stray IS NOT NULL THEN
    RAISE EXCEPTION 'migration 308 removed topic row(s) the audit did not retire: %', stray;
  END IF;

  -- Exactly one row is added, and only on a database carrying the anchor.
  SELECT count(*) INTO added
  FROM public.topics t
  WHERE NOT EXISTS (SELECT 1 FROM _topics_before_308 b WHERE b.id = t.id);
  IF added > 1 THEN
    RAISE EXCEPTION 'migration 308 inserted % rows; exactly one leaf is expected', added;
  END IF;

  RAISE NOTICE 'migration 308: % row(s) added, % row(s) retired, 0 changed', added, removed;
END $$;

NOTIFY pgrst, 'reload schema';

COMMIT;
