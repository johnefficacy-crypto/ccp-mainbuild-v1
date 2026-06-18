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
