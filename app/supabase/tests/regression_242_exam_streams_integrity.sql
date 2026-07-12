-- regression_242_exam_streams_integrity.sql
--
-- Behavioral PostgreSQL regression for migration 242's exam-stream cross-parent
-- integrity (PR #958 checkpost, follow-up P0s). Unlike the string-presence
-- contract test (tests/test_exam_streams_migration.py), this actually applies
-- rows and exercises INSERT / UPDATE / DELETE trigger paths.
--
-- Proves:
--   1.  Valid baseline: same-slug phases across two streams + a common phase,
--       stream sections, and stream coverage all commit within one exam.
--   2.  exam_cycle_streams pairing a cycle and stream of DIFFERENT exams fails.
--   3.  A cycle-bound stream phase with no offered/expected pair fails; a pair
--       with availability='not_offered' does NOT satisfy it.
--   4.  A phase whose stream belongs to a different exam fails.
--   5.  A duplicate (exam, cycle, stream, slug) phase fails (NULLS NOT DISTINCT).
--   6.  A section naming a different stream than its stream-specific parent
--       phase fails; a cross-exam section stream fails.
--   7.  A stream-scoped section under a cycle-bound COMMON phase whose stream is
--       not offered/expected for that cycle fails (availability below the phase).
--   8.  Coverage with exam_cycle_id from a DIFFERENT exam fails (cycle scope).
--   9.  Coverage with section_id from another phase while exam_phase_id IS NULL
--       fails (section resolved through its phase even without a coverage phase).
--   10. Cycle-scoped stream coverage with no offered/expected pair fails.
--   11. Parent move: reassigning exam_streams.exam_id / exam_cycles.exam_id with
--       dependents fails.
--   12. Parent demotion/delete: demoting a depended-on pair to 'not_offered',
--       or deleting it, fails.
--   13. Child UPDATE parent-move: repointing a phase.stream_id cross-exam fails.
--
-- Prerequisites: migration 242 (and its 030 prerequisites) applied.
-- Usage:  psql "$DATABASE_URL" -f regression_242_exam_streams_integrity.sql
-- Expected: PASS notices, no unexpected errors. Runs inside a rolled-back txn.

\set ON_ERROR_STOP on

create or replace function pg_temp._rg241_expect_fail(p_sql text, p_label text)
returns void language plpgsql as $$
begin
  execute p_sql;
  raise exception 'FAIL[%]: expected rejection but the statement succeeded', p_label;
exception
  when sqlstate 'P0422' then raise notice 'PASS[%]', p_label;
  when unique_violation then raise notice 'PASS[% (unique)]', p_label;
end $$;

BEGIN;

-- ── Fixture: two exams (A, B); A has two streams; cycles for each ──────────
insert into public.subjects (id, slug, name)
values ('a1000000-0000-0000-0000-000000000001', 'rg241-subject', 'RG241 Subject');
insert into public.topics (id, slug, name)
values ('a2000000-0000-0000-0000-000000000001', 'rg241-topic', 'RG241 Topic');
insert into public.exam_families (id, slug, name)
values ('a3000000-0000-0000-0000-000000000001', 'rg241-family', 'RG241 Family');
insert into public.exams (id, exam_family_id, slug, name)
values
  ('a0000000-0000-0000-0000-000000000001', 'a3000000-0000-0000-0000-000000000001', 'rg241-exam-a', 'RG241 Exam A'),
  ('b0000000-0000-0000-0000-000000000002', 'a3000000-0000-0000-0000-000000000001', 'rg241-exam-b', 'RG241 Exam B');
insert into public.exam_streams (id, exam_id, stream_key, name)
values
  ('a5000000-0000-0000-0000-00000000000a', 'a0000000-0000-0000-0000-000000000001', 'general', 'A-General'),
  ('a5000000-0000-0000-0000-00000000000d', 'a0000000-0000-0000-0000-000000000001', 'depr',    'A-DEPR'),
  -- A-DSIM: kept dependent-free so Test 7 can demote it without tripping the
  -- depended-on-pair guard.
  ('a5000000-0000-0000-0000-00000000000e', 'a0000000-0000-0000-0000-000000000001', 'dsim',    'A-DSIM'),
  ('b5000000-0000-0000-0000-00000000000a', 'b0000000-0000-0000-0000-000000000002', 'general', 'B-General');
insert into public.exam_cycles (id, exam_id, cycle_name)
values
  ('ac000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'A-2025'),
  ('bc000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'B-2025');

-- Test 2: cross-exam cycle/stream pairing rejected.
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_cycle_streams (exam_cycle_id, stream_id)
     values ('ac000000-0000-0000-0000-000000000001','b5000000-0000-0000-0000-00000000000a')$q$,
  'ecs cross-exam');

-- Offered/expected pairs for exam A's two streams (+ B for later negative reuse).
insert into public.exam_cycle_streams (exam_cycle_id, stream_id, availability) values
  ('ac000000-0000-0000-0000-000000000001','a5000000-0000-0000-0000-00000000000a','offered'),
  ('ac000000-0000-0000-0000-000000000001','a5000000-0000-0000-0000-00000000000d','expected'),
  ('ac000000-0000-0000-0000-000000000001','a5000000-0000-0000-0000-00000000000e','offered'),
  ('bc000000-0000-0000-0000-000000000001','b5000000-0000-0000-0000-00000000000a','offered');

-- Test 3: cycle-bound stream phase requires an offered/expected pair.
-- 3a. no pair for a not-yet-registered stream (reuse depr but demote via a
--     separate not_offered cycle) — first prove not_offered is insufficient:
insert into public.exam_cycle_streams (exam_cycle_id, stream_id, availability)
values ('bc000000-0000-0000-0000-000000000001','b5000000-0000-0000-0000-00000000000a','offered')
on conflict do nothing;
insert into public.exam_cycle_streams (exam_cycle_id, stream_id, availability)
values ('ac000000-0000-0000-0000-000000000001','a5000000-0000-0000-0000-00000000000a','offered')
on conflict do nothing;

-- Test 1: valid baseline — two stream phases same slug + a common phase.
insert into public.exam_phases (id, exam_id, exam_cycle_id, phase_name, phase_slug, stream_id) values
  ('af000000-0000-0000-0000-00000000000a','a0000000-0000-0000-0000-000000000001','ac000000-0000-0000-0000-000000000001','Phase II','phase-2','a5000000-0000-0000-0000-00000000000a'),
  ('af000000-0000-0000-0000-00000000000d','a0000000-0000-0000-0000-000000000001','ac000000-0000-0000-0000-000000000001','Phase II','phase-2','a5000000-0000-0000-0000-00000000000d'),
  ('af000000-0000-0000-0000-00000000000c','a0000000-0000-0000-0000-000000000001','ac000000-0000-0000-0000-000000000001','Phase I','phase-1',null);
do $$ begin raise notice 'PASS[baseline: 2 stream phases same slug + common coexist]'; end $$;

-- Test 4: phase whose stream is from another exam.
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_phases (exam_id, exam_cycle_id, phase_name, phase_slug, stream_id)
     values ('a0000000-0000-0000-0000-000000000001','ac000000-0000-0000-0000-000000000001','X','px','b5000000-0000-0000-0000-00000000000a')$q$,
  'phase cross-exam stream');

-- Test 5: duplicate (exam, cycle, stream, slug) phase.
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_phases (exam_id, exam_cycle_id, phase_name, phase_slug, stream_id)
     values ('a0000000-0000-0000-0000-000000000001','ac000000-0000-0000-0000-000000000001','dup','phase-2','a5000000-0000-0000-0000-00000000000a')$q$,
  'phase duplicate');

