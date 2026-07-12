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
  score_correct integer check (score_correct is null or score_correct >= 0),
  score_total integer check (score_total is null or score_total >= 0),
  total_time_sec integer check (total_time_sec is null or total_time_sec >= 0),
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
  -- Timing is authoritative evidence for future Quant speed/calc signals, so it
  -- must never go negative; the submit RPC additionally clamps to the frozen
  -- session duration (a per-item value cannot exceed the whole session length).
  time_spent_sec integer not null default 0 check (time_spent_sec >= 0),
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

-- ═════════════════════════════════════════════════════════════════════════
-- D. Atomic session lifecycle RPCs (single-transaction — no orphan/partial rows)
-- ═════════════════════════════════════════════════════════════════════════
-- The gym's session + its frozen items, and the finalize (item results +
-- aggregate), must each be all-or-nothing. A PL/pgSQL function runs in ONE
-- transaction, so any raised exception rolls the whole thing back — there is no
-- window where a parent commits without its children (AGENTS.md atomic cascade).

-- Create: insert the session and ALL frozen items atomically.
create or replace function public.create_calc_gym_session(
    p_user_id        uuid,
    p_exam_id        uuid,
    p_skill          text,
    p_question_count integer,
    p_duration_sec   integer,
    p_seed           bigint,
    p_policy_version text,
    p_items          jsonb,
    p_now            timestamptz
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
    v_id   uuid;
    v_item jsonb;
begin
    if p_user_id is null then
        raise exception 'missing_user: p_user_id must not be NULL' using errcode = 'P0422';
    end if;
    insert into public.calc_gym_sessions
        (user_id, exam_id, skill, question_count, duration_sec, seed,
         policy_version, status, started_at, expires_at)
    values
        (p_user_id, p_exam_id, p_skill, p_question_count, p_duration_sec, p_seed,
         p_policy_version, 'in_progress', p_now, p_now + make_interval(secs => p_duration_sec))
    returning id into v_id;

    for v_item in select * from jsonb_array_elements(coalesce(p_items, '[]'::jsonb)) loop
        insert into public.calc_gym_session_items
            (session_id, item_index, prompt, expected_answer, operands)
        values
            (v_id,
             (v_item ->> 'item_index')::int,
             v_item ->> 'prompt',
             v_item ->> 'expected_answer',
             coalesce(v_item -> 'operands', '{}'::jsonb));
    end loop;
    return v_id;
end;
$$;

-- Submit: lock the OWNED session, enforce state + deadline, score against the
-- FROZEN expected answers, clamp client timing, and write every item result plus
-- the aggregate — all in one transaction. A failure at any item rolls back the
-- whole finalize (the session stays in_progress and can be retried cleanly).
create or replace function public.submit_calc_gym_session(
    p_session_id uuid,
    p_user_id    uuid,
    p_answers    jsonb,
    p_now        timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_sess       public.calc_gym_sessions%rowtype;
    v_item       public.calc_gym_session_items%rowtype;
    v_ans        jsonb;
    v_user_ans   text;
    v_time       integer;
    v_is_correct boolean;
    v_correct    integer := 0;
    v_total      integer := 0;
    v_total_time integer := 0;
begin
    if p_user_id is null then
        raise exception 'missing_user: p_user_id must not be NULL' using errcode = 'P0422';
    end if;
    -- Ownership-scoped row lock: another user's session is simply not found.
    select * into v_sess from public.calc_gym_sessions
        where id = p_session_id and user_id = p_user_id
        for update;
    if not found then
        raise exception 'not_found: calc gym session % not found for user', p_session_id
            using errcode = 'P0404';
    end if;
    if v_sess.status = 'submitted' then
        return jsonb_build_object(
            'session_id', p_session_id, 'status', 'submitted',
            'score_correct', v_sess.score_correct, 'score_total', v_sess.score_total,
            'total_time_sec', v_sess.total_time_sec, 'idempotent', true);
    end if;
    if v_sess.status <> 'in_progress' then
        raise exception 'not_in_progress: session % has status %', p_session_id, v_sess.status
            using errcode = 'P0422';
    end if;
    if p_now > v_sess.expires_at then
        update public.calc_gym_sessions set status = 'expired' where id = p_session_id;
        raise exception 'expired: session % is past its deadline', p_session_id
            using errcode = 'P0422';
    end if;

    for v_item in
        select * from public.calc_gym_session_items
        where session_id = p_session_id order by item_index
    loop
        v_total := v_total + 1;
        v_ans := p_answers -> (v_item.item_index::text);
        v_user_ans := nullif(v_ans ->> 'user_answer', '');
        -- Clamp client-supplied timing: non-negative, bounded by the frozen
        -- session duration (a single item cannot exceed the whole session).
        v_time := coalesce((v_ans ->> 'time_spent_sec')::int, 0);
        v_time := greatest(0, least(v_time, v_sess.duration_sec));
        v_is_correct := v_user_ans is not null
            and lower(regexp_replace(btrim(v_user_ans), '\s', '', 'g'))
              = lower(regexp_replace(btrim(v_item.expected_answer), '\s', '', 'g'));
        if v_is_correct then v_correct := v_correct + 1; end if;
        v_total_time := v_total_time + v_time;
        update public.calc_gym_session_items
            set user_answer   = v_ans ->> 'user_answer',
                is_correct     = v_is_correct,
                time_spent_sec = v_time,
                answered_at    = case when v_user_ans is not null then p_now else null end
            where id = v_item.id;
    end loop;

    -- Aggregate is also bounded by the frozen limit.
    v_total_time := least(v_total_time, v_sess.duration_sec);
    update public.calc_gym_sessions
        set status = 'submitted', submitted_at = p_now,
            score_correct = v_correct, score_total = v_total, total_time_sec = v_total_time
        where id = p_session_id;

    return jsonb_build_object(
        'session_id', p_session_id, 'status', 'submitted',
        'score_correct', v_correct, 'score_total', v_total,
        'total_time_sec', v_total_time, 'idempotent', false);
end;
$$;

revoke execute on function public.create_calc_gym_session(uuid, uuid, text, integer, integer, bigint, text, jsonb, timestamptz) from public;
revoke execute on function public.create_calc_gym_session(uuid, uuid, text, integer, integer, bigint, text, jsonb, timestamptz) from anon;
revoke execute on function public.create_calc_gym_session(uuid, uuid, text, integer, integer, bigint, text, jsonb, timestamptz) from authenticated;
grant  execute on function public.create_calc_gym_session(uuid, uuid, text, integer, integer, bigint, text, jsonb, timestamptz) to service_role;

revoke execute on function public.submit_calc_gym_session(uuid, uuid, jsonb, timestamptz) from public;
revoke execute on function public.submit_calc_gym_session(uuid, uuid, jsonb, timestamptz) from anon;
revoke execute on function public.submit_calc_gym_session(uuid, uuid, jsonb, timestamptz) from authenticated;
grant  execute on function public.submit_calc_gym_session(uuid, uuid, jsonb, timestamptz) to service_role;

commit;
