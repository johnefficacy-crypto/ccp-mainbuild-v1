-- 291_content_cards_generalisation.sql
--
-- CONTENT-01 — generalise the two Content Studio content authorities into one
-- type-discriminated table.
--
-- Evidence: workbench/investigations/CONTENT-02_discovery.md. quant_heuristics
-- (migration 243) and reasoning_strategies (migration 262) share 17 identical
-- columns; three more are the same role under different names, and those renames
-- are ALREADY normalised away in app/study_os/solution_strategies.py, whose
-- docstring states that "registering a new subject source must never force
-- subject-specific response-loop rewrites". Migration 262's own table comment
-- says its columns were named to match that shared DTO. Only key_observation is
-- type-specific, and it is itself a member of the shared DTO's ALLOWED_FIELDS.
--
-- Applied version = MAX(filesystem)+1 at authoring (290_study_tasks_day_ordinal).
-- Reconcile against the deployed state with:
--   SELECT MAX(version) FROM schema_migrations;
-- before applying to any environment. Migrations are immutable once merged.
--
-- WHAT THIS DOES
-- --------------
-- A. content_cards — the merged authority. Same dual-FK topic scope, same
--    four-value reviewer lifecycle, same is_active/authorship columns.
-- B. Data move — count-agnostic INSERT ... SELECT from both source tables.
-- C. Junction repoint — the three link tables keep every column except their
--    content FK, which is renamed to card_id and repointed at content_cards.
-- D. Source tables dropped (see "WHY DROP, NOT VIEWS" below).
-- E. cms_review_content_card — the hardened review RPC (migration 246's 8-arg
--    shape, which 262 already matched).
-- F. cms_activate_content_card / cms_deactivate_content_card — the activate
--    split, which the contract documents but which shipped for writing_prompts
--    only (migration 226). Mirrors that implementation.
--
-- DESIGN DECISIONS (each stated because each was a real choice)
-- ------------------------------------------------------------
-- content_type is an OPEN discriminator. It carries a FORMAT check (lowercase
-- snake_case, 1-64 chars) and NO value enum. The contract's §4 seven-value list
-- was never respected by 243 or 262 — neither 'quant_heuristic' nor
-- 'reasoning_strategy' appears in it — so re-imposing it would encode a list the
-- codebase has already outgrown. A format check keeps the column disciplined
-- without fixing the set.
--
-- card_subtype keeps the PER-TYPE value check the source tables had, expressed
-- as a CASE over content_type. A type this migration does not know about is
-- unconstrained rather than rejected — the check narrows known types and stays
-- open for new ones, matching the discriminator's own posture.
--
-- Type-specific fields use NULLABLE TYPED COLUMNS, not a jsonb extras bag.
-- key_observation is the only current instance and it is already in the learner
-- DTO's ALLOWED_FIELDS, so it is shared vocabulary that one type happens not to
-- populate — not private payload. A jsonb bag would also repeat exactly the
-- mistake this migration is removing: applicability_rule was an unvalidated
-- jsonb column that nothing ever read.
--
-- applicability_rule is DROPPED, not carried. It is declared, stored, rendered
-- and never read: no matcher exists anywhere in the repository, and its only
-- concrete values are two frontend test fixtures. Selection runs through the
-- link tables. Carrying it forward would launder an unimplemented design note
-- into a new table.
--
-- COLUMN RENAMES (old -> new)
--   heuristic_code   | strategy_code   -> card_code
--   heuristic_type   | strategy_type   -> card_subtype
--   shortcut_method  | faster_method   -> faster_method
-- faster_method wins because it is the name the shared learner DTO already uses
-- (solution_strategies.ALLOWED_FIELDS), so the projection loses a rename rather
-- than gaining one.
--
-- WHY DROP, NOT VIEWS
-- -------------------
-- Three FK constraints referenced quant_heuristics(id) / reasoning_strategies(id)
-- — all three in the junction tables. A view cannot be an FK target, so keeping
-- the old names as views would have left those constraints unsatisfiable. The
-- junctions are repointed here (FK column only; every other column untouched)
-- and the source tables are then dropped outright. Keeping them as real tables
-- would mean two writable sources of truth, which is the condition this
-- migration exists to end.
--
-- Posture unchanged from 243/262: service-role (Content Studio / FastAPI) only,
-- RLS on, no anon/authenticated policy. Learner delivery stays server-side and
-- verified-only.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. The merged authority
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.content_cards (
  id uuid primary key default gen_random_uuid(),
  -- Open discriminator. Format-checked, deliberately NOT value-checked.
  content_type text not null
    check (content_type ~ '^[a-z][a-z0-9_]{0,63}$'),
  -- microtopics are topic rows with level='microtopic' (migration 029), so both
  -- columns reference topics(id). At least one scope must be set (CHECK below).
  -- Kept exactly as 243/262 had it: this is existing house shape.
  topic_id uuid references public.topics(id) on delete set null,
  microtopic_id uuid references public.topics(id) on delete set null,
  card_code text not null unique,
  name text not null,
  card_subtype text not null,
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
  constraint content_cards_scope_present
    check (topic_id is not null or microtopic_id is not null),
  -- Per-type subtype vocabulary, carried forward from the source tables. An
  -- unknown content_type is unconstrained here by design.
  constraint content_cards_subtype_valid check (
    case content_type
      when 'quant_heuristic' then
        card_subtype in ('shortcut', 'standard_method', 'trap', 'estimation')
      when 'reasoning_strategy' then
        card_subtype in ('approach', 'pattern', 'elimination', 'diagram_method', 'set_method', 'trap')
      else true
    end
  )
);