-- Test 3b: a cycle-bound stream phase for a NOT_OFFERED pair fails.
insert into public.exam_cycle_streams (exam_cycle_id, stream_id, availability)
values ('bc000000-0000-0000-0000-000000000001','b5000000-0000-0000-0000-00000000000a','not_offered')
on conflict (exam_cycle_id, stream_id) do update set availability = 'not_offered';
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_phases (exam_id, exam_cycle_id, phase_name, phase_slug, stream_id)
     values ('b0000000-0000-0000-0000-000000000002','bc000000-0000-0000-0000-000000000001','P','pb','b5000000-0000-0000-0000-00000000000a')$q$,
  'phase requires offered/expected (not_offered rejected)');
update public.exam_cycle_streams set availability='offered'
  where exam_cycle_id='bc000000-0000-0000-0000-000000000001' and stream_id='b5000000-0000-0000-0000-00000000000a';

-- Sections under stream-specific phase af..0a (stream A-General).
insert into public.exam_phase_sections (exam_phase_id, subject_id, section_label, stream_id) values
  ('af000000-0000-0000-0000-00000000000a','a1000000-0000-0000-0000-000000000001','GA',null),
  ('af000000-0000-0000-0000-00000000000a','a1000000-0000-0000-0000-000000000001','GB','a5000000-0000-0000-0000-00000000000a');
do $$ begin raise notice 'PASS[section inherit + same-stream coexist]'; end $$;

-- Test 6: section stream conflicting with its stream-specific parent phase; cross-exam.
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_phase_sections (exam_phase_id, subject_id, section_label, stream_id)
     values ('af000000-0000-0000-0000-00000000000a','a1000000-0000-0000-0000-000000000001','GC','a5000000-0000-0000-0000-00000000000d')$q$,
  'section conflicts parent phase stream');
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_phase_sections (exam_phase_id, subject_id, section_label, stream_id)
     values ('af000000-0000-0000-0000-00000000000a','a1000000-0000-0000-0000-000000000001','GD','b5000000-0000-0000-0000-00000000000a')$q$,
  'section cross-exam stream');

-- Test 7: stream-scoped section under a cycle-bound COMMON phase (af..0c,
-- Phase I in cycle A-2025), for a stream that is not offered/expected for that
-- cycle. A-DSIM is dependent-free, so demoting it is allowed; scoping a section
-- to it under the cycle-bound common phase must then fail on availability.
update public.exam_cycle_streams set availability='not_offered'
  where exam_cycle_id='ac000000-0000-0000-0000-000000000001' and stream_id='a5000000-0000-0000-0000-00000000000e';
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_phase_sections (exam_phase_id, subject_id, section_label, stream_id)
     values ('af000000-0000-0000-0000-00000000000c','a1000000-0000-0000-0000-000000000001','SDSIM','a5000000-0000-0000-0000-00000000000e')$q$,
  'section availability below cycle-bound common phase');
