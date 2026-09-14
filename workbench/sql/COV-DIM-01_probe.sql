-- COV-DIM-01 — live probes. SELECT-ONLY. No INSERT/UPDATE/DELETE/DDL.
-- Written, not run. Numbering matches
-- workbench/investigations/COV-DIM-01_discovery.md § "Requires live data".
-- Run block by block; each is independent.
--
--   exam   upsc-cse   5466e62f-7382-4a38-ba96-2fe5fbfeaba2
--   phase  Mains?     f42ffb84-…   <- per the COV-DIM-01 brief; complete the uuid
--   phase  Mains?     626ec667-4bbf-4420-8715-48c5b83e0d11   <- per PLAN-POOL-01
--   phase  Prelims    6566d50e-7f1c-4410-aa36-8142dfe9a79b


-- ─── §1  Is topic -> section a function on the Mains phase? ───────────────
-- Q3. exam_phase_sections is unique on (exam_phase_id, subject_id,
-- section_label), so a subject MAY own several sections in one phase. A
-- coverage row knows only its topic, and topics.subject_id is single-valued —
-- so the mapping is deterministic only where sections_per_subject = 1.
-- HEALTHY: every row reads sections_per_subject = 1. Any row above 1 means the
-- section dimension cannot be derived from topic_id alone for that subject.
select
  ph.phase_slug,
  s.slug                                   as subject_slug,
  s.subject_group,
  count(*)                                 as sections_per_subject,
  string_agg(eps.section_label, ' | ' order by eps.section_label) as labels,
  string_agg(distinct eps.selection_kind, ',')                    as selection_kinds
from public.exam_phase_sections eps
join public.exam_phases ph on ph.id = eps.exam_phase_id
left join public.subjects s on s.id = eps.subject_id
where ph.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
group by ph.phase_slug, s.slug, s.subject_group
order by sections_per_subject desc, ph.phase_slug, s.slug;

-- 1b. The same question asked only of the subjects that actually carry locked
-- coverage — the ones a backfill would have to resolve.
-- HEALTHY: max_sections_for_its_subject = 1 on every row.
select
  ph.phase_slug,
  s.slug                                   as subject_slug,
  count(distinct c.topic_id)               as locked_topics,
  (select count(*)
     from public.exam_phase_sections e2
    where e2.exam_phase_id = c.exam_phase_id
      and e2.subject_id    = t.subject_id)  as max_sections_for_its_subject
from public.exam_topic_coverage c
join public.topics t   on t.id = c.topic_id
left join public.subjects s on s.id = t.subject_id
left join public.exam_phases ph on ph.id = c.exam_phase_id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
group by ph.phase_slug, s.slug, c.exam_phase_id, t.subject_id
order by locked_topics desc;


-- ─── §2  Which phase holds the 1,497 Mains rows? ──────────────────────────
-- Correction 3. The COV-DIM-01 brief names f42ffb84-…; PLAN-POOL-01 and
-- workbench/scripts/lock_coverage.py:34 name 626ec667-…. Both cannot hold the
-- same rows unless the corpus was re-scoped.
-- HEALTHY: one phase carries ~1,497 locked rows and the other carries none, or
-- does not exist.
select
  c.exam_phase_id,
  ph.phase_slug,
  ph.phase_name,
  ph.exam_cycle_id,
  case when ph.exam_cycle_id is null then 'TEMPLATE (never a plan target)'
       else 'cycle-attached' end            as targetability,
  count(*)                                  as locked_rows,
  count(*) filter (where c.section_id is not null) as with_section,
  min(c.exam_priority_score)                as min_score,
  round(avg(c.exam_priority_score), 2)      as avg_score,
  max(c.exam_priority_score)                as max_score
from public.exam_topic_coverage c
left join public.exam_phases ph on ph.id = c.exam_phase_id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
group by c.exam_phase_id, ph.phase_slug, ph.phase_name, ph.exam_cycle_id
order by locked_rows desc;


-- ─── §3  Which writer produced the 13 sectioned Prelims rows? ─────────────
-- Q2 / D19. Only the CMS can set section_id: the single-create endpoint
-- (validated, admin_exam_intel_cms.py:2674-2679) or the bulk import
-- (unvalidated, :4560-4568). Their audit actions differ.
-- HEALTHY: rows trace to 'exam_intel.cms.coverage.create'. A
-- '…coverage.bulk_create' provenance means they went in unvalidated.
select
  a.action,
  count(*)          as rows,
  min(a.created_at) as first_seen,
  max(a.created_at) as last_seen
from public.admin_audit_logs a
where a.entity_type = 'exam_topic_coverage'
  and a.entity_id in (
    select c.id::text
    from public.exam_topic_coverage c
    where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
      and c.reviewer_status = 'locked'
      and c.section_id is not null
  )
group by a.action
order by rows desc;

