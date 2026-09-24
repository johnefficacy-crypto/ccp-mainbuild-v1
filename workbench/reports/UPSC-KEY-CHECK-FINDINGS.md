# UPSC Prelims 2020 and 2024 — stored-key check against UPSC's official keys (UPSC-KEY-CHECK-01)

Worksheet: `workbench/worksheets/UPSC-KEY-CHECK-2020-2024.csv`. It has 272 rows, one for every 2020 and 2024 row in
`workbench/sources/upsc-explanations-input.json`: 100 from 2020 GS Paper I, 97 from 2024 GS Paper I and 75 from 2024 CSAT
Paper II. No database write was made, and the explanation drafts are unchanged.

## 1. Availability of the official keys

| Year / paper | UPSC document | URL | Final or provisional | How it was read |
|---|---|---|---|---|
| 2020 GS Paper I | "CS(P)- EXAMINATION-2020 GENERAL STUDIES- PAPER- I(ONE)", Sets A–D, "Number of items-100, No of items dropped-02, Maximum Marks-200" | https://upsc.gov.in/sites/default/files/AnsKey-CSP-20-Paper-I-091121.pdf | **Final.** It is the post-cycle key with dropped items marked X; the file name dates it 09-11-2021. | A scanned copy was supplied by the repo owner and read page by page. The URL was confirmed by web search to carry this document, whose title matches. |
| 2024 GS Paper I | "CSP-2024, Paper 1, GS-Paper-I(ONE)", Series A–D, "Total Questions 100, No. of Questions Dropped 3, No. of Questions taken for Scoring 97" | https://upsc.gov.in/sites/default/files/AnsKey-CivilServicesPExam-2024-GeneralStudies-I-210525.pdf | **Final.** Published 21-05-2025 after the cycle, with dropped items marked X. | A scanned copy was supplied by the repo owner. Web search confirms that this URL carries "CSP-2024 - GS-Paper-I(ONE)". |
| 2024 CSAT Paper II | UPSC publishes it at https://upsc.gov.in/sites/default/files/AnsKey-CivilServicesPExam-2024-GeneralStudies-II-210525.pdf | — | — | **Not read.** upsc.gov.in refuses connections from this environment: the TLS handshake gets no answer, and the fetch tool gets HTTP 503. No copy was supplied, so the 75 CSAT rows are UNAVAILABLE. |

Both supplied PDFs are image scans with no text layer. Every key letter was transcribed from the page images. Two checks
support the transcription:

- Each series has exactly the dropped count its own header states: 2 per series in 2020 and 3 per series in 2024.
- The draft explanations, written independently from the question content, agree with the chosen series on 94 of 98
  (2020) and 92 of 97 (2024) scorable rows. Against the other three series they agree on 18–26 rows, which is chance level.

No coaching-site key was used anywhere. The transcribed tables are committed as
`workbench/sources/upsc-official-keys/csp2020_gs1_key_transcription.py` and `csp2024_gs1_key_transcription.py`, so the
transcription can be re-checked against the scans.

## 2. Matching corpus questions to UPSC's numbering

UPSC keys by question number within a booklet series. The corpus numbering corresponds to one series in each year:

- **2020 corpus numbering = Set C.** The two rows with an empty stored key (Q42, Q77) are exactly Set C's dropped items.
  Sets A, B and D drop other numbers: 27 and 52, 47 and 82, 32 and 67. The draft agrees with Set C on 94 of 98 scorable rows.
- **2024 corpus numbering = Series D.** The corpus has 97 GS rows and lacks exactly Q32, Q37 and Q80, which are Series D's
  three dropped items. The draft agrees with Series D on 92 of 97 rows.

The mapping is by number within the identified series. It was not checked against the question text of the Series C/D
booklets, which were not available. The two independent signals above make a series mismatch implausible. One row shows
an option-order problem rather than a numbering problem; see §5.

## 3. Counts by verdict

| Paper | Rows | MATCH | CORRECTION | UNAVAILABLE | UNMAPPABLE |
|---|---|---|---|---|---|
| 2020 GS Paper I | 100 | 83 | 16 | 0 | 1 |
| 2024 GS Paper I | 97 | 78 | 19 | 0 | 0 |
| 2024 CSAT Paper II | 75 | 0 | 0 | 75 | 0 |
| **Total** | **272** | **161** | **35** | **75** | **1** |

MATCH in 2020 includes the 2 items UPSC dropped (Q42, Q77). For those, the stored key is empty and UPSC scores no answer.
They must not be published with a correct answer.

**Correction rate among checked rows:**

- 2020: 16 of 97 scorable, checkable rows, or 16.5%. The count excludes the 2 dropped rows and the 1 UNMAPPABLE row.
- 2024 GS: 19 of 97, or 19.6%.

The CORRECTION rows are:

- **2020 (Set C numbering):** Q8, 20, 27, 32, 38, 49, 51, 52, 54, 55, 66, 68, 84, 86, 89, 90.
- **2024 GS (Series D numbering):** Q20, 21, 22, 28, 41, 43, 52, 53, 58, 64, 65, 67, 70, 71, 75, 81, 83, 86, 100.

Each CORRECTION row in the CSV carries its source URL on upsc.gov.in.

## 4. Pattern analysis — what kind of corruption