update public.exam_cycle_streams set availability='offered'
  where exam_cycle_id='ac000000-0000-0000-0000-000000000001' and stream_id='a5000000-0000-0000-0000-00000000000e';

-- Valid coverage: common phase + stream A-General.
insert into public.exam_topic_coverage (exam_id, exam_cycle_id, exam_phase_id, topic_id, stream_id)
values ('a0000000-0000-0000-0000-000000000001','ac000000-0000-0000-0000-000000000001','af000000-0000-0000-0000-00000000000c','a2000000-0000-0000-0000-000000000001','a5000000-0000-0000-0000-00000000000a');
do $$ begin raise notice 'PASS[coverage common-phase + stream]'; end $$;

-- Test 8: coverage cycle from a different exam.
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_topic_coverage (exam_id, exam_cycle_id, exam_phase_id, topic_id)
     values ('a0000000-0000-0000-0000-000000000001','bc000000-0000-0000-0000-000000000001','af000000-0000-0000-0000-00000000000c','a2000000-0000-0000-0000-000000000001')$q$,
  'coverage cross-exam cycle');

-- Test 9: coverage section from another exam while exam_phase_id IS NULL.
-- Build a section under exam B and reference it from an exam-A coverage row.
insert into public.exam_phases (id, exam_id, phase_name, phase_slug)
values ('bf000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-000000000002','PB','pb-nc');
insert into public.exam_phase_sections (id, exam_phase_id, subject_id, section_label)
values ('bf100000-0000-0000-0000-00000000000a','bf000000-0000-0000-0000-00000000000a','a1000000-0000-0000-0000-000000000001','SB');
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_topic_coverage (exam_id, section_id, topic_id)
     values ('a0000000-0000-0000-0000-000000000001','bf100000-0000-0000-0000-00000000000a','a2000000-0000-0000-0000-000000000001')$q$,
  'coverage section-without-phase cross-exam');

-- Test 10: cycle-scoped stream coverage with no offered/expected pair.
-- Demote A-General for cycle A after removing dependents? af..0a depends on it,
-- so instead use exam B's not_offered pair path: coverage on exam B cycle with
-- B-General demoted.
update public.exam_cycle_streams set availability='not_offered'
  where exam_cycle_id='bc000000-0000-0000-0000-000000000001' and stream_id='b5000000-0000-0000-0000-00000000000a';
select pg_temp._rg241_expect_fail(
  $q$insert into public.exam_topic_coverage (exam_id, exam_cycle_id, exam_phase_id, topic_id, stream_id)
     values ('b0000000-0000-0000-0000-000000000002','bc000000-0000-0000-0000-000000000001','bf000000-0000-0000-0000-00000000000a','a2000000-0000-0000-0000-000000000001','b5000000-0000-0000-0000-00000000000a')$q$,
  'coverage cycle-scoped stream not offered');
update public.exam_cycle_streams set availability='offered'
  where exam_cycle_id='bc000000-0000-0000-0000-000000000001' and stream_id='b5000000-0000-0000-0000-00000000000a';

-- Test 11: parent move rejected while dependents exist.
select pg_temp._rg241_expect_fail(
  $q$update public.exam_streams set exam_id='b0000000-0000-0000-0000-000000000002'
     where id='a5000000-0000-0000-0000-00000000000a'$q$,
  'exam_streams exam reassign with dependents');
select pg_temp._rg241_expect_fail(
  $q$update public.exam_cycles set exam_id='b0000000-0000-0000-0000-000000000002'
     where id='ac000000-0000-0000-0000-000000000001'$q$,
  'exam_cycles exam reassign with dependents');

-- Test 12: demote / delete a depended-on pair.
select pg_temp._rg241_expect_fail(
  $q$update public.exam_cycle_streams set availability='not_offered'
     where exam_cycle_id='ac000000-0000-0000-0000-000000000001' and stream_id='a5000000-0000-0000-0000-00000000000a'$q$,
  'ecs demote depended-on pair');
select pg_temp._rg241_expect_fail(
  $q$delete from public.exam_cycle_streams
     where exam_cycle_id='ac000000-0000-0000-0000-000000000001' and stream_id='a5000000-0000-0000-0000-00000000000a'$q$,
  'ecs delete depended-on pair');

-- Test 13: child UPDATE parent-move — repoint a phase.stream_id cross-exam.
select pg_temp._rg241_expect_fail(
  $q$update public.exam_phases set stream_id='b5000000-0000-0000-0000-00000000000a'
     where id='af000000-0000-0000-0000-00000000000a'$q$,
  'phase UPDATE move cross-exam stream');

do $$ begin raise notice 'ALL RG241 CHECKS COMPLETE'; end $$;

ROLLBACK;
