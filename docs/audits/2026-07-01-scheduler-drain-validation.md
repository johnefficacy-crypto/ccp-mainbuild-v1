---
owner: ops
gate: P6 — Scheduler verification (jobs / manual-run / drain)
status: PARTIAL OPERATOR PASS — AUTOMATIC DRAIN PROVENANCE PENDING
validated_date: 2026-07-01
candidate_sha: b9bd9d7b6b66e7ee84031d508fce6d3532e73bff
supersedes: docs/audits/2026-06-30-mastery-staging-preflight.md (partial-pass evidence only)
---

# Scheduler Drain Validation — Operator Evidence (2026-07-01)

This document records the 2026-07-01 operator validation session for gate P6
("Scheduler verification — jobs / manual-run / drain") at candidate SHA
`b9bd9d7b6b66e7ee84031d508fce6d3532e73bff`. It supersedes the partial
attestation in `2026-06-30-mastery-staging-preflight.md`.

**Current gate status: PARTIAL OPERATOR PASS.**
What this session proves: scheduler is registered and healthy; the worker
processed a controlled `analytics_retry` job to terminal state (`done /
attempts=1 / last_error=null`); DB state is correct. What it does NOT prove:
(a) whether the 09:33 completion was driven by an automatic APScheduler tick
or a manual `POST /api/admin/jobs/run/mock:sweeper` — the contemporaneous
`/api/admin/jobs` response with `last_run.result.derivations` incremented was
not captured; (b) drain within the expected ≤ 30-second cycle — the actual
insertion-to-completion gap was ~65 minutes. Both items are required by the
`docs/ops/pr1_scheduler_drain_verification.md` runbook (steps 3–4). See
§ 13 (Gate Verdict) for the outstanding requirements.

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

The direct `bash scripts/verify_mastery_fingerprint.sh` invocation failed
locally due to a CRLF issue (`pipefail\r` interpreted as a literal token).
The successful portable invocation read the script blob directly from Git:

```bash
export EXPECTED_SHA="b9bd9d7b6b66e7ee84031d508fce6d3532e73bff"
git show HEAD:scripts/verify_mastery_fingerprint.sh | bash
```

Result: **PASS**

| Field | Value |
|-------|-------|
| Combined digest | `f2ee2c407b15813bfbcdca37c843334d0793315a6dcd8063e9b2b8a5d815c28c` |
| File count | 36 |
| Per-file attestation | All 36 files passed |
| Cross-document digest | Consistent across manifest / pr7 / checklist |
| Pinned SHA match | `b9bd9d7b` == `EXPECTED_SHA` |

**Note on the two invocation forms:** The canonical verifier
(`verify_mastery_fingerprint.sh`) hashes Git blobs (always LF) rather than
working-tree bytes, so the digest is platform-independent once the script
itself is read cleanly. On Windows/CRLF checkouts, pipe from `git show`
as above rather than running the script file directly.

This is a **reference fingerprint at the candidate SHA**, not the freeze hash.
The freeze hash must be re-pinned at the final deployed SHA when all P8
prerequisites hold, immediately before recording `window_start`.

---

## 4. E2E template repair (prerequisite for lifecycle validation)

Mock template `ibps-po-prelims-mock-1` returned HTTP 404 (application-level,
not routing) at initial attempt. Root cause: all 15 questions had
`reviewer_status=archived`. Operator executed a guarded staging SQL update to
reset them to `reviewer_status=published`.

Post-repair: 15 selectable questions confirmed. The seed conflict handler
does not reset `reviewer_status`; the repair SQL was run directly.

**Note:** All 15 E2E fixture questions have `topic_id=null` and
`microtopic_id=null`. This constrains what can be validated (see § 11 —
Zero shadow rows).

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

## 6. Inline mastery job (submit-path synchronous processing)

Immediately after submission, a mastery retry job was produced and completed
synchronously within the submit request. The submit route (`app/backend/app/api/mock_engine.py`)
resolves `flag_state` via `get_or_resolve_pinned_mastery_flag`, then — if
not already processed — calls `claim_mastery_retry_required` to claim the job
row, invokes `MasteryWriter.process_attempt` inline, and calls
`complete_mastery_retry_required` to mark it done. All of this occurs within
the HTTP request; there is no async analytics chain. The code comment at
line 172 explicitly states: "no second `compute_and_persist` here."

| Field | Value |
|-------|-------|
| Job ID | `58e495c6-b61a-4c37-8039-14f6ba42b0df` |
| `job_kind` | `mastery_retry` |
| `mastery_flag_state` | `shadow` |
| Final status | `done` |
| Processing path | synchronous inline (submit route, not scheduler) |

**Important distinction:** This job was completed synchronously by the submit
route, not by a scheduler tick. It demonstrates the inline mastery path is
live but is NOT the scheduler drain proof. Per `pr1_scheduler_drain_verification.md`
§ Notes: "The `done:shadow` mastery job in the submit flow does not prove
scheduled drain — that result comes from inline processing at submit time."

