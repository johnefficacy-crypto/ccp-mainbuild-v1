# Attempt answer-save semantics

How a single answer travels from a click to a durable server row, and what the
UI guarantees along the way. The governing rule: **the user never sees an
answer in the UI that the server doesn't have** — every save carries a visible
sync state and a blocked submit until it resolves.

Source of truth for the client logic: `useAnswerSync.js`
(`app/frontend/src/pages/study/mocks/`). Server idempotency:
`save_answer` in `app/backend/app/study_os/mock_engine.py`.

## Client sync state

Each question the user has touched carries a `sync_state`:

| state      | meaning                                            |
|------------|----------------------------------------------------|
| `unsaved`  | user changed it; debounce timer running            |
| `saving`   | POST in flight                                     |
| `saved`    | server acknowledged (2xx)                          |
| `retrying` | a transient failure occurred; backoff timer running|
| `failed`   | retries exhausted, or a non-retryable 4xx          |

### Transitions

```
user change              → unsaved   (clears any existing failed / pending retry)
debounce fires           → saving
POST 2xx                 → saved
POST network/5xx/timeout → retrying  (schedule backoff retry)
retries exhausted        → failed
non-retryable 4xx        → failed     (immediate, no retry)
manual "Retry" click     → saving     (replays the same client_seq)
```

### Retry policy

Exponential backoff: **1s, 2s, 4s** — max **3** retries, then `failed`.

Retryable: network errors (`status` 0/null), client-side timeouts (`408`), and
server errors (`5xx`). **Not** retryable: genuine `4xx` such as `422` (attempt
expired) or section-locked — these are real errors and surface immediately as
`failed` with the server detail, distinguishing them from connectivity blips.

### client_seq

The sequence number is minted **once per logical save** (when the debounce
fires), not per attempt, and frozen onto the payload so every retry — automatic
or manual — replays the **same** `client_seq`. It is a strictly incrementing
integer starting at 0, guaranteed to be well within the Postgres `int4` range
(max 2,147,483,647). It is never seeded from `Date.now()`, `performance.now()`,
or any timestamp source — a per-session counter suffices because the server's
idempotency guard needs only strict ordering within an attempt, not global
uniqueness across sessions.

## Server idempotency

`POST /attempts/:id/answer` is idempotent on `(attempt_id, question_id)`. The
response row is pre-inserted at attempt start, so a save is an in-place
`UPDATE`, never an insert — there is no way to produce a duplicate row.

A guard on `client_seq` makes retries safe:

- `client_seq > stored_seq` → the write is applied and a `question.answered`
  event is emitted once.
- `client_seq <= stored_seq` → the write was already committed (and its event
  already emitted) on the first call. The server returns
  `{ ok: true, idempotent: true, status: "already_recorded" }` **without**
  re-processing: no second row, no duplicate event, no double side effect.

This is what makes the "POST succeeded server-side but the response was lost"
case safe — the client's retry with the same `client_seq` is acknowledged
cleanly.

## UI surfaces

- **Palette** (per question): `saved` keeps its colour; `saving`/`retrying`
  pulse; `failed` shows a red border + warning marker.
- **Inline status** (top-right of the question): `✓ Saved` (fades after ~2s),
  `Saving…`, `Retrying… (attempt N/3)`, or a `failed` banner with
  **Retry** / **View details**.
- **Submit button**: disabled while any answer is `unsaved`/`saving`/`retrying`
  (tooltip names the count). If any answer is `failed`, submit is blocked by a
  hard modal: *"N answers failed to save. Retry or remove before submitting."*
- **Page leave**: a `beforeunload` warning fires while any answer is un-synced.
  It warns, it does not block — blocking a browser close is hostile.

Auto-submit on timer expiry is intentionally **not** gated by sync state: when
the window closes the server is authoritative regardless of pending client
saves.

## Telemetry

Failures and retries are recorded through the PR2b event bus as client events
`answer.save_failed` and `answer.save_retried`, flushed to
`POST /attempts/:id/events` and stored server-side for observability.

## Source of truth invariant

**Scoring reads exclusively from `mock_attempt_responses.selected_option_id`.**
The `mock_attempt_events` table is telemetry — useful for diagnostics,
dwell-time analytics, and anti-cheat signals, but never for reconstructing
answers. The `QUESTION_ANSWERED` event is only recorded **after** the response
row update is confirmed to have affected at least one row. If the DB write
fails, the event is never emitted and the endpoint returns 503.

Any future code that attempts to scan events to "recover" missing answers
violates this invariant and should be rejected in review. Likewise, any
wrapper that swallows a failed DB write and continues to emit an event
reintroduces the silent-failure pattern this invariant is designed to prevent.

## Submit consistency check

On submit, the client sends `claimed_answered_count` — the number of questions
whose sync state is `saved` with a non-null `selected_option_id`. The server
compares this against the DB row count. If the client claims more answered
questions than the DB has, the server returns 409 Conflict with body
`{error: "client_server_mismatch"}`. The frontend then reloads attempt state
so the user sees the server's authoritative view before deciding whether to
submit.

This is defense in depth. Fix 2's strict write means the DB is always correct
if the write path works. The submit check catches regressions where a silent
failure path is reintroduced.

## Non-goals

Offline-first persistence across a browser restart, multi-tab conflict
resolution (PR1's single-active-attempt constraint already prevents it), and
server-side delayed-write queues are out of scope here.
