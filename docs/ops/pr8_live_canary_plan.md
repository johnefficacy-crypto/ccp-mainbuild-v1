# PR8: Bounded Mock Mastery Live Canary Plan

**Type:** Operational plan — docs/runbook only  
**Status:** EXECUTION BLOCKED — `FF_MOCK_MASTERY_LIVE_USER_IDS` (or equivalent per-user
allowlist) is **not implemented** in the deployed codebase. This plan cannot be executed
until the allowlist implementation PR merges, deploys, and is validated. See
Dependency §3 and Allowlist Behavior §below.

> **Required statement — merging this PR:**
> "Merging this PR changes no feature flag (`FF_MOCK_MASTERY_WRITES`) and no
> allowlist (`FF_MOCK_MASTERY_LIVE_USER_IDS` or equivalent).
> The Render transition is a separate operator action.
> This document grants no authorization to perform the canary."

---

## Dependencies (all must be PASS before canary execution)

| # | Dependency | Status |
|---|------------|--------|
| 1 | PR-6 final candidate revalidation | **PASS** |
| 2 | PR-7 14-day shadow gate | **PASS** |
| 3 | Live-user allowlist merged, deployed, and validated | **BLOCKED — not implemented** |
| 4 | Correction atomicity (PR-5B) deployed — migration 182 applied | **PASS** |
| 5 | Scheduler automatic-drain evidence | OPERATOR PENDING |
| 6 | Validation fingerprint unchanged since PR-6 | verify at preflight |

**Dependency §3 detail:** As of this document's authoring, `MasteryWriter.process_attempt_sync`
(`app/backend/app/study_os/mastery_writer.py`, lines 74–106) contains no per-user gate.
When `FF_MOCK_MASTERY_WRITES=live`, live writes execute for **every** user. There is no
`FF_MOCK_MASTERY_LIVE_USER_IDS` environment variable, no allowlist table check, and no
equivalent mechanism. A global unrestricted live flip is **forbidden** — do not proceed
without the allowlist PR.

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

---

## Allowlist Behavior (confirm implementation before execution)

**Required implementation location:** `MasteryWriter.process_attempt_sync` in
`app/backend/app/study_os/mastery_writer.py`, after `_load_current_mastery` (line 95)
and before the `if self.flag_state == "live":` branch (line 103). The check must read
`analytics.user_id` and compare it against the allowlist.

**Allowlist scope:** per-user UUID, not per-attempt or per-session. Once a user UUID is
in the allowlist and `FF_MOCK_MASTERY_WRITES=live`, all their attempts receive live writes
until removed from the allowlist.

**Required behavior matrix — confirm from deployed code before marking this plan READY:**

| Combination | Expected behavior |
|-------------|-------------------|
| Allowlisted user + `FF=live` | Live writes: `_apply_mastery`, `_apply_error_patterns`, `_draft_correction_tasks` execute; `mastery_flag_state=live` audit row written |
| Non-allowlisted user + `FF=live` | Shadow only: `_write_shadow` with `flag_state='shadow'`; no live writes; no `user_topic_mastery_audit` row |
| Any user + `FF=shadow` | Shadow only: `_write_shadow` with `flag_state='shadow'`; no live writes regardless of allowlist |

If the non-allowlisted + `FF=live` behavior is `off` (skip entirely) rather than `shadow`,
document it here and update Stop Condition §1 accordingly. If behavior is ambiguous in
the deployed code, **STOP** and resolve before executing the canary.

---

## Preflight (operator executes immediately before Render action)

All queries are scoped to exact user IDs — no time-window clauses. Save all outputs
before proceeding; they form the rollback baseline.

