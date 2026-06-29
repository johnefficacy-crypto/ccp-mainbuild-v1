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

The table below lists selected Lane-A PRs (mastery validation path) that
merged after the PR-6 inspection baseline SHA
(`ba3ea3516f10d07d4708a12942e03162d2f2da50`) and modified files now in the
v2 fingerprint set. **This is not an exhaustive diff of every manifest
path:** other PRs in this range also touched manifest files for unrelated
reasons (e.g. PR #778 onboarding-priors modified `api/study_os.py`; a
security hardening commit modified `api/canonical.py`). The authoritative
record of what changed is `git diff ba3ea35..c9c44a9e -- <manifest-path>`.

| PR | Files changed in fingerprinted set (mastery path) | Merge time (UTC) |
|----|---------------------------------------------------|-----------------|
| #723 shadow analysis redesign | `tools/mastery_shadow_analysis/shadow_analysis.py` | 2026-06-20T07:41:05Z |
| #726 correction atomicity fix + migration 182 | `mastery_writer.py`, `mocks.py`, `migrations/182_mock_correction_draft_atomic_rpcs.sql` | 2026-06-20T07:48:11Z |
| #745 error-pattern schema fix | `mastery_engine/error_patterns.py`, `mastery_engine/schemas.py`, `mastery_writer.py` | 2026-06-21T15:36:02Z |
| #746 per-user allowlist + effective-mode resolver | `study_os/mock_engine.py`, `mastery_writer.py` | 2026-06-21T15:36:31Z |
| #753 pinned-mode + A4 sync-submit fix | `api/mock_engine.py`, `study_os/mock_engine.py` | 2026-06-21T19:14:59Z |

The PR-6 inspection fingerprint
(`6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a`) is
superseded. The v2 fingerprint manifest boundary is defined at
`docs/ops/mastery_validation_fingerprint_manifest_v2.txt` (32 files;
30 previous + `MockAttemptShell.jsx` + `attemptEventBus.js`).

