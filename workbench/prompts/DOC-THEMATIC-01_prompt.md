# DOC-THEMATIC-01 — write up the thematic corpus session

## WHY THIS EXISTS

On 2026-09-11/12 the optional PYQ corpus went from 4,038 questions (2011-2026)
to 8,302 (1980-2026), and the whole second half — the decision, the schema
shape, the load, 4,264 hand-read tags, the rescore, the republication — exists
only in a chat transcript. Two strategy documents are now wrong. There is no
defects note for any of it.

This task writes it down. It is documentation only: **no code, no SQL, no API
calls.**

## PRIMING

Read, in this order:

1. `docs/status/2026-09-09-mains-optionals-strategy-rev2.md`
2. `docs/status/2026-09-10-mains-optionals-strategy-rev3.md`
3. `docs/status/2026-09-11-mains-optionals-strategy-rev3.1.md`
4. `docs/status/2026-09-10-optionals-corpus-defects.md`
5. `docs/status/2026-09-11-optionals-tagging-defects.md`
6. `docs/status/2026-09-12-optionals-publication-defects.md`
7. `workbench/scripts/load_thematic.py` — its docstring carries the design
8. `workbench/scripts/apply_thematic_tags.py`,
   `review_thematic_questions.py`, `lock_snapshots.py`, `lock_coverage.py`

The scripts' docstrings were written as the work happened and are the most
reliable record. Prefer them over inference.

---

## WHAT HAPPENED, as source material

### The gap nobody had named

