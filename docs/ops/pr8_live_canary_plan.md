# PR8: Bounded Mock Mastery Live Canary Plan

**Type:** Operational plan  
**Prerequisite:** PR7 shadow gate passed  
**Status:** Draft — requires completion before approval

## Approval Authority

Live flag transitions for `FF_MOCK_MASTERY_WRITES` require sign-off from:

| Role | Required |
|------|----------|
| Engineering lead | Yes |
| Product owner | Yes |
| On-call operator | Yes (for rollback availability) |

## Candidate SHA

SHA from PR6 baseline: `______________________________`  
Verified on: `______________________________`

## Canary Identity / Traffic Scope

**Hard prerequisite — not optional:** The current feature flag
(`FF_MOCK_MASTERY_WRITES`) is **global** and applies to all platform
attempts uniformly. A live canary **MUST** be bounded to a named user
allowlist before this plan can be approved. Proceed with global flag
only if the allowlist implementation PR has merged and the allowlist
is non-empty with named consenting users.

Required implementation PR (must be merged before this plan is approved):

- [ ] User-allowlist implementation: check `user_id` against an explicit
      allow-list before calling `MasteryWriter.process_attempt_sync`.
      Platform attempts for users outside the allow-list remain in
      `FF_MOCK_MASTERY_WRITES=shadow` regardless of the global flag.

**Canary scope:** `______________________________` (list of user_ids or allowlist table name)

**Maximum attempts before mandatory review:** `______`

## Pre-Canary Queries

Run these before flipping the flag and save the output as the rollback baseline:

```sql
-- Baseline mastery snapshot for allowlisted users
select user_id, topic_id, mastery_score, updated_at
from public.user_topic_mastery
where user_id in (:allowlist_user_ids)
order by user_id, topic_id;

-- Baseline error patterns for allowlisted users
select user_id, topic_id, microtopic_id, error_type, error_count
from public.user_topic_error_patterns
where user_id in (:allowlist_user_ids)
order by user_id, topic_id;

-- Confirm zero live audit rows exist before canary
select count(*) from public.user_topic_mastery_audit
where reason = 'mock_submit' and user_id in (:allowlist_user_ids);

-- Record all attempt_ids in flight (to scope rollback precisely)
select id as attempt_id, user_id, created_at
from public.mock_attempts
where user_id in (:allowlist_user_ids)
order by created_at desc limit 50;
```

Save the attempt_id list as `:canary_attempt_ids` — the rollback below is
scoped to exact attempt_ids, not to a time window.

## Post-Canary Queries

Run after N attempts have processed:

```sql
-- Live audit trail for canary attempts only
select user_id, topic_id, attempt_id, before_mastery_db, after_mastery_db,
       delta_applied_db, at
from public.user_topic_mastery_audit
where attempt_id in (:canary_attempt_ids) and reason = 'mock_submit'
order by at desc;

-- Sign agreement vs shadow predictions
select
  s.attempt_id,
  s.topic_id,
  s.proposed_delta_db as shadow_delta,
  a.delta_applied_db as live_delta,
  case when (s.proposed_delta_db >= 0) = (a.delta_applied_db >= 0)
       then 'agree' else 'disagree' end as sign_agreement
from public.mock_mastery_shadow s
join public.user_topic_mastery_audit a
  on a.attempt_id = s.attempt_id and a.topic_id = s.topic_id
where a.attempt_id in (:canary_attempt_ids) and a.reason = 'mock_submit'
order by s.attempt_id;

-- Correction tasks drafted for canary attempts
select ct.id, ct.mock_test_id, ct.user_id, ct.category, ct.topic, ct.state, ct.created_at
from public.mock_correction_tasks ct
join public.mock_tests mt on mt.id = ct.mock_test_id
where mt.mock_attempt_id in (:canary_attempt_ids)
order by ct.created_at desc;
```

## Success Thresholds (Canary)

| Metric | Threshold |
|--------|-----------|
| Live vs shadow sign agreement | ≥ 95% |
| Outliers (|delta| > 15 db) | 0 |
| Mastery-audit idempotency violations | 0 |
| Correction-task duplicate violations | 0 |

## Stop Conditions

Immediately revert to `FF_MOCK_MASTERY_WRITES=shadow` if any of:

1. Live vs shadow delta disagrees for > 5% of attempts
2. Any outlier (|delta_applied_db| > 15)
3. Any idempotency violation in `user_topic_mastery_audit`
4. Any unexpected correction-task uniqueness violation not caught by migration 181
5. User-reported mastery regression that traces to a live write
6. Backend error rate for `mock:sweeper` exceeds baseline by > 2×

