-- 243_quant_heuristic_authority.sql
--
-- GQR-Q7 — Quant heuristic authority (Quant lane).
--
-- Contract: docs/architecture/subject-practice-framework.md §3.1. Reusable,
-- reviewed solution heuristics governed in Content Studio, plus a question↔
-- heuristic link, plus the review-lifecycle RPC.
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 242 = MAX(filesystem)+1 as of the rebase
-- onto main after 241_current_affairs_source_evidence.sql landed. Confirm with:
--   SELECT MAX(version) FROM schema_migrations;
-- before applying to any environment.
--
-- WHAT THIS DOES
-- --------------
-- A. quant_heuristics — subject/topic-scoped canonical heuristics with a
--    STRUCTURED applicability_rule (jsonb, not free text alone) and the
--    pending -> verified | rejected | needs_correction reviewer lifecycle.
--    expected_time_saving_pct is DELIBERATELY absent (§3.1): it would be an
--    unvalidated editorial estimate; a reviewed target-time may be added later
--    from real attempt data.
-- B. quant_question_heuristics — the reviewed link between a bank question and a
--    heuristic, with its own reviewer_status so a question's heuristic surface
--    is verified conjunctively (heuristic verified AND link verified) before it
--    can reach a learner.
-- C. cms_review_quant_heuristic — transition-matrix + CAS + audit review RPC,
--    mirroring migration 216's cms_review_competition_metric pattern.
--
-- Posture: service-role (Content Studio / FastAPI) only. No authenticated/anon
-- policy — user-facing heuristic feedback is served server-side (verified-only)
-- and there is no direct client read of these tables in this PR. All new tables
-- get RLS per AGENTS.md app-metadata role convention.
--
-- No Calculation Gym, no performance signals, no planner change here — those are
-- GQR-Q8 / GQR-Q9. Migrations are immutable once merged.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. Heuristic authority
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.quant_heuristics (
  id uuid primary key default gen_random_uuid(),
  -- microtopics are topic rows with level='microtopic' (migration 029), so both
  -- columns reference topics(id). At least one scope must be set (CHECK below).
  topic_id uuid references public.topics(id) on delete set null,
  microtopic_id uuid references public.topics(id) on delete set null,
  heuristic_code text not null unique,
  name text not null,
  heuristic_type text not null
    check (heuristic_type in ('shortcut', 'standard_method', 'trap', 'estimation')),
  -- Structured condition so selection is not purely free-text matching (§3.1).
  applicability_rule jsonb not null default '{}'::jsonb,
  formula_latex text,          -- rendered via the existing KaTeX path
  standard_method text,
  shortcut_method text,
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
  constraint quant_heuristics_scope_present
    check (topic_id is not null or microtopic_id is not null)
);

comment on table public.quant_heuristics is
  'Reviewed, reusable quant solution heuristics (§3.1). expected_time_saving_pct is intentionally excluded from v1.';
comment on column public.quant_heuristics.applicability_rule is
  'Structured (jsonb) condition for heuristic selection — not free-text matching alone.';

create index if not exists idx_qh_topic on public.quant_heuristics(topic_id);
create index if not exists idx_qh_microtopic on public.quant_heuristics(microtopic_id);
create index if not exists idx_qh_reviewer_status on public.quant_heuristics(reviewer_status);
create index if not exists idx_qh_type on public.quant_heuristics(heuristic_type);

-- ═════════════════════════════════════════════════════════════════════════
-- B. Question ↔ heuristic link (own reviewer_status — defense in depth)
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.quant_question_heuristics (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.mock_question_bank(id) on delete cascade,
  heuristic_id uuid not null references public.quant_heuristics(id) on delete cascade,
  relevance text not null default 'primary'
    check (relevance in ('primary', 'secondary', 'related')),
  reviewer_status text not null default 'pending'
    check (reviewer_status in ('pending', 'verified', 'rejected')),
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (question_id, heuristic_id)
);

create index if not exists idx_qqh_question on public.quant_question_heuristics(question_id);
create index if not exists idx_qqh_heuristic on public.quant_question_heuristics(heuristic_id);
create index if not exists idx_qqh_reviewer_status on public.quant_question_heuristics(reviewer_status);

-- ═════════════════════════════════════════════════════════════════════════
-- C. RLS — service-role only (no learner UI in this PR)
-- ═════════════════════════════════════════════════════════════════════════

