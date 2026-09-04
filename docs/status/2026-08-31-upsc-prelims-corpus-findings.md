# UPSC Prelims GS Paper I — corpus findings

Date: 2026-08-31, updated 2026-09-01
Scope: the six verified official Prelims GS-I papers, 2018–2024 (2020 excluded,
unverified paper), `exam_phase_id = 715de35f-6caa-410a-9805-23bbe561e060`.

This supersedes the difficulty-enum note for everything after §1.

---

## Summary

Work started as microtopic cataloguing for a tagging programme. The catalogue was
built and landed. Preparing the first tagging pass then surfaced that the corpus
was not in the state the scope doc assumed: no answer keys anywhere, three
questions lost at import, one option rotation, and — once official keys were
obtained — 102 of 595 answer labels in the source files disagreeing with UPSC's
published keys. All of that is now repaired and the keys are loaded.

Nothing here was caused by the review pass. Reviewer notes do not persist in the
database and the keys were never loaded, so there was nothing for a reviewer to
check answers against.

---

## 1. Difficulty enforcement (closed)

`pyq_questions.observed_difficulty` was a bare `text` column. The only
enforcement was `_OBSERVED_DIFFICULTIES = ("easy","medium","hard")` at
`admin_exam_intel_cms.py:2002`, on the PATCH route, so anything writing outside
that route could store any string. One row held `medium_high`, traced to a demo
seed fixture (see §7).

Applied:

```sql
ALTER TABLE public.pyq_questions
  ADD CONSTRAINT pyq_questions_observed_difficulty_chk
  CHECK (observed_difficulty IS NULL
         OR observed_difficulty IN ('easy','medium','hard'));
```

Verified `convalidated = true`. Enforcement now sits at three layers: endpoint
enum, review-tool parse (rejects `very_hard` by name, PR #1053), and this
constraint — the only one a stray script cannot route around.

**Do not propagate this to `exams`, `subjects`, `topics` or
`exam_topic_coverage`.** Those carry a wider five-point scale deliberately
(`medium`, `medium_high`, `high`). Question difficulty and exam/topic difficulty
are different models.

Distribution, worth noting on its own: of 1,949 populated rows, 1,909 are
`medium`. Only 40 rows corpus-wide carry a difficulty anyone chose. This is why
difficulty is being captured during the tagging pass rather than after it.

---

## 2. Microtopic catalogue (landed)

234 microtopics across seven areas, built from the corpus rather than the
syllabus.

| area | microtopics |
|---|---|
| Economy and Social Development | 46 |
| History | 37 |
| Polity | 35 |
| Geography | 32 (31 after dropping the astronomy duplicate) |
| Science, Technology and Defence | 33 |
| Environment | 31 |
| International Relations and World Affairs | 21 |

Slug convention `gs-<kebab>-<8hex>`, metadata `{"tier":"official","exams":["upsc"]}`.

**Structural decisions taken, with reasons:**

- **Current Events was not a category.** The corpus tests standing world affairs
  — Sahel coups, Donbas, Cabo Delgado, UNCLOS, Organisation of Turkic States —
  not a recency watchlist. ~45 questions across six papers, every year. Renamed
  to International Relations and World Affairs. The residue (awards, sports,
  observances) became four microtopics inside it.
- **Defence was too small for a top-level topic.** 12 questions corpus-wide
  (~2%), concentrated in 2024. Folded into Science and Technology as a
  five-microtopic cluster; the topic was renamed accordingly.
- **Three seam rules locked** before tagging: organism-in-ecosystem →
  Environment vs organism-as-biology → S&T; region↔country pair-matching →
  Geography vs conflict analysis → IR; farming *method* → Environment vs crop
  economics → Economy.

**Migration A** repaired the subject slug (`General Studies` → `general-studies`)
and all seven topic slugs, which previously used four different conventions with
slug/name disagreement on three rows.

### Renaming pass (2026-09-01)

Names were moved to vocabulary aspirants already recognise. Two problems with the
original set: they read like university disciplines rather than exam topics
(*Astronomy and astrophysics* rather than *Space science*), and they used
internal phrasing an aspirant would not have met in any textbook.

93 of 234 renamed against NCERT chapter and subhead titles where a textbook
covers the topic — Class 12 Biology Unit X for Environment, *Indian Constitution
at Work* for Polity, *Fundamentals of Physical Geography* and *India: Physical
Environment* for Geography, *Themes in Indian History* and *An Introduction to
Indian Art* for History, *Indian Economic Development* and the two Class 12
economics books for Economy, Class 11–12 Physics/Chemistry/Biology for science.

Environment mapped almost word for word: Ch 16 *Environmental Issues* gave *Air
pollution and its control*, *Water pollution and its control*, *Solid wastes*,
*Agro-chemicals and their effects*, *Greenhouse effect and global warming*.

Science and technology were separated inside the S&T area — 11 science
microtopics, all NCERT-nameable; 22 technology microtopics, none of which any
textbook covers. Sources for those name ISRO, MeitY, PIB, MoD, DRDO instead,
rather than implying NCERT provenance they do not have.

Two rows removed: Geography's *Stellar and planetary astronomy* (duplicate of
S&T's *Space science*) and *Internet of things* (merged into *Emerging
technologies*). 234 microtopics remain, 233 active.