The compiler PDFs carry two halves. The **year-wise** half ("here is the 2019
PSIR Paper-I, in order") produced the 4,038 questions loaded earlier. The
**topic-wise** half ("here is every question ever asked on Political Theory,
with years") was extracted at the same time — 9,117 rows — and then sat unused
because it had no schema home: no paper, no question number, no join key.

4,273 of those rows are from **before 2011** and exist in no year-wise section.
They were not abandoned; they were never loadable in the shape the schema
expected. rev2 listed this as an open question and it stayed open for days.

### The shape decision, and the two rejected alternatives

Three options were considered:

- **A — synthesise papers.** Create a paper row per subject-year and treat the
  rows as ordinary questions. Everything downstream works, but it asserts a
  paper composition the source does not contain.
- **B — a parallel table.** Honest about what the rows are, but invisible to
  `score_snapshots`, `coverage_derivation`, the explorer and the planner until
  each is taught to read it.
- **C — real rows, honest papers.** Load into `pyq_questions` on paper rows
  that explicitly disclaim composition.

**C was chosen** and needs no migration: `question_number` is already nullable
(migration 224 indexes it `where not null`), and `pyq_papers` requires only
`exam_id`. The 31 paper rows carry `metadata.paper_reconstructed: false` and a
note saying the source records the year a question was asked, not the paper it
sat in. `source_question_ref` uses a `T` prefix — `PSIR-P1-1991-T003` — so a
thematic row is distinguishable from a year-wise one at a glance.

Record why B was rejected specifically: it was the most honest description of
the data and it still lost, because "fully consumed downstream" was the
requirement and B would have needed every consumer changed.

### What was loaded

- 31 paper rows, one per year 1980-2010. Not one per subject-year: that would
  have been 309 rows and reintroduced the card-count explosion M1 rejected.
- 4,264 questions of 4,273. Eight were cross-indexed duplicates — the compiler
  filed the same question under two topic headings — and one more was refused
  by the server's content hash, a near-duplicate the load-time check missed
  because it compared exact text and the server normalises punctuation.
- Every row carries exactly one year. The multi-year case that shaped the early
  design discussion does not occur in the data.

### The tagging

All 4,264 read individually, subject-paper by subject-paper.

A heading-based shortcut was **tried and largely failed**, and that is worth
recording so nobody tries it again: the compiler's topic headings map to
syllabus units well enough that 2,630 rows narrowed to a unit's children, but
**zero rows resolved automatically** (every matched unit has multiple children)
and 1,643 matched no unit at all. Geography mapped not at all; Sociology barely.

An earlier IDF text-matching trial on the year-wise corpus was ~10% wrong in
its highest-confidence band, which is why neither shortcut was accepted.

### The rescore, and what changed

After review, snapshots were recomputed on the full corpus. **1,227 previously
locked v2.0 snapshots had to be rejected first** — locked rows are not
overwritten — and the same was true of 1,497 locked coverage rows, which had to
be walked back to draft before a re-derive would update them. Both are worth
documenting as a procedure: a recompute after a corpus change is a
five-step cycle, not one call.

The ranking changed shape, which is the substantive result:

- History Paper-I fell from **9 of the top 12 optional topics to 4**. Its
  earlier dominance was partly an artefact of 180 map items inflating counts on
  period topics.
- PSIR Paper-I's top topics moved from Panchayati Raj and judicial review to
  the theory core — approaches to political theory, Marxism, Kautilya,
  Aristotle, Hobbes — which is what the paper has asked steadily since the
  1990s and which fourteen years of evidence could not see.
- Score range compressed from 1.24-24.48 to 1.08-14.95 as cohort denominators
  doubled. **Ordering is what matters; any consumer thresholding on a raw
  score needs revisiting.**
- 1,306 snapshots (79 more topics now have evidence), 1,497 coverage rows,
  48 high-yield.

---

## WHAT TO WRITE

### 1. `docs/status/2026-09-12-mains-optionals-strategy-rev4.md`

Amends rev3.1's sequence, which is now wrong — it describes a corpus of 4,038
and a chain that has since run twice.

State: what the corpus is now (8,302 questions, 47 papers, 1980-2026, two
halves distinguished by `metadata.corpus_half`); the C-shape decision and its
rationale; and a corrected sequence that includes the unlock-recompute-relock
cycle, since that is now a repeatable procedure rather than a one-off.

Do not restate M1-M10. Amend only what changed.

### 2. `docs/status/2026-09-12-thematic-corpus-defects.md`

The defects and findings from this half. At minimum:

- **The 1,000-row PostgREST ceiling bites in three more places.**
  `apply_thematic_tags.py` reported "already tagged: 0" on every run because an
  unfiltered tag fetch sees ~8% of 13,168 rows; `review_tags.py` had the same
  blindness until `reviewer_status` was added as a server-side filter;
  `lock_coverage.py` stopped at exactly 1,000 twice. Each was worked around
  differently. The route fix is already ticketed (EI-FIX-01) but the *pattern*
  — client-side filtering of an unbounded list — is the real defect and appears
  in several scripts.
- **`reviewer_notes` is capped at 500 characters** on
  `/items/{kind}/{id}/review` and dropped server-side anyway. A 700-character
  reason string failed 293 questions with a 422 that named the field.
- **A duplicate `idempotency_key` on `/pyq-questions` returns an unhandled
  500**, not a 409, so "re-running is safe" is true but the output is
  unreadable. The resume pattern — ask the server what exists, post only the
  remainder — is what actually works, and every script written for this load
  does it.
- The eight cross-indexed duplicates and the one hash collision, by ref.
- **Operational**: a pasted JWT lost its leading `e` twice more (1,389 chars
  starting `yJ`); `$hdr` does not update when the env var does; env vars are
  per-window and a script exiting with "set CCP_API_BASE" has done nothing.

### 3. Update `docs/status/2026-09-12-optionals-publication-defects.md`

Its end-state table says 4,038 questions and 1,320 coverage rows. Correct it,
and add a line that the figures there describe the year-wise half only.

---

## CONSTRAINTS

- **Documentation only.** No code, no SQL, no API calls, no migrations.
- Annotate, do not delete. rev2 and rev3 stay as written; rev4 amends them.
  This repo's convention is that a superseded decision keeps its reasoning.
- Cite `path:line` for every claim about code behaviour. Where the source is
  this session rather than the repo, say so — do not dress a transcript up as
  a code citation.
- Be specific about what `verified` means for this corpus: mechanically clean,
  de-duplicated, tagged, anchored on a registered document, **never diffed
  against an official UPSC paper** — the officials are unpublished before 2016
  and this corpus reaches to 1980.

## OUTPUT

The three documents. A one-paragraph summary of what a reader who knows only
rev3.1 needs to unlearn.

Offline: commit locally, do not push.
