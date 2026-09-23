# english-language: duplicate leaf pairs under two naming conventions

**Status: report only. Nothing in migration 306 or anywhere else in this PR changes,
renames, re-parents or retires any row named below.**

Subject: `english-language` = `55555555-5555-5555-5555-555555555552` (16 macro / 68
microtopics before migration 306, 71 after). Body-agnostic — no
`topics.metadata.exams` key — and shared by SSC CGL, RBI Phase I, CSAT and the
regulators, which is why a merge here is a four-body decision and not a
tagging-pass decision.

Source: `workbench/catalogs/topic_catalog_nabard_277.json`, the committed
post-277 microtopic export. Its `logical-order` id matches the one the operator
brief quoted, so the dump is current.

---

## 1. What the two conventions are

Two generations of rows sit in the same subject:

| | slug shape | name shape | added by |
| --- | --- | --- | --- |
| **legacy** | bare kebab noun (`prepositions`) | Title Case (`Prepositions`) | the original English seed |
| **modern** | `eng-<kebab-name>-<left(md5(name),8)>` | sentence case (`Preposition and article errors`) | migrations 273 / 277, and 306 |

The modern shape is the convention every migration since 273 has followed and
the one this PR's six new leaves follow. That makes the modern row the
**presumptive canonical** one in each pair — but presumption is not evidence,
and the tag counts that would settle it are not available offline (§4).

## 2. The pairs — six, not four

The brief names four. Sweeping the export for **every** legacy row whose whole
name is contained in a modern row's name (case- and plural-insensitive, function
words dropped) finds **two more**, and shows that one of the four is not a pair
at all. The rule and the sweep are in
`app/backend/tests/test_gir_english_item_type_migration.py::test_the_report_finds_every_legacy_shaped_slug_subsumed_by_a_modern_one`,
so a seventh appearing in a later export fails a test instead of going unnoticed.

| # | legacy | modern | verdict |
| --- | --- | --- | --- |
| 2.1 | `subject-verb-agreement` | `eng-subject-verb-agreement-07be8ac5` | true 1:1 duplicate |
| 2.2 | `pronoun-reference` | `eng-pronoun-reference-and-agreement-d6412298` | 1:1, modern wider |
| 2.3 | `redundancy` | `eng-redundancy-and-wordiness-1787d0ac` | 1:1, modern wider |
| 2.4 | `prepositions` + `articles` | `…-article-errors-…` + `…-phrasal-completion-…` | **not a pair — 2:2 on a different axis** |
| 2.5 | `tense` | `eng-tense-and-sequence-of-tenses-7e82f0cb` | **not in the brief** — 1:1, modern wider |
| 2.6 | `modifiers` | `eng-word-order-and-modifier-placement-1b73c44c` | **not in the brief** — 1:1, modern wider |

### 2.1 Subject-verb agreement — a true 1:1 duplicate

| | slug | id | name |
| --- | --- | --- | --- |
| legacy | `subject-verb-agreement` | `b9facc82-38d7-f725-7c97-8b5894c157f0` | Subject-Verb Agreement |
| modern | `eng-subject-verb-agreement-07be8ac5` | `7c71b869-e50a-4ebd-aea1-fe291dbee5ed` | Subject-verb agreement |

Same scope, same words, differing only in case. No reading of either name
excludes a question the other admits. **Mergeable as-is.**

### 2.2 Pronoun reference — 1:1, modern name is strictly wider

| | slug | id | name |
| --- | --- | --- | --- |
| legacy | `pronoun-reference` | `c6beb287-3fef-397f-e204-57f8e4053328` | Pronoun Reference |
| modern | `eng-pronoun-reference-and-agreement-d6412298` | `ee103c0c-a9fa-4ae8-98dd-78cdc4378732` | Pronoun reference and agreement |

The modern name adds "and agreement", i.e. number/gender concord, which is not
reference. Every legacy-tagged question is still in scope under the modern name;
the reverse is not guaranteed. **Mergeable legacy → modern, not modern → legacy.**

### 2.3 Redundancy — 1:1, modern name is strictly wider

| | slug | id | name |
| --- | --- | --- | --- |
| legacy | `redundancy` | `84fae1ba-f1d4-98da-1c09-45c51ceb2e22` | Redundancy |
| modern | `eng-redundancy-and-wordiness-1787d0ac` | `e6e0700f-0130-49e0-961d-89cbe5eab3f8` | Redundancy and wordiness |

Same as 2.2: wordiness is a superset of redundancy in SSC usage (a redundant
phrase is wordy; a wordy sentence need not repeat itself).
**Mergeable legacy → modern.**

