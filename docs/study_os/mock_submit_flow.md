# Mock Submit Flow & Background Jobs

End-to-end picture of what happens when a mock attempt is finalised, and the
two decisions the PR-fix-3 correctness gate locks in: **how derivation and
mastery write-back are ordered**, and **how background work is consolidated**.

## Submit paths

There are two ways an attempt leaves `in_progress`:

1. **User submit** — `POST /attempts/{id}/submit` → `mock_engine.submit_attempt`.
2. **Auto submit** — the sweeper finalises an attempt whose timer expired while
   the client was gone → `mock_engine.auto_submit_attempt`.

Both share `_finalize_submission`, which does only the deterministic,
snapshot-based work: score from the frozen `question_snapshot`, flip status to
`submitted`, write the lifecycle event, and emit the `mock_tests` compat row.
The difference:

| | `submitted_at` | lifecycle event | derivation |
|---|---|---|---|
| User submit | `now()` | `attempt.submitted` | run inline, retry-queued on failure |
| Auto submit | `expires_at` (when the window actually closed) | `attempt.auto_submitted` | queued as `analytics_retry`, never run inline |

## Decision 1 — derivation → mastery ordering: **Implementation B**

The mastery writer (`mastery_writer.MasteryWriter.process_attempt`) **derives
inline from persisted raw data** — `mock_attempts` + `mock_attempt_responses`
(whose `is_correct` is set at submit time) — and calls the PR4a pure functions
(`mastery_engine.derive_from_analytics`) directly. It does **not** read
`mock_attempt_summary`.

Consequence: the writer does **not** depend on PR4 derivation having completed.
A failed or still-queued derivation **cannot** silently suppress the mastery
write-back. This was the quiet-failure mode flagged in the gate: under the
rejected "Implementation A" (writer reads `mock_attempt_summary`), a missing
summary at call time produces zero deltas with no error.

For this to work, every signal the writer weights on must be captured in the
frozen `question_snapshot` at attempt start (`mock_engine._question_snapshot`):
`topic_id`, `microtopic_id`, `difficulty`, `source_type`, `expected_time_sec`.
These are never read back from the live `mock_question_bank`, so post-submit
edits to the bank cannot change a derived delta — same guarantee as scoring.

The user-submit handler therefore runs the writer **independently** of
derivation (separate try/except); a derivation exception is logged and queued
for retry but does not skip mastery.

### Mastery cap vs clamp (two distinct invariants)

In `_apply_mastery`, both must hold:

- **Cap** (`±0.15` unit ≈ `±15` db) — whiplash guard, so one mock can't swing a
  topic wildly. Applied in Python before the DB call; re-applied defensively
  even though `derive_mastery_deltas` already caps `capped_delta`.
- **Clamp** (`[0, 100]` db) — overflow guard on the stored score. Applied inside
  `apply_mock_mastery_delta` against the freshly-read current value.

A proposed `+0.50` unit therefore writes `+15` db (cap), and `95 + 15` stores
`100` (clamp) — neither invariant masks the other.

### Idempotency + atomicity

`apply_mock_mastery_delta` (migration 145) runs as a single transaction:
it skips when an audit row already exists for `(user_id, topic_id, attempt_id)`
(silent no-op, not a 409-style error), otherwise applies the clamp, writes
mastery, and inserts the audit row together. Re-submitting an attempt re-runs
the writer, which is a no-op — no second audit row, no exception.

> Note: auto-submitted attempts currently queue derivation only. Mastery
> write-back for them is deferred to a future `mastery_retry` job kind (the jobs
> table already allows it). User-submitted attempts get mastery inline as above.

## Decision 2 — one sweeper, switchable job kinds

`mock_attempt_jobs` (migration 145) is the single work queue, drained by one
APScheduler loop (`mock:sweeper`, every 30s, `max_instances=1`). Running two
cron loops over the same DB would compete on locks and split observability, so
auto-submit and derivation retry share one dispatcher (`mock_engine.run_sweeper`
→ `_run_job` by `job_kind`):

- `auto_submit` — finalise an expired attempt, then enqueue its `analytics_retry`.
- `analytics_retry` — `attempt_analytics.compute_and_persist`.
- `mastery_retry` — reserved for later.

Each cycle: **Phase A** enqueues `auto_submit` jobs for attempts whose window
closed more than 60s ago (the grace window avoids racing a slow client submit);
**Phase B** claims due jobs (`status in (pending, running)` and
`scheduled_for <= now`), marks them `running` (bumping `attempts`, which bounds
crash loops), dispatches, then marks `done` or reschedules with exponential
backoff (capped at 300s, failed after `max_attempts`).

**Crash safety:** a process that dies between claim and completion leaves the
job `running` with `scheduled_for` in the past, so the next cycle reclaims it.
Both job kinds are idempotent (`auto_submit_attempt` no-ops once submitted;
`compute_and_persist` upserts), so reprocessing is safe and leaves no orphan
rows. A partial-batch failure completes the healthy jobs and reschedules only
the failed one.

The partial unique index `mock_attempt_jobs(job_kind, attempt_id) where status
in ('pending','running')` guarantees at most one active job per
(kind, attempt); `done`/`failed` rows are retained for observability and do not
block re-enqueue.

### Relationship to `mock_attempt_derivation_retry`

Superseded. Migration 145 copies any in-flight rows into `mock_attempt_jobs`
(`analytics_retry`) and repoints all scheduling there. The old table is left
empty for one release and is scheduled for removal; nothing reads or writes it
after this migration.
