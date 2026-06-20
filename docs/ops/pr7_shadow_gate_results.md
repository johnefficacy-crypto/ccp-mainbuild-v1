# PR7: 14-Day Mastery Shadow Gate Results

**Type:** Operator evidence  
**Clock start:** After PR6 baseline SHA is deployed and verified  
**Status:** Pending

## Gate Thresholds (updated — PR-5A)

All thresholds must pass before proceeding to PR8 (live canary plan).

### shadow-replay gate

| Metric | Required | Actual |
|--------|----------|--------|
| distinct_attempt_count | ≥ 20 | _____ |
| topic_decision_count | ≥ 50 | _____ |
| exact_match_pct | 100.0 | _____ |
| coverage_pct | 100.0 | _____ |
| missing_count | 0 | _____ |
| extra_count | 0 | _____ |
| mismatch_count | 0 | _____ |
| duplicate_key_count | 0 | _____ |
| invariant_violations | 0 | _____ |
| classification_not_ready_count | 0 | _____ |

### correction-parity gate

| Metric | Required | Actual |
|--------|----------|--------|
| decision_count | ≥ 10 | _____ |
| exact_parity_pct | 100.0 | _____ |

## REMOVED gates (invalid — do not use)

The following thresholds from the previous version of this document are
**removed** because they relied on invalid cross-population comparisons or
unapproved comparators:

- ~~Sign agreement ≥ 80%~~ — no approved comparator exists in shadow mode;
  use live-audit-compare during canary only.
- ~~Task overlap ≥ 60%~~ — cross-origin topic identity is unavailable
  (canonical UUID vs display label); metric is not computable.

## Instructions

1. Prerequisite: PR-4 (`attempt_derivation.py`) must be merged before running
   shadow-replay or correction-parity.
2. Do **not** make validation-relevant backend changes during the 14-day window.
3. Run shadow analysis at minimum weekly and at end of window:

```bash
# Weekly check
NEXT_PUBLIC_SUPABASE_URL=<url> SUPABASE_SERVICE_ROLE_KEY=<key> \
  python tools/mastery_shadow_analysis/shadow_analysis.py \
    --json shadow-replay --days 7

# Weekly correction parity
NEXT_PUBLIC_SUPABASE_URL=<url> SUPABASE_SERVICE_ROLE_KEY=<key> \
  python tools/mastery_shadow_analysis/shadow_analysis.py \
    --json correction-parity --days 7

# Final 14-day gate
NEXT_PUBLIC_SUPABASE_URL=<url> SUPABASE_SERVICE_ROLE_KEY=<key> \
  python tools/mastery_shadow_analysis/shadow_analysis.py \
    --json shadow-replay --days 14

NEXT_PUBLIC_SUPABASE_URL=<url> SUPABASE_SERVICE_ROLE_KEY=<key> \
  python tools/mastery_shadow_analysis/shadow_analysis.py \
    --json correction-parity --days 14
```

4. For each run, attach the `--json` output to this PR.

Exit codes: 0 = PASS/FAIL (valid result), 2 = ERROR, 3 = INSUFFICIENT_DATA,
4 = CORRUPT/invariant-invalid.

## shadow-replay Results

| Date | Days | Attempts | Decisions | exact_match_pct | coverage_pct | Status |
|------|------|----------|-----------|-----------------|--------------|--------|
| | 7 | | | | | |
| | 7 | | | | | |
| | 14 (final) | | | | | |

## correction-parity Results

| Date | Days | Decisions | exact_parity_pct | Status |
|------|------|-----------|------------------|--------|
| | 14 (final) | | | |

## Outlier Review

Invariant violations (proposed_delta_db_unweighted or trust-adjusted cap violations,
mastery bounds, clamp errors): expected 0. Any violation requires investigation.

| Attempt ID | Topic ID | Violation Description | Investigation |
|------------|----------|-----------------------|---------------|
| | | | |

## Final Decision

- [ ] shadow-replay: all thresholds pass (exit 0, status PASS): **PASS / FAIL**
- [ ] correction-parity: exact_parity_pct = 100.0 (exit 0, status PASS): **PASS / FAIL**
- [ ] No invariant violations (exit code ≠ 4): **PASS / FAIL**
- [ ] Approved to proceed to PR8 (live canary): **YES / NO**

Do NOT claim 14-day PASS without attaching the JSON output.  
Do NOT claim live validation from shadow-mode runs.

**Decision made by:** `______________________________`  
**Date:** `______________________________`  
**14-day window:** `____________` to `____________`
