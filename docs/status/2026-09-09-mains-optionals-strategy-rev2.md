# UPSC Mains optionals — corpus strategy, revision 2

Supersedes `docs/status/2026-09-05-mains-optionals-strategy.md` on the loading
model only. Its §"shared microtopics", §"catalogue construction" and §"difficulty"
sections stand unchanged and are not restated here.

Written 2026-09-09, after OPT-FRONTLOAD-01 and the preflight queries.

---

## What changed, and why the first version could not have caught it

Revision 1 assumed the corpus would load as papers, and asked in §4 how the
1,131 descriptive Mains GS questions got past the importer. Both premises were
wrong, and each was only visible against live data.

**Finding 1 — bulk import was never the path.** `descriptive` is in
`_QUESTION_TYPES` (`pyq_bulk_import.py:178`) but absent from
`_QUESTION_TYPES_V2_SUPPORTED` (`:208`); v1 accepts the type and rejects the
shape (`:312-323`). Neither path loads a row with no options. The 1,131 went in
one at a time through the CMS route.

**Finding 2 — UPSC Mains uses one paper row per year, not per subject.** Live
count is 13 papers for 13 years. GS1–GS4 and Essay share a single
`pyq_paper_id`; sections separate them. This is why `question_number` and
`display_order` are globally unique per paper and why the 1–20 / 21–40 / 41–60 /
61–79 / 80–87 offset convention exists.

Revision 1's plan would have created 139 paper rows against an exam that has
never had more than one per year.

---

## The loading model

**Decision M1. Optionals load as sections inside a per-year optional paper row —
one row per year, not one per subject, and not shared with the GS year-paper.**

Three models were considered.

| | Paper rows | Explorer cards added | Provenance |
|---|---|---|---|
| A — one paper per subject-year | 139 | 139 | clean |
| B1 — sections on the existing GS year-papers | 0 | 0 | **broken** |
| **B2 — one optional paper per year** | **16** | **16** | **clean** |

**A is rejected**: it breaks the year-paper convention and takes the PYQ
Explorer to 165 cards, 3.8× the 43 that already made SEBI unusable. UPSC would
cross that threshold at roughly the seventeenth optional paper.

**B1 is rejected on provenance, and this is the load-bearing reason.** The 13
existing year-papers are `source_type='official'`, `trust_status='verified'`
(26 of 27 UPSC papers verified; 23 of those anchored on `source_url` alone).
The `pyq_readiness` three-gate rule requires `pyq_papers.trust_status =
'verified'`. Hanging coaching-compiled questions off an official verified paper
makes them readiness-eligible as soon as their own review passes, and makes
D9 unenforceable at the level it is written. Paper-level provenance would
assert something false.

**B2 is adopted.** One `pyq_papers` row per year, `source_type='aggregator'`,
`trust_status='pending'`, holding every optional subject for that year as
sections. Preserves the year-paper shape, keeps provenance truthful at the level
the readiness rule reads, and adds 16 cards rather than 139 — total 43.

### Consequences of M1, stated so they are not discovered later

- The GS year-papers are not touched. Two paper rows per year exist for Mains
  from here: the official GS paper and the aggregator optional paper.
- 16 rows, not 13. The corpus adds PSIR 2026 (no GS 2026 year-paper exists) and
  PubAd 2011 and 2012, which predate the earliest GS year-paper.
- Coverage is uneven by design. Geography starts 2020, History 2017, PubAd 2011.
  Sections exist only on years the corpus covers, so a reader will see gaps.
  Those gaps are real and belong in the data.
- PubAd 2011 and 2012 predate the earliest GS year-paper (2013). Those two
  optional year-papers have no GS counterpart. That is fine and expected.

---

## Subject identity, sections and numbering

**Decision M2. One `subjects` row per optional *paper*, not per optional.**
Twelve subject rows for six optionals. Slug
`upsc-cse-mains-opt-<name>-p1` / `-p2`.

