# COV-DIM-01 — Why coverage carries no section and no comparable score

Read-only investigation. No code, migration, or data changed.
Line numbers are against `main @ 6d08760` (branch `investigate/cov-dim-01`).

---

## Answer in two paragraphs

**The section dimension.** The derivation cannot express a section: the string
`section` does not appear anywhere in `coverage_derivation.py`, and the payload
it writes (`:421-449`) carries four identity keys — `exam_id`, `exam_cycle_id`
(hard `None`), `exam_phase_id`, `topic_id` — and no `section_id`. Its own
contract says so: "exam-wide (`exam_phase_id is None`) and phase-scoped only"
(`:38`), "exactly one explicit scope per invocation" (`:41`, `:619`). The column
is nullable with no default and no trigger (`030:100`), so every one of the
1,497 derived Mains rows is NULL by construction, not by omission. The elective
rule migration 287 states — a section is compulsory, or elective and chosen —
is therefore unreachable for Mains, and `planner.py:600` keeps every NULL row as
"unclassified", which is why an unchosen optional still reaches the palette.
**But the fix is not simply "write the section":** a coverage row keys on
`topic_id` and a section keys on `subject_id`, and `exam_phase_sections` is
unique on `(exam_phase_id, subject_id, section_label)` (`030:92`) — one subject
may own several sections in one phase. `topic → subject` is a function;
`subject → section` is a relation. Until §3's live count says the Mains phase
has at most one section per subject, the mapping is ambiguous and the dimension
is not merely missing.

**The score dimension.** One column holds two unit systems, and this is already
known in-tree: `exam_intelligence/priority_scale.py` exists, opens with "THE
DEFECT THIS EXISTS FOR", and tabulates the exact live split this brief restates
(`:9-24`). The v2.0 model's ceiling is structural, not a coefficient artefact —
`exam_priority_score = frequency_term + cov_component*40 + evidence_quality*10`
(`score_snapshots.py:686-688`), where the 40-point term reads *existing locked
coverage's own score* (`:669`) and is therefore 0 on a corpus whose coverage the
model itself produced, and the 50-point frequency term is a cohort share that
1,252 topics over ~8,300 questions cannot make large. So the brief's premise
that "nothing reads `source_basis`" is **no longer true**: RANK-SCALE-01 landed,
the planner now selects it (`planner.py:337`), carries it (`:432`), attaches a
within-basis percentile (`:438-442`), and `_score_topic` ranks on that instead
of the raw column (`:885-892`). Three consumers use it. The palette is not one
of them — and the reason every topic shows priority 0 is not the unit systems at
all, but a one-key mismatch: `planner_board.py:295` reads
`cov["exam_priority_score"]` from rows whose key is `coverage_priority`
(`planner.py:431`). Every candidate scores 0.0 and the list falls back to
alphabetical (`:313`).

---

## Q1 Derivation payload

`section` — the substring — **does not occur anywhere in
`app/backend/app/exam_intelligence/coverage_derivation.py`**. Not in a column
list, not in a comment, not in the scope validation.

The payload `_proposed_row` returns (`:386-449`), in full:

| Key | Value | Line |
|---|---|---|
| `exam_id` | scope argument | `:422` |
| `exam_cycle_id` | **hard-coded `None`** | `:423` |
| `exam_phase_id` | scope argument | `:424` |
| `topic_id` | the topic being scored | `:425` |
| `exam_priority_score` | from the locked snapshot, `or 0` | `:426` |
| `is_high_yield` | from the snapshot | `:427` |
| `confidence_score` | from the snapshot, `or 0` | `:428` |
| `predictability` / `predictability_band` | projected verbatim, NULL without a snapshot | `:431-432` |
| `coverage_depth` | `bucket_coverage_depth(...)` | `:434` |
| `source_basis` | `_EVIDENCE_DERIVED_BASIS` | `:435` |
| `model_version` | `DERIVATION_VERSION` | `:436` |
| `reviewer_status` | `"draft"` | `:437` |
| `metadata` | evidence envelope incl. fingerprint | `:438-449` |

