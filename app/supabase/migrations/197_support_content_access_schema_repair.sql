-- =============================================================================
-- 197_support_content_access_schema_repair.sql
-- Idempotent forward repair for the missing 102_admin_study_os_phase3.sql
-- contract that was silently skipped because migration number 102 was already
-- occupied in supabase_migrations by the earlier pyq_options_review migration.
--
-- What was skipped:
--   * public.support_content_access (audit table for admin "open content"
--     actions against user-owned artifacts)
--   * support_content_access_user_idx, support_content_access_actor_idx
--   * is_hidden / hidden_reason / hidden_by / hidden_at columns on
--     study_leaderboard_entries and mentor_session_feedback
--   * sle_visible_only_idx (partial index for visible leaderboard rows)
--
-- Security additions beyond the original 102 contract:
--   * Enable RLS on support_content_access with zero client policies so only
--     the service-role backend can read/write it (satisfies migration 195 §4).
--   * Assert after applying that support_content_access exists and has RLS on.
--   * Assert no client INSERT/UPDATE/ALL policies exist on the table.
--
-- Safe on a DB where 102 ran correctly (all IF NOT EXISTS / IF NOT EXISTS).
-- Safe on the shared staging/production DB — does not touch the 100 verified
-- upsc-cse-pre-gs1-2026 PYQ rows or any data-bearing table destructively.
-- =============================================================================

begin;

-- ─────────────────────────────────────────────────────────────────────────────
-- §1  support_content_access — audit table
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.support_content_access (
  id            uuid        primary key default gen_random_uuid(),
  actor_id      uuid        references public.profiles(id) on delete set null,
  actor_email   text,
  user_id       uuid        not null references public.profiles(id) on delete cascade,
  artifact_kind text        not null check (artifact_kind in ('note','flashcard','mistake')),
  artifact_id   uuid        not null,
  fields_returned text[]   not null default '{}',
  reason        text        not null check (char_length(reason) >= 8),
  created_at    timestamptz not null default now()
);

create index if not exists support_content_access_user_idx
  on public.support_content_access (user_id, created_at desc);

create index if not exists support_content_access_actor_idx
  on public.support_content_access (actor_id, created_at desc);

-- Enable RLS; add NO client policies — only service_role (bypasses RLS) may
-- access this table, matching the contract stated in migration 195 §4.
alter table public.support_content_access enable row level security;

-- ─────────────────────────────────────────────────────────────────────────────
-- §2  study_leaderboard_entries — hidden-state columns / index
-- ─────────────────────────────────────────────────────────────────────────────
do $$
begin
  if to_regclass('public.study_leaderboard_entries') is not null then
    alter table public.study_leaderboard_entries
      add column if not exists is_hidden     boolean     not null default false,
      add column if not exists hidden_reason text,
      add column if not exists hidden_by     uuid        references public.profiles(id) on delete set null,
      add column if not exists hidden_at     timestamptz;

    -- Must be inside the guard: partial index on is_hidden requires the column.
    create index if not exists sle_visible_only_idx
      on public.study_leaderboard_entries (board_type, period_end desc)
      where is_hidden = false;
  end if;
end $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- §3  mentor_session_feedback — hidden-state columns
-- ─────────────────────────────────────────────────────────────────────────────
do $$
begin
  if to_regclass('public.mentor_session_feedback') is not null then
    alter table public.mentor_session_feedback
      add column if not exists is_hidden     boolean     not null default false,
      add column if not exists hidden_reason text,
      add column if not exists hidden_by     uuid        references public.profiles(id) on delete set null,
      add column if not exists hidden_at     timestamptz;
  end if;
end $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- §4  Assertions — fail closed if the repair did not land correctly
-- ─────────────────────────────────────────────────────────────────────────────
do $$
declare
  v_rls_enabled  boolean;
  v_client_writes text;
begin
  -- 4a. Table must exist.
  if to_regclass('public.support_content_access') is null then
    raise exception
      'REPAIR FAILED: public.support_content_access still absent after migration 197.';
  end if;

  -- 4b. RLS must be enabled.
  select relrowsecurity
  into   v_rls_enabled
  from   pg_class
  where  oid = 'public.support_content_access'::regclass;

  if not coalesce(v_rls_enabled, false) then
    raise exception
      'REPAIR FAILED: RLS is not enabled on public.support_content_access.';
  end if;

  -- 4c. No client-accessible write policies.
  -- (Uses unnest() to avoid name[]/text[] operator mismatch — see migration 196.)
  select string_agg(policyname, ', ' order by policyname)
  into   v_client_writes
  from (
    select p.policyname,
           (
             array_length(p.roles, 1) is null
             or exists (
               select 1
               from   unnest(p.roles) as r(rn)
               where  r.rn::text <> 'service_role'
             )
           ) as is_client_accessible
    from   pg_policies p
    where  p.schemaname = 'public'
      and  p.tablename  = 'support_content_access'
      and  p.cmd        in ('INSERT', 'UPDATE', 'ALL')
  ) sub
  where is_client_accessible;

  if v_client_writes is not null then
    raise exception
      'REPAIR FAILED: client-accessible write policies found on '
      'public.support_content_access: %. Drop them before applying this migration.',
      v_client_writes;
  end if;
end $$;

commit;

-- PostgREST: reload schema cache.
select pg_notify('pgrst', 'reload schema');
