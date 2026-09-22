# OCR reconciliation - Phase 3 (newly sourced official papers)

Inputs: `D:\Users\user\Downloads\upsc-mains` (read-only). Calibrated phase-2 setup, not retuned: 300 DPI, tesseract `eng`, `strip_legacy_font`, full-text matching, single 85 match cut (exact >=95, variant 85-94, orphan <85). Every scored row is `ocr_derived=true`. Low-confidence extraction (raw OCR < 1500 tokens OR legacy-font noise > 5.0%) is flagged and left `unverifiable`, never scored and never clean. No DB writes, no network, no edits to any extraction JSON.

Year and paper are read from each PDF's own printed content. The **cover page** supplies the examination year and the paper label (English `GENERAL STUDIES (PAPER-<n>)` and the Hindi label's trailing numeral); the **UPSC paper-set code** printed in every page footer (`M-ESC-O-GSA`, `SKYC-G-GST`, `KVMS-G-GSD`) supplies a second paper vote and groups the four papers of one sitting, so a cover whose year OCR'd as garbage can take the year printed on its sitting-mates' covers. Only page 1 is searched for the year: later pages carry years inside the questions themselves ("Budget 2017-18", "Act, 2016", "1917") which would otherwise outvote the header. Ties are not resolved and nothing is ever taken from the filename; the filename column below only records whether it agrees.

## 1. Extraction quality per paper

| file | content year | year read from | content paper | filename says | raw tokens | eng words post-strip | noise % | confidence |
|---|---|---|---|---|---|---|---|---|
| QP-CSM-16-010926-GENERAL STUDIES PAPER - I.pdf | 2016 | cover header | GS1 | no year GS1 | 1071 | 695 | 1.4 | LOW (raw_tokens 1071<1500) |
| QP-CSM-16-010926-GENERAL-STUDIES-PAPER - II.pdf | 2016 | cover header | GS2 | no year GS2 | 1589 | 1010 | 1.5 | ok |
| QP-CSM-16-010926-GENERAL-STUDIES-PAPER-III.pdf | 2016 | cover header | GS3 | no year GS3 | 1533 | 982 | 1.0 | ok |
| QP-CSM-16-010926-GENERAL-STUDIES-PAPER-IV.pdf | 2016 | cover header | GS4 | no year GS4 | 3644 | 2214 | 0.9 | ok |
| QP-CSM-17-010926-GENERAL STUDIES PAPER - I.pdf | 2017 | cover (sole year token) | GS1 | no year GS1 | 1343 | 806 | 2.3 | LOW (raw_tokens 1343<1500) |
| QP-CSM-17-010926-GENERAL-STUDIES-PAPER - II.pdf | **UNREAD** | none | GS2 | no year GS2 | 1780 | 1074 | 1.6 | ok |
| QP-CSM-17-010926-GENERAL-STUDIES-PAPER-III.pdf | 2017 | paper-set code STH (group) | GS3 | no year GS3 | 1810 | 1091 | 1.5 | ok |
| QP-CSM-17-010926-GENERAL-STUDIES-PAPER-IV.pdf | 2017 | paper-set code STH (group) | GS4 | no year GS4 | 2626 | 1563 | 2.6 | ok |
| QP-CSM-18-010926-GENERAL STUDIES PAPER - I.pdf | 2018 | paper-set code EGT (group) | GS1 | no year GS1 | 1295 | 749 | 2.0 | LOW (raw_tokens 1295<1500) |
| QP-CSM-18-010926-GENERAL-STUDIES-PAPER - II.pdf | 2018 | paper-set code EGT (group) | GS2 | no year GS2 | 1677 | 1004 | 2.3 | ok |
| QP-CSM-18-010926-GENERAL-STUDIES-PAPER-III.pdf | 2018 | paper-set code EGT (group) | GS3 | no year GS3 | 1713 | 1030 | 2.2 | ok |
| QP-CSM-18-010926-GENERAL-STUDIES-PAPER-IV.pdf | 2018 | cover header | GS4 | no year GS4 | 4130 | 2485 | 1.1 | ok |
| QP-CSM-23-GENERAL-STUDIES-PAPER-I-180923.pdf | 2023 | cover header | GS1 | no year GS1 | 1226 | 727 | 1.6 | LOW (raw_tokens 1226<1500) |
| QP-CSM-23-GENERAL-STUDIES-PAPER-II-180923.pdf | 2023 | paper-set code SKYC (group) | **UNREAD** | no year GS2 | 1357 | 822 | 1.6 | LOW (raw_tokens 1357<1500) |
| QP-CSM-23-GENERAL-STUDIES-PAPER-III-180923.pdf | 2023 | cover header | GS3 | no year GS3 | 1763 | 1059 | 2.1 | ok |
| QP-CSM-23-GENERAL-STUDIES-PAPER-IV-180923.pdf | 2023 | cover (sole year token) | GS4 | no year GS4 | 5004 | 3043 | 1.5 | ok |
| QP-CSM-26-010926-ESSAY.pdf | 2026 | cover header | **UNREAD** | no year Essay | 403 | 228 | 1.9 | LOW (raw_tokens 403<1500) |
| QP-CSM-26-010926-GENERAL STUDIES PAPER - I.pdf | 2026 | cover header | GS1 | no year GS1 | 1184 | 730 | 2.1 | LOW (raw_tokens 1184<1500) |
| QP-CSM-26-010926-GENERAL-STUDIES-PAPER - II.pdf | 2026 | cover header | GS2 | no year GS2 | 1946 | 1178 | 1.6 | ok |
| QP-CSM-26-010926-GENERAL-STUDIES-PAPER-III.pdf | 2026 | cover header | GS3 | no year GS3 | 1972 | 1204 | 1.3 | ok |
| QP-CSM-26-010926-GENERAL-STUDIES-PAPER-IV.pdf | 2026 | cover header | GS4 | no year GS4 | 5007 | 3083 | 0.9 | ok |