alter table public.quant_heuristics          enable row level security;
alter table public.quant_question_heuristics enable row level security;

do $$
declare t text;
begin
  foreach t in array array['quant_heuristics', 'quant_question_heuristics']
  loop
    execute format('revoke all on public.%I from public', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke all on public.%I from authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
    -- Admin/service-role only. Learner-facing feedback is served server-side and
    -- filters reviewer_status='verified' conjunctively (heuristic AND link); no
    -- direct client read is exposed until a later PR justifies it.
  end loop;
end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- D. Review lifecycle RPC (transition matrix + CAS + audit)
-- ═════════════════════════════════════════════════════════════════════════
-- Mirrors cms_review_competition_metric (migration 216): actor required, target
-- status validated, row locked FOR UPDATE, optimistic-concurrency check against
-- the caller's expected status, transition-matrix guard, audit row. Heuristics
-- have no publication/supersession lane, so the matrix is simpler than 216's.
create or replace function public.cms_review_quant_heuristic(
    p_heuristic_id    uuid,
    p_expected_status text,
    p_new_status      text,
    p_reviewer_notes  text,
    p_actor_user_id   uuid,
    p_actor_email     text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_row      public.quant_heuristics%rowtype;
    v_audit_id uuid;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;

    if p_new_status not in ('pending', 'verified', 'rejected', 'needs_correction') then
        raise exception 'invalid_target_status: % is not a recognised status', p_new_status using errcode = 'P0422';
    end if;

    select * into v_row from public.quant_heuristics where id = p_heuristic_id for update;
    if not found then
        raise exception 'not_found: heuristic % does not exist', p_heuristic_id using errcode = 'P0404';
    end if;

    if v_row.reviewer_status is distinct from p_expected_status then
        raise exception 'concurrent_modification: expected status=% but found %. Re-fetch and retry.',
            p_expected_status, v_row.reviewer_status using errcode = 'P0409';
    end if;

    -- Transition matrix. pending is the intake state; needs_correction routes a
    -- flagged heuristic back to the author; a verified heuristic can be reopened
    -- for correction; a rejected one can be reopened to pending for rework.
    if not (
           (v_row.reviewer_status = 'pending'          and p_new_status in ('verified', 'rejected', 'needs_correction'))
        or (v_row.reviewer_status = 'needs_correction' and p_new_status in ('pending', 'rejected'))
        or (v_row.reviewer_status = 'verified'         and p_new_status = 'needs_correction')
        or (v_row.reviewer_status = 'rejected'         and p_new_status = 'pending')
    ) then
        raise exception 'transition_not_allowed: % -> % is not a permitted transition', v_row.reviewer_status, p_new_status
            using errcode = 'P0422';
    end if;

    -- Reopening a verified heuristic for correction must carry a reason.
    if v_row.reviewer_status = 'verified' and p_new_status = 'needs_correction'
       and nullif(trim(coalesce(p_reviewer_notes, '')), '') is null
    then
        raise exception 'invalid_reviewer_notes: reviewer_notes required when reopening a verified heuristic'
            using errcode = 'P0422';
    end if;

    update public.quant_heuristics
    set reviewer_status = p_new_status,
        reviewed_by = p_actor_user_id,
        reviewed_at = now(),
        reviewer_notes = coalesce(p_reviewer_notes, reviewer_notes),
        updated_at = now()
    where id = p_heuristic_id
    returning * into v_row;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'quant_heuristic_status_transition', 'quant_heuristic', p_heuristic_id::text,
        jsonb_build_object('status', p_expected_status),
        jsonb_build_object('status', p_new_status),
        p_reviewer_notes
    ) returning id into v_audit_id;

    return jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'heuristic_id', p_heuristic_id,
        'prev_status', p_expected_status, 'new_status', p_new_status
    );
end;
$$;

revoke execute on function public.cms_review_quant_heuristic(uuid, text, text, text, uuid, text) from public;
revoke execute on function public.cms_review_quant_heuristic(uuid, text, text, text, uuid, text) from anon;
revoke execute on function public.cms_review_quant_heuristic(uuid, text, text, text, uuid, text) from authenticated;
grant  execute on function public.cms_review_quant_heuristic(uuid, text, text, text, uuid, text) to service_role;

commit;
