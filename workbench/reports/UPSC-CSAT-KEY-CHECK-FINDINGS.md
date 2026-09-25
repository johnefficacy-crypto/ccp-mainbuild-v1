# UPSC Prelims Paper II (CSAT) 2023–2026: stored keys vs UPSC's key vs an independent solve (UPSC-CSAT-KEY-CHECK-01)

**Worksheet:** `workbench/worksheets/UPSC-CSAT-KEY-CHECK.csv` has 315 rows, one per keyed question in the four live CSAT papers.

**Builder:** `workbench/scripts/upsc_csat_key_check_01.py` (stdlib only, no database access). It regenerates the worksheet
and prints every count in this report.

**Inputs:**
- the operator export `workbench/sources/upsc-csat-key-check-input.json`
- UPSC's keys, transcribed in `workbench/sources/upsc-official-keys/csp_2023_2026_gs2_key_transcription.py`
- the key-blind solve in `workbench/sources/upsc-csat-independent-solve.json`

No database write was made. The GS papers, explanation drafts and earlier key worksheets are untouched. The keys of paper
`7b18bf8d` were not checked.

## 1. Summary

**Does CSAT have the same defect as GS?** The evidence says no.
- The stored CSAT keys agree with UPSC's key on 306 of 315 rows.
- 6 need correcting on final keys, and 3 more are proposed from the 2026 provisional key.
- That is 1–3 per paper. The GS papers had 16–19.

**CSAT has a different defect that is much larger:**
- **106 of 315 questions (34%) reach this export without the reading passage they ask about.** They arrive in runs,
  one passage feeding 2–5 consecutive questions. This is the orphaned-stimulus shape.
- **11 more stems lost their superscripts or symbols on import.** For example, 2²⁵ was flattened to "225".

| Paper | Rows | MATCH | CORRECTION | PROPOSED | UNAVAILABLE | UNMAPPABLE | UNVERIFIABLE |
|---|---|---|---|---|---|---|---|
| 2023 `586d515e` | 80 | 77 | 3 | 0 | 0 | 0 | 0 |
| 2024 `9e191ae4` | 75 | 72 | 3 | 0 | 0 | 0 | 0 |
| 2025 `505b29a0` | 80 | 80 | 0 | 0 | 0 | 0 | 0 |
| 2026 `b06305ad` | 80 | 77 | 0 | 3 | 0 | 0 | 0 |
| **Total** | **315** | **306** | **6** | **3** | **0** | **0** | **0** |

- **UNAVAILABLE is zero:** UPSC publishes a key for every year.
- **UNVERIFIABLE is zero:** every row has at least UPSC's key.
- **UNMAPPABLE is zero:** every corpus question number exists in its identified series. 2024 simply lacks five numbers
  (§2).

## 2. Key availability and series identification

| Year | UPSC document | Status | URL |
|---|---|---|---|
| 2023 | CS-P-2023, Paper 2, GS-II, Series A–D, 0 dropped | **Final** (file dated 09-05-2024, after the cycle) | https://www.upsc.gov.in/sites/default/files/AnsKey-CSP-2023-Paper-II-090524.pdf |
| 2024 | CS(P)-2024, Paper II, GS-Paper-II, Series A–D, 0 dropped | **Final** (file dated 21-05-2025) | https://www.upsc.gov.in/sites/default/files/AnsKey-CivilServicesPExam-2024-GeneralStudies-II-210525.pdf |
| 2025 | CS(P)-2025, Paper TWO, GS-II, Series A–D, 0 dropped | **Final** (file dated 13-05-2026) | https://www.upsc.gov.in/sites/default/files/AnsKeyCivilServicesP-Exam-2025-GeneralStudies-II-130526.pdf |
| 2026 | "CS (P)Exam 2026 [Prov. Ans. Key]", Paper II, Series A–D, 0 dropped | **Provisional** (file dated 27-05-2026). The final key is not yet published. | https://www.upsc.gov.in/sites/default/files/ProvAnsKey%E2%80%93GS-II-CSP-Exam-2026-270526.pdf |

