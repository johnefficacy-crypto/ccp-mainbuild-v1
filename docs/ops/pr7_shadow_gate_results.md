---
owner: ops
status: not_started
verdict: START_CONDITION_NOT_MET
checked_date: 2026-06-20
related_audit: docs/audits/mastery-shadow-14day-gate-2026-06-20.md
---

# PR7: 14-Day Mastery Shadow Gate

**Type:** Operator evidence
**Status:** NOT STARTED — BLOCKED ON PR-6

---

## Start-Condition Assessment (2026-06-20)

The 14-day shadow observation window has not opened. All three conditions
below must be true before the window can start.

| Condition | Status | Notes |
|-----------|--------|-------|
| PR-6 PASS verdict | **NOT MET** | PR-6 gate failed at Gate 9 (live canary user allowlist not deployed). Verdict: "DO NOT PROCEED TO LIVE." See `docs/ops/pr6_final_candidate_revalidation.md` and `docs/audits/2026-06-19-final-candidate-revalidation.md`. |
| `FF_MOCK_MASTERY_WRITES=shadow` confirmed in deployed environment | **OPERATOR PENDING** | Cannot be verified without Render dashboard access. |
| Validated baseline SHA deployed and confirmed A==B | **OPERATOR PENDING** | Render deployed SHA has not been operator-confirmed. |

Because PR-6 did not pass, the start condition is not met and the window
has not started. No threshold evaluation has occurred.

---

## Candidate Change Since PR-6 Inspection

Two code-level PRs merged after the PR-6 inspection baseline SHA
(`ba3ea3516f10d07d4708a12942e03162d2f2da50`). Both modified files in the
validation fingerprint set:

| PR | Files changed in fingerprinted set | Merge time (UTC) |
|----|-----------------------------------|-----------------|
| #723 shadow analysis redesign | `tools/mastery_shadow_analysis/shadow_analysis.py` | 2026-06-20T07:41:05Z |
| #726 correction atomicity fix | `app/backend/app/study_os/mastery_writer.py`, `app/backend/app/study_os/mocks.py` | 2026-06-20T07:48:11Z |

This means the PR-6 inspection fingerprint
(`6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a`) is
superseded. No new baseline fingerprint will be established until
`docs/ops/mastery_validation_fingerprint_manifest_v2.txt` is created and
frozen (see Prerequisites below). Once all prerequisites are met, the
operator must compute a new baseline fingerprint using the files listed in
that manifest at the approved candidate SHA and record it here before
starting the clock.

---

## Prerequisites (all required before window opens)

Complete in order — each step depends on those above it.

1. **Lane A code merges (blocking):** The user allowlist /
   effective-mode implementation PR and the error-pattern writer /
   schema remediation PR must both merge to `main` before any
   fingerprint manifest is frozen.
2. **Migration 182 deployment:** Dry-run migration 182 with
   `BEGIN` / `ROLLBACK`; confirm anon / authenticated roles cannot
   `EXECUTE` the three RPCs; apply to the target environment.
3. **Freeze the v2 fingerprint manifest:** Create
   `docs/ops/mastery_validation_fingerprint_manifest_v2.txt` listing
   all safety-critical runtime and migration files, including the
   allowlist, error-pattern, and migration 182 files added in steps 1–2.
   This manifest must be approved before any baseline fingerprint is
   computed.
4. **PR-6 clean operator run:** Run the full 12-gate PR-6 operator
   session on one pinned SHA; confirm Gate 9 passes (allowlist deployed
   and verified) and `FF_MOCK_MASTERY_WRITES=shadow` for the run.
5. **Render SHA confirmation:** Operator confirms Render deployed SHA
   (B) matches the approved candidate main SHA (A).
6. **FF confirmation:** Confirm `FF_MOCK_MASTERY_WRITES=shadow`
   continuously from deploy time.
7. **Establish window_start:** Record exact UTC deploy timestamp as
   `window_start`. Only after the above is complete.
8. **Compute baseline fingerprint:** Using the files listed in
   `docs/ops/mastery_validation_fingerprint_manifest_v2.txt` at the
   confirmed `window_start` SHA; record hash here and in the window
   record below.

---

## Gate Thresholds

All thresholds must pass before the PR-8 bounded live-canary plan becomes executable.
Do not use removed metrics (sign agreement, task overlap) — they are
invalid and were removed by PR-5A.

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

### Additional PASS criteria (all must hold)