-- 3b. Fallback when the audit trail does not resolve them: the rows' own
-- provenance columns.
select
  c.source_basis,
  c.source_kind,
  c.model_version,
  count(*)          as rows,
  min(c.created_at) as first_created,
  max(c.created_at) as last_created
from public.exam_topic_coverage c
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
  and c.section_id is not null
group by c.source_basis, c.source_kind, c.model_version
order by rows desc;


-- ─── §4  Has the unvalidated bulk-import path already been exercised? ─────
-- D19. The single-create endpoint requires section.exam_phase_id to equal the
-- row's exam_phase_id; bulk import enforces nothing.
-- HEALTHY: zero rows.
select
  c.id            as coverage_id,
  c.exam_phase_id as row_phase,
  eps.exam_phase_id as section_phase,
  c.source_basis,
  c.reviewer_status
from public.exam_topic_coverage c
join public.exam_phase_sections eps on eps.id = c.section_id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and (c.exam_phase_id is distinct from eps.exam_phase_id);


-- ─── §5  Does any topic hold more than one locked coverage row? ───────────
-- D20 — the suspected cause of duplicate palette entries. The unique indexes
-- key on (exam, cycle, phase, topic), so an exam-wide row (phase NULL) and a
-- phase-scoped row for the same topic are both legal, and
-- _load_locked_coverage_checked emits one item per ROW with no dedupe by topic.
-- HEALTHY: zero rows.
select
  c.topic_id,
  t.name                                              as topic,
  count(*)                                            as locked_rows,
  string_agg(coalesce(c.exam_phase_id::text, 'EXAM-WIDE'), ', ') as phases,
  string_agg(c.source_basis, ', ')                    as bases,
  string_agg(c.exam_priority_score::text, ', ')       as scores
from public.exam_topic_coverage c
left join public.topics t on t.id = c.topic_id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
group by c.topic_id, t.name
having count(*) > 1
order by locked_rows desc, topic;


-- ─── §6  Score distribution by source_basis and phase ─────────────────────
-- Q4. Confirms the ceiling claim against live data: the v2.0 model's 40-point
-- coverage term is self-referential (starts at 0) and its 50-point frequency
-- term is a cohort share, so derived rows should sit far below authored ones.
-- HEALTHY (i.e. defect still present, as the brief states): max(evidence_derived)
-- < min(official_syllabus). A derived row above an authored one would mean the
-- ceiling analysis is wrong and should be reported.
select
  ph.phase_slug,
  c.source_basis,
  count(*)                              as rows,
  min(c.exam_priority_score)            as min_score,
  round(avg(c.exam_priority_score), 2)  as avg_score,
  max(c.exam_priority_score)            as max_score,
  count(*) filter (where c.is_high_yield)       as high_yield_rows,
  round(avg(c.confidence_score), 3)             as avg_confidence
from public.exam_topic_coverage c
left join public.exam_phases ph on ph.id = c.exam_phase_id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
group by ph.phase_slug, c.source_basis
order by ph.phase_slug, c.source_basis;

-- 6b. Per-subject maxima on the derived side — the optionals' ceiling versus
-- the GS one. HEALTHY: consistent with the brief (optionals max ~12-15, GS
-- reaching ~36); a wildly different shape means the corpus moved.
select
  s.slug                                as subject_slug,
  s.subject_group,
  count(*)                              as locked_rows,
  round(avg(c.exam_priority_score), 2)  as avg_score,
  max(c.exam_priority_score)            as max_score
from public.exam_topic_coverage c
join public.topics t on t.id = c.topic_id
left join public.subjects s on s.id = t.subject_id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
  and c.source_basis = 'evidence_derived'
group by s.slug, s.subject_group
order by max_score desc;


-- ─── §7  Is predictability_band actually populated? ───────────────────────
-- D22. The column exists (migration 288) and the derivation projects it, but
-- the planner's loader does not select it. Before that is worth changing, the
-- data has to be there.
-- HEALTHY: a band on most rows that have year evidence; NULL only on
-- syllabus-only rows.
select
  c.source_basis,
  coalesce(c.predictability_band, '(null)') as band,
  count(*)                                  as rows,
  round(min(c.predictability), 4)           as min_pred,
  round(max(c.predictability), 4)           as max_pred
from public.exam_topic_coverage c
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
group by c.source_basis, c.predictability_band
order by c.source_basis, rows desc;

-- 7b. Specifically the twelve optional subjects — the palette's problem case.
select
  s.slug                                    as subject_slug,
  count(*)                                  as locked_rows,
  count(*) filter (where c.predictability_band is not null) as with_band,
  count(*) filter (where c.predictability_band is null)     as without_band
from public.exam_topic_coverage c
join public.topics t on t.id = c.topic_id
join public.subjects s on s.id = t.subject_id
where c.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
  and c.reviewer_status = 'locked'
  and s.subject_group = 'upsc-optional'
group by s.slug
order by s.slug;
