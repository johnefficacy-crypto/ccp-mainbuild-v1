---
owner: ops
status: insufficient_data
run_date: 2026-06-20
verdict: INSUFFICIENT_DATA
pr: docs/mastery-shadow-14-day-gate
related_ops_doc: docs/ops/pr7_shadow_gate_results.md
fingerprint_start: 95d78f8ac61093028195c2372e7c96c7ff2c8e034a36aea19023e83b211006cf
fingerprint_end: 95d78f8ac61093028195c2372e7c96c7ff2c8e034a36aea19023e83b211006cf
---

# Mastery Shadow 14-Day Gate Audit — 2026-06-20

**Type:** Operator evidence + docs (immutable dated record)
**Run date:** 2026-06-20
**Branch:** `docs/mastery-shadow-14-day-gate`
**Verdict:** INSUFFICIENT_DATA

---

## Verdict

```
INSUFFICIENT_DATA.
14-DAY SHADOW GATE CANNOT OPEN.
PR-6 START CONDITION NOT MET.
WINDOW NEVER STARTED.
LIVE CHANGE REQUIRES SEPARATE APPROVAL.
```

This is not a FAIL. INSUFFICIENT_DATA means the required preconditions were not
in place to conduct the gate; no threshold was evaluated against live data.

---

## Start Condition Check

| Condition | Status | Evidence |
|-----------|--------|----------|
| PR-6 PASS verdict required | **NOT MET** | PR-6 gate FAILED at Gate 9 (2026-06-19); verdict: "DO NOT PROCEED TO LIVE. START GATE FAILED AT GATE 9: ALLOWLIST NOT DEPLOYED." See `docs/ops/pr6_final_candidate_revalidation.md` and `docs/audits/2026-06-19-final-candidate-revalidation.md`. |
| Window must not start before PR-6 | **NOT MET** | Follows from PR-6 FAIL. |

---

## Window

| Field | Value |
|-------|-------|
| window_start (UTC) | NOT SET — start condition not met |
| window_end (UTC) | NOT SET |
| window_duration | 0 days (minimum required: 14) |
| `FF_MOCK_MASTERY_WRITES = shadow` continuously | INSUFFICIENT DATA — Render logs not accessible from agent environment |

---

## SHA Log

Listing all main-branch SHAs deployed since the PR-6 gate check. Render deploy
timestamps for each SHA are **OPERATOR PENDING** (Render API not accessible from
agent environment).

| Event | SHA (GitHub merge commit) | Time (UTC) | Fingerprint impact |
|-------|--------------------------|------------|--------------------|
| PR-6 gate inspection point | `ba3ea3516f10d07d4708a12942e03162d2f2da50` | 2026-06-19 (operator record) | Baseline fingerprint `6ddce48c…` |
| PR #724 merged (CMS CTA removal — docs/frontend) | `e9d8b10…` | 2026-06-19T19:16:42Z | None — no fingerprinted files changed |
| PR #723 merged (shadow analysis redesign) | `ef8e9f5…` | 2026-06-20T07:41:05Z | **YES** — `shadow_analysis.py` in fingerprinted set |
| PR #726 merged (correction atomicity fix) | `dce84d198a3a82e0d5de87a6bff512afe10599c8` | 2026-06-20T07:48:11Z | **YES** — `mastery_writer.py` and `mocks.py` in fingerprinted set |
| PR #725 merged (PR-6 gate docs-only) | `d8d19438e9eba1bb6c12c8a819e7d6a77173dd6e` | 2026-06-20T07:57:07Z | None — docs-only |

Current HEAD at run time: `d8d19438e9eba1bb6c12c8a819e7d6a77173dd6e`

Render SHA B (deployed to production) is OPERATOR PENDING for each of the above.

---

## FF Log

`FF_MOCK_MASTERY_WRITES` transitions during the hypothetical window period cannot
be confirmed because Render environment variable history is not accessible from
the agent container.

Known state from checklist (2026-06-20):
- `FF_MOCK_MASTERY_WRITES=live` is **BLOCKED** (allowlist not deployed)
- Effective flag state during any shadow writes: unknown from this environment

Per gate spec: "If FF continuity cannot be proven from Render logs: INSUFFICIENT_DATA".

---

## Validation Fingerprint

The fingerprint covers these 18 files:

```
app/backend/app/study_os/mastery_writer.py
app/backend/app/study_os/attempt_classification_readiness.py
app/backend/app/study_os/attempt_derivation.py
app/backend/app/study_os/mastery_engine/__init__.py
app/backend/app/study_os/mastery_engine/correction_tasks.py
app/backend/app/study_os/mastery_engine/error_patterns.py
app/backend/app/study_os/mastery_engine/mastery_delta.py
app/backend/app/study_os/mastery_engine/schemas.py
app/backend/app/study_os/mastery_engine/service.py
app/backend/app/study_os/correction_policy.py
app/backend/app/study_os/mock_engine.py
app/backend/app/study_os/mocks.py
app/backend/app/api/mock_engine.py
app/backend/app/api/canonical.py
app/backend/app/api/study_os.py
app/backend/app/api/admin_study_os.py
tools/mastery_shadow_analysis/shadow_analysis.py
app/supabase/migrations/181_mock_correction_tasks_uniqueness.sql
```

Computed with `sha256sum <files> | sha256sum`:

| Point | SHA | Combined fingerprint |
|-------|-----|---------------------|
| PR-6 baseline (2026-06-19) | `ba3ea3516f10d07d4708a12942e03162d2f2da50` | `6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a` |
| Run start (2026-06-20) | `d8d19438e9eba1bb6c12c8a819e7d6a77173dd6e` | `95d78f8ac61093028195c2372e7c96c7ff2c8e034a36aea19023e83b211006cf` |
| Run end (2026-06-20, docs-only PR) | `d8d19438e9eba1bb6c12c8a819e7d6a77173dd6e` | `95d78f8ac61093028195c2372e7c96c7ff2c8e034a36aea19023e83b211006cf` |
| **Stable start→end (this PR)?** | — | **YES** (docs-only; no code changed in this PR) |
| **Stable PR-6 baseline → current?** | — | **NO** — fingerprint changed between PR-6 inspection and current HEAD |

### Files changed within the fingerprinted set (PR-6 baseline → current HEAD)

| File | Changed by | Change type |
|------|-----------|-------------|
| `app/backend/app/study_os/mastery_writer.py` | PR #726 | Correction persistence atomicity + ownership guard |
| `app/backend/app/study_os/mocks.py` | PR #726 | Correction persistence atomicity |
| `tools/mastery_shadow_analysis/shadow_analysis.py` | PR #723 | Shadow analysis tool redesign (RB1-RB5) |

These are all validation-relevant per the gate spec. Any one of them would reset
the shadow clock if the window had started at the PR-6 baseline SHA.

---

## CLI Outputs (raw — sanitized: no keys/tokens present)

### shadow-replay — attempted 2026-06-20

Command attempted from agent environment:

```bash
PYTHONPATH=app/backend python3 tools/mastery_shadow_analysis/shadow_analysis.py \
  --json shadow-replay \
  --from-utc 2026-06-20T07:57:07Z \
  --to-utc 2026-07-04T07:57:07Z
```

Output:

```json
{
  "schema_version": 1,
  "command": "shadow_replay",
  "status": "ERROR",
  "error": "PREREQUISITE_MISSING",
  "detail": "attempt_derivation module not found. This command requires PR-4 (app/backend/app/study_os/attempt_derivation.py) to be present."
}
```

**Exit code: 2 (ERROR)**

Root cause: The CLI imports `from app.study_os import attempt_derivation`, which
triggers the full `app/study_os/__init__.py` import chain including
`mission_control.py` → `exam_eligibility/evaluator.py` → `cachetools` (not
installed in agent container). The attempt_derivation.py file exists at
`app/backend/app/study_os/attempt_derivation.py`; the error is an environment
dependency issue, not a missing file.

Note on window dates: The `--from-utc` / `--to-utc` values above are
hypothetical (PR-6 merge time to +14 days). These are NOT authoritative window
dates because the start condition was not met; they were supplied only to allow
the CLI to reach the environment check.

### correction-parity — attempted 2026-06-20

Command attempted from agent environment:

```bash
PYTHONPATH=app/backend python3 tools/mastery_shadow_analysis/shadow_analysis.py \
  --json correction-parity \
  --from-utc 2026-06-20T07:57:07Z \
  --to-utc 2026-07-04T07:57:07Z
```

