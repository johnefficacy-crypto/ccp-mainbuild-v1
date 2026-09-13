-- PLAN-POOL-01 — live probes. SELECT-ONLY. No INSERT/UPDATE/DELETE/DDL.
-- Run block by block; each block is independent and prints its own header.
-- Written, not run, by the investigation. Section numbers match
-- workbench/investigations/PLAN-POOL-01_discovery.md § "Requires live data".
--
--   exam   upsc-cse   5466e62f-7382-4a38-ba96-2fe5fbfeaba2
--   phase  Mains      626ec667-4bbf-4420-8715-48c5b83e0d11
--   phase  Prelims    6566d50e-7f1c-4410-aa36-8142dfe9a79b
--   user              664d94c6-…  <- fill in the full uuid before running §3,§5,§6,§7
--   plan              e87f1c91-850f-43ca-9edf-9bae3b2c2140


-- ─── §1  Is the Mains phase a template, or cycle-attached? ────────────────
-- exam_target_window.py:56-58 — a phase with exam_cycle_id IS NULL is a
-- template and is NEVER a plan target. If 626ec667 shows a null cycle, the
-- 1,497 Mains coverage rows are unreachable by the planner for every user.
select
  p.id,
  p.phase_slug,
  p.phase_name,
  p.phase_order,
  p.status,
  p.exam_cycle_id,
  case when p.exam_cycle_id is null then 'TEMPLATE (never targeted)'
       else 'cycle-attached' end                       as targetability,
  p.phase_start,
  p.phase_end,
  c.cycle_name,
  c.status                                             as cycle_status,
  c.reviewer_status                                    as cycle_reviewer_status
from public.exam_phases p
left join public.exam_cycles c on c.id = p.exam_cycle_id
where p.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
order by p.exam_cycle_id nulls first, p.phase_order;


-- ─── §2  Which cycle and which phase does the resolver return today? ──────
-- 2a. The cycle candidates _pick_cycle sees (exam_target_window.py:22-28,162-196):
--     verified, not cancelled. Order below mirrors the ladder's preference.
select
  c.id,
  c.cycle_name,
  c.year,
  c.status,
  c.reviewer_status,
  c.exam_start,
  c.planner_activation_enabled,
  case c.status when 'active' then 1 when 'open' then 2
       when 'expected' then case when c.exam_start > current_date then 3 else 9 end
       else 9 end                                      as ladder_rank
from public.exam_cycles c
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'verified'
  and c.status <> 'cancelled'
order by ladder_rank, c.exam_start nulls last, c.created_at desc;

-- 2b. For EACH candidate cycle, which of its phases the ladder would return:
--     current phase (status active, started, not ended) then earliest future.
select
  c.id                                                 as cycle_id,
  c.cycle_name,
  p.id                                                 as phase_id,
  p.phase_slug,
  p.status                                             as phase_status,
  p.phase_start,
  p.phase_end,
  p.phase_order,
  case
    when p.status = 'active'
     and p.phase_start is not null
     and p.phase_start <= current_date
     and (p.phase_end is null or p.phase_end >= current_date)
      then 'CURRENT (branch 2)'
    when p.phase_start > current_date
     and p.status in ('expected','active')
     and (p.phase_end is null or p.phase_end >= current_date)
      then 'future candidate (branch 3)'
    else 'not selectable'
  end                                                  as ladder_branch
from public.exam_cycles c
join public.exam_phases p on p.exam_cycle_id = c.id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'verified'
  and c.status <> 'cancelled'
order by c.exam_start nulls last, p.phase_order;


-- ─── §3  What did the plan actually record? ───────────────────────────────
-- locked_topic_count is written AFTER the phase filter (planner.py:1528,1691).
--   13   → the phase filter fired; this report is correct.
--   1510 → it did not; the report is wrong and the cause is elsewhere.
select
  pl.id                                                as plan_id,
  pl.status,
  pl.exam_id,
  pl.active_phase_id,
  ph.phase_slug                                        as active_phase_slug,
  v.version_number,
  v.activated_at,
  v.input_context ->> 'locked_topic_count'             as locked_topic_count,
  v.input_context ->> 'exam_slug'                      as exam_slug,
  v.input_context ->> 'reason'                         as reason,
  v.input_context ->> 'calibration_gate_status'        as calibration_gate_status,
  v.input_context ->> 'mastery_read_failed'            as mastery_read_failed,
  v.input_context -> 'study_policy'                    as study_policy,
  v.output_summary                                     as output_summary
from public.study_plans pl
left join public.study_plan_versions v on v.id = pl.current_plan_version_id
left join public.exam_phases ph on ph.id = pl.active_phase_id
where pl.id = 'e87f1c91-850f-43ca-9edf-9bae3b2c2140';


-- ─── §4  Provenance: the 13 vs the 1,497 ──────────────────────────────────
-- 4a. Rollup by phase / section-nullness / writer.
select
  c.exam_phase_id,
  ph.phase_slug,
  (c.section_id is not null)                           as has_section,
  c.source_basis,
  c.model_version,
  count(*)                                             as rows,
  min(c.created_at)                                    as first_written,
  max(c.created_at)                                    as last_written,
  min(c.reviewed_at)                                   as first_locked,
  max(c.reviewed_at)                                   as last_locked
