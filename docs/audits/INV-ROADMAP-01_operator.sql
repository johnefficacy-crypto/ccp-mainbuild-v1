-- INV-ROADMAP-01 — read-only operator queries for the aspirant-roadmap investigation.
-- HEAD: f43e6d1383bf5a2ab523f060d7134b7ddc0c4d48   Date: 2026-09-22 (re-verified twice)
--
-- Every statement is SELECT-only and schema-qualified. Run in Supabase Studio.
-- Replace :exam_slug / :user_id before running. Nothing here mutates data.
--
-- Each block states the capability (C1–C10) or hypothesis (H1–H10) it answers.

-- ─────────────────────────────────────────────────────────────────────────────
-- Q1 (C3, C4, C6) — Does the target exam have ANY locked coverage? Every Study OS
-- surface derives its topic universe from locked exam_topic_coverage; zero locked
-- rows makes /subjects, /topics and the report card structurally empty.
select e.slug,
       c.reviewer_status,
       count(*) as rows,
       count(*) filter (where c.is_high_yield) as high_yield_rows,
       count(distinct c.exam_phase_id) as distinct_phases,
       count(distinct c.exam_cycle_id) as distinct_cycles
from public.exam_topic_coverage c
join public.exams e on e.id = c.exam_id
where e.slug = :exam_slug
group by e.slug, c.reviewer_status
order by c.reviewer_status;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q2 (C4, H9) — The syllabus denominator. Topic counts by level per subject for
-- the exam's subjects. H9 claims 456 verified UPSC Mains GS topics = 30 macro
-- (level='topic') + 426 microtopic. Confirm or refute against topics itself.
select s.name as subject_name, t.level, count(*) as topics,
       count(*) filter (where t.is_active is false) as inactive
from public.topics t
join public.subjects s on s.id = t.subject_id
group by s.name, t.level
order by s.name, t.level;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q3 (C4, C6, H9) — The "18 orphaned pre-split topic rows" claim. A microtopic
-- whose parent is missing, or whose parent belongs to a DIFFERENT subject, is an
-- orphan. subjects.py::subject_topic_tree keeps such rows at the top level, so
-- they WOULD render to an aspirant if they carry a live subject_id.
select t.id, t.name, t.level, t.is_active,
       t.subject_id, t.parent_topic_id,
       p.subject_id as parent_subject_id,
       case when t.parent_topic_id is null then 'no_parent'
            when p.id is null then 'parent_missing'
            when p.subject_id <> t.subject_id then 'parent_other_subject'
       end as orphan_kind
from public.topics t
left join public.topics p on p.id = t.parent_topic_id
where t.level = 'microtopic'
  and (t.parent_topic_id is null or p.id is null or p.subject_id <> t.subject_id)
order by orphan_kind, t.name;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q4 (C6) — Are there any level='concept' rows? subjects.py::subject_topic_tree
-- filters in_('level', ['topic','microtopic']), so concept rows are invisible to
-- the aspirant tree. This says whether that exclusion currently hides anything.
select s.name as subject_name, count(*) as concept_rows
from public.topics t
join public.subjects s on s.id = t.subject_id
where t.level = 'concept'
group by s.name
order by concept_rows desc;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q5 (C2, H1) — Is per-user mastery actually populated, and on what scale?
-- H1 claims a continuous 0–100 mastery_score with no state enum.
select count(*) as rows,
       count(distinct user_id) as users,
       count(distinct topic_id) as topics,
       min(mastery_score) as min_score,
       max(mastery_score) as max_score,
       count(*) filter (where evidence_count = 0) as zero_evidence_rows
from public.user_topic_mastery;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q6 (C8) — Cross-exam leakage exposure. planner.py::_load_user_signals_ex reads
-- user_topic_mastery with NO exam filter and only prefers an exam-scoped row when
-- one already exists for that topic; a row belonging to ANOTHER exam is used as a
-- fallback. This counts how many rows are global vs exam-scoped per user.
select user_id,
       count(*) filter (where exam_id is null) as global_rows,
       count(*) filter (where exam_id is not null) as exam_scoped_rows,
       count(distinct exam_id) as distinct_exams
