# v2 Acceptance — UPSC CSE 2026 GS-I

## Run context

- Date:
- Runner: GitHub Actions `extractor-acceptance`
- Environment strategy: CI dispatch only
- Workflow: `.github/workflows/extractor-acceptance.yml`
- Test: `app/backend/tests/exam_intelligence/extraction/test_pipeline_against_fixture.py`
- Current checked-in stem recall threshold: `0.80`

## Stem/question extraction result

Status: FAIL

CI run completed with valid environment:

- Supabase env: present
- Tesseract installed in CI
- Runner: Ubuntu 24.04
- Python: 3.12.13

Result:

- Recall: 0.707
- Required threshold: 0.80
- Precision: 0.774
- Extracted: 84
- Fixture: 92
- Invented question numbers: none
- Duplicate question numbers: none
- Matched: 65
- Missed: 27

Failure:

```text
AssertionError: Recall 0.707 < 0.8.
Missed: [1, 2, 3, 5, 6, 7, 8, 9, 12, 13, 19, 20, 22, 27, 31, 40, 54, 55, 64, 66, 80, 81, 88, 90, 92, 93, 94]
Total extracted: 84
```

## Options extraction result

Status: not covered by checked-in acceptance test.

## Decision

- [ ] PASS
- [x] FAIL

Notes:

Paper #2 ingest remains blocked. The CI environment is valid, but stem recall is below threshold. Options recall is still not measured by the checked-in acceptance gate.

