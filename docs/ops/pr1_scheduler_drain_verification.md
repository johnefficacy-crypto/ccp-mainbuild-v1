# PR1: Automatic Scheduler Drain Verification

**Type:** Operator evidence  
**Status:** Pending capture

## Purpose

Demonstrate that the `mock:sweeper` APScheduler job is registered, advances
its `next_run_at` between ticks, updates `last_run` automatically, and can
drain a pending retry job without manual invocation.

## Required Evidence

### 1. Job registration — `/api/admin/jobs` contains exactly one `mock:sweeper`

```
GET /api/admin/jobs
Authorization: Bearer <admin_token>
```

Expected: response body contains `jobs` list with exactly one entry whose `id`
is `"mock:sweeper"`, and `registered` list includes `"mock:sweeper"`.

### 2. `next_run_at` advances between scheduler ticks

Call `GET /api/admin/jobs` twice, separated by > 30 seconds.

Expected: `mock:sweeper.next_run_at` in the second response is later than in
the first response, confirming the trigger fired and rescheduled.

### 3. `last_run` updates automatically (not via manual invocation)

Wait for the scheduler to fire at least once after restart (≥ 30 s).

Expected: `mock:sweeper.last_run.at` is populated and `last_run.manual` is
absent or `false` — meaning the scheduler fired on its own interval, not via
`POST /api/admin/jobs/run/mock:sweeper`.

### 4. Pending retry job drained by scheduled runner

Insert a controlled `analytics_retry` (or `auto_submit`) job into
`mock_attempt_jobs` with `status='pending'` and `scheduled_for=now()`.

```sql
insert into public.mock_attempt_jobs (
  job_kind, attempt_id, scheduled_for, status, attempts
)
values (
  'analytics_retry',   -- or 'auto_submit'
  '<known_attempt_uuid>',
  now(),
  'pending',
  0
);
```

Then wait one sweeper cycle (≤ 30 s) without manually triggering the job.

Expected: the row transitions from `status='pending'` to `status='done'`
(or `status='failed'` if the attempt data is missing — both prove the sweeper
claimed and ran the job without manual invocation).

Confirm: `mock:sweeper.last_run.result.derivations` (or `auto_submitted`)
incremented in the next `GET /api/admin/jobs` response.

### 5. Final job status, attempts, timestamps, and non-secret result

```sql
select id, job_kind, attempt_id, status, attempts, scheduled_for,
       updated_at, last_error
from public.mock_attempt_jobs
where attempt_id = '<known_attempt_uuid>'
order by created_at desc limit 1;
```

Expected output (redacted):

```
id        | <uuid>
job_kind  | analytics_retry
attempt_id| <known_attempt_uuid>
status    | done
attempts  | 1
scheduled_for | <timestamp>
updated_at| <timestamp after sweeper ran>
last_error| null
```

### 6. No duplicate processing

Verify the `mock_mastery_shadow` table has exactly one row per
`(attempt_id, topic_id, flag_state)` for the test attempt — no duplicates
despite the sweeper's retry-safe design.

```sql
select attempt_id, topic_id, flag_state, count(*)
from public.mock_mastery_shadow
where attempt_id = '<known_attempt_uuid>'
group by 1, 2, 3
having count(*) > 1;
```

Expected: zero rows (no duplicates).

## Operator Checklist

| Step | Verified | Notes |
|------|----------|-------|
| `/api/admin/jobs` contains exactly one `mock:sweeper` | ☐ | |
| `next_run_at` advances between ticks | ☐ | |
| `last_run` updates without manual trigger | ☐ | |
| Pending retry job drained by scheduler | ☐ | |
| Final job status / attempts / timestamps | ☐ | |
| No duplicate shadow rows | ☐ | |

## Notes

- The scheduler is disabled when `DISABLE_SCHEDULER=1` is set.
- Manual kick: `POST /api/admin/jobs/run/mock:sweeper`.
- The submit route can claim and process mastery inline via `MasteryWriter`;
  PR1's drain test must use a controlled `analytics_retry` job (not a
  submit) to prove the scheduler acts independently of inline processing.
- The `done:shadow` mastery job in the submit flow does **not** prove
  scheduled drain — that result comes from inline processing at submit time.
