# Explanation lane — status and handoff

Written 2026-09-25, at the end of the session that built this lane from nothing.

---

## What exists now

`pyq_question_explanations` holds **4,058 rows across six exams**, of which
**3,698 are verified and reach aspirants** on the mock attempt-review screen.

| exam | verified | rejected | needs_correction | pending |
|---|---:|---:|---:|---:|
| NABARD Grade A | 1,021 | 27 | — | — |
| UPSC CSE Prelims | 929 | — | 179 | 101 |
| RBI Grade B | 873 | 22 | — | — |
| SEBI Grade A | 394 | 8 | — | — |
| IFSCA Grade A | 345 | 17 | — | — |
| PFRDA Grade A | 136 | 6 | — | — |

Every verified MCQ in the five regulatory corpora now carries an explanation.
UPSC is complete apart from the rows blocked on the key problem below.

## The pipeline, end to end

None of this existed at the start of the day.

1. **Schema** — migration 230, already present, never used. Unique on
   `(question_id, explanation_source_type)`, so a question may hold one
   explanation per source. Do not collapse that to one per question; the
   multi-source import path depends on it.
2. **Write path** — CMS create/edit routes on the exam-intelligence router,
   plus `_IMPORT_CONFIG` registration. Rows are born `pending`.
3. **Review route** — `POST .../pyq-question-explanations/{id}/review`,
   wrapping the `cms_review_pyq_question_explanation` RPC. Body is flat:
   `{status, reason}`, not the write envelope.
4. **Read path** — verified explanations attach live at the mock attempt-review
   endpoint as `questions[].pyq_explanation`, following the `solution_strategies`
   pattern. Live, not snapshotted, so past attempts benefit and an un-verified
   explanation disappears again.
5. **Frontend** — `PyqExplanationPanel`, with per-option rationales rendered
   beside their options.

## The loop, per exam

1. Export with psql (the SQL client caps at 100 rows). The query left-joins
   `pyq_question_explanations` and selects only rows with none, so it is
   idempotent — a re-run never re-drafts existing work.
2. Commit the source file, PR, merge.
3. Fire the drafting prompt. The canonical version is EXPL-04's text; later
   batches added the aspirant-friendly language rule and the reasoning-puzzle
   rule, and those are now permanent.
4. Read the 20-row sample at the end of the notes file. Accept or reject.
5. Apply with the operator script: read the worksheet with
   `[System.IO.File]::ReadAllText(path, UTF8)`, fold `option_rationales` to
   `{option_id: rationale}`, wrap `formula_used` in an array.
6. Bulk-verify `draft_confidence=high`; read medium and low.

## Open, in priority order

### 1. 35 wrong answer keys in UPSC 2020 and 2024 — BLOCKED on two PDFs

Confirmed against UPSC's own published final keys. 16 in 2020, 19 in 2024,
about one question in six per paper, scattered with no offset pattern. The
corpus follows booklet Set C (2020) and Series D (2024), proved by the dropped
questions matching exactly.

These questions are live and marking correct answers wrong.

**Why it is not applied yet:** 2020 Q75 (hundi) shows the corpus's option order
does not always match the booklet's — UPSC's key letter and the corpus's letter
designate different text. Applying 35 corrections by letter could create 35 new
wrong keys. Corrections must resolve to option *text*.

**What is needed:** the 2020 GS Paper I booklet (Set C) and the 2024 GS Paper I
booklet (Series D, `QP-CSP-24-GENERAL-STUDIES-PAPER-I-180624.pdf`), then the
UPSC-KEY-APPLY-01 run.

The 179 `needs_correction` rows are the explanations for these two papers, held
because they defend the stored key.

### 2. The export query is missing the stimulus join

Every export this session fetched `question_text` and options only. Comprehension
questions carry their passage in `pyq_question_stimuli`, and 73 of 76 UPSC CSAT
rows have one — but the drafting agent never saw them, so those explanations were
written without the passage they concern. Add the join before the next batch, and
consider redrafting those 73.

Only 3 questions genuinely lack a passage: 2025 has 2, 2026 has 1.

### 3. ~23 wrong keys in the regulatory corpora

Found while drafting, evidenced in the `key_note` of the rejected rows. Among
them: colostrum keyed as "Plasma milk", Natya Shastra keyed as the text on
statecraft, PMSBY eligibility keyed 18–60 when it is 18–70, the Padma Awards
Committee keyed as headed by the President. Query the rejected rows' `key_note`
for the full list with reasoning.

### 4. Orphaned-stimulus sweep

31 unanswerable questions were archived this session, found by accident rather
than by a detector. Migration 281's detector has only ever run on RBI 2022. It
has never run on NABARD, SEBI, IFSCA or PFRDA.

### 5. Control-year key check

The 2020/2024 corruption may not be confined to those papers. A control sample
of 20 questions from two other years was requested and could not be completed —
the environment cannot reach upsc.gov.in, and the 2023 and 2025 keys were not
uploaded. Until that is done, "two bad papers" is a hypothesis, not a finding.

### 6. Smaller items

- 6 repairable data defects: two RBI rows with options shifted by a converter
  bug, SEBI 2025 Q6's corporate tax listed twice, the NCRPS ₹10,000 vs ₹1,00,000
  vintage conflict, RBI 2022 Q118 carrying the wrong shared block.
- Tag defects flagged but not fixed: 90 in UPSC, 18 IFSCA, 5 PFRDA, 2 RBI.
- 154 coverage locks and 23 wrong primary tags, from the parallel RBI session.
- SSC CGL's 850 questions need their review pass before explanations can start.

## Gotchas this session added

- **`Get-Content -Raw` reads UTF-8 as cp1252.** Use
  `[System.IO.File]::ReadAllText(path, UTF8)`. Three separate mojibake scares
  today were PowerShell display artefacts, not data corruption — always confirm
  encoding in SQL, never from console output.
- **A content PATCH demotes a verified row to `needs_correction`.** 101 SEBI rows
  were knocked out of verified by a repair that repaired nothing. Check review
  state before editing verified content.
- **Refreshing `$env:CCP_ADMIN_JWT` does not update an already-built `$headers`.**
  Rebuild the hashtable. A run that stalls with no progress is usually a dead
  token, not a slow API.
- **`$env:PGURI` and the payload-builder functions are per-session.** Worth
  putting in `$PROFILE`.
- **Long POST runs stall.** Resume by fetching what exists and posting the
  difference; the unique constraint makes re-posting safe.
- **Reject reasons are the record.** Every rejected row keeps its drafted text
  and `key_note`, which is where the evidence for the wrong keys lives.

## Policy settled this session

- High-confidence rows are bulk-verified after the batch sample is read and
  accepted; medium and low are read individually. A spot-check of 10
  bulk-verified SEBI rows found no defects.
- Where a question has more than one defensible answer, or its key or data is
  wrong, the explanation is **rejected** rather than published. Publishing an
  explanation that defends a single answer would teach something the question
  does not support.
- Explanations are never written for descriptive questions. UPSC Mains' 9,435
  rows belong to the writing-evaluation path, not this one.