upsc.gov.in could be reached from this environment. All four PDFs are image scans, transcribed by eye.

**Transcription check:** each year's Series B, C and D keys are Series A's 10-question blocks in a different order. Every one
of the 96 ten-question blocks in B, C and D (8 per series per year) equals a Series A block exactly. A single misread
letter would break that equality, so the four independent readings of each year corroborate each other.

**Series identification:** no series drops anything in any year, and the corpus has **no unkeyed rows**, so there were no
dropped items to match on. The identification rests on agreement rate alone.

| Year | Series A | B | C | D | Corpus follows |
|---|---|---|---|---|---|
| 2023 | 15 | **77** | 19 | 17 | Series B (77/80) |
| 2024 | **72** | 22 | 15 | 18 | Series A (72/75) |
| 2025 | 24 | **80** | 18 | 18 | Series B (80/80) |
| 2026 | 20 | 13 | 20 | **77** | Series D (77/80, provisional) |

**Confidence: high.** The winning series agrees on 96–100% of rows and the runner-up on at most 30%. On top of that, the
independent solve agrees with the chosen series' letter on 200 of 201 uniquely solved rows (§4).

The 2024 corpus lacks question numbers 49 and 55–58. UPSC dropped nothing in 2024, so these are **not** dropped items.
They are five questions missing from the corpus paper, probably a data-interpretation set given the 55–58 run. That is
inferred; the export cannot show what they were.

## 3. Corrections and proposals

Every CORRECTION carries an option id (`new_correct_option_id`). Each disputed letter was re-read on the scan and sits
inside a block-verified series.

| Year | Q | Stored | UPSC | Independent solve | Verdict / confidence | Working |
|---|---|---|---|---|---|---|
| 2023 | 57 | (c) 8 | (d) 9 | (d) 9 | CORRECTION / high | Floor 400×220 cm, tile 140×60 cm, any axis-parallel orientation. An exhaustive packing search on a 20 cm grid (20×11 cells, tiles 7×3 or 3×7) finds a maximum of 9. It was run twice: once in the solve pass and once independently here. One 9-tile layout, as (x,y,w,h) in 20 cm cells: (0,0,7,3) (7,0,7,3) (14,0,3,7) (17,0,3,7) (0,3,7,3) (7,3,3,7) (10,3,3,7) (0,6,7,3) (13,7,7,3). The obvious two-block layout gives only 8, which is the stored answer. |
| 2023 | 79 | (b) Thursday | (a) Wednesday | Thursday, with two readings | CORRECTION / medium | The stem reads "1010th day"; the exponent was lost, and it means 10¹⁰. 10¹⁰ mod 7 = 4. Counting 10¹⁰ days after Sunday gives Thursday. Counting today as day 1 (10¹⁰ − 1 days later) gives Wednesday. UPSC's key takes the inclusive reading. **UPSC and the solve's first reading disagree.** The solve had flagged Wednesday as the alternative, so UPSC governs. |
| 2023 | 52 | (a) | (d) | not solvable: passage absent | CORRECTION / medium | Final key, 77/80 series agreement. The target rests on UPSC's letter mapping to the corpus label (see §4 for why that is safe). |
| 2024 | 2 | (a) | (c) | not solvable: passage absent | CORRECTION / medium | As above. |
| 2024 | 52 | (a) | (c) | not solvable: passage absent | CORRECTION / medium | As above. |
| 2024 | 71 | (a) | (d) | not solvable: passage absent | CORRECTION / medium | As above. The solver pass omitted this row; it was added at reconciliation as passage-dependent. |

**PROPOSED — needs a human decision (2026, provisional key only, `applies = no`)**

| Q | Stored | UPSC provisional | Solve | Proposed option id |
|---|---|---|---|---|
| 44 | (c) | (b) "2 and 3" | passage absent | `2cbb1fc4-97f2-4072-b65e-ed20f0927c67` |
| 66 | (d) | (a) "1 and 2 only" | passage absent | `a9b6a854-df36-44aa-ae64-f836e7f97e14` |
| 76 | (a) | (d) "Neither 1 nor 2" | passage absent | `f8e1e190-dcc7-424f-bc31-756f6e6d9565` |

