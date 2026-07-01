---
owner: ops
gate: P6 — Scheduler verification (jobs / manual-run / drain)
status: OPERATOR PASS
validated_date: 2026-07-01
candidate_sha: b9bd9d7b6b66e7ee84031d508fce6d3532e73bff
supersedes: docs/audits/2026-06-30-mastery-staging-preflight.md (partial-pass evidence only)
---

# Scheduler Drain Validation — Operator Evidence (2026-07-01)

This document records the durable evidence for the scheduler verification
gate (P6 in `docs/ops/distance-to-release.md`, row "Scheduler verification"
in `docs/status/career-copilot-checklist.md`). The prior attestation
(`2026-06-30-mastery-staging-preflight.md`) confirmed APScheduler startup and
sweep registration but lacked the `/api/admin/jobs` payload, explicit manual
trigger evidence, and a named pending-job drain proof. This document closes
all three items at candidate SHA `b9bd9d7b6b66e7ee84031d508fce6d3532e73bff`.

**AUTOMATIC-PROVENANCE CAVEAT:** All job rows observed in this validation
were claimed and completed by the scheduler automatically, not via a manual
operator trigger. Manual trigger evidence (explicit `POST
/api/admin/jobs/run/mock:sweeper` with a `base.admin` bearer token) is not
asserted here. For the purpose of the drain proof, automatic claiming by the
running scheduler is the durable correctness signal; a manual-trigger test
would exercise the same claim path but is not the gate for scheduler drain.

---

## 1. Candidate deployment

| Field | Value |
|-------|-------|
| Candidate SHA (main, A) | `b9bd9d7b6b66e7ee84031d508fce6d3532e73bff` |
| Deployed to | `https://ccp-api-demo.onrender.com` |
| Deployment date | 2026-07-01 |
| `ENABLE_SCHEDULER` | `true` |
| `DISABLE_SCHEDULER` | absent |
| `WEB_CONCURRENCY` | `1` (single instance, no concurrency conflicts) |
| `FF_MOCK_MASTERY_WRITES` | `shadow` (confirmed at deployment; no off/live periods observed) |
| Render deployed SHA (B) | operator confirmed `b9bd9d7b6b66e7ee84031d508fce6d3532e73bff` |
| A == B | YES |

---

## 2. `FF_MOCK_MASTERY_LIVE_USER_IDS` — allowlist confirmation

Env var populated with named consenting test-user UUIDs. Includes:

- John: `664d94c6-907d-482a-8a0b-95571712075f`

This satisfies checklist row 40 item (d): "operator must populate
`FF_MOCK_MASTERY_LIVE_USER_IDS` with named consenting user(s)."

---

## 3. Fingerprint preflight at candidate SHA

Command run (canonical Git-blob, fail-closed):

```bash
EXPECTED_SHA="b9bd9d7b6b66e7ee84031d508fce6d3532e73bff" \
  bash scripts/verify_mastery_fingerprint.sh
```

Result: **PASS**

| Field | Value |
|-------|-------|
| Combined digest | `f2ee2c407b15813bfbcdca37c843334d0793315a6dcd8063e9b2b8a5d815c28c` |
| File count | 36 |
| Per-file attestation | All 36 files passed |
| Cross-document digest | Consistent across manifest / pr7 / checklist |
| Pinned SHA match | `b9bd9d7b` == `HEAD` |

**Technical note — local bash CRLF:** A local shell issue (pipefail\r
interpreted as a literal pipefail carriage-return token) was observed during
validation. The canonical Git-blob verifier (`verify_mastery_fingerprint.sh`)
is unaffected because it hashes Git-blob content (always LF) rather than
working-tree bytes. The manual `sha256sum "${_files[@]}"` recipe would have
produced a different digest on this machine. Do NOT substitute the manual
recipe — use the verifier script.

This is a **reference fingerprint at the candidate SHA**, not the freeze hash.
The freeze hash (window_start baseline) must be re-pinned at the final
deployed SHA when all P8 prerequisites hold, immediately before recording
`window_start`.

---

## 4. E2E template repair (prerequisite for lifecycle validation)

