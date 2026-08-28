---
name: pyq-prelims-frontload-notes
description: UPSC CSE Prelims PYQ bulk-import project state, reusable paper IDs, source-document verdicts, and blockers. Read before converting or importing any prelims year.
---

# UPSC CSE Prelims PYQ frontload — status & source verdicts

Companion to `docs/pyqfrontloadnotes.md` (Mains). Conversion tool:
`scripts/docx_to_pyq_json.py`. Import path: the PYQ v2 bulk importer
(`app/backend/app/exam_intelligence/pyq_bulk_import.py`), never per-question POSTs.

## Reusable IDs — prelims paper shells already exist, do NOT create new ones

A `pyq_papers` row is already present for every target year on `phase_slug='prelims'`,
each `trust_status='pending'` with **0 verified questions**. Import into these ids.

| Year | pyq_paper_id | trust_status | verified_q |
|---|---|---|---|
| 2024 | `4d0bed5e-3b8a-4143-92c3-614ede901af5` | pending | 0 |
| 2023 | `e7449c64-32e6-4b3d-9f6a-c335548f34b9` | pending | 0 |
| 2022 | `a9033c8e-60b6-4a28-8e01-7538cc24356a` | pending | 0 |
| 2021 | `6e0741aa-9a79-4c11-a0fc-4d8240ffda42` | pending | 0 |
| 2020 | `980cfb08-efbd-453f-8dbc-251fefb9d3f5` | pending | 0 |
| 2019 | `140b9023-b29d-4038-86b7-7ab88351cd54` | pending | 0 |
| 2018 | `df739acc-6616-4338-94ae-5a46181413a1` | pending | 0 |

Separate `prelims-csat-pyq-archive` shells exist for 2023, 2024 and 2026 (all pending, 0 q).

Already populated, leave alone:
- `22ea7f1b-d40b-46e2-b111-efdfc20e6f94` — year **2026**, `paper_code='A'`, verified, 97 questions.
- `505b29a0-0d4d-5230-88aa-3bbc525a6db5` — 2025 Prelims Paper-II CSAT **Set-B**, verified, 80 questions.
  This is the reference implementation for paper metadata; see
  `docs/audits/2026-07-14-upsc-cse-2025-csat-set-b-learner-access-validation.md`.

## Paper metadata conventions (copied from the validated CSAT Set-B paper)

- `paper_code` — e.g. `GS-PAPER-I`
- `metadata.set_code` = `"C"`, `metadata.paper_set` = `"SET-C"`
- Official per-paper PDF URL, not the `previous-question-papers` index page
- Answer-key provenance: `operator_typed_canonical_official_key`

## Source-document verdicts

The supplied `.docx` files are retyped/OCR-derived, not UPSC originals. All three
contain 100 questions numbered contiguously 1–100, but they use three different
internal formats and differ sharply in fidelity.

| Source | Format | Verdict |
|---|---|---|
| 2024 GS-I Set C | Word auto-numbered lists (`numPr`), 8 tables | **Convertible.** 100/100 parse clean. |
| 2022 GS-I Set A | `numPr` + tab indentation | **Convertible after a source fix.** 99/100; Q50 blocked. |
| 2023 GS-I Set A | No numbering at all (no `numbering.xml`) | **Unusable as supplied.** 54 questions broken. |

### 2023 — statement numbering is absent, not merely unstyled

The document carries no list numbering of any kind, so "Consider the following
statements" items appear as bare sentences. 54 questions have options that
reference numbers ("1 and 2 only") which exist nowhere in the stem. This is not
recoverable by parsing — the information is not in the file. A replacement 2023
source is required.

### 2022 Q50 — scrambled option markers

Printed as `(a)`, `(d).`, `(b)`, `(d)` — two options labelled `d`, none labelled `c`.
The converter repairs a damaged marker only when the letter it recovers is the one
due next, so this fails validation rather than being silently reordered. Reassigning
labels by position would be a guess about answer identity. Fix the source document,
then re-run.

## Answer keys

Operator-typed keys for all seven years (2018–2024) are committed under
`docs/reference/answer-keys/` as `question_number,correct_option_label` CSV, one row
per question, blank label for a dropped question. This is the provenance the validated
CSAT Set-B paper records as `operator_typed_canonical_official_key` — the official key
PDFs themselves are not machine-readable:

- 2024 GS-I: 1 page, single full-page image, OCR text layer corrupt (merged rows,
  `#N/A` columns). Its header is legible and authoritative:
  `CSP-2024 / Series C / 100 questions / 3 Dropped / 97 taken for Scoring`.
- 2022 GS-I: 4 pages, **zero** extractable words. Pure scan.

**Set identity is part of the key.** Each year's series (A/B/C/D) shuffles question
order, so a key is only valid for the series it was typed from. Keys on file:

| Year | Series | Keyed | Dropped |
|---|---|---|---|
| 2024 | C | 97 | 42, 47, 90 |
| 2023 | A | 99 | 54 |
| 2022 | A | 99 | 48 |
| 2021 | C | 99 | 30 |
| 2020 | C | 98 | 42, 77 |
| 2019 | B | 100 | — |
| 2018 | C | 100 | — |

A paper `.docx` must be the same series as its key, or the answers land on the wrong
questions with no error raised — the converter can only check that a label resolves to
one of the four options present, not that the question is the one the key meant.

**Open spot-check.** Machine-reading the 2024 scan recovered 53 of 100
number→letter pairs; 50 agree with the typed key and 3 disagree (Q9, Q58, Q59).
The scan's text layer is demonstrably unreliable and Q58/Q59 are adjacent — the
signature of a row slip — so these are most likely OCR artefacts rather than key
errors. Confirm those three against the official PDF by eye before the paper is
promoted to `verified`.

## Dropped questions

Nothing in the schema models a dropped question — `pyq_questions` has no status field
beyond `reviewer_status`. Convention adopted here: import all 100 so the paper is a
faithful record of the exam that was sat, mark them `dropped_by_upsc` in the row, and
assert no correct option. They can never satisfy the projection's
exactly-one-correct-option gate (`pyq_mock_projection.py::_check_question_eligibility`),
so they stay out of learner practice by construction.

Known dropped sets: **2024 Set C — 42, 47, 90** (confirmed by the official key header).

## Topic tagging — blocked on a missing tree

`all_topics.json` holds 474 topics across 4 subjects, all Mains GS I–IV. There is no
Prelims GS or CSAT topic tree. Tags are a second pass anyway (they key on
`question_id`, which only exists post-commit) via
`POST /admin/exam-intelligence-cms/bulk-import` with `entity='pyq-question-topic-tags'`
(max 2000 rows, `reviewer_status` forced to `pending`), but a prelims tree must be
ingested first — same pattern as `scripts/ingest_upsc_gs_syllabus.py`.

## Order of work per paper

1. Convert the `.docx`, resolve every validation error at source.
2. Confirm the paper's printed series matches the key in `docs/reference/answer-keys/`,
   then re-run with `--answer-key`.
3. Set paper provenance + set metadata on the existing shell paper id.
4. `bulk-import/preflight` → inspect → `bulk-import/commit`.
5. Read questions back by `source_question_ref`, build the tag batch, import tags.
6. Review lifecycle to `verified`; confirm all eight projection gates
   (`docs/runbooks/EI-DATA-01_upsc_2026_primary_topic_tags.md`).