comment on table public.content_cards is
  'Reviewed, reusable topic-scoped content cards, discriminated by content_type. Merges quant_heuristics (243) and reasoning_strategies (262). content_type is an open discriminator: format-checked, not value-checked.';
comment on column public.content_cards.content_type is
  'Open discriminator. Format-checked lowercase snake_case only — the contract''s seven-value list is not enforced here and must not be re-imposed (CONTENT-02).';
comment on column public.content_cards.key_observation is
  'Shared learner-DTO field that some content types do not populate. Type-specific fields are nullable typed columns, never a jsonb extras bag.';

create index if not exists idx_cc_content_type    on public.content_cards(content_type);
create index if not exists idx_cc_topic           on public.content_cards(topic_id);
create index if not exists idx_cc_microtopic      on public.content_cards(microtopic_id);
create index if not exists idx_cc_reviewer_status on public.content_cards(reviewer_status);
create index if not exists idx_cc_subtype         on public.content_cards(content_type, card_subtype);

-- ``updated_at`` is the content-revision CAS token consumed by the review and
-- activation RPCs. Maintained in the database (as 262 did for reasoning) so any
-- service-role content edit invalidates a reviewer's stale snapshot even when
-- the writer omits updated_at.
drop trigger if exists content_cards_updated_at on public.content_cards;
create trigger content_cards_updated_at
before update on public.content_cards
for each row execute function public.tg_set_updated_at();

-- ═════════════════════════════════════════════════════════════════════════
-- B. Data move — count-agnostic
-- ═════════════════════════════════════════════════════════════════════════
-- No row count is assumed. Whatever exists in each source table is carried,
-- including zero. ids are PRESERVED so the junction repoint in C needs no
-- mapping table and no FK re-resolution.

insert into public.content_cards (
  id, content_type, topic_id, microtopic_id, card_code, name, card_subtype,
  formula_latex, standard_method, faster_method, key_observation,
  worked_example, common_traps, reviewer_status, reviewer_notes,
  reviewed_by, reviewed_at, is_active, created_by, created_at, updated_at
)
select
  h.id, 'quant_heuristic', h.topic_id, h.microtopic_id, h.heuristic_code, h.name,
  h.heuristic_type, h.formula_latex, h.standard_method,
  h.shortcut_method,        -- shortcut_method -> faster_method
  null::text,               -- quant carries no key_observation
  h.worked_example, h.common_traps, h.reviewer_status, h.reviewer_notes,
  h.reviewed_by, h.reviewed_at, h.is_active, h.created_by, h.created_at, h.updated_at
