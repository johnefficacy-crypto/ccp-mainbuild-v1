-- regression_184_index_repair.sql
--
-- Manual PostgreSQL regression tests for the migration 184 index-repair guard.
--
-- Verifies that the pre-create guard in migration 184 detects and replaces a
-- same-named index that has the wrong shape, so 'CREATE UNIQUE INDEX IF NOT
-- EXISTS' always installs the correct index rather than silently skipping.
--
-- Prerequisites:
--   Migration 183 must be applied (mock_question_bank with pyq_question_id column
--   must exist).  Migration 184 must NOT be applied yet, or the correct index must
--   be dropped first (the BEGIN/ROLLBACK pattern restores state).
--
-- Usage:
--   psql "$DATABASE_URL" -f regression_184_index_repair.sql
--
-- Expected output (two NOTICE lines, no errors):
--   NOTICE:  PASS test 1: multi-column same-named index was detected and replaced
--   NOTICE:  PASS test 2: wrong-predicate same-named index was detected and replaced

\set ON_ERROR_STOP on

-- ─────────────────────────────────────────────────────────────────────────────
-- Shared guard snippet (must stay byte-for-byte identical to migration 184 §1).
-- ─────────────────────────────────────────────────────────────────────────────
-- If the migration guard is updated, update these regression tests in the same
-- commit so the guard and its regressions never drift.

-- ── Test 1: multi-column same-named index ─────────────────────────────────
-- Scenario: a UNIQUE (pyq_question_id, id) index exists with the right name.
-- Expected: guard drops it; correct single-column partial index is created.

BEGIN;

-- Set up: ensure only the wrong multi-column index exists.
drop index if exists public.uq_mock_qbank_pyq_question_id;
create unique index uq_mock_qbank_pyq_question_id
    on public.mock_question_bank(pyq_question_id, id);

-- Confirm setup: index has two key columns.
do $$
begin
    assert exists (
        select 1
        from pg_class ci
        join pg_index  i  on i.indexrelid = ci.oid
        join pg_class  ct on ct.oid        = i.indrelid
        join pg_namespace n on n.oid       = ct.relnamespace
        where n.nspname  = 'public'
          and ct.relname = 'mock_question_bank'
          and ci.relname = 'uq_mock_qbank_pyq_question_id'
          and i.indnkeyatts = 2
    ), 'setup failed: multi-column index not created';
end;
$$;

-- Run guard (verbatim copy of migration 184 §1 pre-create block).
do $$
begin
    if exists (
        select 1
        from pg_class ci
        join pg_index  i  on i.indexrelid = ci.oid
        join pg_class  ct on ct.oid        = i.indrelid
        join pg_namespace n on n.oid       = ct.relnamespace
        where n.nspname  = 'public'
          and ct.relname = 'mock_question_bank'
          and ci.relname = 'uq_mock_qbank_pyq_question_id'
          and not (
              i.indisunique = true
              and i.indnkeyatts = 1
              and i.indnatts    = 1
              and (select a.attname from pg_attribute a
                   where a.attrelid = i.indrelid
                     and a.attnum   = i.indkey[0]) = 'pyq_question_id'
              and coalesce(trim(both '()' from pg_get_expr(i.indpred, i.indrelid)) = 'pyq_question_id IS NOT NULL', false)
          )
    ) then
        execute 'drop index public.uq_mock_qbank_pyq_question_id';
    end if;
end;
$$;

create unique index if not exists uq_mock_qbank_pyq_question_id
    on public.mock_question_bank(pyq_question_id)
    where pyq_question_id is not null;

-- Assert: correct index is now in place.
do $$
declare
    v_count int;
