-- Add 'biannual' to the exams.cadence CHECK constraint.
-- Some exams (e.g. certain banking/insurance recruitment cycles) run twice a
-- year; the existing enum (annual/recurring/irregular/one_off/unknown) had no
-- value for that cadence, forcing operators to misclassify them as 'annual'
-- or 'recurring'. Migrations are immutable — this widens the constraint
-- added in 172_exam_portfolio_lanes.sql rather than editing it.
alter table public.exams
  drop constraint if exists exams_cadence_check;

alter table public.exams
  add constraint exams_cadence_check
  check (cadence is null or cadence in ('annual','biannual','recurring','irregular','one_off','unknown'));