from public.quant_heuristics h;

insert into public.content_cards (
  id, content_type, topic_id, microtopic_id, card_code, name, card_subtype,
  formula_latex, standard_method, faster_method, key_observation,
  worked_example, common_traps, reviewer_status, reviewer_notes,
  reviewed_by, reviewed_at, is_active, created_by, created_at, updated_at
)
select
  s.id, 'reasoning_strategy', s.topic_id, s.microtopic_id, s.strategy_code, s.name,
  s.strategy_type, s.formula_latex, s.standard_method,
  s.faster_method, s.key_observation,
  s.worked_example, s.common_traps, s.reviewer_status, s.reviewer_notes,
  s.reviewed_by, s.reviewed_at, s.is_active, s.created_by, s.created_at, s.updated_at
from public.reasoning_strategies s;

-- Row-for-row assertion. Fails the transaction rather than landing a partial
-- move — the whole point of doing this while the tables are near-empty.
do $$
declare
  v_src_quant     bigint;
  v_src_reasoning bigint;
  v_dst_quant     bigint;
  v_dst_reasoning bigint;
  v_orphan_code   bigint;
begin
  select count(*) into v_src_quant     from public.quant_heuristics;
  select count(*) into v_src_reasoning from public.reasoning_strategies;
  select count(*) into v_dst_quant     from public.content_cards where content_type = 'quant_heuristic';
  select count(*) into v_dst_reasoning from public.content_cards where content_type = 'reasoning_strategy';

  if v_dst_quant <> v_src_quant then
    raise exception 'content_cards migration: quant row count mismatch src=% dst=%', v_src_quant, v_dst_quant;
  end if;
  if v_dst_reasoning <> v_src_reasoning then
    raise exception 'content_cards migration: reasoning row count mismatch src=% dst=%', v_src_reasoning, v_dst_reasoning;
  end if;

  -- Every source code must be present on a card with the same id, and every
  -- source id must resolve. Catches a silent column-order error that a bare
  -- count would pass.
  select count(*) into v_orphan_code
  from public.quant_heuristics h
  where not exists (
    select 1 from public.content_cards c
    where c.id = h.id and c.card_code = h.heuristic_code
      and c.content_type = 'quant_heuristic'
      and c.card_subtype is not distinct from h.heuristic_type
      and c.faster_method is not distinct from h.shortcut_method
  );
  if v_orphan_code > 0 then
    raise exception 'content_cards migration: % quant row(s) did not round-trip', v_orphan_code;
  end if;

  select count(*) into v_orphan_code
  from public.reasoning_strategies s
  where not exists (
    select 1 from public.content_cards c
    where c.id = s.id and c.card_code = s.strategy_code
      and c.content_type = 'reasoning_strategy'
      and c.card_subtype is not distinct from s.strategy_type
      and c.faster_method is not distinct from s.faster_method
      and c.key_observation is not distinct from s.key_observation
  );
  if v_orphan_code > 0 then
    raise exception 'content_cards migration: % reasoning row(s) did not round-trip', v_orphan_code;
  end if;

  raise notice 'content_cards: migrated % quant + % reasoning row(s)', v_src_quant, v_src_reasoning;
end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- C. Junction repoint — FK column only
-- ═════════════════════════════════════════════════════════════════════════
-- quant_question_heuristics and reasoning_question_strategies are the SAME
-- shape (id, question_id -> mock_question_bank, content FK, relevance,
-- reviewer_status, reviewed_by, reviewed_at, created_at, unique pair).
-- reasoning_stimulus_strategies differs on its left side only: stimulus_id
-- references pyq_stimuli(id), not mock_question_bank(id).
--
-- Every other column, check, index and unique constraint on all three is left
-- exactly as it was. Only the content-side FK moves, because it pointed at a
-- table this migration drops. ids were preserved in B, so no row is rewritten.

alter table public.quant_question_heuristics
  rename column heuristic_id to card_id;