Revision 1 left this open — "two sections under one subject, or two subjects?"
It is settled by the syllabus, not by preference: **UPSC publishes a separate
official syllabus for Paper I and Paper II of every optional, and the two are
disjoint rather than two halves of one tree.**

| Optional | Paper I | Paper II |
|---|---|---|
| PSIR | Political theory, Indian government and politics | Comparative politics, international relations |
| Sociology | Fundamentals of sociology | Indian society: structure and change |
| Geography | Principles of geography | Geography of India |
| History | Ancient and medieval | Modern India and world history |
| Public Administration | Administrative theory | Indian administration |
| Anthropology | Biological and social anthropology | Indian anthropology, tribal issues |

GS already resolves this the same way and for the same reason: GS I–IV are four
separate `subjects` rows because each paper carries its own syllabus, and
`ingest_upsc_gs_syllabus.py` maps `papers[].paper_title` to one subject each.
**On this exam, paper is subject.** One subject holding two disjoint syllabi
would force a `topics` tree whose two halves never meet, and would make
per-paper coverage derivation impossible without a synthetic split.

Consequences:

- Each optional paper gets its own syllabus spine, ingested separately, and its
  own microtopic tree — which is what the shared-microtopic model in revision 1
  needs anyway, since PSIR Paper-I overlaps GS-II Polity while PSIR Paper-II
  overlaps GS-II International Relations. Those are different GS microtopics.
- Coverage derives per subject, so a `exam_topic_coverage` row is scoped to one
  optional paper rather than to a merged pair.
- Twelve subjects is the correct count and is not duplication. The trap to avoid
  remains a *second* subject with the same slug stem under a different
  convention — the `upsc-mains-gs1` / `upsc-cse-mains-gs1` pattern that left four
  subjects holding zero topics while their twins held 444.

**Decision M2b. One `exam_phase_sections` row per optional subject per optional
year-paper.** Twelve sections on a fully-covered year, each pointing at its own
subject row. Section label carries subject and paper, e.g.
`Optional: PSIR Paper-I`. Sections and topics must resolve to the *same* subject
row; verify immediately after creating each.

Note the granularity: `exam_phase_sections` hangs off the **phase**, not the
paper. Mains `626ec667` currently has 5 sections (Essay, GS I–IV) shared by all
13 year-papers. Adding 12 optional sections makes 17 on that phase, and all 17
are selectable against any paper on it, including the GS ones. That is how the
table already works and is not harmful, but it means the section list is not a
per-paper contents page and should not be read as one.

**Decision M3. Question numbering uses reserved per-subject blocks starting at
100,** leaving 1–99 for the GS convention should the two ever be compared. Both
`question_number` and `display_order` take the same value — the 2022 Essay
failure proved `display_order` is globally unique per paper too, not per section.

| Subject row | Block |
|---|---|
| `…-opt-psir-p1` | 100–149 |
| `…-opt-psir-p2` | 150–199 |
| `…-opt-pubad-p1` | 200–249 |
| `…-opt-pubad-p2` | 250–299 |
| `…-opt-sociology-p1` | 300–349 |
| `…-opt-sociology-p2` | 350–399 |
| `…-opt-anthropology-p1` | 400–449 |
| `…-opt-anthropology-p2` | 450–499 |
| `…-opt-history-p1` | 500–549 |
| `…-opt-history-p2` | 550–599 |
| `…-opt-geography-p1` | 600–649 |
| `…-opt-geography-p2` | 650–699 |

One block per subject row, so a block maps to exactly one section and one
syllabus tree.

Fifty slots per subject-paper against a maximum observed of 43 (History Paper-I,
28 questions where Q1 expands to 20 map items). Blocks are fixed and must never
be renumbered — a later subject takes 700+.

**Decision M4. `source_question_ref` is prefixed with the subject and paper**,
e.g. `PSIR-P1-1a`. Unprefixed refs collide across sections and surface as a
generic 500, which cost a session to diagnose during the 2022 load.

