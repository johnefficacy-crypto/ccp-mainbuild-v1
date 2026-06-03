-- 169_organizations_short_name.sql
--
-- Adds organizations.short_name for exact-match deduplication in the exam-registry
-- importer.  The column stores normalize_short_name(input_short_name) at insert time,
-- eliminating the heuristic _abbrev_from_name(stored_full_name) reconstruction loop
-- that caused 11 state_psc duplicate clusters.
--
-- Backfill (authoritative short_name from xlsx "PSC Short Name" column) runs via
-- scripts/dedupe_state_psc_orgs.py after this migration is applied.
--
-- Type segregation: recruitment-pipeline orgs (type in 'Banking', 'Railway', ...)
-- are inserted by the promote_recruitment_rpc without metadata.import_source and
-- keep short_name = NULL — they are completely excluded from the partial index below.

alter table public.organizations
  add column if not exists short_name text;

-- Partial unique index: prevents re-duplication on any future importer run.
-- Scope: only rows where import_source is an importer value AND short_name is set.
-- Recruitment pipeline rows (import_source = NULL or other values) are excluded.
-- COALESCE(state, '') treats NULL state (central orgs) as '' so the index covers them.
create unique index if not exists orgs_importer_dedupe_key
  on public.organizations(type, short_name, coalesce(state, ''))
  where (metadata->>'import_source') in ('exam_registry_workbook', 'exam_registry_source_urls')
    and short_name is not null;
