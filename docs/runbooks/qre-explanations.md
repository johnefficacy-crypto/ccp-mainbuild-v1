# QRE PYQ explanations — scope, draft, gate, write, review

Quantitative aptitude, general intelligence & reasoning and English language
PYQ explanations, run through the existing explanation lane
(`workbench/reports/EXPL-LANE-STATUS.md`) with one addition: a deterministic
**answer-key gate** between the draft and the write.

Tool: `scripts/pyq_explanation_gate.py` (offline; no network, no model call).
Tests: `app/backend/tests/scripts/test_pyq_explanation_gate.py`.

First target: **SSC CGL 2024 Tier I**, exam
`3742f421-eae0-4a02-8fd1-ac3aa0589c9f`. Expected scope is **845 verified,
projected, QRE-only questions across 13 papers**.

---

## What already exists, and what this adds

| Step | Before | Now |
|---|---|---|
| Export | ad-hoc psql, not committed; no stimulus join | `pyq_question_review.py export` + `pyq_explanation_gate.py input`, which carries `stimulus_text` |
| Draft | a Claude session writes `<EXAM>-EXPLANATIONS-DRAFT.json` | unchanged |
| Key check | the drafter's self-reported `key_verdict` | **`gate`**: deterministic comparison against the keyed option |
| Write | operator script (not committed) folds rows and posts them | `gate` writes the folded CMS body for passing rows only |
| Review | `POST .../pyq-question-explanations/{id}/review` | unchanged |

Nothing about storage, the review lifecycle, or the learner read path changes.
Every row is still born `pending` (`_IMPORT_CONFIG["pyq-question-explanations"]`
forces it), and only `verified` rows reach an aspirant
(`app/backend/app/study_os/pyq_explanations.py`, `_verified_rows`).

---

## 1. Export (read-only, operator)

```bash
export CCP_API_BASE=https://<host>
export CCP_ADMIN_JWT=<admin JWT>

python scripts/pyq_question_review.py export \
    --exam-id 3742f421-eae0-4a02-8fd1-ac3aa0589c9f \
    --exam-phase-id <tier-1-phase-id> \
    --status all \
    --out review_out_ssc --apply
```

Two id lists come from SQL (read-only, operator, psql):

```sql
-- projected_ids.txt: questions with a projected mock twin
select distinct mqb.pyq_question_id
from public.mock_question_bank mqb
join public.pyq_questions q on q.id = mqb.pyq_question_id
join public.pyq_papers p on p.id = q.pyq_paper_id
where p.exam_id = '3742f421-eae0-4a02-8fd1-ac3aa0589c9f';

-- existing_ids.txt: questions that already carry an explanation of any status
select distinct e.question_id
from public.pyq_question_explanations e
join public.pyq_questions q on q.id = e.question_id
join public.pyq_papers p on p.id = q.pyq_paper_id
where p.exam_id = '3742f421-eae0-4a02-8fd1-ac3aa0589c9f';
```

## 2. Scope the input — one exam, one question set

```bash
python scripts/pyq_explanation_gate.py input \
    --export-dir review_out_ssc \
    --exam-id 3742f421-eae0-4a02-8fd1-ac3aa0589c9f \
    --section-aliases workbench/audit/ssc_cgl/ssc_section_aliases.json \
    --projected-ids projected_ids.txt \
    --exclude-ids existing_ids.txt \
    --expect 845 \
    --out workbench/sources/ssc-cgl-2024-t1-explanations-input.json --apply
```

- The question set defaults to the three QRE subjects. Narrow it with
  `--subject-slug` (repeatable), or with `--paper-id` (repeatable) for one paper.
- The tool refuses an export that holds a paper from another exam.
- It keeps a question only if the question is `verified`, is an MCQ, has at
  least two verified options and has a key. Every exclusion is counted by
  reason. `--expect` fails the run if the total is not 845. If the count is
  off, read the exclusion counts before anything else.
- Without `--projected-ids` or `--exclude-ids`, the run says that check was
  not made. It does not quietly pass.
- `stimulus_text` carries the shared passage, DI table or puzzle for set
  members (the missing join listed in the lane status, open item 5).

Commit the input file and merge it before drafting, as the lane already does.

## 3. Draft

A drafting session reads the input and writes
`workbench/worksheets/SSC-CGL-EXPLANATIONS-DRAFT.json` and
`SSC-CGL-EXPLANATIONS-NOTES.md`, using the field set and standing rules of the
earlier batches (see `RBI-EXPLANATIONS-NOTES.md`). The rules that matter here:

- keys are accepted wherever they are defensible;
- puzzles are worked from a single arrangement;
- plain language throughout;
- one rationale per distractor;
- `final_answer_option_id` is set on AGREE rows.

It must also read `stimulus_text`.

This step spends model credits. It is a separate, explicitly authorised run.

## 4. Gate

