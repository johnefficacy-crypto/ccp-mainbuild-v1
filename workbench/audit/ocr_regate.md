# OCR re-gate - post-strip English word floor

No re-OCR: both caches were warm and every number below comes from the cached 300 DPI text. Matching is unchanged - `strip_legacy_font`, full-text `partial_ratio`, single 85 cut (exact >=95, variant 85-94, orphan <85). The gate is the only thing that moved. Rows scored under it carry `gate_relaxed=true`; `ocr_phase2_verdict.csv` and `ocr_phase3_verdict.csv` are untouched, so the original conservative counts stay traceable.

## 1. Why the raw-token gate was the wrong measure

The old gate required >= 1500 RAW OCR tokens. Raw tokens count the bilingual output: the font-mangled Devanagari that `strip_legacy_font` removes is counted alongside the English. Across the whole corpus the English share of raw tokens is near-constant, so the raw-token count is essentially a measure of document bulk:

- English share of raw tokens across 37 papers: min 0.53, median 0.61, max 0.65. The gate did not separate noisy papers from clean ones; it separated long papers from short ones.
- Every paper it excluded has legacy-font noise well inside the 5% limit, so none of them is a failed extraction.

## 2. Deriving the new floor

Reference population: the **25 papers that scored cleanly** in phase 2 or phase 3 (passed the original gate and were used as matching targets). Their post-strip English word counts:

- min **953**, median 1260, max 3083
- the observed minimum is 2019 GS3 at **953** English words, which scored normally.

The floor is placed **30% below that observed minimum**: 953 x 0.70 = **667 English words**.

That margin is not arbitrary, and what it buys is worth stating plainly. Between the floor and the clean minimum the corpus is **continuous**: the 12 papers under 953 English words rise in steps of at most 74 words. There is no break down there for a floor to sit in, so no floor in that range would separate sound extractions from failed ones - it would only cut the population at an arbitrary point.

The lowest classified paper in the corpus is **670** English words (2019 GS1). The floor of 667 sits just below it, so **every classified paper passes the new gate**. That is the correct outcome rather than a weakness: none of the 37 papers is a failed extraction, and the gate's job is to catch one that is.

What a failed extraction actually looks like is available for comparison: `QP-CSM-26-010926-ESSAY.pdf` yields **403** raw tokens and **228** English words - 442 words below the lowest GS paper, the one real discontinuity anywhere in the batch. The floor of 667 falls inside that 442-word gap. (That file is out of scope for its own reason - it is the Essay paper and carries no GS identity - so it is a reference point here, not part of the population the floor was derived from.)

## 3. Gate status per paper

| year | paper | phase | raw tokens | eng words | noise % | old gate | new gate | |
|---|---|---|---|---|---|---|---|---|
| 2013 | GS1 | phase2 | 1592 | 996 | 2.6 | pass | pass |  |
| 2013 | GS2 | phase2 | 2091 | 1260 | 1.5 | pass | pass |  |
| 2013 | GS3 | phase2 | 2080 | 1287 | 2.1 | pass | pass |  |
| 2013 | GS4 | phase2 | 3823 | 2456 | 1.3 | pass | pass |  |
| 2014 | GS1 | phase2 | 1330 | 737 | 2.8 | **FAIL** | pass | **RE-SCORED** |
| 2014 | GS2 | phase2 | 2093 | 1265 | 1.1 | pass | pass |  |
| 2014 | GS3 | phase2 | 1922 | 1252 | 0.9 | pass | pass |  |
| 2014 | GS4 | phase2 | 3620 | 2291 | 1.0 | pass | pass |  |
| 2016 | GS1 | phase3 | 1071 | 695 | 1.4 | **FAIL** | pass | **RE-SCORED** |
| 2016 | GS2 | phase3 | 1589 | 1010 | 1.5 | pass | pass |  |
| 2016 | GS3 | phase3 | 1533 | 982 | 1.0 | pass | pass |  |
| 2016 | GS4 | phase3 | 3644 | 2214 | 0.9 | pass | pass |  |
| 2017 | GS1 | phase3 | 1343 | 806 | 2.3 | **FAIL** | pass | **RE-SCORED** |
| 2017 | GS3 | phase3 | 1810 | 1091 | 1.5 | pass | pass |  |
| 2017 | GS4 | phase3 | 2626 | 1563 | 2.6 | pass | pass |  |
| 2018 | GS1 | phase3 | 1295 | 749 | 2.0 | **FAIL** | pass | **RE-SCORED** |
| 2018 | GS2 | phase3 | 1677 | 1004 | 2.3 | pass | pass |  |
| 2018 | GS3 | phase3 | 1713 | 1030 | 2.2 | pass | pass |  |
| 2018 | GS4 | phase3 | 4130 | 2485 | 1.1 | pass | pass |  |
| 2019 | GS1 | phase2 | 1161 | 670 | 1.4 | **FAIL** | pass | **RE-SCORED** |
| 2019 | GS2 | phase2 | 1145 | 701 | 1.6 | **FAIL** | pass | **RE-SCORED** |
| 2019 | GS3 | phase2 | 1621 | 953 | 1.1 | pass | pass |  |
| 2019 | GS4 | phase2 | 2780 | 1620 | 1.9 | pass | pass |  |
| 2020 | GS1 | phase2 | 1201 | 739 | 2.1 | **FAIL** | pass | **RE-SCORED** |
| 2020 | GS2 | phase2 | 1665 | 1045 | 1.2 | pass | pass |  |
| 2020 | GS3 | phase2 | 1488 | 880 | 1.8 | **FAIL** | pass | **RE-SCORED** |
| 2020 | GS4 | phase2 | 3170 | 2011 | 1.3 | pass | pass |  |
| 2021 | GS2 | phase2 | 1273 | 672 | 2.7 | **FAIL** | pass | **RE-SCORED** |
| 2021 | GS3 | phase2 | 1274 | 750 | 2.4 | **FAIL** | pass | **RE-SCORED** |
| 2021 | GS4 | phase2 | 3972 | 2485 | 1.1 | pass | pass |  |
| 2023 | GS1 | phase3 | 1226 | 727 | 1.6 | **FAIL** | pass | **RE-SCORED** |
| 2023 | GS3 | phase3 | 1763 | 1059 | 2.1 | pass | pass |  |
| 2023 | GS4 | phase3 | 5004 | 3043 | 1.5 | pass | pass |  |
| 2026 | GS1 | phase3 | 1184 | 730 | 2.1 | **FAIL** | pass | **RE-SCORED** |
| 2026 | GS2 | phase3 | 1946 | 1178 | 1.6 | pass | pass |  |
| 2026 | GS3 | phase3 | 1972 | 1204 | 1.3 | pass | pass |  |
| 2026 | GS4 | phase3 | 5007 | 3083 | 0.9 | pass | pass |  |

