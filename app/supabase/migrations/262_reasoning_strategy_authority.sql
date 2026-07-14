-- 262_reasoning_strategy_authority.sql
--
-- GQR-S3 — Reasoning strategy authority (Reasoning lane).
--
-- Contract: docs/architecture/solution-strategies-improvement-lab.md §8.2/§8.3 and
-- docs/status/GQR-Solution-Strategies-Improvement-Lab-Checklist-2026-07-14.md
-- (GQR-S3). The Reasoning equivalent of the Quant heuristic authority
-- (migrations 243 + 246), governed in Content Studio. Reviewed, reusable solving
-- strategies for INDEPENDENT text reasoning questions (analogy/classification,
-- series, coding-decoding, blood relations, directions, ranking, syllogism,
-- statement-conclusion, statement-assumption, logical sequence). Set/stimulus-
-- aware delivery is a later slice (GQR-S7) and is deliberately absent here.
--
-- Applied version = MAX(filesystem)+1 at merge-conflict resolution (262, after
-- 261_exam_cycles_trust_gate.sql). Reconcile against the deployed state with:
--   SELECT MAX(version) FROM schema_migrations;
-- before applying to any environment.
--
-- WHAT THIS DOES
-- --------------
-- A. reasoning_strategies — subject/topic-scoped canonical strategies with a
--    STRUCTURED applicability_rule (jsonb, not free text alone) and the
--    pending -> verified | rejected | needs_correction reviewer lifecycle. Learner
--    content columns are named to match the shared learner DTO
--    (solution-strategies-improvement-lab.md §5) so the later GQR-S4 projection is
--    a straight field copy: standard_method, faster_method, key_observation,
--    worked_example, common_traps, formula_latex.
-- B. reasoning_question_strategies — the reviewed link between a bank question and
--    a strategy, with its own reviewer_status so a question's strategy surface is
--    verified conjunctively (strategy verified AND active AND link verified) before
--    it can reach a learner (defense in depth).
-- C. cms_review_reasoning_strategy — transition-matrix + dual CAS (status +
--    content updated_at) + mandatory 8-500 char reason + audit review RPC. Folds
--    migration 246's hardening into the first landing (no 6-arg predecessor):
--    mirrors cms_review_quant_heuristic exactly.
--
-- Posture: service-role (Content Studio / FastAPI) only. No authenticated/anon
-- policy — learner-facing strategy delivery is served server-side (verified-only)
-- and there is NO direct client read of these tables in this PR (GQR-S3 stops
-- before learner delivery; GQR-S4 owns the batched projection). All new tables get
-- RLS per AGENTS.md app-metadata role convention. Migrations are immutable once
-- merged.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. Strategy authority
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.reasoning_strategies (
  id uuid primary key default gen_random_uuid(),
  -- microtopics are topic rows with level='microtopic' (migration 029), so both
  -- columns reference topics(id). At least one scope must be set (CHECK below).
  topic_id uuid references public.topics(id) on delete set null,
  microtopic_id uuid references public.topics(id) on delete set null,
  strategy_code text not null unique,
  name text not null,
  strategy_type text not null
    check (strategy_type in ('approach', 'pattern', 'elimination', 'diagram_method', 'set_method', 'trap')),
  -- Structured condition so selection is not purely free-text matching (§8.2).
  applicability_rule jsonb not null default '{}'::jsonb,
  formula_latex text,          -- rendered via the existing KaTeX path
  standard_method text,
  faster_method text,
  key_observation text,
  worked_example text,
  common_traps text,
  reviewer_status text not null default 'pending'
    check (reviewer_status in ('pending', 'verified', 'rejected', 'needs_correction')),
  reviewer_notes text,
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  is_active boolean not null default true,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint reasoning_strategies_scope_present
    check (topic_id is not null or microtopic_id is not null)
);

comment on table public.reasoning_strategies is
  'Reviewed, reusable reasoning solving strategies (§8.2). Learner content columns match the shared solution-strategy DTO so GQR-S4 projection is a straight copy.';
comment on column public.reasoning_strategies.applicability_rule is
  'Structured (jsonb) condition for strategy selection — not free-text matching alone.';

create index if not exists idx_rs_topic on public.reasoning_strategies(topic_id);
create index if not exists idx_rs_microtopic on public.reasoning_strategies(microtopic_id);
create index if not exists idx_rs_reviewer_status on public.reasoning_strategies(reviewer_status);
create index if not exists idx_rs_type on public.reasoning_strategies(strategy_type);

-- ``updated_at`` is the content-revision token consumed by the review RPC.
-- Maintain it in the database so every service-role content edit invalidates a
-- reviewer's stale snapshot even when the writer does not explicitly include an
-- updated_at value (the authoring RPC lands in GQR-S3b).
create trigger reasoning_strategies_updated_at
before update on public.reasoning_strategies
for each row execute function public.tg_set_updated_at();

-- ═════════════════════════════════════════════════════════════════════════
-- B. Question ↔ strategy link (own reviewer_status — defense in depth)
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.reasoning_question_strategies (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.mock_question_bank(id) on delete cascade,
  strategy_id uuid not null references public.reasoning_strategies(id) on delete cascade,
  relevance text not null default 'primary'
    check (relevance in ('primary', 'secondary', 'related')),
  reviewer_status text not null default 'pending'
    check (reviewer_status in ('pending', 'verified', 'rejected')),
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (question_id, strategy_id)
);

create index if not exists idx_rqs_question on public.reasoning_question_strategies(question_id);
create index if not exists idx_rqs_strategy on public.reasoning_question_strategies(strategy_id);
create index if not exists idx_rqs_reviewer_status on public.reasoning_question_strategies(reviewer_status);

