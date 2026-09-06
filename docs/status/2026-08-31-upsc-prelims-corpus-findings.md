# UPSC Prelims GS Paper I — corpus findings

Date: 2026-08-31, updated 2026-09-05
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

`topic_catalog.json` exports microtopic ids only. With the seven parents
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

## 7. mock_question_bank.microtopic_id was never written (CLOSED 2026-09-05)

**CLOSED 2026-09-05.** Migration 270 landed, every paper was re-synced, and the
column now carries a value on 2,112 of 2,115 projected rows across four exams.
What follows is the state that was found, kept because the diagnosis is the
useful part.

**Was the most consequential finding of the programme, and the one that
determined whether any of the tagging work reached learners.**

`mock_question_bank.microtopic_id` is NULL for **all 1,259 projected questions**
— every paper, every exam, since the table was created.

```sql
SELECT count(*) FILTER (WHERE microtopic_id IS NOT NULL) AS with_microtopic,
       count(*) AS total
FROM public.mock_question_bank;
--  with_microtopic 0 | total 1259
```

The column is read by at least six modules:

| module | use |
|---|---|
| `study_os/attempt_derivation.py:150` | keys mastery on `(topic_id, microtopic_id)` |
| `study_os/attempt_evidence.py:62` | same key for evidence rows |
| `study_os/quant_signals.py:139` | upserts on `user_id, exam_id, topic_id, microtopic_id, policy_version` |
| `study_os/attempt_analytics/topic_breakdown.py:14` | groups the per-attempt breakdown |
| `study_os/reasoning_strategies.py:175` | inner-joins `mock_question_bank(topic_id, microtopic_id)` |
| `study_os/quant_heuristics.py:179` | same join |

No writer exists. The projection RPC
`project_pyq_question_to_mock_bank` has been revised six times — migrations 183,
184, 186, 187, 229, 239 — and **none of them mentions `microtopic_id`**. The
insert lists 22 columns; that is not one of them, so it takes its NULL default
on every projection, and the update branch does not touch it either.

### Why nobody noticed

`writing_practice/evidence_deriver.py:103` builds its key with
`coalesce(microtopic_id, 'no_microtopic')`. The signal degrades to a literal
instead of failing. Mastery is produced, dashboards populate, nothing errors —
the numbers are simply all at topic level. 402 rows already sit in
`mock_attempt_topic_breakdown` on a NULL microtopic key.

### The actual defect is narrower than "it ignores tags"

```sql
topic_id = v_primary_tag.topic_id
```

The RPC writes whatever the verified primary tag points at into `topic_id`,
**without checking its level**. While every primary tag was topic-level this was
correct and invisible. Now that microtopic tags exist, re-projecting would write
a microtopic id into `topic_id` and leave `microtopic_id` NULL — every consumer
keyed on the pair would see a microtopic in the topic slot and nothing in the
microtopic slot.

**Do not run `sync_paper_projection` on a paper with verified microtopic tags
until the RPC is fixed.** `preview_paper_projection` makes no writes and is
safe. As of this note only the 2026 GS-I paper has such tags (66 verified).

### The fix

A seventh revision of the RPC:

1. Resolve the verified primary tag's `level`.
2. When it is `microtopic`: write it to `microtopic_id` and write its
   `parent_topic_id` to `topic_id`.
3. When it is `topic`: current behaviour.
4. Add `microtopic_id` to the insert column list.
5. Add it to the content hash, so a microtopic change alone marks the row
   `would_update`.

Then re-project the affected papers and confirm `microtopic_id` is populated.

### What this means for the tagging programme

The 800 tags are correct and stored in `pyq_question_topic_tags`. Nothing needs
redoing. But until the RPC is fixed, microtopic-level mastery cannot work for
any question, and **the 244-microtopic catalogue has no consumer** — which was
the entire purpose of building it.

---

## 10. Demo seed fixtures in a working database

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

## 8. The 2024 key came from the wrong series

**Found by a person reading answers, not by any check.**

Another session spot-checked the corpus and found ten wrong answers in 2024 and
one in 2018. All ten were factually right: Canada-USA is the longest border,
Sachchidananda Sinha was provisional President of the Constituent Assembly,
Garba was the 2023 ICH inscription, Cote d'Ivoire and Ghana lead cocoa
production, and none of Rafale, MiG-29 or Tejas Mk-1 is a fifth-generation
aircraft.

