-- PLAN-LOOP-01 — read-only probe SQL
--
-- Answers the open questions in
-- workbench/investigations/PLAN-LOOP-01_discovery.md § "Requires live data".
--
-- CONTRACT: this file is SELECT-only. It contains no write statements and no
-- DDL of any kind. It is written, not run — this investigation asserted
-- nothing about live row counts.
--
-- Run against a read replica or with a read-only role. Section numbers match
-- the report's numbered list. Column names were verified against the
-- migrations that define each table; note the timestamp columns are NOT
-- uniformly named (`at`, `decided_at`, `observed_at`, `created_at`).


-- ─────────────────────────────────────────────────────────────────────────
-- §1. Is the mock-engine mastery writer actually live?
--
-- Q: Has apply_mock_mastery_delta (migration 145) ever fired in production?
--    The RPC writes user_topic_mastery_audit in the same transaction as the
--    mastery row, so audit presence is proof the FF reached 'live' for at
--    least one allowlisted user.
--    Timestamp column is `at` (migration 144:25), not created_at.
--
-- Healthy result if the loop is intended to be ON:
--    total_audit_rows > 0, distinct_users matching the size of
--    FF_MOCK_MASTERY_LIVE_USER_IDS, and last_applied_at recent (hours-to-days).
-- Expected result if the FF is still off/shadow (what the code defaults to):
--    a single row of zeros and NULLs.
-- ─────────────────────────────────────────────────────────────────────────
select
  count(*)                   as total_audit_rows,
  count(distinct user_id)    as distinct_users,
  count(distinct attempt_id) as distinct_attempts,
  count(distinct reason)     as distinct_reasons,
  min(at)                    as first_applied_at,
  max(at)                    as last_applied_at
from public.user_topic_mastery_audit;


-- ─────────────────────────────────────────────────────────────────────────
-- §2. How many mastery rows exist, and which writer produced them?
--
-- Q: W1 (mastery.py recompute_topic_mastery) always populates accuracy_score,
--    confidence_score and evidence_count. W2 (the delta RPC) writes only
--    (id, user_id, topic_id, mastery_score) and leaves the rest at their
--    column defaults — evidence_count and confidence_score are NOT NULL
--    DEFAULT 0 (migration 033:47 and 033:52), so 0 is the W2 signature, not NULL.
--    The split tells us how much of the planner's weakness signal is
--    self-reported manual-log data vs. platform-scored attempts.
--
-- Healthy result: both buckets non-zero, with w2_shaped_rows growing over time.
-- A w2_shaped_rows of 0 corroborates §1 — the mock engine never wrote live.
-- A w1_shaped_rows of 0 means no manual log was ever reviewed with
-- topic_breakdowns, so the planner's only mastery came from the mock engine.
-- ─────────────────────────────────────────────────────────────────────────
select
  count(*)                                                as total_rows,
  count(distinct user_id)                                 as distinct_users,
  count(*) filter (where evidence_count > 0)              as w1_shaped_rows,
  count(*) filter (where evidence_count = 0
                     and accuracy_score is null)          as w2_shaped_rows,
  count(*) filter (where exam_id is null
                     and exam_phase_id is null)           as globally_scoped_rows,
  count(*) filter (where exam_id is not null)             as exam_scoped_rows,
  round(avg(mastery_score), 2)                            as avg_mastery,
  min(mastery_score)                                      as min_mastery,
  max(mastery_score)                                      as max_mastery,
  max(updated_at)                                         as last_write
from public.user_topic_mastery;


-- ─────────────────────────────────────────────────────────────────────────
-- §3. Does defect D1's dual-row condition occur in practice?
--
-- Q: The delta RPC hard-scopes to (exam_id IS NULL AND exam_phase_id IS NULL);
--    recompute_topic_mastery scopes to the mock's own exam/phase. Migration
--    033:59-65 defines TWO partial unique indexes — one for the exam-scoped
--    shape, one for the global shape — so both rows can legitimately coexist
--    for the same (user, topic). The planner then silently prefers the
--    exam-scoped one (planner.py:426-435), hiding every accumulated mock delta.
--
-- Healthy result: ZERO rows returned. Any row returned is a live instance of
-- D1 — that user's mock-derived mastery for that topic is invisible to the
-- planner.
-- ─────────────────────────────────────────────────────────────────────────
select
  m.user_id,
  m.topic_id,
  count(*)                                                    as row_count,
  count(*) filter (where m.exam_id is null)                   as global_rows,
  count(*) filter (where m.exam_id is not null)               as exam_scoped_rows,
  max(m.mastery_score) filter (where m.exam_id is null)       as global_mastery,
  max(m.mastery_score) filter (where m.exam_id is not null)   as exam_scoped_mastery