## Rollback Procedure

**IMPORTANT:** Scope the rollback to exact canary attempt_ids recorded in the
pre-canary baseline. Do NOT use a time window — a time window may catch
non-canary writes or miss writes from slow attempts.

### Step 1 — Revert the flag

Set `FF_MOCK_MASTERY_WRITES=shadow` on Render and redeploy. Verify that
`/api/admin/study-os/mastery-flag` returns `{"flag": "shadow"}` before
continuing.

### Step 2 — Collect the canary attempt_ids

```sql
-- All attempt_ids processed during the canary
select distinct attempt_id
from public.user_topic_mastery_audit
where attempt_id in (:canary_attempt_ids) and reason = 'mock_submit';
```

Save this as `:actual_canary_attempt_ids` (may be smaller than :canary_attempt_ids
if not all attempts reached the mastery write step).

### Step 3 — Revert user_topic_mastery

```sql
-- Revert mastery scores to pre-canary values
with reverted as (
  select user_id, topic_id, before_mastery_db
  from public.user_topic_mastery_audit
  where attempt_id in (:actual_canary_attempt_ids)
    and reason = 'mock_submit'
)
update public.user_topic_mastery utm
set mastery_score = r.before_mastery_db
from reverted r
where utm.user_id = r.user_id and utm.topic_id = r.topic_id;
```

### Step 4 — Audit the revert (user_topic_mastery_audit)

```sql
insert into public.user_topic_mastery_audit (
  id, user_id, topic_id, attempt_id,
  before_mastery_db, after_mastery_db, delta_applied_db, reason
)
select
  gen_random_uuid(),
  a.user_id, a.topic_id, a.attempt_id,
  a.after_mastery_db,
  a.before_mastery_db,
  (a.before_mastery_db - a.after_mastery_db),
  'rollback'
from public.user_topic_mastery_audit a
where a.attempt_id in (:actual_canary_attempt_ids)
  and a.reason = 'mock_submit';
```

### Step 5 — Revert user_topic_error_patterns

Revert error patterns to their pre-canary baseline snapshot (saved in
pre-canary queries above). This is a destructive replace — use the saved
baseline rows.

```sql
-- Delete error patterns written during the canary for allowlisted users
-- (safe only after saving the pre-canary baseline)
delete from public.user_topic_error_patterns
where user_id in (:allowlist_user_ids)
  and topic_id in (
    select distinct topic_id
    from public.user_topic_mastery_audit
    where attempt_id in (:actual_canary_attempt_ids) and reason = 'mock_submit'
  );

-- Re-insert from the saved baseline
-- (run the INSERT from the pre-canary snapshot captured above)
```

### Step 6 — Delete canary correction tasks

```sql
-- Delete mock_correction_tasks for canary attempts
delete from public.mock_correction_tasks
where mock_test_id in (
  select id from public.mock_tests
  where mock_attempt_id in (:actual_canary_attempt_ids)
);
```

### Step 7 — Revert canary study tasks (if corrections were applied)

```sql
-- Mark any study_tasks created from canary corrections as cancelled
update public.study_tasks
set status = 'cancelled'
where metadata->>'mock_test_id' in (
  select id::text from public.mock_tests
  where mock_attempt_id in (:actual_canary_attempt_ids)
)
and task_type = 'mock_correction';
```

### Step 8 — Verify rollback completeness

```sql
-- Verify: mastery rows restored (should match pre-canary snapshot count)
select count(*) from public.user_topic_mastery_audit
where attempt_id in (:actual_canary_attempt_ids) and reason = 'rollback';

-- Verify: no drafted correction tasks remain for canary attempts
select count(*) from public.mock_correction_tasks
where mock_test_id in (
  select id from public.mock_tests
  where mock_attempt_id in (:actual_canary_attempt_ids)
)
and state = 'drafted';

-- Verify: mastery scores match pre-canary snapshot for allowlisted users
select utm.user_id, utm.topic_id, utm.mastery_score,
       baseline.mastery_score as expected
from public.user_topic_mastery utm
join (:baseline_snapshot) baseline
  on baseline.user_id = utm.user_id and baseline.topic_id = utm.topic_id
where utm.mastery_score <> baseline.mastery_score;
-- Expected: zero rows
```

## Flag Restoration

After rollback: `FF_MOCK_MASTERY_WRITES=shadow`.  
After full live promotion: `FF_MOCK_MASTERY_WRITES=live` (no rollback needed).

## Evidence Location

Canary evidence (queries, screenshots, metrics) must be attached to PR9
before PR9 can request final approval.