-- ═════════════════════════════════════════════════════════════════════════
-- C. RLS — service-role only (no learner UI in this PR)
-- ═════════════════════════════════════════════════════════════════════════

alter table public.reasoning_strategies          enable row level security;
alter table public.reasoning_question_strategies enable row level security;

do $$
declare t text;
begin
  foreach t in array array['reasoning_strategies', 'reasoning_question_strategies']
  loop
    execute format('revoke all on public.%I from public', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke all on public.%I from authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
    -- Admin/service-role only. Learner-facing delivery is served server-side and
    -- filters reviewer_status='verified' conjunctively (strategy AND link); no
    -- direct client read is exposed until GQR-S4 justifies the projection.
  end loop;
end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- D. Review lifecycle RPC (transition matrix + dual CAS + reason + audit)
-- ═════════════════════════════════════════════════════════════════════════
-- Mirrors cms_review_quant_heuristic (migration 246): actor required, mandatory
-- 8-500 char audit reason, content-revision CAS token (p_expected_updated_at)
-- required, target status validated, row locked FOR UPDATE, optimistic-
-- concurrency check against the caller's expected status, transition-matrix guard,
-- audit row. Strategies have no publication/supersession lane, so the matrix is
-- the heuristic one, not migration 216's.
create or replace function public.cms_review_reasoning_strategy(
    p_strategy_id         uuid,
    p_expected_status     text,
    p_expected_updated_at timestamptz,
    p_new_status          text,
    p_reviewer_notes      text,
    p_reason              text,
    p_actor_user_id       uuid,
    p_actor_email         text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_row      public.reasoning_strategies%rowtype;
    v_audit_id uuid;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;

    -- Mandatory audit rationale (mirrors cms_review_quant_heuristic).
    if nullif(btrim(coalesce(p_reason, '')), '') is null
       or char_length(btrim(p_reason)) < 8 or char_length(btrim(p_reason)) > 500 then
        raise exception 'invalid_reason: p_reason must be 8–500 characters' using errcode = 'P0422';
    end if;

    -- Content-revision CAS token is required (fail closed, never verify blind).
    if p_expected_updated_at is null then
        raise exception 'concurrent_modification: p_expected_updated_at (CAS token) is required' using errcode = 'P0409';
    end if;

    if p_new_status not in ('pending', 'verified', 'rejected', 'needs_correction') then
        raise exception 'invalid_target_status: % is not a recognised status', p_new_status using errcode = 'P0422';
    end if;

    select * into v_row from public.reasoning_strategies where id = p_strategy_id for update;
    if not found then
        raise exception 'not_found: strategy % does not exist', p_strategy_id using errcode = 'P0404';
    end if;

    if v_row.reviewer_status is distinct from p_expected_status then
        raise exception 'concurrent_modification: expected status=% but found %. Re-fetch and retry.',
            p_expected_status, v_row.reviewer_status using errcode = 'P0409';
    end if;

    -- Content CAS: any edit since the reviewer's read (even one leaving the row
    -- 'pending') bumps updated_at, so the decision is rejected rather than applied
    -- to a revision the reviewer never saw.
    if v_row.updated_at is distinct from p_expected_updated_at then
        raise exception 'concurrent_modification: strategy content changed since read. Re-fetch and retry.'
            using errcode = 'P0409';
    end if;

    -- Transition matrix. pending is the intake state; needs_correction routes a
    -- flagged strategy back to the author; a verified strategy can be reopened for
    -- correction; a rejected one can be reopened to pending for rework.
    if not (
           (v_row.reviewer_status = 'pending'          and p_new_status in ('verified', 'rejected', 'needs_correction'))
        or (v_row.reviewer_status = 'needs_correction' and p_new_status in ('pending', 'rejected'))
        or (v_row.reviewer_status = 'verified'         and p_new_status = 'needs_correction')
        or (v_row.reviewer_status = 'rejected'         and p_new_status = 'pending')
    ) then
        raise exception 'transition_not_allowed: % -> % is not a permitted transition', v_row.reviewer_status, p_new_status
            using errcode = 'P0422';
    end if;

    -- Reopening a verified strategy for correction must carry a reason.
    if v_row.reviewer_status = 'verified' and p_new_status = 'needs_correction'
       and nullif(trim(coalesce(p_reviewer_notes, '')), '') is null
    then
        raise exception 'invalid_reviewer_notes: reviewer_notes required when reopening a verified strategy'
            using errcode = 'P0422';
    end if;

    update public.reasoning_strategies
    set reviewer_status = p_new_status,
        reviewed_by = p_actor_user_id,
        reviewed_at = now(),
        reviewer_notes = coalesce(p_reviewer_notes, reviewer_notes),
        updated_at = now()
    where id = p_strategy_id
    returning * into v_row;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'reasoning_strategy_status_transition', 'reasoning_strategy', p_strategy_id::text,
        jsonb_build_object('status', p_expected_status),
        jsonb_build_object('status', p_new_status,
                           'reviewer_notes', p_reviewer_notes,
                           'reason', btrim(p_reason)),
        btrim(p_reason)
    ) returning id into v_audit_id;

    return jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'strategy_id', p_strategy_id,
        'prev_status', p_expected_status, 'new_status', p_new_status
    );
end;
$$;

revoke execute on function public.cms_review_reasoning_strategy(uuid, text, timestamptz, text, text, text, uuid, text) from public;
revoke execute on function public.cms_review_reasoning_strategy(uuid, text, timestamptz, text, text, text, uuid, text) from anon;
revoke execute on function public.cms_review_reasoning_strategy(uuid, text, timestamptz, text, text, text, uuid, text) from authenticated;
grant  execute on function public.cms_review_reasoning_strategy(uuid, text, timestamptz, text, text, text, uuid, text) to service_role;

commit;