from public.user_topic_mastery m
group by m.user_id, m.topic_id
having count(*) filter (where m.exam_id is null) > 0
   and count(*) filter (where m.exam_id is not null) > 0
order by row_count desc
limit 200;


-- ─────────────────────────────────────────────────────────────────────────
-- §4. Has defect D1's clobber actually fired?
--
-- Q: When a manual-log mock has a NULL exam_id, W1 and W2 target the SAME row,
--    and W1 overwrites mastery_score with raw accuracy — discarding the
--    capped, trust-weighted deltas W2 accumulated. The audit trail still
--    claims they were applied.
--
-- Compares each globally-scoped (user, topic)'s most recent audited
-- after_mastery_db against the current live mastery_score.
--
-- Healthy result: zero rows — every audited value still matches the live one.
-- Any row returned is a mastery value that was overwritten after the delta
-- was audited as applied, i.e. the audit trail and the live value disagree.
-- ─────────────────────────────────────────────────────────────────────────
with latest_audit as (
  select distinct on (a.user_id, a.topic_id)
    a.user_id,
    a.topic_id,
    a.after_mastery_db,
    a.at as audited_at
  from public.user_topic_mastery_audit a
  order by a.user_id, a.topic_id, a.at desc
)
select
  la.user_id,
  la.topic_id,
  la.after_mastery_db                             as audit_says,
  m.mastery_score                                 as live_value,
  round(m.mastery_score - la.after_mastery_db, 2) as drift,
  la.audited_at,
  m.updated_at                                    as mastery_updated_at
from latest_audit la
join public.user_topic_mastery m
  on  m.user_id  = la.user_id
  and m.topic_id = la.topic_id
  and m.exam_id is null
  and m.exam_phase_id is null
where abs(m.mastery_score - la.after_mastery_db) > 0.01
order by abs(m.mastery_score - la.after_mastery_db) desc
limit 200;


-- ─────────────────────────────────────────────────────────────────────────
-- §5. How much derived mastery signal is stranded in shadow?
--
-- Q: At flag_state != 'live' the MasteryWriter still derives a full per-topic
--    delta and records it in mock_mastery_shadow — then discards it. Same for
--    trap drills. These counts size the signal the planner is not seeing.
--    Timestamp column on both tables is `decided_at`
--    (migrations 144:10 and 232:45), not created_at.
--
-- Healthy result if the loop is meant to be live: shadow rows small and stale
-- (a brief dark-launch window), 'live' rows dominating mock_mastery_shadow.
-- Expected result today: shadow rows large and still growing, zero 'live'.
-- trap_drill_mastery_shadow is CHECK-pinned to 'shadow' and can never show
-- anything else.
-- ─────────────────────────────────────────────────────────────────────────
select
  'mock_mastery_shadow'      as table_name,
  flag_state,
  count(*)                   as row_count,
  count(distinct user_id)    as distinct_users,
  count(distinct attempt_id) as distinct_attempts,
  max(decided_at)            as newest_row
from public.mock_mastery_shadow
group by flag_state

union all

select
  'trap_drill_mastery_shadow',
  flag_state,
  count(*),
  count(distinct user_id),
  null,
  max(decided_at)
from public.trap_drill_mastery_shadow
group by flag_state

order by table_name, flag_state;


-- ─────────────────────────────────────────────────────────────────────────
-- §6. Is the writing-practice evidence table accumulating rows nobody reads?
--
-- Q: Defect D2 — migration 205:825 declares
--    effective_user_topic_mastery_evidence "the ONLY planner/level source",
--    but no Python call site reads it. If the table has real volume, the
--    writing loop is producing a signal that terminates in storage.
--    Timestamp column is `observed_at` (migration 205:517), not created_at.
--
-- Healthy result if a consumer existed: evidence rows tracking writing session
-- volume, effective_rows < total_evidence_rows (supersession working), and
-- the same users carrying mastery rows. A large effective_rows next to a
-- mastery_rows_for_those_users of 0 is the defect, stated numerically.
-- ─────────────────────────────────────────────────────────────────────────
select
  (select count(*)
     from public.user_topic_mastery_evidence)                    as total_evidence_rows,
  (select count(distinct user_id)
     from public.user_topic_mastery_evidence)                    as distinct_users,
  (select count(*)
     from public.effective_user_topic_mastery_evidence)          as effective_rows,
  (select max(observed_at)
     from public.user_topic_mastery_evidence)                    as newest_evidence_row,
  (select count(*)
     from public.user_topic_mastery
    where user_id in (select user_id
                        from public.user_topic_mastery_evidence)) as mastery_rows_for_those_users;


