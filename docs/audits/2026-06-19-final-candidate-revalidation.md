---
owner: ops
status: gate_failed
validation_date: 2026-06-19
environment: production (code-only; live gates not executed)
source_of_truth: code_inspection + operator_pending
verified_main_sha: ba3ea3516f10d07d4708a12942e03162d2f2da50
validation_fingerprint: 6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a
related_ops_doc: docs/ops/pr6_final_candidate_revalidation.md
prior_failed_report: docs/audits/ssc-cgl-generated-mock-shadow-validation-2026-06-18.md
---

# Final Study OS Shadow Candidate Revalidation — 2026-06-19

> **What this is.** A code-level pre-flight verification of the Study OS
> shadow candidate against the 12-gate start-gate protocol required before
> the platform-attempt shadow revalidation run. This run STOPPED at Gate 9
> (live canary allowlist not deployed); no live HTTP calls, no DB queries,
> and no FF changes were made.
>
> **Provenance.** All findings derive from static code inspection of
> `origin/main` SHA `ba3ea3516f10d07d4708a12942e03162d2f2da50`. This document
> PR made no database queries, called no live APIs, and altered no feature
> flags.
>
> **Immutability.** This report is immutable once filed (audit convention).
> It records the Gate 9 hard stop and the full start-gate matrix at this
> date. A future clean operator run must produce a separate dated audit.

---

## Executive Verdict

```
DO NOT PROCEED TO LIVE.
START GATE FAILED AT GATE 9: ALLOWLIST NOT DEPLOYED.
```

The code remediations for all four blocking defects from the 2026-06-18
failed validation (DEFECT-001, -002, -003, -005A) are present on `main`.
The idempotency migration (180) and correction-uniqueness migration (181)
are deployed. The preview route and admin jobs endpoint are confirmed.

However, the **live canary user allowlist** (`FF_MOCK_MASTERY_LIVE_USER_IDS`
or any equivalent per-user scoping mechanism) is **absent from the deployed
code**. `FF_MOCK_MASTERY_WRITES` remains a global flag. The canary plan
(`docs/ops/pr8_live_canary_plan.md`) explicitly requires a non-empty named-user
allowlist before any live-flag traffic can be bounded. Until this is deployed,
the validation run cannot commence.

---

## Environment and Provenance

| Field | Value |
|-------|-------|
| Validation date | 2026-06-19 |
| Environment | production (code-only; live phase not reached) |
| Verified main SHA (A) | `ba3ea3516f10d07d4708a12942e03162d2f2da50` |
| Render deployed SHA (B) | OPERATOR PENDING — must be captured by operator |
| A == B confirmed | OPERATOR PENDING |
| Validation fingerprint (start) | `6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a` |
| Validation fingerprint (end) | `6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a` — MATCH |
| Render instance count | OPERATOR PENDING |
| Render worker count | OPERATOR PENDING |
| Disposable operator user | NOT ESTABLISHED (Gate 9 stopped the run before operator session) |
| Attempt ID / blueprint ID | NOT GENERATED |

---

## Validation Fingerprint

The following 18 files were fingerprinted at the start and end of this
code-inspection run. The fingerprint is stable (no files changed between
start and end — docs-only PR).