### metadata.study_sources

Each microtopic now carries a `study_sources` array in `topics.metadata`:

```json
{"study_sources": [
  {"type": "ncert", "ref": "Class 12 Biology — Environmental Issues"},
  {"type": "standard", "ref": "Shankar IAS Environment"}
]}
```

**This is study guidance, not provenance.** It does not claim a question was set
from that chapter. It says: this is where the syllabus a candidate has already
read connects to what the exam asks. Chapter *titles* are stored rather than
numbers, because NCERT renumbers between editions — Class 12 Biology went from 16
chapters to 13 in the rationalised edition and *Environmental Issues* moved.

Being user-facing, it needs an owner: a pointer to a chapter that no longer
exists misleads, where a stale provenance note would merely be inert.

`workbench/catalogs/topic_catalog.json` exports microtopic ids only. With the seven parents
excluded, any tag written at topic level fires `unknown_topic` in the sweep —
giving the level check the projection currently lacks, one layer earlier.

---

## 3. Review tooling (PR #1053, merged)

`scripts/pyq_question_review.py` validated existing tags but could not assign
them, and a question with **zero** tags produced no tag row at all — so a fully
untagged paper swept clean.

Added: `no_primary_tag` flag, `assign_topic_id` and `difficulty` worksheet
columns, apply-time validation against `--topic-catalog`, and `Client.post`.
`very_hard` is rejected at parse time.

Confirmed working on the 2018 paper: 97 rows, 0 clean, `no_primary_tag: 97`.

---

## 4. The corpus had no answer keys

**Resolved 2026-09-01.** 593 keys loaded via `answer_key_migration.sql`;
`keyed` equals `marked` on every paper and exactly one option is correct per
question corpus-wide. What follows is the state that was found.

**697 questions, zero `correct_option_id`, 2,788 options with `is_correct` false
throughout.** The key-loading step never ran for UPSC Prelims.

Every paper's metadata says so explicitly: *"GS Paper I only. No verified answer
key attached at import time."* The importer recorded the gap honestly.

This inverts the scope doc's central claim. It budgeted UPSC review cheaply
because an authoritative key exists — true of the world, false of the database.
Until §5 was done, a reviewer had *less* to work with than the regulatory corpus,
where questions at least carried a recalled answer.

The 177 already-projected questions (2025, 2026) are unaffected — they came in
through a different path with real `source_url` values and keys present, and
projected correctly. That path works; the 2018–2024 compilation import is the
anomaly.

---

## 5. 102 of 595 answer labels were wrong

The six `pyq_<year>_prelims_gs1_set<x>.json` files carry
`correct_option_label`. Diffed against the official UPSC answer-key PDFs:

| year | series | wrong |
|---|---|---|
| 2019 | B | 1 |
| 2024 | C | 5 |
| 2023 | A | 11 |
| 2021 | C | 16 |
| 2018 | C | 34 |
| 2022 | A | 37 |

**17% of the corpus.** The distribution is bimodal, which random transcription
slips would not produce.

A hypothesis, unproven but worth recording: before seeing the 2018 key, three
labels (Q36 Prosopis, Q98 Aral Sea, Q99 Rule of Law Index) were flagged as wrong
on the merits, and the official key agreed on all three. A mis-transcribed letter
is random and would not align with substantive error. These read like answers
*reasoned out* rather than copied — which would explain 2019 and 2024 being near
clean while 2018 and 2022 are a third wrong.

