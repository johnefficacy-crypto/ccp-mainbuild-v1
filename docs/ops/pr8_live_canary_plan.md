# PR8: Bounded Mock Mastery Live Canary Plan

**Type:** Operational plan — design document only  
**Status:** DESIGN PRESENT — EXECUTION BLOCKED

Blocking prerequisites (none may be skipped):
1. Allowlist implementation PR — CODE FIXED (PR #753: `resolve_effective_mastery_flag` + `FF_MOCK_MASTERY_LIVE_USER_IDS` enforcement at sync submit and analytics_retry enqueue)
2. Pinned effective mode for delayed correction recovery — CODE FIXED (PR #753: `get_or_resolve_pinned_mastery_flag` used at sync submit, analytics_retry D4, and `_recover_corrections_after_mock_tests`; eager mastery enqueue removed from `auto_submit_attempt`)
3. PR-6 final candidate revalidation — GATE FAILED (re-run required after items 1–2 PRs deploy)
4. PR-7 14-day shadow gate — NOT STARTED — BLOCKED ON PR-6
5. Migration 182 — CODE PRESENT, dry-run/apply/permission validation pending
6. `_apply_error_patterns` schema mismatch — not resolved (see Preflight P9 and Rollback Step 5)
7. Staging rehearsal of complete rollback procedure — not completed

> **Required statement — merging this PR:**
> "Merging this PR changes no feature flag (`FF_MOCK_MASTERY_WRITES`) and no
> allowlist (`FF_MOCK_MASTERY_LIVE_USER_IDS` or equivalent).
> The Render transition is a separate operator action.
> This document grants no authorization to perform the canary."

---

## Dependencies (all must be PASS before canary execution)

| # | Dependency | Status |
|---|------------|--------|
| 1 | PR-6 final candidate revalidation | **GATE FAILED — RE-RUN REQUIRED** |
| 2 | PR-7 14-day shadow gate | **NOT STARTED — BLOCKED ON PR-6** |
| 3 | Live-user allowlist implementation merged, deployed, and validated | **CODE FIXED (PR #753) — DEPLOYMENT AND VALIDATION PENDING** |
| 4 | Correction atomicity (PR-5B) deployed — migration 182 applied | **CODE PRESENT — DRY-RUN/APPLY/PERMISSION VALIDATION PENDING** |
| 5 | Scheduler automatic-drain evidence | OPERATOR PENDING |
| 6 | Deployed SHA matches approved PR-6 candidate SHA | OPERATOR PENDING |

**Dep #1 detail:** `docs/ops/pr6_final_candidate_revalidation.md` status is `gate_failed`.
Gate 9 stopped the 2026-06-19 run: no per-user allowlist deployed. The gate cannot clear
until dependency #3 resolves and a clean re-run is completed.

**Dep #2 detail:** `docs/ops/pr7_shadow_gate_results.md` status is `not_started`, verdict
`START_CONDITION_NOT_MET` (checked 2026-06-20). Start condition failed: PR-6 PASS not met.
No observation window has opened and no threshold evaluation has occurred. Blocked on #1.

**Dep #3 detail:** Per-user allowlist is code-implemented in PR #753.
`resolve_effective_mastery_flag(requested_flag, user_id)` (`mastery_writer.py`) reads
`FF_MOCK_MASTERY_LIVE_USER_IDS` and downgrades `live` → `shadow` for users not in the list.
`get_or_resolve_pinned_mastery_flag` (`mock_engine.py`) pins the resolved flag per-attempt
so FF or allowlist changes after first submit cannot alter the effective mode.
Remaining gate: merge PR #753, deploy, and run the four-combination resolver matrix on
staging (see Allowlist Architecture §) before marking this dependency PASS.

**Dep #4 detail:** Migration 182 adds three SECURITY DEFINER RPCs. Code is present in the
repository. Required before canary: (a) dry-run on staging clone, (b) permission
verification (anon/authenticated cannot EXECUTE), (c) production apply and schema
confirmation. See Migration 182 Prerequisites § below.

---

## Scope (locked — global unrestricted canary is forbidden)

- **One** named disposable canary user UUID (in allowlist)
- **One** named disposable control user UUID (NOT in allowlist, same exam/template as canary)
- **One** live attempt maximum — canary user
- **One** control attempt maximum — control user
- No real customer in scope
- No correction task may be applied during canary window
- **Maximum canary window:** 15 minutes from FF=live deploy to FF=shadow redeploy

Populate before execution:

| Identity | UUID |
|----------|------|
| Canary user | `<CANARY_USER_UUID>` |
| Control user | `<CONTROL_USER_UUID>` |
| Canary attempt | `<CANARY_ATTEMPT_ID>` (recorded after run) |
| Control attempt | `<CONTROL_ATTEMPT_ID>` (recorded after run) |
| Canary `mock_test_id` | `<CANARY_MOCK_TEST_ID>` (recorded after run) |
| Canary run ID | `<CANARY_RUN_ID>` (e.g. `canary-2026-MM-DD-<first-8-of-CANARY_USER_UUID>`) |
| Live deploy timestamp | `<LIVE_DEPLOY_TIMESTAMP>` (recorded at Step 3 completion) |

---

## Pre-Execution Attempt Specification

Before beginning any preflight step, complete this table and record it in the dated
evidence file under `docs/audits/`. The canary cannot proceed without a complete
specification — success criteria must be validated against these values, not inferred
post-hoc.

| Field | Value (operator fills before preflight) |
|-------|----------------------------------------|
| Exam template ID | `<TEMPLATE_ID>` |
| Question IDs to answer (≥2) | `[<Q1_UUID>, <Q2_UUID>, ...]` |
| Correct answer selection(s) — question IDs | `[<Q1_UUID>]` (≥1) |
| Incorrect answer selection(s) — question IDs | `[<Q2_UUID>]` (≥1) |
| Known raw `error_type` for each incorrect answer (from `mock_attempt_response_classification`) | one of: `silly_mistake`, `concept_gap`, `option_trap`, `calc_error`, `time_pressure_unattempted`, `knowledge_gap`, `marked_unanswered` |
| Expected normalized correction `category` for each incorrect answer (from `correction_policy.py` `CANONICAL_CATEGORIES`) | one of: `concept_gap`, `memory_gap`, `careless`, `speed_issue`, `option_trap` (alias mapping: `silly_mistake`→`careless`, `calc_error`→`careless`, `knowledge_gap`→`concept_gap`, `time_pressure_unattempted`→`speed_issue`) |
| Expected `mock_attempt_response_classification` row count | `<N>` |
| Mastery-eligible topic IDs (from answered questions) | `[<TOPIC_UUID>, ...]` |
| Expected correction categories | `[<category>, ...]` |
| Maximum expected `user_topic_mastery_audit` rows | `<N>` |
| Maximum expected `mock_correction_tasks` rows | `<N>` |

---

## Migration 182 Prerequisites

Migration 182 (`app/supabase/migrations/182_*.sql`) adds three SECURITY DEFINER RPCs
required in the correction path. All of the following must pass before canary execution:

- [ ] Dry-run on staging/clone DB: `BEGIN; -- apply migration; -- SELECT 3 RPCs from pg_proc; ROLLBACK;`
- [ ] `ensure_mock_correction_draft`: wrong `user_id` raises `no_data_found` — confirmed in staging
- [ ] `ensure_mock_correction_drafts`: wrong `user_id` raises `no_data_found` — confirmed in staging
- [ ] `replace_manual_mock_correction_drafts`: atomically replaces drafts — confirmed in staging
- [ ] Privilege checks — all six queries must return `false`:
  ```sql
  SELECT has_function_privilege('anon',          'public.ensure_mock_correction_draft(uuid,uuid,text,text,text,jsonb)', 'EXECUTE');
  SELECT has_function_privilege('authenticated',  'public.ensure_mock_correction_draft(uuid,uuid,text,text,text,jsonb)', 'EXECUTE');
  SELECT has_function_privilege('anon',          'public.ensure_mock_correction_drafts(uuid,uuid,jsonb)', 'EXECUTE');
  SELECT has_function_privilege('authenticated',  'public.ensure_mock_correction_drafts(uuid,uuid,jsonb)', 'EXECUTE');
  SELECT has_function_privilege('anon',          'public.replace_manual_mock_correction_drafts(uuid,uuid,jsonb)', 'EXECUTE');
  SELECT has_function_privilege('authenticated',  'public.replace_manual_mock_correction_drafts(uuid,uuid,jsonb)', 'EXECUTE');
  ```
  Expected: `false` for every row. Any `true` result is a security defect — STOP and fix grants.
- [ ] Migration applied to the target (production) environment
- [ ] Deployed schema confirms all three RPCs present: `SELECT proname FROM pg_proc WHERE proname LIKE 'ensure_mock_correction%' OR proname = 'replace_manual_mock_correction_drafts'`

---

## Allowlist Architecture (confirm implementation before execution)

**Current state (PR #753 code-fixed, deployment pending):**
`resolve_effective_mastery_flag(requested_flag, user_id)` (`mastery_writer.py`) implements
the per-user allowlist. `get_or_resolve_pinned_mastery_flag(sb, attempt_id, user_id)`
(`mock_engine.py`) pins the resolved mode per-attempt by reading any existing
non-cancelled mastery_retry job row before falling back to env resolution.

Resolver behavior (fail closed — empty or malformed allowlist → shadow):

| Global flag | User in allowlist | Resolved flag |
|-------------|-------------------|---------------|
| `off` | any | `off` |
| `shadow` | any | `shadow` |
| `live` | yes | `live` |
| `live` | no | `shadow` |
| `live` | allowlist empty or malformed | `shadow` |

**RESOLUTION points** — call `get_or_resolve_pinned_mastery_flag(sb, attempt_id, user_id)`
(which internally calls `resolve_effective_mastery_flag` only when no pinned job exists):

1. **Synchronous submit endpoint** (`api/mock_engine.py`) — `get_or_resolve_pinned_mastery_flag`
   called with the authenticated `user_id`. CODE FIXED (PR #753).
2. **`_run_job JOB_ANALYTICS_RETRY`** (`mock_engine.py`) — calls
   `get_or_resolve_pinned_mastery_flag` after analytics succeeds; enqueues `JOB_MASTERY_RETRY`
   with the pinned flag. This is the primary resolution point for the async path.
   CODE FIXED (PR #753).
3. **`auto_submit_attempt`** (`mock_engine.py`) — schedules ONLY `JOB_ANALYTICS_RETRY`;
   does NOT call `enqueue_mastery_retry_required` or resolve the mastery flag. D2 eager
   enqueue removed. Resolution happens when `JOB_ANALYTICS_RETRY _run_job` enqueues
   `JOB_MASTERY_RETRY` (point 2 above). CODE FIXED (PR #753).

**CONSUMER points** — must NOT call `resolve_effective_mastery_flag` or
`get_mastery_write_flag()`; must use the already-persisted `mastery_flag_state`:

4. **`_run_job JOB_MASTERY_RETRY`** (`mock_engine.py`) — reads `mastery_flag_state` from
   the job row. Already correct; unchanged.
5. **`_recover_corrections_after_mock_tests`** (`mock_engine.py`) — now calls
   `get_or_resolve_pinned_mastery_flag` to read the original persisted mode from the
   mastery_retry job row for the same attempt. Does NOT call `get_mastery_write_flag()`
   directly. CODE FIXED (PR #753).

**Failure case this classification prevents:**
1. Attempt submitted → effective mode resolved to `live` → `mastery_flag_state='live'` pinned to job row
2. Compat-row creation fails; `_recover_corrections_after_mock_tests` is scheduled
3. Operator changes `FF_MOCK_MASTERY_WRITES` back to `shadow` (e.g., after a rollback or incident)
4. Delayed correction recovery runs → `get_or_resolve_pinned_mastery_flag` reads the
   pinned `live` job row → correctly executes live correction recovery.
   (Pre-fix: re-resolved from current env → read `shadow` → incorrectly skipped live corrections.)

This runtime correctness defect is resolved in code by PR #753.

**Required behavior matrix — confirm from deployed code before marking plan READY:**

| Combination | Expected observable behavior |
|-------------|------------------------------|
| Allowlisted user + `FF=live` | `resolve_effective_mastery_flag` returns `live`; job row `mastery_flag_state='live'`; writer executes `_apply_mastery`, `_apply_error_patterns`, `_draft_correction_tasks`; `user_topic_mastery_audit` row written |
| Non-allowlisted user + `FF=live` | Resolver returns `shadow`; job row `mastery_flag_state='shadow'`; writer writes shadow row only; no `user_topic_mastery_audit` row |
| Any user + `FF=shadow` | Resolver returns `shadow` regardless of allowlist; shadow row only |
| Any user + `FF=off` | Resolver returns `off`; no writes |

If any combination produces different behavior, document it and update Stop Conditions
before proceeding.

---

## Preflight (operator executes immediately before Render action)

All queries are scoped to exact user IDs. Save all outputs before proceeding; they form
the rollback baseline.

```sql
-- P1: Record current deployed SHA
-- Obtain from Render dashboard → Service → Deploys → current deploy SHA.
-- SHA: _______________________________________________

-- P2: Confirm deployed SHA matches approved PR-6 candidate baseline; verify code fingerprint
--
-- Step 1: The SHA recorded in P1 must match <APPROVED_PR6_CANDIDATE_SHA>.
--   This value is populated only after all blocking code/migration PRs merge and
--   a clean PR-6 PASS is obtained on that exact candidate SHA.
--   STOP if SHA differs — the code state has changed since the validated baseline.
--
-- Step 2: Compute the validation fingerprint on the deployed repo checkout using
--   the file manifest at <FINGERPRINT_MANIFEST_PATH> (version <FINGERPRINT_MANIFEST_VERSION>).
--   The canonical v2 manifest (docs/ops/mastery_validation_fingerprint_manifest_v2.txt)
--   must be created and frozen after all Lane A blocking PRs merge; do not use the
--   superseded PR-6 18-file manifest or its fingerprints.
--     sha256sum <file1> <file2> ... | sha256sum
--   Expected: <APPROVED_PR7_BASELINE_FINGERPRINT>
--   This value is populated when PR-7 establishes a baseline and must remain
--   unchanged throughout the 14-day shadow window.
--   STOP if fingerprint differs — code state has diverged from the validated baseline.
--
-- Result: _______________________________________________

-- P3: Confirm FF currently shadow
-- Step 1: Verify Render env var panel shows FF_MOCK_MASTERY_WRITES=shadow.
-- Step 2: Confirm absence of recently created live-pinned mastery_retry jobs:
SELECT job_kind, mastery_flag_state, status
FROM public.mock_attempt_jobs
WHERE job_kind = 'mastery_retry'
  AND created_at > now() - interval '5 minutes'
ORDER BY created_at DESC LIMIT 5;
-- Expected: zero rows, OR all rows have mastery_flag_state = 'shadow'.
-- STOP if any row has mastery_flag_state = 'live' — FF is not shadow.
-- Step 3: Confirm staging integration tests for the resolver behavior matrix passed
--   (see Allowlist Architecture § — all four resolver combinations must be rehearsed
--   on staging before execution begins).
-- Do NOT submit an additional production attempt for FF confirmation.
-- The control attempt (Canary Sequence Step 4) is the bounded behavioral proof
-- that the non-allowlisted path resolves to shadow.

-- P4: Allowlist contains ONLY the named canary user UUID
-- Read deployed config: env var FF_MOCK_MASTERY_LIVE_USER_IDS or allowlist mechanism.
-- Value observed: _______________________________________________
-- Expected: exactly '<CANARY_USER_UUID>' — no other UUIDs.
-- STOP if any other UUID is present.

-- P5: No pending or running mastery_retry with mastery_flag_state=live
SELECT count(*) AS live_pending
FROM public.mock_attempt_jobs
WHERE job_kind          = 'mastery_retry'
  AND mastery_flag_state = 'live'
  AND status             IN ('pending', 'running');
-- Expected: 0. STOP if > 0.

-- P6: Scheduler healthy
-- GET /api/admin/jobs — verify last_run_at recent, no stuck/failed jobs.
-- Result: _______________________________________________

-- P7: Baseline mastery for canary user — mock scope only (save full result)
--   apply_mock_mastery_delta scopes to exam_id IS NULL AND exam_phase_id IS NULL;
--   baseline and rollback must use the same scope.
--   Note: updated_at is recorded here for documentation only — do NOT attempt
--   to restore it on rollback; the BEFORE UPDATE trigger (migration 116) sets
--   it automatically and will overwrite any explicit value.
SELECT id, topic_id, mastery_score, updated_at
FROM public.user_topic_mastery
WHERE user_id       = '<CANARY_USER_UUID>'
  AND exam_id       IS NULL
  AND exam_phase_id IS NULL
ORDER BY topic_id;
-- Save as: canary_mastery_baseline

-- P8: Baseline mastery for control user — mock scope only (save full result)
SELECT id, topic_id, mastery_score, updated_at
FROM public.user_topic_mastery
WHERE user_id       = '<CONTROL_USER_UUID>'
  AND exam_id       IS NULL
  AND exam_phase_id IS NULL
ORDER BY topic_id;
-- Save as: control_mastery_baseline

-- P8b: Baseline correction tasks for control user (save full result)
SELECT ct.id, ct.category, ct.topic, ct.state
FROM public.mock_correction_tasks ct
JOIN public.mock_tests mt ON mt.id = ct.mock_test_id
WHERE ct.user_id = '<CONTROL_USER_UUID>'
ORDER BY ct.created_at;
-- Save as: control_correction_baseline (expected empty for a fresh disposable user)

-- P9: Error patterns baseline for canary user
-- ⛔ HARD BLOCKER: _apply_error_patterns (mastery_writer.py lines 289–294) upserts
-- columns 'microtopic_id' and 'error_count' which DO NOT EXIST in
-- user_topic_error_patterns (migration 033). Actual schema columns are:
--   id, user_id, exam_id, exam_phase_id, topic_id, question_id, error_type,
--   frequency_count, last_seen_at, evidence, created_at, updated_at
-- No later migration adds microtopic_id or error_count. The writer will raise a
-- DB-level error on any live attempt. This step is BLOCKED until the schema
-- mismatch is resolved in a separate code PR and the correct columns confirmed.
-- Do not execute the canary until this blocker is cleared.
--
-- ⚠️ PARTIAL-WRITE WARNING: The live write order is (1) _write_shadow, (2) _apply_mastery +
-- user_topic_mastery_audit (via apply_mock_mastery_delta RPC — atomic for its own writes),
-- (3) _apply_error_patterns, (4) _draft_correction_tasks. A DB-level failure in step (3)
-- does NOT imply zero live mutation. Mastery and audit rows from step (2) may already be
-- committed before the error-pattern failure occurs. If _apply_error_patterns fails,
-- check user_topic_mastery and user_topic_mastery_audit for the canary user before
-- concluding no live mutation occurred.
--
-- Documentation only (do not use for restore — restore is blocked):
SELECT id, user_id, exam_id, exam_phase_id, topic_id, question_id,
       error_type, frequency_count, last_seen_at, created_at
FROM public.user_topic_error_patterns
WHERE user_id = '<CANARY_USER_UUID>'
ORDER BY topic_id, error_type;
-- Save as: canary_error_baseline (observation only)

-- P10: Correction tasks baseline for canary user (save full result)
SELECT ct.id, ct.category, ct.topic, ct.state
FROM public.mock_correction_tasks ct
JOIN public.mock_tests mt ON mt.id = ct.mock_test_id
WHERE ct.user_id = '<CANARY_USER_UUID>'
ORDER BY ct.created_at;
-- Save as: canary_correction_baseline (expected empty for a fresh disposable user)

-- P11: Confirm zero existing live audit rows for both users
SELECT count(*) AS existing_audit_rows
FROM public.user_topic_mastery_audit
WHERE user_id IN ('<CANARY_USER_UUID>', '<CONTROL_USER_UUID>');
-- Expected: 0. If nonzero, document exactly and reconcile before proceeding.

-- P12: No concurrent activity on either user
SELECT count(*) AS active_jobs
FROM public.mock_attempt_jobs
WHERE status      IN ('pending', 'running')
  AND attempt_id  IN (
    SELECT id FROM public.mock_attempts
    WHERE user_id IN ('<CANARY_USER_UUID>', '<CONTROL_USER_UUID>')
  );
-- Expected: 0. STOP if > 0.
```

---

## Canary Sequence

**Timer starts when Step 3 (FF=live) deploy completes. Window: 15 minutes maximum.**

### Step 1 — Verify allowlist is set

Read deployed config and confirm the allowlist mechanism contains exactly
`<CANARY_USER_UUID>` and no other UUIDs. Do not continue if any other UUID is present.

### Step 2 — Deploy while FF remains shadow

Set `FF_MOCK_MASTERY_WRITES=shadow` on Render. Deploy. Confirm via Render env var panel
that `FF_MOCK_MASTERY_WRITES=shadow` is active. Verify service is running:
`GET /api/health` → `{"status": "ok", "service": "career-copilot", "ts": "..."}`.
Then run P3 to confirm `mastery_flag_state='shadow'` for any new jobs before proceeding.

### Step 3 — Set FF=live and deploy

Set `FF_MOCK_MASTERY_WRITES=live` on Render. Deploy. Confirm via Render env var panel
that `FF_MOCK_MASTERY_WRITES=live` is active. Verify service is running:
`GET /api/health` → `{"status": "ok", "service": "career-copilot", "ts": "..."}`.
Record `<LIVE_DEPLOY_TIMESTAMP>`. **Start 15-minute timer.**

### Step 4 — Run ONE control attempt (non-allowlisted user)

Submit exactly one mock attempt as `<CONTROL_USER_UUID>`. Wait for the `mastery_retry`
job to reach `status='done'` (observe via `/api/admin/jobs` or query below). Then assert:

```sql
-- C1: Control user must NOT receive live writes
SELECT count(*) AS control_live_rows
FROM public.user_topic_mastery_audit
WHERE user_id = '<CONTROL_USER_UUID>';
-- Expected: 0

SELECT mastery_flag_state, status
FROM public.mock_attempt_jobs
WHERE job_kind   = 'mastery_retry'
  AND attempt_id = '<CONTROL_ATTEMPT_ID>';
-- Expected: mastery_flag_state = 'shadow'
```

**STOP and roll back immediately if `control_live_rows > 0`.**
This confirms non-allowlisted users are not affected by `FF=live`.

### Step 5 — Run ONE canary attempt (allowlisted user)

Submit exactly one mock attempt as `<CANARY_USER_UUID>`. Wait for the `mastery_retry`
job to reach `status='done'`. Proceed to success criteria verification.

---

## Canary Success Criteria (all required)

Run all queries before the 15-minute window expires.

```sql
-- S1: Shadow decision exists with flag_state=live for canary attempt
SELECT topic_id, proposed_delta_db, flag_state
FROM public.mock_mastery_shadow
WHERE attempt_id = '<CANARY_ATTEMPT_ID>'
  AND flag_state = 'live';
-- Expected: ≥1 row; topic_ids must match pre-execution spec mastery-eligible topics

-- S2: user_topic_mastery_audit row exists for (canary_user, topic, attempt_id)
SELECT user_id, topic_id, attempt_id, before_mastery_db, after_mastery_db, delta_applied_db
FROM public.user_topic_mastery_audit
WHERE attempt_id = '<CANARY_ATTEMPT_ID>'
  AND user_id    = '<CANARY_USER_UUID>';
-- Expected: ≥1 row; count must not exceed max from pre-execution spec

-- S3: audit delta_applied_db equals persisted live shadow decision within 0.01 db
SELECT
  s.topic_id,
  s.proposed_delta_db                                AS shadow_delta,
  a.delta_applied_db                                 AS live_delta,
  abs(s.proposed_delta_db - a.delta_applied_db)      AS delta_diff,
  CASE WHEN abs(s.proposed_delta_db - a.delta_applied_db) <= 0.01
       THEN 'PASS' ELSE 'FAIL' END                   AS check_result
FROM public.mock_mastery_shadow s
JOIN public.user_topic_mastery_audit a
  ON  a.attempt_id = s.attempt_id
  AND a.topic_id   = s.topic_id
WHERE s.attempt_id = '<CANARY_ATTEMPT_ID>'
  AND s.flag_state = 'live'
  AND a.user_id    = '<CANARY_USER_UUID>';
-- Expected: all check_result = 'PASS', all delta_diff ≤ 0.01

-- S4: Exactly one audit row per (canary_user, topic_id, attempt_id)
SELECT user_id, topic_id, attempt_id, count(*) AS cnt
FROM public.user_topic_mastery_audit
WHERE attempt_id = '<CANARY_ATTEMPT_ID>'
  AND user_id    = '<CANARY_USER_UUID>'
GROUP BY user_id, topic_id, attempt_id
HAVING count(*) > 1;
-- Expected: zero rows

-- S5: mastery_score after = clamp(before + delta) ± 0.01, and mastery_score ∈ [0, 100]
--     apply_mock_mastery_delta scopes to exam_id IS NULL AND exam_phase_id IS NULL
SELECT
  a.topic_id,
  a.before_mastery_db,
  a.delta_applied_db,
  a.after_mastery_db,
  GREATEST(0, LEAST(100, a.before_mastery_db + a.delta_applied_db)) AS expected_after,
  abs(a.after_mastery_db
      - GREATEST(0, LEAST(100, a.before_mastery_db + a.delta_applied_db))) AS clamp_diff,
  CASE WHEN a.after_mastery_db BETWEEN 0 AND 100
            AND abs(a.after_mastery_db
                    - GREATEST(0, LEAST(100, a.before_mastery_db + a.delta_applied_db))) <= 0.01
       THEN 'PASS' ELSE 'FAIL' END AS check_result
FROM public.user_topic_mastery_audit a
WHERE a.attempt_id = '<CANARY_ATTEMPT_ID>'
  AND a.user_id    = '<CANARY_USER_UUID>';
-- Expected: all check_result = 'PASS'

-- S6: [BLOCKED — schema mismatch] user_topic_error_patterns verification
-- _apply_error_patterns (mastery_writer.py lines 289–294) references
-- 'microtopic_id' and 'error_count' which do not exist in migration 033.
-- This criterion is BLOCKED pending schema reconciliation in a separate code PR.
-- Canary MUST NOT PROCEED past S6 until the mismatch is resolved and the
-- correct column names are confirmed here.

-- S7: mock_correction_tasks drafted for canary user (if classifications complete)
SELECT ct.id, ct.category, ct.topic, ct.state
FROM public.mock_correction_tasks ct
JOIN public.mock_tests mt ON mt.id = ct.mock_test_id
WHERE mt.mock_attempt_id = '<CANARY_ATTEMPT_ID>'
  AND ct.user_id          = '<CANARY_USER_UUID>';
-- Expected: state='drafted' rows matching pre-execution spec correction categories;
-- empty only if all questions correct and no correction eligible

-- S8: All correction categories valid (check constraint from migration 063)
SELECT ct.category,
  CASE WHEN ct.category IN
    ('concept_gap', 'memory_gap', 'careless', 'speed_issue', 'option_trap')
  THEN 'VALID' ELSE 'INVALID' END AS category_check
FROM public.mock_correction_tasks ct
JOIN public.mock_tests mt ON mt.id = ct.mock_test_id
WHERE mt.mock_attempt_id = '<CANARY_ATTEMPT_ID>'
  AND ct.user_id          = '<CANARY_USER_UUID>';
-- Expected: all category_check = 'VALID'

-- S9: No duplicate drafted correction for (mock_test_id, user_id, category, topic)
SELECT mock_test_id, user_id, category, topic, count(*) AS cnt
FROM public.mock_correction_tasks
WHERE mock_test_id IN (
  SELECT id FROM public.mock_tests
  WHERE mock_attempt_id = '<CANARY_ATTEMPT_ID>'
)
AND state = 'drafted'
GROUP BY mock_test_id, user_id, category, topic
HAVING count(*) > 1;
-- Expected: zero rows

-- S10: Resubmit is idempotent — verify via normal submit endpoint
-- Action: submit the already-submitted canary attempt again using the SAME
--   claimed_answered_count via the normal submit endpoint.
--   Expected response: HTTP 200 (idempotent — attempt is already submitted).
--   A 409 response means the operator used a different claimed_answered_count;
--   this is operator error and is NOT a passing idempotency result — stop and
--   resubmit with the correct count before continuing.
--   Do NOT manually enqueue a mastery_retry job; the route handles mastery
--   internally via claim_mastery_retry_required.
-- Then verify all of the following are unchanged from previous steps:
--   (a) No new mastery_retry job claimed or completed for <CANARY_ATTEMPT_ID>.
--       The done-job unique index mock_attempt_jobs_mastery_done_uidx on
--       (attempt_id, mastery_flag_state) WHERE status='done' (migration 180)
--       prevents a second done-job for the same pair.
--   (b) Audit row count for <CANARY_ATTEMPT_ID> is unchanged from S2.
--   (c) Mastery scores for <CANARY_USER_UUID> are unchanged from S5.
--   (d) Correction-draft count is unchanged from S7.
--   (e) No new duplicate shadow rows for <CANARY_ATTEMPT_ID>.
SELECT count(*) AS row_count
FROM public.user_topic_mastery_audit
WHERE attempt_id = '<CANARY_ATTEMPT_ID>'
  AND user_id    = '<CANARY_USER_UUID>';
-- Expected: same count as S2 (unique constraint on (user_id, topic_id, attempt_id)
-- prevents a second row; conflict-ignore upsert must leave existing rows untouched)

-- S11: Control user — zero live audit rows, zero live mastery changes, zero live corrections
SELECT count(*) AS control_live_audit
FROM public.user_topic_mastery_audit
WHERE user_id = '<CONTROL_USER_UUID>';
-- Expected: 0

SELECT count(*) AS control_live_corrections
FROM public.mock_correction_tasks
WHERE user_id    = '<CONTROL_USER_UUID>'
  AND mock_test_id IN (
    SELECT id FROM public.mock_tests
    WHERE mock_attempt_id = '<CONTROL_ATTEMPT_ID>'
  );
-- Expected: 0

-- S12: Zero writer exceptions in backend logs during canary window
-- Check Render log stream for 'career_copilot.study_os.mastery_writer' ERROR entries.
-- Expected: zero
```

**All of S1–S12 must pass (S6 is blocked until schema mismatch resolved). Any FAIL or
timeout triggers immediate rollback.**

---

## Stop Conditions (any triggers immediate rollback)

| # | Condition |
|---|-----------|
| 1 | Non-allowlisted live write: any `user_topic_mastery_audit` row where `user_id = '<CONTROL_USER_UUID>' AND attempt_id = '<CONTROL_ATTEMPT_ID>'`; or any row with `at >= '<LIVE_DEPLOY_TIMESTAMP>'` for any `user_id NOT IN ('<CANARY_USER_UUID>', '<CONTROL_USER_UUID>')` |
| 2 | Missing audit row: canary attempt submitted and `mastery_retry` completed but no `user_topic_mastery_audit` row exists |
| 3 | Delta mismatch: `abs(proposed_delta_db − delta_applied_db) > 0.01` for any topic |
| 4 | Duplicate audit row: count > 1 for any `(canary_user, topic_id, attempt_id)` |
| 5 | `mastery_score` (i.e. `after_mastery_db`) outside `[0, 100]` |
| 6 | Invalid correction category: any value not in `('concept_gap','memory_gap','careless','speed_issue','option_trap')` |
| 7 | Duplicate drafted correction: count > 1 for any `(mock_test_id, user_id, category, topic)` with `state='drafted'` |
| 8 | Incomplete classification coverage at mastery processing time (`MasteryClassificationNotReady` raised; check `mock_attempt_jobs.last_error`) |
| 9 | Pending or failed live `mastery_retry` job that cannot drain (`mastery_flag_state='live'`, `status='failed'`, non-retryable) |
| 10 | SHA or fingerprint mismatch detected at any point |
| 11 | 15-minute canary window expires before all of S1–S12 confirmed |

> ⚠️ **Partial-write warning:** A writer exception at `_apply_error_patterns` does NOT
> imply zero live mutation. The live write order is (1) shadow, (2) mastery + audit rows
> (via `apply_mock_mastery_delta` RPC — atomic for its own writes), (3) error patterns,
> (4) corrections. A failure at step (3) means mastery and audit rows from step (2) may
> already be committed. When any stop condition fires, check `user_topic_mastery` and
> `user_topic_mastery_audit` for both users before concluding no live mutation occurred.
> Rollback must cover all four surfaces — not just error patterns.

Stop condition 1 diagnostic query:
```sql
SELECT user_id, attempt_id, topic_id, at
FROM public.user_topic_mastery_audit
WHERE
  (
    user_id = '<CONTROL_USER_UUID>'::uuid
    AND attempt_id = '<CONTROL_ATTEMPT_ID>'::uuid
  )
  OR (
    user_id NOT IN (
      '<CANARY_USER_UUID>'::uuid,
      '<CONTROL_USER_UUID>'::uuid
    )
    AND at >= '<LIVE_DEPLOY_TIMESTAMP>'::timestamptz
  );
-- Expected: zero rows. Any row = Stop Condition 1 — rollback immediately.
```

---

## Rollback Procedure

**Trigger:** any stop condition fires, or 15-minute window expires without full
confirmation.

**Immutability rule:** `user_topic_mastery_audit` rows are **immutable**. The table has a
unique constraint on `(user_id, topic_id, attempt_id)` (migration 144). NEVER insert a
second row for the same triple — the DB will reject it with 23505. All rollback audit
trail goes into `admin_audit_logs` only.

**`updated_at` restoration:** `user_topic_mastery` has a BEFORE UPDATE trigger (migration
116) that sets `updated_at = NOW()` on every UPDATE. Do not attempt to restore the
original `updated_at` value — the trigger will overwrite it. Restore only `mastery_score`,
identified by row `id`.

**Partial-write warning:** The live write order is (1) `_write_shadow`, (2) `_apply_mastery`
+ `user_topic_mastery_audit` (via `apply_mock_mastery_delta` RPC — atomic for its own writes),
(3) `_apply_error_patterns`, (4) `_draft_correction_tasks`. A writer exception at
`_apply_error_patterns` does not imply zero live mutation. Mastery and audit rows from
step (2) may already be committed before the error-pattern failure occurs. Always check
`user_topic_mastery` and `user_topic_mastery_audit` for both users before concluding no
live mutation occurred — and restore all applicable surfaces regardless of which step failed.

### Step 1 — Set FF=shadow and redeploy

Set `FF_MOCK_MASTERY_WRITES=shadow` on Render. Deploy. Confirm:
- Render env var panel shows `FF_MOCK_MASTERY_WRITES=shadow`
- `GET /api/health` returns `{"status": "ok", "service": "career-copilot", "ts": "..."}`
- No pending or running live-pinned mastery_retry jobs remain (see Step 3 drain query):
  ```sql
  SELECT count(*) AS live_pending FROM public.mock_attempt_jobs
  WHERE job_kind='mastery_retry' AND mastery_flag_state='live' AND status IN ('pending','running');
  ```
  Expected: 0 (or draining — wait for Step 3 before proceeding to data restore)
- Do NOT submit a new production attempt to confirm FF rollback. Use Render env var panel
  and absence of active live-pinned jobs as proof.

### Step 2 — Verify effective mode shadow

```sql
SELECT mastery_flag_state, status, count(*)
FROM public.mock_attempt_jobs
WHERE job_kind    = 'mastery_retry'
  AND created_at  > now() - interval '5 minutes'
GROUP BY mastery_flag_state, status;
-- Expected: mastery_flag_state = 'shadow' for all new jobs
```

### Step 3 — Query and drain live mastery_retry jobs for canary/control attempt_ids

```sql
SELECT id, attempt_id, status, mastery_flag_state, attempts, last_error
FROM public.mock_attempt_jobs
WHERE job_kind          = 'mastery_retry'
  AND mastery_flag_state = 'live'
  AND attempt_id         IN ('<CANARY_ATTEMPT_ID>', '<CONTROL_ATTEMPT_ID>');
-- Wait until every row has status IN ('done', 'failed').
-- A 'failed' job will not re-execute after FF=shadow — safe to proceed.
-- A 'running' job: wait for completion before proceeding.
-- Any live-pinned job that cannot drain blocks completion — escalate if stuck.
```

### Step 4a — Restore canary user mastery (one transaction)

**Dry-run on staging/clone first:** execute `BEGIN`, verify SELECT in 4a-3 matches
`canary_mastery_baseline` (P7), then run `ROLLBACK`. Only after staging verification,
replace `ROLLBACK` with `COMMIT` for production.

```sql
BEGIN;

-- 4a-1: Restore existing topics from canary_mastery_baseline (P7)
--   Scope: exam_id IS NULL AND exam_phase_id IS NULL (mock mastery only).
--   Use row id from P7 to identify exact rows — do not match by topic_id alone.
--   Do NOT set updated_at — BEFORE UPDATE trigger (migration 116) sets it automatically.
UPDATE public.user_topic_mastery
SET
  mastery_score = baseline.mastery_score
FROM (VALUES
  -- ('<row_id>'::uuid, <mastery_score>::numeric),
  -- One row per id in P7. If P7 was empty, this UPDATE touches zero rows — correct.
  (NULL::uuid, NULL::numeric)
) AS baseline(id, mastery_score)
WHERE public.user_topic_mastery.id            = baseline.id
  AND public.user_topic_mastery.user_id       = '<CANARY_USER_UUID>'::uuid
  AND public.user_topic_mastery.exam_id       IS NULL
  AND public.user_topic_mastery.exam_phase_id IS NULL
  AND baseline.id IS NOT NULL;

-- 4a-2: Delete topics created by canary that were absent from P7 baseline
DELETE FROM public.user_topic_mastery
WHERE user_id       = '<CANARY_USER_UUID>'::uuid
  AND exam_id       IS NULL
  AND exam_phase_id IS NULL
  AND id NOT IN (
    -- List all id values from P7 baseline.
    -- If P7 was empty, use a placeholder that matches nothing:
    '00000000-0000-0000-0000-000000000000'::uuid
  )
  AND topic_id IN (
    SELECT topic_id
    FROM public.user_topic_mastery_audit
    WHERE attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
      AND user_id    = '<CANARY_USER_UUID>'::uuid
  );

-- 4a-3: Verify — must match P7 topic_id/mastery_score row-for-row before committing
SELECT id, topic_id, mastery_score
FROM public.user_topic_mastery
WHERE user_id       = '<CANARY_USER_UUID>'::uuid
  AND exam_id       IS NULL
  AND exam_phase_id IS NULL
ORDER BY topic_id;

ROLLBACK; -- Replace with COMMIT after staging dry-run verified
```

### Step 4b — Restore control user mastery and verify all control surfaces

Always run this step — do not skip even if C1 showed `control_live_rows = 0`:

- **If Stop Condition 1 fired** (unexpected live writes to control user): restore mastery
  using the same pattern as Step 4a, substituting `<CONTROL_USER_UUID>`,
  `control_mastery_baseline` (P8), and `<CONTROL_ATTEMPT_ID>`. Then restore correction
  tasks using Step 6 pattern substituting `<CONTROL_USER_UUID>` and `<CONTROL_ATTEMPT_ID>`.
- **If control user appears clean** (C1 confirmed `control_live_rows = 0`): verify all
  surfaces are still at baseline — do not assume they are.

```sql
BEGIN;

-- 4b-1: Restore control user mastery if Stop Condition 1 fired
--   (use same 4a-1/4a-2 pattern with values from P8 control_mastery_baseline)
--   If control user had no live writes, skip 4b-1 and go to 4b-2 verification.

-- 4b-2: Verify control user mastery matches P8 baseline row-for-row
SELECT id, topic_id, mastery_score
FROM public.user_topic_mastery
WHERE user_id       = '<CONTROL_USER_UUID>'::uuid
  AND exam_id       IS NULL
  AND exam_phase_id IS NULL
ORDER BY topic_id;
-- Must match P8 exactly (expected: no changes if SC1 did not fire).

-- 4b-3: Verify control user correction tasks match P8b baseline (expected: 0 new rows)
SELECT count(*) AS unexpected_control_corrections
FROM public.mock_correction_tasks ct
JOIN public.mock_tests mt ON mt.id = ct.mock_test_id
WHERE ct.user_id          = '<CONTROL_USER_UUID>'::uuid
  AND mt.mock_attempt_id  = '<CONTROL_ATTEMPT_ID>'::uuid;
-- Expected: 0. If > 0 and SC1 fired: delete following Step 6 pattern for control user.

-- 4b-4: Verify control user audit rows (immutable — cannot delete if present)
SELECT count(*) FROM public.user_topic_mastery_audit
WHERE user_id = '<CONTROL_USER_UUID>'::uuid;
-- Expected: 0 (immutable rows cannot be deleted — if > 0, escalate)

ROLLBACK; -- Replace with COMMIT after staging dry-run verified
```

### Step 5 — Restore user_topic_error_patterns

⛔ **BLOCKED — schema mismatch.** `_apply_error_patterns` (`mastery_writer.py` lines
289–294) upserts `microtopic_id` and `error_count` into `user_topic_error_patterns`,
but those columns do not exist (migration 033). Because the writer will fail at the DB
layer before writing any error-pattern rows, no actual canary-written rows are expected
in this table. Until the schema mismatch is resolved in a separate code PR and the
actual written columns confirmed, rollback Step 5 cannot be specified. If the mismatch
is fixed before canary execution, update this step with SQL matching the deployed schema.

> ⚠️ **Partial-write warning:** A failure at `_apply_error_patterns` does not mean no
> prior live writes occurred. `_apply_mastery` (via `apply_mock_mastery_delta` RPC) commits
> mastery and `user_topic_mastery_audit` rows before `_apply_error_patterns` runs. Even if
> Step 5 is blocked, always execute Steps 4a and 4b to check and restore mastery for both
> users.

### Step 6 — Delete drafted mock_correction_tasks

**STOP if any row has `state='applied'`** — automated rollback is forbidden; escalate
for manual remediation before proceeding.

Dry-run on staging first.

```sql
BEGIN;

-- 6a: Safety gate — MUST return 0 before continuing
SELECT count(*) AS applied_rows
FROM public.mock_correction_tasks
WHERE user_id    = '<CANARY_USER_UUID>'::uuid
  AND state      = 'applied'
  AND mock_test_id IN (
    SELECT id FROM public.mock_tests
    WHERE mock_attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
  );
-- If 6a applied_rows > 0: ROLLBACK immediately, escalate for manual remediation.

-- 6b: Delete drafted corrections linked to canary mock_test_id absent from P10 baseline
DELETE FROM public.mock_correction_tasks
WHERE user_id     = '<CANARY_USER_UUID>'::uuid
  AND state       = 'drafted'
  AND mock_test_id IN (
    SELECT id FROM public.mock_tests
    WHERE mock_attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
  )
  AND id NOT IN (
    -- List correction task IDs from canary_correction_baseline (P10) that preexisted.
    -- If P10 was empty (fresh disposable user), this list is empty and all canary
    -- drafted rows are deleted.
    '00000000-0000-0000-0000-000000000000'::uuid
  );

-- 6c: Verify
SELECT count(*) AS remaining_drafted
FROM public.mock_correction_tasks
WHERE user_id     = '<CANARY_USER_UUID>'::uuid
  AND state       = 'drafted'
  AND mock_test_id IN (
    SELECT id FROM public.mock_tests
    WHERE mock_attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
  );
-- Expected: 0 (or count matching P10 baseline if baseline had pre-existing rows)

ROLLBACK; -- Replace with COMMIT after staging dry-run verified
```

### Step 7 — Verify study_tasks unchanged

```sql
SELECT count(*) AS unexpected_study_tasks
FROM public.study_tasks
WHERE metadata->>'mock_test_id' IN (
  SELECT id::text FROM public.mock_tests
  WHERE mock_attempt_id = '<CANARY_ATTEMPT_ID>'
)
AND task_type = 'mock_correction';
-- Expected: 0. If > 0: STOP — manual investigation required before completing rollback.
```

### Step 8 — Post-rollback verification

```sql
-- V1: FF=shadow confirmed (new mastery_retry jobs carry shadow flag)
SELECT mastery_flag_state, count(*)
FROM public.mock_attempt_jobs
WHERE job_kind   = 'mastery_retry'
  AND created_at > now() - interval '5 minutes'
GROUP BY mastery_flag_state;
-- Expected: mastery_flag_state = 'shadow'

-- V2: No active live-pinned job can write live
SELECT count(*) AS live_pinned
FROM public.mock_attempt_jobs
WHERE job_kind           = 'mastery_retry'
  AND mastery_flag_state  = 'live'
  AND status              IN ('pending', 'running');
-- Expected: 0

-- V3: Canary user mastery row count matches P7 baseline
SELECT count(*) FROM public.user_topic_mastery
WHERE user_id       = '<CANARY_USER_UUID>'
  AND exam_id       IS NULL
  AND exam_phase_id IS NULL;
-- Must match P7 row count

-- V4: Control user mastery unchanged from P8 baseline
SELECT count(*) FROM public.user_topic_mastery
WHERE user_id       = '<CONTROL_USER_UUID>'
  AND exam_id       IS NULL
  AND exam_phase_id IS NULL;
-- Must match P8 row count

-- V5: Control user correction tasks unchanged from P8b baseline
SELECT count(*) FROM public.mock_correction_tasks ct
JOIN public.mock_tests mt ON mt.id = ct.mock_test_id
WHERE ct.user_id          = '<CONTROL_USER_UUID>'
  AND mt.mock_attempt_id  = '<CONTROL_ATTEMPT_ID>';
-- Must match P8b count (expected: 0 for fresh disposable user)

-- V6: Scheduler normal — GET /api/admin/jobs: no stuck jobs, last_run_at recent
```

### Final Step — Record completed rollback in admin_audit_logs

> ⚠️ **Execute this step last — only after Steps 1–8 all pass and are verified.**
> This step is NOT executable while any restore step is blocked, failed, or unverified.
> Do not record `rollback_complete=true` or any field implying a complete rollback while
> Step 5 (error-pattern restore) is blocked or any other step has not cleared. Record the
> actual state of Step 5 explicitly in `affected_error_pattern_ids` (see template below).
>
> Step 5 (error-pattern restore) is currently BLOCKED pending schema-contract resolution.
> The final audit step cannot indicate a complete rollback until that blocker clears.

**Do NOT insert into `user_topic_mastery_audit`** (immutable; unique constraint would
reject a second row for the same `(user_id, topic_id, attempt_id)`). Write exactly one
`admin_audit_logs` row. The `WHERE NOT EXISTS` guard makes this insert idempotent on
`(action, entity_type, entity_id)` if the rollback procedure is run more than once.

```sql
BEGIN;

INSERT INTO public.admin_audit_logs (
  actor_id,
  actor_email,
  action,
  entity_type,
  entity_id,
  old_value,
  new_value,
  notes
)
SELECT
  NULL::uuid,
  '<OPERATOR_EMAIL>',
  'study_os.mock_mastery_canary.rollback',
  'mock_mastery_canary',
  '<CANARY_RUN_ID>',
  jsonb_build_object(
    'stop_condition_fired',               '<STOP_CONDITION_NUMBER_AND_DESCRIPTION>',
    'canary_user_id',                     '<CANARY_USER_UUID>',
    'control_user_id',                    '<CONTROL_USER_UUID>',
    'canary_attempt_id',                  '<CANARY_ATTEMPT_ID>',
    'control_attempt_id',                 '<CONTROL_ATTEMPT_ID>',
    'canary_affected_audit_ids',          coalesce(
      (SELECT jsonb_agg(id ORDER BY id)
       FROM public.user_topic_mastery_audit
       WHERE attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
         AND user_id    = '<CANARY_USER_UUID>'::uuid),
      '[]'::jsonb
    ),
    'control_affected_audit_ids',         coalesce(
      (SELECT jsonb_agg(id ORDER BY id)
       FROM public.user_topic_mastery_audit
       WHERE attempt_id = '<CONTROL_ATTEMPT_ID>'::uuid
         AND user_id    = '<CONTROL_USER_UUID>'::uuid),
      '[]'::jsonb
    ),
    'canary_pre_rollback_mastery',        coalesce(
      (SELECT jsonb_object_agg(topic_id::text, after_mastery_db)
       FROM public.user_topic_mastery_audit
       WHERE attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
         AND user_id    = '<CANARY_USER_UUID>'::uuid),
      '{}'::jsonb
    ),
    'control_pre_rollback_mastery',       coalesce(
      (SELECT jsonb_object_agg(topic_id::text, after_mastery_db)
       FROM public.user_topic_mastery_audit
       WHERE attempt_id = '<CONTROL_ATTEMPT_ID>'::uuid
         AND user_id    = '<CONTROL_USER_UUID>'::uuid),
      '{}'::jsonb
    ),
    'deleted_canary_correction_task_ids', coalesce(
      (SELECT jsonb_agg(ct.id ORDER BY ct.id)
       FROM public.mock_correction_tasks ct
       JOIN public.mock_tests mt ON mt.id = ct.mock_test_id
       WHERE ct.user_id         = '<CANARY_USER_UUID>'::uuid
         AND mt.mock_attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
         AND ct.state           = 'drafted'),
      '[]'::jsonb
    ),
    'deleted_control_correction_task_ids', coalesce(
      (SELECT jsonb_agg(ct.id ORDER BY ct.id)
       FROM public.mock_correction_tasks ct
       JOIN public.mock_tests mt ON mt.id = ct.mock_test_id
       WHERE ct.user_id         = '<CONTROL_USER_UUID>'::uuid
         AND mt.mock_attempt_id = '<CONTROL_ATTEMPT_ID>'::uuid
         AND ct.state           = 'drafted'),
      '[]'::jsonb
    ),
    'affected_error_pattern_ids',         to_jsonb(
      'BLOCKED — error-pattern schema mismatch not resolved; '
      'no canary rows expected (writer fails before writing error patterns); '
      'update this field when schema blocker clears'::text
    )
  ),
  jsonb_build_object(
    'canary_restored_baseline_mastery',  coalesce(
      (SELECT jsonb_object_agg(topic_id::text, mastery_score)
       FROM public.user_topic_mastery
       WHERE user_id       = '<CANARY_USER_UUID>'::uuid
         AND exam_id       IS NULL
         AND exam_phase_id IS NULL),
      '{}'::jsonb
    ),
    'control_restored_baseline_mastery', coalesce(
      (SELECT jsonb_object_agg(topic_id::text, mastery_score)
       FROM public.user_topic_mastery
       WHERE user_id       = '<CONTROL_USER_UUID>'::uuid
         AND exam_id       IS NULL
         AND exam_phase_id IS NULL),
      '{}'::jsonb
    ),
    'study_task_verification_result',    to_jsonb('<pass | stop_manual_investigation_required>'::text),
    'post_rollback_verification_result', to_jsonb('<summary of Step 8 V1–V6 outcomes>'::text),
    'rollback_completion_timestamp',     now()
  ),
  'Bounded live canary rollback. Stop condition: see old_value.stop_condition_fired. '
  'Mastery reverted to pre-canary P7/P8 baselines for both users. '
  'user_topic_mastery_audit rows are immutable — see old_value.*_affected_audit_ids. '
  'Error-pattern restore blocked (schema mismatch) — see old_value.affected_error_pattern_ids. '
  'Dry-run verified on staging before production apply. '
  'Inserted only after Steps 1–8 all passed and were verified.'
WHERE NOT EXISTS (
  SELECT 1 FROM public.admin_audit_logs
  WHERE action      = 'study_os.mock_mastery_canary.rollback'
    AND entity_type = 'mock_mastery_canary'
    AND entity_id   = '<CANARY_RUN_ID>'
);

COMMIT;
```

---

## Rollback SQL — Staging Dry-Run Checklist

Before production apply, run all transaction blocks against a staging/clone DB seeded
with a snapshot taken at or before the P1 SHA recording time:

- [ ] Step 4a dry-run: SELECT in 4a-3 matches P7 exactly (id, topic_id, mastery_score) → ROLLBACK
- [ ] Step 4b dry-run (Stop Condition 1 path): SELECT in 4b-2 matches P8 exactly → ROLLBACK; 4b-3 count = 0 → ROLLBACK
- [ ] Step 4b dry-run (clean control path): verify all control surfaces at baseline → ROLLBACK
- [ ] Step 5: BLOCKED — cannot dry-run until schema mismatch is resolved
- [ ] Step 6 dry-run: remaining_drafted in 6c = 0 → ROLLBACK
- [ ] All applicable staging verifications complete before any production COMMIT

Steps 4a, 4b, and 6 are independent and may run in parallel on staging. Final Step runs
in production only after Steps 1–8 all pass and are verified.
- [ ] Final Step: WHERE NOT EXISTS guard makes insert idempotent on (action, entity_type, entity_id); verify it inserts exactly one row, then re-running inserts zero

---

## Post-Canary (if all success criteria pass)

1. Set `FF_MOCK_MASTERY_WRITES=shadow` (not live — live activation requires PR-9 approval).
2. Wait for the 15-minute window to close, then capture all post-canary query outputs
   (S1–S12) and freeze the evidence outside Git.
3. Attach frozen evidence to PR-9 before PR-9 requests final approval.
4. Confirm no correction task has `state='applied'` for the canary attempt (the canary
   window is correction-draft-only; no task application permitted).

---

## Evidence Location

Canary evidence (query outputs, Render log excerpts, screenshots, metrics) must be
attached to PR-9. Do not commit run-specific UUIDs or query results into this document —
use a separate dated evidence file under `docs/audits/`.

---

*Merging this PR changes no feature flag (`FF_MOCK_MASTERY_WRITES`) and no allowlist
(`FF_MOCK_MASTERY_LIVE_USER_IDS` or equivalent). The Render transition is a separate
operator action. This document grants no authorization to perform the canary.*
