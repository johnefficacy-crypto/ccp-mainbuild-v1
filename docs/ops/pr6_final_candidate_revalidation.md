---
owner: ops
status: code_fix_required
validation_date: 2026-07-02
partial_run_sha: 9b0c96ed82f8427049c838ee22b7147f5bdd151e
related_audit: docs/audits/2026-07-02-p7-candidate-revalidation-partial.md
prior_preflight_audit: docs/audits/2026-06-19-final-candidate-revalidation.md
---

# PR6: Final Study OS Shadow Candidate Revalidation

**Type:** Operator validation (docs + evidence only)
**Branch:** `docs/final-shadow-candidate-revalidation`
**Prerequisite:** PRs 2–5 merged and deployed on one fixed SHA
**Current status:** CODE-FIX REQUIRED, REVALIDATION PENDING — all 12 start gates PASS at candidate SHA `9b0c96ed82f8427049c838ee22b7147f5bdd151e` (2026-07-02); checklist B–J PASS or INSUFFICIENT DATA; Gate A BLOCKED (`canonical.py::review_mock` writes `review_status`/`reviewed_at` but schema has `review_state`/no `reviewed_at`)
**Verdict:** DO NOT PROCEED TO LIVE — fix schema contract in `app/backend/app/api/canonical.py::review_mock`, re-deploy, re-run Gate A on the fixed SHA

---
**Type:** Operator validation  
**Prerequisite:** PRs 2–5 merged and deployed together on one fixed SHA;
  PR-4 (`attempt_derivation.py`) present for shadow-replay and correction-parity gates  
**Status:** CODE-FIX REQUIRED

## Purpose

Validate on one pinned deployment SHA that all system invariants hold before
starting the 14-day shadow observation window. This becomes the **baseline SHA**
for the shadow gate — but only once the allowlist gate (Gate 9) is cleared.

---

## Start Gate Results — 2026-06-19 (STATIC PREFLIGHT — NOT a clean operator run)

> **Important:** The 2026-06-19 session was a **static code-inspection preflight**, not a live
> operator run. No HTTP calls, no DB queries, no feature-flag changes were made. Gates 2, 3, 5,
> 6 (live state), 7 (live registration), 12 were OPERATOR PENDING or NOT RUN. The run stopped
> at Gate 9. These results do **not** constitute eleven operator passes — only a partial
> code-level pre-check. A full clean operator run is required for P7. The existing
> `docs/audits/2026-06-19-final-candidate-revalidation.md` is immutable; the clean run must
> produce a **separate dated audit** (e.g. `docs/audits/2026-07-XX-final-candidate-revalidation.md`).

Code-level gates were verified against `origin/main` SHA
`ba3ea3516f10d07d4708a12942e03162d2f2da50` (stale — new candidate must be current `main`).
Live gates are marked OPERATOR PENDING and cannot be verified from the documentation agent environment.

| Gate | Check | Result | Notes |
|------|-------|--------|-------|
| 1 | main SHA (A) recorded | CODE PASS | `ba3ea3516f10d07d4708a12942e03162d2f2da50` — **stale**; new candidate must be current `main` |
| 2 | Render deployed SHA (B) | OPERATOR PENDING | Render API not accessible from agent; must be captured by operator |
| 3 | A == B | OPERATOR PENDING | Requires Gate 2 |
| 4 | Validation fingerprint computed | SUPERSEDED | 18-file hash `6ddce48c…` computed at stale SHA against old v1 manifest; **v2 manifest is 36 files** (reference hash `f2ee2c40…` per `pr7_shadow_gate_results.md`); must be recomputed at the new deployed candidate SHA before use |
| 5 | Render instance count = 1 | OPERATOR PENDING | Topology proof requires Render dashboard access |
| 6 | DISABLE_SCHEDULER unset or false | CODE PRESENT | `scheduler.py:140` guard confirmed; live env state requires operator |
| 7 | `GET /api/admin/jobs` preflight | CODE PASS / LIVE PENDING | Endpoint at `notifications.py:241`; `mock:sweeper` registered (30 s interval, `max_instances=1`) — live scheduler registration requires operator confirmation |
| 8 | Preview route exists (404 not 405) | CODE PASS | `admin_study_os.py:1318` — `GET /api/admin/study-os/mocks/{mock_id}/mastery-preview` defined |
| **9** | **Allowlist code deployed** | **STOP — NOT FOUND (2026-06-19); CODE-FIXED on main** | Allowlist (`FF_MOCK_MASTERY_LIVE_USER_IDS`) was absent in June; merged PR #753. Operator must set `FF_MOCK_MASTERY_LIVE_USER_IDS` with ≥1 named user UUID on the new candidate |
| 10 | Migration 181 deployed | FILE PRESENT / LIVE-DB PENDING | File + static inspection confirmed; live staging DB migration history must be verified (`\d+ mock_correction_tasks` and partial indexes) |
| 11 | Writer-authority guard deployed | CODE PASS | `canonical.py` — `platform_attempt_authoritative_fields_rejected` confirmed |
| 12 | FF = shadow for run | NOT RUN | Gate 9 stopped the run in June; must be confirmed on new candidate |