All three are reading questions with no passage in the export, so the solve cannot arbitrate. UPSC's final 2026 key will
settle them. The proposed ids are in the `note` column, not in `new_correct_option_id`.

## 4. Where UPSC and the independent solve disagree

The solve was done without the stored key or UPSC's key. The solvers received only the question text and option texts.
Of 209 rows the solve could answer, 201 have a single answer, and **200 of those 201 name the same option text that UPSC's
letter points to in the corpus.**

The only exception, and the rows with more than one defensible reading, are these:

| Year | Q | Stored | UPSC | Solve | What happened |
|---|---|---|---|---|---|
| 2024 | 54 | (c) 10 | (c) 10 | (a) 3 | **Corrupt stem, not a key error.** The stem reads "325 + 227 is divisible by". Literally, 552 = 2³·3·23, which is divisible by 3 only. The exponents were clearly lost, but 3²⁵ + 2²⁷ has residues 2, 4, 1 and 8 mod 3, 7, 10 and 11, so no option divides it either. The real stem cannot be recovered from the export. UPSC and the stored key agree on (c). The row is MATCH with low confidence and needs its stem restored from the booklet. |
| 2023 | 79 | (b) | (a) | (b), two readings | See §3. UPSC takes the inclusive-count reading. |
| 2025 | 7 | (b) 13 | (b) 13 | (c) 14, two readings | Meetings every 7.5 min. "Between 5:20 and 7:00" is 14 if 7:00 counts and 13 if it does not. UPSC and the stored key take the exclusive reading. |
| 2025 | 60 | (d) | (d) | (c), low confidence | Together, the statements make Q a sibling of P's father, but Q's gender is unknown (uncle or aunt). UPSC and the stored key say it cannot be determined. The solve had flagged (d) as the alternative. |
| 2023 | 44 | = UPSC | = UPSC | two readings | "2192" is 2¹⁹². The exponent reading agrees with UPSC. |
| 2024 | 69 | = UPSC | = UPSC | two readings | Whole-rupee versus fractional prices. |
| 2025 | 36, 79 | = UPSC | = UPSC | two readings / left open | Q36: whether the primes must be distinct. Q79: the truth-telling rule is not stated. |
| 2026 | 75 | = UPSC | = UPSC | two readings | Whether placements may overlap along an edge. |

**The 2020-Q75 option-order signature does not appear.** No row has a unique-answer solve that points at a different option
text from UPSC's letter. The one mismatch, 2024 Q54, is explained by the corrupt stem.

**This is the substitute for the missing booklet check.** On the 200 rows that were solved uniquely, the corpus's
label-to-text mapping must match UPSC's booklet, because UPSC's letter lands on the text the solve derived. That is evidence
of correct option order for about two-thirds of the corpus, spread across all four papers. The other 115 rows (106 passage
questions plus 9 with no unique solve) are covered only by letter agreement.

## 5. Incomplete and corrupt stems

**Missing passages: 106 of 315 questions.** The solve pass flagged each one as depending on a passage absent from
`question_text`.

| Year | Questions | Runs (each run = one missing passage shared by consecutive questions) |
|---|---|---|
| 2023 | 27 | 1–5, 11–13, 21–23, 31–33, 41–43, 51–54, 61–63, 71–73 |
| 2024 | 27 | 1–4, 11–14, 21–23, 31–34, 41–44, 51–53, 61–63, 71–72 |
| 2025 | 29 | 1–4, 11–14, 21–24, 31–34, 41–42, 51–53, 61–64, 71–74 |
| 2026 | 23 | 6–8, 11–12, 19–20, 26–27, 32–35, 41–44, 66–67, 71–72, 76–77 |