- [ ] Zero live audit rows for window attempt IDs (verify: no row in
  `user_topic_mastery_audit` for any attempt_id in the window)
- [ ] Zero persisted platform correction rows for window attempt IDs
  (verify: no `mock_correction_tasks` row with `state=drafted` for
  platform attempts in window)
- [ ] Validation fingerprint unchanged throughout window
- [ ] `FF_MOCK_MASTERY_WRITES=shadow` continuously (no off/live period)
- [ ] Window ≥ 14 full days

---

## REMOVED gates (invalid — do not use)

The following thresholds from earlier versions of this document are
**removed** because they relied on invalid comparators or cross-population
topic identity that is not available:

- ~~Sign agreement ≥ 80%~~ — no approved comparator in shadow mode
- ~~Task overlap ≥ 60%~~ — cross-origin topic identity unavailable
  (canonical UUID vs display label); metric not computable

---

## Window Record (operator to fill after window completes)

| Field | Value |
|-------|-------|
| window_start (UTC) | `______________________________` |
| window_end (UTC) | `______________________________` |
| window_duration | `______________________________` |
| Baseline SHA (A — main) | `______________________________` |
| Render deployed SHA (B) | `______________________________` |
| A == B confirmed | `______________________________` |
| Validation fingerprint at window_start | `______________________________` |
| Validation fingerprint at window_end | `______________________________` |
| Fingerprint stable throughout window | `______________________________` |
| `FF_MOCK_MASTERY_WRITES` log (no off/live periods) | `______________________________` |

---

## Weekly Run Log

Run CLI weekly during the window for early warning. Weekly results are
evidence only — final verdict uses the full 14-day window run.

| Date | Days | Attempts | Topic decisions | exact_match_pct | coverage_pct | Status |
|------|------|----------|-----------------|-----------------|--------------|--------|
| | 7 (early warning) | | | | | |
| | 14 or later (final) | | | | | |

### correction-parity weekly log

| Date | Days | Decisions | exact_parity_pct | Status |
|------|------|-----------|------------------|--------|
| | 14 (final) | | | |

---

## CLI Commands (operator to run from deployed environment)

```bash
# Weekly / final shadow-replay gate
NEXT_PUBLIC_SUPABASE_URL=<url> SUPABASE_SERVICE_ROLE_KEY=<key> \
  python tools/mastery_shadow_analysis/shadow_analysis.py \
    --json shadow-replay \
    --from-utc {window_start} \
    --to-utc {now_or_window_end}

# Weekly / final correction-parity gate
NEXT_PUBLIC_SUPABASE_URL=<url> SUPABASE_SERVICE_ROLE_KEY=<key> \
  python tools/mastery_shadow_analysis/shadow_analysis.py \
    --json correction-parity \
    --from-utc {window_start} \
    --to-utc {now_or_window_end}
```

Exit codes: 0 = valid result (PASS or FAIL), 2 = ERROR (fix and rerun),
3 = INSUFFICIENT_DATA (extend window), 4 = CORRUPT (investigate before
any verdict).

---

## Outlier Review

For each mismatch / missing / extra / invariant violation: record exact
attempt_id, topic_id, violation type, and disposition. Any unresolved
violation blocks PASS verdict.

| Attempt ID | Topic ID | Violation Type | Disposition |
|------------|----------|-----------------------|-------------|
| | | | |

---

## Evidence File Index

| Artifact | Location |
|----------|----------|
| shadow-replay JSON (14-day) | Attach to PR |
| correction-parity JSON (14-day) | Attach to PR |
| Weekly run JSON (each run) | Attach to PR |
| FF transition log | Attach to PR |
| Render deployed SHA proof | Attach to PR |
| Baseline fingerprint computation | Record in window record above |

---

## Final Decision

- [ ] shadow-replay: all thresholds pass (exit 0): **PASS / FAIL**
- [ ] correction-parity: exact_parity_pct = 100.0 (exit 0): **PASS / FAIL**
- [ ] All additional PASS criteria met: **PASS / FAIL**
- [ ] No unresolved outliers: **PASS / FAIL**
- [ ] PR-8 bounded live-canary plan is executable: **YES / NO**

Do NOT claim 14-day PASS without attaching the JSON output from a
completed operator run with DB credentials.
Do NOT claim live validation from shadow-mode runs.

**Decision made by:** `______________________________`
**Date:** `______________________________`
**14-day window:** `____________` to `____________`