```sql
-- P1: Record current deployed SHA
-- Obtain from Render dashboard → Service → Deploys, or from healthcheck metadata.
-- SHA: _______________________________________________

-- P2: Validation fingerprint must match PR-6 candidate
SELECT md5(
  string_agg(
    attempt_id::text || '|' || topic_id::text || '|' || proposed_delta_db::text,
    ','
    ORDER BY attempt_id, topic_id
  )
) AS fingerprint
FROM public.mock_mastery_shadow
WHERE flag_state = 'shadow';
-- Expected: <PR6_FINGERPRINT> (from PR-6 revalidation evidence doc)
-- STOP if mismatch.

-- P3: Confirm FF currently shadow — behavioral confirmation
-- Submit a throwaway attempt and check the resulting mastery_retry job:
SELECT job_kind, mastery_flag_state, status
FROM public.mock_attempt_jobs
WHERE job_kind = 'mastery_retry'
  AND created_at > now() - interval '5 minutes'
ORDER BY created_at DESC LIMIT 5;
-- Expected: mastery_flag_state = 'shadow' for any newly created job

-- P4: Allowlist contains ONLY the named canary user UUID
-- Read deployed config: env var FF_MOCK_MASTERY_LIVE_USER_IDS or allowlist table.
-- Value observed: _______________________________________________
-- Expected: exactly '<CANARY_USER_UUID>' — no other UUIDs
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

-- P7: Baseline mastery for canary user (save full result)
SELECT topic_id, mastery_score, updated_at
FROM public.user_topic_mastery
WHERE user_id = '<CANARY_USER_UUID>'
ORDER BY topic_id;
-- Save as: canary_mastery_baseline

-- P8: Baseline mastery for control user (save full result)
SELECT topic_id, mastery_score, updated_at
FROM public.user_topic_mastery
WHERE user_id = '<CONTROL_USER_UUID>'
ORDER BY topic_id;
-- Save as: control_mastery_baseline

-- P9: Error patterns baseline for canary user (save full result)
SELECT topic_id, microtopic_id, error_type, error_count
FROM public.user_topic_error_patterns
WHERE user_id = '<CANARY_USER_UUID>'
ORDER BY topic_id, microtopic_id, error_type;
-- Save as: canary_error_baseline

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
-- Expected: 0. If nonzero, document exactly and reconcile against prior run state.

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

Read deployed config and confirm `FF_MOCK_MASTERY_LIVE_USER_IDS` (or equivalent) contains
exactly `<CANARY_USER_UUID>` and no other UUIDs. Do not continue if any other UUID is present.

### Step 2 — Deploy while FF remains shadow

Deploy the PR-6 candidate SHA with `FF_MOCK_MASTERY_WRITES=shadow`. Confirm via
healthcheck that `{"flag": "shadow"}` is returned before proceeding.

### Step 3 — Set FF=live and deploy

Set `FF_MOCK_MASTERY_WRITES=live` on Render. Deploy. Confirm `{"flag": "live"}` from
healthcheck. **Start 15-minute timer.**

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
-- Expected: ≥1 row (one per mastery-eligible topic)

-- S2: user_topic_mastery_audit row exists for (canary_user, topic, attempt_id)
SELECT user_id, topic_id, attempt_id, before_mastery_db, after_mastery_db, delta_applied_db
FROM public.user_topic_mastery_audit
WHERE attempt_id = '<CANARY_ATTEMPT_ID>'
  AND user_id    = '<CANARY_USER_UUID>';
-- Expected: ≥1 row

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
SELECT
  a.topic_id,
  a.before_mastery_db,
  a.delta_applied_db,
  a.after_mastery_db,
  GREATEST(0, LEAST(100, a.before_mastery_db + a.delta_applied_db)) AS expected_after,
  abs(a.after_mastery_db
      - GREATEST(0, LEAST(100, a.before_mastery_db + a.delta_applied_db)))  AS clamp_diff,
  CASE WHEN a.after_mastery_db BETWEEN 0 AND 100
            AND abs(a.after_mastery_db
                    - GREATEST(0, LEAST(100, a.before_mastery_db + a.delta_applied_db))) <= 0.01
       THEN 'PASS' ELSE 'FAIL' END AS check_result
FROM public.user_topic_mastery_audit a
WHERE a.attempt_id = '<CANARY_ATTEMPT_ID>'
  AND a.user_id    = '<CANARY_USER_UUID>';
-- Expected: all check_result = 'PASS'

-- S6: user_topic_error_patterns updated for canary user
SELECT topic_id, microtopic_id, error_type, error_count
FROM public.user_topic_error_patterns
WHERE user_id = '<CANARY_USER_UUID>'
ORDER BY topic_id, microtopic_id, error_type;
-- Compare to P9 baseline — expect new or updated rows for canary topics

-- S7: mock_correction_tasks drafted for canary user (if classifications complete)
SELECT ct.id, ct.category, ct.topic, ct.state
FROM public.mock_correction_tasks ct
JOIN public.mock_tests mt ON mt.id = ct.mock_test_id
WHERE mt.mock_attempt_id = '<CANARY_ATTEMPT_ID>'
  AND ct.user_id          = '<CANARY_USER_UUID>';
-- Expected: state='drafted' rows; may be empty only if all questions correct

-- S8: All correction categories valid (063 check constraint)
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

-- S10: Resubmit is no-op — retrigger mastery_retry for <CANARY_ATTEMPT_ID> then verify
SELECT count(*) AS row_count, max(at) AS last_at
FROM public.user_topic_mastery_audit
WHERE attempt_id = '<CANARY_ATTEMPT_ID>'
  AND user_id    = '<CANARY_USER_UUID>';
-- Expected: same count as S2, last_at unchanged

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
-- Check Render log stream for `career_copilot.study_os.mastery_writer` ERROR entries.
-- Expected: zero
```