---

## 7. `/api/admin/jobs` — confirmed fields

`GET /api/admin/jobs` (with `base.admin` bearer token). The following
is **schematic** (field names and value shapes confirmed; the literal
payload was not captured verbatim):

```
{
  "jobs": [
    {
      "id": "mock:sweeper",
      "next_run_at": <ISO-8601, advances ~30s between polls>,
      "trigger": "interval[0:00:30]",
      "last_run": {
        "at": <ISO-8601, updates after each sweep>,
        // "manual" is absent for automatic scheduler runs
        "result": { ... }
      }
    }
  ],
  "registered": ["mock:sweeper"]
}
```

Confirmed observations:
- `mock:sweeper` present in both `jobs` array and `registered` array.
- `next_run_at` advances between successive polls.
- `last_run.at` updates after each completed sweep.
- `trigger` is the string `"interval[0:00:30]"`, not an object.
- `last_run.manual` is absent (not `false`) for automatic scheduler runs.
- **There is NO `enabled` field** in the response.
- The exact payload at the time of the controlled job completion was not
  captured. In particular, `last_run.result.derivations` (or equivalent) was
  not recorded after the 09:33 completion. This missing capture is one of the
  two outstanding items for full P6 PASS (see § 13).

---

## 8. Controlled `analytics_retry` drain — evidence

A controlled `analytics_retry` row was inserted with `scheduled_for=now()`
to allow the scheduler's next tick to claim it.

| Field | Value |
|-------|-------|
| Job ID (`mock_attempt_jobs.id`) | `1afa0c0a-4b6c-4c11-9638-cc7ad0363365` |
| `job_kind` | `analytics_retry` |
| Insertion timestamp (`created_at`) | `2026-07-01T08:28:17.828378Z` |
| `scheduled_for` at insertion | `now()` at insertion time (~08:28 UTC) |
| Intermediate observation | `2026-07-01T09:05:47Z` — `status=pending`, `attempts=0` |
| Completion (`updated_at`) | `2026-07-01T09:33:09.393890Z` |
| Final `scheduled_for` | `2026-07-01T09:34:07Z` (post-claim lease; see note) |
| Final `status` | `done` |
| Final `attempts` | `1` |
| Final `last_error` | `null` |
| Insertion-to-completion gap | **~65 minutes** (08:28 → 09:33) |

**Timestamp correction:** The row was inserted at `08:28:17Z`. The 09:05:47Z
observation is an intermediate check ~37 minutes after insertion, not the
insertion time. Earlier versions of this document incorrectly described 09:05
as the insertion time and computed a ~28-minute gap; both were wrong.

**On the 65-minute gap:** The scheduler fires every 30 seconds. A 65-minute
drain delay is not explained by the crash-recovery lease mechanism — that
lease updates `scheduled_for` to a future time during claim, which is why
final `scheduled_for=09:34:07Z` is later than `updated_at=09:33:09Z`, but
that does not explain why the row remained unclaimed through many prior
30-second ticks. Plausible causes include a service restart or idle period
between 08:28 and 09:33; this was not investigated. The delay does not
prevent the DB state from being correct, but it means the runbook requirement
of "drain within one sweeper cycle (≤ 30 s)" was not demonstrated.

**On automatic vs manual provenance:** The `done / attempts=1 / last_error=null`
final state proves the `run_sweeper()` worker processed the row. It does not
distinguish an APScheduler tick from a manual `POST /api/admin/jobs/run/mock:sweeper`,
because both paths invoke the same worker function and produce the same DB
mutation. The runbook (step 4) requires "wait one sweeper cycle without
manually triggering" and then "confirm `last_run.result.derivations`
incremented in the next GET /api/admin/jobs response." The contemporaneous
`/api/admin/jobs` capture after completion was not recorded. This is the
second outstanding item for full P6 PASS.

---

## 9. Duplicate shadow row check

Query (per `pr1_scheduler_drain_verification.md` step 6 — correct invariant):

```sql
SELECT attempt_id, topic_id, flag_state, COUNT(*)
FROM public.mock_mastery_shadow
WHERE attempt_id = 'ed665628-3026-46bf-8c25-ad667ce079ba'::uuid
GROUP BY 1, 2, 3
HAVING COUNT(*) > 1;
```

Result: **0 rows** (no duplicates for this attempt).

**Scope limitation:** Because this fixture emitted zero shadow rows (see § 11),
this result confirms "no spurious duplicate shadow rows were created" but does
not exercise the shadow-write idempotency path. A real topic-linked attempt
is required to validate idempotency under re-processing.

---

## 10. Total shadow rows for validation window

```sql
SELECT COUNT(*) FROM public.mock_mastery_shadow
WHERE attempt_id = 'ed665628-3026-46bf-8c25-ad667ce079ba'::uuid;
```

Result: **0 rows**.

---

## 11. Explanation — zero shadow rows

