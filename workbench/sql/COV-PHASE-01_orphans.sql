-- COV-PHASE-01 — the duplicated Mains corpus and the 180 orphan topics.
--
-- Read-only except where marked. Run §1-§4 before the consolidation runbook,
-- §5-§6 after it. Substitute the exam id; the phase ids are resolved by §1 and
-- should not be pasted from an earlier brief — the corpus has moved once.
--
--   exam: 5466e62f-7382-4a38-ba96-2fe5fbfeaba2  (upsc-cse)

-- ── §1 phase inventory: which Mains phase is plannable ────────────────────
-- A phase with exam_cycle_id IS NULL is a TEMPLATE: exam_target_window can
-- never target it, so a plan can never be built from its coverage.
select p.id                      as exam_phase_id,
       p.phase_slug,
       p.exam_cycle_id,
       case when p.exam_cycle_id is null then 'template' else 'cycle-attached' end
                                 as kind,
       count(c.id) filter (where c.reviewer_status = 'locked') as locked_rows
from exam_phases p
left join exam_topic_coverage c on c.exam_phase_id = p.id
where p.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
group by p.id, p.phase_slug, p.exam_cycle_id
order by p.phase_slug, kind;

-- ── §2 the orphans: locked coverage on the template, none on the cycle ────
-- Expected before consolidation: 180 rows.
with template as (
  select c.topic_id
  from exam_topic_coverage c
  join exam_phases p on p.id = c.exam_phase_id
  where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and c.reviewer_status = 'locked'
    and p.exam_cycle_id is null
),
cycle as (
  select c.topic_id
  from exam_topic_coverage c
  join exam_phases p on p.id = c.exam_phase_id
  where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and c.reviewer_status = 'locked'
    and p.exam_cycle_id is not null
)
select count(*) as orphan_topics from (
  select topic_id from template except select topic_id from cycle
) o;

-- §2b the orphans themselves, by subject — this is the list an operator
-- checks the re-derive against.
with template as (
  select distinct c.topic_id
  from exam_topic_coverage c
  join exam_phases p on p.id = c.exam_phase_id
  where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and c.reviewer_status = 'locked' and p.exam_cycle_id is null
),
cycle as (
  select distinct c.topic_id
  from exam_topic_coverage c
  join exam_phases p on p.id = c.exam_phase_id
  where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and c.reviewer_status = 'locked' and p.exam_cycle_id is not null
)
select s.name as subject, count(*) as orphan_topics
from (select topic_id from template except select topic_id from cycle) o
join topics t on t.id = o.topic_id
left join subjects s on s.id = t.subject_id
group by s.name
order by orphan_topics desc;

-- ── §3 can the derivation even produce them? ──────────────────────────────
-- The derivation copies evidence numbers verbatim from a LOCKED score
-- snapshot for the target scope (PD-1/PD-6) and snapshots are not inherited
-- across phases by locked_score_snapshots. An orphan with no locked snapshot
-- on the cycle phase needs step 2 of the runbook (compute + lock snapshots)
-- before step 4 can write anything for it.
with template as (
  select distinct c.topic_id
  from exam_topic_coverage c
  join exam_phases p on p.id = c.exam_phase_id
  where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and c.reviewer_status = 'locked' and p.exam_cycle_id is null
),
cycle as (
  select distinct c.topic_id
  from exam_topic_coverage c
  join exam_phases p on p.id = c.exam_phase_id
  where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and c.reviewer_status = 'locked' and p.exam_cycle_id is not null
),
orphans as (select topic_id from template except select topic_id from cycle)
select count(*) filter (where snap.topic_id is not null) as orphans_with_cycle_snapshot,
       count(*) filter (where snap.topic_id is null)     as orphans_without
from orphans o
left join lateral (
  select s.topic_id
  from exam_topic_score_snapshots s
  join exam_phases p on p.id = s.exam_phase_id
  where s.topic_id = o.topic_id
    and s.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and s.reviewer_status = 'locked'
    and p.exam_cycle_id is not null
  limit 1
) snap on true;

-- ── §4 the duplication, by topic ──────────────────────────────────────────
-- Expected before consolidation: ~1,317 topics at 2 locked rows.
select locked_rows, count(*) as topics from (
  select c.topic_id, count(*) as locked_rows
  from exam_topic_coverage c
  where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and c.reviewer_status = 'locked'
  group by c.topic_id
) t
group by locked_rows
order by locked_rows;

-- ── §5 AFTER the runbook: no orphan remains ───────────────────────────────
-- Re-run §2. Healthy: orphan_topics = 0.

-- ── §6 AFTER the runbook: what a learner read now resolves to ─────────────
-- Mirrors _canonical_coverage_rows in planner.py: cycle-attached phase, then
-- exam-wide (phase IS NULL), then template; coverage_id breaks a tie.
-- Healthy: one row per topic, kind = 'cycle-attached' for every topic that has
-- one, and the count equals the distinct locked topic count.
select kind, count(*) as topics from (
  select distinct on (c.topic_id)
         c.topic_id,
         case
           when p.exam_cycle_id is not null then 'cycle-attached'
           when c.exam_phase_id is null     then 'exam-wide'
           else 'template'
         end as kind
  from exam_topic_coverage c
  left join exam_phases p on p.id = c.exam_phase_id
  where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
    and c.reviewer_status = 'locked'
  order by c.topic_id,
           (case when p.exam_cycle_id is not null then 2
                 when c.exam_phase_id is null then 1 else 0 end) desc,
           c.id asc
) canonical
group by kind
order by topics desc;
