---
audit_type: p7_partial_run
date: 2026-07-02
candidate_sha: 9b0c96ed82f8427049c838ee22b7147f5bdd151e
sha_verified: "Render deployed SHA B == candidate SHA A (confirmed at run time)"
ff_mock_mastery_writes: shadow
outcome: CODE-FIX REQUIRED — Gate A BLOCKED
next_action: merge PR #840, re-deploy, re-run Gate A on preserved staging fixtures
---

# P7 Partial Candidate Revalidation — 2026-07-02

**Candidate SHA:** `9b0c96ed82f8427049c838ee22b7147f5bdd151e`
**Render deployed SHA:** confirmed B == A
**FF_MOCK_MASTERY_WRITES:** `shadow` (active throughout)
**Outcome:** CODE-FIX REQUIRED — Gate A schema mismatch blocks full PASS

---

## 12 Start Gates — All PASS at candidate SHA

| Gate | Description | Result |
|------|-------------|--------|
| 1 | Deployed SHA pinned and confirmed | PASS |
| 2 | `FF_MOCK_MASTERY_WRITES=shadow` active | PASS |
| 3 | Topology reachable (API + DB) | PASS |
| 4 | 36-file fingerprint manifest present | REFERENCE ONLY — NOT RECOMPUTED at this SHA |
| 5 | Scheduler running, no stuck jobs | PASS |
| 6 | Migration 181 applied | PASS |
| 7 | `FF_MOCK_MASTERY_LIVE_USER_IDS` populated (≥1 named user) | PASS |
| 8 | Topic-linked attempt reachable | PASS |
| 9 | Allowlist resolution (`live` → `shadow` for non-allowlisted users) | PASS |
| 10 | Shadow write path reachable (attempt derivation API) | PASS |
| 11 | Correction parity path reachable | PASS |
| 12 | Live-audit-compare path reachable | PASS |

> **Gate 4 NOTE:** The 36-file fingerprint (`f2ee2c40…`) is a reference digest computed at a
> prior SHA. It was NOT recomputed at SHA `9b0c96ed`. Gate 4 is REFERENCE ONLY and must be
> recomputed and attested at the final fixed SHA before T0 / `window_start` is set.

---

## Checklist A–J Results

| Item | Description | Result |
|------|-------------|--------|
| A | `review_mock` writes accepted values to `mock_tests` | **BLOCKED — schema mismatch** |
| B | Shadow write idempotency (no duplicate shadow rows) | PASS |
| C | Mastery flag pinning (non-cancelled job read before re-resolve) | PASS |
| D | Classification readiness gate (mastery never runs with null error_types) | PASS |
| E | Correction-parity query covers unanswered-only attempts | PASS |
| F | Shadow-replay exit 0 (≥20 attempts AND ≥50 topic decisions) | INSUFFICIENT DATA (≥20 attempts confirmed; topic decisions = 3 at run time, below ≥50 threshold) |
| G | Live-audit-compare PASS (sign_agreement ≥95%, delta_mismatch = 0) | INSUFFICIENT DATA (decision_count = 3) |
| H | Scheduler drain confirmed (cross-ref P6 audit) | PASS (OPERATOR PASS 2026-07-01; no routine rerun needed) |
| I | No jobs stranded `running` after archive race | CODE-FIXED (PR #834, F3); live staging validation pending |
| J | Allowlist downgrades `live` → `shadow` for non-allowlisted users | PASS |

---

## Gate A Detail — BLOCKED

**What was tested:**

| Test | Expected | Actual |
|------|----------|--------|
| POST `review` with `topic_breakdowns` payload | 409 | 409 ✓ |
| POST `review` with `notes` only (notes-only path) | 200; `review_state` unchanged | 200; `review_state` unchanged ✓ |
| POST `review` with `review_status: "reviewed"` | 200; `review_state = "reviewed"` in DB | 500 ✗ (schema mismatch) |

**Root cause:** `canonical.py::review_mock` writes `review_status` to `mock_tests`, but the DB
column is named `review_state`. The route also writes `reviewed_at` which does not exist as a
column in the schema. The accepted state values (`unreviewed|reviewed|correction`) are stale —
the canonical schema values are `scheduled|unreviewed|reviewed|correction_drafted`.

**Code fix (PR #840, branch `claude/brave-maxwell-kywecs`):**
- API field `review_status` is retained (public contract unchanged).
- Platform path and non-platform path both map `review_status` → DB column `review_state`.
- `reviewed_at` write removed entirely; only `updated_at` is updated.
- Accepted values updated to `scheduled|unreviewed|reviewed|correction_drafted`.
- Explicit `review_status: null` is null-guarded — does NOT write `review_state: null`
  (NOT NULL constraint protection).
- File: `app/backend/app/api/canonical.py` (`MockReviewBody` + `review_mock`).
- Tests: `app/backend/tests/study_os/test_mock_review.py` (3 assertion fixes + 4 new regression
  tests: null-guard, correction_drafted acceptance, platform null-guard, platform correction_drafted).

---

## Gate F / G Context

At the 2026-07-02 run, `decision_count = 3` shadow decisions existed in the DB for the test
attempt. Both gates require a higher population:
- Gate F exit 0: ≥20 submitted attempts AND ≥50 topic decisions.
- Gate G: sign_agreement and delta_mismatch are only meaningful with sufficient data.

These gates are INSUFFICIENT DATA, not FAIL. They should be re-evaluated after the 14-day
shadow window accumulates production-scale data.

---

## Staging Fixtures — PRESERVE UNTIL GATE A RE-RUN PASSES

| Fixture | ID |
|---------|----|
| Mock template | `f753a9fc-cdf8-489c-b560-5c0ac5d431b4` |
| Attempt (use for Gate A re-run) | `60b14100-02eb-40fa-a1f0-88a43a48b315` |
| Compat mock row | `e07efb59-049d-4c64-8e16-243019297a51` |

Do NOT delete these fixtures until the Gate A re-run produces a clean PASS on the fixed SHA.

---

## Next Steps for Operator

1. Await PR #840 merge to `main`.
2. Deploy the merged `main` SHA to staging. Record candidate SHA A′; confirm Render B == A′.
3. With `FF_MOCK_MASTERY_WRITES=shadow` and `FF_MOCK_MASTERY_LIVE_USER_IDS` populated:
   - POST `/api/study/mocks/60b14100-02eb-40fa-a1f0-88a43a48b315/review` with
     `{"review_status": "reviewed"}` — expect HTTP 200 and `review_state = "reviewed"` in DB.
   - POST with `{"review_status": null, "notes": "note"}` — expect HTTP 200,
     `review_state` unchanged, `notes` updated.
4. If Gate A PASS, re-run the full A–J checklist and record results in a new dated audit.
5. Recompute the 36-file fingerprint at the deployed SHA A′ (from `f2ee2c40…` reference);
   attest the per-file digest. This is the T0 / `window_start` baseline — do NOT use the
   reference hash blindly.
6. Record `window_start` (UTC). T0 starts the 14-day P8 shadow window.

**T0 has not occurred. Do not set `window_start` until all 7 prerequisites in
`docs/ops/distance-to-release.md` hold simultaneously.**
