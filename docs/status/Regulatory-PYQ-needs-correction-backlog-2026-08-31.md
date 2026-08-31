# Regulatory PYQ — needs_correction backlog

**Status:** deferred, tracked. Nothing here blocks projection: a
`needs_correction` question fails the projection's `question_not_verified` gate,
so none of these can reach `mock_question_bank` until deliberately repaired.

**Scope:** the SEBI / PFRDA / IFSCA corpus, 1,085 questions across 103 verified
papers, reviewed question-by-question under EI-DATA-03.

| | count |
|---|---|
| verified | 886 |
| **needs_correction** | **121** |
| rejected | 60 |
| pending (descriptive, correctly typed out of scope) | 18 |

---

## The 121, by cause

Two populations, and they want different work.

### A. Wrong or doubtful answer keys — ~45

These need a human with the source paper. No amount of pipeline work fixes them.

The corpus is `source_type = 'memory_based'`: the regulators publish neither
papers nor keys, and the content is coaching-institute compilations of aspirant
recall. The provenance note on every paper already says keys may differ from the
actual paper — these are that warning made concrete.

Key accuracy varies sharply and predictably by content type:

| subject | wrong keys | of |
|---|---|---|
| pension-sector + insurance | **0** | 39 |
| english-language (self-contained questions) | **0** | 40 |
| quantitative-aptitude | 1 | 85 |
| costing | 1 | 100 |
| economics | 5 | 88 |

Hard-edged statutory and scheme parameters survive recall intact. Interpretive
content does not. In Reasoning the wrong keys cluster *inside* sets whose other
questions are right — the aspirant rebuilt the puzzle correctly and misreported
one derived answer.

**Three papers should be pulled rather than repaired:**

- `SEBI-GA-2020-P1-ECO` — all five questions fail. Three are General Awareness;
  two have wrong keys (statistics of population keyed as Ecology not Demography;
  FDI keyed as equity investment, though the *same question* in that year's
  Finance paper keys it correctly).
- `PFRDA-GA-2025-P1P2-FIN` — 4 of 9 keys wrong; the answer column appears
  shifted. All nine need re-checking against source.
- `IFSCA-GA-2024-P1P2-MGMT` — the entire section is General Awareness, not
  Management. Needs re-sectioning, not key repair.

### B. Conversion damage — ~76

These are pipeline defects. Two sub-causes.

**B1. Page-header and section-title bleed into option text — ~35.**
The same trailing-note branch in `scripts/docx_to_pyq_json.py` that PR #1051
fixed for directions blocks also appends page furniture to the last option:
`Reasoning Ability`, `9 IFSCA Grade A 2023 Phase 1 Paper 1 Recollected
Questions`, `INSURANCE & PENSION`. In several cases the header lands on the
**correct** option, so a learner sees it attached to the right answer.

Harder than directions blocks: a directions line announces itself, a page header
is ordinary text that happens to be furniture. The tractable signal is
repetition — a string recurring at regular intervals across the document is a
running header; a one-off is not. Own PR.

**B2. Mathematical Unicode — 6, one file.**
`IFSCA_Phase-1_paper-1.docx`. `√960.89` stores as
`960.89−−−−−−√𝟗𝟗𝟗𝟗𝟗𝟗.𝟖𝟖𝟖𝟖`.

**Confirmed NOT a converter defect.** Verified with python-docx: the source
`.docx` contains zero `oMath` elements. The PDF→DOCX step wrote each number
twice — once readable, once in mathematical-bold codepoints (U+1D7D8+) — with
the radical's overline as a dash run. **Source repair, six paragraphs. Do not
change the converter for it.** All six keys are correct; only the stems are
unreadable.

---

## Still in the wrong shape (does not block projection)

**Three QA data-interpretation sets — 16 questions.** Their shared data block
still sits inside a neighbouring question's option `e`, so there is nothing in a
stem for EI-DATA-08 to lift:

| set | carrier | governed |
|---|---|---|
| 2024 Q11–15, three-friends caselet | `f063b6d3` option e | 5 |
| 2024 Q21–25, spoons table | `461dad49` option e | 5 |
| 2025 Q20–25, power-bank table | `38af2d28` option e | 6 |

The data survives in all three and every key in them checks out, so they become
verifiable the moment the blocks are moved. Two routes: a targeted re-import of
those two papers through the fixed converter, or a hand migration modelled on
EI-DATA-08 reading from the option rather than the stem.

**Note the tabular convention** when repairing: both table sets use "average" to
mean the average of the two product types, so totals are double the tabled
figure. Confirmed independently by three questions in each set.

---

## Unrecoverable — the 60 rejected

Not backlog. Recorded so nobody re-derives them.

**32 lost to the shared-stimulus defect** — the block is absent from the corpus
entirely, not merely displaced: Reasoning 2023 Q1–5, 2024 Q1–5, 2025 Q1 and
Q3–7, PFRDA Q1–5; QA 2023 Q16–20 (pie chart) and PFRDA Q6–10 (fruit prices);
English PFRDA 2025 Q1–6 (digital-detox passage).

**11 perishable-and-distorted** in financial-awareness, per the standing rule:
perishable + sound → verify, perishable + distorted → reject.

**10 General Awareness questions mis-filed into subject papers.**

**7 individually broken** — including `fcb502b9`, whose stem was reduced to the
single word "Statements:" with the statements themselves in options a and b and
the real answer choices buried inside option b.

**Also absent from the corpus, never captured:** Reasoning 2024 Q24, 2025 Q2,
PFRDA Q6. Sourcing backlog, not defect list.

---

## Priority

1. **B1, the header-bleed converter fix.** ~35 questions, one PR, same file and
   same branch as #1051. Highest return per unit of work.
2. **The three QA DI sets.** 16 questions, all keys already checked.
3. **B2, the source repair.** 6 questions, six paragraphs, one file.
4. **A, the key repairs.** ~45 questions, needs a human with source papers.
   Pull the three broken papers first rather than repairing them item by item.

---

## Related

- PR #1051 — converter emits shared directions blocks as stimuli
- EI-DATA-03 — question review standard (Track A conceptual / Track B numerical)
- EI-DATA-04 / EI-DATA-05 — hand stem repairs, since superseded by EI-DATA-08
- EI-DATA-08 — lifted 51 hand-repaired stems into 12 proper `pyq_stimuli` rows
