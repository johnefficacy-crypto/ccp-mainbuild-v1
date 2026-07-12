-- 245_quant_heuristic_review_cas_reason.sql
--
-- Checkpost #965 follow-up (GQR-Q7). Brings the quant-heuristic review path up to
-- the Content Studio review invariant already enforced for writing prompts
-- (migration 215):
--   1. A reviewer must not verify a REVISION they did not read. Migration 243's
--      cms_review_quant_heuristic CAS-checked only reviewer_status, so a content
--      edit that left the row 'pending' after the reviewer loaded the dialog could
--      still be verified. This adds a mandatory `p_expected_updated_at` content
--      CAS token (rejected 409 on mismatch), exactly like cms_review_writing_prompt.
--   2. Every review decision must carry an auditable rationale. This adds a
--      mandatory 8–500 char `p_reason`, persisted on the audit row (reviewer_notes
--      stays a separate optional/conditional field).
--
-- Migration 243 is immutable; this migration DROPs its 6-arg function and creates
-- the 8-arg replacement. Applied version = MAX(filesystem)+1 at authoring (245);
-- reconcile against `SELECT MAX(version) FROM schema_migrations;` before applying.
--
-- Posture unchanged: service-role (Content Studio / FastAPI) only. Migrations are
-- immutable once merged.

begin;

drop function if exists public.cms_review_quant_heuristic(uuid, text, text, text, uuid, text);

create or replace function public.cms_review_quant_heuristic(
    p_heuristic_id        uuid,
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
    v_row      public.quant_heuristics%rowtype;
    v_audit_id uuid;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;

    -- Mandatory audit rationale (mirrors cms_review_writing_prompt).
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

    select * into v_row from public.quant_heuristics where id = p_heuristic_id for update;
    if not found then
        raise exception 'not_found: heuristic % does not exist', p_heuristic_id using errcode = 'P0404';
    end if;

    if v_row.reviewer_status is distinct from p_expected_status then
        raise exception 'concurrent_modification: expected status=% but found %. Re-fetch and retry.',
            p_expected_status, v_row.reviewer_status using errcode = 'P0409';
    end if;

    -- Content CAS: any edit since the reviewer's read (even one leaving the row
    -- 'pending') bumps updated_at, so the decision is rejected rather than applied
    -- to a revision the reviewer never saw.
    if v_row.updated_at is distinct from p_expected_updated_at then
        raise exception 'concurrent_modification: heuristic content changed since read. Re-fetch and retry.'
            using errcode = 'P0409';
    end if;

    -- Transition matrix (unchanged from migration 243). pending is intake;
    -- needs_correction routes back to the author; a verified heuristic can be
    -- reopened for correction; a rejected one can be reopened to pending.
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
        jsonb_build_object('status', p_new_status,
                           'reviewer_notes', p_reviewer_notes,
                           'reason', btrim(p_reason)),
        btrim(p_reason)
    ) returning id into v_audit_id;

    return jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'heuristic_id', p_heuristic_id,
        'prev_status', p_expected_status, 'new_status', p_new_status
    );
end;
$$;

revoke execute on function public.cms_review_quant_heuristic(uuid, text, timestamptz, text, text, text, uuid, text) from public;
revoke execute on function public.cms_review_quant_heuristic(uuid, text, timestamptz, text, text, text, uuid, text) from anon;
revoke execute on function public.cms_review_quant_heuristic(uuid, text, timestamptz, text, text, text, uuid, text) from authenticated;
grant  execute on function public.cms_review_quant_heuristic(uuid, text, timestamptz, text, text, text, uuid, text) to service_role;

commit;