### Diagnosis

Eight questions in the 2024 paper have an answer that is unambiguous from the
option text alone. Reading which label held the correct text gave the pattern
`a d d c c a d d`. Set D matches 8 of 8; Set C matches 0 of 8.

The dropped questions confirm it independently. Set D drops Q32, Q37 and Q80;
Set C drops Q42, Q47 and Q90. The database held the Set C drops.

**The paper is Set D. It was keyed against Set C.** UPSC shuffles option order
per question between series, so a Set C letter lands somewhere arbitrary in Set
D's ordering — which is why the errors looked uncorrelated rather than shifted
by a constant.

### Root cause

`paper_code` was NULL on every paper. Nothing recorded which series had been
imported, so nothing could detect that the key came from a different one.

### Why the checks passed

`option_audit.py` compared the database's option text against the source JSON's
option text at the same label and reported no differences — because both derive
from the same aggregator compilation and agree with each other. Neither was ever
compared against the answer key's series. Counts matched, exactly one correct
option per question, no structural anomaly anywhere.

### Fixed

`rekey_2024_setd.sql` cleared all keys and rewrote them by Set D label, matched
to option ids inside the transaction, with an abort guard on the final counts.
97 keyed; Q32, Q37 and Q80 left NULL. All eight diagnostic questions verified
correct afterwards.

`paper_code` is now populated on all nine papers: 2018 C, 2019 B, 2020 C,
2021 C, 2022 A, 2023 A, 2024 D, 2025 A, 2026 A.

### Also resolved

**2018 Q22** — key said Jaipur School, corrected to Kishangarh (Bani Thani).
Set C matched Set C on that paper, so this was an isolated wrong letter among
2018's 34 corrections, not a series problem.

**2022 Q50** — the option rotation is fixed. Options now read (b) genetically
modified flora, (c) mini forests, (d) wind energy, matching the official paper,
and the key correctly points at (c). This question was never a UPSC drop and
stays keyed.

### Still open: five keyed questions that UPSC dropped

2020 Q42 and Q77, 2021 Q30, 2022 Q61 and 2023 Q34 all carry keys. If those are
genuine drops in their series they must be NULL — a dropped question is not
scored, and keying it marks a learner wrong on a question that did not count.
Verify each against its official key before nulling.

---

## 9. UPSC Prelims 2025 GS Paper I loaded

The corpus is now nine papers. 2025 was the last missing year: paper
`c82f3e64-dd2c-4aec-96b5-e7305747e173` had existed since 2026-07-05 as a shell
marked `official`/`verified` with **zero questions** and a NULL
`exam_phase_id` — the same ghost-shell defect flagged on the 2026 CSAT rows.

**It is now the best-provenanced paper in the corpus.** Text from the official
upsc.gov.in PDF rather than an aggregator compilation, official Set A answer key
merged at import rather than backfilled, `paper_code` recorded before loading,
and it went through the sanctioned `pyq-papers/{id}/bulk-import` path with a
preflight rather than direct SQL. 100 rows preflighted `ok`, 100 committed, 0
skipped, 0 failed. Zero questions dropped by UPSC in Set A, so all 100 are
keyed.

If the other seven aggregator-sourced papers are ever re-sourced, this is the
template.

Two gaps the importer leaves, both backfilled afterwards: v1 sets neither
`section_id` nor `pyq_questions.correct_option_id`, writing only
`pyq_options.is_correct`.

---

## 11. The practice surface was empty: an unbatched .in_() (PR #1065)

`practice_ready_count` was 0 on all 26 UPSC papers while 1,070 projections sat
active, every paper was verified, and every gate a SQL query could test passed.

### The cause

`_active_projection_ids` (`study_os/pyq_practice.py:85`) passed ~1,000 UUIDs into
a single PostgREST `.in_()`. That renders into the URL query string —
roughly 40 KB — and the request was rejected:

```
db_op_failed op=pyq_practice.active_projections err=Error 400:
```