**FREEZE PENDING — original blocking bugs fixed, but the v2 boundary is NOT
yet closed (PR #796 review found open telemetry-validity defects):**
- `time_analytics.py` read `created_at` but DB writes `occurred_at` (and
  read `question_id` top-level instead of from `payload` JSONB) — all
  production events were skipped; dwell fell back to `time_spent_sec`.
  Fixed and merged: PR #795 (`fix/time-analytics-v2`).
- `MockAttemptShell.jsx` did not emit `question.visited` for question 1
  on initial load (visit effect ran before `attempt` populated
  `questions_ref`). Fixed and merged: PR #793 (`fix/mock-attempt-first-visit`).

Still-open blockers before the boundary may be FROZEN (see the
telemetry-quality gate below and prerequisite step 2):
- **[P0]** `attemptEventBus._flushBeacon()` posts via `navigator.sendBeacon`
  with no `Authorization` header; the events endpoint requires
  `get_current_user` (401), so visibility-hidden/unmount batches — including
  `question.visited` anchors — are dropped after `splice(0)`. `_flush()` also
  never checks `response.ok` and discards on 401/409/5xx.
- **[P0]** `compute_dwell_times()` applies the `time_spent_sec` fallback via
  `setdefault` BEFORE the `len(by_q) < len(responses)` check, so partial event
  coverage never emits the documented `partial event coverage; fallback
  applied` warning required by `docs/mock_engine/attempt_analytics.md`.
- **[P1]** Manifest boundary is not closed over `core/auth.py` (event-batch
  acceptance) or frontend `lib/supabase.js` (token source); either can change
  ingestion without changing the fingerprint.

Pre-fix reference hash at `main @ c9c44a9e` (32 files; bugs present):
`96dd2a67756d7af4837daa68c495c8ebef88b2bb5d1b64bf1206c1720b907a4b`

Reference fingerprint at `main @ 1679adb8` (current 32-file boundary) — this
is NOT the window_start hash; the freeze hash must be recomputed at a new
post-fix SHA after the boundary is closed and the P0/P1 defects clear:
`b7394b79e00dc320705a4ccb0380afb2b0275f6cf9f0289f07d80e7ba0c3bc2b`

---

## Prerequisites (all required before window opens)

Steps 1–2 are code-level and can be completed independently of deployment.
Steps 3–8 are sequential and each depends on those above it.

1. ✅ **Lane A code merges (DONE — 2026-06-21):** User allowlist /
   effective-mode (PR #746, PR #753) and error-pattern writer / schema
   remediation (PR #745) merged to `main`.
2. **Freeze the v2 fingerprint manifest (FREEZE PENDING — boundary not yet
   closed):** Current boundary is 32 files (20 original + `attempt_analytics`
   7 + event-backend 3 + frontend event producers 2: `MockAttemptShell.jsx`,
   `attemptEventBus.js`). The two originally-blocking bug fixes are merged
   (PR #795 `time_analytics`; PR #793 `MockAttemptShell` first-visit), and a
   reference fingerprint was computed at `main @ 1679adb8`
   (`b7394b79e00dc320705a4ccb0380afb2b0275f6cf9f0289f07d80e7ba0c3bc2b`).
   This is NOT yet the freeze hash. Before FROZEN (PR #796 review): (i) fix or
   explicitly gate the P0 event-delivery (beacon auth/retry) and P0 partial-
   fallback reporting defects; (ii) close the boundary over `core/auth.py` and
   frontend `lib/supabase.js` (operator-approved manifest expansion) and
   recompute; (iii) commit a per-file SHA-256 attestation (or a CI check that
   recomputes the digest at the pinned SHA). Then recompute the freeze hash at
   the new post-fix `main` SHA and record it here.
3. ✅ **Migration 182 deployment (DONE — 2026-06-29):** RPC presence and
   privilege matrix: PASS (operator validated). Three RPCs
   (`ensure_mock_correction_drafts`, `ensure_mock_correction_draft`,
   `replace_manual_mock_correction_drafts`) confirmed SECURITY DEFINER,
   service_role-only; anon / authenticated cannot EXECUTE.
4. **PR-6 clean operator run (OPERATOR RERUN PENDING):** Run the full
   12-gate PR-6 operator session on one pinned SHA; confirm Gate 9
   passes (allowlist deployed with named user(s) in
   `FF_MOCK_MASTERY_LIVE_USER_IDS`) and `FF_MOCK_MASTERY_WRITES=shadow`
   for the run.
5. **Render SHA confirmation:** Operator confirms Render deployed SHA
   (B) matches the approved candidate main SHA (A).
6. **FF confirmation:** Confirm `FF_MOCK_MASTERY_WRITES=shadow`
   continuously from deploy time.
7. **Establish window_start:** Record exact UTC deploy timestamp as
   `window_start`. Only after steps 3–6 are complete.
8. **Compute baseline fingerprint (fail-closed):** From repo root at
   the confirmed `window_start` SHA, run:

   ```bash
   set -euo pipefail
   readarray -t _files < <(grep -v '^#' docs/ops/mastery_validation_fingerprint_manifest_v2.txt | grep -v '^$')
   _expected=32
   _actual=${#_files[@]}
   [[ $_actual -eq $_expected ]] || { echo "ERROR: expected $_expected files, got $_actual" >&2; exit 1; }
   for _f in "${_files[@]}"; do
     [[ -f "$_f" ]] || { echo "ERROR: missing $_f" >&2; exit 1; }
   done
   sha256sum "${_files[@]}" | sha256sum
   ```

   Record hash here and in the window record below.

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

### telemetry-quality gate (fail-closed — PR #796 review)

The replay gates above prove deterministic replay, NOT that classifications
were derived from the documented primary event source. Without these, the
window can PASS while validating dwell/classification inputs that silently
fell back to `mock_attempt_responses.time_spent_sec`. All must hold:

| Metric | Required | Actual |
|--------|----------|--------|
| events_used (per attempt) | > 0 | _____ |
| visit-event coverage (questions with a `question.visited` anchor) | 100.0% | _____ |
| fallback_question_count (dwell from `time_spent_sec`) | 0 | _____ |
| event ingest rejection count (401/409/5xx on `/events`) | 0 | _____ |
| beacon/fetch delivery-success rate | 100.0% | _____ |

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