- Papers admitted by the new gate: **12**.

Three files phase 3 OCR'd never reached a gate at all, because they carry no usable (year, paper) identity. No change to the gate can bring them into scope; they stay unverifiable:
- `QP-CSM-17-010926-GENERAL-STUDIES-PAPER - II.pdf` - paper reads GS2, no year on the cover and no paper-set code to inherit one from.
- `QP-CSM-23-GENERAL-STUDIES-PAPER-II-180923.pdf` - year reads 2023, paper unresolved: English label reads 'Paper I', Hindi label reads II.
- `QP-CSM-26-010926-ESSAY.pdf` - year reads 2026, Essay paper - outside GS scope.

## 4. DB rows re-scored under the relaxed gate

| year | paper | exact | variant | orphan | total | score min/med/max |
|---|---|---|---|---|---|---|
| 2014 | GS1 | 8 | 6 | 26 | 40 | 48.1 / 51.2 / 100.0 |
| 2016 | GS1 | 18 | 2 | 20 | 40 | 48.5 / 86.8 / 100.0 |
| 2017 | GS1 | 26 | 4 | 10 | 40 | 47.1 / 98.7 / 100.0 |
| 2018 | GS1 | 18 | 1 | 1 | 20 | 79.6 / 100.0 / 100.0 |
| 2019 | GS1 | 19 | 0 | 1 | 20 | 84.0 / 100.0 / 100.0 |
| 2019 | GS2 | 11 | 2 | 7 | 20 | 47.3 / 98.0 / 100.0 |
| 2020 | GS1 | 16 | 0 | 4 | 20 | 64.5 / 100.0 / 100.0 |
| 2020 | GS3 | 18 | 0 | 2 | 20 | 82.3 / 100.0 / 100.0 |
| 2021 | GS2 | 4 | 3 | 13 | 20 | 46.5 / 80.5 / 100.0 |
| 2021 | GS3 | 10 | 4 | 6 | 20 | 66.8 / 96.2 / 100.0 |
| 2023 | GS1 | 20 | 0 | 0 | 20 | 95.7 / 100.0 / 100.0 |
| **all** | | **168** | **22** | **90** | **280** | |

Admitted by the relaxed gate but absent from the table above, because the source JSONs hold no DB rows for them: 2026 GS1.

## 5. Per-year totals, with and without the relaxed rows

Baseline = the original conservative verdicts: phase 3 for 2016, 2017, 2018 and 2023 (it supersedes phase 2, which had no raw file for those years) and phase 2 for every other year. The relaxed rows replace the baseline's `unverifiable` rows for the same (year, paper), they are not added on top.

| year | baseline exact/variant/orphan/unverifiable | revised exact/variant/orphan/unverifiable | rows moved |
|---|---|---|---|
| 2013 | 2 / 0 / 184 / 0 | 2 / 0 / 184 / 0 | 0 |
| 2014 | 0 / 0 / 116 / 40 | 8 / 6 / 142 / 0 | 40 |
| 2016 | 38 / 0 / 40 / 40 | 56 / 2 / 60 / 0 | 40 |
| 2017 | 71 / 5 / 19 / 80 | 97 / 9 / 29 / 40 | 40 |
| 2018 | 58 / 1 / 0 / 20 | 76 / 2 / 1 / 0 | 20 |
| 2019 | 31 / 2 / 6 / 40 | 61 / 4 / 14 / 0 | 40 |
| 2020 | 21 / 7 / 11 / 40 | 55 / 7 / 17 / 0 | 40 |
| 2021 | 8 / 5 / 6 / 60 | 22 / 12 / 25 / 20 | 40 |
| 2023 | 26 / 0 / 6 / 40 | 46 / 0 / 6 / 20 | 20 |
| **all** | **255 / 20 / 388 / 360** | **423 / 42 / 478 / 80** | **280** |

The 80 rows still unverifiable after the relaxation are not gate casualties - no floor can reach them:

- **2017: 40 rows** - the 2017 GS2 PDF carries no readable year and no paper-set code to inherit one from, so it was never classified (two source files contribute 20 rows each)
- **2021: 20 rows** - no 2021 GS1 raw file exists in the corpus at all
- **2023: 20 rows** - the 2023 GS2 PDF classifies to 2023 but its paper is unresolved - the English label reads 'Paper I' against a Hindi label reading II