from public.exam_topic_coverage c
left join public.exam_phases ph on ph.id = c.exam_phase_id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
group by 1,2,3,4,5
order by rows desc;

-- 4b. The 13 Prelims rows in full — which section each points at, and whether
--     that section is compulsory (hence always in scope, planner.py:493-495).
select
  c.id                                                 as coverage_id,
  t.name                                               as topic,
  s.slug                                               as subject_slug,
  s.subject_group,
  eps.section_label,
  eps.selection_kind,
  eps.elective_group,
  c.exam_priority_score,
  c.is_high_yield,
  c.source_basis,
  c.model_version,
  c.created_at
from public.exam_topic_coverage c
join public.topics t   on t.id = c.topic_id
left join public.subjects s on s.id = t.subject_id
left join public.exam_phase_sections eps on eps.id = c.section_id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
  and c.exam_phase_id = '6566d50e-7f1c-4410-aa36-8142dfe9a79b'
order by c.exam_priority_score desc;


-- ─── §5  Where does max_tasks = 2 come from? ──────────────────────────────
-- planner.py:1548-1562 — preference row wins; else persona study_policy;
-- else the _DEFAULT_MAX_TASKS of 4.
select
  'user_study_plan_preferences'                        as source,
  p.focus,
  p.max_tasks_per_day::text                            as max_tasks_per_day,
  p.preferred_task_size,
  coalesce(array_length(p.muted_topic_ids, 1), 0)::text  as muted_count,
  coalesce(array_length(p.pinned_topic_ids, 1), 0)::text as pinned_count
from public.user_study_plan_preferences p
where p.user_id = '664d94c6-0000-0000-0000-000000000000'  -- fill in
union all
select
  'aspirant_persona_snapshots.study_policy',
  null,
  s.study_policy ->> 'max_tasks_per_day',
  s.study_policy ->> 'preferred_task_size',
  null,
  null
from public.aspirant_persona_snapshots s
where s.user_id = '664d94c6-0000-0000-0000-000000000000'  -- fill in
order by 1;


-- ─── §6  How much would elective scoping actually exclude? ────────────────
-- Reproduces planner.py:579-588 exactly: keep a row when section_id is NULL
-- OR its section is non-elective OR its (group, subject) is the user's choice.
-- Expected result: excluded = 0 — which is the point (defect D8).
with in_scope as (
  select eps.id
  from public.exam_phase_sections eps
  join public.exam_phases ph on ph.id = eps.exam_phase_id
  where ph.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and (
      eps.selection_kind is distinct from 'elective'
      or exists (
        select 1
        from public.user_exam_electives ue
        where ue.user_id = '664d94c6-0000-0000-0000-000000000000'  -- fill in
          and ue.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
          and ue.elective_group = eps.elective_group
          and eps.subject_id = any (ue.subject_ids)
      )
    )
)
select
  count(*) filter (where c.section_id is null)                      as kept_unclassified,
  count(*) filter (where c.section_id in (select id from in_scope)) as kept_in_scope,
  count(*) filter (where c.section_id is not null
                     and c.section_id not in (select id from in_scope)) as excluded,
  count(*)                                                          as total_locked
from public.exam_topic_coverage c
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked';

-- 6b. The exam's section classification, for the same reason.
select
  ph.phase_slug,
  eps.section_label,
  s.slug                                               as subject_slug,
  s.subject_group,
  eps.selection_kind,
  eps.elective_group,
  (select count(*) from public.exam_topic_coverage c
    where c.section_id = eps.id and c.reviewer_status = 'locked') as locked_coverage_rows
from public.exam_phase_sections eps
join public.exam_phases ph on ph.id = eps.exam_phase_id
left join public.subjects s on s.id = eps.subject_id
where ph.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
order by eps.selection_kind, ph.phase_slug, s.slug;

-- 6c. What the user actually chose.
select ue.elective_group, ue.choice_key, ue.subject_ids, ue.chosen_at,
       (select string_agg(s.slug, ', ' order by s.slug)
          from public.subjects s where s.id = any (ue.subject_ids)) as subject_slugs
from public.user_exam_electives ue
where ue.user_id = '664d94c6-0000-0000-0000-000000000000'  -- fill in
  and ue.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2';


-- ─── §7  The two persisted tasks, including why_this_task ─────────────────
select
  tk.id,
  tk.title,
  tk.task_type,
  tk.status,
  tk.scheduled_date,
  tk.priority_score,
  tk.exam_phase_id,
  ph.phase_slug,
  s.slug                                               as subject_slug,
  tk.exam_topic_coverage_id,
  (tk.why_this_task is null)                           as why_is_null,
  (tk.why_this_task = '{}'::jsonb)                     as why_is_empty_object,
  tk.why_this_task
from public.study_tasks tk
left join public.exam_phases ph on ph.id = tk.exam_phase_id
left join public.topics t on t.id = tk.topic_id
left join public.subjects s on s.id = t.subject_id
where tk.plan_id = 'e87f1c91-850f-43ca-9edf-9bae3b2c2140'
order by tk.priority_score desc;