### Syllabus parts are topics, not sections

**Decision M10. The official syllabus's internal divisions become top-level
`topic` rows under the paper's subject. They are never modelled as
`exam_phase_sections`, and the question paper's Section A/B is never treated as
a syllabus division.**

Two structures are easy to conflate and only coincide for one subject.

*The question paper* always has exactly SECTION 'A' and SECTION 'B'. This holds
for all six subjects in every year of the corpus — a clean 14/14 split of the 28
sub-parts, Q1–Q4 in A and Q5–Q8 in B.

*The syllabus* divides inconsistently:

| Subject | Official divisions |
|---|---|
| PSIR | Named Part A / Part B on both papers |
| Geography | Paper-I splits Physical / Human; Paper-II is one flat list of 10 units |
| Sociology | Paper-I flat, 10 units; Paper-II has **three** parts (A/B/C) |
| History | Flat chronological units, no parts |
| Anthropology | Numbered `1.1`/`1.2` hierarchy, no parts |
| Public Administration | Flat numbered units, no parts |

Only PSIR aligns its paper sections to named syllabus parts — Paper-I Section A
to Political Theory and Indian Political Thought, Section B to Indian Government
and Politics. For History or Public Administration, Section A/B is simply where
the paper cuts a flat syllabus, and Sociology Paper-II has three syllabus parts
against two paper sections.

Consequences:

- `exam_phase_sections` stays at one row per optional subject (M2b). Twelve, not
  twenty-four. A section per syllabus part would invent divisions for four of the
  six subjects and undercount Sociology Paper-II.
- The topic spine's top level is whatever the syllabus actually has: named parts
  for PSIR, a Physical/Human split for Geography Paper-I, three parts for
  Sociology Paper-II, and the numbered units themselves everywhere else. Do not
  force a uniform two-part tree.
- `section_ref` (`Section A` / `Section B`) travels in question `metadata`. It is
  a real property of the paper and worth keeping — but it is a **coarse topic
  signal only for PSIR**, and must not be used as a tagging shortcut elsewhere.
- The corpus already carries this field on all 4,015 rows, derived from question
  number, because printed section headers are missing or inconsistent in the
  source for several years.

---

## Isolation from GS — the `shared` branch must be deleted

> **M8 and M9 below are superseded by
> `docs/status/2026-09-10-mains-optionals-strategy-rev3.md`.** OPT-SPIKE-01
> established that the concept row M8 requires cannot be created: all four topic
> write paths reject a cross-subject `parent_topic_id`. The parent edge would
> also have bought nothing — mastery does not traverse `parent_topic_id`. The
> reasoning about WHY isolation is needed still stands; the mechanism does not.

Revision 1 proposed a three-way overlap worksheet: `shared` (tag optional
questions directly to the GS microtopic), `concept-child`, or `new`. **The
`shared` branch is unsafe and is withdrawn.**

**Decision M8. An optional question is never tagged to a topic owned by a GS
subject.** Every optional tag resolves to a row owned by that optional paper's
own subject — either a `concept` child parented to the GS microtopic, or a new
microtopic where no GS counterpart exists. Sharing is expressed by *parentage*,
never by two subjects tagging the same `topic_id`.

Two independent reasons, either sufficient.

**Coverage rows collide.** The unique index is
`exam_topic_coverage(exam_id, exam_cycle_id, exam_phase_id, topic_id)`
(`030:124-125`). `section_id` is a column on the table but **not part of the
key**. GS and the optionals share `exam_id` and the Mains phase
`626ec667-4bbf-4420-8715-48c5b83e0d11`, so a microtopic tagged by both can hold
exactly one coverage row. Deriving optional coverage would overwrite GS's
`coverage_depth`, `exam_priority_score` and `is_high_yield` on that topic — and
the reverse on the next GS derivation. Distinct `topic_id` per subject is what
keeps the rows distinct.

