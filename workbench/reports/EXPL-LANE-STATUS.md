# Explanation lane and UPSC key repair — status and handoff

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

Every verified MCQ in the five regulatory corpora carries an explanation.

The 179 UPSC rows at `needs_correction` are the 2020 and 2024 papers, held while
their keys were checked. **Those keys are now fixed, and a check confirmed none
of the 179 disagrees with the corrected key — they can all go straight to
verified.** That is the first thing to do next session.

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
   endpoint as `questions[].pyq_explanation`, following the
   `solution_strategies` pattern. Live, not snapshotted, so past attempts
   benefit and an un-verified explanation disappears again.
5. **Frontend** — `PyqExplanationPanel`, with per-option rationales rendered
   beside their options.

## The loop, per exam

1. Export with psql (the SQL client caps at 100 rows). The query left-joins
   `pyq_question_explanations` and selects only rows with none, so it is
   idempotent — a re-run never re-drafts existing work.
2. Commit the source file, PR, merge.
3. Fire the drafting prompt (EXPL-04's text is canonical; later batches added
   the aspirant-friendly language rule and the reasoning-puzzle rule).
4. Read the 20-row sample at the end of the notes file. Accept or reject.
5. Apply with the operator script: read the worksheet with
   `[System.IO.File]::ReadAllText(path, UTF8)`, fold `option_rationales` to
   `{option_id: rationale}`, wrap `formula_used` in an array.
6. Bulk-verify `draft_confidence=high`; read medium and low.

---

## The UPSC key repair — done

**36 wrong answer keys were corrected**, verified against UPSC's own published
final keys, and propagated to the mock bank in one transaction. A platform-wide
check afterwards returned `mock_rows_wrong = 0`: every projected question now
agrees with its corpus key.

What was actually wrong, per paper — they were different problems:

- **2020**: `docs/reference/answer-keys/upsc_cse_2020_setc_prelims_gs1.csv` is
  the import source and carries 17 wrong answers. The import was faithful; the
  file is wrong. **Replace that CSV with UPSC's Set C key**, or a future
  re-import will restore the errors.
- **2024**: the corpus follows Series D, but a Set C key was loaded against it
  and later rekeyed by `rekey_2024_setd.sql`. That rekey misread 19 letters.
  **Do not re-run that SQL and do not import `pyq_2024_prelims_gs1_setc.json`'s
  keys** — either would put back roughly 79 wrong answers.
- **2025**: four keys are wrong (Q56, Q71, Q81, Q88). Not yet corrected.
  Three bad GS papers, not two.
- 2018, 2019, 2021, 2022, 2023 match UPSC on every scorable row.
- Five of the eight reference CSVs are materially wrong against UPSC, but the
  database only inherited the error in 2020 and 2025.

**Option order is sound**: 196 of 197 GS rows match the booklet. The single
exception was 2020 Q75, now fixed. The booklet labels its options (a)(c)(b)(d)
and the corpus labelled them a,b,c,d in reading order, so the same letter meant
different text. That is why corrections had to be applied by option id rather
than by letter.

Booklets for 2018–2024 and the 2025 official key are committed under
`workbench/sources/upsc-official-keys/`.

---

## Open, in priority order

### 1. Verify the 179 held UPSC explanations
Their keys are corrected and none disagrees. Straight to verified.

### 2. The 2025 keys — four wrong, not yet corrected
Q56, Q71, Q81, Q88. Same repair shape as the 36 already applied: resolve to
option id, then update `pyq_questions.correct_option_id`,
`pyq_options.is_correct` and `mock_question_options.is_correct` in one
transaction.

### 3. A misfiled paper in 2026
`b06305ad-cc93-4c27-b309-1b590f0a3247` holds 80 CSAT questions — quantitative
aptitude, reasoning, comprehension passages — but sits on the Prelims **GS**
phase `6566d50e`, not the CSAT phase `1d6611c7`. They surface in GS practice,
count toward GS coverage, and duplicate questions already correctly filed on
2026's CSAT paper. Confirm the overlap before moving or retiring it.

### 4. Stripped superscripts in maths questions
Five questions lost their exponents on import and are unanswerable as stored:
2026 Q20/Q22 ("6129 × 7307" is almost certainly 61²⁹ × 73⁰⁷) and Q69/Q79
("10m × 1000 × n = 7525 × 2532 × 3275"). 2025 Q5 may be intact — check whether
343, 2401 and 77777 are literal. The committed booklets have the real
expressions. This defect is invisible unless someone works the answer.

### 5. The export query is missing the stimulus join
Every export this session fetched `question_text` and options only.
Comprehension questions carry their passage in `pyq_question_stimuli`, and 73 of
76 UPSC CSAT rows have one — but the drafting agent never saw them, so those
explanations were written without the passage they concern. Add the join before
the next batch, and consider redrafting those 73. Only 3 questions genuinely
lack a passage.

### 6. ~23 wrong keys in the regulatory corpora
Found while drafting, evidenced in the `key_note` of the rejected rows. Among
them: colostrum keyed as "Plasma milk", Natya Shastra keyed as the text on
statecraft, PMSBY eligibility keyed 18–60 when it is 18–70, the Padma Awards
Committee keyed as headed by the President.

### 7. Orphaned-stimulus sweep
31 unanswerable questions were archived this session, found by accident rather
than by a detector. Migration 281's detector has only ever run on RBI 2022 —
never on NABARD, SEBI, IFSCA or PFRDA.

### 8. Smaller items
- 6 repairable data defects: two RBI rows with options shifted by a converter
  bug, SEBI 2025 Q6's corporate tax listed twice, the NCRPS ₹10,000 vs ₹1,00,000
  vintage conflict, RBI 2022 Q118 carrying the wrong shared block.
- Tag defects flagged but not fixed: 90 UPSC, 18 IFSCA, 5 PFRDA, 2 RBI.
- 154 coverage locks and 23 wrong primary tags, from the parallel RBI session.
- SSC CGL's 850 questions need their review pass before explanations can start.

---

## Gotchas this session added

- **`Get-Content -Raw` reads UTF-8 as cp1252.** Use
  `[System.IO.File]::ReadAllText(path, UTF8)`. Three separate mojibake scares
  were PowerShell display artefacts, not data corruption — always confirm
  encoding in SQL, never from console output.
- **A content PATCH demotes a verified row to `needs_correction`.** 101 SEBI
  rows were knocked out of verified by a repair that repaired nothing.
- **Refreshing `$env:CCP_ADMIN_JWT` does not update an already-built
  `$headers`.** Rebuild the hashtable. A run that stalls with no progress is
  usually a dead token, not a slow API.
- **`$env:PGURI` and the payload-builder functions are per-session.** Worth
  putting in `$PROFILE`.
- **Long POST runs stall.** Resume by fetching what exists and posting the
  difference; the unique constraint makes re-posting safe.
- **Question numbers restart per paper.** A year holds several papers — Prelims
  GS, CSAT and the Mains papers all share a year, so 72 numbers appear twice in
  2024 alone. Never match a question by number without its `pyq_paper_id`.
- **`correct_option_id` is not in the CMS field allowlist.** Key corrections
  need direct SQL, and must update `pyq_options.is_correct` and
  `mock_question_options.is_correct` in the same transaction or the mock bank
  keeps serving the old answer.
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
