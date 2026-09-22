# Legacy-font run filter — detection, removal, and re-score

Legacy-font Hindi (Krutidev etc.) survives the `[\x20-\x7E]+` filter as ASCII gibberish ("jkds'k" = Rakesh), leaving a garbled duplicate of every question. `strip_legacy_font` drops runs with near-zero English-dictionary hit rate (dictionary: wordfreq) and heavy symbol density. This report quantifies removal and re-scores 2015 GS1/GS2 with and without the filter through the same matcher.

## Per-paper text removed

| year | paper | file | ascii_chars | removed | % removed |
|---|---|---|---|---|---|
| 2015 | GS1 | GS1-2015.pdf | 6252 | 1187 | 19.0% |
| 2015 | GS2 | GS-2-2015.pdf | 7608 | 1150 | 15.1% |
| 2015 | GS3 | GS3-2015.pdf | 8545 | 1474 | 17.2% |
| 2022 | GS1 | done\UPSC GS Mains GS1 2022.pdf | 5314 | 442 | 8.3% |
| 2022 | GS2 | GS Mains Paper II (2022).pdf | 7525 | 544 | 7.2% |
| 2022 | GS3 | GS Mains Paper III (2022).pdf | 7876 | 699 | 8.9% |
| 2022 | GS4 | GS Mains Paper IV (2022).pdf | 38809 | 3815 | 9.8% |

DOCX papers (2024/2025) are born-digital — no legacy font, ~0% removal — and are excluded from this scanned-paper check.

## Re-score 2015 GS1 — WITH vs WITHOUT filter

- rows: 40 (across per-paper + APPEND sources), **verdict moves: 0**.

| qno | verdict (raw) | best (raw) | verdict (filtered) | best (filtered) | moved |
|---|---|---|---|---|---|
| 1 | variant | 92.0 | variant | 92.0 | - |
| 10 | orphan | 64.4 | orphan | 64.4 | - |
| 11 | orphan | 59.2 | orphan | 59.2 | - |
| 12 | orphan | 58.4 | orphan | 58.4 | - |
| 13 | orphan | 53.3 | orphan | 53.3 | - |
| 14 | orphan | 51.9 | orphan | 50.9 | - |
| 15 | orphan | 54.7 | orphan | 54.7 | - |
| 16 | orphan | 56.3 | orphan | 56.3 | - |
| 17 | orphan | 54.3 | orphan | 53.9 | - |
| 18 | orphan | 56.0 | orphan | 56.0 | - |
| 19 | orphan | 54.2 | orphan | 54.2 | - |
| 2 | exact | 97.8 | exact | 97.8 | - |
| 20 | orphan | 53.5 | orphan | 53.5 | - |
| 21 | variant | 92.0 | variant | 92.0 | - |
| 22 | exact | 97.8 | exact | 97.8 | - |
| 23 | exact | 100.0 | exact | 100.0 | - |
| 24 | orphan | 53.3 | orphan | 53.3 | - |
| 25 | variant | 92.8 | variant | 92.8 | - |
| 26 | orphan | 51.9 | orphan | 52.8 | - |
| 27 | orphan | 63.3 | orphan | 63.3 | - |
| 28 | orphan | 52.8 | orphan | 52.8 | - |
| 29 | orphan | 58.0 | orphan | 58.0 | - |
| 3 | exact | 100.0 | exact | 100.0 | - |
| 30 | orphan | 64.4 | orphan | 64.4 | - |
| 31 | orphan | 59.2 | orphan | 59.2 | - |
| 32 | orphan | 58.4 | orphan | 58.4 | - |
| 33 | orphan | 53.3 | orphan | 53.3 | - |
| 34 | orphan | 51.9 | orphan | 50.9 | - |
| 35 | orphan | 54.7 | orphan | 54.7 | - |
| 36 | orphan | 56.3 | orphan | 56.3 | - |
| 37 | orphan | 54.3 | orphan | 53.9 | - |
| 38 | orphan | 56.0 | orphan | 56.0 | - |
| 39 | orphan | 54.2 | orphan | 54.2 | - |
| 4 | orphan | 53.3 | orphan | 53.3 | - |
| 40 | orphan | 53.5 | orphan | 53.5 | - |
| 5 | variant | 92.8 | variant | 92.8 | - |
| 6 | orphan | 51.9 | orphan | 52.8 | - |
| 7 | orphan | 63.3 | orphan | 63.3 | - |
| 8 | orphan | 52.8 | orphan | 52.8 | - |
| 9 | orphan | 58.0 | orphan | 58.0 | - |

