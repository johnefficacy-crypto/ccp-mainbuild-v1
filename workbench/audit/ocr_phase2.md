# OCR reconciliation — Phase 2 (nine scan-only years)

Calibrated setup, not retuned: 300 DPI, tesseract eng, `strip_legacy_font`, full-text matching, single 85 match cut (exact >=95, variant 85-95, orphan <85). Every row is `ocr_derived=true`. Low-confidence extraction (raw OCR < 1500 tokens OR legacy-font noise > 5.0%) is flagged and left `unverifiable`, not scored. Years with no classifiable raw file (2016, 2017, 2018, 2023; also 2021 GS1) are `unverifiable`.

## OCR extraction inventory + confidence

| year | paper | file | raw_tokens | eng_words | noise% | confidence |
|---|---|---|---|---|---|---|
| 2013 | GS1 | GS I-2013.pdf | 1592 | 996 | 2.6 | ok |
| 2013 | GS2 | GS II-2013.pdf | 2091 | 1260 | 1.5 | ok |
| 2013 | GS3 | GS III-2013.pdf | 2080 | 1287 | 2.1 | ok |
| 2013 | GS4 | GS IV-2013.pdf | 3823 | 2456 | 1.3 | ok |
| 2014 | GS1 | GENERAL STUDIES-I-2014.pdf | 1330 | 737 | 2.8 | LOW (raw_tokens 1330<1500) |
| 2014 | GS2 | GENERAL STUDIES-II-2014.pdf | 2093 | 1265 | 1.1 | ok |
| 2014 | GS3 | GENERAL STUDIES-III-2014.pdf | 1922 | 1252 | 0.9 | ok |
| 2014 | GS4 | GENERAL STUDIES-IV-2014.pdf | 3620 | 2291 | 1.0 | ok |
| 2019 | GS1 | done\GS-Mains-Paper-I-2019.pdf | 1161 | 670 | 1.4 | LOW (raw_tokens 1161<1500) |
| 2019 | GS2 | done\GS-Mains-Paper-II-2019.pdf | 1145 | 701 | 1.6 | LOW (raw_tokens 1145<1500) |
| 2019 | GS3 | done\GS-Mains-Paper-III-2019.pdf | 1621 | 953 | 1.1 | ok |
| 2019 | GS4 | done\GS-Mains-Paper-IV-2019.pdf | 2780 | 1620 | 1.9 | ok |
| 2020 | GS1 | GS Mains Paper-I (2020).pdf | 1201 | 739 | 2.1 | LOW (raw_tokens 1201<1500) |
| 2020 | GS2 | GS Mains Paper-II (2020).pdf | 1665 | 1045 | 1.2 | ok |
| 2020 | GS3 | GS Mains Paper-III (2020).pdf | 1488 | 880 | 1.8 | LOW (raw_tokens 1488<1500) |
| 2020 | GS4 | GS Mains Paper-IV (2020).pdf | 3170 | 2011 | 1.3 | ok |
| 2021 | GS2 | Gs paper 2 (2021).pdf | 1273 | 672 | 2.7 | LOW (raw_tokens 1273<1500) |
| 2021 | GS3 | G.S Paper-III (2021).pdf | 1274 | 750 | 2.4 | LOW (raw_tokens 1274<1500) |
| 2021 | GS4 | G.S Paper-4 (2021).pdf | 3972 | 2485 | 1.1 | ok |

## Verdict counts by year and paper

