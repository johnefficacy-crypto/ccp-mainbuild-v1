-- =============================================================================
-- 194_accountability_pairs_pending_consent.sql
-- Security: allow a 'pending' state on accountability_pairs so partner
-- requests require the target's consent before becoming 'active'.
--
-- Vuln (see docs/audits/2026-06-25-auth-rbac-security-review.md #6 / H5):
--   request_partner inserted rows with status='active', binding an arbitrary
--   partner_id (the victim) into an active partnership — and the resulting
--   trust/leaderboard linkage — with no acceptance step. The backend now
--   inserts 'pending' and only the target (user_b) can flip it to 'active'
--   via accept_partner, but the table's CHECK constraint only allowed
--   ('active','paused','ended'). This migration adds 'pending'.
--
-- Idempotent and re-runnable. Does not change the default ('active') so any
-- other legitimate direct insert paths are unaffected.
-- =============================================================================

begin;

do $$
begin
  if to_regclass('public.accountability_pairs') is not null then
    alter table public.accountability_pairs
      drop constraint if exists accountability_pairs_status_check;
    alter table public.accountability_pairs
      add constraint accountability_pairs_status_check
      check (status in ('active', 'paused', 'ended', 'pending'));
  end if;
end $$;

commit;

-- PostgREST: reload the schema cache so the constraint change is picked up.
select pg_notify('pgrst', 'reload schema');