- **Not a constant shift.** Suppose each wrong stored key were UPSC's answer for a neighbouring question (offsets −5 to +5).
  The best offset explains only 8 of 16 wrong keys in 2020 (offsets −1 and +4) and 6 of 19 in 2024 (offset +3). Other
  offsets explain 2–5. Among four equally likely letters that is chance level, and no single offset stands out.
- **Not a series swap.** The stored keys agree with the other booklet series no better than chance: 22, 18 and 24 of 100
  in 2020, and 23, 25 and 17 of 97 in 2024. The stored keys are mostly Set C and Series D answers with scattered errors.
- **Not one letter.** The wrong stored letters are spread across A, C and D in 2020 and across B, C and D in 2024. The
  correct UPSC letters are spread evenly: 4/4/4/4 in 2020 and 9/1/3/6 in 2024. Overall letter frequencies of the stored and
  official keys are similar.
- **Conclusion:** the defect looks like scattered, question-by-question corruption. It affects about 1 in 6 questions in
  each of these two papers. It is not a mechanical offset that a single rule could undo, so the fix is row-by-row from
  this worksheet.

## 5. The drafting pass versus UPSC

| Paper | Draft disputes on keyed rows | Of those, UPSC-confirmed corrections | Disputes UPSC overrules | Corrections the draft missed |
|---|---|---|---|---|
| 2020 | 16 | 15 | 1 (Q75, now UNMAPPABLE) | 1 (Q89) |
| 2024 GS | 22 | 18 | 4 (Q25, Q35, Q38, Q82: UPSC keeps the stored key) | 1 (Q28) |

- **The draft's disputes are mostly a subset of the corrections.** 33 of the 38 keyed disputes are confirmed by UPSC.
  Beyond the dispute itself, the draft's proposed option equals UPSC's answer on all but two of those 33 (2020 Q20 and Q51).
- **The draft under-detected, but only slightly.** UPSC corrects 2 rows the draft accepted: 2020 Q89 and 2024 Q28 (SUMED
  pipeline). The draft had marked Q28 low confidence and named UPSC's answer as the more common reading. So 2 of 35
  corrections (about 6%) slipped through the "accept where defensible" standard. In a batch with no key corruption, that
  standard would let through about the same share of genuinely wrong keys.
- **The draft over-detected in 5 places:**
  - UPSC upholds the stored key on 2024 Q25, Q35, Q38 and Q82. On these rows the draft's reasoning is wrong and UPSC
    governs.
  - 2020 Q75 (hundi) is different. UPSC's Set C letter C equals the stored letter, but corpus option c reads "a diary for
    daily accounts". The documented meaning of a hundi is a bill of exchange, which is corpus option b. The likely cause is
    that the corpus's option order for this question differs from the booklet, so the letter cannot be applied safely.
    It is marked UNMAPPABLE; see §7.

## 6. Control years

**Not performed against official keys.** UPSC's keys for other years exist on upsc.gov.in. Web search located, for example,
`AnsKey-CSP-2023-Paper-I-090524.pdf` and `AnsKeyCivilServicesP-Exam-2025-GeneralStudies-I-130526.pdf`. But upsc.gov.in
cannot be read from this environment, and only the 2020 and 2024 keys were supplied. This check is outstanding.

Indirect evidence, which is not a substitute: the drafting pass disputed 0 GS rows in 2018, 2019, 2021, 2023 and 2026, and
2 each in 2022 and 2025. In the two corrupted papers it disputed 16 and 22. Given the ~6% under-detection rate measured in
§5, a clean-looking year could still hide a small number of wrong keys. The 16–22-per-paper signature, however, does not
appear elsewhere. Supplying two more official keys (for example 2023 and 2025 GS Paper I) would settle this. The
worksheet builder already takes any series table as input.

## 7. UNMAPPABLE rows

| Year | Q | Stored | UPSC (Set C) | Draft | Reason |
|---|---|---|---|---|---|
| 2020 | 75 | C | C | B | UPSC's letter matches the stored letter, but the corpus text under that letter ("A diary to be maintained for daily accounts") is not the attested meaning of a hundi (a bill of exchange, corpus option b). The corpus option order probably differs from the booklet. Resolve by checking the Set C booklet's option order before applying any key. |

## 8. What happened — evidence versus inference

**What the evidence shows:**

- 35 of 194 checkable GS rows in 2020 and 2024 carry a stored key that contradicts UPSC's final published key: 16 in 2020
  and 19 in 2024.
- The errors are scattered. They follow no constant offset, no series swap and no single letter.
- The corpus numbering for these papers follows Set C (2020) and Series D (2024).
- The drafting pass independently caught 33 of the 35.

**What I infer but cannot prove from these files:**

- The stored keys for these two papers were most likely hand-entered or copied from a non-official source (for example a
  coaching key) during import, rather than taken from UPSC's final key. Scattered disagreement on about one question in six
  is what a non-official key would produce. A mechanical import bug would more likely produce a shift or a swap.
- The 2020 Q75 case suggests that some question imports also reordered options. That is a separate defect, and it would
  make a letter-level key correction silently wrong. Before applying corrections, the operator should spot-check option
  order on the CORRECTION rows against the Set C / Series D booklets.

## 9. Recommended operator step (not done here)

1. Apply the 35 CORRECTION rows by setting `correct_option_id` to the option whose label equals `upsc_key_label`, after
   the option-order spot check above.
2. Mark 2020 Q42 and Q77 as dropped so no answer is shown as correct.
3. Resolve 2020 Q75 manually.
4. Supply the 2024 CSAT Paper II key and two control-year keys, then rerun the check.
