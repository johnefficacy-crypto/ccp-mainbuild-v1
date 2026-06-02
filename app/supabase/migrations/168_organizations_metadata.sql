-- 168_organizations_metadata.sql
-- Add metadata jsonb column to organizations, mirroring the pattern on exams
-- and exam_cycles.  Needed so the exam-registry importer can record
-- import_status='pending_review' and official_url on imported org rows,
-- satisfying the platform's trust-model requirement that imported rows are
-- distinguishable from reviewed/verified rows.
--
-- Additive only.  Migration 167 is not changed.
-- The NOT NULL DEFAULT '{}' means all pre-existing rows get an empty object —
-- no backfill required, no existing writer or reader is broken.

alter table public.organizations
  add column if not exists metadata jsonb not null default '{}'::jsonb;

notify pgrst, 'reload schema';
