-- 297_descriptive_attempts_answer_mode.sql
-- Answer writing: record HOW an attempt was answered — typed, or written by
-- hand and photographed.
--
-- WHY THIS LANDS WITH THE HISTORY, NOT WITH THE UPLOAD
-- The answer history has to say which of an aspirant's attempts were
-- handwritten: two attempts at one question, one typed and one on paper, are
-- not the same kind of practice and cannot be read side by side without the
-- distinction. The history surface therefore needs the column before the
-- upload path that populates it exists. Until then every row reads 'typed',
-- which is true — there was no other way to answer.
--
-- 'typed' NOT NULL, not a nullable mode: an attempt that already exists was
-- typed. There is no third thing it could have been, so a null here would
-- assert an uncertainty that does not exist.
alter table public.descriptive_attempts
  add column if not exists answer_mode text not null default 'typed'
    check (answer_mode in ('typed', 'handwritten'));

comment on column public.descriptive_attempts.answer_mode is
  'How the answer was produced: typed into the editor, or handwritten and '
  'uploaded as page images. Handwritten attempts carry no word_count — nothing '
  'has read the pages — and their self-evaluation rubric is identical.';

-- The history surface filters and sorts by the attempt''s own timeline, and
-- `started_at` is not unique. `id` is the tiebreak that lets range pagination
-- partition the result instead of overlapping it.
create index if not exists idx_descriptive_attempts_user_started
  on public.descriptive_attempts(user_id, started_at desc, id);

notify pgrst, 'reload schema';