begin
    select count(*) into v_count
    from pg_class ci
    join pg_index  i  on i.indexrelid = ci.oid
    join pg_class  ct on ct.oid        = i.indrelid
    join pg_namespace n on n.oid       = ct.relnamespace
    where n.nspname  = 'public'
      and ct.relname = 'mock_question_bank'
      and ci.relname = 'uq_mock_qbank_pyq_question_id'
      and i.indisunique                       = true
      and i.indnkeyatts                      = 1
      and i.indnatts                         = 1
      and (select a.attname from pg_attribute a
           where a.attrelid = i.indrelid
             and a.attnum   = i.indkey[0])   = 'pyq_question_id'
      and trim(both '()' from pg_get_expr(i.indpred, i.indrelid)) = 'pyq_question_id IS NOT NULL';

    if v_count = 0 then
        raise exception
            'FAIL test 1: correct index not present after multi-column replacement';
    end if;
    raise notice 'PASS test 1: multi-column same-named index was detected and replaced';
end;
$$;

ROLLBACK;


-- ── Test 2: wrong-predicate same-named index ──────────────────────────────
-- Scenario: a UNIQUE (pyq_question_id) WHERE reviewer_status = 'published'
-- index exists with the right name but the wrong partial predicate.
-- Expected: guard drops it; correct partial predicate is created.

BEGIN;

drop index if exists public.uq_mock_qbank_pyq_question_id;
create unique index uq_mock_qbank_pyq_question_id
    on public.mock_question_bank(pyq_question_id)
    where reviewer_status = 'published';

-- Confirm setup: predicate is wrong.
do $$
begin
    assert exists (
        select 1
        from pg_class ci
        join pg_index  i  on i.indexrelid = ci.oid
        join pg_class  ct on ct.oid        = i.indrelid
        join pg_namespace n on n.oid       = ct.relnamespace
        where n.nspname  = 'public'
          and ct.relname = 'mock_question_bank'
          and ci.relname = 'uq_mock_qbank_pyq_question_id'
          and pg_get_expr(i.indpred, i.indrelid) <> 'pyq_question_id IS NOT NULL'
    ), 'setup failed: wrong-predicate index not created';
end;
$$;

-- Run guard (verbatim copy of migration 184 §1 pre-create block).
do $$
begin
    if exists (
        select 1
        from pg_class ci
        join pg_index  i  on i.indexrelid = ci.oid
        join pg_class  ct on ct.oid        = i.indrelid
        join pg_namespace n on n.oid       = ct.relnamespace
        where n.nspname  = 'public'
          and ct.relname = 'mock_question_bank'
          and ci.relname = 'uq_mock_qbank_pyq_question_id'
          and not (
              i.indisunique = true
              and i.indnkeyatts = 1
              and i.indnatts    = 1
              and (select a.attname from pg_attribute a
                   where a.attrelid = i.indrelid
                     and a.attnum   = i.indkey[0]) = 'pyq_question_id'
              and coalesce(trim(both '()' from pg_get_expr(i.indpred, i.indrelid)) = 'pyq_question_id IS NOT NULL', false)
          )
    ) then
        execute 'drop index public.uq_mock_qbank_pyq_question_id';
    end if;
end;
$$;

create unique index if not exists uq_mock_qbank_pyq_question_id
    on public.mock_question_bank(pyq_question_id)
    where pyq_question_id is not null;

-- Assert: correct index is now in place.
do $$
declare
    v_count int;
begin
    select count(*) into v_count
    from pg_class ci
    join pg_index  i  on i.indexrelid = ci.oid
    join pg_class  ct on ct.oid        = i.indrelid
    join pg_namespace n on n.oid       = ct.relnamespace
    where n.nspname  = 'public'
      and ct.relname = 'mock_question_bank'
      and ci.relname = 'uq_mock_qbank_pyq_question_id'
      and i.indisunique                       = true
      and i.indnkeyatts                      = 1
      and i.indnatts                         = 1
      and (select a.attname from pg_attribute a
           where a.attrelid = i.indrelid
             and a.attnum   = i.indkey[0])   = 'pyq_question_id'
      and trim(both '()' from pg_get_expr(i.indpred, i.indrelid)) = 'pyq_question_id IS NOT NULL';

    if v_count = 0 then
        raise exception
            'FAIL test 2: correct index not present after wrong-predicate replacement';
    end if;
    raise notice 'PASS test 2: wrong-predicate same-named index was detected and replaced';