**Gate 9 is a hard prerequisite.** Allowlist code (`FF_MOCK_MASTERY_LIVE_USER_IDS`) is now
merged (PR #753). The new P7 run must deploy current `main` to staging, populate the allowlist
env var with ≥1 named consenting user, and re-run all 12 gates on that pinned SHA.

---

## Start Gate Results — 2026-07-02 (P7 PARTIAL RUN — Gate A BLOCKED)

**Candidate SHA (A):** `9b0c96ed82f8427049c838ee22b7147f5bdd151e`  
**Run type:** Live operator run on staging  
**Verdict:** CODE-FIX REQUIRED — all 12 start gates PASS (Gate 4: REFERENCE ONLY — fingerprint not recomputed at candidate SHA, see note); checklist B–J PASS or INSUFFICIENT DATA; Gate A BLOCKED by schema contract mismatch  
**Staging fixture preserved** (do NOT delete until fixed SHA is deployed and Gate A is rerun):
- Template: `f753a9fc-cdf8-489c-b560-5c0ac5d431b4`
- Attempt: `60b14100-02eb-40fa-a1f0-88a43a48b315`
- Compat mock: `e07efb59-049d-4c64-8e16-243019297a51`

| Gate | Check | Result | Notes |
|------|-------|--------|-------|
| 1 | main SHA (A) recorded | PASS | `9b0c96ed82f8427049c838ee22b7147f5bdd151e` |
| 2 | Render deployed SHA (B) | PASS | Operator confirmed via Render dashboard |
| 3 | A == B | PASS | SHA match confirmed |
| 4 | Validation fingerprint computed | REFERENCE ONLY — NOT RECOMPUTED | 36-file reference hash `f2ee2c40…` per `pr7_shadow_gate_results.md`; fingerprint was **not recomputed** at candidate SHA `9b0c96e…`; must be re-pinned at the final fixed SHA before use as `window_start` baseline |
| 5 | Render instance count = 1 | PASS | Single instance confirmed |
| 6 | DISABLE_SCHEDULER unset or false | PASS | Live env confirmed |
| 7 | `GET /api/admin/jobs` preflight | PASS | `mock:sweeper` registered, running |
| 8 | Preview route exists (404 not 405) | PASS | `GET /api/admin/study-os/mocks/{mock_id}/mastery-preview` returns 200 |
| 9 | Allowlist code deployed | PASS | `FF_MOCK_MASTERY_LIVE_USER_IDS` set with ≥1 named user UUID |
| 10 | Migration 181 deployed | PASS | Live DB confirmed: `mock_correction_tasks` + partial indexes present |
| 11 | Writer-authority guard deployed | PASS | `platform_attempt_authoritative_fields_rejected` confirmed live |
| 12 | FF = shadow for run | PASS | `FF_MOCK_MASTERY_WRITES=shadow` active |

### Gate A — BLOCKED (schema mismatch)

`app/backend/app/api/canonical.py::review_mock` builds a patch with `review_status` and `reviewed_at`, but:
- The DB column is `mock_tests.review_state` (not `review_status`)
- There is no `reviewed_at` column on `mock_tests`
- The correct terminal state value is `correction_drafted` (not `correction`)
- `StudyOsService` correctly reads `review_state` — only the write path is wrong

**Required fix:** In `app/backend/app/api/canonical.py::review_mock`, rename the patch key from `review_status` to `review_state`, remove the `reviewed_at` write, and align accepted state values to include `scheduled`, `unreviewed`, `reviewed`, `correction_drafted`. Update tests that asserted on the old field names.

**Live test evidence (2026-07-02):**
- `POST /review` with `topic_breakdowns` → HTTP 409 `platform_attempt_authoritative_fields_rejected`, breakdown count 0→0 ✓
- `POST /review` with notes only → HTTP 200, notes persisted, `review_state` unchanged (`unreviewed`) ✓
- `POST /review` with `review_status: reviewed` → HTTP 500 (DB write failed — `review_status` column does not exist) ✗ **BLOCKED**

Full evidence in `docs/audits/2026-07-02-p7-candidate-revalidation-partial.md`.

---

## Shadow Gate Tool

The shadow analysis tool (`tools/mastery_shadow_analysis/shadow_analysis.py`)
now implements truthful gate logic. Old thresholds (sign agreement ≥ 80%,
task overlap ≥ 60%) are **removed** — they relied on invalid comparators or
cross-population topic identity that is not available. The valid gates are:

- `shadow-replay`: exact_match_pct = 100.0, coverage_pct = 100.0, zero violations (≥20 attempts required for exit 0; exit 3 if insufficient)
- `correction-parity`: exact_parity_pct = 100.0 (≥50 topic decisions required for exit 0; exit 3 if insufficient)

See docs/ops/pr7_shadow_gate_results.md for the full threshold table.

## Pre-conditions

- PRs 2 (source-based writer authority), 3 (real shadow analysis), 4 (correction
  preview), and 5 (correction uniqueness) are all deployed on the same SHA.
- PR-4 (`app/backend/app/study_os/attempt_derivation.py`) is present on the
  deployed SHA (required for shadow-replay and correction-parity subcommands).
- `FF_MOCK_MASTERY_WRITES=shadow` is active.
- At least one platform attempt has completed since the SHA deployed.

All four blocking defects from the 2026-06-18 failed validation are
code-fixed on `main`. Live proof pending Gate A clearance.

| Defect | Description | Code fix | Migration |
|--------|-------------|----------|-----------|
| DEFECT-001 | Untouched topics received negative deltas | `mastery_writer.py` — `selected_option_id is not None` as attempted source | — |
| DEFECT-002 | Shadow rows duplicated on resubmit | `mastery_writer.py` — conflict-ignore upsert | `180_mock_mastery_shadow_idempotency.sql` |
| DEFECT-003 | Classifications not propagated to writer | `mastery_writer.py` — loads `mock_attempt_response_classification` | — |
| DEFECT-005A | `total_marks` numeric coercion failure | `mock_engine.py:67` — `_to_integral_marks` | — |

---

## Pre-conditions (all required before the gate can open)

1. PRs 2–5 merged and deployed on one fixed SHA ← code-verified on `main`
2. `FF_MOCK_MASTERY_WRITES=shadow` active (not live)
3. At least one platform attempt completed since the SHA deployed
4. **Live canary user allowlist PR merged and deployed** ← MERGED PR #753; deployed at candidate SHA ✓

---

## Validation Checklist (abbreviated — see full audit for detail)

### A. Source-based writer guard (PR2) — **BLOCKED pending Gate A code fix**

- [ ] `POST /review` with `review_status: reviewed` → HTTP 200; `mock_tests.review_state` = `reviewed`
- [ ] `POST /review` with `topic_breakdowns` → HTTP 409 `platform_attempt_authoritative_fields_rejected`
- [ ] No `mock_topic_breakdowns` rows written for that mock_id
- [ ] `POST /review` with notes only → HTTP 200; `review_state` **unchanged** (notes persisted, state not mutated)

### B. Correction-preview classification parity (PR4) — PASS (2026-07-02)

- [x] `GET /mocks/{id}/mastery-preview` returns 200; validate all six sections:
  - `response_counts` — four buckets sum to total frozen question count: `selected`, `marked_unanswered`, `visited_unanswered`, `untouched`
  - `classification_coverage` — `ready = true`
  - `persisted_shadow_decision` — `rows` present, `duplicate_keys = []`
  - `replay_consistency` — `status = MATCH`, zero mismatches/missing/extra
  - `attempt_evidence_corrections` — deterministic corrections (no user state); each entry has a canonical `category` (one of five)
  - `current_state_preview` — labeled mutable; not used for PASS/FAIL
- [x] `classification_counts` keys match `error_type` values in `mock_attempt_response_classification` for that attempt

### C. Deterministic correction categories — PASS (2026-07-02)

- [x] Preview endpoint called twice → identical `attempt_evidence_corrections`

### D. Null-selection behavior — PASS (2026-07-02)

- [x] Preview `response_counts.marked_unanswered` > 0 for null-selection attempt
- [x] Unanswered questions absent from `mastery_deltas`

### E. Shadow idempotency — PASS (2026-07-02)

- [x] Resubmit does not increase `mock_mastery_shadow` row count (unique index enforced)

### F. Shadow-replay gate (PR-5A tool) — INSUFFICIENT DATA (exit 3 — permitted)

> 1 attempt in window; ≥20-attempt threshold not met. 100% exact_match / 100% coverage on
> available sample. Re-run (exit 0 requires ≥20 attempts **and** ≥50 topic decisions) after
> more attempts accumulate on the fixed candidate SHA.

- [x] Run: `python tools/mastery_shadow_analysis/shadow_analysis.py --json shadow-replay --days 1`
- [x] Exit code 3 (INSUFFICIENT_DATA) — permitted per runbook when <20 attempts exist.
      100% match on the 1 available attempt; no violations.
- [ ] Full PASS (exit 0, ≥20 attempts, ≥50 topic decisions) — pending fixed SHA + more attempts

### G. Correction-parity gate (PR-5A tool) — INSUFFICIENT DATA (exit 3 — permitted)

> 3 topic decisions in window; ≥50-decision threshold not met (minimum 10 per runbook). 100%
> exact_parity on available sample. Re-run after ≥10 decisions accumulate on the fixed SHA.

- [x] Run: `python tools/mastery_shadow_analysis/shadow_analysis.py --json correction-parity --days 1`
- [x] Exit code 3 (INSUFFICIENT_DATA) — permitted per runbook. decision_count = 3.
- [ ] Full PASS (exit 0, ≥10 decisions) — pending fixed SHA + more attempts

### H. Automatic scheduler drain (see PR1 checklist) — PASS (cross-ref P6)

- [x] Scheduler evidence per `docs/audits/2026-07-01-scheduler-drain-validation.md` (P6 OPERATOR PASS).
      No re-run needed — P6 audit satisfies this gate for the same candidate lineage.

### I. No live-table mutation — PASS (2026-07-02)

- [x] `user_topic_mastery` unchanged for test user
- [x] `user_topic_mastery_audit` unchanged
- [x] `study_tasks` unchanged

### J. Compatibility-row parity — PASS (2026-07-02)

- [x] `mock_tests` row present with `source_type=platform_attempt`, `trust_level=platform_verified`, `total_marks` integer

---

## Evidence Location

### 2026-06-19 static preflight (IMMUTABLE — superseded)

| Artifact | Location |
|----------|----------|
| Code-level inspection results | This file (gate table above) |
| Preflight SHA | `ba3ea3516f10d07d4708a12942e03162d2f2da50` (stale — static inspection only) |
| Old 18-file fingerprint | `6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a` (superseded by 36-file v2 manifest) |
| Historical record | `docs/audits/2026-06-19-final-candidate-revalidation.md` (immutable) |

**Gate 9 failure date:** 2026-06-19  
**Validated by:** Static code inspection only; no live HTTP/DB/FF evidence; full operator run blocked by Gate 9  

---

### P7 2026-07-02 partial run evidence (Gate A BLOCKED — IMMUTABLE once closed)

> This is a partial run. Gate A failed due to schema mismatch. Evidence for B–J is captured
> in the dated audit. P7 is NOT complete — do not mark as PASS until Gate A is re-run on the
> fixed SHA.

| Artifact | Location |
|---|---|
| Partial run gate table (start gates 1–12 + checklist B–J) | `docs/audits/2026-07-02-p7-candidate-revalidation-partial.md` |
| Staging fixture IDs (preserve until re-run) | Template `f753a9fc-cdf8-489c-b560-5c0ac5d431b4`; Attempt `60b14100-02eb-40fa-a1f0-88a43a48b315`; Compat mock `e07efb59-049d-4c64-8e16-243019297a51` |
| Gate A schema mismatch diagnosis | This file (§ "Gate A — BLOCKED" above) |
| shadow-replay JSON (exit 3, INSUFFICIENT_DATA, 1 attempt) | `docs/audits/2026-07-02-p7-candidate-revalidation-partial.md` |
| correction-parity JSON (exit 3, INSUFFICIENT_DATA, 3 decisions) | `docs/audits/2026-07-02-p7-candidate-revalidation-partial.md` |

**Partial run SHA:** `9b0c96ed82f8427049c838ee22b7147f5bdd151e`  
**Run date:** 2026-07-02  
**Gate A status:** BLOCKED — fix `app/backend/app/api/canonical.py::review_mock` schema contract, re-deploy to staging, re-run Gate A  
**Validated by:** Operator

---

### Clean re-run evidence after Gate A fix (TO BE FILLED)

After the `app/backend/app/api/canonical.py::review_mock` fix is deployed to a new candidate SHA:

| Artifact | Where to store |
|---|---|
| Gate A HTTP response (review_state = reviewed; notes-only leaves review_state unchanged) | New dated audit |
| shadow-replay JSON (≥20 attempts and ≥50 decisions, exit 0) | New dated audit |
| correction-parity JSON (≥10 decisions, exit 0) | New dated audit |
| 36-file fingerprint recomputed at fixed candidate SHA | New dated audit |
| Baseline SHA (fixed candidate) | Record below |

**Baseline SHA (fixed candidate):** `______________________________`  
**Deployed at:** `______________________________`  
**Validated by:** `______________________________`  
**Date:** `______________________________`
