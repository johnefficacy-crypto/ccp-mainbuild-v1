# UPSC Mains optional subjects — corpus strategy

Written 2026-09-05. Scope: the ten most-taken optional subjects, papers already
in JSON.

Read `docs/status/2026-08-31-upsc-prelims-corpus-findings.md` first. The defects
in §7, §11 and §12 are platform-wide, and §2's catalogue-sizing evidence is the
model this follows.

---

## What is being built, and what is not

**Not** a practice surface. Optional papers are descriptive — no options, no
correct answer — so `mock_question_bank` cannot hold them. The 1,131 Mains GS
questions are already in that position: fully tagged, unprojectable, and
correctly so.

The deliverable is **coverage analysis and high-yield ranking**: which themes
this optional actually tests, how often, with what recency, and where an
aspirant's existing GS preparation already covers ground.

Study aids come after, and are a separate piece of work.

---

## The decision that shapes everything: shared microtopics

Optionals reuse GS microtopics where the subject matter genuinely overlaps.
PSIR Paper I against GS-II Polity, Geography against GS-I, Sociology against
GS-I Society.

**Why this is right rather than merely convenient.** `study_os/shared_core.py`
already partitions topics covered by two or more exams as shared core, with
cross-exam mastery deliberately fail-closed — only a global `user_topic_mastery`
row (`exam_id IS NULL`) counts, so mastery earned in one context never suppresses
a topic in another. That machinery is shipped and proven: as of 2026-09-05,
seven domain subjects and three QRE subjects are shared across four regulatory
exams, drawn on at different depths without divergence.

An aspirant whose GS-II mastery on *Federalism in India* is high should not start
their PSIR preparation on that theme from zero.

### The depth problem, and how to handle it

Optionals go deeper than GS on the same ground. *Federalism* is one microtopic in
GS-II and a chapter in PSIR. A shared microtopic will be right-sized for GS and
too coarse for the optional.

**Resolve it with a third level, not by duplicating.** `topics` already supports
`level in ('topic','microtopic','concept')` and self-referencing
`parent_topic_id`. Where an optional needs more granularity than the shared
microtopic offers, add `concept`-level children **under the shared microtopic**,
owned by the optional's subject.

That way:

- GS mastery on the parent microtopic still counts
- The optional's finer distinctions are expressible
- Nothing is duplicated, so the two never drift

Where an optional's theme has no GS counterpart — Anthropology's kinship theory,
PSIR's Western political thought — it gets a microtopic under the optional's own
subject as normal.

**Do not create a parallel microtopic with the same name under a different
subject.** That is exactly the `upsc-mains-gs1` / `upsc-cse-mains-gs1`
duplication found and retired on 2026-09-05: four subjects holding zero topics
while their twins held 444, with sections pointing at the empty ones. Ten
optionals compounding that pattern would be unrecoverable.

---

## Catalogue construction: syllabus for the spine, corpus for the leaves

Both sources, at different levels.

**Topics and themes from the published syllabus.** UPSC publishes a detailed
syllabus per optional, and unlike GS it is specific enough to build a spine from
directly. That gives the macro structure and guarantees nothing officially in
scope is missing.

**Microtopics and micro-themes from the corpus.** What the papers actually test,
at the granularity the questions distinguish. This is the standard the Prelims
catalogue was built and validated against: 244 microtopics, largest bucket 10
questions of 900, 92% earning at least one question. Corpus-derived granularity
is what makes mastery mean something.

The Mains GS catalogue was built the other way — syllabus-first, PYQ-refined —
and 134 of its 444 microtopics have never been tested in thirteen years. That is
not a failure, but it is the difference: a syllabus-built tree covers the
possible, a corpus-built tree covers the asked. **Build both, and mark which is
which** in `metadata`, so a coverage report can distinguish "not yet asked" from
"not asked in thirteen years".

---

## Sequence, per optional

Ten optionals, one at a time. Do the first end to end before starting the second
— the Prelims work proved that the second paper costs a third of the first.

### 1. Subject identity, decided before anything loads

One subject row per optional. Slug pattern `upsc-cse-mains-opt-<name>`, matching
the `upsc-cse-mains-gs*` convention rather than the retired `upsc-mains-*` one.
`subject_group` — see the open question below.

Sections and topics must point at the **same** subject row. Verify immediately
after creating it:

```sql
SELECT s.section_label, sub.slug,
       (SELECT count(*) FROM public.topics t WHERE t.subject_id = sub.id) AS topics
FROM public.exam_phase_sections s
JOIN public.subjects sub ON sub.id = s.subject_id
WHERE sub.slug LIKE 'upsc-cse-mains-opt-%';
```

### 2. Syllabus spine

Ingest the official syllabus as `topic`-level rows, one per official syllabus
line, `metadata.source = 'official_syllabus'`.

