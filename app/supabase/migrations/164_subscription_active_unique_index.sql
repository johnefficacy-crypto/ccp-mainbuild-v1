-- Enforce one active/past_due subscription per user.
-- Migration 014 created user_subscriptions_user_active_idx as a plain partial
-- index while the payments code relies on it being unique. Resolve existing
-- duplicates by retaining the newest active/past_due row per user and
-- cancelling older rows before recreating the partial index as unique.

with ranked as (
  select
    id,
    row_number() over (
      partition by user_id
      order by
        coalesce(current_period_start, created_at, starts_at, now()) desc,
        created_at desc nulls last,
        id desc
    ) as rn
  from public.user_subscriptions
  where status in ('active', 'past_due')
)
update public.user_subscriptions us
set
  status = 'cancelled',
  cancelled_at = coalesce(us.cancelled_at, now()),
  updated_at = now()
from ranked r
where us.id = r.id
  and r.rn > 1;

drop index if exists public.user_subscriptions_user_active_idx;

create unique index user_subscriptions_user_active_idx
  on public.user_subscriptions(user_id)
  where status in ('active', 'past_due');
