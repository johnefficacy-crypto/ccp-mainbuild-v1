# PR9: Approval Request — Bounded Mastery Live Canary

**Type:** Evidence aggregation and approval request  
**Prerequisite:** PRs 2–8 complete; canary plan (PR8) executed  
**Status:** Pending

**This PR must not change the Render feature flag.**  
The operator performs any eventual flag transition separately, after this PR
is approved and merged.

## Evidence Summary

### Shadow Gate (PR7)

| Metric | Required | Actual | Pass? |
|--------|----------|--------|-------|
| Sign agreement (14d) | ≥ 80% | | |
| Task overlap (14d) | ≥ 60% | | |
| Material outliers | 0 | | |

Attach: `pr7_shadow_gate_results.md` and raw `--json` outputs.

### Canary Run (PR8)

| Metric | Required | Actual | Pass? |
|--------|----------|--------|-------|
| Live vs shadow sign agreement | ≥ 95% | | |
| Outliers (delta > 15 db) | 0 | | |
| Mastery-audit idempotency violations | 0 | | |
| Correction-task duplicate violations | 0 | | |

**Canary SHA:** `______________________________`  
**Canary scope:** `______________________________`  
**Canary duration:** `______` attempts over `______` days

Attach: SQL query outputs from PR8 pre/post queries.

### System Invariants (PR6)

- [ ] Source-based writer guard confirmed (409 for platform + breakdowns)
- [ ] Correction-preview classification parity confirmed
- [ ] Deterministic correction categories confirmed
- [ ] Null-selection behavior confirmed
- [ ] Shadow idempotency confirmed
- [ ] Automatic scheduler drain confirmed (PR1)
- [ ] No live-table mutation in shadow mode confirmed
- [ ] Compatibility-row parity confirmed

## Approvals Required

| Approver | Role | Status | Date |
|----------|------|--------|------|
| | Engineering lead | ☐ Approved | |
| | Product owner | ☐ Approved | |
| | On-call operator | ☐ Approved | |

## Post-Approval Steps (operator, not in this PR)

1. Confirm all approvers have signed off above.
2. Set `FF_MOCK_MASTERY_WRITES=live` on Render.
3. Redeploy backend.
4. Verify first live attempt: `user_topic_mastery_audit` receives a row with
   `reason='mock_submit'`.
5. Monitor error rate for `mock:sweeper` for 1 hour.

## Rollback

If issues arise after going live, execute rollback per
`docs/ops/pr8_live_canary_plan.md § Rollback Procedure`.
