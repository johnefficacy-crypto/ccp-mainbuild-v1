-- regression_247_exam_stream_eligibility.sql
--
-- Behavioral PostgreSQL regression for migration 247 (Lane R §4 stream
-- eligibility). Assumes migrations 110, 242, 247 applied. Reworked per the
-- PR #967 checkpost.
--
-- Proves:
--   1. Baseline: common + stream-specific rule for the same (scope, rule_type)
--      coexist (NULLS NOT DISTINCT); duplicate common rejected.
--   2. All new rule_types accepted (discipline, min_percentage, certification,
--      stream_availability, experience_min_years); qualification_combination
--      REQUIRES value_json (CHECK).
--   3. Cross-parent: a baseline rule whose stream belongs to another exam is
--      rejected on INSERT and on UPDATE.
--   4. Parent-side: reassigning exam_streams.exam_id while a baseline rule
--      references the stream is rejected (242 guard extended by 245).
--   5. Cycle eligibility attaches only to a real (cycle, stream) pair; carries
--      age cut-off (cutoff_date_basis/cutoff_date) and experience rows.
--   6. Deleting a cycle-stream pair that has reviewed cycle-eligibility rows is
--      REJECTED (RESTRICT — audit trail preserved), not cascaded.
--
-- Usage:  psql "$DATABASE_URL" -f regression_247_exam_stream_eligibility.sql
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
  when check_violation then raise notice 'PASS[% (check)]', p_label;
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

-- 1. Baseline coexistence.
insert into public.exam_eligibility_rules (exam_id, scope, rule_type, value_text)
  select id, 'all', 'education_min_level', 'graduation' from public.exams where slug='rg245-exam-a';
insert into public.exam_eligibility_rules (exam_id, stream_id, scope, rule_type, value_text)
  select e.id, s.id, 'all', 'education_min_level', 'graduation'
  from public.exams e join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal' where e.slug='rg245-exam-a';
do $$ begin raise notice 'PASS[baseline common + stream-specific rule coexist]'; end $$;
select pg_temp._rg245_expect_fail(
  $q$insert into public.exam_eligibility_rules (exam_id, scope, rule_type, value_text)
     select id, 'all', 'education_min_level', 'graduation' from public.exams where slug='rg245-exam-a'$q$,
  'duplicate common baseline rule');

-- 2. New baseline rule_types (experience is NOT baseline — cycle-only).
insert into public.exam_eligibility_rules (exam_id, stream_id, scope, rule_type, value_text, value_num, value_json)
  select e.id, s.id, 'all', v.rt, v.vt, v.vn, v.vj
  from public.exams e join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal'
  cross join (values
    ('discipline','LLB',null::numeric,null::jsonb),
    ('certification','Bar Council',null,null),
    ('stream_availability','offered',null,null),
    ('min_percentage',null,60,null),
    ('qualification_combination',null,null,'{"op":"and","clauses":[{"rule_type":"discipline","value_text":"LLB"},{"rule_type":"min_percentage","value_num":60}]}'::jsonb)
  ) as v(rt, vt, vn, vj)
  where e.slug='rg245-exam-a';
do $$ begin raise notice 'PASS[new baseline rule_types incl qualification_combination accepted]'; end $$;

-- experience_min_years is NOT a baseline rule_type.
select pg_temp._rg245_expect_fail(
  $q$insert into public.exam_eligibility_rules (exam_id, scope, rule_type, value_num)
     select id, 'sc', 'experience_min_years', 3 from public.exams where slug='rg245-exam-a'$q$,
  'experience_min_years rejected on baseline');

-- Fail-closed: a new-type rule cannot be promoted to verified.
select pg_temp._rg245_expect_fail(
  $q$insert into public.exam_eligibility_rules (exam_id, scope, rule_type, value_text, reviewer_status)
     select id, 'st', 'discipline', 'LLB', 'verified' from public.exams where slug='rg245-exam-a'$q$,
  'new rule_type cannot be verified (fail-closed)');

