-- UPSC CSE Compiler v1 precondition smoke check.
-- Read-only: performs SELECT-only assertions and raises exceptions on failures.
-- Expected current blocker: this check fails while the 2026 verified PYQ topic-tag count is zero.

begin read only;

do $$
declare
  survivor_id constant uuid := '5466e62f-7382-4a38-ba96-2fe5fbfeaba2';
  merged_from_id constant uuid := 'a0000002-0000-0000-0000-000000000001';
  active_upsc_cse_count integer;
  merged_from_child_count bigint;
  off_survivor_pyq_count integer;
  inconsistent_fk_count integer;
  paper_2026_id uuid;
  question_count integer;
  option_count integer;
  verified_topic_tag_count integer;
begin
  select count(*)
    into active_upsc_cse_count
    from public.exams
   where slug = 'upsc-cse'
     and is_active is true;

  if active_upsc_cse_count <> 1 or not exists (
    select 1 from public.exams where id = survivor_id and slug = 'upsc-cse' and is_active is true
  ) then
    raise exception 'Expected exactly one active upsc-cse row and it must be canonical survivor %, found active count %', survivor_id, active_upsc_cse_count;
  end if;

  select coalesce(sum(row_count), 0)
    into merged_from_child_count
    from (
      select (
        xpath(
          '/row/c/text()',
          query_to_xml(
            format('select count(*) as c from %I.%I where %I = %L', fk.table_schema, fk.table_name, fk.column_name, merged_from_id),
            false,
            true,
            ''
          )
        )[1]::text
      )::bigint as row_count
      from (
        select distinct kcu.table_schema, kcu.table_name, kcu.column_name
          from information_schema.table_constraints tc
          join information_schema.key_column_usage kcu
            on kcu.constraint_schema = tc.constraint_schema
           and kcu.constraint_name = tc.constraint_name
          join information_schema.constraint_column_usage ccu
            on ccu.constraint_schema = tc.constraint_schema
           and ccu.constraint_name = tc.constraint_name
         where tc.constraint_type = 'FOREIGN KEY'
           and ccu.table_schema = 'public'
           and ccu.table_name = 'exams'
           and ccu.column_name = 'id'
           and kcu.table_schema = 'public'
      ) fk
    ) fanout;

  if merged_from_child_count <> 0 then
    raise exception 'Merged-from UPSC CSE exam % still has % child rows', merged_from_id, merged_from_child_count;
  end if;

  select count(*)
    into off_survivor_pyq_count
    from public.pyq_papers pp
    join public.exams e on e.id = pp.exam_id
   where e.slug = 'upsc-cse'
     and pp.exam_id <> survivor_id;

  if off_survivor_pyq_count <> 0 then
    raise exception 'Found % UPSC CSE PYQ papers not attached to survivor %', off_survivor_pyq_count, survivor_id;
  end if;

  select count(*)
    into inconsistent_fk_count
    from public.pyq_papers pp
    left join public.exam_cycles ec on ec.id = pp.exam_cycle_id
    left join public.exam_phases ep on ep.id = pp.exam_phase_id
   where pp.exam_id = survivor_id
     and (
       (pp.exam_cycle_id is not null and ec.exam_id is distinct from survivor_id)
       or (pp.exam_phase_id is not null and ep.exam_id is distinct from survivor_id)
     );

  if inconsistent_fk_count <> 0 then
    raise exception 'Found % UPSC CSE PYQ papers with cycle/phase FKs outside survivor %', inconsistent_fk_count, survivor_id;
  end if;

  select id
    into paper_2026_id
    from public.pyq_papers
   where exam_id = survivor_id
     and year = 2026
   order by paper_date nulls last, id
   limit 1;

  if paper_2026_id is null then
    raise exception 'No 2026 UPSC CSE PYQ paper found for survivor %', survivor_id;
  end if;

  select count(distinct id)
    into question_count
    from public.pyq_questions
   where pyq_paper_id = paper_2026_id;

  if question_count <> 100 then
    raise exception 'Expected 100 distinct questions for 2026 UPSC CSE paper %, found %', paper_2026_id, question_count;
  end if;

  select count(*)
    into option_count
    from public.pyq_options po
    join public.pyq_questions pq on pq.id = po.question_id
   where pq.pyq_paper_id = paper_2026_id;

  if option_count <> 400 then
    raise exception 'Expected 400 options for 2026 UPSC CSE paper %, found %', paper_2026_id, option_count;
  end if;

  select count(*)
    into verified_topic_tag_count
    from public.pyq_question_topic_tags pqtt
    join public.pyq_questions pq on pq.id = pqtt.question_id
   where pq.pyq_paper_id = paper_2026_id
     and pq.reviewer_status = 'verified'
     and pqtt.reviewer_status = 'verified';

  if verified_topic_tag_count = 0 then
    raise exception 'Compiler gate blocked: 2026 UPSC CSE verified questions have zero verified topic tags';
  end if;
end $$;

rollback;
