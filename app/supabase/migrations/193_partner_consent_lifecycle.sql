-- Migration 193: Partner consent lifecycle.
--
-- Makes ``accountability_partner_requests`` the canonical pending store and
-- adds ``accept_partner_request()`` — a SECURITY DEFINER transaction that
-- validates the recipient, enforces the one-active-pair-per-user guard for
-- BOTH users, and atomically creates the pair on accept (all or nothing).
-- Backs the request -> recipient accept/decline -> atomic pair creation
-- lifecycle in docs/product/accountability-partner-governance.md §2.1.
--
-- 193 = MAX(main)+1 on the filesystem (current max migration is 192).
-- Do NOT renumber existing migrations.

-- ── 1. Carry pairing goal + exam on the request so accept can build the pair ──
alter table public.accountability_partner_requests
  add column if not exists pairing_goal text
    not null default 'discipline'
    check (pairing_goal in ('discipline','same_exam','mock_review','revision')),
  add column if not exists exam_id uuid;

-- ── 2. Recipient may update (accept/decline) their own pending request ────────
-- Backend mutations run as service_role, but 070 granted the recipient SELECT
-- with no UPDATE policy (the gap the review flagged). Add a scoped UPDATE so a
-- recipient can also act directly under RLS.
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'accountability_partner_requests'
      and policyname = 'apr_recipient_update'
  ) then
    create policy apr_recipient_update on public.accountability_partner_requests
      for update using (auth.uid() = partner_id)
      with check (auth.uid() = partner_id);
  end if;
end $$;

-- ── 3. Atomic accept ─────────────────────────────────────────────────────────
create or replace function public.accept_partner_request(
    p_request_id uuid,
    p_user_id    uuid
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_req   record;
    v_pair  record;
begin
    select * into v_req
    from public.accountability_partner_requests
    where id = p_request_id
    for update;

    if not found then
        raise exception 'request_not_found' using errcode = 'P0002';
    end if;
    if v_req.partner_id is distinct from p_user_id then
        raise exception 'not_recipient' using errcode = 'P0001';
    end if;
    if v_req.status is distinct from 'pending' then
        raise exception 'request_not_pending' using errcode = 'P0001';
    end if;

    -- One-active-pair guard for BOTH users (the contract is "one person").
    if exists (
        select 1 from public.accountability_pairs
        where status = 'active'
          and (user_a in (v_req.requester_id, v_req.partner_id)
               or  user_b in (v_req.requester_id, v_req.partner_id))
    ) then
        raise exception 'already_paired' using errcode = 'P0001';
    end if;

    insert into public.accountability_pairs (user_a, user_b, pairing_goal, exam_id, status)
    values (v_req.requester_id, v_req.partner_id, v_req.pairing_goal, v_req.exam_id, 'active')
    returning * into v_pair;

    update public.accountability_partner_requests
    set status = 'accepted', responded_at = now()
    where id = p_request_id;

    return jsonb_build_object(
        'id',           v_pair.id,
        'user_a',       v_pair.user_a,
        'user_b',       v_pair.user_b,
        'pairing_goal', v_pair.pairing_goal,
        'exam_id',      v_pair.exam_id,
        'status',       v_pair.status
    );
end;
$$;

-- Grant matrix (mirror 190 / 191 / 192): a SECURITY DEFINER RPC that mutates
-- accountability_pairs must never be callable by anon or authenticated directly
-- via PostgREST /rpc/. The backend invokes it as service_role.
revoke all     on function public.accept_partner_request(uuid, uuid) from public;
revoke execute on function public.accept_partner_request(uuid, uuid) from anon;
revoke execute on function public.accept_partner_request(uuid, uuid) from authenticated;
grant  execute on function public.accept_partner_request(uuid, uuid) to service_role;

select pg_notify('pgrst', 'reload schema');