**Drop positions were also wrong.** 2022 and 2023 marked drops at Q48 and Q54;
no official series drops those. Official Series A drops Q61 and Q34 respectively.
Two sources were feeding one field.

Resolution: `correct_option_label` was regenerated wholesale from the official
PDFs rather than patched cell by cell — the field had no credibility as a
transcription. 102 relabelled, 0 blocked. Zero blocks is itself evidence the
option sets are sound: every official key letter existed among that question's
four options.

Official key sources, per series: 2018 Set C, 2019 Set B, 2021 Set C, 2022 Set A,
2023 Set A, 2024 Set C. The 2018 key is no longer served from upsc.gov.in
(`AnsKey-CSP-18-Paper-I.pdf` 404s); a mirror of the same file exists at
`cdn1.byjus.com/wp-content/uploads/2019/04/`.

---

## 6. Import damage: three questions lost, one option lost

**2018 Q12, Q56 and Q65 were absent from the DB.** The Set C source docx contains
all 100. Cause found: the parser ran each missing question's stem into the
*preceding* question's option (d) instead of starting a new question.

```
Q11(d): "...guarantee by the Government of India. Q.12) With reference to the
         election of the President of India, consider the following statements:..."
Q55(d): "To establish British paramountcy over the India States Q.56) Which one
         of the following statements correctly describes the meaning of legal
         tender money?"
Q64(d): "2 and 3 only Q.65) In which of the following areas can GPS technology
         be used? 1. Mobile phone operations..."
```

Three questions and their twelve options were reconstructed and inserted;
`display_order` and `normalized_option_hash` backfilled.

**2018 Q37 had three options.** The missing one was (d) `1, 2 and 3` — which is
the correct answer. The question would have been unmarkable.

The paper is now 100 questions / 400 options, and the same checks across all six
papers return clean on count and gap.

### One option rotation, found only by cross-source comparison

2022 Q50 (Miyawaki method) had options b, c and d rotated one position against
the official paper. The official key is **C** — mini forests — which in the DB
sat at label (d). Writing the key to label (c) would have marked *"Development of
gardens using genetically modified flora"* as the correct answer.

A rotation is invisible to every structural check: four options, four distinct
labels, correct count, no marker text. It surfaced only because the key generator
compares the JSON's option text against the DB's at the key label and refuses
rather than guessing.

An audit extending that comparison to all four labels across all 600 questions
found **one** rotation and four text differences, all already known. So the fault
is isolated, not systematic — but the check is worth keeping as a standing step
for any future key load, in the same family as the `no_primary_tag` flag:
verifying that something is *present and correctly placed*, not only that what is
present is well-formed.

Q50 is deliberately excluded from the key migration and stays keyless until its
option text is corrected.

