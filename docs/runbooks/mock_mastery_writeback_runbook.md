# Runbook: Mock Mastery Write-back

- Set env `FF_MOCK_MASTERY_WRITES` to `off|shadow|live` and redeploy backend.
- In shadow: run (requires `NEXT_PUBLIC_SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in env):
  - `python tools/mastery_shadow_analysis/shadow_analysis.py --json shadow-replay --days 14`
  - `python tools/mastery_shadow_analysis/shadow_analysis.py --json correction-parity --days 14`
  - Add `--json` for machine-readable output (also accepted after the subcommand name).
  - The tool exits with a structured error if credentials are missing — it never
    prints apparently valid zero metrics on absent credentials.
- Shadow gate thresholds (ALL must pass):
  - `exact_match_pct = 100.0` (exact Decimal match of persisted shadow decisions vs replay)
  - `coverage_pct = 100.0` (all shadow topics are covered by the replay)
  - `distinct_attempt_count >= 20`
  - `topic_decision_count >= 50`
  - Zero missing / extra / mismatch / duplicate / invariant violations
  - Zero `classification_not_ready` attempts
- Correction parity threshold: `exact_parity_pct = 100.0` (min 10 decisions)
- Correction preview (read-only, no writes):
  - `GET /api/admin/study-os/mocks/<mock_id>/mastery-preview` (admin, PERM_OPS)
- Rollback: execute rollback SQL from docs/study_os/mock_mastery_writeback.md.
- Full canary plan: docs/ops/pr8_live_canary_plan.md

## CLI reference

```
shadow-analysis [--json] <subcommand> [--json] [flags]

Subcommands:
  shadow-replay      Shadow self-consistency gate (REQUIRES PR-4 attempt_derivation.py)
    --attempt-id UUID     Exact single attempt (mutually exclusive with --days/--from-utc)
    --from-utc ISO8601    Window start
    --to-utc ISO8601      Window end (used with --from-utc)
    --days N              Rolling window in days (default 14)

  correction-parity  Prove generated corrections == correction_policy (REQUIRES PR-4)
    (same flags as shadow-replay)

  live-audit-compare Compare live shadow writes against audit trail (CANARY-ONLY)
    --days N              Rolling window in days (default 14)

  tasks-overlap      (INVALID) Exits 2 — use correction-parity instead

Exit codes:
  0  PASS or FAIL — run completed, data was sufficient
  2  ERROR — config / credential / query error or PREREQUISITE_MISSING
  3  INSUFFICIENT_DATA — not enough attempts/decisions
  4  CORRUPT — invariant-invalid data detected
```

## Exit code 2 — PREREQUISITE_MISSING

`shadow-replay` and `correction-parity` require PR-4
(`app/backend/app/study_os/attempt_derivation.py`). If the module is absent,
the tool exits 2 with:

```json
{"status": "ERROR", "error": "PREREQUISITE_MISSING", ...}
```

Do not implement an inline fallback. Merge PR-4 first.

## tasks-overlap is invalid

Cross-population topic identity is unavailable: generated corrections use
canonical topic UUIDs; manual study tasks use display-name topic references.
`tasks-overlap` always exits 2. Use `correction-parity` instead.

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
