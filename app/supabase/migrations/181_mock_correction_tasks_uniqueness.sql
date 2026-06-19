-- 181: Enforce uniqueness for drafted mock corrections.
--
-- Adds DB-enforced uniqueness on the effective deduplication key:
--   (mock_test_id, user_id, category, topic)  WHERE state = 'drafted'
--
-- NULL topic is handled by a separate partial index because NULL is never
-- equal to NULL in a standard unique index, which would allow unlimited
-- NULL-topic duplicates. Two partial indexes together enforce the invariant
-- for both non-null and null topic values:
--
--   non-null: mock_correction_tasks_drafted_unique
--   null:     mock_correction_tasks_drafted_null_topic_unique
--
-- This replaces the read-before-insert guard in MasteryWriter._correction_exists,
-- which is SERIAL-retry safe but explicitly documented as NOT concurrency-safe.
-- Concurrent inserts with the same key will now fail with a unique-constraint
-- violation; callers should use ON CONFLICT DO NOTHING or handle the 23505 error.

-- Deduplicate existing rows before adding the constraint.  Keep the oldest
-- row (smallest created_at, then smallest id as tie-breaker) per effective key.

-- Non-null topic: deduplicate.
-- COALESCE handles rows where created_at is NULL (rows inserted before
-- the column had a default); these sort before any real timestamp so the
-- oldest-row-wins invariant is preserved deterministically.
with ranked_nn as (
  select
    id,
    row_number() over (
      partition by mock_test_id, user_id, category, topic
      order by coalesce(created_at, '1970-01-01'::timestamptz) asc, id asc
    ) as rn
  from public.mock_correction_tasks
  where state = 'drafted' and topic is not null
)
delete from public.mock_correction_tasks
where id in (select id from ranked_nn where rn > 1);

-- Null topic: deduplicate.
with ranked_null as (
  select
    id,
    row_number() over (
      partition by mock_test_id, user_id, category
      order by coalesce(created_at, '1970-01-01'::timestamptz) asc, id asc
    ) as rn
  from public.mock_correction_tasks
  where state = 'drafted' and topic is null
)
delete from public.mock_correction_tasks
where id in (select id from ranked_null where rn > 1);

-- Index for non-null topic drafted corrections.
create unique index if not exists mock_correction_tasks_drafted_unique
  on public.mock_correction_tasks(mock_test_id, user_id, category, topic)
  where state = 'drafted' and topic is not null;

-- Index for null-topic drafted corrections.
create unique index if not exists mock_correction_tasks_drafted_null_topic_unique
  on public.mock_correction_tasks(mock_test_id, user_id, category)
  where state = 'drafted' and topic is null;

notify pgrst, 'reload schema';