| File | SHA256 |
|------|--------|
| `app/backend/app/study_os/mastery_writer.py` | `482a33c902a16d51cb7c815a2d33f2cb65297763f5bd2794dbed220988bdd0e1` |
| `app/backend/app/study_os/attempt_classification_readiness.py` | `631b3ac55680ca8ef038e975e60ba549c176075ba4f0bb68a99138b73f0c85cf` |
| `app/backend/app/study_os/attempt_derivation.py` | `cb759ea3ec68cbd33ac61a1abc44f7044ac74917741d90f8d9a82a8cc4590055` |
| `app/backend/app/study_os/mastery_engine/__init__.py` | `c2eb460d66ff272f2c3f5a99b2d281f3a478bb12642003c4a122e04fe45087c0` |
| `app/backend/app/study_os/mastery_engine/correction_tasks.py` | `61684c1c0ff22d937e23b2fc44788c18dfe72ab41cec1a8b1d38940b39a70ff2` |
| `app/backend/app/study_os/mastery_engine/error_patterns.py` | `29b0f8d07c0bec5848c5935a2288ed0a92dc272b6d31ef172978ef9b4f58d8da` |
| `app/backend/app/study_os/mastery_engine/mastery_delta.py` | `fbd3cb9b060aba2bcad738dfe2cc37aa3cac6fb3c010479f7b298a7cb2365cf2` |
| `app/backend/app/study_os/mastery_engine/schemas.py` | `6fd611d02c8c56b499713801349334e3b53451cf97e05b0ef7fc79a34b9cd075` |
| `app/backend/app/study_os/mastery_engine/service.py` | `8a073d5d1d59239c20343c7f38f47fabd60aaae95f3343c35442621c434a1bb1` |
| `app/backend/app/study_os/correction_policy.py` | `48a0ef6b7ed29d1a3484d9e46b9c73c47faa9f6664ad95e0deef762ee1e113d8` |
| `app/backend/app/study_os/mock_engine.py` | `f77e60305e9724736b1b4241c3a19c0f61577b8576e60b6df8e7d63b902f63a5` |
| `app/backend/app/study_os/mocks.py` | `e407cc0930edf121dacbb54c53d34746e479cf681b8b1953978ff767bd59b48d` |
| `app/backend/app/api/mock_engine.py` | `a60caf20b653b38c013e31e08903e4f013c680d42fdbb233671ad279d8fee84c` |
| `app/backend/app/api/canonical.py` | `9f5beb73b6283711f7e2d5c1d377ef8c249f7c25d3c216708251899a62188db6` |
| `app/backend/app/api/study_os.py` | `22765e1e12df8f7d5cd7e14ff980b542b77642bd96c20b8f10acc46dd112abf7` |
| `app/backend/app/api/admin_study_os.py` | `038f0b586fa5528ef5e7e6b78dd9fba2fc96c325cbb22068d0c476f93dea5033` |
| `tools/mastery_shadow_analysis/shadow_analysis.py` | `3be905d19d76223f5c309508894f65a3dbf6596c27dcb89e0c524e3c34dd251e` |
| `app/supabase/migrations/181_mock_correction_tasks_uniqueness.sql` | `755aab31df2799088420f39615607cdbdac74314fde055bae9c52d225a164748` |
| **Combined fingerprint** | **`6ddce48c1c8e92a5c40bb076e3b6e9740b9a4c4d9ce3cfc325fbfa995603b72a`** |

Fingerprint verified at run end: **MATCH** (docs-only PR; no file mutations).

---

## Start Gate — Full Matrix

| Gate | Check | Method | Result | Evidence / Location |
|------|-------|--------|--------|---------------------|
| 1 | main SHA (A) recorded | `git rev-parse origin/main` | PASS | `ba3ea3516f10d07d4708a12942e03162d2f2da50` |
| 2 | Render deployed SHA (B) | Render deployment metadata | OPERATOR PENDING | Render API not accessible from agent environment |
| 3 | A == B | Compare | OPERATOR PENDING | Requires Gate 2 |
| 4 | Validation fingerprint | `sha256sum` 18 files | PASS | See fingerprint table above |
| 5 | Render instance = 1, worker = 1 | Render dashboard | OPERATOR PENDING | No Render API in agent scope |
| 6 | `DISABLE_SCHEDULER` unset/false | Code + live env | CODE PRESENT | `scheduler.py:140`; live state requires operator |
| 7a | `GET /api/admin/jobs` preflight (not 404/405) | Code inspection | PASS | `notifications.py:241` — route defined and routed |
| 7b | `mock:sweeper` registered, `next_run_at` future | Live HTTP + code | CODE PASS / LIVE PENDING | `scheduler.py:190-196` — registered at 30 s interval, `max_instances=1`; live scheduler health requires operator |
| 8 | Preview route: 404 not 405 for nil UUID | Code inspection | PASS | `admin_study_os.py:1318` — route defined; nil mock_id returns 404 (not found), not 405 |
| **9** | **Allowlist code deployed** | **Code inspection** | **STOP — NOT FOUND** | `FF_MOCK_MASTERY_WRITES` is global; no `FF_MOCK_MASTERY_LIVE_USER_IDS`, no per-user allow mechanism anywhere in `app/backend/`; canary plan requires this — see below |
| 10 | Migration 181 uniqueness indexes | File presence | PASS | `181_mock_correction_tasks_uniqueness.sql` present; two partial unique indexes on `mock_correction_tasks` |
| 11 | Writer-authority guard | Code inspection | PASS | `canonical.py:2252` — `platform_attempt_authoritative_fields_rejected`; allowlist `_PLATFORM_REVIEW_ALLOWED = {"review_status", "notes"}` |
| 12 | `mastery_flag_state=shadow` for run | Live HTTP | NOT RUN | Gate 9 stops execution |

