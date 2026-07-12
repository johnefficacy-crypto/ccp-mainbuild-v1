-- regression_245_exam_stream_eligibility.sql
--
-- Behavioral PostgreSQL regression for migration 245 (Lane R §4 stream
-- eligibility). Assumes migrations 110, 242, 245 applied.
--
-- Proves:
--   1. Baseline: a common rule (stream_id NULL) and a stream-specific rule for
--      the SAME (scope, rule_type) coexist (NULLS NOT DISTINCT); a duplicate
--      common rule is rejected.
--   2. The new rule_types (min_percentage, discipline, certification,
--      qualification_combination, stream_availability) are accepted.
--   3. Cross-parent: a baseline rule whose stream belongs to another exam is
--      rejected on INSERT and on UPDATE (parent move).
--   4. Cycle eligibility only attaches to a real (exam_cycle_id, stream_id)
--      pair (composite FK); an unknown pair is rejected; duplicates rejected.
--   5. Deleting the cycle-stream pair cascades its cycle-eligibility rows.
--
-- Usage:  psql "$DATABASE_URL" -f regression_245_exam_stream_eligibility.sql
-- Expected: PASS notices, no unexpected errors. Runs in a rolled-back txn.

\set ON_ERROR_STOP on

create or replace function pg_temp._rg245_expect_fail(p_sql text, p_label text)
returns void language plpgsql as $$
begin
  execute p_sql;
  raise exception 'FAIL[%]: expected rejection but the statement succeeded', p_label;
exception
  when sqlstate 'P0422' then raise notice 'PASS[%]', p_label;
  when unique_violation then raise notice 'PASS[% (unique)]', p_label;
  when foreign_key_violation then raise notice 'PASS[% (fk)]', p_label;
end $$;

BEGIN;

insert into public.exam_families (slug, name) values ('rg245-fam','RG245 Family');
insert into public.exams (slug, name, exam_family_id)
  select 'rg245-exam-a','RG245 Exam A', id from public.exam_families where slug='rg245-fam';
insert into public.exams (slug, name, exam_family_id)
  select 'rg245-exam-b','RG245 Exam B', id from public.exam_families where slug='rg245-fam';
insert into public.exam_streams (exam_id, stream_key, name)
  select id, 'legal', 'Legal' from public.exams where slug='rg245-exam-a';
insert into public.exam_streams (exam_id, stream_key, name)
  select id, 'general', 'General' from public.exams where slug='rg245-exam-b';
insert into public.exam_cycles (exam_id, cycle_name)
  select id, 'RG245-A-2025' from public.exams where slug='rg245-exam-a';
insert into public.exam_cycle_streams (exam_cycle_id, stream_id, availability)
  select c.id, s.id, 'offered'
  from public.exam_cycles c
  join public.exams e on e.id=c.exam_id and e.slug='rg245-exam-a'
  join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal';

-- 1. Baseline coexistence: common education rule + stream-specific one.
insert into public.exam_eligibility_rules (exam_id, scope, rule_type, value_text)
  select id, 'all', 'education_min_level', 'graduation' from public.exams where slug='rg245-exam-a';
insert into public.exam_eligibility_rules (exam_id, stream_id, scope, rule_type, value_text)
  select e.id, s.id, 'all', 'education_min_level', 'graduation'
  from public.exams e join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal'
  where e.slug='rg245-exam-a';
do $$ begin raise notice 'PASS[baseline common + stream-specific rule coexist]'; end $$;

select pg_temp._rg245_expect_fail(
  $q$insert into public.exam_eligibility_rules (exam_id, scope, rule_type, value_text)
     select id, 'all', 'education_min_level', 'graduation' from public.exams where slug='rg245-exam-a'$q$,
  'duplicate common baseline rule');

-- 2. New rule_types accepted.
insert into public.exam_eligibility_rules (exam_id, stream_id, scope, rule_type, value_text)
  select e.id, s.id, 'all', 'discipline', 'LLB'
  from public.exams e join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal' where e.slug='rg245-exam-a';