from public.user_topic_mastery
group by user_id
having count(distinct exam_id) > 1 or count(*) filter (where exam_id is null) > 0
order by distinct_exams desc nulls last
limit 50;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q7 (C6) — The subjects.py::list_subjects denominator problem. `progress` is the
-- average mastery over ONLY those locked topics that have a mastery row; topics
-- with no row are excluded from the average, not counted as 0. This measures how
-- thin that denominator is per subject for one user.
select s.name as subject_name,
       count(distinct c.topic_id) as locked_topics,
       count(distinct m.topic_id) as topics_with_mastery_row,
       round(100.0 * count(distinct m.topic_id)
             / nullif(count(distinct c.topic_id), 0), 1) as pct_of_subject_measured
from public.exam_topic_coverage c
join public.exams e on e.id = c.exam_id
join public.topics t on t.id = c.topic_id
join public.subjects s on s.id = t.subject_id
left join public.user_topic_mastery m
       on m.topic_id = c.topic_id and m.user_id = :user_id
where e.slug = :exam_slug
  and c.reviewer_status = 'locked'
group by s.name
order by pct_of_subject_measured nulls first;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q8 (C5) — Is the revision signal populated? next_revision_at is written by
-- mastery.py from the _REVISION_DAYS band table; revision_items is the separate
-- SRS surface behind /app/study/revision.
select 'user_topic_mastery.next_revision_at' as source,
       count(*) as rows,
       count(next_revision_at) as with_next_revision,
       count(*) filter (where next_revision_at <= now()) as overdue,
       count(last_practiced_at) as with_last_practiced
from public.user_topic_mastery
union all
select 'revision_items' as source,
       count(*) as rows,
       count(*) filter (where status = 'scheduled') as with_next_revision,
       count(*) filter (where status = 'scheduled' and scheduled_for <= current_date) as overdue,
       count(*) filter (where topic_id is not null) as with_last_practiced
from public.revision_items;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q9 (C7) — Can a mastery timeline be rebuilt? These are the only append-only
-- per-topic histories. Empty tables mean no journey can be reconstructed at all.
select 'user_topic_mastery_audit' as source, count(*) as rows,
       min(at) as earliest, max(at) as latest
from public.user_topic_mastery_audit
union all
select 'user_topic_mastery_evidence', count(*), min(observed_at), max(observed_at)
from public.user_topic_mastery_evidence
union all
select 'study_adaptation_events', count(*), min(created_at), max(created_at)
from public.study_adaptation_events
union all
select 'study_plan_versions', count(*), min(created_at), max(created_at)
from public.study_plan_versions
union all
select 'study_report_cards', count(*), min(computed_at), max(computed_at)
from public.study_report_cards;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q10 (C1) — Confirm the two report endpoints read objects that do not exist.
-- /api/study/reports/subject-mastery reads `subject_mastery_snapshots`, which is
-- in no migration; /api/study/reports/topic-recovery selects topic_name,
-- created_at and mastery_db from user_topic_mastery_audit, which has none of them.
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('subject_mastery_snapshots', 'user_topic_mastery_audit');

select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'user_topic_mastery_audit'
order by ordinal_position;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q11 (C9) — Is there any pace data to drive an "on track / behind" signal?
-- There is no per-topic hour estimate (H6); the only planned time is per task.
select count(*) as tasks,
       count(planned_minutes) as with_planned_minutes,
       count(duration_mins) as with_duration_mins,
       count(topic_id) as with_topic_id,
       count(*) filter (where status = 'completed') as completed,
       count(*) filter (where status = 'carried_forward') as carried_forward
from public.study_tasks
where user_id = :user_id;

select count(*) as prefs_rows,
       count(max_tasks_per_day) as with_max_tasks,
       count(preferred_task_size) as with_task_size
