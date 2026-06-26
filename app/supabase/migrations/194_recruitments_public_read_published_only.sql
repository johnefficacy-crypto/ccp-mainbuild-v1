-- 194_recruitments_public_read_published_only.sql
-- Restricts the public catalog read policies on recruitments and posts to
-- ``publish_status = 'published'`` ONLY, removing the ``needs_review`` exposure
-- that migration 130 introduced.
--
-- Why: promotion creates recruitments at ``publish_status = 'needs_review'``,
-- so migration 130's ``publish_status in ('published', 'needs_review')`` policy
-- made *promotion* — not publication — the de-facto public-visibility boundary.
-- That leaks unpublished drafts (and their posts) to anon/authenticated readers
-- before the publish gate runs, contradicting the "only published reaches users"
-- invariant. Promotion is NOT publication: only ``published`` rows are public.
-- This is the P0 RLS exposure flagged in
-- docs/audits/2026-06-25-pipeline-workspace-critical-examination.md
-- (cross-cutting RLS finding).
--
-- This migration SUPERSEDES the ``needs_review`` exposure in migration 130's
-- recruitments_public_read / posts_public_read policies. organizations_public_read
-- is intentionally left as-is in 130 (catalog reference data, fully public).
--
-- Idempotent: each policy is dropped-if-exists then recreated. RLS is already
-- enabled on these tables by migration 130, so it is intentionally NOT touched
-- here. The backend service role bypasses RLS; only anon/authenticated reads are
-- affected.
--
-- Verified against repo before writing:
--   * recruitments_public_read / posts_public_read defined ONLY in migration 130
--   * recruitments.publish_status  -> migration 002 / 009
--   * posts.recruitment_id         -> migration 002

-- recruitments: only published rows are publicly readable.
drop policy if exists recruitments_public_read on public.recruitments;
create policy recruitments_public_read
on public.recruitments
for select
using (publish_status = 'published');

-- posts: readable when their parent recruitment is publicly readable (published).
drop policy if exists posts_public_read on public.posts;
create policy posts_public_read
on public.posts
for select
using (
  exists (
    select 1
    from public.recruitments r
    where r.id = posts.recruitment_id
      and r.publish_status = 'published'
  )
);

notify pgrst, 'reload schema';