**This belongs in `scripts/docx_to_pyq_json.py` (PR #1026, still draft).** A
`Q.n)` marker appearing mid-option is a hard signal the parser should refuse on,
not absorb. Two other docx shapes it must handle: options in separate paragraphs
from their stem, and question content in tables.

---

## 7. Demo seed fixtures in a working database

`exam_intelligence_demo_ssc_cgl.sql` — self-declared "DEMO / DEVELOPMENT seed —
NOT production truth" — has been applied to a database that also holds the UPSC
corpus and the 36-paper SSC CGL import.

Its exam row (`22222222-…-222222222222`, slug `ssc-cgl`) was later renamed in
place to `[SANDBOX - DO NOT USE] SSC CGL`. The seed now fails on `exams_pkey`,
because `ON CONFLICT (slug)` finds no `ssc-cgl` row while the id is taken.

The seed anticipated exactly this and contains a guard —
*"Repair exam identity before re-running this seed"* — but it is unreachable: the
pkey violation aborts the statement before the check runs.

The real SSC CGL exam is `3742f421-…`, slug
`national-ssc-combined-graduate-level-cgl`, created through the registry path.

**Not deleted.** The sandbox holds two `exam_competition_metrics` rows with
`reviewer_status = 'locked'`, protected by `_ecm_guard_published_delete()`. Both
have `reviewed_by` NULL and `reviewed_at` six weeks *before* `created_at` — the
seed asserted `locked` as literal data. Every locked row in the system is demo
data; the lock semantics have never been exercised by a real review.

`medium_high` originated in that fixture's
`metadata.legacy_difficulty_trend_unconverted.expected_difficulty` and propagated
to `exams.default_difficulty_level` and then to a fixture question.

---

## The pattern

Four instances this session of a rule that validates content but never validates
that a decision occurred:

- **Projection** has no level check: a question tagged to a top-level topic
  passes `primary_topic_tag_count_not_one` exactly like one tagged to a
  microtopic, leaving `mock_question_bank.microtopic_id` NULL. 97 published
  questions affected.
- **Review sweep** built tag rows only from exported tags, so zero-tag questions
  swept clean. Fixed (PR #1053).
- **`_ecm_guard_published_delete()`** honours `reviewer_status = 'locked'`
  without requiring `reviewed_by IS NOT NULL`. A demo seed can create
  permanently undeletable rows.
- **`/options/backfill-hashes`** reports `option_rows_scanned: 0` and success on
  an exam of 2,232 questions. PostgREST caps reads at 1,000 rows regardless of
  `.limit(20000)`; the resulting 1,000-uuid `.in_()` fails, `_safe` swallows it,
  and the endpoint returns a success shape having written nothing.

Worth naming once rather than filing four unrelated tickets.

---

## Status

**Done**
- Difficulty constraint, three-layer enforcement
- 234 microtopics across seven areas; Migration A slug repair
- Renamed to NCERT vocabulary; science and technology separated;
  `metadata.study_sources` populated on 233
- PR #1053 merged and pulled
- 2018 paper repaired: 3 questions + 13 options inserted, hashes and ordering
  backfilled
- All six papers structurally verified: 100 questions / 400 options each
- `correct_option_label` regenerated from official keys in all six JSON files
  (102 corrections)
- **593 answer keys loaded.** Exactly one correct option per question corpus-wide
- Option audit across all 600 questions: one rotation found, four known text
  differences

**Open — corpus**
- **2022 Q50** option rotation: (b), (c), (d) hold each other's text. Excluded
  from the key migration; stays keyless. Official text is in the findings above.
- **2018 Q55(d) and Q64(d)** still carry the trailing bled stem
- Re-hash the five options after those text fixes
- Sweep `option_text ~ 'Q\.\s*\d+\s*\)'` across all six papers — the §6 bleed
  may exist where the question survived, invisible to count checks

**Open — code**
- `docx_to_pyq_json.py` parser fix (PR #1026, draft): refuse a `Q.n)` marker
  mid-option; handle options in separate paragraphs and content in tables
- `/options/backfill-hashes` PostgREST 1,000-row cap — reports success having
  written nothing
- Migration files for the difficulty constraint and the microtopic rename, both
  applied directly
- Seed: remove the SSC CGL exam block; stop metrics fixtures asserting `locked`
  with NULL `reviewed_by`

**Open — tagging**
- 2018: worksheet filled with 100 draft microtopic assignments. 18 need a
  judgement call on seam cases; `difficulty` and `decision` unfilled. Not applied.
- 2019, 2021, 2022, 2023, 2024: not started. 500 questions.
- **Catalogue gap:** Aral Sea (2018 Q98) and Lake Chad (2022) are human-caused
  water-body degradation, which the seam rule sends to Environment, but
  Environment has no microtopic for it. Decide once.
- **Ch 16 gaps:** *Ozone depletion in the stratosphere* and *Deforestation* have
  no microtopic. Ozone is the more pressing — a distinct mechanism currently
  swept into greenhouse gases, and it recurs.

**The difficulty rubric** — must travel with the worksheets or each paper is
judged against a different standard:
- **easy** — single fact, directly recalled, no elimination
- **medium** — two or three statements to evaluate, or one fact plus reasoning
- **hard** — four-way matching with close options, obscure detail, or a chain of
  inference

Judge before checking the key; the answer makes a question feel easier than it
was. Calibrate to an aspirant six months in, not to someone who has been working
on this corpus. Expect roughly 20/60/20; a 5/90/5 split means the bulk-default
instinct reasserting itself.

**Needs a decision**
- Should `_ecm_guard_published_delete()` require `reviewed_by IS NOT NULL`?
- Two `is_current_published` rows on one split pair — intended?
- **Does any consumer read competition metrics by `reviewer_status` rather than
  by exam?** If so, demo numbers are live for an exam named DO NOT USE. Only item
  here with user-facing risk.
- Demo or production Supabase project? The demo API and the SQL editor were
  confirmed to reach the same database, which answers half of it — but that
  means demo seed fixtures sit alongside the real corpus either way.
