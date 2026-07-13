-- Operator VERIFY DB for migration 254 (Lane R R1 eligibility + cycles seed).
--
-- Run against staging AFTER applying migration 254. Confirms the seed landed,
-- that NOTHING is aspirant-visible yet (all rows reviewer_status='draft', per the
-- Tier-A governance posture), and that every qualification_combination row is
-- structurally valid. This is a read-only audit — it writes nothing.
--
--   psql "$STAGING_DSN" -v ON_ERROR_STOP=1 -f validate_regulatory_eligibility_seed.sql

\echo '== cycles seeded (expect sebi 2025, pfrda 2025, irdai 2024) =='
select e.slug, c.year, c.cycle_name, c.status, c.reviewer_status is not distinct from null as no_reviewer_col
from public.exam_cycles c join public.exams e on e.id = c.exam_id
where e.slug in ('sebi-grade-a','pfrda-grade-a','irdai-am')
order by e.slug, c.year;

\echo '== eligibility rules by exam / draft posture (expect ALL draft, 0 verified) =='
select e.slug,
       count(*)                                            as rules,
       count(*) filter (where r.stream_id is not null)     as stream_scoped,
       count(*) filter (where r.reviewer_status = 'draft') as draft,
       count(*) filter (where r.reviewer_status = 'verified') as verified
from public.exam_eligibility_rules r
join public.exams e on e.id = r.exam_id
where e.slug in ('sebi-grade-a','pfrda-grade-a','irdai-am')
group by e.slug order by e.slug;

\echo '== HARD GATE: no seeded regulator rule may be verified before review =='
do $$
declare n int;
begin
  select count(*) into n
  from public.exam_eligibility_rules r
  join public.exams e on e.id = r.exam_id
  where e.slug in ('sebi-grade-a','pfrda-grade-a','irdai-am')
    and r.reviewer_status = 'verified'
    and r.source_notes ilike '%stream%';  -- heuristic: seeded rows carry source_notes
  if n > 0 then
    raise exception 'GOVERNANCE VIOLATION: % seeded regulatory rule(s) are verified without review', n;
  end if;
  raise notice 'OK: no seeded regulatory rule is verified yet';
end$$;

\echo '== every qualification_combination row is structurally valid =='
select e.slug, s.stream_key,
       public.is_valid_qualification_combination(r.value_json) as valid
from public.exam_eligibility_rules r
join public.exams e on e.id = r.exam_id
left join public.exam_streams s on s.id = r.stream_id
where r.rule_type = 'qualification_combination'
  and e.slug in ('sebi-grade-a','pfrda-grade-a','irdai-am')
order by e.slug, s.stream_key;