alter table public.quant_question_heuristics
  drop constraint if exists quant_question_heuristics_heuristic_id_fkey;
alter table public.quant_question_heuristics
  add constraint quant_question_heuristics_card_id_fkey
  foreign key (card_id) references public.content_cards(id) on delete cascade;

alter table public.reasoning_question_strategies
  rename column strategy_id to card_id;
alter table public.reasoning_question_strategies
  drop constraint if exists reasoning_question_strategies_strategy_id_fkey;
alter table public.reasoning_question_strategies
  add constraint reasoning_question_strategies_card_id_fkey
  foreign key (card_id) references public.content_cards(id) on delete cascade;

alter table public.reasoning_stimulus_strategies
  rename column strategy_id to card_id;
alter table public.reasoning_stimulus_strategies
  drop constraint if exists reasoning_stimulus_strategies_strategy_id_fkey;
alter table public.reasoning_stimulus_strategies
  add constraint reasoning_stimulus_strategies_card_id_fkey
  foreign key (card_id) references public.content_cards(id) on delete cascade;

-- Indexes named for the old column keep working (an index survives a column
-- rename), but the names would mislead. Recreate under the new name.
drop index if exists public.idx_qqh_heuristic;
drop index if exists public.idx_rqs_strategy;
drop index if exists public.idx_rss_strategy;
create index if not exists idx_qqh_card on public.quant_question_heuristics(card_id);
create index if not exists idx_rqs_card on public.reasoning_question_strategies(card_id);
create index if not exists idx_rss_card on public.reasoning_stimulus_strategies(card_id);

-- ═════════════════════════════════════════════════════════════════════════
-- D. Retire the source tables and their RPCs
-- ═════════════════════════════════════════════════════════════════════════
-- Safe only because C removed the last FK references. No CASCADE: if anything
-- still depends on these, this migration must fail loudly rather than silently
-- dropping a dependant.

drop function if exists public.cms_review_quant_heuristic(uuid, text, timestamptz, text, text, text, uuid, text);
drop function if exists public.cms_review_quant_heuristic(uuid, text, text, text, uuid, text);
drop function if exists public.cms_review_reasoning_strategy(uuid, text, timestamptz, text, text, text, uuid, text);

drop table if exists public.quant_heuristics;
drop table if exists public.reasoning_strategies;

-- ═════════════════════════════════════════════════════════════════════════
-- E. RLS — service-role only, unchanged posture
-- ═════════════════════════════════════════════════════════════════════════

alter table public.content_cards enable row level security;

do $$
begin
  execute 'revoke all on public.content_cards from public';
  execute 'revoke all on public.content_cards from anon';
  execute 'revoke all on public.content_cards from authenticated';
  execute 'grant select, insert, update, delete on public.content_cards to service_role';
  -- Admin/service-role only. Learner-facing delivery is served server-side and
  -- filters reviewer_status='verified' AND is_active conjunctively with the
  -- link row's own reviewer_status; no direct client read is exposed.
end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- F. Review lifecycle RPC
-- ═════════════════════════════════════════════════════════════════════════
-- The 8-arg hardened shape: actor required, mandatory 8-500 char audit reason,
-- MANDATORY content-revision CAS token, status CAS, transition matrix, audit
-- row. This is migration 246's signature (which 262 already matched), carried
-- over unchanged apart from the table and entity names.

