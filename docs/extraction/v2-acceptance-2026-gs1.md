# v2 Extractor — Acceptance Gate Results: 2026 GS-I

Fixture: `tests/fixtures/exam_intelligence_extraction/upsc_cse_pyq_v1/questions.json`  
Document ID: `83722a86-610b-471d-8b6b-4a8397aa1791`  
Threshold: recall ≥ 0.80 (hard gate), precision ≥ 0.85 (target)

---

## Run history

| Date       | Extractor | Recall         | Precision      | Extracted | Fixture | Status |
|------------|-----------|----------------|----------------|-----------|---------|--------|
| 2026-05-31 | v2 / PR #528 | 0.707 (65/92) | 0.774 (65/84) | 84        | 92      | **FAIL** |

| 2026-06-01 | PR #554 guarded stem-end fix | 0.815 (75/92) | 0.893 (75/84) | 84 | 92 | **PASS** |

### FAIL run detail — 2026-05-31

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
required: 0.80
recall:   0.707  (65/92 matched)
precision: 0.774 (19 spurious of 84 extracted)
invented Q#: none
duplicate Q#: none

missed Q#: [1, 2, 3, 5, 6, 7, 8, 9, 12, 13, 19, 20, 22, 27, 31,
            40, 54, 55, 64, 66, 80, 81, 88, 90, 92, 93, 94]
```

Gap analysis: `docs/extraction/v2-recall-fix-gap-analysis.md`