### 2.4 Prepositions — **not a pair. 2 legacy rows against 2 modern rows, split on a different axis.**

| | slug | id | name |
| --- | --- | --- | --- |
| legacy | `prepositions` | `5db857e5-5b9d-2f80-0046-1978c199ed85` | Prepositions |
| legacy | `articles` | `b790ab2c-17e8-9025-f313-2c44d24dac8d` | Articles |
| modern | `eng-preposition-and-article-errors-000b76d8` | `f9c12eec-a497-4d10-b219-2da6b28a92f7` | Preposition and article errors |
| modern | `eng-preposition-and-phrasal-completion-5c07ccb9` | `613e6076-97c1-4a2b-b932-8831642cf075` | Preposition and phrasal completion |

The brief names `prepositions` / `eng-preposition-and-article-errors-…` as a
pair. It is not one, in two ways:

1. The modern row **merges two parts of speech** (preposition + article) that the
   legacy rows keep apart. Merging `prepositions` into it silently retires
   `articles`' distinction too; merging `articles` into it as well makes it a 2→1
   collapse, which loses the ability to answer "how many article questions does
   SSC CGL ask".
2. There is a **second** modern preposition leaf,
   `eng-preposition-and-phrasal-completion-5c07ccb9`, which the brief does not
   mention. The modern pair splits on **task type** (spot the error vs. fill the
   blank); the legacy pair splits on **part of speech**. A tag on `prepositions`
   does not say which modern row it belongs to, so this cannot be merged by rule
   at all — only by looking at each tagged question.

**Not mergeable without a per-question pass.** Recommendation in §3.

### 2.5 Tense — **not in the brief.** 1:1, modern name is strictly wider

| | slug | id | name |
| --- | --- | --- | --- |
| legacy | `tense` | `aa680736-24d9-abb2-d7f2-ad3bcb2acb77` | Tense |
| modern | `eng-tense-and-sequence-of-tenses-7e82f0cb` | `f146f9b5-b13d-47c0-8aca-c80a6566b4fe` | Tense and sequence of tenses |

Same relationship as 2.2 and 2.3: the modern name adds sequence of tenses, which
a bare "Tense" does not exclude. **Mergeable legacy → modern.**

### 2.6 Modifiers — **not in the brief.** 1:1, modern name is strictly wider

| | slug | id | name |
| --- | --- | --- | --- |
| legacy | `modifiers` | `aca53761-13fc-65c9-bd3c-9f324e9a589f` | Modifiers |
| modern | `eng-word-order-and-modifier-placement-1b73c44c` | `3ab068c5-397c-4189-913f-0d26569b3899` | Word order and modifier placement |

A misplaced-modifier question is a modifier question. The modern name also
covers word order generally, so it is the wider of the two.
**Mergeable legacy → modern.**

### 2.7 Interaction with migration 306 — none, but worth knowing

The two newly found pairs are exactly the two English **anchors** migration 306
hangs its leaves off, in their modern form:
`eng-tense-and-sequence-of-tenses-7e82f0cb` (voice and narration) and
`eng-word-order-and-modifier-placement-1b73c44c` (para jumble).

306 is not coupled to them. It inherits `a.parent_topic_id` — the anchor's
**macro** — not the anchor's id, so the new leaves are the anchor's siblings.
Deactivating the anchor in a later merge does not orphan or move them.

One thing a merge decision does have to check, and cannot be checked from the
committed export (which is leaves-only, no parents): **if the merge picks the
legacy row as canonical and that row sits under a different macro**, the merged
content ends up in one macro while 306's new leaves sit in another. Query (b) in
§4 returns the parents; run it before choosing a direction for 2.5 and 2.6.

### 2.8 Rows that look like pairs and are not

The same sweep turns up five legacy rows sharing one significant word with a
modern row and nothing more — `Simple Sentences`, `Compound Sentences`,
`Complex Sentences`, `Sentence Transformation`, `Sentence Structure` against
`Word interchange within a sentence`; also `Word Choice` / `Word Limit` against
`Word-pair fit`, `Topic Sentence`, `Formal Vocabulary`, and `Logical Order`
against `Word order and modifier placement`.

None is a duplicate. The legacy rows are a **descriptive-writing assessment**
vocabulary — what a marker judges in a candidate's own prose — and the modern
rows are **MCQ item types**. The overlap is the word "sentence" or "word", not
the scope. This is the same distinction migration 306 acts on: it does not move
the five para jumbles off `Logical Order`, it gives them an item-type leaf to be
re-tagged onto by a reviewed worksheet. **Leave all of these alone.**

## 3. Proposed merge plan — ship nothing until the counts in §4 exist