- Files OCR'd: **21**. Classified from content to a GS paper: **18**.
- Unclassified from content (reported, never guessed, never scored): **3** - `QP-CSM-17-010926-GENERAL-STUDIES-PAPER - II.pdf` (year=none, paper=GS2), `QP-CSM-23-GENERAL-STUDIES-PAPER-II-180923.pdf` (year=2023, paper=none), `QP-CSM-26-010926-ESSAY.pdf` (year=2026, paper=none).
- Failed / low-confidence extractions (flagged, NOT scored): **7** - `QP-CSM-16-010926-GENERAL STUDIES PAPER - I.pdf` [raw_tokens 1071<1500], `QP-CSM-17-010926-GENERAL STUDIES PAPER - I.pdf` [raw_tokens 1343<1500], `QP-CSM-18-010926-GENERAL STUDIES PAPER - I.pdf` [raw_tokens 1295<1500], `QP-CSM-23-GENERAL-STUDIES-PAPER-I-180923.pdf` [raw_tokens 1226<1500], `QP-CSM-23-GENERAL-STUDIES-PAPER-II-180923.pdf` [raw_tokens 1357<1500], `QP-CSM-26-010926-ESSAY.pdf` [raw_tokens 403<1500], `QP-CSM-26-010926-GENERAL STUDIES PAPER - I.pdf` [raw_tokens 1184<1500].

## 2. DB source rows vs the now-available official papers

Scope: the DB/source GS JSONs for 2016, 2017, 2018 and 2023 (`UPSCCSEMains*.json`), scored against the official paper for their own year and paper. Counts are per source ROW, not per distinct question: 2016 and 2017 are each covered by more than one source file (e.g. `UPSCCSEMains2016GS2.json` and `UPSCCSEMains2016APPENDGS1GS2.json`), so a paper carrying 20 questions can contribute 40 rows.

### Counts by year and paper

| year | paper | exact | variant | orphan | unverifiable | total |
|---|---|---|---|---|---|---|
| 2016 | GS1 | 0 | 0 | 0 | 40 | 40 |
| 2016 | GS2 | 0 | 0 | 40 | 0 | 40 |
| 2016 | GS3 | 20 | 0 | 0 | 0 | 20 |
| 2016 | GS4 | 18 | 0 | 0 | 0 | 18 |
| 2017 | GS1 | 0 | 0 | 0 | 40 | 40 |
| 2017 | GS2 | 0 | 0 | 0 | 40 | 40 |
| 2017 | GS3 | 30 | 2 | 8 | 0 | 40 |
| 2017 | GS4 | 41 | 3 | 11 | 0 | 55 |
| 2018 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2018 | GS2 | 20 | 0 | 0 | 0 | 20 |
| 2018 | GS3 | 20 | 0 | 0 | 0 | 20 |
| 2018 | GS4 | 18 | 1 | 0 | 0 | 19 |
| 2023 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2023 | GS2 | 0 | 0 | 0 | 20 | 20 |
| 2023 | GS3 | 20 | 0 | 0 | 0 | 20 |
| 2023 | GS4 | 6 | 0 | 6 | 0 | 12 |

