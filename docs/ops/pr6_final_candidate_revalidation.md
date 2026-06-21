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

## Start Gate Results — 2026-06-19

Code-level gates were verified against `origin/main` SHA
`ba3ea3516f10d07d4708a12942e03162d2f2da50`. Live gates are marked OPERATOR
PENDING and cannot be verified from the documentation agent environment.

| Gate | Check | Result | Notes |
|------|-------|--------|-------|
| 1 | main SHA (A) recorded | PASS | `ba3ea3516f10d07d4708a12942e03162d2f2da50` |
| 2 | Render deployed SHA (B) | OPERATOR PENDING | Render API not accessible from agent; must be captured by operator |
| 3 | A == B | OPERATOR PENDING | Requires Gate 2 |
| 4 | Validation fingerprint computed | PASS | Combined SHA256: `6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a` |
| 5 | Render instance count = 1 | OPERATOR PENDING | Topology proof requires Render dashboard access |
| 6 | DISABLE_SCHEDULER unset or false | CODE PRESENT | `scheduler.py:140` guard confirmed; live env state requires operator |
| 7 | `GET /api/admin/jobs` preflight | PASS | Endpoint at `notifications.py:241`; `mock:sweeper` registered (30 s interval, `max_instances=1`) |
| 8 | Preview route exists (404 not 405) | PASS | `admin_study_os.py:1318` — `GET /api/admin/study-os/mocks/{mock_id}/mastery-preview` defined |
| **9** | **Allowlist code deployed** | **STOP — NOT FOUND** | No `FF_MOCK_MASTERY_LIVE_USER_IDS` or per-user allowlist found; `FF_MOCK_MASTERY_WRITES` is global; canary plan requires bounded allowlist before any live traffic |
| 10 | Migration 181 deployed | PASS | `181_mock_correction_tasks_uniqueness.sql` present; unique partial indexes on `mock_correction_tasks` confirmed |
| 11 | Writer-authority guard deployed | PASS | `canonical.py:2252` — `platform_attempt_authoritative_fields_rejected` (allowlist `_PLATFORM_REVIEW_ALLOWED = {"review_status", "notes"}`) |
| 12 | FF = shadow for run | NOT RUN | Gate 9 stops the run |

**Gate 9 is a hard prerequisite.** Per the canary plan, `FF_MOCK_MASTERY_WRITES`
is currently a global flag. A live flip without a user-scoped allowlist would
expose every user to live mastery writes. The allowlist implementation PR has not
yet merged (see checklist: `Live canary user allowlist | BLOCKED`).

---

## Code Remediation Status
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

### F. Automatic scheduler drain
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

| Artifact | Location |
|----------|----------|
| HTTP curl output | Operator-held (outside repo) |
| SQL query results | Operator-held (outside repo) |
| Shadow analysis JSON | Operator-held (outside repo) |
| Code fingerprint | Recorded in this file and in `docs/audits/2026-06-19-final-candidate-revalidation.md` |

**Baseline SHA:** `ba3ea3516f10d07d4708a12942e03162d2f2da50` (main as of 2026-06-19 inspection; deployed Render SHA must be confirmed A == B by operator)
**Validation fingerprint:** `6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a`
**Gate 9 failure date:** 2026-06-19
**Validated by:** Remote docs agent (code-level only); full operator run blocked by Gate 9
**Next action:** Merge and deploy live canary user allowlist, then repeat full operator run
| Artifact | Where to store |
|---|---|
| HTTP response screenshots / curl output | Attach to this PR |
| SQL query results | Attach to this PR |
| shadow-replay JSON output | Attach to this PR |
| correction-parity JSON output | Attach to this PR |
| Baseline SHA | Record below |

**Baseline SHA:** `______________________________`  
**Deployed at:** `______________________________`  
**Validated by:** `______________________________`  
**Date:** `______________________________`