**Identity keys: `(exam_id, exam_cycle_id=None, exam_phase_id, topic_id)`.**
That tuple is also what the read-back and reconciliation passes key on
(`_existing_coverage_rows`, `:476-486`; stale reconciliation, `:567`), both
narrowed by `.eq("source_basis", _EVIDENCE_DERIVED_BASIS)` so the module only
ever touches rows it owns (PD-4/PD-4a, `:22-26`).

**Stated scope contract** (`:38-45`, restated at `:619-621`): exam-wide
(`exam_phase_id is None`) XOR one phase. Cycle-only scope "cannot even be
expressed — this module has no `exam_cycle_id` parameter". Section scope is not
mentioned as excluded; it is simply absent from the design.

**What would have to change** (statement of fact, not a proposal): the module
would need (a) a section argument or a resolver on the write path — the payload
at `:421` and the scope validation at `:663-686`, which today validates only
that `exam_phase_id` belongs to `exam_id`; (b) the ownership reads at `:476-486`
and `:560-570` extended, since two rows differing only by `section_id` would
otherwise collide on the same identity tuple; and (c) an answer to Q3, because
the module has a `topic_id` and a section needs a `subject_id`.

---

## Q2 Every writer of `exam_topic_coverage`

Searched three ways: the table name, `_COVERAGE_FIELDS` (the model), and every
`.insert(` / `.update(` / `insert into` call shape.

| # | Writer | Site | Can set `section_id`? | Requires one? | Validation |
|---|---|---|---|---|---|
| 1 | **Derivation** `derive_topic_coverage` | insert `coverage_derivation.py:761`, update `:594` | **No** — not in the payload (`:421-449`) | n/a | Phase-belongs-to-exam only (`:663-686`) |
| 2 | **CMS single create** `create_exam_topic_coverage` | `admin_exam_intel_cms.py:2659-2690`, insert at `:2681` | **Yes** — `section_id` ∈ `_COVERAGE_FIELDS` (`:2631-2637`) | No, optional | **Strongest**: must resolve in `exam_phase_sections` and its `exam_phase_id` must equal the row's (`:2674-2679`, 422 otherwise). Forces `reviewer_status='pending_review'` (`:2680`) |
| 3 | **CMS bulk import** `exam-topic-coverage` entity | registry `admin_exam_intel_cms.py:4560-4568` | **Yes** — same `_COVERAGE_FIELDS` allowlist | No | **None for the section.** The entry has `"fks": {"exam_id": "exams"}` and **no `row_validator`**, unlike `pyq_papers` directly above it (`:4551-4557`). A section from another phase, or a non-existent one, is not caught here |
| 4 | **Demo seed** | `app/supabase/seeds/exam_intelligence_demo_ssc_cgl.sql:132-140` | **No** — column not in the INSERT list | n/a | n/a. Writes SSC tier-1 rows `source_basis='hybrid'`, `exam_priority_score` 88, `reviewer_status='locked'` |
| 5 | **Import template** | `app/supabase/seeds/templates/exam_intelligence_import_template.sql:159-168` | **No** — `section_id` is absent from the column list | n/a | Writes `source_basis='official_syllabus'`, `reviewer_status='pending_review'` |
| 6 | Migrations | `149:139` sets `source_kind='manual'` where NULL; `116:46` adds an `updated_at` trigger; `242:411-414` a BEFORE INSERT/UPDATE stream-consistency trigger | No (none write `section_id`) | n/a | The 242 trigger rejects cross-exam `stream_id`, nothing about sections |
| 7 | `scripts/`, `workbench/` | none write this table (`workbench/scripts/lock_coverage.py` only PATCHes `reviewer_status` through the admin API, `:99-112`) | n/a | n/a | n/a |

**Which writer produced the 13 Prelims rows?** Writer 2 or 3 — they are the only
two that can set `section_id`, and both are the CMS. Their `source_basis` is
`official_syllabus`, which matches the import template's literal (`template:166`)
but the template cannot write a section, so a templated row would have NULL.
That leaves the CMS create endpoint (validated) or the CMS bulk import
(unvalidated) as the producer. Code cannot distinguish them; `admin_audit_logs`
can — see §Requires live data. Either way the existence proof holds: **the
column is usable, and one writer already validates it.**

The two SSC `hybrid` rows at 78-88 in the brief match the demo seed exactly
(writer 4) — they are fixture data, not authored intelligence.

---

## Q3 What would a section on a Mains row resolve to?