Zero shadow rows are expected for this attempt. All 15 E2E fixture questions
have `topic_id=null` and `microtopic_id=null`. `MasteryWriter` requires a
non-null `topic_id` to emit a mastery delta row; without it, no
`mock_mastery_shadow` row is written and no `user_topic_mastery_audit` row is
produced. This is correct behavior, not a failure.

**Consequence:** This E2E fixture validates the attempt lifecycle, synchronous
inline mastery processing, scheduler registration/health, worker job
completion, and no-spurious-duplicate invariant. It **cannot** validate topic
mastery deltas, error-pattern writes, persisted shadow decisions, exact shadow
replay, correction parity, or shadow-write idempotency under re-processing. A
real topic-linked attempt is required for those (see § 13, Blocker B).

---

## 12. Technical findings

**F1 — `/api/admin/jobs` has no `enabled` field.**
Any checklist item or playbook referencing `enabled: true` as a scheduler
confirmation step is stale and should be corrected.

**F2 — Manual sweeper trigger ≠ scheduler drain proof.**
The drain proof requires a controlled row inserted with `scheduled_for=now()`
observed to completion via the scheduler's own tick, plus a contemporaneous
`/api/admin/jobs` capture confirming automatic provenance. A manual
`POST /api/admin/jobs/run/mock:sweeper` would exercise the same worker but
proves a different code path.

**F3 — Correct event endpoint.**
The event ingest endpoint is `POST /api/study/mocks/attempts/{attempt_id}/events`
(attempt-scoped path). The frontend authenticates with a bearer token via
`fetch({keepalive:true})` — NOT `navigator.sendBeacon`. The ACK body contract
is `{accepted, duplicates, rejected}`.

**F4 — E2E template required repair.**
All 15 questions in `ibps-po-prelims-mock-1` had `reviewer_status=archived`.
A staging SQL repair was required. The seed conflict handler does not reset
`reviewer_status`; direct DB intervention was necessary.

**F5 — Local bash CRLF issue.**
The operator's local shell interpreted `pipefail\r` as a literal token. The
portable invocation is `git show HEAD:scripts/verify_mastery_fingerprint.sh | bash`.

**F6 — 65-minute drain delay unexplained.**
The controlled job was inserted at 08:28 and completed at 09:33 (~65 min),
not within one 30-second scheduler cycle. The cause was not investigated.

---

## 13. Gate verdict

### What this session proved

| Check | Result |
|-------|--------|
| Candidate SHA deployed, A==B confirmed | PASS |
| `FF_MOCK_MASTERY_WRITES=shadow` at deployment | PASS |
| `ENABLE_SCHEDULER=true`, single instance | PASS |
| `mock:sweeper` in `/api/admin/jobs` `jobs` + `registered` | PASS |
| `next_run_at` advances between polls | PASS |
| `last_run.at` updates after sweeps | PASS |
| Controlled `analytics_retry` row reaches `done / attempts=1 / last_error=null` | PASS |
| No spurious duplicate shadow rows for test attempt | PASS |
| Fingerprint preflight (canonical Git-blob invocation) | PASS |

### Outstanding requirements for full PASS (per `pr1_scheduler_drain_verification.md`)

| Requirement | Runbook step | Status |
|-------------|-------------|--------|
| Drain within ≤ 30 s of insertion without manual trigger | Step 4 | **PENDING** — gap was ~65 min |
| Contemporaneous `GET /api/admin/jobs` showing `last_run.result.derivations` incremented after drain | Step 4 | **PENDING** — not captured |

Until both are provided, automatic provenance cannot be distinguished from a
manual invocation, and the runbook drain-timing requirement is unmet.

**Overall gate verdict: PARTIAL OPERATOR PASS**

---

## 14. Remaining blockers before T0 (window_start)

**A — PR-6 clean rerun (Gate 9).**
Deploy current `main` to staging (record candidate SHA A, confirm Render
deployed SHA B == A). Run all 12 PR-6 gates with `FF=shadow` against that
deployed SHA. Gate 9 must pass: `FF_MOCK_MASTERY_LIVE_USER_IDS` populated.

**B — Real topic-linked attempt.**
A real-data attempt with `topic_id != null` is required to validate topic
mastery deltas, error-pattern writes, persisted shadow decisions, exact shadow
replay, correction parity, and shadow-write idempotency.

**C — P6 automatic drain proof (see § 13).**
New controlled job with insertion timestamp, drain within ≤ 30 s of
`scheduled_for`, plus a succeeding `GET /api/admin/jobs` response showing
`last_run.result.derivations` (or equivalent) incremented with `manual`
absent/false.

**D — PR #800 staging validation (3 checks).**
Authenticated beacon ACK (`POST /api/study/mocks/attempts/{attempt_id}/events`
returns `{accepted, duplicates, rejected}`); forced-rejection retry; partial-
coverage `fallback_question_count`.

**E — Explicit 36-file boundary approval.**
Operator sign-off on the v2 manifest boundary.

**F — Evidence merge, final freeze, T0.**

**G — 14-day shadow window (PR-7), canary (PR-8), live flip (PR-9).**