`safe_required(allow_empty=True)` returned `None`, the caller caught the
resulting `RuntimeError` and returned `{}`, and every paper reported zero. No
error reached the endpoint.

`_BATCH = 250` already existed in five other modules, commented "PostgREST
URL-length ceiling", and `exam_intelligence.py:390-393` records the identical
incident: *"an unbatched .in_() over every verified question id overflowed the
request, failed, and surfaced as a false '0 results' for every topic/subject
selection."* Same failure, same file, already written down.

### A second truncation underneath it

The bank read used `.limit(50000)`, which does not defeat Supabase's
`db-max-rows` of 1,000. The candidate list was already being cut to 1,000 before
it overflowed the filter — which is why the reproduced trace says 1000 ids, not
1,070. Two silent truncations in one call chain, the first feeding the second.

### The swallow inventory

Eleven places on this path report a fault as "not ready" rather than as a fault.
Nine share one shape: `allow_empty=True`, plus `or []`, plus a boolean readiness
predicate with no "unknown" state. `pyq_practice.py:320` conflates a `None` read
failure with a legitimately empty result; both become "no candidates".

Fixed in PR #1065: chunking at 250 across `_active_projection_ids`,
`_load_questions` and `_printed_order_meta`; range-pagination inside each chunk;
and `or []` dropped so a read failure raises. The other nine swallow points are
deferred and recorded in the PR body.

**Result: 0 to 1,201 practice-ready on UPSC.** Higher than the predicted 1,070
because removing the row cap recovered questions nobody knew were missing.

---

## 12. The regulatory corpus was demoted to draft by its own invalidation

872 of 906 bank rows across SEBI, IFSCA and PFRDA sat `reviewer_status='draft'`
with `sync_status='stale'` and `microtopic_id` NULL — while every paper and every
question was verified.

Not a review gap. Migration `183_pyq_mock_projection_bridge.sql:855-898` defines
two helpers that fire on invalidation and on blocking:

```sql
update public.mock_question_bank
set reviewer_status = 'draft', updated_at = now()
where pyq_question_id = p_qid
  and reviewer_status in ('verified', 'published', 'live');
```

So a row whose projection goes stale is **also demoted to draft**. That coupling
is deliberate — a stale row should not be served — but it means "draft" here
records an invalidation, not an unfinished review. All 402 SEBI rows were
projected and published in one operation on 2026-08-30; 368 were later
invalidated and demoted, 34 were untouched.

The fix is a re-sync, not a promotion: the RPC sets `published` again, marks the
projection active, and under 270 populates `microtopic_id` in the same pass.
91 papers re-synced 2026-09-05. All three exams now 100% published with
microtopics.

---

## 13. Multi-paper years break the paper-card layout

Six exams have years with more than two papers — IFSCA up to 15, PFRDA 18,
SSC CGL 13, SEBI 12, RBI 4, UPSC 3. The PYQ Explorer renders one card per paper,
which works for UPSC and produces 43 undifferentiated cards for SEBI.

Not a data defect: SEBI Phase I is genuinely subject-split, and `subject_name`
and `phase_name` are already on every row the endpoint returns. It needs
year → subject grouping in the component: one card per year with its papers
inside. That also surfaces something the flat list hides — which years are
complete.

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


### Fifth instance, and the largest

`mock_question_bank.microtopic_id` (§7) is the same failure at the largest
scale. Six revisions of the projection RPC, a dozen consumers, 1,259 projected
questions, and a column nothing writes — invisible because `coalesce(...,
'no_microtopic')` turns the absence into a valid-looking value.

Every one of these five defects passes the checks that exist. Counts are right,
requests return 200, hashes compute, mastery rows appear. What none of the
checks ask is whether the thing that should be there **is** there:

- 697 questions, 2,788 options, zero correct answers — all counts correct
- `/options/backfill-hashes` — 200 OK, zero rows scanned
- the tag sweep — clean, because it only examined tags that existed
- 2022 Q50 — four options, four labels, rotated
- `microtopic_id` — every row present, every value NULL

The generalisable form: **a validator that reads what is present will never
report what is missing.** Where a field is optional at the schema level but
required in practice, that gap needs an explicit assertion, not an inference
from a successful write.