-- qualification_combination structural validation (CHECK) — negatives.
do $$
declare v_exam uuid; v_stream uuid; bad jsonb;
begin
  select id into v_exam from public.exams where slug='rg245-exam-a';
  select id into v_stream from public.exam_streams where exam_id=v_exam and stream_key='legal';
  for bad in select value from jsonb_array_elements($j$[
      null,
      {},
      {"op":"xor","clauses":[{"rule_type":"discipline","value_text":"LLB"}]},
      {"op":"and","clauses":[]},
      {"op":"and"},
      {"op":"and","clauses":[{"rule_type":"unknown","value_text":"x"}]},
      {"op":"and","clauses":[{"rule_type":"min_percentage","value_text":"sixty"}]},
      {"op":"and","clauses":[{"op":"or","clauses":[]}]}
    ]$j$::jsonb)
  loop
    begin
      insert into public.exam_eligibility_rules (exam_id, scope, rule_type, value_json)
        values (v_exam, 'ews', 'qualification_combination', bad);
      raise exception 'FAIL: malformed qualification_combination accepted: %', coalesce(bad::text,'null');
    exception when check_violation then null;  -- expected
    end;
  end loop;
  raise notice 'PASS[qualification_combination structural CHECK rejects malformed op/clauses/rule_type/value/nesting]';
end $$;

-- 3. Cross-parent stream (INSERT + UPDATE).
select pg_temp._rg245_expect_fail(
  $q$insert into public.exam_eligibility_rules (exam_id, stream_id, scope, rule_type, value_text)
     select ea.id, sb.id, 'all', 'discipline', 'X'
     from public.exams ea, public.exams eb
     join public.exam_streams sb on sb.exam_id=eb.id and sb.stream_key='general'
     where ea.slug='rg245-exam-a' and eb.slug='rg245-exam-b'$q$,
  'baseline rule cross-exam stream (insert)');
select pg_temp._rg245_expect_fail(
  $q$update public.exam_eligibility_rules
       set stream_id = (select sb.id from public.exams eb join public.exam_streams sb on sb.exam_id=eb.id and sb.stream_key='general' where eb.slug='rg245-exam-b')
     where exam_id = (select id from public.exams where slug='rg245-exam-a') and rule_type='discipline'$q$,
  'baseline rule UPDATE move cross-exam stream');

-- 4. Parent-side: move the stream's exam while a baseline rule references it.
select pg_temp._rg245_expect_fail(
  $q$update public.exam_streams set exam_id=(select id from public.exams where slug='rg245-exam-b')
     where id=(select s.id from public.exams e join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal' where e.slug='rg245-exam-a')$q$,
  'exam_streams exam reassign with dependent baseline rule');

-- 5. Cycle eligibility on a real pair, with cut-off + experience.
insert into public.exam_cycle_stream_eligibility (exam_cycle_id, stream_id, scope, rule_type, value_num, cutoff_date_basis, cutoff_date)
  select c.id, s.id, 'all', 'age_max', 30, 'cycle_notification', null
  from public.exam_cycles c join public.exams e on e.id=c.exam_id and e.slug='rg245-exam-a'
  join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal';
insert into public.exam_cycle_stream_eligibility (exam_cycle_id, stream_id, scope, rule_type, value_num)
  select c.id, s.id, 'all', 'experience_min_years', 2
  from public.exam_cycles c join public.exams e on e.id=c.exam_id and e.slug='rg245-exam-a'
  join public.exam_streams s on s.exam_id=e.id and s.stream_key='legal';
do $$ begin raise notice 'PASS[cycle eligibility with cutoff + experience on a real pair]'; end $$;
select pg_temp._rg245_expect_fail(
  $q$insert into public.exam_cycle_stream_eligibility (exam_cycle_id, stream_id, scope, rule_type, value_num)
     select c.id, sb.id, 'all', 'min_percentage', 50
     from public.exam_cycles c join public.exams e on e.id=c.exam_id and e.slug='rg245-exam-a'
     join public.exams eb on eb.slug='rg245-exam-b'
     join public.exam_streams sb on sb.exam_id=eb.id and sb.stream_key='general'$q$,
  'cycle eligibility on a non-existent pair');

-- 6. Deleting a pair with reviewed cycle-eligibility is REJECTED (RESTRICT).
select pg_temp._rg245_expect_fail(
  $q$delete from public.exam_cycle_streams cs
     using public.exam_cycles c, public.exams e, public.exam_streams s
     where cs.exam_cycle_id=c.id and c.exam_id=e.id and e.slug='rg245-exam-a'
       and cs.stream_id=s.id and s.exam_id=e.id and s.stream_key='legal'$q$,
  'delete cycle-stream pair with dependent eligibility (audit preserved)');

do $$ begin raise notice 'ALL RG245 CHECKS COMPLETE'; end $$;

ROLLBACK;
