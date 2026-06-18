-- Make mastery shadow writes idempotent for submit replays.
-- Preserve the first accepted decision per (attempt_id, topic_id, flag_state):
-- earliest decided_at wins, with id as a deterministic tie-breaker.

with ranked as (
  select
    id,
    row_number() over (
      partition by attempt_id, topic_id, flag_state
      order by decided_at asc, id asc
    ) as rn
  from public.mock_mastery_shadow
)
delete from public.mock_mastery_shadow s
using ranked r
where s.id = r.id
  and r.rn > 1;

create unique index if not exists mock_mastery_shadow_attempt_topic_flag_unique
  on public.mock_mastery_shadow(attempt_id, topic_id, flag_state);

alter table public.mock_attempt_jobs
  add column if not exists mastery_flag_state text;

update public.mock_attempt_jobs
set status = 'failed',
    last_error = 'legacy_unscoped_mastery_retry_not_replayable',
    updated_at = now()
where job_kind = 'mastery_retry'
  and mastery_flag_state is null;

alter table public.mock_attempt_jobs
  drop constraint if exists mock_attempt_jobs_mastery_flag_state_check;

alter table public.mock_attempt_jobs
  add constraint mock_attempt_jobs_mastery_flag_state_check
  check (
    (
      job_kind = 'mastery_retry'
      and mastery_flag_state in ('shadow', 'live')
      and status in ('pending','running','done','failed')
    )
    or (
      job_kind = 'mastery_retry'
      and mastery_flag_state is null
      and status = 'failed'
      and last_error = 'legacy_unscoped_mastery_retry_not_replayable'
    )
    or (job_kind <> 'mastery_retry' and mastery_flag_state is null)
  );

create unique index if not exists mock_attempt_jobs_mastery_active_uidx
  on public.mock_attempt_jobs(attempt_id, mastery_flag_state)
  where job_kind = 'mastery_retry' and status in ('pending','running');

create unique index if not exists mock_attempt_jobs_mastery_done_uidx
  on public.mock_attempt_jobs(attempt_id, mastery_flag_state)
  where job_kind = 'mastery_retry' and status = 'done';

create or replace function public.claim_mock_mastery_retry(
  p_attempt_id uuid,
  p_flag_state text,
  p_lease_until timestamptz
)
returns table(id uuid, claimed boolean)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_id uuid;
begin
  if p_flag_state not in ('shadow', 'live') then
    raise exception 'mastery retry flag_state must be shadow or live';
  end if;

  insert into public.mock_attempt_jobs (
    job_kind, attempt_id, mastery_flag_state, scheduled_for, attempts, status, last_error
  ) values (
    'mastery_retry', p_attempt_id, p_flag_state, p_lease_until, 0, 'running', null
  )
  on conflict do nothing
  returning mock_attempt_jobs.id into v_id;

  if v_id is not null then
    return query select v_id, true;
    return;
  end if;

  select j.id into v_id
  from public.mock_attempt_jobs j
  where j.job_kind = 'mastery_retry'
    and j.attempt_id = p_attempt_id
    and j.status in ('pending','running')
  order by j.created_at asc
  limit 1;

  return query select v_id, false;
end;
$$;

create or replace function public.complete_mock_mastery_retry(p_job_id uuid)
returns void
language sql
security definer
set search_path = public
as $$
  update public.mock_attempt_jobs
  set status = 'done',
      last_error = null,
      updated_at = now()
  where id = p_job_id
    and job_kind = 'mastery_retry';
$$;