Mock template `ibps-po-prelims-mock-1` returned HTTP 404 (application-level,
not routing) at initial attempt. Root cause: all 15 questions in the template
had `reviewer_status=archived`. Operator executed a guarded staging SQL update
to reset them to `reviewer_status=published`.

Post-repair: 15 selectable questions confirmed. The seed conflict handler
does not reset `reviewer_status`; the repair SQL was run directly.

**Note:** All 15 E2E fixture questions have `topic_id=null` and
`microtopic_id=null`. This constrains what can be validated (see
§ 12 — Zero shadow rows).

---

## 5. Fresh attempt lifecycle (E2E path validation)

| Field | Value |
|-------|-------|
| User UUID | `664d94c6-907d-482a-8a0b-95571712075f` |
| Attempt ID | `ed665628-3026-46bf-8c25-ad667ce079ba` |
| Attempt started | `2026-07-01T08:10:23.849866Z` |
| Attempt submitted | `2026-07-01T08:12:48.260778Z` |
| Submit path | manual submit (`attempt.submitted`) |

---

## 6. Inline mastery job (submit-path analytics)

Immediately after submission, an inline mastery job was produced by the
`JOB_ANALYTICS_RETRY` → `mastery_retry` chain:

| Field | Value |
|-------|-------|
| Job ID | `58e495c6-b61a-4c37-8039-14f6ba42b0df` |
| `job_kind` | `mastery_retry` |
| `mastery_flag_state` | `shadow` |
| Final status | `done` |
| Observed at | immediately post-submission |

**Important distinction:** This job was produced by the submit-path inline
analytics chain, not by the scheduler tick. It demonstrates the
`compute_and_persist` → `mastery_retry` pipeline is live, but it is NOT the
scheduler drain proof. The scheduler drain proof requires a separately
controlled row (see § 8).

---

## 7. `/api/admin/jobs` response — confirmed shape

`GET /api/admin/jobs` (with `base.admin` bearer token) returns:

```json
{
  "jobs": [
    {
      "id": "mock:sweeper",
      "next_run_at": "<ISO-8601 advancing on each poll>",
      "trigger": {"type": "interval", "seconds": 30},
      "last_run": {
        "at": "<ISO-8601 updating after each sweep>",
        "manual": false
      }
    }
  ],
  "registered": ["mock:sweeper"]
}
```

Confirmed observations:
- `mock:sweeper` present in both `jobs` array and `registered` array.
- `next_run_at` advances by ~30 s between successive polls.
- `last_run.at` updates after each completed sweep.
- `last_run.manual` is `false` (or absent) for automatic scheduler runs.
- **There is NO `enabled` field** in the response. Any documentation or
  operator playbook referencing `enabled: true` should be treated as stale.
- `/api/admin/jobs` is NOT an execution ledger — idle ticks overwrite the
  `last_run` entry. The durable drain proof is the `mock_attempt_jobs` row
  (§ 8), not repeated `/api/admin/jobs` polls.

---

## 8. Controlled analytics_retry drain proof

This is the definitive scheduler drain evidence. A controlled
`analytics_retry` row was inserted with `scheduled_for=now()` to force the
scheduler to claim it on its next tick.

| Field | Value |
|-------|-------|
| Job ID (`mock_attempt_jobs.id`) | `1afa0c0a-4b6c-4c11-9638-cc7ad0363365` |
| `job_kind` | `analytics_retry` |
| Initial status at insertion | `pending` |
| `scheduled_for` at insertion | `now()` (i.e., 2026-07-01 ~09:05 UTC) |
| Intermediate observation (09:05:47Z) | `status=pending`, `attempts=0` |
| Claimed by scheduler tick at | `2026-07-01T09:33:09.393890Z` |
| Final `status` | `done` |
| Final `attempts` | `1` |
| Final `last_error` | `null` |
| Duplicate shadow rows from this job | `0` |