### Counts by year

| year | exact | variant | orphan | unverifiable | total | score dist |
|---|---|---|---|---|---|---|
| 2016 | 38 | 0 | 40 | 40 | 118 | n=78 min=46.9 med=69.7 max=100.0 |
| 2017 | 71 | 5 | 19 | 80 | 175 | n=95 min=45.3 med=100.0 max=100.0 |
| 2018 | 58 | 1 | 0 | 20 | 79 | n=59 min=89.8 med=100.0 max=100.0 |
| 2023 | 26 | 0 | 6 | 40 | 72 | n=32 min=70.5 med=100.0 max=100.0 |

- Total DB rows scored across the four years: **444** - **193 exact, 6 variant, 65 orphan, 180 unverifiable**.
- DB orphans that match a DIFFERENT official paper at >= 85 (misfiled rather than invented): **1** of 65.
    - 2017 GS3: 1 row(s) match 2016 GS3 instead

### Orphan blocks (DB text absent from the official paper)

| year | paper | orphans | own-score min/med/max | best score vs any other official paper |
|---|---|---|---|---|
| 2016 | GS2 | 40 | 46.9 / 51.0 / 69.7 | 65.8 |
| 2017 | GS3 | 8 | 48.8 / 49.6 / 84.2 | 100.0 |
| 2017 | GS4 | 11 | 45.3 / 46.5 / 81.7 | 57.9 |
| 2023 | GS4 | 6 | 70.5 / 71.3 / 83.2 | 54.0 |

A block that is orphan against its own paper AND scores no better against any other official paper is not a filing error: that text is not in the official corpus at all.

## 3. UnlockIAS extraction vs the same official papers (trust test)

Same thresholds. A paper is **MISFILED** when at least 50% of its UnlockIAS questions are orphans against the official paper they are filed under, **TRUSTED** when it has zero orphans, **PARTIAL** in between. Orphans scoring >= 85 against another official paper are reported as relocations - that is what misfiling looks like.

### Counts by year and paper (2016/2017/2018/2023)

| year | paper | exact | variant | orphan | unverifiable | total |
|---|---|---|---|---|---|---|
| 2016 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2016 | GS2 | 20 | 0 | 0 | 0 | 20 |
| 2016 | GS3 | 20 | 0 | 0 | 0 | 20 |
| 2016 | GS4 | 18 | 0 | 0 | 0 | 18 |
| 2017 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2017 | GS2 | 0 | 0 | 0 | 20 | 20 |
| 2017 | GS3 | 19 | 0 | 1 | 0 | 20 |
| 2017 | GS4 | 17 | 1 | 0 | 0 | 18 |
| 2018 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2018 | GS2 | 20 | 0 | 0 | 0 | 20 |
| 2018 | GS3 | 20 | 0 | 0 | 0 | 20 |
| 2018 | GS4 | 19 | 0 | 0 | 0 | 19 |
| 2023 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2023 | GS2 | 0 | 0 | 0 | 20 | 20 |
| 2023 | GS3 | 20 | 0 | 0 | 0 | 20 |
| 2023 | GS4 | 19 | 0 | 0 | 0 | 19 |

### Per-paper trust line