### Gate 9 Detail

The PR instructions require confirmation of
`FF_MOCK_MASTERY_LIVE_USER_IDS` or an equivalent named-user allowlist
before proceeding. Full search of `app/backend/` found:

- `FF_MOCK_MASTERY_WRITES` at `mastery_writer.py:492` — reads a global env var;
  applies the same flag state to every user and every attempt.
- No per-user list, no `_LIVE_USER_IDS`, no `LIVE_USER_IDS`, no
  `allowlist_live`, no allowlist check in the flag evaluation path.

The checklist (`docs/status/career-copilot-checklist.md`) already records:

> `Live canary user allowlist | BLOCKED | Hard prerequisite — the user
> allowlist implementation PR has NOT yet merged.`

**Verdict: STOP. The validation run cannot begin until the allowlist is
deployed.**

---

## Code Remediation Verification

All four blocking defects from the 2026-06-18 failed run are code-fixed on
`main`. This is a code-level verification only; live proof is blocked by Gate 9.

### DEFECT-001 — Attempted semantics

**Was:** `MasteryWriter._load_analytics` treated frozen responses (regardless
of `selected_option_id`) as attempted, producing negative deltas on untouched
topics.

**Fix verified:** `mastery_writer.py` now gates on `selected_option_id is not None`
as the source of truth for attempted status. `derive_mastery_deltas` skips
unattempted questions. (Checklist: `DEFECT-001 attempted semantics | CODE-FIXED,
VALIDATION PENDING`)

### DEFECT-002 — Shadow idempotency

**Was:** No unique constraint on `(attempt_id, topic_id, flag_state)` in
`mock_mastery_shadow`; resubmit doubled rows (31→62).

**Fix verified:** Migration `180_mock_mastery_shadow_idempotency.sql` present;
`mastery_writer.py` uses conflict-ignore upsert in `_write_shadow`. (Checklist:
`DEFECT-002 shadow idempotency | CODE-FIXED, VALIDATION PENDING`)

### DEFECT-003 — Classification propagation

**Was:** `_load_analytics` selected only `question_id, is_correct, time_spent_sec,
question_snapshot` and read a non-existent `error_type` column; classifications
from `mock_attempt_response_classification` never reached the writer.

**Fix verified:** `mastery_writer.py` now loads `mock_attempt_response_classification`
and feeds `error_type` into analytics. `attempt_classification_readiness.py`
is a new module added. (Checklist: `DEFECT-003 classification propagation |
CODE-FIXED, VALIDATION PENDING`)

### DEFECT-005A — `total_marks` numeric coercion

**Was:** `"200.0"` rejected by the integer `total_marks` column (Postgres 22P02);
compatibility row absent.

**Fix verified:** `mastery_writer.py` uses `_to_integral_marks` in both initial
compat-row insert and retry emission. (Checklist: `DEFECT-005A total_marks
coercion | CODE-FIXED, VALIDATION PENDING`)

---

## Topology Evidence (Code-Level Only)

| Check | Code evidence | Live state |
|-------|---------------|------------|
| `BackgroundScheduler` init | `scheduler.py:30,136,144` — one global `_scheduler` guarded by `is not None`; `DISABLE_SCHEDULER` env kills initialization | OPERATOR PENDING |
| `mock:sweeper` registered | `scheduler.py:189-196` — `IntervalTrigger(seconds=30)`, `max_instances=1`, `coalesce=True` | OPERATOR PENDING |
| Platform correction gate | `study_os.py:1244` — `PLATFORM_ATTEMPT_MANUAL_CORRECTION_FORBIDDEN` HTTP 409 | OPERATOR PENDING |
| Correction uniqueness | `181_mock_correction_tasks_uniqueness.sql` — two partial indexes | OPERATOR PENDING |
| Writer authority | `canonical.py:2252` — `platform_attempt_authoritative_fields_rejected` | OPERATOR PENDING |
| Preview route | `admin_study_os.py:1318` — `GET /mocks/{mock_id}/mastery-preview`, `PERM_OPS`, zero writes | OPERATOR PENDING |

