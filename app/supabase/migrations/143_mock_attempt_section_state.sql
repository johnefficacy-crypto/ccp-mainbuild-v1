ALTER TABLE mock_attempts
  ADD COLUMN IF NOT EXISTS current_section_index int DEFAULT 0,
  ADD COLUMN IF NOT EXISTS section_locks_enabled bool DEFAULT false;

CREATE TABLE IF NOT EXISTS mock_attempt_section_state (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id uuid NOT NULL REFERENCES mock_attempts(id) ON DELETE CASCADE,
  section_index int NOT NULL,
  entered_at timestamptz,
  exited_at timestamptz,
  expires_at timestamptz,
  is_completed bool DEFAULT false,
  time_used_sec int DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (attempt_id, section_index)
);
