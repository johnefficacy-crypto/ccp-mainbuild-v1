-- 249_exam_eligibility_stream_aware_activation.sql
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

notify pgrst, 'reload schema';
