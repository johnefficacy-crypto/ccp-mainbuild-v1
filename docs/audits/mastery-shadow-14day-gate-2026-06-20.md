---
owner: ops
status: not_started
verdict: START_CONDITION_NOT_MET
checked_date: 2026-06-20
related_ops_doc: docs/ops/pr7_shadow_gate_results.md
---

# Mastery Shadow 14-Day Gate — Start-Condition Check — 2026-06-20

**Type:** Operator evidence + docs (immutable dated record)
**Checked:** 2026-06-20
**Branch:** `docs/mastery-shadow-14-day-gate`
**Verdict:** START_CONDITION_NOT_MET

This document records a **start-condition check**, not a completed gate
evaluation. No shadow observation window was opened, no thresholds were
evaluated, and no gate verdict (PASS / FAIL / INSUFFICIENT_DATA) applies
to this run.

---

## Verdict

```
START_CONDITION_NOT_MET.
14-DAY SHADOW OBSERVATION WINDOW NOT OPENED.
PR-6 PASS IS REQUIRED BEFORE THE WINDOW CAN START.
LIVE CHANGE REQUIRES SEPARATE APPROVAL.
```

---

## Start-Condition Check

| Condition | Status | Evidence |
|-----------|--------|----------|
| PR-6 PASS verdict | **NOT MET** | PR-6 gate stopped at Gate 9 (2026-06-19): no per-user allowlist deployed; verdict: "DO NOT PROCEED TO LIVE. START GATE FAILED AT GATE 9." See `docs/ops/pr6_final_candidate_revalidation.md`. |
| `FF_MOCK_MASTERY_WRITES=shadow` confirmed | **OPERATOR PENDING** | Render environment variable history not accessible from agent environment. |
| Render deployed SHA (B) confirmed A==B | **OPERATOR PENDING** | Render dashboard not accessible from agent environment. |

Because PR-6 did not pass, the shadow window has not started and no
threshold evaluation has occurred.

---

## Observation Window

| Field | Value |
|-------|-------|
| window_start (UTC) | NOT SET — start condition not met |
| window_end (UTC) | NOT SET |
| window_duration | N/A — window not started |
| 14-day duration criterion | NOT EVALUATED |

---

## GitHub Merge History Since PR-6 Inspection

The following PRs merged to `main` after the PR-6 inspection baseline.
These are GitHub merge commits only. Render deployed SHA and deploy
timestamps are OPERATOR PENDING — not accessible from agent environment.

| Event | GitHub merge SHA | Time (UTC) |
|-------|-----------------|------------|
| PR-6 inspection baseline | `ba3ea3516f10d07d4708a12942e03162d2f2da50` | 2026-06-19 (operator record) |
| PR #723 merged (shadow analysis redesign) | `ef8e9f5…` | 2026-06-20T07:41:05Z |
| PR #726 merged (correction atomicity fix) | `dce84d198a3a82e0d5de87a6bff512afe10599c8` | 2026-06-20T07:48:11Z |
| PR #725 merged (PR-6 gate docs — docs-only) | `d8d19438e9eba1bb6c12c8a819e7d6a77173dd6e` | 2026-06-20T07:57:07Z |

**Render deployed SHA:** OPERATOR PENDING
**Render deployment timestamps:** OPERATOR PENDING

---

## FF Log

`FF_MOCK_MASTERY_WRITES` transition history is OPERATOR PENDING — Render
environment variable history is not accessible from the agent container.

Known state from checklist (2026-06-20):
- `FF_MOCK_MASTERY_WRITES=live` is BLOCKED (allowlist not deployed).

No FF continuity record is possible from this environment. This does not
constitute a gate evaluation; FF continuity is only required once the
observation window opens.

---

## Validation Fingerprint

The fingerprint covers 18 files (see `docs/ops/pr7_shadow_gate_results.md`
for the full list).

Computed with `sha256sum <18 files> | sha256sum`:

| Point | SHA | Combined fingerprint |
|-------|-----|---------------------|
| PR-6 inspection baseline | `ba3ea3516f10d07d4708a12942e03162d2f2da50` | `6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a` |
| Checked (2026-06-20) | `d8d19438e9eba1bb6c12c8a819e7d6a77173dd6e` | `95d78f8ac61093028195c2372e7c96c7ff2c8e034a36aea19023e83b211006cf` |

**Observation-window fingerprint:** N/A — window not started

**Candidate changed since PR-6 inspection:** YES

Two PRs that merged after the PR-6 inspection modified files in the
fingerprinted set:

| File | Changed by |
|------|-----------|
| `app/backend/app/study_os/mastery_writer.py` | PR #726 |
| `app/backend/app/study_os/mocks.py` | PR #726 |
| `tools/mastery_shadow_analysis/shadow_analysis.py` | PR #723 |

This means the PR-6 inspection fingerprint is superseded. It does **not**
mean an observation window failed — no window was ever opened. Once PR-6
PASS is obtained, the operator must compute a new baseline fingerprint at
the candidate deploy SHA before starting the clock.

**Required action:** establish new baseline fingerprint after PR-6 PASS.

---

## Non-Gate Environment Diagnostic (not validation evidence)

The following CLI attempts were made from the agent container. They
produced no usable gate metrics and are recorded here for transparency
only. They have no effect on the verdict.

### Context

- The agent container does not have the full backend Python dependency
  stack installed (`cachetools` and other packages are absent).
- No live DB credentials (`NEXT_PUBLIC_SUPABASE_URL`,
  `SUPABASE_SERVICE_ROLE_KEY`) were available.
- The window dates supplied (`2026-06-20T07:57:07Z` to
  `2026-07-04T07:57:07Z`) were hypothetical; `2026-07-04` had not yet
  occurred and there was no valid observation window to query.
- These runs are therefore not gate evidence.

### shadow-replay

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

Exit: 2. The `PREREQUISITE_MISSING` label is misleading here:
`attempt_derivation.py` exists at `app/backend/app/study_os/attempt_derivation.py`.
The actual cause is that importing `app.study_os` triggers
`__init__.py` → `mission_control.py` → `exam_eligibility/evaluator.py`
which requires `cachetools`, a transitive backend dependency not installed
in the agent container. The CLI's `ModuleNotFoundError` handler catches
all import failures uniformly and emits `PREREQUISITE_MISSING` regardless
of root cause. This mis-classification should be addressed as a follow-up
code fix to `shadow_analysis.py` (outside scope of this docs PR).

### correction-parity

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

Exit: 2. Same root cause.

**Gate conclusion derived from these runs: none.** CLIs must be rerun
from the operator environment with the full backend Python stack and
live DB credentials. `attempt_derivation.py` is present in the repo.

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

1. Deploy the live canary user allowlist (Gate 9 — BLOCKED).
2. Run all 12 PR-6 gates in a live operator session; obtain PR-6 PASS
   verdict with Gate 9 confirmed and `FF_MOCK_MASTERY_WRITES=shadow`.
3. Operator confirms Render deployed SHA (B) == main SHA (A); records
   exact UTC deploy timestamp as `window_start`.
4. Compute new baseline fingerprint at `window_start` SHA over the 18
   fingerprinted files; record in `docs/ops/pr7_shadow_gate_results.md`.
5. Run CLI weekly (and at day 14) from the operator environment with DB
   credentials using `--from-utc {window_start} --to-utc {now}`.
6. At `window_start + 14 full days`, run final gate; capture JSON; attach
   to a new PR-7 update.