---

## Per-Phase Pass/Fail Matrix

The following 10-phase matrix records all gates that could be assessed
code-only, and the live phases that are blocked pending Gate 9 clearance.

| Phase | Description | Result |
|-------|-------------|--------|
| P01 | SHA + fingerprint start gate | PARTIAL — A recorded, B/A==B OPERATOR PENDING |
| P02 | Topology (instance, scheduler, endpoints) | PARTIAL — code verified, live state OPERATOR PENDING |
| P03 | Allowlist preflight | **STOP — NOT FOUND** |
| P04 | Migration + authority guards code verification | PASS (code-level) |
| P05 | Baseline DB row capture (operator user) | NOT RUN |
| P06 | Attempt design + blueprint inspection | NOT RUN |
| P07 | Submit + classification readiness + compat row | NOT RUN |
| P08 | Shadow correctness (counts, math, isolation) | NOT RUN |
| P09 | Preview determinism + authority checks | NOT RUN |
| P10 | Scheduler drain + CLI parity + idempotency + fingerprint end | NOT RUN (fingerprint computed code-only — MATCH) |

---

## Evidence File Index

No operator-held live evidence bundle exists for this run (Gate 9 stopped
execution before any live session began). The only evidence is this
documentation file itself and the code inspection performed against
`origin/main` SHA `ba3ea3516f10d07d4708a12942e03162d2f2da50`.

When the allowlist is deployed and the operator runs the full session, the
evidence bundle should include:

| File | Purpose |
|------|---------|
| `session.txt` | Operator user ID, tokens (sanitized), environment proof |
| `gate2-render-sha.txt` | Render dashboard deployed SHA (B) |
| `topology.txt` | Instance count, scheduler status, DISABLE_SCHEDULER proof |
| `admin-jobs-preflight.txt` | `GET /api/admin/jobs` response at T0 and T0+35–70s |
| `baseline-{table}.txt` | Row counts + contents for each monitored table |
| `attempt-design.txt` | Blueprint inspection, answer plan (raw, outside Git) |
| `submit-result.json` | HTTP response, attempt_id, score, submitted_at |
| `classification-readiness.txt` | `check_classification_readiness` response |
| `compat-row.txt` | `mock_tests` row verification |
| `shadow-rows.txt` | `mock_mastery_shadow` rows with math check |
| `isolation-diff-{table}.txt` | Diff vs baseline for each monitored table |
| `preview-{1,2}.json` | Preview endpoint response (called twice) |
| `authority-reject-breakdowns.txt` | `POST /review` with topic_breakdowns → 409 |
| `authority-reject-correction.txt` | `POST correction-tasks` → 409 |
| `authority-pass-notes.txt` | `POST /review` with notes only → 200 |
| `scheduler-t0.txt` and `scheduler-t1.txt` | Jobs status ~35–70 s apart |
| `shadow-replay.json` | CLI `shadow-replay --attempt-id ... --json` |
| `correction-parity.json` | CLI `correction-parity --attempt-id ... --json` |
| `idempotency-resubmit.txt` | Resubmit result + row count verification |
| `fingerprint-end.txt` | Combined SHA256 at run end |

---

## Explicit No-Change Attestation

- No code changed in this PR.
- No feature flag changed.
- No production data mutated.
- No database writes performed.
- No HTTP calls made to live endpoints.
- This PR contains documentation files only.

---

## Recommendation and Next Gate

```
DO NOT PROCEED TO LIVE.
```

Required before next attempt at this gate:

1. **Implement and deploy the live canary user allowlist.** The flag
   `FF_MOCK_MASTERY_WRITES` must become user-scoped (or a named-user
   allowlist must gate the `live` path) so that a live flip affects only the
   designated operator account, not all users.
2. **Confirm that the allowlist PR is merged and deployed** (live Render
   instance).
3. **Re-run the full 12-gate start gate** with a live operator session:
   record SHA B, confirm A == B, verify topology, verify scheduler health,
   confirm FF=shadow, execute all phases.
4. **File a new dated audit** — do not amend this report.
5. **Only a clean repeat with live evidence may change the recommendation.**
