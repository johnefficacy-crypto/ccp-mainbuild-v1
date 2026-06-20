---
owner: ops
status: insufficient_data
run_date: 2026-06-20
related_audit: docs/audits/mastery-shadow-14day-gate-2026-06-20.md
---

# PR7: 14-Day Mastery Shadow Gate Results

**Type:** Operator evidence + docs only
**Run date:** 2026-06-20
**Verdict:** INSUFFICIENT_DATA

---

## Verdict

```
INSUFFICIENT_DATA.
14-DAY SHADOW GATE CANNOT OPEN.
START CONDITION (PR-6 PASS) NOT MET.
LIVE CHANGE REQUIRES SEPARATE APPROVAL.
```

---

## Reasons for INSUFFICIENT_DATA

| Reason | Detail |
|--------|--------|
| Start condition | PR-6 gate FAILED at Gate 9 (live canary user allowlist not deployed, 2026-06-19). PR-6 PASS is a hard prerequisite. |
| Window never started | No valid 14-day shadow observation period; window_start and window_end cannot be set. |
| Window duration | 0 days — below the 14-day minimum. |
| Fingerprint unstable | Validation fingerprint changed between the PR-6 baseline SHA and current HEAD. PR #726 modified `mastery_writer.py` and `mocks.py`; PR #723 modified `shadow_analysis.py`. Any change to those files resets the shadow clock. |
| FF continuity unproven | `FF_MOCK_MASTERY_WRITES` shadow-mode continuity cannot be verified from this environment; no Render dashboard access. |
| CLI did not run | Both `shadow-replay` and `correction-parity` exited 2 (ERROR: PREREQUISITE\_MISSING) in the agent environment; backend Python dependencies and live DB credentials are required. |

---

## Gate Thresholds

All thresholds must pass before proceeding to PR8 (live canary plan).

### shadow-replay gate

| Metric | Required | Actual |
|--------|----------|--------|
| distinct_attempt_count | ≥ 20 | N/A — window not run |
| topic_decision_count | ≥ 50 | N/A — window not run |
| exact_match_pct | 100.0 | N/A — window not run |
| coverage_pct | 100.0 | N/A — window not run |
| missing_count | 0 | N/A — window not run |
| extra_count | 0 | N/A — window not run |
| mismatch_count | 0 | N/A — window not run |
| duplicate_key_count | 0 | N/A — window not run |
| invariant_violations | 0 | N/A — window not run |
| classification_not_ready_count | 0 | N/A — window not run |

### correction-parity gate

| Metric | Required | Actual |
|--------|----------|--------|
| decision_count | ≥ 10 | N/A — window not run |
| exact_parity_pct | 100.0 | N/A — window not run |

---

## REMOVED gates (invalid — do not use)

The following thresholds from the previous version of this document are
**removed** because they relied on invalid cross-population comparisons or
unapproved comparators:

- ~~Sign agreement ≥ 80%~~ — no approved comparator exists in shadow mode;
  use live-audit-compare during canary only.
- ~~Task overlap ≥ 60%~~ — cross-origin topic identity is unavailable
  (canonical UUID vs display label); metric is not computable.

---

## Validation Fingerprint

| Point | SHA | Fingerprint |
|-------|-----|-------------|
| PR-6 baseline (2026-06-19) | `ba3ea3516f10d07d4708a12942e03162d2f2da50` | `6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a` |
| Current HEAD (2026-06-20) | `d8d19438e9eba1bb6c12c8a819e7d6a77173dd6e` | `95d78f8ac61093028195c2372e7c96c7ff2c8e034a36aea19023e83b211006cf` |
| Fingerprint stable throughout window | — | **NO — fingerprint changed** |

Files that changed between PR-6 baseline and current HEAD (within the fingerprinted set):

- `app/backend/app/study_os/mastery_writer.py` — changed by PR #726 (atomic correction persistence)
- `app/backend/app/study_os/mocks.py` — changed by PR #726
- `tools/mastery_shadow_analysis/shadow_analysis.py` — changed by PR #723 (shadow analysis redesign)

---

## SHA + Deploy Log