`scripts/ingest_upsc_gs_syllabus.py` is the working precedent. Note its recorded
gotcha: it resolves documents by content hash, so **editing the source JSON
creates a new `syllabus_documents` row with a full fresh mention set** rather
than updating in place, orphaning any review already applied. Freeze the source
before reviewing.

### 3. Overlap mapping — the step that earns the shared model

Before tagging a single question, map each syllabus theme to an existing GS
microtopic where one covers it. Produce a three-column worksheet: optional theme,
candidate GS microtopic, and one of `shared` / `concept-child` / `new`.

- **shared** — the GS microtopic is right-sized; tag optional questions directly
  to it
- **concept-child** — the theme needs more depth; add a `concept` under the GS
  microtopic, owned by the optional's subject
- **new** — no GS counterpart; new microtopic under the optional's subject

This worksheet is the artefact. Everything downstream depends on it, and it is
the only place the sharing reasoning is recorded.

### 4. Load the papers

The JSON is already in hand. Transform to the v1 bulk-import row shape and post
to `POST /pyq-papers/{id}/bulk-import/preflight`, then `/commit`.

**Descriptive questions may not fit v1**, which requires `option_a`–`option_d`
and `correct_option` on every row (`exam_intelligence/pyq_bulk_import.py:292-345`).
Check how the 1,131 Mains GS questions were loaded — they are descriptive and got
in somehow. If v1 rejects them, that path is the precedent to follow.

Known importer gaps, both backfilled afterwards on 2025 Prelims: v1 sets neither
`section_id` nor `pyq_questions.correct_option_id`.

### 5. Tag against the mapping

Follow the worksheet from step 3. `scripts/pyq_question_review.py` handles
export → sweep → merge → apply, and `workbench/scripts/merge_tags.py` takes a
year argument.

`uq_pyq_question_one_primary_tag` means a wrong tag cannot be replaced by
`assign_topic_id` — it 409s. Wrong tags need delete-then-insert.

### 6. Review, then publish

Questions land `pending`. Tags land `pending`. Both need explicit verification;
neither is implied by the other. The 2024 Prelims paper was fully tagged,
difficulty-judged and structurally valid while carrying ten wrong answers from a
mis-keyed series — tagging quality says nothing about content correctness.

Paper-level `trust_status` and question-level `reviewer_status` are separate
gates. Promoting the paper does not verify its questions.

### 7. Coverage derivation

`POST /api/admin/exam-intelligence/exams/{exam_id}/coverage/derive` writes
`exam_topic_coverage` rows with `coverage_depth` on the five-point scale
(`mentioned | light | normal | deep | core`), `exam_priority_score` and
`is_high_yield`. Only `reviewer_status='locked'` rows are planner-ready.

Confirmed on 2026-08-24: document-level `trust_status` is **not** a gate for
coverage derivation — only mention-level `reviewer_status='verified'` matters.

---

## Difficulty

**Do not borrow the Prelims rubric.** It measures traceability — NCERT is easy,
standard reference is medium, untraceable is hard — and that only works for a
question with one correct answer sitting in a source. A descriptive question is
not answerable from a book; every candidate can write something. What varies is
whether they can write something good.

The Mains GS corpus has 1,131 questions with `observed_difficulty` entirely NULL
for exactly this reason, and the CSAT papers carry rule-derived values their own
handoff describes as "worth a real pass".

For optionals, the candidate axes are **predictability** (a standard theme any
prepared candidate anticipated, or an angle nobody saw), **source density**
(enough material for 250 words, or synthesis across areas), and **directive
load** ("discuss" versus "critically evaluate in the light of").

Predictability is the closest analogue to reachability and the most useful to an
aspirant. Design it deliberately before judging anything.

---

## Open questions, to settle before the first optional loads

**`subject_group` for optionals.** The value drives runtime policy via
`_GROUP_FAMILY` in `study_os/subject_runtime_policy.py`. `gs` is deliberately
unmapped so PYQ-backed subjects keep the generic runtime — optionals are also
PYQ-backed and descriptive, so an unmapped value is probably right. But note the
live defect this pattern already caused: `upsc-csat` carries
`subject_group='aptitude'`, which matches nothing, so CSAT silently falls through
to generic and out of its own readiness checks. Pick a value deliberately, and
check `_GROUP_FAMILY` and `_SLUG_FAMILY` before writing it.

**Paper structure.** Each optional has Paper I and Paper II with different
syllabi. Two sections under one subject, or two subjects? One subject with two
sections is consistent with how GS I–IV are modelled.

**Which ten.** The order matters less than doing the first completely. PSIR,
Geography or Sociology are the strongest candidates for going first, because
each has the heaviest GS overlap — so the first optional also proves the shared
model rather than just exercising the pipeline.

**Mains multi-paper years.** 13 Mains papers per year already; ten optionals add
20 more. Findings §13 records that the PYQ Explorer renders one card per paper
and produces 43 undifferentiated cards for SEBI. Optionals will make that worse
before the grouping fix lands.