**This is the orphaned-stimulus shape.** A run is 2–5 consecutive questions that each assume a passage "above" them, where
the passage belongs to the run and none of its questions carries it. A run can hold more than one passage: UPSC usually
prints one passage per 1–2 questions.

**What migration 228 shows for 2025:**
- It stores 14 passages as `pyq_stimuli` rows and links them to 25 of the 29 passage questions through
  `pyq_question_stimuli`. For those 25, the passage exists; the export simply does not include stimuli.
- **Q3, Q4, Q11 and Q12 have no stimulus link in the migration.** Two passages appear never to have been imported, so
  these four are truly orphaned.
- The migration is the original load. Later edits cannot be seen from the repository.

For 2023, 2024 and 2026 the import is not in the repository. Whether their 81 passage questions have stimulus links cannot
be determined from here. One query settles it:

```sql
select p.year, count(*) filter (where qs.question_id is null) as unlinked, count(*) as passage_questions
from pyq_questions q join pyq_papers p on p.id = q.pyq_paper_id
left join pyq_question_stimuli qs on qs.question_id = q.id
where q.pyq_paper_id in ('586d515e-2d3d-485d-a944-3983e4569e53','9e191ae4-68b9-47bf-9121-6d9d468a7bc5',
                         '505b29a0-0d4d-5230-88aa-3bbc525a6db5','b06305ad-cc93-4c27-b309-1b590f0a3247')
  and q.question_text ~* '(above passage|the passage|the author)'
group by p.year;
```

This query catches only stems that say "passage". Some 2026 passage questions do not; the solve flagged them by reading.

**One visible consequence:** without their passages, some questions in the same paper have identical stems and are
distinguishable only by their options:
- 2023: Q2, Q23, Q63
- 2024: Q13/Q44 and Q61/Q63
- 2025: Q1, Q61, Q71; Q3/Q42; Q31, Q51, Q63

**Other stem damage: 11 questions with symbols or superscripts lost on import.** Q2 and Q17 of 2026 and Q60 and Q79 of 2025
were flagged as ambiguous but are not damage.

| Year | Q | Defect | Effect |
|---|---|---|---|
| 2023 | 14 | Operator shown as private-use glyph U+F0C5 | Solvable; the rule fits all three examples |
| 2023 | 25 | Expression "(p+c)(p−c)" lost its formatting | Solvable either way |
| 2023 | 38 | Exponent printed inline | Solvable |
| 2023 | 44 | 2¹⁹² printed "2192" | Answer depends on the reading |
| 2023 | 79 | 10¹⁰ printed "1010" | Answer depends on the reading; CORRECTION row |
| 2024 | 9 | 1²×2⁴×…×25⁵⁰ printed "12 × 24 × … × 2550" | Solvable on the exponent reading |
| 2024 | 17 | 30³⁰ printed "3030" | Solvable on the exponent reading |
| 2024 | 39 | (p−r)² printed "(p−r)2" | Answer depends on the reading |
| 2024 | 54 | "325 + 227" | **Unrecoverable.** No reading matches UPSC's (c). |
| 2026 | 22 | 6¹²⁹×7³⁰⁷ printed "6129 × 7307" | Solvable on the exponent reading |
| 2026 | 79 | Exponents flattened ("10m", "7525", "2532", "3275") | Solvable on the exponent reading |

Cosmetic only: 2023 Q19 and Q77 options prefixed with ": ", 2024 Q76 "≯/≮" symbols dropped, 2026 Q48 "×" shown as
U+FFFD, and 2026 Q78 blanks shown as "×".

**Directions block spread across the option slots (the 7b18bf8d Q55 shape): 0 in the four live papers.** Both the solve
pass and a scan of option texts (long options, "directions"/"read the following" in options) found none.

## 6. Duplicate options and overlap

- **Duplicate option text:** 0 of 315, compared with whitespace and case normalised and symbols kept.
  - A first pass that stripped symbols flagged 7 false positives ("15" vs "–15", "R < S" vs "R > S", 10⁴ vs 10⁸).
    Those are distinct options.
