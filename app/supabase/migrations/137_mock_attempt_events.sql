-- PR2b: mock_attempt_events — append-only telemetry log.
--
-- Server-emitted events are written in the same DB call as the state change
-- (attempt.started, question.answered, attempt.submitted, etc.).
-- Client events arrive via POST /study/mocks/attempts/:id/events, async best-effort.
--
-- Parallel-safety: no ALTERs to any existing table. Zero overlap with PR2's tables.

CREATE TABLE IF NOT EXISTS mock_attempt_events (
  id          bigserial PRIMARY KEY,
  attempt_id  uuid        NOT NULL REFERENCES mock_attempts(id) ON DELETE CASCADE,
  user_id     uuid        NOT NULL REFERENCES auth.users(id),
  event_type  text        NOT NULL,
  payload     jsonb       NOT NULL DEFAULT '{}'::jsonb,
  sequence_no bigint,
  source      text        NOT NULL CHECK (source IN ('client', 'server')),
  occurred_at timestamptz NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now()
);

-- Idempotency guard: duplicate (attempt_id, sequence_no) for client events is a no-op.
CREATE UNIQUE INDEX IF NOT EXISTS mock_attempt_events_client_seq
  ON mock_attempt_events (attempt_id, sequence_no)
  WHERE source = 'client' AND sequence_no IS NOT NULL;

-- Primary access pattern: all events for an attempt in time order.
CREATE INDEX IF NOT EXISTS mock_attempt_events_attempt_time
  ON mock_attempt_events (attempt_id, occurred_at);

-- Cross-attempt analytics by event type (PR4/PR5 consumers).
CREATE INDEX IF NOT EXISTS mock_attempt_events_type_time
  ON mock_attempt_events (event_type, recorded_at);
