-- 232_trap_drill_mastery_shadow.sql
-- PYQ v2 PR-8 (shadow only): observe would-be mastery/revision from direct-PYQ
-- trap-drill attempts, WITHOUT touching the frozen mock mastery path.
--
-- Governance / P8 constraints honoured:
--   * This is a SEPARATE table from public.mock_mastery_shadow. The P8 shadow
--     window (docs/audits/2026-07-06-p8-t0-start.md) measures mock_mastery_shadow
--     as OUTPUT — trap-drill rows must never land there or they'd contaminate the
--     analysis and there is no source column on that table to exclude them.
--   * No foreign key to public.mock_attempts. Trap-drill evidence has no
--     mock_attempts row; its attempt id is a deterministic uuid5 synthesised by
--     app/study_os/attempt_evidence.load_trap_drill_evidence — lineage only.
--   * flag_state is CHECK-pinned to 'shadow'. It is structurally impossible for a
--     trap-drill mastery row to be recorded as a live decision from this table;
--     the writer is additionally gated behind its own FF_TRAP_DRILL_MASTERY_SHADOW
--     flag, independent of FF_MOCK_MASTERY_WRITES.
--   * None of the 36 fingerprinted mastery-validation files are modified by this
--     migration (it only adds a new table), so the P8 T0 baseline is unaffected.
--
-- Post-migration-173 table: the one-time blanket service_role grant (173) ran
-- before this table existed, so an explicit grant is required (same pattern as
-- migrations 225 / 231).

create table if not exists public.trap_drill_mastery_shadow (
  id                            uuid primary key default gen_random_uuid(),
  -- deterministic uuid5 from load_trap_drill_evidence; lineage only, NOT an FK.
  synthetic_attempt_id          uuid not null,
  user_id                       uuid not null references public.profiles(id) on delete cascade,
  exam_id                       uuid not null references public.exams(id) on delete cascade,
  drill_seed                    text,
  topic_id                      uuid not null references public.topics(id) on delete cascade,
  proposed_delta_unit           numeric(6,4),
  proposed_delta_db             numeric(5,2),
  proposed_delta_db_unweighted  numeric(5,2),
  current_mastery_db            numeric(5,2),
  would_be_mastery_db           numeric(5,2),
  -- P3 revision routing (relearn | review | practice); trap-drill is application
  -- evidence, so a mid-band topic routes to 'practice'.
  revision_bucket               text check (revision_bucket in ('relearn', 'review', 'practice')),
  -- pinned, not just defaulted: this table is a distinct population by construction.
  source                        text not null default 'trap_drill' check (source = 'trap_drill'),
  -- shadow-only by construction — never a live write from this table.
  flag_state                    text not null default 'shadow' check (flag_state = 'shadow'),
  trust_level                   text not null default 'platform_verified',
  decided_at                    timestamptz not null default now()
);

-- Idempotency: one shadow decision per (drill session, topic). Retried drill
-- logging re-derives the same synthetic_attempt_id, so upsert stays stable.
create unique index if not exists trap_drill_mastery_shadow_attempt_topic_uidx
  on public.trap_drill_mastery_shadow(synthetic_attempt_id, topic_id);

create index if not exists trap_drill_mastery_shadow_user_exam_idx
  on public.trap_drill_mastery_shadow(user_id, exam_id, decided_at desc);

-- Internal validation data: service-role only. Enable RLS with no anon/authenticated
-- policy so aspirants can never read shadow decisions; service_role bypasses RLS
-- but carries an explicit all-policy for belt-and-suspenders.
alter table public.trap_drill_mastery_shadow enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
     where schemaname = 'public'
       and tablename = 'trap_drill_mastery_shadow'
       and policyname = 'trap_drill_mastery_shadow_service_role_all'
  ) then
    create policy "trap_drill_mastery_shadow_service_role_all"
      on public.trap_drill_mastery_shadow for all to service_role
      using (true) with check (true);
  end if;
end $$;

grant select, insert, update, delete on public.trap_drill_mastery_shadow to service_role;

select pg_notify('pgrst', 'reload schema');