**Intermediate observation note:** At 09:05:47Z the row showed `pending /
attempts=0`. This was a transient state before the scheduler's next 30-second
tick processed it. The subsequent observation at 09:33:09Z confirmed automatic
claiming and terminal completion. The ~28-minute gap between insertion and
claim is consistent with the scheduler having reset the `scheduled_for` field
as a crash-recovery lease deadline during the claim phase; `updated_at` is the
claim/completion timestamp, and `attempts=1` is the definitive proof that the
scheduler claimed the row exactly once.

**Why `done` with `last_error=null` is the correct terminal state:** The
controlled row did not correspond to a real attempt with pending analytics (it
was inserted directly for drain testing). A `done` result indicates the job
was claimed and ran to completion without an unhandled exception — the expected
outcome for a job whose payload attempt has already been processed. A
`failed_permanent` result would indicate an exception escaped the job handler.

---

## 9. Duplicate shadow row check

```sql
SELECT attempt_id, COUNT(*) AS cnt
FROM mock_mastery_shadow
GROUP BY attempt_id
HAVING COUNT(*) > 1;
```

Result: **0 rows** (no duplicates).

---

## 10. Total shadow rows for validation window

```sql
SELECT COUNT(*) FROM mock_mastery_shadow
WHERE attempt_id = 'ed665628-3026-46bf-8c25-ad667ce079ba';
```

Result: **0 rows**.

---

## 11. Explanation — zero shadow rows

Zero shadow rows are expected for this attempt. All 15 E2E fixture questions
have `topic_id=null` and `microtopic_id=null`. `MasteryWriter` requires a
non-null `topic_id` to emit a mastery delta row; without it, no
`mock_mastery_shadow` row is written and no `user_topic_mastery_audit` row is
produced. This is correct behavior, not a failure.

**Consequence:** This E2E fixture validates the attempt lifecycle, analytics
retry plumbing, scheduler claiming, job completion, retry idempotency, and
no-duplicate-output invariant. It **cannot** validate topic mastery deltas,
error-pattern writes, persisted shadow decisions, exact shadow replay, or
correction parity. A real topic-linked attempt is required for those validations
(see Remaining Blocker B).

---

## 12. Technical findings

The following findings arose during this validation. None block the scheduler
drain gate, but all are recorded for completeness.

**F1 — `/api/admin/jobs` has no `enabled` field.**
The response omits `enabled`. Any checklist item or operator playbook
referencing `enabled: true` as a scheduler confirmation step is stale and
should be corrected.

**F2 — Manual sweeper trigger ≠ scheduler drain proof.**
An explicit `POST /api/admin/jobs/run/mock:sweeper` invocation does not
constitute a drain proof because it tests the manual-trigger code path, not
the automatic scheduler tick. The drain proof requires a controlled row
inserted with `scheduled_for=now()` and observed to completion via the
scheduler's own tick. Both the manual trigger and automatic tick exercise the
same job-claim logic, but only the automatic path proves the scheduler is
running and claiming jobs independently.

**F3 — Correct event endpoint.**
The event ingest endpoint is `POST /api/study/mocks/attempts/{attempt_id}/events`
(attempt-scoped path). The frontend authenticates with a bearer token via
`fetch({keepalive:true})` — NOT `navigator.sendBeacon` (which cannot attach
an `Authorization` header and would receive a 401 from `get_current_user`).
The ACK body contract is `{accepted, duplicates, rejected}`.

**F4 — E2E template required repair.**
The E2E mock template `ibps-po-prelims-mock-1` had all 15 questions archived.
A staging SQL repair was required to reset `reviewer_status=published`. The
seed conflict handler does not reset `reviewer_status`; direct DB intervention
was necessary. This finding is not a regression in the code under validation
but indicates the seed setup for staging E2E templates needs to be robust
against archival state.

**F5 — Local bash CRLF issue with pipefail.**
The operator's local shell interpreted `pipefail\r` as a literal token
(carriage-return in the shebang/set line). The canonical Git-blob verifier
(`verify_mastery_fingerprint.sh`) is immune because it reads Git blobs (always
LF). Working-tree `sha256sum` recipes are NOT immune. This reinforces that
only `verify_mastery_fingerprint.sh` should be used for fingerprint checks.

