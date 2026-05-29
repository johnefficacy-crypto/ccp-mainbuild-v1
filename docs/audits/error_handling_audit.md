# Error Handling Audit — `_safe()` Near Write Operations

**Date:** 2026-05-27  
**Scope:** `app/backend/app/study_os/mock_engine.py`  
**Trigger:** `_emit_mock_tests_row` silently dropped `mock_tests` insert failures, causing dashboard rows to never appear after a submit.

---

## Root Cause

`_safe(call, default=None)` is a helper that catches all exceptions and returns a default. It was designed for read operations where a missing row is acceptable. When applied to write operations (INSERT/UPSERT), a DB failure (e.g. missing column after a broken migration, transient network error, RLS violation) is logged at WARNING level but no retry is scheduled and no caller receives the error signal.

`_emit_mock_tests_row` used `_safe` to wrap the `mock_tests` INSERT. Migration 148 was broken (its backfill referenced a non-existent `metadata` column), so the INSERT failed on columns that didn't exist. The error was silently swallowed and `mock_tests` rows were never written.

---

## Triage of `_safe` Usages in `mock_engine.py`

| Location | Operation | Classification | Disposition |
|---|---|---|---|
| `_emit_mock_tests_row` (was) | `mock_tests.insert` | **Critical write** — dashboard row | **Fixed** — explicit try/except + `mock_tests_retry` job |
| `schedule_job` | `mock_attempt_jobs.insert` | Fire-and-forget scheduling | Allowed — sweeper Phase A re-detects expired attempts; annotated `# safe-write-ok` |
| `_complete_job` | `mock_attempt_jobs.update` | Job status bookkeeping | Acceptable — done rows are observability-only; stale running rows are reclaimed |
| `_mark_running` | `mock_attempt_jobs.update` | Claim-for-run | Acceptable — idempotent; sweeper retries if claim is lost |
| `_reschedule_job` | `mock_attempt_jobs.update` | Backoff scheduling | Acceptable — sweeper reclaims running rows past schedule |
| `_fail_job` | `mock_attempt_jobs.update` | Max-attempts bookkeeping | Acceptable — worst case: job retried one extra cycle |
| `_finalize_submission` (response updates) | `mock_attempt_responses.update` | Scoring | Read-scoring from snapshot, not from these rows; low risk |
| `_finalize_submission` (attempt update) | `mock_attempts.update` | Status flip | Dangerous if silently dropped, but idempotency + duplicate submit guard cover the gap |
| All read paths (`select`, `limit`, etc.) | Read-only | Out of scope | No change needed |

---

## Fix Applied (PR-fix-12)

1. **`_emit_mock_tests_row`** — replaced `_safe` with explicit `try/except`. On failure: logs at ERROR, schedules `mock_tests_retry` job via `schedule_job`.

2. **`_retry_emit_mock_tests_row`** — idempotent retry function. Checks if a `mock_tests` row already exists for the attempt before inserting. Raises on failure so the sweeper's exponential-backoff loop handles it.

3. **`JOB_MOCK_TESTS_RETRY = "mock_tests_retry"`** — new job kind, added to the `mock_attempt_jobs.job_kind` check constraint in migration 150.

4. **`_run_job`** — dispatches `mock_tests_retry` to `_retry_emit_mock_tests_row`.

5. **`scripts/lint_safe_writes.py` + `.github/workflows/safe-write-lint.yml`** — CI lint that fails if `_safe()` is introduced wrapping `.insert()` or `.upsert()` without a `# safe-write-ok` annotation.

---

## Future Work

- `_finalize_submission`'s `mock_attempts.update` (status flip) is the highest-risk remaining `_safe` usage. If it silently fails, the attempt stays `in_progress` and the sweeper auto-submits it on the next cycle — acceptable for now, but worth wrapping in explicit error detection when the submit path is revisited.
- The `mock_attempt_responses.update` loop in `_finalize_submission` (scoring) could be wrapped in a bulk upsert with a server-side function to make partial-failure detection practical.
