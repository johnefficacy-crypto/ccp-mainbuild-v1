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

The supplied `.docx` files are retyped/OCR-derived, not UPSC originals. All seven
contain 100 questions numbered contiguously 1-100, but **no two years share a
layout** — question markers, option markers and list numbering all differ.
`scripts/docx_to_pyq_json.py` normalises this rather than special-casing per year:
it flattens paragraphs to lines, detects the question-marker style per document,
and restores Word's auto-list numbering.

| Year | Set | Marker | Options as | Verdict |
|---|---|---|---|---|
| 2024 | C | `1.` | `(a)` paragraphs | **Converts** 100/100 |
| 2023 | A | `1.` | `(a)` paragraphs | **Converts** 100/100 (7 statement runs renumbered) |
| 2022 | A | `1.` | `(a)` paragraphs | Blocked: Q50 |
| 2021 | C | `Q.1)` | `a)` paragraphs | Blocked: Q86 |
| 2020 | C | `Question 1.` / `Question 5:` / `Question: 6.` | packed `(a)` lines | Blocked: Q40 |
| 2019 | B | `1.` | lower-letter auto-list | **Converts** 100/100 |
| 2018 | C | `Q.1)` | packed `(a)` lines | **Converts** 100/100 (Q37 corrected; see key conflict) |

### Operator corrections

`docs/reference/corrections/*.json`, applied with `--corrections`, repair how
options were **formatted** — their labels, or a run printed as a list instead of
as options. A correction never states which option is correct: that stays with
the answer key, and a correction that displaced the keyed option would surface as
an unresolved key at build time. Two positional operations:

- `relabel` — assign these labels to the parsed options in printed order.
- `options_from_stem` — take the last N numbered lines off the stem and make them
  options a-d.
- `add_options` — supply the text of an option the source dropped entirely. The
  only operation that introduces text rather than rearranging what was parsed, so
  it is the narrowest: the label must be absent and the result must be a complete
  a-d set.

Applied so far:

- **2022 Q50** — printed `(a)`, `(d).`, `(b)`, `(d)`. Printed order is farming /
  wind energy / GM gardens / mini forests, whose true labels are `a / d / b / c`.
  The key says (c) is "Creation of mini forests in urban areas", the fourth
  printed item, which the relabelling puts at c.
- **2021 Q86** — the four options were formatted as a decimal auto-list, so they
  parsed as numbered statements. Promoted to a-d in printed order. The key says
  (a) is "environmentally responsible practices in electronics recycling
  industry", which is printed item 1.
- **2018 Q37** — option (d) was absent from the file. Its text is forced by the
  other three: `(a) 1 and 2 only`, `(b) 3 only`, `(c) 1 and 3 only` leave
  "1, 2 and 3" as the only remaining combination.

### ⚠ Unresolved answer conflict — 2018 Q37

The operator key on file gives Q37 = **(c) "1 and 3 only"**. The source that
supplied the missing option (d) states the correct answer is **(d) "1, 2 and 3"**
— i.e. that statement 2 is also correct. Both cannot hold.

**The key has not been changed.** The envelope carries (c), so the paper imports
at `reviewer_status='pending'` with the key as it stands, and nothing reaches a
learner until review. Resolve against the official UPSC 2018 Set-C answer key
before this question is promoted to `verified`: the mock projection gates on
exactly one correct option, so a wrong key here ships a wrong answer silently.

### Remaining blockers

Each needs a correction in the `.docx` itself; neither is repairable positionally,
and neither is a parser limitation.

- **2020 Q40** — the fourth option is labelled `(a)`, which a `relabel` correction
  would fix. But the damage is not only the label: all four statements are merged
  into a single stem line **and the text is itself corrupted** — "'Certificate of
  Deposit is a long-term of India to a corporation" has words dropped mid-clause.
  Relabelling alone would produce a well-formed question whose statements are
  unreadable, so the stem needs **retyping from the official Set-C paper**. Two
  attempts to supply a replacement have not carried that text: the first offered a
  different question (the Alma-Ata / Hague / Talanoa / Under2 pairs item, whose
  option texts coincide because both are four-statement questions), the second
  restated the option labelling and confirmed the key as (c) — which the key on
  file already gives — without the statements themselves. The key is not the
  blocker here; the four statement texts are.

### What the converter repairs, and what it refuses to

Repaired, because the correction is forced and loses no information:

- damaged option markers (`{b)`, `c)`, `(C)`, `(b).`) — only when the recovered
  letter is the one due next;
- two options glued onto one line (`(c) 3 only d)1 and 3`) — only where the
  embedded marker is preceded by space and followed immediately by non-space,
  the exact shape a normally spaced `(d)` inside option text never takes;
- a complete but shuffled option set (`a, c, b, d`) — reordered by label, since
  every label is present exactly once and each keeps its own text.

Refused, because the correction would be a guess about which option is the answer:

- a scrambled marker whose letter is not the one due (2022 Q50);
- a missing or duplicated label (2018 Q37, 2020 Q40, 2021 Q86).

### Statement numbering

Word keeps auto-list markers out of the text layer while the options refer to them
("1 and 2 only"), so decimal lists are restored as `1.`/`2.` from their numbering
instance. Some sources carry no list numbering at all. There the distinction that
matters is what the options do with it:

- options that **tally** statements ("Only two", "All four") take the count over
  the statements as printed, so their numbering is cosmetic and its absence is not
  an error;
- options that **name** statements by index ("1 only", "Both 1 and 2") make the
  numbering load-bearing, and the question is unanswerable without it.

`--number-unmarked-statements` restores the latter by printed order, and reports
which questions it changed. It is opt-in and runs only on an unambiguous shape — a
lead-in, a run of two or more lines, then the closing interrogative, with nothing
already numbered. It infers print order only, never answer identity, but a stem
line misread as a statement would shift every number after it, so the reported
questions are owed an eye-check before the paper is promoted to `verified`.

Applied so far: 2023 Q53/58/65/71/72/79/100, 2022 Q25, 2019 Q43, 2018 Q77.

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

`workbench/catalogs/all_topics.json` holds 474 topics across 4 subjects, all Mains GS I–IV. There is no
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