create or replace function public.cms_review_content_card(
    p_card_id             uuid,
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
    v_row      public.content_cards%rowtype;
    v_audit_id uuid;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;

    if nullif(btrim(coalesce(p_reason, '')), '') is null
       or char_length(btrim(p_reason)) < 8 or char_length(btrim(p_reason)) > 500 then
        raise exception 'invalid_reason: p_reason must be 8–500 characters' using errcode = 'P0422';
    end if;

    if p_expected_updated_at is null then
        raise exception 'concurrent_modification: p_expected_updated_at (CAS token) is required' using errcode = 'P0409';
    end if;

    if p_new_status not in ('pending', 'verified', 'rejected', 'needs_correction') then
        raise exception 'invalid_target_status: % is not a recognised status', p_new_status using errcode = 'P0422';
    end if;

    select * into v_row from public.content_cards where id = p_card_id for update;
    if not found then
        raise exception 'not_found: content_card % does not exist', p_card_id using errcode = 'P0404';
    end if;

    if v_row.reviewer_status is distinct from p_expected_status then
        raise exception 'concurrent_modification: expected status=% but found %. Re-fetch and retry.',
            p_expected_status, v_row.reviewer_status using errcode = 'P0409';
    end if;

    if v_row.updated_at is distinct from p_expected_updated_at then
        raise exception 'concurrent_modification: card content changed since read. Re-fetch and retry.'
            using errcode = 'P0409';
    end if;

    if not (
           (v_row.reviewer_status = 'pending'          and p_new_status in ('verified', 'rejected', 'needs_correction'))
        or (v_row.reviewer_status = 'needs_correction' and p_new_status in ('pending', 'rejected'))
        or (v_row.reviewer_status = 'verified'         and p_new_status = 'needs_correction')
        or (v_row.reviewer_status = 'rejected'         and p_new_status = 'pending')
    ) then
        raise exception 'transition_not_allowed: % -> % is not a permitted transition', v_row.reviewer_status, p_new_status
            using errcode = 'P0422';
    end if;

    if v_row.reviewer_status = 'verified' and p_new_status = 'needs_correction'
       and nullif(trim(coalesce(p_reviewer_notes, '')), '') is null
    then
        raise exception 'invalid_reviewer_notes: reviewer_notes required when reopening a verified card'
            using errcode = 'P0422';
    end if;

    update public.content_cards
    set reviewer_status = p_new_status,
        reviewed_by = p_actor_user_id,
        reviewed_at = now(),
        reviewer_notes = coalesce(p_reviewer_notes, reviewer_notes),
        updated_at = now()
    where id = p_card_id
    returning * into v_row;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'content_card_status_transition', 'content_card', p_card_id::text,
        jsonb_build_object('status', p_expected_status),
        jsonb_build_object('status', p_new_status,
                           'content_type', v_row.content_type,
                           'reviewer_notes', p_reviewer_notes,
                           'reason', btrim(p_reason)),
        btrim(p_reason)
    ) returning id into v_audit_id;

    return jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'card_id', p_card_id,
        'content_type', v_row.content_type,
        'prev_status', p_expected_status, 'new_status', p_new_status
    );
end;
$$;

-- ═════════════════════════════════════════════════════════════════════════
-- G. Activation lifecycle — the third authority
-- ═════════════════════════════════════════════════════════════════════════
-- The contract's §1.1 activate split (content_studio.activate, distinct from
-- author and review, neither of which may flip is_active) shipped for
-- writing_prompts only, in migration 226. content_cards had NO activation path
-- at all: is_active defaulted true and nothing could set it.
--
-- This mirrors cms_activate_writing_prompt: the RPC is the SOLE eligibility
-- authority, all blockers are collected without short-circuit, and a blocked
-- activation is a NORMAL {eligible:false, blockers:[...]} result — not an
-- error. CAS failure and a missing row stay HARD errors.
--
-- One deliberate difference from 226: there is no applicability-target blocker.
-- writing_prompt_targets is prompt-specific and content_cards has no
-- applicability model; inventing one here would assert a gate that does not
-- exist. Card delivery is gated by the link row's own reviewer_status instead,
-- which is enforced at read time, not at activation.

