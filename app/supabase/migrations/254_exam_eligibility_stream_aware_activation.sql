-- 254_exam_eligibility_stream_aware_activation.sql
--
-- Lane R §4 follow-up — activate stream-AWARE evaluation.
--
-- Migration 248 added a fail-closed CHECK
-- (`exam_eligibility_rules_verified_supported_check`) that blocked promoting the
-- new rule_types (discipline / min_percentage / certification /
-- qualification_combination / stream_availability) to reviewer_status='verified',
-- because the evaluator did not yet interpret them — a verified-but-ignored rule
-- would silently tell an aspirant "eligible".
--
-- app/exam_eligibility/evaluator.py now implements branches for ALL baseline
-- rule_types (against aspirant_education discipline/percentage and
-- aspirant_certifications), with stream-aware selection and the four-state
-- (eligible/conditional/not_eligible/unknown) + knockout contract preserved. The
-- gate is therefore lifted so operators can verify the full baseline vocabulary.
--
-- Cycle-scoped eligibility (exam_cycle_stream_eligibility) has no such CHECK;
-- experience_min_years stays cycle-only.

alter table public.exam_eligibility_rules
  drop constraint if exists exam_eligibility_rules_verified_supported_check;

-- ── Baseline qualification_combination grammar (checkpost P1) ──
-- experience_min_years is cycle/recruitment truth (§4) and must NOT appear in a
-- BASELINE combination, even though the shared validator (248, still used by the
-- cycle table) permits it. A baseline-specific validator forbids experience.
create or replace function public.is_valid_baseline_qualification_combination(j jsonb)
returns boolean language plpgsql immutable as $fn$
declare el jsonb; rt text;
begin
  if j is null or jsonb_typeof(j) <> 'object' then return false; end if;
  if j ? 'op' then
    if (j->>'op') not in ('and','or') then return false; end if;
    if not (j ? 'clauses')
       or jsonb_typeof(j->'clauses') <> 'array'
       or jsonb_array_length(j->'clauses') = 0 then
      return false;
    end if;
    for el in select value from jsonb_array_elements(j->'clauses') loop
      if not public.is_valid_baseline_qualification_combination(el) then return false; end if;
    end loop;
    return true;
  end if;
  rt := j->>'rule_type';
  if rt = 'min_percentage' then           -- experience_min_years intentionally excluded
    return (j ? 'value_num') and jsonb_typeof(j->'value_num') = 'number';
  elsif rt in ('discipline','certification','education_min_level','nationality') then
    return (j ? 'value_text') and jsonb_typeof(j->'value_text') = 'string';
  else
    return false;
  end if;
end;
$fn$;

alter table public.exam_eligibility_rules
  drop constraint if exists exam_eligibility_rules_qual_combo_json_check;
alter table public.exam_eligibility_rules
  add constraint exam_eligibility_rules_qual_combo_json_check
  check (rule_type <> 'qualification_combination'
         or public.is_valid_baseline_qualification_combination(value_json));

-- ── stream_availability domain (checkpost P1) ──
-- Fail-closed at the DB: a stream_availability rule must carry a known value,
-- so a typo can't be stored (and then silently pass) at the evaluator.
alter table public.exam_eligibility_rules
  drop constraint if exists exam_eligibility_rules_stream_availability_domain_check;
alter table public.exam_eligibility_rules
  add constraint exam_eligibility_rules_stream_availability_domain_check
  check (rule_type <> 'stream_availability'
         or value_text in ('offered','not_offered','expected'));

notify pgrst, 'reload schema';
