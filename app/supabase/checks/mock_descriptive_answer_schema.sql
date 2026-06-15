-- B-PR1 descriptive-answer schema foundation smoke check.
-- Read-only: SELECT-only assertions, raises an exception on any mismatch.
-- Verifies migrations 174 + 175 landed: the descriptive mock_question_type
-- enum values and the additive mock_attempt_responses columns/constraints.
--
-- Manual validation:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f app/supabase/checks/mock_descriptive_answer_schema.sql

begin read only;

do $$
declare
  missing_enum text[];
  expected_enum constant text[] :=
    array['mcq','integer','msq','descriptive','essay','precis','letter'];
  v_count int;
begin
  -- ── 1. Enum values (174) ──────────────────────────────────────────────────
  select array_agg(v)
    into missing_enum
    from unnest(expected_enum) as v
   where not exists (
     select 1 from pg_enum
      where enumtypid = 'mock_question_type'::regtype
        and enumlabel = v
   );

  if missing_enum is not null then
    raise exception 'mock_question_type is missing enum values: %', missing_enum;
  end if;

  -- ── 2. Additive columns (175) ─────────────────────────────────────────────
  -- answer_text: text, nullable.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_attempt_responses'
       and column_name = 'answer_text' and data_type = 'text'
       and is_nullable = 'YES'
  ) then
    raise exception 'mock_attempt_responses.answer_text (text, nullable) missing';
  end if;

  -- word_count: integer, nullable.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_attempt_responses'
       and column_name = 'word_count' and data_type = 'integer'
       and is_nullable = 'YES'
  ) then
    raise exception 'mock_attempt_responses.word_count (int, nullable) missing';
  end if;

  -- autosave_snapshot: jsonb, NOT NULL, default '{}'.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_attempt_responses'
       and column_name = 'autosave_snapshot' and data_type = 'jsonb'
       and is_nullable = 'NO' and column_default like '%''{}''::jsonb%'
  ) then
    raise exception 'mock_attempt_responses.autosave_snapshot (jsonb not null default {}) missing';
  end if;

  -- evaluation_status: text, NOT NULL, default 'not_required'.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_attempt_responses'
       and column_name = 'evaluation_status' and data_type = 'text'
       and is_nullable = 'NO' and column_default like '%not_required%'
  ) then
    raise exception 'mock_attempt_responses.evaluation_status (text not null default not_required) missing';
  end if;

  -- rubric_score: jsonb, NOT NULL, default '{}'.
  if not exists (
    select 1 from information_schema.columns
     where table_schema = 'public' and table_name = 'mock_attempt_responses'
       and column_name = 'rubric_score' and data_type = 'jsonb'
       and is_nullable = 'NO' and column_default like '%''{}''::jsonb%'
  ) then
    raise exception 'mock_attempt_responses.rubric_score (jsonb not null default {}) missing';
  end if;

  -- ── 3. Check constraints (175) ────────────────────────────────────────────
  select count(*)
    into v_count
    from pg_constraint
   where conrelid = 'public.mock_attempt_responses'::regclass
     and contype = 'c'
     and conname = 'mock_attempt_responses_word_count_check';
  if v_count <> 1 then
    raise exception 'mock_attempt_responses_word_count_check constraint missing';
  end if;

  select count(*)
    into v_count
    from pg_constraint
   where conrelid = 'public.mock_attempt_responses'::regclass
     and contype = 'c'
     and conname = 'mock_attempt_responses_evaluation_status_check';
  if v_count <> 1 then
    raise exception 'mock_attempt_responses_evaluation_status_check constraint missing';
  end if;
end $$;

rollback;