Output:

```json
{
  "schema_version": 1,
  "command": "correction_parity",
  "status": "ERROR",
  "error": "PREREQUISITE_MISSING",
  "detail": "attempt_derivation module not found. This command requires PR-4 (app/backend/app/study_os/attempt_derivation.py) to be present."
}
```

**Exit code: 2 (ERROR)**

Same root cause as shadow-replay above.

### Disposition

Per gate spec: "exit 2 → ERROR: do not publish; fix the error and rerun."

This does not override the INSUFFICIENT_DATA verdict — the verdict is
INSUFFICIENT_DATA because the window never started, not because the CLI failed.
The CLI failure confirms the CLIs must be run from the deployed operator
environment (not the agent container), and that no usable gate data was produced.

---

## Threshold Comparison

No data produced; all thresholds are N/A.

### shadow-replay thresholds

| Metric | Required | Actual | Pass? |
|--------|----------|--------|-------|
| distinct_attempt_count | ≥ 20 | N/A | N/A |
| topic_decision_count | ≥ 50 | N/A | N/A |
| exact_match_pct | 100.0 | N/A | N/A |
| coverage_pct | 100.0 | N/A | N/A |
| missing_count | 0 | N/A | N/A |
| extra_count | 0 | N/A | N/A |
| mismatch_count | 0 | N/A | N/A |
| duplicate_key_count | 0 | N/A | N/A |
| invariant_violations | 0 | N/A | N/A |
| classification_not_ready_count | 0 | N/A | N/A |

### correction-parity thresholds

| Metric | Required | Actual | Pass? |
|--------|----------|--------|-------|
| decision_count | ≥ 10 | N/A | N/A |
| exact_parity_pct | 100.0 | N/A | N/A |

### Additional PASS criteria

| Criterion | Result |
|-----------|--------|
| Zero duplicate shadow keys | NOT CHECKED |
| Zero missing/extra/mismatch rows | NOT CHECKED |
| Zero classification_not_ready attempts | NOT CHECKED |
| Zero invariant violations | NOT CHECKED |
| Zero live audit rows for window attempt IDs | NOT CHECKED |
| Zero persisted platform correction rows for window attempt IDs | NOT CHECKED |
| Validation fingerprint stable throughout window | **BLOCKED** — fingerprint changed between PR-6 baseline and current HEAD |
| FF shadow continuously (no off/live period) | **INSUFFICIENT DATA** — Render logs not accessible |
| Window ≥ 14 full days | **FAILED** — 0 days elapsed |

---

## Outlier Table

No attempt IDs evaluated; no outliers to record.

| Attempt ID | Topic ID | Violation Type | Disposition |
|------------|----------|----------------|-------------|
| — | — | — | N/A |

---

## Weekly Runs

No weekly runs were conducted (window never started).

---

## Explicit Attestations

- No code changed in this PR.
- No feature flag changed (`FF_MOCK_MASTERY_WRITES` not touched).
- No production data mutated.
- No database writes performed.
- No live HTTP calls made.
- No secrets, tokens, or Authorization headers in any file.

---

## Next Steps (for operator)

1. **Gate 9 — allowlist implementation**: Deploy a per-user allowlist for `FF_MOCK_MASTERY_WRITES` scope. This is the only blocking item from PR-6. Without it, the canary plan cannot be executed safely.
2. **Repeat PR-6 full operator run**: Once allowlist is deployed, run all 12 gates in a live operator session. Confirm Gate 9 passes (allowlist found), Gate 12 passes (FF = shadow for run), all live phases P05–P10 pass.
3. **Record new baseline SHA and deploy timestamp**: The Render deployed SHA (B) must be confirmed A == B by operator. Record exact UTC timestamp as `window_start`.
4. **Run CLIs weekly**: From the operator environment with DB credentials, run `shadow-replay` and `correction-parity` with `--from-utc {window_start} --to-utc {now}` for early-warning monitoring.
5. **Run final 14-day gate**: At `window_start + 14 full days`, run both CLIs with `--from-utc {window_start} --to-utc {window_end}`. Capture JSON. Attach to next PR-7 attempt.
6. **Verify fingerprint stable**: Recompute `sha256sum <18 files> | sha256sum` at gate time. Must match the value recorded at `window_start`.
