-- 245_integer_numeric_answer.sql
-- Integer / numerical answer runtime contract (PYQ checklist PR-11, gate G11:
-- "Implement integer/numerical answer scoring before enabling integer
-- questions"). Adds the canonical correct-numeric-answer store on the mock bank
-- and the learner's typed numeric answer on attempt responses.
--
-- Both columns are additive and nullable; MCQ/MSQ rows and responses keep NULL
-- and are unaffected. No RLS change — these are new columns on existing tables
-- that already carry their table's policies. Scoring always reads the correct
-- value from the FROZEN question_snapshot (written at attempt start), never from
-- mock_question_bank at submit time, so the immutable-attempt contract holds.

alter table public.mock_question_bank
  add column if not exists numeric_answer jsonb;

comment on column public.mock_question_bank.numeric_answer is
  'Correct numeric answer for integer/numerical questions: {"value": <number>, "tolerance": <number> (absolute, default 0)}. NULL for MCQ/MSQ. Frozen into mock_attempt_responses.question_snapshot at attempt start; the deterministic scorer grades |submitted - value| <= tolerance.';

alter table public.mock_attempt_responses
  add column if not exists numeric_answer numeric;

comment on column public.mock_attempt_responses.numeric_answer is
  'Learner-entered numeric answer for integer/numerical questions. NULL for MCQ/MSQ responses (which use selected_option_id). Mutually exclusive with selected_option_id per response.';