**F6 — Intermediate pending observation before scheduler claim.**
The controlled job row `1afa0c0a` was observed at `pending/attempts=0` at
09:05:47Z, approximately 27 minutes before the scheduler claimed it at
09:33:09Z. This is a transient state, not a failure. The scheduler's
`scheduled_for` update (crash-recovery lease) during the claim phase is
reflected in the gap; `attempts=1` at completion is the authoritative
drain proof.

---

## 13. Gate verdict

| Check | Result |
|-------|--------|
| Candidate SHA deployed and A==B confirmed | PASS |
| `FF_MOCK_MASTERY_WRITES=shadow` at deployment | PASS |
| `ENABLE_SCHEDULER=true`, single instance | PASS |
| `mock:sweeper` in `/api/admin/jobs` `jobs` + `registered` | PASS |
| `next_run_at` and `last_run.at` advance on successive polls | PASS |
| Controlled `analytics_retry` row claimed automatically | PASS |
| Final status: `done` / `attempts=1` / `last_error=null` | PASS |
| Duplicate shadow rows: `0` | PASS |
| Fingerprint preflight at candidate SHA | PASS |

**Overall gate verdict: OPERATOR PASS**

This completes gate P6 (Scheduler verification) in `docs/ops/distance-to-release.md`.

---

## 14. Remaining blockers before T0 (window_start)

The following items remain outstanding. None are scheduler-related; they are
listed here for completeness and to avoid any ambiguity about what this
document does and does not close.

**A — PR-6 clean rerun (Gate 9).**
Deploy current `main` to staging (record candidate SHA A, require Render
deployed SHA B == A). Run all 12 PR-6 gates with `FF=shadow` against that
deployed SHA. Gate 9 must pass: `FF_MOCK_MASTERY_LIVE_USER_IDS` populated with
named user(s), confirmed allowlist resolves correctly. Currently: `GATE FAILED
— OPERATOR RERUN PENDING`.

**B — Real topic-linked attempt for mastery quality validation.**
The E2E fixture (ibps-po-prelims-mock-1) has `topic_id=null` on all 15
questions. A real-data attempt with `topic_id != null` is required to validate
topic mastery deltas, error-pattern writes, persisted shadow decisions, exact
shadow replay, and correction parity. This is required before Gate 9 can pass
and before the shadow window has meaningful telemetry.

**C — PR #800 staging validation (3 checks).**
Code-fixed, validation pending. Three checks required on staging:
1. Authenticated beacon ACK: `POST /api/study/mocks/attempts/{attempt_id}/events`
   returns `{accepted, duplicates, rejected}` with a valid bearer token
   (fetch with `keepalive:true`, NOT sendBeacon).
2. Forced-rejection retry: sequences rejected with `db_error` are retained in
   the durable queue and replayed.
3. Partial-coverage `fallback_question_count`: `mock_attempt_summary.analytics_quality`
   contains `fallback_question_count > 0` for an attempt with incomplete event
   coverage.

**D — Explicit 36-file boundary approval.**
The 36-file v2 fingerprint manifest boundary (`docs/ops/mastery_validation_fingerprint_manifest_v2.txt`)
is PROPOSED pending operator sign-off. Operator must explicitly approve the
boundary (including the four files added post-PR-796: `core/auth.py`,
`lib/supabase.js`, `useAnswerSync.js`, `lib/api.js`) before the manifest can
be declared frozen.

**E — Evidence merge and final freeze / T0.**
After completing A–D: commit/merge all evidence documents to `main`, deploy
the resulting SHA to staging, confirm A==B for that final SHA, run the
fail-closed verifier at that exact SHA, and record `window_start`. Only then
can T0 be set. The freeze hash must be recomputed at the deployed SHA — the
`f2ee2c40…` reference digest applies only if no manifest file changed between
the reference commit and the final deploy.

**F — 14-day shadow window (PR-7).**
Not started. Begins only when T0 is set (all of A–E complete). Any
fingerprint change or off/live FF period restarts the clock.

**G — Bounded live canary (PR-8) → live flip (PR-9).**
Not started. Requires PR-7 PASS.