end;
$$;

ROLLBACK;


-- ── Test 3: same-named non-partial index ──────────────────────────────────
-- Scenario: a UNIQUE (pyq_question_id) index exists with the right name but
-- no WHERE clause.  pg_get_expr(indpred, indrelid) returns NULL for a
-- non-partial index.  Without coalesce, the predicate comparison evaluates
-- to NULL inside NOT (...), which is also NULL, so the guard does not fire.
-- Expected: guard drops it; correct partial predicate is created.

BEGIN;

drop index if exists public.uq_mock_qbank_pyq_question_id;
create unique index uq_mock_qbank_pyq_question_id
    on public.mock_question_bank(pyq_question_id);

-- Confirm setup: index is non-partial (indpred IS NULL).
do $$
begin
    assert exists (
        select 1
        from pg_class ci
        join pg_index  i  on i.indexrelid = ci.oid
        join pg_class  ct on ct.oid        = i.indrelid
        join pg_namespace n on n.oid       = ct.relnamespace
        where n.nspname  = 'public'
          and ct.relname = 'mock_question_bank'
          and ci.relname = 'uq_mock_qbank_pyq_question_id'
          and i.indpred is null
    ), 'setup failed: non-partial index not created';
end;
$$;

-- Run guard (verbatim copy of migration 184 §1 pre-create block).
do $$
begin
    if exists (
        select 1
        from pg_class ci
        join pg_index  i  on i.indexrelid = ci.oid
        join pg_class  ct on ct.oid        = i.indrelid
        join pg_namespace n on n.oid       = ct.relnamespace
        where n.nspname  = 'public'
          and ct.relname = 'mock_question_bank'
          and ci.relname = 'uq_mock_qbank_pyq_question_id'
          and not (
              i.indisunique = true
              and i.indnkeyatts = 1
              and i.indnatts    = 1
              and (select a.attname from pg_attribute a
                   where a.attrelid = i.indrelid
                     and a.attnum   = i.indkey[0]) = 'pyq_question_id'
              and coalesce(trim(both '()' from pg_get_expr(i.indpred, i.indrelid)) = 'pyq_question_id IS NOT NULL', false)
          )
    ) then
        execute 'drop index public.uq_mock_qbank_pyq_question_id';
    end if;
end;
$$;

create unique index if not exists uq_mock_qbank_pyq_question_id
    on public.mock_question_bank(pyq_question_id)
    where pyq_question_id is not null;

-- Assert: correct index is now in place.
do $$
declare
    v_count int;
begin
    select count(*) into v_count
    from pg_class ci
    join pg_index  i  on i.indexrelid = ci.oid
    join pg_class  ct on ct.oid        = i.indrelid
    join pg_namespace n on n.oid       = ct.relnamespace
    where n.nspname  = 'public'
      and ct.relname = 'mock_question_bank'
      and ci.relname = 'uq_mock_qbank_pyq_question_id'
      and i.indisunique                       = true
      and i.indnkeyatts                      = 1
      and i.indnatts                         = 1
      and (select a.attname from pg_attribute a
           where a.attrelid = i.indrelid
             and a.attnum   = i.indkey[0])   = 'pyq_question_id'
      and trim(both '()' from pg_get_expr(i.indpred, i.indrelid)) = 'pyq_question_id IS NOT NULL';

    if v_count = 0 then
        raise exception
            'FAIL test 3: correct index not present after non-partial replacement';
    end if;
    raise notice 'PASS test 3: non-partial same-named index was detected and replaced';
end;
$$;

ROLLBACK;