**Shape of the relation, from schema alone.**

- `exam_phase_sections` hangs off `exam_phase_id` and `subject_id`, with
  `unique(exam_phase_id, subject_id, section_label)` (`030:77-92`). The label is
  part of the key, so **one subject may own several sections within one phase** —
  the schema explicitly permits it.
- `topics.subject_id` is a single nullable FK, so a topic has **at most one**
  subject.
- `exam_topic_coverage` keys on `topic_id` (`030:100-101`); there is no
  `subject_id` on the coverage row at all.

Therefore: **`topic → subject` is a function** (partial — a topic may have no
subject). **`subject → section` is a relation**, one-to-many within a phase. The
composition `topic → section` is a function **only if** every subject on that
phase carries exactly one section. Where a subject carries two (say a paper
split into Section A and Section B), a coverage row cannot be attributed to one
of them from `topic_id` alone, and no other column on the row disambiguates.

Two further wrinkles the schema forces:

1. Migration 287 marks electives on `exam_phase_sections`
   (`287:129-137`, keyed on `subjects.subject_group='upsc-optional'`), so the
   elective flag lives on the section, not the subject. If a subject had two
   sections and only one were marked elective, a topic would resolve to
   conflicting scope answers.
2. The CMS validator requires `section.exam_phase_id == row.exam_phase_id`
   (`admin_exam_intel_cms.py:2677-2679`). A coverage row written **exam-wide**
   (`exam_phase_id IS NULL`, which the derivation's own contract permits, `:38`)
   can therefore never carry a section at all under that rule.

**How many sections the Mains phase actually carries is a data question.** The
brief gives 12 elective + 51 compulsory sections for the exam, not per phase, and
gives no per-subject section count. SQL in §Requires live data settles whether
the mapping is a function today.

---

## Q4 Where `exam_priority_score` comes from, and what bounds it

### The v2.0 model

`compute_exam_topic_scores` (`score_snapshots.py:290`), `MODEL_VERSION = "v2.0"`
(`:29`). Per topic (`:662-693`):

```
freq_component   = topic_count / cohort_total                    # :666
cov_component    = locked_coverage.exam_priority_score / 100     # :669
evidence_quality = min(topic_count / 10, 1.0)                    # :670
cohort_mean      = cohort_total / cohort_topics                  # :675
cohort_lift      = topic_count / cohort_mean                     # :676
prominence       = min(cohort_lift / 10.0, 1.0)                  # :677, _LIFT_FULL_MARKS = 10.0 (:35)
weight           = 1 - cohort_total/scope_total                  # :679 → _cohort_weight (:223-236)
frequency_term   = freq_component*50*(1-weight) + prominence*50*weight   # :684
exam_priority_score = round(frequency_term + cov_component*40 + evidence_quality*10, 2)   # :686-688
```

Nominal range 0-100 (50 + 40 + 10). Why it cannot approach that here:

1. **The 40-point term is self-referential and starts at zero.** `cov_component`
   reads *existing locked coverage's* `exam_priority_score` (`:669`). On UPSC
   Mains that coverage is the derivation's own prior output, so the first pass
   contributes 0 and later passes only ever feed back a fraction of an already
   small number. The observed Mains max of 36.10 is consistent with this term
   being near zero. **This is an artefact of bootstrapping, not of normalisation.**
2. **The 50-point frequency term is a share.** `freq_component` is a topic's
   count over its cohort's total. With 1,252 topics over ~8,300 primary-counted
   questions the mean topic is ~6.6 questions; a topic needs >20 % of its whole
   cohort to earn 10 of the 50 points. The blended alternative, `prominence`,
   needs **10× the cohort mean** for full marks (`_LIFT_FULL_MARKS = 10.0`,
   `:35`) — ~66 questions for one topic here. **This bound is intrinsic to
   cohort-share normalisation**, and `_LIFT_FULL_MARKS` is the one coefficient
   that moves it.
3. **The 10-point evidence term saturates at 10 questions** (`:670`). A
   mean-sized topic earns ~6.6 of 10. This is the only term most topics score on,
   which is why the Mains average is 6.42 — almost exactly the evidence term
   alone.

`_cohort_weight` (`:223-236`) is explicitly a neutrality device: it is 0 when the
exam is a single cohort, making v2.0 "bit-for-bit identical to v1.0" there. It
redistributes between two axes; it does not raise the ceiling.

The optional-subject maxima the brief reports (12.26-14.95) sit where this
predicts: a specialised paper's cohort is small, so `weight` is high and the
score rides on `prominence`, which needs a 10× outlier to pay out.

### Every signal-bearing column on `exam_topic_coverage`

| Column | Meaning | Comparable across `source_basis`? |
|---|---|---|
| `exam_priority_score` `numeric(5,2)` (`030:106`) | importance, **two unit systems** | **No** — the defect |
| `is_high_yield` `boolean` (`030:107`) | derived: `freq_component > 0.15` OR cohort lift ≥ 3.0 OR inherited from locked coverage (`score_snapshots.py:690-696`) | **Boolean, so partially** — but the predicate differs by producer: authored rows carry a human's flag |
| `confidence_score` `numeric(4,3)` (`030:108`) | derived: `0.3 + evidence_quality*0.7` (`:697`) | **No** — a derived row's confidence is a question-count proxy; an authored row's is a human's certainty |
| `coverage_depth` enum (`030:103`) | `bucket_coverage_depth(evidence, mentions, high_yield)` (`coverage_derivation.py:394-397`) | **Most comparable of the set** — a bounded ordinal vocabulary (`unknown/none/mentioned/light/normal/deep/core`) both producers use with the same words |
| `predictability` `numeric`, `predictability_band` text (`288:33-38`) | PRED-01: `0.65*breadth + 0.25*regularity + 0.10*recency` within the subject-paper; band is a percentile floored by absolute breadth (`288:67-73`) | **Band yes, score no.** The band is already percentile-within-paper, i.e. the same normalisation `priority_scale` applies to priority. NULL on any row with no year evidence |
| `expected_difficulty` text (`030:105`) | free text, no producer sets it in the derivation | n/a |
| `source_basis` (`030:110`) / `model_version` / `source_kind` (`149:123`) | provenance | the discriminator itself |

`predictability_band` is the one signal already delivered on a cross-producer
scale, and `coverage_depth` is the one ordinal both producers speak.

---

## Q5 Who reads the score, and does anything read `source_basis`?

### Consumers of `exam_priority_score` / `coverage_priority`

| Consumer | Site | Compares across basis? | Effect |
|---|---|---|---|
| Planner `_score_topic` | `planner.py:885-892`, term at `:906` | **No, since RANK-SCALE-01** — reads `comparable_priority`, falling back to raw only when nothing attached one | Fixed |
| Planner loader | `planner.py:438-442` | attaches the percentile over the exam-wide set | The fix's insertion point |
| Mission control | `mission_control.py:447-460` | **No** — attaches, then sorts on `comparable_priority` (`:451`) | Fixed |
| Plan impact | `plan_impact.py:201-203`, `:129` | **No** — attaches over a shared reference set so a before/after delta is not a change of denominator | Fixed |
| **Planner board palette** | `planner_board.py:295`, sort `:313` | **Moot — it reads a key that does not exist** (see D16) | Every candidate 0.0 |
| `GET /api/study/topics` | `api/study_os.py:1264` | Emits raw `coverage_priority` as `exam_priority_score` | Displays the raw two-scale number |
| Subject hub ordering | `subjects.py:318-331` | Sorts by raw `exam_priority_score` desc | Within one subject the basis is usually uniform, so mostly harmless; across subjects it is not |
| Writing planner tasks | `writing_practice/planner_tasks.py:174` | Passes raw through into task context | Display only |
| Admin coverage reads | `exam_intelligence/coverage.py:258-259`, `:460` | Returns both score and `source_basis` to the caller | Admin surface, caller decides |
| Evidence API | `api/evidence.py:46-47` | Selects both | Display |

### The snapshot component's arithmetic

`_score_topic`'s snapshot term (`planner.py:895-900`):
`min(15, score/100 * 15 * confidence)`.

- input **14.95** → `0.1495 × 15 = 2.24` before confidence;
- input **95** → `0.95 × 15 = 14.25` before confidence.

A **6.4× gap on the same axis**, from the unit system alone. Note this term reads
`snapshot["exam_priority_score"]` — the raw locked snapshot — and **is not
covered by RANK-SCALE-01**, which attaches the comparable value to *coverage*
rows only. The coverage term was fixed; the snapshot term was not.

### Does anything read `source_basis`?

**Yes — and this refutes the brief's suspicion.** `exam_intelligence/priority_scale.py`
(RANK-SCALE-01) is a module written for exactly this defect; its docstring
tabulates the same live split this brief restates (`:9-24`) and dates it
2026-09-12. It groups rows by `source_basis` and emits a **mid-rank percentile
within each group** (`:90-110`), deliberately not rescaling derived scores onto
0-100 (`:34-36`), and returns raw scores untouched when the set spans a single
basis (`:96-99`). Three callers: `planner.py:34,440`, `mission_control.py:22,447`,
`plan_impact.py:26,201-203`.

Elsewhere `source_basis` is selected and surfaced (`coverage.py:190,259`;
`evidence.py:47`) but not acted on, and `competition.py:201-244` reads the
same-named column on a different table.

**So the column is no longer inert — but the fix is partial.** It covers the
coverage rows three consumers rank on. It does not cover: the palette
(`planner_board.py`), `/api/study/topics` (`api/study_os.py:1264`), the subject
hub's ordering (`subjects.py:329-331`), or `_score_topic`'s snapshot term
(`planner.py:895-900`).

---

## Q6 What the palette can show today

Per candidate topic, against what `list_candidates` (`planner_board.py:260-315`)
already has in hand from `load_scoped_coverage_checked`:

| Wanted | Available? | From | Cost |
|---|---|---|---|
| **Weightage** | **Yes** — already on the row as `coverage_priority`, plus `comparable_priority` attached at `planner.py:438-442` | `exam_topic_coverage.exam_priority_score` | **Zero** — already fetched. Currently read under the wrong key (D16) |
| **High-yield status** | **Yes** — already emitted (`planner_board.py:305`) | `exam_topic_coverage.is_high_yield` | **Zero** |
| **PYQ frequency** | **Yes, with one extra call** | `verified_pyq_topic_counts(supabase, exam_id)` (`exam_intelligence/coverage.py:269`) returns `{topic_id: verified_primary_pyq_count}` for the whole exam, or `None` on an incomplete read | **One exam-wide call, not per topic**: three paginated read groups (papers → questions in 250-id chunks → primary tags in 250-id chunks). `_compute_plan` already makes this exact call (`planner.py:1614`) |
| **Syllabus tree position** | **Partially** | `subject_id`/`subject_name` and `parent_topic_id`/`topic_level` are already carried on every row (`planner.py:415-421`) | **Zero for the ids.** But the **parent's name is not guaranteed**: the loader fetches `topics` only for ids that appear in coverage rows (`planner.py:~356`), so a macro topic with no locked coverage row of its own is absent from the map and its name cannot be resolved without an extra read |

**Plainly: three of four are available today at no extra query** (weightage,
high-yield, and the tree *position* as ids/level), **one needs a single
exam-wide call** (PYQ frequency), and **one is partial** — rendering
"subject → macro topic → microtopic" as *names* needs a second `topics` read for
parent ids that carry no coverage row.

Two things the palette does **not** have and cannot get from this row: the
section (Q1) and, for `predictability_band`, the column is not in the loader's
select list (`planner.py:330-339`) even though it exists on the table (`288:37-38`).

---

## Corrections to stated facts

1. **"Nothing reads `source_basis`" is out of date.** RANK-SCALE-01 landed:
   `priority_scale.py` exists, the planner selects and carries `source_basis`
   (`planner.py:337`, `:432`), attaches a within-basis percentile (`:438-442`),
   and `_score_topic` ranks on it (`:885-892`). Mission control and plan impact
   do the same. The brief's framing describes the state before that merge.
2. **The palette's "priority 0" is not the unit-system defect.** It is a key
   mismatch — `planner_board.py:295` reads `exam_priority_score`; the rows carry
   `coverage_priority` (`planner.py:431`). The two defects are independent and
   the second would survive any normalisation work.
3. **The Mains phase id differs from the previous investigation.** This brief
   names `f42ffb84-…`; PLAN-POOL-01 (2026-09-13) established `626ec667-…` as the
   phase carrying the 1,497 Mains rows, and `workbench/scripts/lock_coverage.py:34`
   pins `626ec667-…`. Both cannot be the phase holding the same 1,497 rows unless
   the corpus was re-scoped between the two dates. Not resolvable from code —
   see §Requires live data.
4. **"Two other locked rows on SSC tier-1 are hybrid (78-88)"** — these are demo
   fixture rows, written by `exam_intelligence_demo_ssc_cgl.sql:132-140`, not
   authored exam intelligence. Treating them as a third human-authored basis in
   any analysis would be wrong.
5. **The suspected common origin is confirmed for the section and refuted for
   the score.** The derivation was never given a section dimension (Q1). It *was*
   given a score dimension — a deliberate, documented one — whose ceiling is a
   consequence of share normalisation plus a self-referential term, not an
   oversight.

---

## Defects observed

- **D16 — the palette scores every candidate 0.0.** `planner_board.py:295` reads
  `cov.get("exam_priority_score")`; `load_scoped_coverage_checked` emits
  `coverage_priority` (`planner.py:431`) and `comparable_priority` (`:438-442`).
  Neither key is `exam_priority_score`, so `_score` returns 0.0 for every row and
  the sort at `:313` degenerates to alphabetical by topic name. This is the whole
  of the reported symptom, and it is one word.
- **D17 — the elective scope filter is a no-op on Mains.** `planner.py:600` keeps
  a row when `section_id` is falsy; all 1,497 Mains rows are NULL (Q1), so
  unchosen optionals reach every consumer of `load_scoped_coverage`. The scoping
  merged in #1100/#1102 excludes nothing on this phase.
- **D18 — `_score_topic`'s snapshot term still mixes unit systems.**
  `planner.py:895-900` divides the raw locked-snapshot score by 100. RANK-SCALE-01
  fixed the coverage term beside it but not this one: 14.95 yields 2.24 points,
  95 yields 14.25.
- **D19 — bulk import can write an unvalidated `section_id`.** The registry entry
  (`admin_exam_intel_cms.py:4560-4568`) allows the full `_COVERAGE_FIELDS` but
  declares no `row_validator`, while the single-create endpoint enforces
  section-belongs-to-phase (`:2674-2679`). Two paths into one column, one of them
  unchecked.
- **D20 — a topic can hold two coverage rows and the palette would show it
  twice.** `exam_topic_coverage`'s unique indexes key on
  `(exam, cycle, phase, topic)` (`030:124-131`), so an exam-wide row
  (`exam_phase_id IS NULL`) and a phase-scoped row for the same topic are both
  legal. `_load_locked_coverage_checked` emits one item per coverage row with no
  dedupe by `topic_id`, so both would appear. This is the most likely cause of
  the duplicate "Balance of power" rows mentioned in the brief — recorded, not
  chased; the confirming query is in §Requires live data.
- **D21 — the palette exposes no search.** `list_candidates`
  (`planner_board.py:260`) takes no query parameter and the module contains no
  search or filter term, so the reported non-functional search box is
  frontend-only. Noted per the brief; not chased.
- **D22 — `predictability_band` is not selected by the planner's loader.** The
  column exists (`288:37-38`) and is written by the derivation (`:431-432`), but
  `planner.py:330-339` does not select it, so no learner surface can show the one
  signal already normalised across producers.

---

## Requires live data

Each question, with the SQL that answers it, is in
`workbench/sql/COV-DIM-01_probe.sql` under the same numbering.

1. **Is `topic → section` a function on the Mains phase?** (Q3 — decides whether
   the section dimension can be populated deterministically at all.) Healthy:
   every subject on the phase has exactly one section.
2. **Which phase actually holds the 1,497 Mains rows — `f42ffb84-…` or
   `626ec667-…`?** (Correction 3.)
3. **Which writer produced the 13 sectioned Prelims rows** — the validated CMS
   create or the unvalidated bulk import? (Q2, D19.)
4. **Do any coverage rows carry a `section_id` whose section belongs to a
   different phase** — i.e. has D19 already been exercised? Healthy: zero rows.
5. **Does any topic hold more than one locked coverage row for this exam?**
   (D20, the duplicate palette entries.) Healthy: zero.
6. **What is the actual distribution of `exam_priority_score` by
   `source_basis` and phase**, and does any derived row exceed any authored row?
   (Q4 — confirms the ceiling claim against live data rather than the brief's
   summary.)
7. **How many locked rows carry `predictability_band`**, and is it populated on
   the optionals? (D22 — whether the one comparable signal is actually there.)

---

## Live probe results — 2026-09-14

All seven probes run by the operator. Four of this report's conclusions change.

### §1 — `topic → section` IS a function on Mains; the ambiguity is on Prelims

Every Mains subject carries **exactly one** section: four GS papers, twelve
optional papers, Essay — `sections_per_subject = 1` on all seventeen. So the
composition `topic → subject → section` **is deterministic for Mains**, and the
section dimension can be populated without a disambiguation rule. Q3's
conditional resolves in the favourable direction.

The ambiguity is on the phase this report did not expect:

| phase | subject | sections | labels |
|---|---|---:|---|
| prelims | `upsc-cse-prelims-gs` | **3** | "General Studies Paper I" × 3 |
| prelims | `upsc-csat` | **2** | "General Studies Paper II / CSAT" × 2 |

**Those duplicates should be impossible.** `exam_phase_sections` is
`unique(exam_phase_id, subject_id, section_label)` (`030:92`), and the labels
printed identical. Either the live index is absent, or the labels differ by
characters that do not render (trailing space, non-breaking space, case). Both
are defects — see D23.

§1b returns each Mains subject **twice**, once with
`max_sections_for_its_subject = 1` and once with `0`. That is the two-phase
split below: sections exist on only one of the two phases named `mains`.

### §2 — the corpus is on TWO Mains phases, not one

| `exam_phase_id` | slug | cycle | targetability | locked rows | with section | max score |
|---|---|---|---|---:|---:|---|
| `626ec667-…` | mains | **NULL** | TEMPLATE (never a plan target) | **1,497** | 0 | 36.10 |
| `f42ffb84-…` | mains | `787b0067-…` | cycle-attached | **1,317** | 0 | 36.10 |
| `6566d50e-…` | prelims | `787b0067-…` | cycle-attached | 13 | **13** | 95.00 |

Correction 3 resolves as **neither brief was wrong**: PLAN-POOL-01's
`626ec667-…` and this brief's `f42ffb84-…` both exist, both are slug `mains`,
and the corpus was **duplicated across them**, not moved — 1,497 + 1,317 = 2,814,
which is exactly the derived row count §6 reports. 180 topics have a row only on
the template phase.

This also confirms PLAN-POOL-01's core finding from the other side: the phase
holding 1,497 rows has `exam_cycle_id IS NULL`, so
`exam_target_window.py:56-57` can never target it. The planner's usable Mains
pool is the 1,317 on `f42ffb84-…`, and only when the resolver picks Mains over
Prelims — both hang off the same cycle `787b0067-…`.

### §3 — the 13 sectioned rows came from a writer this report did not list

- **No `admin_audit_logs` rows at all** for those coverage ids. Both CMS paths
  audit unconditionally (`admin_exam_intel_cms.py:2683-2687` for create; the
  registry's `"audit": "exam_intel.cms.coverage.bulk_create"` at `:4566`).
- Their provenance: `source_basis='official_syllabus'`, `source_kind='manual'`,
  `model_version=NULL`, all 13 created **2026-05-26 11:23:25 → 11:23:29** — a
  four-second burst.

`source_kind='manual'` is not evidence of the CMS: migration `149:139`
backfilled that value onto every pre-existing row. An unaudited four-second
insert of 13 rows is a **direct SQL session**, not an API call. Q2's writer
enumeration was therefore incomplete: there is an **eighth path — operator psql**
— which no code in this repository governs and which is how `section_id` came to
be set. The existence proof still holds; the provenance claim in Q2 ("writer 2
or 3") does not.

### §4 — the unvalidated bulk-import path has not been exercised

Zero rows where a coverage row's `section_id` points at a section on a different
phase. D19 remains latent.

### §5 — every Mains topic is duplicated, exactly as D20 predicted

Every sampled topic returns `locked_rows = 2`, one row on each Mains phase, both
`evidence_derived`, **both carrying the identical score** ("5.07, 5.07";
"15.21, 15.21"; …). Including `af4729dd-…` **"Balance of power: methods and
contemporary relevance"**, 9.20 twice — the duplicate the brief reported seeing
in the palette, explained exactly: `_load_locked_coverage_checked` emits one item
per coverage **row** and never dedupes by `topic_id`, so a topic present on both
Mains phases is offered twice. D20 confirmed against data.

### §6 — the ceiling claim holds, and the brief undercounted the corpus

| phase | basis | rows | min | avg | max | high-yield |
|---|---|---:|---|---|---|---:|
| mains | `evidence_derived` | **2,814** | 0.00 | 6.46 | 36.10 | 91 |
| prelims | `official_syllabus` | 13 | 60.00 | 82.31 | 95.00 | 11 |

`max(derived) = 36.10 < min(authored) = 60.00` — the structural gap is real, and
Q4's analysis stands. Note the derived corpus is **2,814 rows, not 1,497**: the
brief counted one of the two Mains phases.

Per-subject maxima confirm the cohort-normalisation prediction precisely: GS4
reaches 36.10 and GS1 28.42, while **every one of the twelve optionals tops out
between 12.26 and 14.95** — Geography P1 at 14.95 and Anthropology P2 at 12.26,
the exact bounds the brief quoted. A specialised paper's small cohort drives
`weight` high, so the score rides on `prominence`, which needs a 10× outlier to
pay out (`_LIFT_FULL_MARKS`, `score_snapshots.py:35`).

Average confidence differs the same way: 0.597 derived versus 0.935 authored —
consistent with the derived value being `0.3 + evidence_quality*0.7` (`:697`),
i.e. a question-count proxy, not a human's certainty.

### §7 — `predictability_band` is populated and is the strongest available signal

| band | rows |
|---|---:|
| occasional | 1,085 |
| likely | 623 |
| rare | 464 |
| near_certain | 260 |
| (null) | 382 |

**2,432 of 2,814 derived rows carry a band** (86 %). Across the twelve optional
papers it is **complete** — every row banded — except `psir-p1`, where 50 of 254
lack one. The 13 authored Prelims rows have no band, as expected: they have no
year evidence behind them.

This materially raises D22's importance. The band is percentile-within-paper
(`288:71-73`), so it is **already comparable across subjects and across
producers** in a way `exam_priority_score` is not — and it is the one signal the
palette could show today that means the same thing for a PSIR topic and a GS
topic. The planner's loader simply does not select it (`planner.py:330-339`).

### Consequences for the two dimensions

- **Section:** populatable for Mains deterministically (one section per subject),
  **but only for the 1,317 rows on `f42ffb84-…`** — the template phase carries no
  sections at all, so its 1,497 rows have nothing to point at. Any backfill must
  decide what the template phase's rows are for before it can decide their scope.
- **Score:** the two-unit-system finding is confirmed on live data, and
  `predictability_band` is a populated, already-normalised alternative that no
  learner surface currently reads.

---

## Defects observed (added after the live run)

- **D23 — duplicate `exam_phase_sections` rows on Prelims.**
  `upsc-cse-prelims-gs` has three sections and `upsc-csat` two, with labels that
  print identically, against a `unique(exam_phase_id, subject_id, section_label)`
  (`030:92`). Either the index is missing in the live database or the labels
  differ by invisible characters. Until resolved, `topic → section` is ambiguous
  on Prelims — the one phase whose coverage rows actually carry a section.
- **D24 — the Mains corpus is duplicated across two phases.** 1,497 rows on the
  cycle-less template `626ec667-…` and 1,317 on the cycle-attached
  `f42ffb84-…`, same topics, identical scores. Everything reading locked coverage
  exam-wide sees each topic twice (the palette, the calibration subject set, the
  Subject Hub); the planner's phase filter (`planner.py:1528`) hides it only
  because it keeps one phase. 180 topics exist solely on the untargetable
  template phase and are invisible to the planner entirely.
- **D25 — an unaudited direct-SQL write path into `exam_topic_coverage`.** The 13
  sectioned rows have no `admin_audit_logs` entry and landed in four seconds.
  Every code path in this repo audits; this one did not go through code. Not a
  bug in the codebase, but it means `source_kind`/`source_basis` are the only
  provenance for those rows and the CMS's section validation never ran on them.