**All of S1–S12 must pass. Any FAIL or timeout triggers immediate rollback.**

---

## Stop Conditions (any triggers immediate rollback)

| # | Condition |
|---|-----------|
| 1 | Non-allowlisted live write: any `user_topic_mastery_audit` row for `user_id ≠ <CANARY_USER_UUID>` |
| 2 | Missing audit row: canary attempt submitted and `mastery_retry` completed but no `user_topic_mastery_audit` row exists |
| 3 | Delta mismatch: `abs(proposed_delta_db − delta_applied_db) > 0.01` for any topic |
| 4 | Duplicate audit row: count > 1 for any `(canary_user, topic_id, attempt_id)` |
| 5 | `mastery_score` (i.e. `after_mastery_db`) outside `[0, 100]` |
| 6 | Invalid correction category: any value not in `('concept_gap','memory_gap','careless','speed_issue','option_trap')` |
| 7 | Duplicate drafted correction: count > 1 for any `(mock_test_id, user_id, category, topic)` with `state='drafted'` |
| 8 | Incomplete classification coverage at mastery processing time (`MasteryClassificationNotReady` raised, check `mock_attempt_jobs.last_error`) |
| 9 | Pending or failed live `mastery_retry` job that cannot drain (`mastery_flag_state='live'`, `status='failed'`, non-retryable) |
| 10 | SHA or fingerprint mismatch detected at any point |
| 11 | 15-minute canary window expires before all of S1–S12 confirmed |

---

## Rollback Procedure

**Trigger:** any stop condition fires, or 15-minute window expires without full confirmation.

**Immutability rule:** `user_topic_mastery_audit` rows are **immutable**. The table has a
unique constraint on `(user_id, topic_id, attempt_id)` (migration 144). NEVER insert a
second row for the same triple — the DB will reject it with 23505 and any attempt to
do so signals a logic error. All rollback audit trail goes into `admin_audit_logs` only.

### Step 1 — Set FF=shadow and redeploy

Set `FF_MOCK_MASTERY_WRITES=shadow` on Render. Deploy. Confirm:
- Healthcheck returns `{"flag": "shadow"}`
- Submit a test attempt and confirm the resulting `mastery_retry` job has
  `mastery_flag_state='shadow'`

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
-- Wait until every row has status ∈ {'done', 'failed'}.
-- A 'failed' job will not re-execute after FF=shadow — safe to proceed.
-- A 'running' job: wait for completion; do not proceed until none remain running.
-- Any live-pinned job that cannot drain blocks completion — escalate if stuck.
```

### Step 4 — Restore canary user mastery (one transaction)

**Dry-run on staging/clone first:** execute `BEGIN`, verify all SELECT outputs match
`canary_mastery_baseline` (P7), then run `ROLLBACK`. Only after staging verification,
replace `ROLLBACK` with `COMMIT` for production.

```sql
BEGIN;