-- ─────────────────────────────────────────────────────────────────────────
-- §7. Real end-to-end latency from mock submit to plan refresh.
--
-- Q: Q5 predicts a bimodal distribution — minutes for the manual-log
--    'mock_reviewed' regen path (canonical.py:2366), and up to ~17 hours for
--    everything else, which waits for the 03:00 UTC sweep.
--
-- For each submitted attempt, finds the first study_plan_versions row created
-- for that user afterwards.
--
-- Healthy result for a responsive loop: median hours_to_plan well under 1.
-- Expected result: a cluster near 0 (manual-log path) and a long tail out to
-- ~17-24h (nightly cron), with NULLs where no regen ever followed.
-- ─────────────────────────────────────────────────────────────────────────
with submitted as (
  select
    a.id      as attempt_id,
    a.user_id,
    a.submitted_at
  from public.mock_attempts a
  where a.status = 'submitted'
    and a.submitted_at is not null
    and a.submitted_at > now() - interval '90 days'
),
paired as (
  select
    s.attempt_id,
    s.user_id,
    s.submitted_at,
    (
      select min(v.created_at)
      from public.study_plan_versions v
      join public.study_plans p on p.id = v.plan_id
      where p.user_id = s.user_id
        and v.created_at > s.submitted_at
    ) as first_plan_version_after
  from submitted s
)
select
  attempt_id,
  user_id,
  submitted_at,
  first_plan_version_after,
  round(
    extract(epoch from (first_plan_version_after - submitted_at)) / 3600.0
  , 2) as hours_to_plan
from paired
order by submitted_at desc
limit 500;


-- ─────────────────────────────────────────────────────────────────────────
-- §8. Lower-bound indicator for defect D4 (regen discards user edits).
--
-- Q: _persist clears every study_tasks row for today whose status is still
--    'planned' (planner.py:1059-1069) before rebuilding the day. Rows already
--    gone cannot be counted, so this measures the standing population at
--    risk: tasks still 'planned' whose scheduled_date has passed, per user.
--
-- Healthy result: low counts — users complete, start, or explicitly skip their
-- tasks. High counts mean a large body of untouched planned tasks is being
-- silently rebuilt nightly, and any user edit among them is lost.
-- Note: an indicator, not proof. Proving D4 needs instrumentation on the
-- planner's cleanup step, not a query.
-- ─────────────────────────────────────────────────────────────────────────
select
  t.user_id,
  count(*)                         as planned_past_tasks,
  min(t.scheduled_date)            as oldest_planned_date,
  max(t.scheduled_date)            as newest_planned_date,
  count(distinct t.scheduled_date) as distinct_days
from public.study_tasks t
where t.status = 'planned'
  and t.scheduled_date < current_date
group by t.user_id
order by planned_past_tasks desc
limit 200;


-- ─────────────────────────────────────────────────────────────────────────
-- §9. Is user_signal_events genuinely single-purpose? (preflight P3)
--
-- Q: The table is schema-generic and its own comment invites
--    "onboarding/study/focus/mock/eligibility" emitters, but code shows one
--    writer (persona_questions/events.py:55) feeding persona recompute only.
--    If production carries only persona event_types, it is effectively a
--    persona-private table and a planner ledger would be new work; if other
--    types already appear, it is reusable as the cross-tool substrate.
--
-- Healthy result either way — this is a decision input, not a health check.
-- A single event_type family confirms the code reading.
-- ─────────────────────────────────────────────────────────────────────────
select
  event_type,
  count(*)                                     as row_count,
  count(distinct user_id)                      as distinct_users,
  count(*) filter (where processed_at is null) as unprocessed_rows,
  min(created_at)                              as first_seen,
  max(created_at)                              as last_seen
from public.user_signal_events
group by event_type
order by row_count desc;


-- ─────────────────────────────────────────────────────────────────────────
-- §9b. Companion: which regen paths actually fire.
--
-- Q: study_adaptation_events is the planner's OUTPUT audit (not an input).
--    Its event_type distribution shows which regen paths run in practice.
--
-- Healthy result for an event-driven loop: 'mock_reviewed' a meaningful
-- share. Expected result: 'manual_regeneration' dominating, because that is
-- the event_type the 03:00 UTC sweep passes (regen.py:189).
-- ─────────────────────────────────────────────────────────────────────────
select
  event_type,
  trigger_source,
  count(*)                as row_count,
  count(distinct user_id) as distinct_users,
  max(created_at)         as last_seen
from public.study_adaptation_events
group by event_type, trigger_source
order by row_count desc;
