-- 263_reasoning_stimulus_strategy_authority.sql
--
-- GQR-S7 — governed set/stimulus strategy links.
-- VERIFY DB: filesystem number follows migration 262 on main. Reconcile with
-- SELECT max(version) FROM schema_migrations before applying to an environment.

begin;

create table if not exists public.reasoning_stimulus_strategies (
  id uuid primary key default gen_random_uuid(),
  -- Canonical PYQ stimulus identity survives projection into every frozen mock
  -- question snapshot as pyq_stimulus_id.
  stimulus_id uuid not null references public.pyq_stimuli(id) on delete cascade,
  strategy_id uuid not null references public.reasoning_strategies(id) on delete cascade,
  relevance text not null default 'primary'
    check (relevance in ('primary', 'secondary', 'related')),
  reviewer_status text not null default 'pending'
    check (reviewer_status in ('pending', 'verified', 'rejected')),
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (stimulus_id, strategy_id)
);

comment on table public.reasoning_stimulus_strategies is
  'Reviewed links from canonical PYQ stimuli to reusable reasoning set-solving strategies. Learner delivery requires verified link + verified active strategy + scope match.';

create index if not exists idx_rss_stimulus
  on public.reasoning_stimulus_strategies(stimulus_id);
create index if not exists idx_rss_strategy
  on public.reasoning_stimulus_strategies(strategy_id);
create index if not exists idx_rss_reviewer_status
  on public.reasoning_stimulus_strategies(reviewer_status);

alter table public.reasoning_stimulus_strategies enable row level security;

revoke all on public.reasoning_stimulus_strategies from public;
revoke all on public.reasoning_stimulus_strategies from anon;
revoke all on public.reasoning_stimulus_strategies from authenticated;
grant select, insert, update, delete
  on public.reasoning_stimulus_strategies to service_role;

notify pgrst, 'reload schema';

commit;