| year | paper | exact | variant | orphan | unverifiable | total |
|---|---|---|---|---|---|---|
| 2013 | GS1 | 2 | 0 | 48 | 0 | 50 |
| 2013 | GS2 | 0 | 0 | 50 | 0 | 50 |
| 2013 | GS3 | 0 | 0 | 50 | 0 | 50 |
| 2013 | GS4 | 0 | 0 | 36 | 0 | 36 |
| 2014 | GS1 | 0 | 0 | 0 | 40 | 40 |
| 2014 | GS2 | 0 | 0 | 40 | 0 | 40 |
| 2014 | GS3 | 0 | 0 | 40 | 0 | 40 |
| 2014 | GS4 | 0 | 0 | 36 | 0 | 36 |
| 2016 | GS1 | 0 | 0 | 0 | 40 | 40 |
| 2016 | GS2 | 0 | 0 | 0 | 40 | 40 |
| 2016 | GS3 | 0 | 0 | 0 | 20 | 20 |
| 2016 | GS4 | 0 | 0 | 0 | 18 | 18 |
| 2017 | GS1 | 0 | 0 | 0 | 40 | 40 |
| 2017 | GS2 | 0 | 0 | 0 | 40 | 40 |
| 2017 | GS3 | 0 | 0 | 0 | 40 | 40 |
| 2017 | GS4 | 0 | 0 | 0 | 55 | 55 |
| 2018 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2018 | GS2 | 0 | 0 | 0 | 20 | 20 |
| 2018 | GS3 | 0 | 0 | 0 | 20 | 20 |
| 2018 | GS4 | 0 | 0 | 0 | 19 | 19 |
| 2019 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2019 | GS2 | 0 | 0 | 0 | 20 | 20 |
| 2019 | GS3 | 18 | 0 | 2 | 0 | 20 |
| 2019 | GS4 | 13 | 2 | 4 | 0 | 19 |
| 2020 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2020 | GS2 | 19 | 1 | 0 | 0 | 20 |
| 2020 | GS3 | 0 | 0 | 0 | 20 | 20 |
| 2020 | GS4 | 2 | 6 | 11 | 0 | 19 |
| 2021 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2021 | GS2 | 0 | 0 | 0 | 20 | 20 |
| 2021 | GS3 | 0 | 0 | 0 | 20 | 20 |
| 2021 | GS4 | 8 | 5 | 6 | 0 | 19 |
| 2023 | GS1 | 0 | 0 | 0 | 20 | 20 |
| 2023 | GS2 | 0 | 0 | 0 | 20 | 20 |
| 2023 | GS3 | 0 | 0 | 0 | 20 | 20 |
| 2023 | GS4 | 0 | 0 | 0 | 12 | 12 |

## Verdict counts by year (all papers)

| year | exact | variant | orphan | unverifiable | total | score dist (scored) |
|---|---|---|---|---|---|---|
| 2013 | 2 | 0 | 184 | 0 | 186 | n=186 min=45.1 median=51.4 max=100.0 |
| 2014 | 0 | 0 | 116 | 40 | 156 | n=116 min=44.9 median=50.7 max=82.8 |
| 2016 | 0 | 0 | 0 | 118 | 118 | n=0 |
| 2017 | 0 | 0 | 0 | 175 | 175 | n=0 |
| 2018 | 0 | 0 | 0 | 79 | 79 | n=0 |
| 2019 | 31 | 2 | 6 | 40 | 79 | n=39 min=63.6 median=99.4 max=100.0 |
| 2020 | 21 | 7 | 11 | 40 | 79 | n=39 min=49.7 median=98.1 max=100.0 |
| 2021 | 8 | 5 | 6 | 60 | 79 | n=19 min=63.3 median=91.9 max=100.0 |
| 2023 | 0 | 0 | 0 | 72 | 72 | n=0 |

## Overall score distribution (scored rows)

- n=399 min=44.9 median=51.9 max=100.0

| bucket | n |
|---|---|
| <50 | 99 |
| 50-59 | 180 |
| 60-69 | 23 |
| 70-79 | 10 |
| 80-84 | 11 |
| 85-94 | 14 |
| 95-100 | 62 |

## Orphans in 2018-2025

- Phase-2 OCR orphans (2018-2023 in range; only 2019/2020/2021 have raw): **23**.
- Plus text-layer orphans 2022/2024/2025 (not OCR'd here): **1**.
- **Total orphans 2018-2025: 24.**
(2018 and 2023 have no classifiable raw -> unverifiable, not orphan; 2024/2025 have no in-scope source questions.)