### Sixth instance: the wrong-series key

The 2024 key (§8) passed every check it was given. Option text in the database
matched option text in the source JSON at every label. Counts matched. Exactly
one correct option per question. No structural anomaly.

Both texts came from the same aggregator compilation, so they agreed with each
other — and neither was ever compared against the answer key's series. The
missing check was not structural at all: it was whether the marked option's
*text* is the right answer to the question, which requires knowing the subject.

A person reading ten answers found it. No amount of structural validation would
have.

That is the boundary worth recording. Five of these six defects were findable by
asserting on absence. This one was not — it needed someone who knew that Chile
and Argentina do not share the world's longest border.


### Seventh and eighth instances

The unbatched `.in_()` (§11) is the same shape at the largest blast radius yet:
one oversized request, caught and reported as "not ready", hiding 1,201
questions from every learner. The codebase had already met this failure, named
the constant, and written the incident into a comment 340 lines from the call
that repeated it.

The regulatory demotion (§12) is a variant worth distinguishing. Nothing was
swallowed — the demote-on-invalidation is deliberate and correct. What made it
opaque is that **one column carries two meanings**: `reviewer_status='draft'`
reads as "not yet reviewed" but here recorded "was invalidated". Every paper and
question was verified; only the derived row said otherwise, and it said it in
vocabulary borrowed from a different concept.

So the inventory now has two families:

- **absence reported as success** — six instances, all fixed by asserting on
  what should be there rather than validating what is
- **a state whose name means something else** — one instance, fixed by knowing
  the mechanism rather than by any check

The second is harder to guard against. No assertion catches it, because nothing
is wrong: the value is correct for the mechanism that wrote it and misleading to
the person reading it.

## Status

### Platform-wide, 2026-09-05

| exam | bank rows | with microtopic | published |
|---|---|---|---|
| upsc-cse | 1,209 | 1,206 | 1,201 |
| sebi-grade-a | 402 | 402 | 402 |
| ifsca-grade-a | 362 | 362 | 362 |
| pfrda-grade-a | 142 | 142 | 142 |

2,112 of 2,115 projected rows carry a microtopic. The three exceptions are UPSC
rows whose primary tag is still topic-level. `ssc-cgl-legacy-sandbox-do-not-use`
holds a further 140 rows, unpublished, and is excluded — it is the demo fixture
recorded in §10.

### UPSC Prelims corpus — nine papers, 900 questions

| year | series | questions | keyed | primary-tagged | difficulty |
|---|---|---|---|---|---|
| 2018 | C | 100 | 100 | 100 | 100 |
| 2019 | B | 100 | 100 | 100 | 100 |
| 2020 | C | 100 | 100 | 100 | 100 |
| 2021 | C | 100 | 100 | 100 | 100 |
| 2022 | A | 100 | 100 | 100 | 100 |
| 2023 | A | 100 | 100 | 100 | 100 |
| 2024 | D | 100 | 97 | 100 | 100 |
| 2025 | A | 100 | 100 | 100 | 100 |
| 2026 | A | 100 | 97 | 97 | 100 |

2024's 97 is correct — Set D dropped three questions. 2025's 100 is correct —
Set A dropped none. The five 100s at 2020-2023 are **not** correct: each carries
a key on a question UPSC dropped (§8, still open).

Unkeyed questions are UPSC's own drops. Untagged: 2021 Q59 (stem carries no
subject — the content is entirely in the options) and 2026 Q51–Q53 (see below).

**Done**
- Difficulty constraint, three-layer enforcement
- 244 active microtopics across seven areas; renamed to NCERT vocabulary;
  science separated from technology; `metadata.study_sources` on all of them
- 11 microtopics added after tagging all eight papers, each with corpus evidence
- 791 answer keys loaded from official UPSC keys
- 2018 repaired (3 questions, 13 options); 2020 repaired (Q40 stem)
- 796 primary microtopic tags applied; 800 difficulty values judged
- 2026 GS-I recovered: it was invisible to every phase-scoped query
- Two duplicate GS subjects untangled; the six papers' section repointed at the
  populated subject

### Catalogue validation

Built from a 40-question sample, then tested against 800 real questions:

- **largest microtopic: 10 questions** (1.25% of the corpus) — no bucket is
  doing too much work
- **19 of 243 microtopics have no question** — all of them topics UPSC
  demonstrably asks about that these eight papers happened to skip
  (*Climate of India*, *Vedic age*, *Sufi traditions*, *High Courts*, *Atoms and
  nuclei*). None is a syllabus artefact; all should be kept.
- **~85% first-pass tagging accuracy** across the eight papers

### Difficulty distribution

Judged against a traceability rubric — NCERT-traceable is easy, standard-text
traceable is medium, current affairs by prominence, untraceable or absurd is
hard — rather than a felt sense of hardness.

| year | easy | medium | hard |
|---|---|---|---|
| 2018 | 39 | 45 | 16 |
| 2019 | 22 | 59 | 19 |
| 2020 | 18 | 50 | 32 |
| 2021 | 18 | 54 | 28 |
| 2022 | 21 | 53 | 26 |
| 2023 | 17 | 55 | 28 |
| 2024 | 23 | 50 | 27 |
| 2025 | 16 | 58 | 26 |
| 2026 | 10 | 56 | 34 |

**These nine rows are the reachability chart's data.** Any hardcoded copy in the
frontend must carry all nine — 2025 was added 2026-09-04 and sits between 2024
and 2026, as the trend predicts.

The trend is monotonic apart from 2018: papers have become steadily less
reachable from standard preparation. 2018's 39 easy is the one figure worth
re-checking — judging prominence at eight years' distance flattens it, and that
would inflate `easy`.

**Open**
- **2026 GS-I Q51-Q53** are ethics case studies ("Mr. X, a senior officer, was
  overseeing a critical vaccination programme…"). GS Paper IV in shape. The
  original 2026 review tagged them Polity, so someone saw and accepted them.
  Untagged and unprojected pending confirmation against the official paper.
- **Five questions carry keys UPSC dropped**: 2020 Q42/Q77, 2021 Q30, 2022 Q61,
  2023 Q34. Confirm against each paper's official key, then null them — a
  dropped question must not be scored.
- **Multi-paper year grouping** (§13) — a component change, no data work.
- **Mains difficulty** — 1,131 questions, all NULL. The Prelims traceability
  rubric does not transfer: a Mains question is not answerable from a book, so
  what varies is predictability or synthesis load, not reachability. Design the
  rubric before judging 1,131 questions against a borrowed one.
- **CSAT difficulty is rule-derived**, assigned by question type and keyword
  pattern, not judged. It must not appear on the reachability chart beside the
  nine judged GS papers — two standards, one axis, invisible to a reader.
- **The nine deferred swallow points** from the PR #1065 audit.
- **CSAT 2024** is five questions short (source is a scan with no text layer);
  **CSAT 2025** is missing two passages; **CSAT 2026** Q79's exponents were
  flattened by extraction.
- **140 sandbox rows** in `mock_question_bank` under
  `ssc-cgl-legacy-sandbox-do-not-use`, plus 176 phantom rows on the test exam.
  Harmless until an unfiltered `count(*)`.

**The difficulty rubric** — must travel with the worksheets or each paper is
judged against a different standard:
- **easy** — traceable to NCERT, or prominent current affairs inside the exam's
  two-year window
- **medium** — traceable to a standard reference (Laxmikanth, Spectrum,
  GC Leong, Shankar IAS, Ramesh Singh, Nitin Singhania), or lower-prominence
  current affairs in window
- **hard** — not traceable to any standard source, out-of-window current
  affairs, or incidental detail (a laureate's college, an ILO convention number)

Judge before checking the key. Calibrate to an aspirant six months in.

**Needs a decision**
- Should `_ecm_guard_published_delete()` require `reviewed_by IS NOT NULL`?
- Two `is_current_published` rows on one split pair — intended?
- Does any consumer read competition metrics by `reviewer_status` rather than by
  exam? If so, demo numbers are live for an exam named DO NOT USE.
- Retire the empty `upsc-gs-paper-1` subject (`4ebb113b`) now that nothing
  references it
- Whether to consolidate the three "Prelims" phases, and in which direction —
  the 2026 GS-I paper has 97 published projections, so moving it is not free
