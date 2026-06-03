-- 169_organizations_short_name.sql
-- Add short_name column to organizations and a partial unique index so the
-- exam-registry importer can do exact-match deduplication instead of the lossy
-- _abbrev_from_name reconstruction that caused 11 duplicate state_psc clusters.
--
-- Index scope: only rows written by the importer carry short_name; recruitment-
-- pipeline orgs leave it NULL, so WHERE short_name IS NOT NULL already excludes
-- them without referencing import_source inside metadata jsonb.

alter table public.organizations
  add column if not exists short_name text;

create unique index if not exists uq_organizations_type_short_name_state
  on public.organizations (type, short_name, state)
  where short_name is not null;

notify pgrst, 'reload schema';
