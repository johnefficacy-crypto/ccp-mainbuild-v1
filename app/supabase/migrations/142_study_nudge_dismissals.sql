-- 141_study_nudge_dismissals.sql
-- Per-user dismissal log for Study OS Home nudges.
-- One row per (user_id, nudge_code). The mission_control payload reads
-- this table and hides the nudge for a fixed TTL after dismissed_at, so
-- a dismissed nudge can still resurface once the underlying condition
-- recurs after the TTL window.

create table if not exists public.study_nudge_dismissals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  nudge_code text not null
    check (nudge_code in (
      'mock_review_pending',
      'subject_behind',
      'backlog_over_threshold',
      'milestone_in_7d',
      'focus_streak_break'
    )),
  dismissed_at timestamptz not null default now(),
  unique(user_id, nudge_code)
);

create index if not exists idx_study_nudge_dismissals_user
  on public.study_nudge_dismissals(user_id);

alter table public.study_nudge_dismissals enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'study_nudge_dismissals'
      and policyname = 'study_nudge_dismissals_owner_select'
  ) then
    create policy study_nudge_dismissals_owner_select
      on public.study_nudge_dismissals
      for select to authenticated using (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'study_nudge_dismissals'
      and policyname = 'study_nudge_dismissals_owner_insert'
  ) then
    create policy study_nudge_dismissals_owner_insert
      on public.study_nudge_dismissals
      for insert to authenticated with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'study_nudge_dismissals'
      and policyname = 'study_nudge_dismissals_owner_update'
  ) then
    create policy study_nudge_dismissals_owner_update
      on public.study_nudge_dismissals
      for update to authenticated
      using (auth.uid() = user_id)
      with check (auth.uid() = user_id);
  end if;
end $$;

notify pgrst, 'reload schema';