create or replace function public.cms_activate_content_card(
    p_card_id             uuid,
    p_expected_updated_at timestamptz,
    p_reason              text,
    p_actor_user_id       uuid default null,
    p_actor_email         text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_row      public.content_cards%rowtype;
    v_blockers text[] := '{}';
    v_audit_id uuid;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;

    -- CAS is a HARD error, never a blocker (226's rule).
    if p_expected_updated_at is null then
        raise exception 'concurrent_modification: stale_card — p_expected_updated_at (CAS token) is required'
            using errcode = 'P0409';
    end if;

    select * into v_row from public.content_cards where id = p_card_id for update;
    if not found then
        raise exception 'not_found: content_card % does not exist', p_card_id using errcode = 'P0404';
    end if;
    if v_row.updated_at is distinct from p_expected_updated_at then
        raise exception 'concurrent_modification: stale_card — card changed since read' using errcode = 'P0409';
    end if;

    -- Collect ALL blockers; no short-circuit.
    if p_reason is null or char_length(btrim(p_reason)) < 8 or char_length(btrim(p_reason)) > 500 then
        v_blockers := array_append(v_blockers, 'reason_required');
    end if;

    if v_row.reviewer_status is distinct from 'verified' then
        v_blockers := array_append(v_blockers, 'card_not_verified');
    end if;

    if v_row.is_active is true then
        v_blockers := array_append(v_blockers, 'already_active');
    end if;

    if array_length(v_blockers, 1) > 0 then
        return jsonb_build_object(
            'ok', true, 'eligible', false, 'blockers', to_jsonb(v_blockers),
            'card_id', p_card_id, 'content_type', v_row.content_type
        );
    end if;

    update public.content_cards
    set is_active = true,
        updated_at = now()
    where id = p_card_id
    returning * into v_row;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'content_card_activated', 'content_card', p_card_id::text,
        jsonb_build_object('is_active', false),
        jsonb_build_object('is_active', true, 'content_type', v_row.content_type, 'reason', btrim(p_reason)),
        btrim(p_reason)
    ) returning id into v_audit_id;

    return jsonb_build_object(
        'ok', true, 'eligible', true, 'blockers', '[]'::jsonb,
        'audit_id', v_audit_id, 'card_id', p_card_id,
        'content_type', v_row.content_type, 'is_active', true
    );
end;
$$;

create or replace function public.cms_deactivate_content_card(
    p_card_id             uuid,
    p_expected_updated_at timestamptz,
    p_reason              text,
    p_actor_user_id       uuid default null,
    p_actor_email         text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_row      public.content_cards%rowtype;
    v_audit_id uuid;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;
    if p_expected_updated_at is null then
        raise exception 'concurrent_modification: stale_card — p_expected_updated_at (CAS token) is required'
            using errcode = 'P0409';
    end if;
    if p_reason is null or char_length(btrim(p_reason)) < 8 or char_length(btrim(p_reason)) > 500 then
        raise exception 'invalid_reason: p_reason must be 8–500 characters' using errcode = 'P0422';
    end if;

    select * into v_row from public.content_cards where id = p_card_id for update;
    if not found then
        raise exception 'not_found: content_card % does not exist', p_card_id using errcode = 'P0404';
    end if;
    if v_row.updated_at is distinct from p_expected_updated_at then
        raise exception 'concurrent_modification: stale_card — card changed since read' using errcode = 'P0409';
    end if;

    update public.content_cards
    set is_active = false,
        updated_at = now()
    where id = p_card_id
    returning * into v_row;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'content_card_deactivated', 'content_card', p_card_id::text,
        jsonb_build_object('is_active', true),
        jsonb_build_object('is_active', false, 'content_type', v_row.content_type, 'reason', btrim(p_reason)),
        btrim(p_reason)
    ) returning id into v_audit_id;

    return jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'card_id', p_card_id,
        'content_type', v_row.content_type, 'is_active', false
    );
end;
$$;

do $$
declare fn text;
begin
  foreach fn in array array[
    'public.cms_review_content_card(uuid, text, timestamptz, text, text, text, uuid, text)',
    'public.cms_activate_content_card(uuid, timestamptz, text, uuid, text)',
    'public.cms_deactivate_content_card(uuid, timestamptz, text, uuid, text)'
  ]
  loop
    execute format('revoke execute on function %s from public', fn);
    execute format('revoke execute on function %s from anon', fn);
    execute format('revoke execute on function %s from authenticated', fn);
    execute format('grant  execute on function %s to service_role', fn);
  end loop;
end $$;

commit;