- **Shared questions among the four live papers** (identical stem and identical option set): 0 for every pair.
- **Overlap with the stray import `7b18bf8d`:** not checkable. The paper is not in the export.
  - `workbench/reports/EXPL-LANE-STATUS.md` states that it duplicates 56 of the 80 questions in `b06305ad` and has 14 of
    its own. That figure was not re-derived here.

## 7. Inventory

| pyq_paper_id | Year | Questions | State | Checked here |
|---|---|---|---|---|
| `586d515e-2d3d-485d-a944-3983e4569e53` | 2023 | 80 keyed | live | yes (Series B, final key) |
| `9e191ae4-68b9-47bf-9121-6d9d468a7bc5` | 2024 | 75 keyed (Q49, Q55–58 absent) | live | yes (Series A, final key) |
| `505b29a0-0d4d-5230-88aa-3bbc525a6db5` | 2025 | 80 keyed | live | yes (Series B, final key) |
| `b06305ad-cc93-4c27-b309-1b590f0a3247` | 2026 | 80 keyed | live | yes (Series D, provisional key) |
| `7b18bf8d-2919-4328-9779-8b0fe9a8b22a` | 2026 | 70 | unprocessed import: none verified, projected or explained | no, out of scope |

## 8. Counts and validation

- **Rows:** 315, question_ids set-equal to the export.
- **new_correct_option_id:** 0 rows point at another question's option. 0 rows have `applies = yes` with no new id. 0 new
  ids equal the current id. `applies = yes`: 6.
- **Verdict:** MATCH 306, CORRECTION 6, PROPOSED 3.
- **Confidence:** high 200, medium 111, low 4.
  - Medium is mostly MATCH rows the solve could not answer, where agreement rests on letters alone.
  - Low: 2024 Q54 and the three 2026 PROPOSED rows.
- **Solvable:** yes 209, no 106 (all passage-dependent).
  - Of the 209, 201 have a unique answer and 8 have more than one reading: 2023 Q44 and Q79, 2024 Q69, 2025 Q7, Q36, Q60
    and Q79, 2026 Q75.

## 9. Evidence versus inference

**What the evidence shows:**
- The stored CSAT keys follow Series B, A, B and D for 2023–2026, and agree with UPSC's key on 306 of 315 rows.
- 6 stored keys contradict UPSC's final key. 2023 Q57 is independently confirmed by an exhaustive search. The 3
  passage-question corrections rest on the final key alone.
- 3 stored 2026 keys contradict UPSC's provisional key and cannot be solved from the export.
- The independent solve agrees with UPSC's letter on 200 of 201 uniquely solved rows. No row shows the option-reorder
  signature.
- 106 questions reach the export without their passage, in 33 runs. For 2025, migration 228 links 25 of them to stored
  passages and leaves Q3, Q4, Q11 and Q12 unlinked.
- 11 stems lost symbols or superscripts, and 2024 Q54 cannot be recovered.
- There are no duplicate options, no shared questions among the live papers, and no directions-in-options rows.

**What I infer but have not proved:**
- The CSAT keys were taken from UPSC's own keys (or a faithful copy), unlike the 2020, 2024 and 2025 GS keys. Nine
  disagreements in 315 look like individual transcription slips, not a non-official source.
- For 2023, 2024 and 2026, the missing passages are either an export limitation (stimuli stored separately, as for most
  of 2025) or genuinely orphaned stimuli. The §5 query decides which.
- 2024 Q49 and Q55–58 are a missing data-interpretation set.
- The 2026 PROPOSED rows will resolve toward UPSC's letter when the final key is published, but a provisional key can
  change.

## 10. Operator step (not done here)

1. Apply the 6 rows where `applies = yes` by option id.
2. Leave the 3 PROPOSED rows until UPSC publishes the final 2026 Paper II key.
3. Run the §5 query. Restore the passages for every unlinked run. For 2025, re-import the passages for Q3–4 and Q11–12.
4. Restore the 11 damaged stems from the booklets, 2024 Q54 first.