| year | paper | questions | exact | variant | orphan | orphan % | relocates to | verdict |
|---|---|---|---|---|---|---|---|---|
| 2016 | GS1 | 20 | - | - | - | - | - | **UNVERIFIABLE** (no usable official paper) |
| 2016 | GS2 | 20 | 20 | 0 | 0 | 0% | - | **TRUSTED** |
| 2016 | GS3 | 20 | 20 | 0 | 0 | 0% | - | **TRUSTED** |
| 2016 | GS4 | 18 | 18 | 0 | 0 | 0% | - | **TRUSTED** |
| 2017 | GS1 | 20 | - | - | - | - | - | **UNVERIFIABLE** (no usable official paper) |
| 2017 | GS2 | 20 | - | - | - | - | - | **UNVERIFIABLE** (no usable official paper) |
| 2017 | GS3 | 20 | 19 | 0 | 1 | 5% | - | **PARTIAL** |
| 2017 | GS4 | 18 | 17 | 1 | 0 | 0% | - | **TRUSTED** |
| 2018 | GS1 | 20 | - | - | - | - | - | **UNVERIFIABLE** (no usable official paper) |
| 2018 | GS2 | 20 | 20 | 0 | 0 | 0% | - | **TRUSTED** |
| 2018 | GS3 | 20 | 20 | 0 | 0 | 0% | - | **TRUSTED** |
| 2018 | GS4 | 19 | 19 | 0 | 0 | 0% | - | **TRUSTED** |
| 2023 | GS1 | 20 | - | - | - | - | - | **UNVERIFIABLE** (no usable official paper) |
| 2023 | GS2 | 20 | - | - | - | - | - | **UNVERIFIABLE** (no usable official paper) |
| 2023 | GS3 | 20 | 20 | 0 | 0 | 0% | - | **TRUSTED** |
| 2023 | GS4 | 19 | 19 | 0 | 0 | 0% | - | **TRUSTED** |

### Per-year trust line

- **2016: MIXED** - GS1 UNVERIFIABLE, GS2 TRUSTED, GS3 TRUSTED, GS4 TRUSTED.
- **2017: MIXED** - GS1 UNVERIFIABLE, GS2 UNVERIFIABLE, GS3 PARTIAL, GS4 TRUSTED.
- **2018: MIXED** - GS1 UNVERIFIABLE, GS2 TRUSTED, GS3 TRUSTED, GS4 TRUSTED.
- **2023: MIXED** - GS1 UNVERIFIABLE, GS2 UNVERIFIABLE, GS3 TRUSTED, GS4 TRUSTED.

## 4. 2026 - UnlockIAS only (the DB holds no 2026 Mains paper)

Nothing to reconcile on the DB side: the source JSONs contribute **0** in-scope 2026 GS rows. The UnlockIAS 2026 extraction is scored against the official 2026 papers below.

### 2026 counts by paper

| year | paper | exact | variant | orphan | unverifiable | total |
|---|---|---|---|---|---|---|
| 2026 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2026 | GS2 | 20 | 0 | 0 | 0 | 20 |
| 2026 | GS3 | 20 | 0 | 0 | 0 | 20 |
| 2026 | GS4 | 13 | 0 | 6 | 0 | 19 |

| paper | questions | exact | variant | orphan | orphan % | verdict |
|---|---|---|---|---|---|---|
| GS1 | 20 | - | - | - | - | **UNVERIFIABLE** |
| GS2 | 20 | 20 | 0 | 0 | 0% | **TRUSTED** |
| GS3 | 20 | 20 | 0 | 0 | 0% | **TRUSTED** |
| GS4 | 19 | 13 | 0 | 6 | 32% | **PARTIAL** |

Orphan questions (UnlockIAS 2026, best score vs the official paper they are filed under):

- GS4 local Q2 - 56.2
- GS4 local Q4 - 59.1
- GS4 local Q6 - 53.0
- GS4 local Q8 - 58.1
- GS4 local Q10 - 57.6
- GS4 local Q12 - 56.3

- **Safe to load: NO** - at least one 2026 paper is not clean against the official paper it is filed under (see the table). Loading it as-is would import unverified rows.

## 5. repair_worklist.csv update

Four columns were **appended**; every original column, including `source_confidence`, is copied through unchanged: `phase3_db_verdict`, `phase3_db_score`, `phase3_unlockias_verdict`, `phase3_unlockias_score`.

Scope note: no worklist row carries `source_confidence = unverifiable`. The unverifiable class in this file is spelled `aggregator-only`, and in 2016/2017/2018/2023 every row carries it. Those are the rows given a phase-3 verdict.

| year | scored text | exact | variant | orphan | unverifiable |
|---|---|---|---|---|---|
| 2016 | db_text | 38 | 0 | 20 | 20 |
| 2016 | unlockias_text | 58 | 0 | 0 | 20 |
| 2017 | db_text | 38 | 1 | 0 | 40 |
| 2017 | unlockias_text | 36 | 1 | 1 | 40 |
| 2018 | db_text | 58 | 1 | 0 | 20 |
| 2018 | unlockias_text | 59 | 0 | 0 | 20 |
| 2023 | db_text | 26 | 0 | 6 | 40 |
| 2023 | unlockias_text | 39 | 0 | 0 | 40 |
