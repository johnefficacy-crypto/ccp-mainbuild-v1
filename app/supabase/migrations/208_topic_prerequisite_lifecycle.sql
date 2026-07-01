-- Migration 208: Topic-prerequisite review lifecycle + cycle-safe write RPC
--
-- Gate: docs/status/Topic-Prerequisite-Semantics-Gate-2026-07-01.md (J2-A′),
--       sections C / D / E. Implements EXACTLY the approved plan.
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 208 = MAX(filesystem)+1 as of the
-- branch cut. Confirm with:
--   SELECT MAX(version) FROM schema_migrations;
-- before applying to any environment.
--
-- WHAT THIS DOES
-- --------------
--   C. Adds a review lifecycle (reviewer_status + audit columns) to the existing
--      RLS-enabled public.topic_prerequisites table. reviewer_status is a new
--      column on an existing authenticated-read table; the existing read policy
--      still applies, so no new RLS policy is added.
--   D. One-time PD-D-opt-1 grandfather backfill: every edge that exists at deploy
--      time is promoted to 'locked' so already-live planner authority is preserved.
--   E. A cycle-safe, self-edge-safe SECURITY DEFINER write RPC that NEVER sets
--      review state — every write lands as 'draft' and must go through the review
--      lifecycle separately. Concurrency is serialized by ONE global advisory lock
--      so that interleaved writes A->B, B->C, C->A cannot jointly form a cycle.
--
-- Cycle-check direction (see also the 3-line note in the RPC body):
--   An edge "X depends on Y" is stored as topic_id=X, prerequisite_topic_id=Y.
--   Adding X->Y closes a cycle iff Y already (transitively) depends on X. We
--   therefore start the recursive walk at Y (p_prerequisite_topic_id), follow
--   topic_id=current -> prerequisite_topic_id over ORDERING edges only, and see
--   if we ever reach X (p_topic_id). If so, the new edge is rejected.

begin;

-- ── C. Lifecycle columns (idempotent) ────────────────────────────────────────
alter table public.topic_prerequisites
  add column if not exists reviewer_status text not null default 'draft'
    check (reviewer_status in ('draft', 'pending_review', 'reviewed', 'locked', 'rejected'));

alter table public.topic_prerequisites
  add column if not exists reviewed_by uuid references public.profiles(id) on delete set null;

alter table public.topic_prerequisites
  add column if not exists reviewed_at timestamptz;

alter table public.topic_prerequisites
  add column if not exists review_notes text;

alter table public.topic_prerequisites
  add column if not exists created_by uuid references public.profiles(id) on delete set null;

alter table public.topic_prerequisites
  add column if not exists updated_at timestamptz not null default now();

create index if not exists idx_topic_prerequisites_reviewer_status
  on public.topic_prerequisites(reviewer_status);

-- ── D. PD-D-opt-1 one-time grandfather backfill (operator-approved) ───────────
-- This migration runs exactly once at deploy. Every edge that already exists at
-- deploy time predates the review lifecycle and is trusted by the live planner,
-- so we grandfather each such edge to 'locked'. New rows added AFTER this
-- migration go through cms_write_topic_prerequisite and start as 'draft'; they
-- are NOT affected because they do not exist yet when this statement runs.
update public.topic_prerequisites
set reviewer_status = 'locked'
where reviewer_status = 'draft';

-- ── E. Cycle-safe write RPC ───────────────────────────────────────────────────
create or replace function public.cms_write_topic_prerequisite(
    p_id                     uuid,   -- NULL for create, existing id for update
    p_topic_id               uuid,
    p_prerequisite_topic_id  uuid,
    p_relation_type          text,
    p_strength               numeric,
    p_source_basis           text,
    p_created_by             uuid
)
returns public.topic_prerequisites
language plpgsql
security definer
set search_path = public
as $$
declare
    v_row public.topic_prerequisites%rowtype;
begin
    -- a) validate relation_type against the 4-value set.
    if p_relation_type not in ('requires', 'recommended_before', 'supports', 'foundation_for') then
        raise exception 'invalid_relation_type: % is not a recognised topic-prerequisite relation', p_relation_type;
    end if;

    -- b) reject self-edges.
    if p_topic_id = p_prerequisite_topic_id then
        raise exception 'self_edge: a topic cannot be its own prerequisite';
    end if;

    -- c) ONE global transaction-scoped advisory lock shared by ALL ordering
    --    writes. A single constant key (not a pair-scoped lock) forces concurrent
    --    writes A->B, B->C, C->A to serialize so they cannot jointly close a cycle.
    perform pg_advisory_xact_lock(hashtext('topic_prerequisites_ordering_graph'));

    -- d) cycle check — only for ordering relations. An edge "X depends on Y" is
    --    stored topic_id=X, prerequisite_topic_id=Y. Adding X->Y closes a cycle
    --    iff Y already transitively depends on X, so we start at Y and walk
    --    topic_id=current -> prerequisite_topic_id over ordering edges (excluding
    --    the row under update) to see if we reach X. `union` (not `union all`)
    --    dedupes visited nodes, guaranteeing termination on finite graphs.
    if p_relation_type in ('requires', 'recommended_before') then
        if exists (
            with recursive reach(node) as (
                select p_prerequisite_topic_id
                union
                select tp.prerequisite_topic_id
                from public.topic_prerequisites tp
                join reach r on tp.topic_id = r.node
                where tp.relation_type in ('requires', 'recommended_before')
                  and (p_id is null or tp.id <> p_id)
            )
            select 1 from reach where node = p_topic_id
        ) then
            raise exception 'cycle: adding this prerequisite would create a transitive cycle';
        end if;
    end if;

    -- e) create or update. This RPC MUST NOT touch review state.
    if p_id is null then
        insert into public.topic_prerequisites (
            topic_id, prerequisite_topic_id, relation_type,
            strength, source_basis, created_by, reviewer_status, updated_at
        )
        values (
            p_topic_id, p_prerequisite_topic_id, p_relation_type,
            p_strength, p_source_basis, p_created_by, 'draft', now()
        )
        returning * into v_row;
        return v_row;
    else
        update public.topic_prerequisites
        set topic_id              = p_topic_id,
            prerequisite_topic_id = p_prerequisite_topic_id,
            relation_type         = p_relation_type,
            strength              = p_strength,
            source_basis          = p_source_basis,
            updated_at            = now()
        where id = p_id
        returning * into v_row;

        if not found then
            raise exception 'not_found';
        end if;
        return v_row;
    end if;
end;
$$;

-- ── Grants: mirror migration 203 / 204 hardening exactly. ─────────────────────
-- Supabase auto-grants public-schema functions to anon + authenticated at
-- creation; REVOKE FROM PUBLIC alone is insufficient, so revoke all three.
revoke execute on function public.cms_write_topic_prerequisite(uuid, uuid, uuid, text, numeric, text, uuid) from public;
revoke execute on function public.cms_write_topic_prerequisite(uuid, uuid, uuid, text, numeric, text, uuid) from anon;
revoke execute on function public.cms_write_topic_prerequisite(uuid, uuid, uuid, text, numeric, text, uuid) from authenticated;
grant  execute on function public.cms_write_topic_prerequisite(uuid, uuid, uuid, text, numeric, text, uuid) to service_role;

commit;

select pg_notify('pgrst', 'reload schema');