**The shared-core machinery does not cover this case.** `partition_topics`
(`shared_core.py:55-70`) keys on `exam_id`, and its fail-closed cross-exam
mastery rule reads a global `user_topic_mastery` row. That is a *cross-exam*
guarantee. GS and the optionals are the same exam, so it offers no isolation
between them. Revision 1 cited it as precedent; the precedent does not transfer.

### What an aspirant must see

- **GS-only aspirant, browsing GS-II.** Sees GS-II microtopics and the 1,131 GS
  PYQs. Sees no optional question and no optional topic. Their high-yield
  ranking is computed from GS questions only. Guaranteed by M8: optional tags
  point at rows owned by optional subjects, so any query scoped by GS
  `subject_id` — or by `level='microtopic'` where optional depth sits at
  `level='concept'` — cannot reach them.
- **PSIR aspirant.** Sees PSIR topics, and may see the parent GS microtopic as
  supporting context. The relationship is deliberately asymmetric: optional prep
  may draw on GS, GS prep never surfaces optional material.

**Decision M9. Every aspirant-facing read of topics or PYQs is scoped by
`subject_id`, never by `topic_id` alone.** A query that resolves a topic without
its subject will cross the GS/optional boundary as soon as concept children
exist. This applies to search, coverage reports, the topic tree and the PYQ
Explorer.

Practice surfaces are unaffected for now: optionals are descriptive and never
reach `mock_question_bank`, so `pyq_practice.py`'s
`mock_question_bank.topic_id = target` filter cannot return them. That is a
property of the corpus, not a safeguard — if descriptive questions ever become
projectable, M9 becomes load-bearing there too.

### M8 has no live precedent — spike it before committing

`concept` is a legal value in `_TOPIC_LEVELS` but **is unused in production**:
every UPSC subject reports `concepts: 0`, and a probe for concept rows parented
to another subject's microtopic returned nothing. M8 therefore rests on a
mechanism nobody has exercised.

Prove it on one PSIR topic before creating twelve subjects around it: one
`concept` row owned by `…-opt-psir-p1`, parented to a GS-II microtopic, then
confirm (a) coverage derivation emits a separate row for it, (b) a GS-II-scoped
read does not return it, and (c) the projection's level resolution — which reads
`topics.parent_topic_id` and writes microtopic to `microtopic_id`, parent to
`topic_id` — behaves sanely at concept depth. Migration 270 was written for a
two-level tree; a third level is untested.

### Open, and needed before the overlap worksheet is built

Under M8, GS mastery no longer counts toward an optional topic automatically,
because the `topic_id` differs. Whether mastery rolls up or down a
`parent_topic_id` edge is unresolved, and revision 1's motivating example —
"an aspirant with high GS-II mastery on *Federalism* should not start PSIR from
zero" — depends entirely on the answer. Determine it before the worksheet is
built, not after.

---

## Provenance and trust

**Decision M5. Optional papers load `pending`, and are promoted only once the
compiler PDFs are registered as `document_assets` and linked as
`source_document_id`. The anchor, not the source class, is what gates them.**

Revision 2 first recorded this as "aggregator content stays pending, full stop."
Live data disproved that. Paper provenance across all exams:

| trust | source_type | papers | with url | with document |
|---|---|---:|---:|---:|
| verified | memory_based | 105 | 0 | 105 |
| verified | coaching | 44 | 0 | 44 |
| verified | official | 26 | 26 | 3 |
| pending | memory_based | 38 | 0 | 38 |
| pending | coaching | 16 | 0 | 3 |
| rejected | official | 1 | 1 | 0 |

**149 non-official papers are already verified.** Coaching and memory-based
content is not barred from promotion here — SEBI, PFRDA, IFSCA and NABARD all
carry verified papers. So "these are the first aggregator papers on UPSC CSE" is
true but is *not* the reason to hold them.

The actual, consistently applied rule is about the anchor:

- **Not one** coaching or memory-based paper is verified on a `source_url`.
  All 149 carry a `source_document_id`.
- **Not one** official paper needs a document — 26 of 26 verified officials are
  URL-anchored, only 3 also carry a document.

A URL is a sufficient anchor when it points at the issuing authority's own
published paper. It is worthless when it points at a coaching site that can
re-edit or remove the page. The document asset is what makes non-official
content auditable, and that is the invariant already recorded for
SEBI/PFRDA/IFSCA: register the source files as `document_assets` and point
`source_document_id` at them to satisfy the promotion gate.

So the optionals have a real route to `verified`, and it is the same one the
regulatory corpora took. Until the six LotusArise PDFs are registered, the
papers hold at `pending` — not because they are aggregator-sourced, but because
a coaching URL is not an anchor.

**Do not promote these on `source_url` alone.** Migration `186:147-151` accepts
either anchor and would let it through; no existing non-official paper has ever
been promoted that way.

**Decision M6. Question-level provenance travels in question `metadata`** —
`extraction_source`, `verified_against_official: false`, and the compiler name.
Paper-level trust is too coarse to carry it, and `metadata` is a whole-column
replace, so every write is read-merge-write.

---

## Corpus defects that must survive the load

**Decision M7. Flagged rows load with their flags, and are never silently
dropped or silently corrected.**

- `structure_anomaly` — 102 rows whose parent has a non-standard sub-part count.
  `marks_inferred` is null on all of them; do not let a default fill it.
- `duplicate_in_source` — 4 rows. Sociology 2014 Paper-2 is corrupt in the
  compiler's own PDF: Q5 and Q6 print identical (b) and (c), and Q7(a) repeats
  Q6(a). Resolving needs the official 2014 paper.
- `map_item` — History Paper-I Q1 and Geography Paper-II Q1 are location lists,
  20 and 10 items. Loaded one row per location, `marks` null.
- Six papers are incomplete **in the source**: PubAd 2022 Paper-1 stops after
  Q5; PubAd 2017 Paper-1 has no Q6. Not extraction failures.

A reviewer must be able to find every one of these by query. That is the whole
point of loading them flagged rather than clean.

---

## The topic-wise corpus — still unhoused

9,111 rows across the six subjects, each with a topic heading and one or more
years, spanning 1980–2025. No paper number, no question number, and no key
joining them to the 4,015 year-wise rows — joining requires text matching.

This is the single largest open question and it is **not** answered here.
`pyq_questions` is the wrong home: these are not paper questions. The options
are a new table, `syllabus_topic_mentions`, or discarding them and deriving
ask-frequency from the year-wise rows alone.

Worth weighing: they are the cheapest available source for the *predictability*
axis of the optionals difficulty rubric, because they carry ask-frequency and
recency per theme directly. Discarding them means computing that from 4,015
rows by hand.

---

---

## Confirmed live, 2026-09-09 — findings that outlive this document

Recorded here because three of them are not in the repository at all.

**Schema drift: `uq_pyq_question_one_primary_tag` exists in the database and in
no migration.** Live definition:

```
CREATE UNIQUE INDEX uq_pyq_question_one_primary_tag
  ON public.pyq_question_topic_tags USING btree (question_id)
  WHERE (tag_role = 'primary');
```

A full-tree grep finds it only in revision 1 of this document. It is working —
0 questions carry two primary tags — but a rebuild from migrations would lose
it silently, and every wrong-tag replacement in the tagging step depends on it.
**Write the migration to match live.** Separate task, not part of the optionals
load.

**Resumability is already solved.** `uq_pyq_questions_idempotency_key` is a
partial unique index on `idempotency_key`. A load run interrupted by JWT expiry
can re-post the same rows without duplicating them, so the loader does not need
a pre-flight existence check per question. `pyq_papers` still has no such guard,
so paper creation does need one.

