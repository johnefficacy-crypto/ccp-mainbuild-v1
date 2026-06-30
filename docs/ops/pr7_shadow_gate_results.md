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
`docs/ops/mastery_validation_fingerprint_manifest_v2.txt` (**35 files**;
30 previous + `MockAttemptShell.jsx` + `attemptEventBus.js` + the two
event-acceptance dependencies `core/auth.py` + `lib/supabase.js` + the
answer-write dependency `useAnswerSync.js`).

**FREEZE PENDING — all code/tooling blockers resolved; OPERATOR APPROVAL the
only remaining gate (PR #803 review).** Disposition of the PR #803 blockers:
- **[P0 RESOLVED]** Submit-time telemetry race — (a) `MockAttemptShell.doSubmit()`
  `await`s `eventBus.flushAndWait()` (time-bounded, ACK-gated) BEFORE POSTing
  `/submit`; (b) the backend idempotently recomputes analytics on late `/events`
  accepted within the grace window (`mock_attempt_events.py` →
  `compute_and_persist`), so a flush that does not fully drain is still
  reconciled. Fully closed, not merely mitigated. Regression:
  `MockAttemptShell.submitFlush.test.jsx`, `flushAndWait` unit tests, and
  `test_attempt_events` recompute tests.
- **[P1 RESOLVED]** Boundary closed over `useAnswerSync.js` (added; 34 → 35) and
  a transitive-dependency inclusion rule is documented in the manifest header.
- **[P1 RESOLVED]** Telemetry-quality gate is executable and authoritative —
  `shadow-analysis telemetry-quality` validates the PERSISTED
  `mock_attempt_summary.analytics_quality` snapshot (late events cannot mask the
  fallback used at submit), scoped to the exact `mock_mastery_shadow` population;
  metrics `fallback_engaged_question_count` (answered/marked fallback; untouched
  excluded), `events_used`, `attempts_missing_snapshot`, and `trailing_gap_count`
  (via the `attempt.submit_flush` final-sequence marker). Fail-closed; unit-tested.
- **[P2 RESOLVED]** `verify_mastery_fingerprint.sh` cross-checks the recorded
  digest across the manifest / pr7 / checklist AND requires a pinned SHA
  (`EXPECTED_SHA`, or `SKIP_SHA=1` for a content-only check).
- **[OPEN — OPERATOR ONLY]** PR #800 remains `CODE-FIXED / VALIDATION PENDING`
  (its three staging checks unchecked) and the 34 → 35 manifest expansion is
  PROPOSED pending operator approval. Per AGENTS.md the gate stays FREEZE PENDING
  until the operator validates #800 on staging and approves the boundary.

**Reference fingerprint (PR #803 branch, 35 files) — NOT the freeze /
window_start hash; re-pin to the post-merge main SHA at window_start:**
`52791ea8689be1e2bb8ad5b520f3c11642678da1b9edf52c573e27d572da0c45`

A per-file SHA-256 attestation is committed at
`docs/ops/mastery_validation_fingerprint_manifest_v2.attestation.txt`; verify
fail-closed with `bash scripts/verify_mastery_fingerprint.sh`. The freeze hash
must be recomputed (with the final boundary) once the blockers above clear and
operator approval is captured.

Superseded reference hashes (NOT window_start hashes):
`b7394b79e00dc320705a4ccb0380afb2b0275f6cf9f0289f07d80e7ba0c3bc2b` (`1679adb8`, 32 files, pre-#800);
`96dd2a67756d7af4837daa68c495c8ebef88b2bb5d1b64bf1206c1720b907a4b` (`c9c44a9e`, 32 files, bugs present)

---

## Prerequisites (all required before window opens)

Steps 1–2 are code-level and can be completed independently of deployment.
Steps 3–8 are sequential and each depends on those above it.

1. ✅ **Lane A code merges (DONE — 2026-06-21):** User allowlist /
   effective-mode (PR #746, PR #753) and error-pattern writer / schema
   remediation (PR #745) merged to `main`.
2. **Freeze the v2 fingerprint manifest (FREEZE PENDING — code/tooling closed;
   OPERATOR APPROVAL is the only remaining gate):** Boundary closed at 35 files
   (added event-acceptance deps `core/auth.py` + `lib/supabase.js` and answer-
   write dep `useAnswerSync.js`); reference fingerprint + per-file attestation
   regenerated (`52791ea8689be1e2bb8ad5b520f3c11642678da1b9edf52c573e27d572da0c45`).
   This is NOT yet the freeze hash. PR #803 review disposition: (i) ✅ submit/
   late-event race fixed via an awaited pre-submit ACKed flush AND backend
   idempotent recompute on late `/events`; (ii) ✅ boundary closed over
   `useAnswerSync.js` + a transitive-dependency rule; (iii) ✅ telemetry-quality
   gate is snapshot-based + shadow-scoped with engaged-fallback population and a
   trailing-loss marker, tested; (v) ✅ `verify_mastery_fingerprint.sh` hardened
   (cross-document digest + required `EXPECTED_SHA`). (iv) ⛔ OPERATOR PENDING —
   PR #800 staging validation + boundary approval. After approval: re-pin the
   fingerprint to the post-merge main SHA and record it here.
3. **Migration 182 deployment (OPERATOR PENDING):** Dry-run migration
   `182_mock_correction_draft_atomic_rpcs.sql` with `BEGIN` / `ROLLBACK`;
   confirm anon / authenticated roles cannot `EXECUTE` the three RPCs
   (`ensure_mock_correction_drafts`, `ensure_mock_correction_draft`,
   `replace_manual_mock_correction_drafts`); apply to the target environment.
   **Durable evidence required before marking DONE** (all fields must be
   recorded in a dated audit document):
   - Target environment (staging / prod)
   - Reviewed/deployed SHA at time of apply
   - UTC run time
   - `schema_migrations` history result confirming 182 applied (e.g. `SELECT * FROM schema_migrations WHERE version = '182'`)
   - Exact RPC signatures returned by `pg_proc` / `\df` for all three functions
   - SECURITY DEFINER owner and `search_path` for each function
   - Effective EXECUTE privileges (grantee query output — not a prose assertion)
   - Dry-run `BEGIN` / `ROLLBACK` output OR rollback-safe smoke-test confirming no data mutation
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
   _expected=35
   _actual=${#_files[@]}
   [[ $_actual -eq $_expected ]] || { echo "ERROR: expected $_expected files, got $_actual" >&2; exit 1; }
   for _f in "${_files[@]}"; do
     [[ -f "$_f" ]] || { echo "ERROR: missing $_f" >&2; exit 1; }
   done
   sha256sum "${_files[@]}" | sha256sum
   # Or simply: bash scripts/verify_mastery_fingerprint.sh
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
fell back to `mock_attempt_responses.time_spent_sec`. All must hold.

**Implemented and executable** via `shadow-analysis telemetry-quality`
(`--from-utc … --to-utc …` or `--days N`, `--min-attempts 20` for the real
window). It validates the **persisted `mock_attempt_summary.analytics_quality`
snapshot** (what the frozen classifications/dwell actually used at submit, so
late events cannot hide submit-time fallback), scoped to the **exact
`mock_mastery_shadow` population** (not all submitted attempts). The engaged
population (answered or marked questions; untouched excluded) is defined by the
backend at submit via `fallback_engaged_question_count`. Trailing loss is
detected from the `attempt.submit_flush` marker: `trailing_gap` = declared
`final_sequence_no` − max observed client `sequence_no`. PASS requires every one
of these aggregate metrics to be 0:

| Metric (`telemetry-quality`) | Required |
|--------|----------|
| `attempts_missing_snapshot` (every shadow attempt has a persisted snapshot) | 0 |
| `snapshots_missing_field` (snapshot carries `fallback_engaged_question_count`) | 0 |
| `attempts_without_events` (snapshot `events_used` > 0) | 0 |
| `fallback_engaged_question_count` (answered/marked question fell back) | 0 |
| `attempts_missing_marker` (every attempt emitted `attempt.submit_flush`) | 0 |
| `trailing_gap_count` (declared final seq − max observed seq) | 0 |

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
