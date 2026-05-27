create table if not exists public.mock_attempt_derivation_retry (
  attempt_id uuid primary key references public.mock_attempts(id) on delete cascade,
  attempts int not null default 0,
  last_error text,
  next_retry_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
