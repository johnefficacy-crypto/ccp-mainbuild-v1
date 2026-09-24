-- VERIFY DB — EXPL-OPTID-01 (migration 307) backfill dry run + post-apply proof
--
-- The unit tests assert migration 307's TEXT: that the projection insert carries
-- pyq_option_id, and that the backfill carries its count and text guards. What
-- they cannot do is tell you how many rows the backfill will actually populate,
-- because that depends on live data. This script answers that, and proves the
-- result afterwards. It is an OPERATOR / VERIFY DB step; do NOT record backfill
-- coverage from code inspection alone.
--
-- Section 1 is READ-ONLY and is the dry run. Run it BEFORE applying 307.
-- Sections 2-4 run AFTER applying 307.

-- ── 1. DRY RUN — what would the backfill do? (read-only, run before 307) ──────
-- Same logic as 307's UPDATE, counting instead of writing. `would_stay_null`
-- is rows the backfill declines to guess at: the count guard or the text guard
-- failed. Those keep using the positional fallback, exactly as today.

with src as (
  select o.id as pyq_option_id, o.question_id as pyq_question_id, o.option_text,
         row_number() over (partition by o.question_id
                            order by o.option_label, o.id) - 1 as opt_idx,
         count(*) over (partition by o.question_id) as src_n
  from public.pyq_options o
  where o.reviewer_status = 'verified'
), tgt as (
  select mo.id as mock_option_id, mo.option_index, mo.option_text,
         q.pyq_question_id,
         count(*) over (partition by mo.question_id) as tgt_n
  from public.mock_question_options mo
  join public.mock_question_bank q on q.id = mo.question_id
  where q.pyq_question_id is not null
)
select count(*)                                           as pyq_derived_rows,
       count(*) filter (where s.pyq_option_id is not null) as would_populate,
       count(*) filter (where s.pyq_option_id is null)     as would_stay_null
from tgt t
left join src s
  on  s.pyq_question_id = t.pyq_question_id
  and s.opt_idx         = t.option_index
  and s.src_n           = t.tgt_n
  and s.option_text is not distinct from t.option_text;

-- Rows with no PYQ lineage at all. 307 never touches these and they stay NULL
-- permanently by design (authored + imported questions have no source option).
select count(*) as authored_rows_never_backfilled
from public.mock_question_options mo
join public.mock_question_bank q on q.id = mo.question_id
where q.pyq_question_id is null;

-- WHY a row would stay null, split by guard. Use this to decide whether the
-- fallback can eventually be dropped, or whether a set of papers needs re-syncing.
with src as (
  select o.question_id as pyq_question_id, o.option_text,
         row_number() over (partition by o.question_id
                            order by o.option_label, o.id) - 1 as opt_idx,
         count(*) over (partition by o.question_id) as src_n
  from public.pyq_options o
  where o.reviewer_status = 'verified'
), tgt as (
  select mo.id as mock_option_id, mo.option_index, mo.option_text,
         q.pyq_question_id,
         count(*) over (partition by mo.question_id) as tgt_n
  from public.mock_question_options mo
  join public.mock_question_bank q on q.id = mo.question_id
  where q.pyq_question_id is not null
)
select
  count(*) filter (
    where not exists (select 1 from src s
                      where s.pyq_question_id = t.pyq_question_id
                        and s.opt_idx = t.option_index)
  ) as no_source_option_at_that_index,
  count(*) filter (
    where exists (select 1 from src s
                  where s.pyq_question_id = t.pyq_question_id
                    and s.opt_idx = t.option_index
                    and s.src_n <> t.tgt_n)
  ) as count_guard_failed,
  count(*) filter (
    where exists (select 1 from src s
                  where s.pyq_question_id = t.pyq_question_id
                    and s.opt_idx = t.option_index
                    and s.src_n = t.tgt_n
                    and s.option_text is distinct from t.option_text)
  ) as text_guard_failed
from tgt t;

-- ── 2. POST-APPLY — column, FK action and index are as specified ─────────────

select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name   = 'mock_question_options'
  and column_name  = 'pyq_option_id';
-- expect: uuid, is_nullable = YES

select con.conname, con.confdeltype
from pg_constraint con
join pg_class rel on rel.oid = con.conrelid
where rel.relname = 'mock_question_options'
  and con.contype = 'f'
  and con.conkey @> array[(
    select attnum from pg_attribute
    where attrelid = 'public.mock_question_options'::regclass
      and attname  = 'pyq_option_id'
  )::smallint];
-- expect confdeltype = 'n' (SET NULL). 'c' (CASCADE) is WRONG and would delete
-- projected option rows out from under in-flight attempts.

select indexname from pg_indexes
where schemaname = 'public'
  and tablename  = 'mock_question_options'
  and indexname  = 'idx_mock_question_options_pyq_option';

-- ── 3. POST-APPLY — the backfill wrote nothing it should not have ────────────
-- Every backfilled row must point at a pyq_option belonging to the SAME source
-- question as its projected parent, with identical text. Zero rows is the pass.

select count(*) as backfill_violations
from public.mock_question_options mo
join public.mock_question_bank  q  on q.id = mo.question_id
join public.pyq_options         po on po.id = mo.pyq_option_id
where mo.pyq_option_id is not null
  and (po.question_id is distinct from q.pyq_question_id
       or po.option_text is distinct from mo.option_text);

-- No projected question may end up with the same source option on two rows.
select count(*) as duplicate_source_options
from (
  select question_id, pyq_option_id
  from public.mock_question_options
  where pyq_option_id is not null
  group by 1, 2
  having count(*) > 1
) d;

-- ── 4. POST-APPLY — a fresh projection carries the id on every option ────────
-- Re-project ONE already-verified PYQ question and confirm no option is null.
-- Substitute a real id; the RPC is service_role only.
\set Q '00000000-0000-0000-0000-000000000000'

-- select public.project_pyq_question_to_mock_bank(:'Q', null, 'EXPL-OPTID-01 verify');

select count(*) filter (where mo.pyq_option_id is null) as null_after_reprojection,
       count(*)                                          as total_options
from public.mock_question_options mo
join public.mock_question_bank q on q.id = mo.question_id
where q.pyq_question_id = :'Q';
-- expect null_after_reprojection = 0
