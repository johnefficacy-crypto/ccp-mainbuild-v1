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
| 2026-06-01 | v2 / PR #553 (Phase 4) | ≥ 0.80 | ≥ 0.774 | pending CI | pending CI | — | 92 | **pending** |

### FAIL run detail — 2026-05-31

```
required: 0.80
recall:   0.707  (65/92 matched)
precision: 0.774 (19 spurious of 84 extracted)
invented Q#: none
duplicate Q#: none

missed Q#: [1, 2, 3, 5, 6, 7, 8, 9, 12, 13, 19, 20, 22, 27, 31,
            40, 54, 55, 64, 66, 80, 81, 88, 90, 92, 93, 94]
```

Gap analysis: `docs/extraction/v2-recall-fix-gap-analysis.md`

### Phase 3 PASS — 2026-06-01

Root-cause fix merged: guarded off-edge option boundary in `find_stem_end`
(PR #553). Recall recovered to ≥ 0.80. Exact metrics available in CI log
for the `extractor-acceptance` workflow run on this branch.

### Phase 4 options_recall gate — 2026-06-01

Options measurement: **presence-rate baseline** — fraction of matched stems
for which the extractor produced a complete valid `(a, b, c, d)` tuple with
non-empty text for each option. No fixture ground-truth option text required.  
Threshold: ≥ 0.70.  
Status: pending CI run with live Supabase credentials.
