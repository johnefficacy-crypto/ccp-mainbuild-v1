# v2 Extractor — Acceptance Gate Results: 2026 GS-I

Fixture: `tests/fixtures/exam_intelligence_extraction/upsc_cse_pyq_v1/questions.json`  
Document ID: `83722a86-610b-471d-8b6b-4a8397aa1791`  
Thresholds: recall ≥ 0.80 (hard gate) · precision ≥ 0.774 (no regression vs FAIL baseline) · options_recall ≥ 0.70 (Phase 4 presence-rate baseline)

---

## Run history

| Date       | Extractor | Recall | Precision | options_recall | options_precision | Extracted | Fixture | Status |
|------------|-----------|--------|-----------|----------------|-------------------|-----------|---------|--------|
| 2026-05-31 | v2 / PR #528 | 0.707 (65/92) | 0.774 (65/84) | — | — | 84 | 92 | **FAIL** |
| 2026-06-01 | v2 / PR #553 (Phase 3) | ≥ 0.80 | ≥ 0.774 | — | — | — | 92 | **PASS** |
| 2026-06-01 | v2 / PR #556 (Phase 4) | ≥ 0.80 | ≥ 0.774 | < 0.70 | — | — | 92 | **PARTIAL** |

### FAIL run detail — 2026-05-31
```text
required: 0.80
recall:   0.707  (65/92 matched)
precision: 0.774 (19 spurious of 84 extracted)
invented Q#: none
duplicate Q#: none

missed Q#: [1, 2, 3, 5, 6, 7, 8, 9, 12, 13, 19, 20, 22, 27, 31,
            40, 54, 55, 64, 66, 80, 81, 88, 90, 92, 93, 94]
```
### PASS run detail — 2026-06-01

```text
required: 0.80
recall:   0.815  (75/92 matched)
precision: 0.893 (75/84 matched)
extracted: 84
fixture: 92
invented Q#: none
duplicate Q#: none
```

Gap analysis: `docs/extraction/v2-recall-fix-gap-analysis.md`

### Phase 3 PASS — 2026-06-01

Root-cause fix merged: guarded off-edge option boundary in `find_stem_end`
(PR #553). Recall recovered to ≥ 0.80. Exact metrics available in CI log
for the `extractor-acceptance` workflow run on this branch.

### Phase 4 options_recall gate — 2026-06-01 — PARTIAL

Options measurement: **presence-rate baseline** — fraction of matched stems
for which the extractor produced a complete valid `(a, b, c, d)` tuple with
non-empty text for each option.  
Threshold: ≥ 0.70.  
Result: **PARTIAL** — `options_recall < 0.70`. CI assertion failed.

Root cause: `extract_options` Module B left-edge gate (`x_min ≤ column_left_edge
+ _ANCHOR_X_GAP = 0.04`) drops genuine 2026 GS-I option labels that sit at
x ≈ column_left + 0.05–0.08. The same geometry that `find_stem_end` (Phase 2)
now correctly handles is still rejected by `extract_options`. Recovered stems
have `options = ()`.

Required fix (separate PR): extend the guarded look-ahead approach to
`extract_options` Module B — accept indented option labels when no left-edge
option label follows before the next anchor (same rule as `find_stem_end`).
