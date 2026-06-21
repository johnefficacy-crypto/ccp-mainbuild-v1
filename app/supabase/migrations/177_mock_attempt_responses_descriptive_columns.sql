-- =============================================================================
-- 177_mock_attempt_responses_descriptive_columns.sql
-- B-PR1: descriptive-answer schema foundation (additive response columns).
--
-- Adds the per-response columns needed to persist typed descriptive answers and
-- their evaluation lifecycle.  All columns are additive and safe for existing
-- MCQ rows:
--
--   answer_text         text             — typed answer body (NULL for MCQ).
--   word_count          int              — cached word count; NULL or >= 0.
--   autosave_snapshot   jsonb            — latest client autosave; default {}.
--   evaluation_status   text             — evaluation lifecycle; MCQ rows stay
--                                          'not_required'.
--   rubric_score        jsonb            — structured rubric result; default {}.
--
-- Existing MCQ rows receive the NOT NULL defaults automatically via ALTER TABLE;
-- no backfill beyond those defaults is performed.  No evaluation tables, answer
-- assets, or indexes are introduced here — those land in later PRs.
--
-- This migration does NOT reference the new mock_question_type enum values added
-- in 176; the descriptive columns are type-agnostic on purpose.
-- =============================================================================

alter table public.mock_attempt_responses
  add column if not exists answer_text       text,
  add column if not exists word_count        int,
  add column if not exists autosave_snapshot jsonb not null default '{}'::jsonb,
  add column if not exists evaluation_status text  not null default 'not_required',
  add column if not exists rubric_score      jsonb not null default '{}'::jsonb;

-- Non-negative (or NULL) word count.
alter table public.mock_attempt_responses
  drop constraint if exists mock_attempt_responses_word_count_check;
alter table public.mock_attempt_responses
  add constraint mock_attempt_responses_word_count_check
  check (word_count is null or word_count >= 0);

-- Evaluation lifecycle gate.
alter table public.mock_attempt_responses
  drop constraint if exists mock_attempt_responses_evaluation_status_check;
alter table public.mock_attempt_responses
  add constraint mock_attempt_responses_evaluation_status_check
  check (
    evaluation_status in (
      'not_required',
      'pending_evaluation',
      'in_review',
      'completed'
    )
  );

comment on column public.mock_attempt_responses.answer_text is
  'Typed descriptive answer body. NULL for MCQ/integer/MSQ responses.';
comment on column public.mock_attempt_responses.word_count is
  'Cached word count of answer_text. NULL when not applicable; otherwise >= 0.';
comment on column public.mock_attempt_responses.autosave_snapshot is
  'Latest client-side autosave payload for an in-progress descriptive answer.';
comment on column public.mock_attempt_responses.evaluation_status is
  'Evaluation lifecycle: not_required | pending_evaluation | in_review | completed. '
  'MCQ-style responses remain not_required.';
comment on column public.mock_attempt_responses.rubric_score is
  'Structured rubric/score result for a completed descriptive evaluation.';

notify pgrst, 'reload schema';