Preconditions for any of it: the counts in §4 are read from the live database,
and the chosen canonical row is confirmed to be the one the newer worksheets
target.

**Step 0 — decide direction from evidence, not from convention.** For each pair,
if the legacy row carries materially more verified tags than the modern one, the
cheaper and less destructive merge may be modern → legacy. The convention argues
for modern; the tag counts decide.

**Step 1 — pairs 2.1, 2.2, 2.3, 2.5, 2.6 only. Re-point tags, then deactivate.
Never delete.**

```sql
-- Per pair, in one transaction, with <from>/<to> from the decision in step 0.
UPDATE public.pyq_question_topic_tags g
   SET topic_id = '<to>'
 WHERE g.topic_id = '<from>'
   AND NOT EXISTS (                     -- a question already carrying both
     SELECT 1 FROM public.pyq_question_topic_tags h
      WHERE h.question_id = g.question_id
        AND h.topic_id = '<to>'
        AND h.tag_role = g.tag_role);
DELETE FROM public.pyq_question_topic_tags g   -- the collisions just skipped
 WHERE g.topic_id = '<from>';
UPDATE public.topics SET is_active = false WHERE id = '<from>';
```

Notes that make this safe rather than merely short:

- The `NOT EXISTS` guard exists because the unique constraint on
  `(question_id, topic_id, tag_role)` would abort the whole UPDATE on the first
  question tagged with both rows. Such questions exist wherever a later pass
  re-tagged without removing the old tag.
- **`is_active = false`, not `DELETE FROM public.topics`.** Per CLAUDE.md,
  retire ≠ archive, and a deleted topic id breaks every historical worksheet,
  export and evidence record that names it. The row stays readable; it stops
  being offered.
- `catalog_rows` drops `is_active = false` rows, so the deactivated leaf leaves
  the proposer's candidate set on the next export and no new tag can land on it.
- This must be a **migration**, numbered after 306, not a console edit: it
  changes rows other bodies' tags point at, and the change has to be replayable
  on a clean `supabase db reset`.
- It is **not additive**, so it cannot share a migration with 306 or with
  anything else; and unlike 306 it needs a documented review, because four exam
  bodies read this subject.

**Step 2 — pair 2.4. No merge. A worksheet first.**

Export every verified tag on `prepositions` and `articles` with its question
text, and have the operator assign each to one of the two modern rows by task
type. Only then is there a mapping to write. Until that worksheet is reviewed,
all four rows stay live: an unmergeable pair left alone costs a duplicate in the
catalogue, while a guessed merge costs the per-part-of-speech counts permanently.

**Step 3 — after either step, re-export the catalogue** and re-run
`node scripts/operator-validation.js --check`, and record the merge as an
operator-validation gate at `validation_pending` until the deployed path is
re-read. Code completion is not operator validation.

## 4. The per-exam tag counts the brief asked for — NOT PRODUCED HERE, and why

The brief asks for "each pair with its tag counts per exam". **Those counts are
not in this report and could not be computed in this environment:**

- `workbench/audit/ssc_cgl/` contains only `README.md` and
  `ssc_section_aliases.json`. **There is no `drafts/` directory in the
  repository** — the 122 tagged drafts from the two operator passes are the
  operator's local files and were never committed.
- This session has no live database credentials and makes no live reads; the
  committed catalogue export carries slugs, ids, names and subjects only, with no
  tag rows and no per-exam attribution.

Reporting a plausible number here would be a fabrication, so none is reported.
Run this to get them — it is the missing half of this report, and the input to
step 0 above:

```sql
-- Verified primary and secondary tag counts per pair member, per exam body.
WITH pair(member, topic_id) AS (VALUES
  ('subject-verb-agreement',                    'b9facc82-38d7-f725-7c97-8b5894c157f0'::uuid),
  ('eng-subject-verb-agreement-07be8ac5',       '7c71b869-e50a-4ebd-aea1-fe291dbee5ed'),
  ('prepositions',                              '5db857e5-5b9d-2f80-0046-1978c199ed85'),
  ('articles',                                  'b790ab2c-17e8-9025-f313-2c44d24dac8d'),
  ('eng-preposition-and-article-errors-000b76d8','f9c12eec-a497-4d10-b219-2da6b28a92f7'),
  ('eng-preposition-and-phrasal-completion-5c07ccb9','613e6076-97c1-4a2b-b932-8831642cf075'),
  ('pronoun-reference',                         'c6beb287-3fef-397f-e204-57f8e4053328'),
  ('eng-pronoun-reference-and-agreement-d6412298','ee103c0c-a9fa-4ae8-98dd-78cdc4378732'),
  ('redundancy',                                '84fae1ba-f1d4-98da-1c09-45c51ceb2e22'),
  ('eng-redundancy-and-wordiness-1787d0ac',     'e6e0700f-0130-49e0-961d-89cbe5eab3f8'),
  ('tense',                                     'aa680736-24d9-abb2-d7f2-ad3bcb2acb77'),
  ('eng-tense-and-sequence-of-tenses-7e82f0cb', 'f146f9b5-b13d-47c0-8aca-c80a6566b4fe'),
  ('modifiers',                                 'aca53761-13fc-65c9-bd3c-9f324e9a589f'),
  ('eng-word-order-and-modifier-placement-1b73c44c','3ab068c5-397c-4189-913f-0d26569b3899')
)
SELECT p.member,
       COALESCE(e.slug, '(no exam)')                      AS exam,
       g.tag_role,
       g.reviewer_status,
       count(*)                                           AS tags,
       count(DISTINCT g.question_id)                      AS questions
  FROM pair p
  JOIN public.pyq_question_topic_tags g ON g.topic_id = p.topic_id
  JOIN public.pyq_questions q           ON q.id = g.question_id
  LEFT JOIN public.pyq_papers pp        ON pp.id = q.pyq_paper_id
  LEFT JOIN public.exams e              ON e.id = pp.exam_id
 GROUP BY 1, 2, 3, 4
 ORDER BY 1, 2, 3, 4;
```

Two companion reads the plan also needs:

```sql
-- (a) Questions carrying BOTH members of a pair: these are the rows the
--     NOT EXISTS guard in step 1 skips, and the count tells you how many
--     tags the DELETE removes.
SELECT a.topic_id AS legacy, b.topic_id AS modern, count(*) AS both
  FROM public.pyq_question_topic_tags a
  JOIN public.pyq_question_topic_tags b
    ON b.question_id = a.question_id AND b.tag_role = a.tag_role
 WHERE (a.topic_id, b.topic_id) IN (
   ('b9facc82-38d7-f725-7c97-8b5894c157f0','7c71b869-e50a-4ebd-aea1-fe291dbee5ed'),
   ('c6beb287-3fef-397f-e204-57f8e4053328','ee103c0c-a9fa-4ae8-98dd-78cdc4378732'),
   ('84fae1ba-f1d4-98da-1c09-45c51ceb2e22','e6e0700f-0130-49e0-961d-89cbe5eab3f8'))
 GROUP BY 1, 2;

-- (b) Which macro each member sits under. The committed export is leaves-only,
--     so the parents are unknown offline. A pair split across two macros is a
--     different problem from a pair inside one, and changes the plan.
SELECT t.slug, t.name, t.level, t.is_active, parent.slug AS macro
  FROM public.topics t
  LEFT JOIN public.topics parent ON parent.id = t.parent_topic_id
 WHERE t.subject_id = '55555555-5555-5555-5555-555555555552'
   AND t.slug IN ('subject-verb-agreement','eng-subject-verb-agreement-07be8ac5',
                  'prepositions','articles','eng-preposition-and-article-errors-000b76d8',
                  'eng-preposition-and-phrasal-completion-5c07ccb9',
                  'pronoun-reference','eng-pronoun-reference-and-agreement-d6412298',
                  'redundancy','eng-redundancy-and-wordiness-1787d0ac',
                  'tense','eng-tense-and-sequence-of-tenses-7e82f0cb',
                  'modifiers','eng-word-order-and-modifier-placement-1b73c44c')
 ORDER BY macro, t.slug;
```

## 5. Same check on the other two shared catalogues

Run over the export for completeness, since both were grown the same way:

- `general-intelligence-reasoning` (`…553`): **no duplicate pair.** All 59 leaves
  carry the `reas-` prefix.
- `quantitative-aptitude` (`…551`): **no duplicate pair, but two legacy-shaped
  slugs survive** —
  `permutations-and-combinations` (`de0e24eb-5c25-4e0f-8eeb-325b8732f9cc`,
  "Permutations, combinations and counting") and
  `clocks-and-calendars` (`484fbb39-85bd-4c88-88b3-9426befa6b49`,
  "Clocks and calendars"). Neither has a `qa-`-prefixed twin, so there is nothing
  to merge and no tag to re-point. They are a cosmetic inconsistency only:
  the slug is an opaque key, `catalog_rows` and `build_candidates` match on
  `name`, and renaming a slug would invalidate every worksheet that names it.
  **Recommendation: leave both. Do not "normalise" a slug to match a
  convention — that is a rename of a live row for no functional gain.**

The duplication proper is specific to `english-language`, whose original seed
predates the prefix convention and was later re-seeded rather than extended.