-- 4a: Restore existing topics from canary_mastery_baseline (P7)
--     Replace the VALUES list with actual rows from the P7 query output.
UPDATE public.user_topic_mastery
SET
  mastery_score = baseline.mastery_score,
  updated_at    = baseline.updated_at
FROM (VALUES
  -- ('<topic_uuid>'::uuid, <mastery_score>::numeric, '<updated_at>'::timestamptz),
  -- One row per topic in P7. If P7 was empty, this UPDATE touches zero rows — correct.
  (NULL::uuid, NULL::numeric, NULL::timestamptz)
) AS baseline(topic_id, mastery_score, updated_at)
WHERE public.user_topic_mastery.user_id  = '<CANARY_USER_UUID>'::uuid
  AND public.user_topic_mastery.topic_id  = baseline.topic_id
  AND baseline.topic_id IS NOT NULL;

-- 4b: Delete topics created by canary that were absent from canary_mastery_baseline (P7)
DELETE FROM public.user_topic_mastery
WHERE user_id  = '<CANARY_USER_UUID>'::uuid
  AND topic_id NOT IN (
    -- List all topic_ids from P7. If P7 was empty, use a values list that matches nothing:
    NULL::uuid
  )
  AND topic_id IN (
    SELECT topic_id
    FROM public.user_topic_mastery_audit
    WHERE attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
      AND user_id    = '<CANARY_USER_UUID>'::uuid
  );

-- 4c: Verify — must match P7 row-for-row before committing
SELECT topic_id, mastery_score, updated_at
FROM public.user_topic_mastery
WHERE user_id = '<CANARY_USER_UUID>'::uuid
ORDER BY topic_id;

ROLLBACK; -- Replace with COMMIT after staging dry-run verified
```

### Step 5 — Write rollback record to admin_audit_logs

**Do NOT insert into `user_topic_mastery_audit`** (immutable; unique constraint would
reject a second row for the same `(user_id, topic_id, attempt_id)`). Write exactly one
`admin_audit_logs` row with the following shape:

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
    'canary_attempt_id',   '<CANARY_ATTEMPT_ID>',
    'control_attempt_id',  '<CONTROL_ATTEMPT_ID>',
    'affected_audit_ids',  coalesce(
      (SELECT jsonb_agg(id ORDER BY id)
       FROM public.user_topic_mastery_audit
       WHERE attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
         AND user_id    = '<CANARY_USER_UUID>'::uuid),
      '[]'::jsonb
    ),
    'pre_rollback_mastery', coalesce(
      (SELECT jsonb_object_agg(topic_id::text, after_mastery_db)
       FROM public.user_topic_mastery_audit
       WHERE attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
         AND user_id    = '<CANARY_USER_UUID>'::uuid),
      '{}'::jsonb
    )
  ),
  jsonb_build_object(
    'restored_baseline_mastery', coalesce(
      (SELECT jsonb_object_agg(topic_id::text, mastery_score)
       FROM public.user_topic_mastery
       WHERE user_id = '<CANARY_USER_UUID>'::uuid),
      '{}'::jsonb
    ),
    'rollback_at', now()
  ),
  'Bounded live canary rollback. Mastery reverted to pre-canary P7 baseline. '
  'user_topic_mastery_audit rows are immutable — see old_value.affected_audit_ids. '
  'Dry-run verified on staging before production apply.';

COMMIT;
```

### Step 6 — Restore user_topic_error_patterns

Dry-run on staging first (BEGIN + verify + ROLLBACK).

