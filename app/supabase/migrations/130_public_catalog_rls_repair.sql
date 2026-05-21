-- 130_public_catalog_rls_repair.sql
-- Codifies the public catalog read policies that were added manually in the
-- Supabase SQL editor, and enables RLS on the three catalog tables so the
-- policies actually take effect.
--
-- Why enable RLS here: no prior migration runs ``enable row level security``
-- on recruitments / posts / organizations. Without RLS enabled the
-- ``publish_status`` filter below is dormant and every row (including drafts)
-- is world-readable. Enabling RLS is the intended secure state; the backend
-- service role bypasses RLS, so server-side writes/reads are unaffected and
-- only anon/authenticated reads are filtered.
--
-- Idempotent: enable-RLS is a no-op when already enabled; each policy is
-- dropped-if-exists then recreated.
--
-- Scope: ONLY the three catalog tables in this migration. Drift on other
-- RLS-enabled-but-policyless tables is documented in
-- docs/schema/rls-policy-drift-audit.md and intentionally NOT changed here.
--
-- Verified against repo before writing:
--   * recruitments.publish_status   -> migration 002 / 009
--   * posts.recruitment_id          -> migration 002
--   * organizations                 -> migration 002

alter table public.recruitments  enable row level security;
alter table public.posts         enable row level security;
alter table public.organizations enable row level security;

-- recruitments: published or needs_review rows are publicly readable.
drop policy if exists recruitments_public_read on public.recruitments;
create policy recruitments_public_read
on public.recruitments
for select
using (publish_status in ('published', 'needs_review'));

-- posts: readable when their parent recruitment is publicly readable.
drop policy if exists posts_public_read on public.posts;
create policy posts_public_read
on public.posts
for select
using (
  exists (
    select 1
    from public.recruitments r
    where r.id = posts.recruitment_id
      and r.publish_status in ('published', 'needs_review')
  )
);

-- organizations: catalog reference data, fully public for read.
drop policy if exists organizations_public_read on public.organizations;
create policy organizations_public_read
on public.organizations
for select
using (true);

notify pgrst, 'reload schema';