**Question counts, corrected.** 1,209 descriptive questions live, not 1,131:
1,191 `source_kind='manual'` (16–22 Aug 2026) plus 18 `bulk_import`. The manual
count matches the CMS audit-row count exactly, confirming the per-question CMS
route as the path those took.

**Optional subjects do not exist yet.** No row matches `upsc-cse-mains-opt-%`.
Step 4 creates all twelve from nothing.

**`subject_group` has no convention to inherit.** Live values are a mix of
per-paper (`GS_1`…`GS_4` on the four active Mains subjects), family-style
(`regulatory-finance`, `upsc-gs`), and the six retired `gs` rows. The four
retired `upsc-mains-gs*` subjects and `upsc-gs-paper-1` all sit on `gs` with
`is_active=false` and 0 topics — the duplication trap, now visible in data.
Choose the optionals' value deliberately and check `_GROUP_FAMILY` before
writing it.

---

## Sequence

**Steps 1, 4 and 5-papers are DONE (2026-09-09).** 16 optional year-papers
created (`UPSC-CSE-MAINS-OPT-<year>`, aggregator/pending), and twelve subject
rows plus twelve sections created and verified to resolve to the same subject.
Ledgers: `workbench/ledgers/OPT-LOAD-02_optional_year_papers.csv` and
`OPT-LOAD-03_subjects_sections.csv`. `subject_group='upsc-optional'` is
deliberately unmapped in `_GROUP_FAMILY` — `family_for_subject()` returns None
and the caller maps None to the generic PYQ runtime, the same reasoning already
recorded for UPSC `gs`. Do not map it to a family.

Remaining:

1. **G5/G6 preflight** — `OPT-PREFLIGHT-01.sql`. Confirms whether
   `upsc-cse-mains-opt-*` subjects exist and how Mains sections are modelled.
   Nothing below starts without it.
2. **Explorer rendering check** — does the card list include `pending` papers?
   If yes, 16 cards land at load, not at promotion, taking UPSC to 43 — the exact
   count at which SEBI became unusable.
2a. **Mastery roll-up across `parent_topic_id`** — resolve before the overlap
   worksheet (M8 open item).
3. **OPT-FRONTLOAD-02** — extend the v2 importer to accept `descriptive` with no
   options. Three edit sites, not one.
4. **Subjects and sections** — twelve subject rows, slug
   `upsc-cse-mains-opt-<name>-p1` / `-p2` (M2), one section each (M2b),
   `subject_group` chosen against `_GROUP_FAMILY` and `_SLUG_FAMILY` and stated
   explicitly. Verify sections and topics resolve to the same subject row
   before loading anything.
4a. **Syllabus spine per paper** — ingest twelve official syllabi, one per
   subject row, following `ingest_upsc_gs_syllabus.py`. Note its content-hash
   gotcha: editing a source JSON creates a new `syllabus_documents` row with a
   full fresh mention set rather than updating in place. Freeze each source
   before review starts.
5. **Load** — 14 optional year-papers, then questions per M3/M4. PSIR first,
   end to end, before any second subject.
6. **Review, then tag.** Question review and tag review are separate gates.
   Neither implies the other.

## Open, and deliberately not decided here

- `uq_pyq_question_one_primary_tag` appears nowhere in the repository — one
  mention, in revision 1 of this document, at line 165. Either the live database
  has drifted from migration history, or a 409 was attributed to a constraint
  that does not exist. Do not design the tagging step on it until
  `OPT-PREFLIGHT-01.sql` OV-3 answers it.
- `subject_group` for optionals. Note the live `upsc-csat` defect:
  `subject_group='aptitude'` matches nothing in `_GROUP_FAMILY` and falls
  through to generic, silently.
- Difficulty rubric. The Prelims traceability rubric does not transfer;
  predictability is the closest analogue and needs designing before anything
  is judged.
- Mathematics and Commerce & Accountancy. No corpus exists. Mathematics is
  scanned and OCR corrupts notation badly enough that extraction is not
  defensible; born-digital official PDFs would be required.