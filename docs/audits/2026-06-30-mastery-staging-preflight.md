---
owner: ops
status: partial_pass
verdict: DO_NOT_OPEN_SHADOW_WINDOW
checked_date: 2026-06-30
candidate_sha: daaddaae48285c6400234fc32077f083f10e0acb
---

# Mastery staging preflight — 2026-06-30

## Environment

- Render environment: Staging
- Service: ccp-api-demo
- Region: Singapore
- Instance count: 1
- Worker count: 1
- WEB_CONCURRENCY: 1

## Deployment

- Candidate SHA: `daaddaae48285c6400234fc32077f083f10e0acb`
- Deployed SHA: `daaddaae48285c6400234fc32077f083f10e0acb`
- SHA parity: PASS
- Service status: live
- Observed live timestamp: `2026-06-30T13:21:27Z`

## Runtime configuration

- `FF_MOCK_MASTERY_WRITES=shadow`
- `FF_MOCK_MASTERY_LIVE_USER_IDS`: 3 configured UUIDs; values redacted
- `ENABLE_SCHEDULER=true`
- `DISABLE_SCHEDULER`: absent

## Scheduler and database evidence

- Postgres/Supabase connectivity: PASS
- APScheduler startup: PASS
- `mock:sweeper` registration: PASS
- `mock:sweeper` interval: 30 seconds
- Repeated scheduled sweeps: PASS
- `mock_attempts` query response: HTTP 200
- `mock_attempt_jobs` query response: HTTP 200
- Clean scheduler shutdown during deployment replacement: PASS

Remaining scheduler evidence:

- `/api/admin/jobs` payload: PENDING
- Explicit manual sweeper invocation: PENDING
- Named pending-job drain proof: PENDING

## Fingerprint verification

The original verifier failed on a Windows checkout with:

- `core.autocrlf=true`
- index line endings: LF
- working-tree line endings: CRLF

All 36 canonical Git blobs matched the committed attestation.

- Canonical per-file attestation diff: PASS
- File count: 36
- Combined digest: `f2ee2c407b15813bfbcdca37c843334d0793315a6dcd8063e9b2b8a5d815c28c`

Cross-platform verifier validation:

- Positive verification: PASS
- Wrong `EXPECTED_SHA` rejection: PASS
- Unstaged fingerprint drift rejection: PASS
- Staged fingerprint drift rejection: PASS
- Automated verifier tests: 6 passed

## Gate disposition

- Deployment and scheduler-startup preflight: PASS
- Migration 182 operator validation: PASS; separate durable audit exists
- Fingerprint canonical integrity: PASS
- Fingerprint portability remediation: CODE-FIXED, PR PENDING
- PR #800 authenticated event-delivery checks: PENDING
- PR-6 clean repeat validation: PENDING
- 36-file boundary operator approval: PENDING
- 14-day shadow window: NOT STARTED
- `window_start`: NOT SET

## Verdict

**PREFLIGHT PARTIAL PASS**

Do not open the 14-day shadow window.

Do not set `FF_MOCK_MASTERY_WRITES=live`.
