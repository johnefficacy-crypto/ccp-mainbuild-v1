-- 137_attempt_analytics.sql
create table if not exists public.mock_attempt_summary (
  attempt_id uuid primary key references public.mock_attempts(id) on delete cascade,
  score_raw numeric not null,
  score_percentage numeric not null,
  total_correct int,
  total_wrong int,
  total_unattempted int,
  total_marked int,
  net_marks numeric,
  accuracy_pct numeric,
  time_used_sec int,
  time_remaining_sec int,
  avg_time_per_q_sec numeric,
  computed_at timestamptz not null default now()
);

create table if not exists public.mock_attempt_section_breakdown (
  id uuid primary key default gen_random_uuid(),
  attempt_id uuid not null references public.mock_attempts(id) on delete cascade,
  section_index int,
  section_name text,
  correct int,
  wrong int,
  unattempted int,
  marks numeric,
  accuracy_pct numeric,
  time_used_sec int,
  unique (attempt_id, section_index)
);

create table if not exists public.mock_attempt_topic_breakdown (
  id uuid primary key default gen_random_uuid(),
  attempt_id uuid not null references public.mock_attempts(id) on delete cascade,
  topic_id uuid references public.topics(id),
  microtopic_id uuid references public.topics(id),
  attempted int,
  correct int,
  wrong int,
  accuracy_pct numeric,
  avg_time_sec numeric,
  difficulty_breakdown jsonb not null default '{}'::jsonb,
  unique (attempt_id, topic_id, microtopic_id)
);

create table if not exists public.mock_attempt_response_classification (
  attempt_id uuid not null references public.mock_attempts(id) on delete cascade,
  question_id uuid not null references public.mock_question_bank(id) on delete cascade,
  error_type text not null check (error_type in (
    'correct','silly_mistake','concept_gap','option_trap',
    'calc_error','time_pressure_unattempted','knowledge_gap','marked_unanswered'
  )),
  signals jsonb not null default '{}'::jsonb,
  primary key (attempt_id, question_id)
);
