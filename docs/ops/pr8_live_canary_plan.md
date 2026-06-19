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

**Important:** The current feature flag (`FF_MOCK_MASTERY_WRITES`) is **global** —
it applies to all platform attempts uniformly. A genuinely bounded canary (limited
to a subset of users or attempts) requires one of:

- [ ] A user-allowlist implementation PR (check `user_id` against an allow-list
      before calling `MasteryWriter.process_attempt_sync`)
- [ ] A percentage-rollout implementation PR (hash `user_id` against a configured
      percentage threshold)
- [ ] Acceptance that the canary is global and the safety controls are the stop
      conditions + rollback procedure below

**Decision (choose one):**
- [ ] Proceed with global flag (accepted risk; stop conditions are the safety gate)
- [ ] Implement user-allowlist before proceeding (blocks this PR until done)
- [ ] Implement percentage-rollout before proceeding (blocks this PR until done)

If a bounded implementation is required, file that implementation PR before
approving this document.

**Canary scope:** `______________________________`

## Maximum Attempts

The canary will run until either:
- Maximum **`______`** platform attempts have been processed in live mode, OR
- A stop condition is triggered (see below)

## Pre-Canary Queries

Run before flipping the flag:

```sql
-- Baseline mastery snapshot (per-topic)
select user_id, topic_id, mastery_score, updated_at
from public.user_topic_mastery
where updated_at >= now() - interval '24 hours'
order by updated_at desc limit 100;

-- No live audit rows exist yet
select count(*) from public.user_topic_mastery_audit
where reason = 'mock_submit';
```

## Post-Canary Queries

Run after N attempts have processed:

```sql
-- Audit trail for canary attempts
select user_id, topic_id, attempt_id, before_mastery_db, after_mastery_db,
       delta_applied_db, at
from public.user_topic_mastery_audit
where reason = 'mock_submit'
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
where a.reason = 'mock_submit'
order by s.attempt_id;
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

1. Set `FF_MOCK_MASTERY_WRITES=shadow` on Render and redeploy.
2. Execute rollback SQL (from `docs/study_os/mock_mastery_writeback.md`),
   replacing `:days` with the number of days since canary start:

```sql
-- Revert user_topic_mastery
with reverted as (
  select id, user_id, topic_id, before_mastery_db
  from public.user_topic_mastery_audit
  where at >= now() - interval ':days days' and reason='mock_submit'
)
update public.user_topic_mastery utm
set mastery_score = r.before_mastery_db
from reverted r
where utm.user_id=r.user_id and utm.topic_id=r.topic_id;

-- Audit the revert
insert into public.user_topic_mastery_audit (
  id,user_id,topic_id,attempt_id,before_mastery_db,after_mastery_db,delta_applied_db,reason
)
select gen_random_uuid(), a.user_id, a.topic_id, a.attempt_id,
       a.after_mastery_db, a.before_mastery_db, (a.before_mastery_db-a.after_mastery_db),
       'rollback'
from public.user_topic_mastery_audit a
where a.at >= now() - interval ':days days' and a.reason='mock_submit';
```

3. Verify: `select count(*) from user_topic_mastery_audit where reason='rollback';`
   should equal the number of rows reverted.

## Flag Restoration

After rollback: `FF_MOCK_MASTERY_WRITES=shadow`.  
After full live promotion: `FF_MOCK_MASTERY_WRITES=live` (no rollback needed).

## Evidence Location

Canary evidence (queries, screenshots, metrics) must be attached to PR9
before PR9 can request final approval.
