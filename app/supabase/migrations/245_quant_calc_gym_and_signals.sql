-- 245_quant_calc_gym_and_signals.sql
--
-- GQR-Q8 — Calculation Gym (deterministic, no LLM) + quant performance signals
-- (shadow sibling to mastery, NOT a mastery writer). Quant lane.
--
-- Contract: docs/architecture/subject-practice-framework.md §3.2 (Calculation
-- Gym) and §3.3 (quant performance signal).
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 245 = MAX(filesystem)+1 as of the rebase
-- onto main after 244_financial_regulatory_family_identity_seed.sql landed.
-- Confirm with: SELECT MAX(version) FROM schema_migrations; before applying.
--
-- WHAT THIS DOES
-- --------------
-- A. calc_gym_sessions / calc_gym_session_items — the server owns the range,
--    random seed, generation, expected answers, and session limits. The seed and
--    generated items are FROZEN so a session is reproducible (§3.2). No LLM.
-- B. quant_performance_signals — a SIBLING signal derived from attempt analytics
--    (accuracy + time_ratio), never a new user_topic_mastery writer (§3.3).
--    Thresholds are shadow defaults, centrally VERSIONED (policy_version).
--
-- Posture: service-role (FastAPI) only — the learner-runtime wiring and shadow
-- dashboards are a later slice (this PR does not touch subject_practice dispatch
-- or the mastery time weighting). All new tables get RLS.
--
-- Migrations are immutable once merged.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. Calculation Gym — frozen, reproducible sessions
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.calc_gym_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  exam_id uuid references public.exams(id) on delete set null,
  skill text not null
    check (skill in (
      'tables', 'squares', 'cubes', 'square_roots', 'cube_roots',
      'fraction_percent', 'ratio_simplify', 'approximation', 'multiplication_patterns'
    )),
  question_count integer not null check (question_count > 0),
  duration_sec integer not null check (duration_sec > 0),
  -- The frozen PRNG seed: identical (skill, seed, count, policy_version) always
  -- regenerates identical items, so a session is reproducible / auditable.
  seed bigint not null,
  policy_version text not null,
  status text not null default 'in_progress'
    check (status in ('in_progress', 'submitted', 'expired')),
  started_at timestamptz not null default now(),
  expires_at timestamptz not null,
  submitted_at timestamptz,
  score_correct integer,
  score_total integer,
  total_time_sec integer,
  created_at timestamptz not null default now()
);

comment on table public.calc_gym_sessions is
  'Deterministic Calculation Gym sessions (§3.2). seed + items frozen for reproducibility. No LLM.';

create index if not exists idx_cgs_user on public.calc_gym_sessions(user_id);
create index if not exists idx_cgs_status on public.calc_gym_sessions(status);
create index if not exists idx_cgs_skill on public.calc_gym_sessions(skill);

create table if not exists public.calc_gym_session_items (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.calc_gym_sessions(id) on delete cascade,
  item_index integer not null,
  prompt text not null,
  -- Expected answer frozen at generation — scoring never recomputes it live, so
  -- a later generator change cannot alter an in-flight or historical session.
  expected_answer text not null,
  operands jsonb not null default '{}'::jsonb,
  user_answer text,
  is_correct boolean,
  time_spent_sec integer not null default 0,
  answered_at timestamptz,
  unique (session_id, item_index)
);

create index if not exists idx_cgsi_session on public.calc_gym_session_items(session_id);

-- ═════════════════════════════════════════════════════════════════════════
-- B. Quant performance signals — sibling to mastery, shadow, versioned
-- ═════════════════════════════════════════════════════════════════════════
-- Derived independently from AttemptQuestionAnalytics (expected/actual time,
-- correctness) — NEVER a user_topic_mastery writer. The existing 5% over-time
-- penalty in mastery_delta.py stays untouched; this is a separate, comparable
-- signal computed first in shadow (§3.3).

create table if not exists public.quant_performance_signals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  exam_id uuid references public.exams(id) on delete set null,
  topic_id uuid references public.topics(id) on delete set null,
  microtopic_id uuid references public.topics(id) on delete set null,
  signal_type text not null
    check (signal_type in (
      'insufficient_evidence', 'concept_gap', 'application_gap',
      'speed_gap', 'calculation_gap', 'stable'
    )),
  sample_count integer not null default 0,
  accuracy_pct numeric,
  median_time_ratio numeric,   -- actual_time_sec / expected_time_sec
  p75_time_ratio numeric,
  confidence numeric,
  policy_version text not null,
  computed_at timestamptz not null default now(),
  input_fingerprint text,
  created_at timestamptz not null default now()
);

comment on table public.quant_performance_signals is
  'Sibling quant signal (§3.3) — accuracy + time_ratio, NOT a mastery tier. Thresholds are shadow defaults, versioned by policy_version.';

-- One current signal per (user, scope, policy_version). NULLS NOT DISTINCT
-- (PG15+, as migrations 219/223) so a NULL microtopic/exam scope still collapses
-- to a single upsert target instead of accumulating duplicates.
create unique index if not exists uq_qps_scope_policy
  on public.quant_performance_signals(user_id, exam_id, topic_id, microtopic_id, policy_version)
  nulls not distinct;
create index if not exists idx_qps_user on public.quant_performance_signals(user_id);
create index if not exists idx_qps_signal_type on public.quant_performance_signals(signal_type);

-- ═════════════════════════════════════════════════════════════════════════
-- C. RLS — service-role only (no learner UI / dashboards in this PR)
-- ═════════════════════════════════════════════════════════════════════════

alter table public.calc_gym_sessions          enable row level security;
alter table public.calc_gym_session_items      enable row level security;
alter table public.quant_performance_signals   enable row level security;

do $$
declare t text;
begin
  foreach t in array array[
    'calc_gym_sessions', 'calc_gym_session_items', 'quant_performance_signals'
  ]
  loop
    execute format('revoke all on public.%I from public', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke all on public.%I from authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
    -- Service-role only. The gym runtime and shadow dashboards are served through
    -- FastAPI (server owns seed/answers/limits); no direct client read is exposed
    -- until the learner-runtime slice (GQR-11) wires it.
  end loop;
end $$;

commit;
