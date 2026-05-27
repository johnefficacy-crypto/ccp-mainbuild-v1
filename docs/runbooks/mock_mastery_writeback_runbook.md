# Runbook: Mock Mastery Write-back

- Set env `FF_MOCK_MASTERY_WRITES` to `off|shadow|live` and redeploy backend.
- In shadow: run
  - `python tools/mastery_shadow_analysis/shadow_analysis.py compare --days 14`
  - `python tools/mastery_shadow_analysis/shadow_analysis.py tasks-overlap --days 14`
- Rollback: execute rollback SQL from docs/study_os/mock_mastery_writeback.md.

## Submit flow & ordering

- Full picture (auto-submit, mastery cap vs clamp, idempotency, derivation
  ordering): docs/study_os/mock_submit_flow.md.
- Mastery is derived inline from raw responses (implementation B), so it does
  not wait on PR4 derivation and a derivation failure does not suppress it.

## Background sweeper (`mock:sweeper`)

- Single APScheduler loop, every 30s, drains `mock_attempt_jobs` by `job_kind`
  (`auto_submit`, `analytics_retry`). Disable all schedulers with
  `DISABLE_SCHEDULER=1`.
- Manual kick (admin job-trigger endpoint): job id `mock:sweeper`.
- Inspect the queue:
  ```sql
  select job_kind, status, count(*), max(attempts) as max_attempts
  from public.mock_attempt_jobs group by 1, 2 order by 1, 2;
  ```
- Stuck/failed jobs: rows in `status='failed'` exhausted `max_attempts` (5);
  inspect `last_error`, fix the cause, then re-enqueue by setting
  `status='pending', attempts=0, scheduled_for=now()`.
- `mock_attempt_derivation_retry` is superseded by `mock_attempt_jobs` and is
  expected to be empty; do not write to it.
