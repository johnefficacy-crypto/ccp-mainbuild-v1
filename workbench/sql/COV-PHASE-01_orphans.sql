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
[
  {
    "exam_phase_id": "aec937d6-cbb8-4e7b-8270-8e9585d7ab75",
    "phase_slug": "mains",
    "exam_cycle_id": "881832c8-4b70-4b58-adc1-b9584ede75fe",
    "kind": "cycle-attached",
    "locked_rows": 0
  },
  {
    "exam_phase_id": "f42ffb84-082e-49db-9154-9fd973e8b6e5",
    "phase_slug": "mains",
    "exam_cycle_id": "787b0067-b7c4-4311-a1c0-d488395927b6",
    "kind": "cycle-attached",
    "locked_rows": 1497
  },
  {
    "exam_phase_id": "626ec667-4bbf-4420-8715-48c5b83e0d11",
    "phase_slug": "mains",
    "exam_cycle_id": null,
    "kind": "template",
    "locked_rows": 0
  },
  {
    "exam_phase_id": "7d18bfa9-c79f-45b4-88ff-8a52f5f348d0",
    "phase_slug": "personality-test",
    "exam_cycle_id": "881832c8-4b70-4b58-adc1-b9584ede75fe",
    "kind": "cycle-attached",
    "locked_rows": 0
  },
  {
    "exam_phase_id": "60a04169-8456-448d-b689-88fcf37aa11a",
    "phase_slug": "personality-test",
    "exam_cycle_id": null,
    "kind": "template",
    "locked_rows": 0
  },
  {
    "exam_phase_id": "6566d50e-7f1c-4410-aa36-8142dfe9a79b",
    "phase_slug": "prelims",
    "exam_cycle_id": "787b0067-b7c4-4311-a1c0-d488395927b6",
    "kind": "cycle-attached",
    "locked_rows": 13
  },
  {
    "exam_phase_id": "d58661ee-33c3-4020-9012-38781ae2e601",
    "phase_slug": "prelims",
    "exam_cycle_id": "881832c8-4b70-4b58-adc1-b9584ede75fe",
    "kind": "cycle-attached",
    "locked_rows": 0
  },
  {
    "exam_phase_id": "d813043d-22f5-440b-8992-4a7466191d02",
    "phase_slug": "prelims",
    "exam_cycle_id": "5944895e-4024-4d77-a94e-72b405b42b80",
    "kind": "cycle-attached",
    "locked_rows": 0
  },
  {
    "exam_phase_id": "715de35f-6caa-410a-9805-23bbe561e060",
    "phase_slug": "prelims",
    "exam_cycle_id": null,
    "kind": "template",
    "locked_rows": 0
  },
  {
    "exam_phase_id": "9349fe7b-17b9-49dd-8895-ce447e7e0c7b",
    "phase_slug": "prelims-csat",
    "exam_cycle_id": "5944895e-4024-4d77-a94e-72b405b42b80",
    "kind": "cycle-attached",
    "locked_rows": 0
  },
  {
    "exam_phase_id": "1d6611c7-d749-45e1-9fbd-232d936b005b",
    "phase_slug": "prelims-csat-pyq-archive",
    "exam_cycle_id": null,
    "kind": "template",
    "locked_rows": 0
  }
]

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
[
  {
    "orphan_topics": 0
  }
]
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
No rows.

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
Failed to run sql query: ERROR:  42703: column s.reviewer_status does not exist
LINE 25:     and s.reviewer_status = 'locked'
                 ^

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
[
  {
    "locked_rows": 1,
    "topics": 1510
  }
]
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
[
  {
    "kind": "cycle-attached",
    "topics": 1510
  }
]