```bash
python scripts/pyq_explanation_gate.py gate \
    --input workbench/sources/ssc-cgl-2024-t1-explanations-input.json \
    --draft workbench/worksheets/SSC-CGL-EXPLANATIONS-DRAFT.json \
    --out-dir workbench/audit/ssc_cgl/explanations --apply
```

Writes three files:

- `cms_body.json`: passing rows, folded for the bulk-import route
  (`option_rationales` → `{option_id: text}`, `formula_used` → array,
  `final_answer_option_id` = the keyed option, `ambiguity_status='none'`).
- `quarantine.csv`: every row that failed, in the review-worksheet shape
  (`scripts/pyq_question_review.py` `WORKSHEET_FIELDS`), with
  `row_type=explanation`, the flags, a note naming the keyed and the drafted
  option, and **`decision` blank**.
- `gate_summary.json`: counts, flags, refused signatures, and the question
  ids the draft left out.

### What a row is checked for

| Flag | Kind | Meaning |
|---|---|---|
| `unknown_question` | hard | the draft row is not in the scoped input |
| `key_missing` | hard | no keyed option among the verified options |
| `key_inconsistent` | hard | `correct_option_id` disagrees with `options[].correct` |
| `final_answer_missing` | hard | the draft asserts no final answer |
| `final_answer_mismatch` | hard | the draft's final answer is not the keyed option |
| `key_disputed` | hard | the drafter's `key_verdict` is not AGREE |
| `rationale_foreign_option` | hard | a rationale is keyed to an option that is not on this question |
| `rationale_missing_option` | soft | a distractor has no rationale |
| `text_names_other_option` | soft | a sentence says "the answer is option (x)" or "option x is correct", where x is not the key |
| `duplicate_draft_row` | soft, never releasable | the same question appears twice in the draft |

**What a pass means:** the explanation agrees with the key, and the key is
consistent. It does not mean the explanation is right. A passing row is still
`pending` and is still reviewed.

Calibration: run against the committed RBI batches
(`rbi-explanations-input*.json` with `RBI-EXPLANATIONS-DRAFT*.json`), the gate
passes 519 of 531 and 354 of 364 rows. Every row it quarantines is one the
drafter had already marked DISPUTED, AMBIGUOUS or UNANSWERABLE.

## 5. The quarantine, and how an operator signs it

A quarantined row is written nowhere. It does not exist in
`pyq_question_explanations`, so no learner can see it and no reviewer can verify
it by accident. It stays out until someone decides what to do with it.

For each row, fill `decision` in `quarantine.csv`. Use the same vocabulary as
every other review worksheet, and write the reason in `notes`:

| decision | Use when | What happens |
|---|---|---|
| `verified` | the flag is soft and, having read the row, you find the explanation supports the keyed option | released into `cms_body.json` on the next gate run; `metadata.explanation_gate` records the flags and your note |
| `rejected` | the explanation is wrong | stays out; redraft it in the next batch |
| `needs_correction` | the **key** is wrong, or the stored question is broken (missing premise, shifted options) | stays out; send it to key/data repair, following the UPSC key-repair shape: resolve by option id, then update `pyq_questions.correct_option_id`, `pyq_options.is_correct` and `mock_question_options.is_correct` in one transaction |

Signing a hard-flagged row `verified` is **refused**, and the gate reports it
under `refused_signatures`. The explanation and the key disagree, and a
signature cannot settle which of them is wrong. The fix is a key repair or a
redraft, then a fresh export and a fresh gate run. Once the key is fixed, a
redrafted row passes without a signature.

Apply the signatures:

```bash
python scripts/pyq_explanation_gate.py gate \
    --input ... --draft ... \
    --signed workbench/audit/ssc_cgl/explanations/quarantine.csv \
    --out-dir workbench/audit/ssc_cgl/explanations --apply
```

The gate re-checks every row on each run. A signature applies to the flags
that are current at that run, so if a key or a draft changed after signing,
the row is judged again from scratch. Commit the signed CSV: it is the audit
trail, because the bulk-import audit row carries only the reason.

## 6. Write (operator; the only step that touches the database)

```bash
curl -sS -X POST "$CCP_API_BASE/api/admin/exam-intelligence-cms/bulk-import" \
  -H "Authorization: Bearer $CCP_ADMIN_JWT" -H "Content-Type: application/json" \
  --data-binary @workbench/audit/ssc_cgl/explanations/cms_body.json
```

Rows land `pending`, and the per-row result lists any failures. The route
re-checks option scope and the `(question_id, explanation_source_type)`
uniqueness. The cap is 2,000 rows.

## 7. Review

Use `POST /api/admin/exam-intelligence-cms/pyq-question-explanations/{id}/review`
with the flat body `{status, reason}`. As in the lane:

- bulk-verify `draft_confidence=high`;
- read the `medium` and `low` rows before verifying them.

The RPC refuses `verified` without a final answer, `ambiguity_status='none'`
and a cleared licence. It does not re-compare against the key, which is why
the gate runs before the write.

Do not record this in the operator-validation registry as passed until the
write and the review have run live.
