-- 171_rejection_notes.sql
--
-- Adds rejection_notes (text null) to recruitment_verification_reports.
--
-- Previously reject_report() discarded the admin-supplied reason; this
-- column gives every rejection a durable audit trail. Nullable so
-- pre-existing rejected rows are unaffected (no backfill needed).

alter table public.recruitment_verification_reports
  add column if not exists rejection_notes text;

notify pgrst, 'reload schema';
