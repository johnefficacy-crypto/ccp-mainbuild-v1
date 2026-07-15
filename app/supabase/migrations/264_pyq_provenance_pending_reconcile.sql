-- 264_pyq_provenance_pending_reconcile.sql
--
-- Reconcile the stale `metadata.provenance_pending` flag on PYQ papers/sources.
--
-- Background (audit 2026-07-14, defect #5): migration 228 seeded the canonical
-- UPSC CSE 2025 CSAT Set-B paper and its official source with
-- `metadata.provenance_pending = true` while trust was pending. After the
-- operator attached the official source and promoted both rows to
-- `trust_status = 'verified'`, the pending flag was never cleared — the
-- promotion workflow (review_pyq_paper RPC / direct verify) touches
-- `trust_status` but not this metadata key. Runtime eligibility does not read
-- the flag, so nothing broke, but verified rows carrying `provenance_pending`
-- are misleading debt.
--
-- Fix has two parts:
--   Part A — one-time data reconciliation: strip `provenance_pending` from any
--            already-verified paper/source that still carries it.
--   Part B — workflow reconciliation: a BEFORE INSERT/UPDATE trigger that clears
--            the flag atomically whenever a row lands at `trust_status =
--            'verified'`, so every future promotion path (RPC or direct write)
--            converges without re-introducing the debt. Pending/rejected rows
--            keep the flag untouched.

-- ─── Part A: reconcile existing verified rows ──────────────────────────────────

update public.pyq_papers
set metadata   = metadata - 'provenance_pending',
    updated_at = now()
where trust_status = 'verified'
  and metadata ? 'provenance_pending';

-- pyq_sources has no updated_at column (migration 032) — update metadata only.
update public.pyq_sources
set metadata = metadata - 'provenance_pending'
where trust_status = 'verified'
  and metadata ? 'provenance_pending';

-- ─── Part B: keep verified promotions clean going forward ──────────────────────

create or replace function public.clear_provenance_pending_on_verify()
returns trigger
language plpgsql
as $$
begin
  if new.trust_status = 'verified'
     and new.metadata ? 'provenance_pending' then
    new.metadata := new.metadata - 'provenance_pending';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_pyq_papers_clear_provenance_pending on public.pyq_papers;
create trigger trg_pyq_papers_clear_provenance_pending
  before insert or update on public.pyq_papers
  for each row execute function public.clear_provenance_pending_on_verify();

drop trigger if exists trg_pyq_sources_clear_provenance_pending on public.pyq_sources;
create trigger trg_pyq_sources_clear_provenance_pending
  before insert or update on public.pyq_sources
  for each row execute function public.clear_provenance_pending_on_verify();
