-- 290_study_tasks_day_ordinal.sql
-- PLAN-UI-01 — an explicit within-day ordering for the drag-and-drop planner.
--
-- `study_tasks` had no ordinal. The only per-task ordering field was
-- `priority_score numeric(5,2)`, which is the deterministic engine's OUTPUT:
-- `_build_tasks` copies it from the scored coverage row and `why_this_task`
-- records the same number as the planner's own justification. Rewriting it to
-- store a drag position would make that justification a lie and corrupt a
-- signal other surfaces read.
--
-- `day_ordinal` is presentation order within one `scheduled_date`, owned by the
-- user's arrangement. It is NULL for every task the user has never arranged;
-- readers sort `day_ordinal nulls last, priority_score desc` so an unarranged
-- day keeps exactly the ordering it has today.
--
-- Nullable with no default: an absent ordinal is meaningful ("never arranged"),
-- and no existing insert path has to learn the column.

alter table public.study_tasks
  add column if not exists day_ordinal integer;

-- The board reads one plan's tasks across a seven-day window, ordered.
create index if not exists idx_study_tasks_day_order
  on public.study_tasks(plan_id, scheduled_date, day_ordinal);

notify pgrst, 'reload schema';