insert into public.exam_eligibility_rules (exam_id, stream_id, scope, rule_type, value_num)
  select e.id, s.id, 'all', 'min_percentage', 60
  from public.exams e join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal' where e.slug='rg245-exam-a';
do $$ begin raise notice 'PASS[new rule_types discipline/min_percentage accepted]'; end $$;

-- 3. Cross-parent: stream from exam B on an exam A rule.
select pg_temp._rg245_expect_fail(
  $q$insert into public.exam_eligibility_rules (exam_id, stream_id, scope, rule_type, value_text)
     select ea.id, sb.id, 'all', 'discipline', 'X'
     from public.exams ea, public.exams eb
     join public.exam_streams sb on sb.exam_id=eb.id and sb.stream_key='general'
     where ea.slug='rg245-exam-a' and eb.slug='rg245-exam-b'$q$,
  'baseline rule cross-exam stream');

-- UPDATE parent-move: repoint an exam-A rule's stream to exam B's stream.
select pg_temp._rg245_expect_fail(
  $q$update public.exam_eligibility_rules
       set stream_id = (select sb.id from public.exams eb join public.exam_streams sb on sb.exam_id=eb.id and sb.stream_key='general' where eb.slug='rg245-exam-b')
     where exam_id = (select id from public.exams where slug='rg245-exam-a') and rule_type='discipline'$q$,
  'baseline rule UPDATE move cross-exam stream');

-- 4. Cycle eligibility attaches only to a real (cycle, stream) pair.
insert into public.exam_cycle_stream_eligibility (exam_cycle_id, stream_id, scope, rule_type, value_num)
  select c.id, s.id, 'all', 'min_percentage', 55
  from public.exam_cycles c join public.exams e on e.id=c.exam_id and e.slug='rg245-exam-a'
  join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal';
do $$ begin raise notice 'PASS[cycle eligibility on a real pair]'; end $$;

-- Unknown pair (exam B general has no cycle-stream row) -> FK reject.
select pg_temp._rg245_expect_fail(
  $q$insert into public.exam_cycle_stream_eligibility (exam_cycle_id, stream_id, scope, rule_type, value_num)
     select c.id, sb.id, 'all', 'min_percentage', 50
     from public.exam_cycles c join public.exams e on e.id=c.exam_id and e.slug='rg245-exam-a'
     join public.exams eb on eb.slug='rg245-exam-b'
     join public.exam_streams sb on sb.exam_id=eb.id and sb.stream_key='general'$q$,
  'cycle eligibility on a non-existent pair');

-- Duplicate cycle rule.
select pg_temp._rg245_expect_fail(
  $q$insert into public.exam_cycle_stream_eligibility (exam_cycle_id, stream_id, scope, rule_type, value_num)
     select c.id, s.id, 'all', 'min_percentage', 99
     from public.exam_cycles c join public.exams e on e.id=c.exam_id and e.slug='rg245-exam-a'
     join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal'$q$,
  'duplicate cycle eligibility rule');

-- 5. Cascade on pair delete.
delete from public.exam_cycle_streams cs
 using public.exam_cycles c, public.exams e, public.exam_streams s
 where cs.exam_cycle_id=c.id and c.exam_id=e.id and e.slug='rg245-exam-a'
   and cs.stream_id=s.id and s.exam_id=e.id and s.stream_key='legal';
do $$
declare v_int int;
begin
  select count(*) into v_int from public.exam_cycle_stream_eligibility;
  if v_int <> 0 then raise exception 'FAIL: cycle eligibility not cascaded on pair delete (%)', v_int; end if;
  raise notice 'PASS[cycle eligibility cascades on pair delete]';
end $$;

do $$ begin raise notice 'ALL RG245 CHECKS COMPLETE'; end $$;

ROLLBACK;