```sql
BEGIN;

-- 6a: Delete canary-written error patterns for topics touched in the canary attempt
DELETE FROM public.user_topic_error_patterns
WHERE user_id  = '<CANARY_USER_UUID>'::uuid
  AND topic_id IN (
    SELECT topic_id
    FROM public.user_topic_mastery_audit
    WHERE attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
      AND user_id    = '<CANARY_USER_UUID>'::uuid
  );

-- 6b: Re-insert baseline rows from canary_error_baseline (P9)
--     Replace VALUES with actual rows from P9 output. If P9 was empty, skip 6b.
INSERT INTO public.user_topic_error_patterns
  (id, user_id, topic_id, microtopic_id, error_type, error_count)
VALUES
  -- ('<uuid>'::uuid, '<CANARY_USER_UUID>'::uuid, '<topic_id>'::uuid,
  --  '<microtopic_id>'::uuid, '<error_type>', <count>)
  -- One row per row in P9.
ON CONFLICT (user_id, topic_id, microtopic_id, error_type)
  DO UPDATE SET error_count = EXCLUDED.error_count;

-- 6c: Verify — must match P9 row-for-row
SELECT topic_id, microtopic_id, error_type, error_count
FROM public.user_topic_error_patterns
WHERE user_id = '<CANARY_USER_UUID>'::uuid
ORDER BY topic_id, microtopic_id, error_type;

ROLLBACK; -- Replace with COMMIT after staging dry-run verified
```

### Step 7 — Delete drafted mock_correction_tasks

**STOP if any row has `state='applied'`** — automated rollback is forbidden; escalate
for manual remediation before proceeding.

Dry-run on staging first.

```sql
BEGIN;

-- 7a: Safety gate — MUST return 0 before continuing
SELECT count(*) AS applied_rows
FROM public.mock_correction_tasks
WHERE user_id    = '<CANARY_USER_UUID>'::uuid
  AND state      = 'applied'
  AND mock_test_id IN (
    SELECT id FROM public.mock_tests
    WHERE mock_attempt_id = '<CANARY_ATTEMPT_ID>'::uuid
  );
-- If applied_rows > 0: ROLLBACK immediately, escalate for manual remediation.

-- 7b: Delete drafted corrections linked to canary mock_test_id absent from P10 baseline
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
    '<BASELINE_CORRECTION_ID_IF_ANY>'::uuid
  );

-- 7c: Verify
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

### Step 8 — Verify study_tasks and study_adaptation_events unchanged

```sql
-- No study_tasks should exist for canary mock_test_id (corrections not applied during window)
SELECT count(*) AS unexpected_study_tasks
FROM public.study_tasks
WHERE metadata->>'mock_test_id' IN (
  SELECT id::text FROM public.mock_tests
  WHERE mock_attempt_id = '<CANARY_ATTEMPT_ID>'
)
AND task_type = 'mock_correction';
-- Expected: 0. If > 0: STOP — manual investigation required before completing rollback.
```

### Post-rollback verification

```sql
-- V1: FF=shadow confirmed (behavioral — new mastery_retry jobs carry shadow flag)
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
WHERE user_id = '<CANARY_USER_UUID>';
-- Must match P7 row count

-- V4: Control user mastery unchanged
SELECT count(*) FROM public.user_topic_mastery
WHERE user_id = '<CONTROL_USER_UUID>';
-- Must match P8 row count

-- V5: Scheduler normal — GET /api/admin/jobs: no stuck jobs, last_run_at recent
```

---

## Rollback SQL — Staging Dry-Run Checklist

Before production apply, run all four transaction blocks (Steps 4, 5, 6, 7) against a
staging/clone DB seeded with a snapshot taken at or before the P1 SHA recording time:

- [ ] Step 4 dry-run: SELECT in 4c matches P7 exactly → ROLLBACK
- [ ] Step 5: runs cleanly (no staging required — admin_audit_logs write is idempotent on entity_id)
- [ ] Step 6 dry-run: SELECT in 6c matches P9 exactly → ROLLBACK
- [ ] Step 7 dry-run: remaining_drafted in 7c = 0 → ROLLBACK
- [ ] All four staging verifications complete before any production COMMIT

Steps 4, 6, and 7 are independent and may run in parallel on staging. Step 5 runs in
production only after Step 4 commits.

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
