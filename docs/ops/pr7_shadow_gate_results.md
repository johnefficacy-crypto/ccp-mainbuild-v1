# PR7: 14-Day Mastery Shadow Gate Results

**Type:** Operator evidence  
**Clock start:** After PR6 baseline SHA is deployed and verified  
**Status:** Pending

## Gate Thresholds

| Metric | Required | Actual |
|--------|----------|--------|
| Sign agreement | ≥ 80% | _____ |
| Task overlap | ≥ 60% | _____ |
| Material outliers | 0 | _____ |

All three thresholds must pass before proceeding to PR8 (live canary plan).

## Instructions

1. Do **not** make validation-relevant backend changes during the 14-day window.
2. Run shadow analysis weekly (minimum) and at the end of the window:

```bash
# Weekly check
SUPABASE_URL=<url> SUPABASE_SERVICE_KEY=<key> \
  python tools/mastery_shadow_analysis/shadow_analysis.py \
    --json compare --days 7

# Final 14-day gate
SUPABASE_URL=<url> SUPABASE_SERVICE_KEY=<key> \
  python tools/mastery_shadow_analysis/shadow_analysis.py \
    --json compare --days 14

SUPABASE_URL=<url> SUPABASE_SERVICE_KEY=<key> \
  python tools/mastery_shadow_analysis/shadow_analysis.py \
    --json tasks-overlap --days 14
```

3. For each run, attach the `--json` output to this PR.

## Sign Agreement

**Denominator:** shadow rows matched to live audit rows via (attempt_id, topic_id).  
**Formula:** rows where sign(proposed_delta_db) == sign(delta_applied_db) / matched rows × 100.

| Date | Days | Shadow Rows | Matched | Sign Agreement | Pass? |
|------|------|-------------|---------|----------------|-------|
| | 7 | | | | |
| | 7 | | | | |
| | 14 (final) | | | | |

## Task Overlap

**Denominator:** |PR5_keys ∪ rule_keys| where key = (user_id, topic, category).  
**Formula:** Jaccard similarity of correction sets from platform attempts vs manual reviews.

| Date | Days | PR5 Tasks | Rule Tasks | Overlap | Overlap % | Pass? |
|------|------|-----------|------------|---------|-----------|-------|
| | 14 (final) | | | | | |

## Outlier Review

Outliers are shadow rows where |proposed_delta_db| > 15 (exceeds the ±15 db cap).
Expected: 0. Any outlier requires investigation before proceeding.

| Attempt ID | Topic ID | proposed_delta_db | Investigation |
|------------|----------|-------------------|---------------|
| | | | |

## Final Decision

- [ ] Sign agreement ≥ 80%: **PASS / FAIL**
- [ ] Task overlap ≥ 60%: **PASS / FAIL**
- [ ] No material outliers: **PASS / FAIL**
- [ ] Approved to proceed to PR8 (live canary): **YES / NO**

**Decision made by:** `______________________________`  
**Date:** `______________________________`  
**14-day window:** `____________` to `____________`
