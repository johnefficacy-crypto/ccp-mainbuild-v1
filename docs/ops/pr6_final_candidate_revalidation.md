---
owner: ops
status: gate_failed
validation_date: 2026-06-19
related_audit: docs/audits/2026-06-19-final-candidate-revalidation.md
---

# PR6: Final Study OS Shadow Candidate Revalidation

**Type:** Operator validation (docs + evidence only)
**Branch:** `docs/final-shadow-candidate-revalidation`
**Prerequisite:** PRs 2–5 merged and deployed on one fixed SHA
**Current status:** START GATE FAILED — live canary user allowlist not deployed
**Verdict:** DO NOT PROCEED TO LIVE

---
**Type:** Operator validation  
**Prerequisite:** PRs 2–5 merged and deployed together on one fixed SHA;
  PR-4 (`attempt_derivation.py`) present for shadow-replay and correction-parity gates  
**Status:** Pending

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

## Shadow Gate Tool

The shadow analysis tool (`tools/mastery_shadow_analysis/shadow_analysis.py`)
now implements truthful gate logic. Old thresholds (sign agreement ≥ 80%,
task overlap ≥ 60%) are **removed** — they relied on invalid comparators or
cross-population topic identity that is not available. The valid gates are:

- `shadow-replay`: exact_match_pct = 100.0, coverage_pct = 100.0, zero violations
- `correction-parity`: exact_parity_pct = 100.0 (min 10 decisions)

See docs/ops/pr7_shadow_gate_results.md for the full threshold table.

## Pre-conditions

- PRs 2 (source-based writer authority), 3 (real shadow analysis), 4 (correction
  preview), and 5 (correction uniqueness) are all deployed on the same SHA.
- PR-4 (`app/backend/app/study_os/attempt_derivation.py`) is present on the
  deployed SHA (required for shadow-replay and correction-parity subcommands).
- `FF_MOCK_MASTERY_WRITES=shadow` is active.
- At least one platform attempt has completed since the SHA deployed.

All four blocking defects from the 2026-06-18 failed validation are
code-fixed on `main`. Live proof pending Gate 9 clearance.

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
4. **Live canary user allowlist PR merged and deployed** ← **MISSING — BLOCKS**

---

## Validation Checklist (abbreviated — see full audit for detail)

### A. Source-based writer guard (PR2)

- [ ] `POST /review` with `topic_breakdowns` → HTTP 409 `platform_attempt_authoritative_fields_rejected`
- [ ] No `mock_topic_breakdowns` rows written for that mock_id
- [ ] `POST /review` with notes only → HTTP 200; `review_status` updated

### B. Correction-preview classification parity (PR4)

- [ ] `GET /mocks/{id}/mastery-preview` returns 200; validate all six sections:
  - `response_counts` — four buckets sum to total frozen question count: `selected`, `marked_unanswered`, `visited_unanswered`, `untouched`
  - `classification_coverage` — `ready = true`
  - `persisted_shadow_decision` — `rows` present, `duplicate_keys = []`
  - `replay_consistency` — `status = MATCH`, zero mismatches/missing/extra
  - `attempt_evidence_corrections` — deterministic corrections (no user state); each entry has a canonical `category` (one of five)
  - `current_state_preview` — labeled mutable; not used for PASS/FAIL
- [ ] `classification_counts` keys match `error_type` values in `mock_attempt_response_classification` for that attempt

### C. Deterministic correction categories

- [ ] Preview endpoint called twice → identical `attempt_evidence_corrections`

### D. Null-selection behavior

- [ ] Preview `response_counts.marked_unanswered` > 0 for null-selection attempt
- [ ] Unanswered questions absent from `mastery_deltas`

### E. Shadow idempotency

- [ ] Resubmit does not increase `mock_mastery_shadow` row count (unique index enforced)

### F. Shadow-replay gate (PR-5A tool)

- [ ] Run: `python tools/mastery_shadow_analysis/shadow_analysis.py --json shadow-replay --days 1`
- [ ] Exit code 0 (PASS or FAIL) or 3 (INSUFFICIENT_DATA if <20 attempts yet).
      Exit code 2 (PREREQUISITE_MISSING) means attempt_derivation.py is absent — fix first.
- [ ] Attach JSON output to this PR.

### G. Correction-parity gate (PR-5A tool)

- [ ] Run: `python tools/mastery_shadow_analysis/shadow_analysis.py --json correction-parity --days 1`
- [ ] Attach JSON output to this PR.

### H. Automatic scheduler drain (see PR1 checklist)

- [ ] Scheduler evidence per `docs/ops/pr1_scheduler_drain_verification.md`

### I. No live-table mutation

- [ ] `user_topic_mastery` unchanged for test user
- [ ] `user_topic_mastery_audit` unchanged
- [ ] `study_tasks` unchanged

### J. Compatibility-row parity

- [ ] `mock_tests` row present with `source_type=platform_attempt`, `trust_level=platform_verified`, `total_marks` integer

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
**Next action:** Deploy current `main` to staging; record new candidate SHA A; confirm Render SHA B == A; set `FF_MOCK_MASTERY_LIVE_USER_IDS`; re-run all 12 gates + A–J checklist on a real topic-linked attempt. Create a new dated audit for the clean run.

---

### Clean P7 run evidence (TO BE FILLED by operator)

Create a new dated audit file: `docs/audits/2026-07-XX-final-candidate-revalidation.md`  
Then update `docs/ops/pr6_final_candidate_revalidation.md` and the shared checklist to reflect PASS/FAIL.

| Artifact | Where to store |
|---|---|
| HTTP response screenshots / curl output | New dated audit + attached to PR |
| SQL query results (migration 181 live-DB check) | New dated audit |
| shadow-replay JSON output | New dated audit |
| correction-parity JSON output | New dated audit |
| 36-file fingerprint recomputed at candidate SHA | New dated audit |
| Baseline SHA | Record below |

**Baseline SHA (new candidate):** `______________________________`  
**Deployed at:** `______________________________`  
**Validated by:** `______________________________`  
**Date:** `______________________________`
