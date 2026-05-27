# Attempt Events — Design Reference (PR2b)

Append-only telemetry for every mock attempt. Referenced by PR3 (server-authoritative timer), PR4 (time analytics), PR5 (mastery signals).

## Table: `mock_attempt_events`

| Column       | Type        | Notes                                              |
|--------------|-------------|----------------------------------------------------|
| id           | bigserial   | PK                                                 |
| attempt_id   | uuid        | FK → mock_attempts.id ON DELETE CASCADE            |
| user_id      | uuid        | FK → auth.users.id                                 |
| event_type   | text        | Validated at app layer against constants module    |
| payload      | jsonb       | Event-specific fields (see catalogue below)        |
| sequence_no  | bigint      | Client monotonic counter; null for server events   |
| source       | text        | `'client'` or `'server'`                           |
| occurred_at  | timestamptz | Client wall-clock if source=client; else server ts |
| recorded_at  | timestamptz | Server insertion time (DEFAULT now())              |

**Indexes:**
- `UNIQUE (attempt_id, sequence_no) WHERE source='client' AND sequence_no IS NOT NULL` — idempotency guard
- `(attempt_id, occurred_at)` — primary read pattern
- `(event_type, recorded_at)` — cross-attempt analytics (PR4/PR5)

## Event Catalogue v1

### Lifecycle (source=server)

| event_type             | payload fields                                             | Written by        |
|------------------------|------------------------------------------------------------|-------------------|
| `attempt.started`      | `{template_slug}`                                          | `start_attempt`   |
| `attempt.resumed`      | `{}`                                                       | PR3               |
| `attempt.submitted`    | `{score_raw, score_percentage, total_correct, total_wrong, total_unattempted}` | `submit_attempt` |
| `attempt.auto_submitted` | `{}`                                                     | PR3               |
| `attempt.expired`      | `{}`                                                       | PR3               |

### Question Interaction (source=client, server-corroborated)

| event_type          | payload fields                                               |
|---------------------|--------------------------------------------------------------|
| `question.visited`  | `{question_id}`                                              |
| `question.answered` | `{question_id, selected_option_id\|null, time_spent_sec}`   |
| `question.marked`   | `{question_id}`                                              |
| `question.unmarked` | `{question_id}`                                              |
| `question.cleared`  | `{question_id}`                                              |

Server also emits `question.answered` (source=server) in `save_answer` — the server row is the source of truth for any downstream scoring consumer (PR5).

### Anti-Cheat Foundation (source=client, record-only — no enforcement in PR2b)

| event_type            | payload fields                            |
|-----------------------|-------------------------------------------|
| `attempt.tab_blurred` | `{at_question_id}`                        |
| `attempt.tab_focused` | `{at_question_id, away_for_ms}`           |
| `attempt.copy`        | `{at_question_id}`                        |
| `attempt.paste`       | `{at_question_id}`                        |

Enforcement (auto-submit on repeated blur, lockout) is PR3 scope.

### Drift Detection (source=client)

| event_type          | payload fields                                             |
|---------------------|------------------------------------------------------------|
| `attempt.heartbeat` | `{client_remaining_sec, server_remaining_sec_last_seen}`   |

Heartbeats fire every 15 s from the frontend. Drift > 30 s is recorded but not acted upon in PR2b; PR3 will use these rows to trigger server-authoritative timer enforcement.

## Write Paths

### Server events

Written synchronously inside `mock_engine.py` immediately after the state change:

```python
# In submit_attempt, after UPDATE mock_attempts SET status='submitted':
record_server_event(supabase, attempt_id, user_id, ATTEMPT_SUBMITTED,
                    payload={...}, occurred_at=now_iso)
```

Uses the same `_safe()` wrapper pattern — DB hiccup logs a warning but never breaks the hot path.

### Client events

Frontend batches events in `attemptEventBus.js`:
- Ring buffer, max 200 events
- Flush every 5 s OR when buffer ≥ 25 events
- `navigator.sendBeacon` flush on `visibilitychange → hidden` (survives tab close)
- `POST /api/study/mocks/attempts/:id/events`, max 100 events per call
- Idempotent on `sequence_no` — duplicate calls return `{accepted:0, duplicates:N}`

## Downstream Consumers

| PR  | Consumes             | What                                                    |
|-----|----------------------|---------------------------------------------------------|
| PR3 | server rows          | Timer drift → auto-submit; anti-cheat enforcement       |
| PR4 | client + server rows | Time-per-question analytics, time distribution charts   |
| PR5 | server rows only     | Mastery signals, error patterns, topic weakness         |
| PR6 | server + client rows | Admin event-log viewer (admin UI)                        |