from public.user_study_plan_preferences
where user_id = :user_id;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q12 (C8) — How many users target more than one exam? user_exam_goals is the
-- multi-exam weighting table; aspirant_preferences.target_exams is the slug list.
select count(*) as users_with_multiple_active_goals
from (
  select user_id
  from public.user_exam_goals
  where status = 'active'
  group by user_id
  having count(*) > 1
) x;

select count(*) as users_with_multiple_target_exam_slugs
from public.aspirant_preferences
where array_length(target_exams, 1) > 1;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q13 (C1, C3) — The report card's high-yield denominator. _build_high_yield_coverage
-- counts ONLY locked high-yield coverage rows, so this is the entire universe the
-- one aspirant-visible "covered / total" number is measured against.
select e.slug,
       count(*) filter (where c.reviewer_status = 'locked') as locked_rows,
       count(*) filter (where c.reviewer_status = 'locked' and c.is_high_yield) as locked_high_yield
from public.exam_topic_coverage c
join public.exams e on e.id = c.exam_id
group by e.slug
order by locked_high_yield desc;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q14 (C6) — Is there a locked prerequisite graph to sequence a roadmap with?
-- planner.py::_load_prerequisites consumes only reviewer_status='locked' edges.
select reviewer_status, relation_type, count(*) as edges
from public.topic_prerequisites
group by reviewer_status, relation_type
order by reviewer_status, relation_type;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q15 (C4, C8) — Is elective scoping populated? Every learner-facing coverage
-- read now goes through planner.load_scoped_coverage, which filters on the
-- section's selection_kind (migration 287) and the user's chosen optional. An
-- empty user_exam_electives means the scoping is inert in practice and the new
-- palette shows every optional paper to everyone.
select selection_kind, count(*) as sections,
       count(*) filter (where elective_group is not null) as with_group
from public.exam_sections
group by selection_kind
order by selection_kind;

select count(*) as elective_choices,
       count(distinct user_id) as users_who_chose
from public.user_exam_electives;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q16 (C6) — Is the predictability axis populated? It is the only signal on a
-- coverage row that is comparable across subject-papers, and the palette renders
-- nothing where it is null (PaletteCard.jsx), so an unpopulated column makes the
-- new axis invisible rather than wrong.
select e.slug,
       count(*) filter (where c.reviewer_status = 'locked') as locked_rows,
       count(c.predictability_band) filter (where c.reviewer_status = 'locked')
         as with_predictability_band,
       count(distinct c.predictability_band) as distinct_bands,
       count(distinct c.source_basis) as distinct_source_bases
from public.exam_topic_coverage c
join public.exams e on e.id = c.exam_id
group by e.slug
order by locked_rows desc;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q17 (C4, K17) — How much of the palette's "unplaced" set is actually untouched?
-- planner_board.list_candidates calls a topic placed only when it has a task in
-- the 7-day window, so a topic mastered months ago reads the same as one never
-- opened. This splits the unplaced set by whether the user has any mastery row.
select case
         when m.topic_id is null then 'no_mastery_row'
         when m.mastery_score >= 75 then 'mastery_75_plus'
         when m.mastery_score > 0 then 'mastery_partial'
         else 'mastery_zero'
       end as bucket,
       count(*) as topics
from public.exam_topic_coverage c
join public.exams e on e.id = c.exam_id
left join public.user_topic_mastery m
       on m.topic_id = c.topic_id and m.user_id = :user_id
where e.slug = :exam_slug
  and c.reviewer_status = 'locked'
group by bucket
order by topics desc;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q18 (C2, K5) — Do board placements and task origin actually carry? Migration
-- 289 added study_tasks.source ('planner'|'user') and 290 added day_ordinal.
select source, count(*) as tasks,
       count(day_ordinal) as arranged,
       count(topic_id) as with_topic_id,
       count(*) filter (where status = 'completed') as completed
from public.study_tasks
where user_id = :user_id
group by source
order by source;
