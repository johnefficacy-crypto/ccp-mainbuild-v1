-- PR-fix-3 correctness gate: consolidate the mock-engine background work into a
-- single jobs table with switchable job kinds, and add an atomic, idempotent
-- mastery-apply function.
--
-- Supersedes 141_mock_attempt_derivation_retry.sql: derivation retries now run
-- as `analytics_retry` jobs in mock_attempt_jobs. The old table is retained
-- (empty) for one release and is scheduled for removal; nothing reads or writes
-- it after this migration. See docs/study_os/mock_submit_flow.md.

-- ── 1. consolidated jobs table ────────────────────────────────────────────────
create table if not exists public.mock_attempt_jobs (
  id            uuid primary key default gen_random_uuid(),
  job_kind      text not null check (job_kind in ('auto_submit','analytics_retry','mastery_retry')),
  attempt_id    uuid not null references public.mock_attempts(id) on delete cascade,
  scheduled_for timestamptz not null default now(),
  attempts      int not null default 0,
  last_error    text,
  status        text not null default 'pending' check (status in ('pending','running','done','failed')),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- At most one active (pending/running) job per (job_kind, attempt). Done/failed
-- rows are kept for observability and do not block re-enqueue.
create unique index if not exists mock_attempt_jobs_active_uidx
  on public.mock_attempt_jobs(job_kind, attempt_id)
  where status in ('pending','running');

-- Sweeper claim query: due jobs ordered by schedule.
create index if not exists mock_attempt_jobs_due_idx
  on public.mock_attempt_jobs(status, scheduled_for);

-- ── 2. migrate any in-flight derivation retries into the jobs table ───────────
-- mock_attempt_derivation_retry (migration 141) is absent on instances where 141
-- was never applied. An unguarded reference raises 42P01 and aborts the whole
-- migration in its transaction, so 145 is never recorded and 146/147 never run.
-- Guard the copy on the source table's existence; there is nothing to migrate
-- when it is missing.
do $migrate_retries$
begin
  if exists (
    select 1 from information_schema.tables
    where table_schema = 'public' and table_name = 'mock_attempt_derivation_retry'
  ) then
    insert into public.mock_attempt_jobs (job_kind, attempt_id, scheduled_for, attempts, last_error, status)
    select 'analytics_retry', r.attempt_id, r.next_retry_at, coalesce(r.attempts, 0), r.last_error, 'pending'
    from public.mock_attempt_derivation_retry r
    where exists (select 1 from public.mock_attempts a where a.id = r.attempt_id)
    on conflict do nothing;
  end if;
end
$migrate_retries$;

-- ── 3. atomic, idempotent mastery apply ───────────────────────────────────────
-- Runs as a single transaction (function body). Idempotency, the [0,100] safety
-- clamp, the mastery write and the audit insert all commit or roll back together,
-- so a partial failure can never leave mastery updated without an audit row.
-- The ±0.15-unit per-attempt delta cap is applied by the caller before invoking
-- this function (p_delta_db arrives already capped at ±15 db).
create or replace function public.apply_mock_mastery_delta(
  p_user_id    uuid,
  p_topic_id   uuid,
  p_attempt_id uuid,
  p_delta_db   numeric,
  p_reason     text
) returns jsonb
language plpgsql
as $$
declare
  v_mastery_id uuid;
  v_current    numeric;
  v_new        numeric;
begin
  -- Idempotency: a prior audit row for this (user, topic, attempt) means the
  -- delta was already applied. Silent no-op, not an error.
  perform 1
    from public.user_topic_mastery_audit
   where user_id = p_user_id and topic_id = p_topic_id and attempt_id = p_attempt_id
   limit 1;
  if found then
    return jsonb_build_object('applied', false, 'reason', 'already_applied');
  end if;

  select id, mastery_score
    into v_mastery_id, v_current
    from public.user_topic_mastery
   where user_id = p_user_id and topic_id = p_topic_id
     and exam_id is null and exam_phase_id is null
   limit 1;

  if v_mastery_id is null then
    v_current := 50;  -- unseen topics start at the neutral baseline
  end if;

  v_new := greatest(0, least(100, v_current + p_delta_db));  -- safety clamp

  if v_mastery_id is null then
    insert into public.user_topic_mastery (id, user_id, topic_id, mastery_score)
    values (gen_random_uuid(), p_user_id, p_topic_id, v_new);
  else
    update public.user_topic_mastery
       set mastery_score = v_new, updated_at = now()
     where id = v_mastery_id;
  end if;

  insert into public.user_topic_mastery_audit
    (id, user_id, topic_id, attempt_id, before_mastery_db, after_mastery_db, delta_applied_db, reason)
  values
    (gen_random_uuid(), p_user_id, p_topic_id, p_attempt_id, v_current, v_new, p_delta_db, coalesce(p_reason, 'mock_submit'));

  return jsonb_build_object('applied', true, 'before', v_current, 'after', v_new, 'delta', p_delta_db);
end;
$$;
