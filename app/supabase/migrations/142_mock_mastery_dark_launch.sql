create table if not exists public.mock_mastery_shadow (
  id uuid primary key,
  attempt_id uuid references public.mock_attempts(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  topic_id uuid not null references public.topics(id) on delete cascade,
  proposed_delta_unit numeric(6,4),
  proposed_delta_db numeric(5,2),
  current_mastery_db numeric(5,2),
  would_be_mastery_db numeric(5,2),
  decided_at timestamptz not null default now(),
  flag_state text not null check (flag_state in ('shadow','live'))
);

create index if not exists mock_mastery_shadow_attempt on public.mock_mastery_shadow(attempt_id);

create table if not exists public.user_topic_mastery_audit (
  id uuid primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  topic_id uuid not null references public.topics(id) on delete cascade,
  attempt_id uuid references public.mock_attempts(id) on delete set null,
  before_mastery_db numeric(5,2),
  after_mastery_db numeric(5,2),
  delta_applied_db numeric(5,2),
  reason text not null,
  at timestamptz not null default now(),
  unique (user_id, topic_id, attempt_id)
);