| Event | SHA | Merge/deploy time (UTC) | Fingerprint change |
|-------|-----|------------------------|--------------------|
| PR-6 baseline (PR #721 merged) | `ba3ea3516f10d07d4708a12942e03162d2f2da50` | ≈2026-06-19 (operator captured) | — |
| PR #723 merged (shadow tool redesign) | `ef8e9f5d…` (merge SHA) | 2026-06-20T07:41:05Z | YES — shadow_analysis.py changed |
| PR #726 merged (correction atomicity) | `dce84d198a3a82e0d5de87a6bff512afe10599c8` | 2026-06-20T07:48:11Z | YES — mastery_writer.py + mocks.py changed |
| PR #725 merged (PR-6 gate docs) | `d8d19438e9eba1bb6c12c8a819e7d6a77173dd6e` | 2026-06-20T07:57:07Z | NO — docs-only |

Render deploy timestamps and SHA B (Render deployed SHA) are **OPERATOR PENDING** — not accessible from agent environment.

---

## FF Log

`FF_MOCK_MASTERY_WRITES` continuity record: **INSUFFICIENT_DATA — Render logs not accessible.**

The `FF_MOCK_MASTERY_WRITES=live` flag remains **BLOCKED** (see checklist). FF transition records cannot be confirmed from this environment.

---

## CLI Outputs

### shadow-replay (attempted 2026-06-20)

```bash
PYTHONPATH=app/backend python3 tools/mastery_shadow_analysis/shadow_analysis.py \
  --json shadow-replay \
  --from-utc 2026-06-20T07:57:07Z \
  --to-utc 2026-07-04T07:57:07Z
```

```json
{
  "schema_version": 1,
  "command": "shadow_replay",
  "status": "ERROR",
  "error": "PREREQUISITE_MISSING",
  "detail": "attempt_derivation module not found. This command requires PR-4 (app/backend/app/study_os/attempt_derivation.py) to be present."
}
```

**Exit code: 2 (ERROR).** The CLI requires the full backend Python environment (dependencies not installed in agent container) and live DB credentials. Per spec: exit 2 → do not publish final gate result; rerun from operator environment.

### correction-parity (attempted 2026-06-20)

```bash
PYTHONPATH=app/backend python3 tools/mastery_shadow_analysis/shadow_analysis.py \
  --json correction-parity \
  --from-utc 2026-06-20T07:57:07Z \
  --to-utc 2026-07-04T07:57:07Z
```

```json
{
  "schema_version": 1,
  "command": "correction_parity",
  "status": "ERROR",
  "error": "PREREQUISITE_MISSING",
  "detail": "attempt_derivation module not found. This command requires PR-4 (app/backend/app/study_os/attempt_derivation.py) to be present."
}
```

**Exit code: 2 (ERROR).** Same environment constraint as above.

---

## Outlier Table

No data: window never ran. Zero attempts evaluated.

| Attempt ID | Topic ID | Violation Type | Disposition |
|------------|----------|----------------|-------------|
| — | — | — | — |

---

## Pass Criteria Check

| Criterion | Result |
|-----------|--------|
| shadow-replay: exact_match_pct = 100.0 | NOT MET — window not run |
| shadow-replay: coverage_pct = 100.0 | NOT MET — window not run |
| correction-parity: exact_parity_pct = 100.0 | NOT MET — window not run |
| Zero duplicate shadow keys | NOT CHECKED |
| Zero missing/extra/mismatch rows | NOT CHECKED |
| Zero classification_not_ready attempts | NOT CHECKED |
| Zero invariant violations | NOT CHECKED |
| Zero live audit rows for window attempt IDs | NOT CHECKED |
| Zero persisted platform correction rows for window attempt IDs | NOT CHECKED |
| Validation fingerprint stable throughout window | **FAILED** — fingerprint changed (PR #723, PR #726) |
| FF shadow continuously | **INSUFFICIENT DATA** — Render logs not accessible |
| Window ≥ 14 days | **FAILED** — 0 days; window never started |

---

## Instructions (for future operator run)

Prerequisites before restarting the clock:

1. Deploy the live canary user allowlist PR (Gate 9 — currently BLOCKED; `FF_MOCK_MASTERY_WRITES` is global).
2. Clear PR-6: run the full 12-gate operator session, confirm Gate 9 passes and FF = shadow for the run.
3. Record the exact UTC deploy timestamp of the approved SHA as `window_start`.
4. Ensure no validation-relevant backend changes occur for 14 full days.
5. At weekly intervals (and at day 14), run from the deployed operator environment:

```bash
NEXT_PUBLIC_SUPABASE_URL=<url> SUPABASE_SERVICE_ROLE_KEY=<key> \
  python3 tools/mastery_shadow_analysis/shadow_analysis.py \
    --json shadow-replay \
    --from-utc {window_start} \
    --to-utc {window_end} \
    > shadow_replay_14d.json

NEXT_PUBLIC_SUPABASE_URL=<url> SUPABASE_SERVICE_ROLE_KEY=<key> \
  python3 tools/mastery_shadow_analysis/shadow_analysis.py \
    --json correction-parity \
    --from-utc {window_start} \
    --to-utc {window_end} \
    > correction_parity_14d.json
```

Exit codes: 0 = valid result (PASS or FAIL), 2 = ERROR (fix and rerun), 3 = INSUFFICIENT_DATA (extend window), 4 = CORRUPT (investigate before any verdict).

---

**Decision made by:** `______________________________`
**Date:** `______________________________`
**14-day window:** `____________` to `____________`

Do NOT claim 14-day PASS without attaching the JSON output from a completed operator run.
Do NOT claim live validation from shadow-mode runs.
