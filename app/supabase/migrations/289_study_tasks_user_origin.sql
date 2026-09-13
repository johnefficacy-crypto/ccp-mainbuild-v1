-- 289_study_tasks_user_origin.sql
-- PLAN-PIN-01 — user-arranged tasks must survive the nightly regeneration.
--
-- Today `_persist` (app/backend/app/study_os/planner.py) deletes every
-- still-`planned` task for today on the active plan before re-inserting the
-- freshly-computed set, and `regenerate_stale_plans` runs that sweep nightly.
-- No column on `study_tasks` could express "a person placed this, leave it
-- alone": `status` describes progress, not provenance, and every status value
-- already carries an unrelated meaning (`carried_forward` is written only by
-- POST /api/study/tasks/carry-forward).
--
-- `source` is that column. It is provenance only — it does not gate reads, does
-- not change scoring, and is never consulted by any status transition.
--
--   planner  — emitted by the deterministic planner; regeneration owns it and
--              may delete and re-insert it freely (existing behaviour).
--   user     — placed by the aspirant; regeneration must never delete it.
--
-- Backfill: `not null default 'planner'` stamps every pre-existing row with the
-- planner value in the same statement, so no historical task is mistaken for a
-- user placement and no existing insert path has to learn a new column.

alter table public.study_tasks
  add column if not exists source text not null default 'planner';

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'study_tasks_source_check'
      and conrelid = 'public.study_tasks'::regclass
  ) then
    alter table public.study_tasks
      add constraint study_tasks_source_check
      check (source in ('planner', 'user'));
  end if;
end $$;

-- The regeneration path reads user-placed tasks for one plan/day on every
-- apply; the planner-row majority is excluded from the index entirely.
create index if not exists idx_study_tasks_user_placed
  on public.study_tasks(plan_id, scheduled_date)
  where source = 'user';

notify pgrst, 'reload schema';