## Re-score 2015 GS2 — WITH vs WITHOUT filter

- rows: 40 (across per-paper + APPEND sources), **verdict moves: 0**.

| qno | verdict (raw) | best (raw) | verdict (filtered) | best (filtered) | moved |
|---|---|---|---|---|---|
| 1 | orphan | 59.1 | orphan | 59.1 | - |
| 10 | orphan | 54.5 | orphan | 54.5 | - |
| 11 | orphan | 53.0 | orphan | 53.0 | - |
| 12 | orphan | 51.3 | orphan | 51.7 | - |
| 13 | orphan | 53.5 | orphan | 52.8 | - |
| 14 | orphan | 54.6 | orphan | 54.6 | - |
| 15 | orphan | 50.4 | orphan | 50.4 | - |
| 16 | orphan | 51.1 | orphan | 51.1 | - |
| 17 | orphan | 54.8 | orphan | 54.8 | - |
| 18 | orphan | 51.9 | orphan | 51.3 | - |
| 19 | orphan | 53.6 | orphan | 53.6 | - |
| 2 | orphan | 52.6 | orphan | 52.6 | - |
| 20 | orphan | 51.0 | orphan | 51.0 | - |
| 3 | orphan | 53.5 | orphan | 53.5 | - |
| 4 | orphan | 55.7 | orphan | 54.1 | - |
| 41 | orphan | 59.1 | orphan | 59.1 | - |
| 42 | orphan | 52.6 | orphan | 52.6 | - |
| 43 | orphan | 53.5 | orphan | 53.5 | - |
| 44 | orphan | 55.7 | orphan | 54.1 | - |
| 45 | orphan | 55.3 | orphan | 55.3 | - |
| 46 | orphan | 49.1 | orphan | 49.1 | - |
| 47 | orphan | 53.0 | orphan | 52.9 | - |
| 48 | orphan | 55.2 | orphan | 55.2 | - |
| 49 | orphan | 53.2 | orphan | 53.2 | - |
| 5 | orphan | 55.3 | orphan | 55.3 | - |
| 50 | orphan | 54.5 | orphan | 54.5 | - |
| 51 | orphan | 53.0 | orphan | 53.0 | - |
| 52 | orphan | 51.3 | orphan | 51.7 | - |
| 53 | orphan | 53.5 | orphan | 52.8 | - |
| 54 | orphan | 54.6 | orphan | 54.6 | - |
| 55 | orphan | 50.4 | orphan | 50.4 | - |
| 56 | orphan | 51.1 | orphan | 51.1 | - |
| 57 | orphan | 54.8 | orphan | 54.8 | - |
| 58 | orphan | 51.9 | orphan | 51.3 | - |
| 59 | orphan | 53.6 | orphan | 53.6 | - |
| 6 | orphan | 49.1 | orphan | 49.1 | - |
| 60 | orphan | 51.0 | orphan | 51.0 | - |
| 7 | orphan | 53.0 | orphan | 52.9 | - |
| 8 | orphan | 55.2 | orphan | 55.2 | - |
| 9 | orphan | 53.2 | orphan | 53.2 | - |

## Conclusion

**2015 GS2 stays 20/20 orphan with the filter applied — the verdict does NOT move.** The earlier finding (the 2015 GS2 source JSON is not the official paper) is CONFIRMED, not an artefact of un-stripped legacy-font text. `partial_ratio` already locates the best English substring regardless of surrounding garbage, so removing the garbled Hindi (the per-paper removal above) leaves the match scores essentially unchanged.

Total verdict moves across re-scored rows: **0**. The filter is verdict-neutral here but is worth wiring into the extraction path as hygiene (smaller/cleaner text, and protection against a future case where garbage coincidentally aligns with a question window).
