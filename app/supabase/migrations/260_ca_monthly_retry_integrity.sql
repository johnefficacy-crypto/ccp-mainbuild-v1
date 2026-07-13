-- 260_ca_monthly_retry_integrity.sql
-- GQR-G6 integrity hardening over migrations 258/259.
--
-- 1. Retry-tail selection and consumption are bound to the learner's exact exam.
-- 2. Replaying an older weekly submission cannot overwrite/re-arm a newer retry item.
-- 3. A question is current-relevant only when EVERY promoted claim link remains
--    event-consistent, verified, current, and grounded by active official evidence.
-- 4. Only the scoped monthly-start wrapper remains executable by service_role.

begin;

-- Preserve source ordering on the queue so a delayed/replayed OLD weekly submission
-- can never re-arm an item created or consumed from a NEWER weekly attempt.
alter table public.current_affairs_retry_items
  add column if not exists source_period_end date,
  add column if not exists source_started_at timestamptz,
  add column if not exists source_submitted_at timestamptz;

update public.current_affairs_retry_items ri
set source_period_end = coalesce(ri.source_period_end, a.period_end),
    source_started_at = coalesce(ri.source_started_at, a.started_at),
    source_submitted_at = coalesce(ri.source_submitted_at, a.submitted_at, a.started_at)
from public.current_affairs_attempts a
where ri.source_attempt_id = a.id
  and (ri.source_period_end is null
       or ri.source_started_at is null
       or ri.source_submitted_at is null);

-- Full promoted-relation predicate: EVERY question link must resolve to a verified,
-- current claim on the same active/relevant event and each claim must have at least one
-- active primary/official-secondary evidence source. One good claim may not mask a
-- second superseded, mismatched, or ungrounded linked claim.
create or replace function public.ca_question_current_relevant(p_qid uuid)
returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1
    from public.mock_question_bank q
    join public.current_affairs_events ev on ev.id = q.current_affairs_item_id
    where q.id = p_qid
      and q.source_kind = 'current_event'
      and q.is_current_based = true
      and q.reviewer_status in ('verified', 'published', 'live')
      and (q.valid_from is null or q.valid_from <= now())
      and (q.valid_until is null or q.valid_until > now())
      and ev.status = 'active'
      and (ev.relevance_from is null or ev.relevance_from <= current_date)
      and (ev.relevance_until is null or ev.relevance_until >= current_date)
      and exists (
        select 1
        from public.current_affairs_question_links ql
        where ql.mock_question_id = q.id
      )
      and not exists (
        select 1
        from public.current_affairs_question_links ql
        left join public.current_affairs_claims cl on cl.id = ql.claim_id
        where ql.mock_question_id = q.id
          and (
            ql.claim_id is null
            or ql.event_id is distinct from q.current_affairs_item_id
            or cl.id is null
            or cl.event_id is distinct from q.current_affairs_item_id
            or cl.reviewer_status is distinct from 'verified'
            or cl.factual_status is distinct from 'current'
            or not exists (
              select 1
              from public.current_affairs_claim_evidence ce
              join public.current_affairs_documents d on d.id = ce.document_id
              join public.current_affairs_sources s on s.id = d.source_id
              where ce.claim_id = cl.id
                and s.is_active = true
                and s.authority_level in ('primary_official', 'official_secondary')
            )
          )
      )
  )
$$;

-- Keep weekly and monthly bundle authority aligned with the stricter per-question
-- predicate. A degraded member rejects the whole bundle at start; it is never shortened.
create or replace function public.ca_eligible_bundle_question_ids(p_bundle uuid)
returns table(mock_question_id uuid, display_order integer)
language sql stable security definer set search_path = public as $$
  select bq.mock_question_id, bq.display_order
  from public.current_affairs_bundle_questions bq
  where bq.bundle_id = p_bundle
    and public.ca_question_current_relevant(bq.mock_question_id)
  order by bq.display_order, bq.mock_question_id
$$;

-- Exact-exam retry authority. A mistake from one target exam must not enter a monthly
-- attempt for another exam merely because the bank question is globally reusable.
revoke all on function public.ca_eligible_retry_tail(uuid)
  from public, anon, authenticated, service_role;
drop function public.ca_eligible_retry_tail(uuid);

create function public.ca_eligible_retry_tail(
  p_user uuid,
  p_exam uuid
) returns table(question_id uuid, due_at timestamptz, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select ri.question_id, ri.due_at, ri.created_at
  from public.current_affairs_retry_items ri
  where ri.user_id = p_user
    and ri.exam_id is not distinct from p_exam
    and ri.status = 'pending'
    and (ri.due_at is null or ri.due_at <= now())
    and (ri.expires_at is null or ri.expires_at > now())
    and public.ca_question_current_relevant(ri.question_id)
  order by ri.due_at nulls first, ri.created_at, ri.question_id
$$;

-- Newer-source-wins enqueue. Same-attempt replay is a no-op; an older delayed submit is
-- also a no-op after a newer weekly mistake has taken ownership of the queue row.
create or replace function public.ca_enqueue_weekly_retry_items(
  p_attempt_id uuid,
  p_user uuid
) returns integer
language plpgsql security definer set search_path = public as $$
declare
  v_att public.current_affairs_attempts%rowtype;
  v_count int := 0;
  r record;
begin
  select * into v_att
  from public.current_affairs_attempts
  where id = p_attempt_id;
  if not found then raise exception 'attempt_not_found' using errcode = 'P0404'; end if;
  if v_att.user_id is distinct from p_user then
    raise exception 'not_attempt_owner' using errcode = 'P0403';
  end if;
  if v_att.status <> 'submitted' then
    raise exception 'attempt_not_submitted' using errcode = 'P0422';
  end if;
  if v_att.cadence <> 'weekly' then
    raise exception 'not_a_weekly_attempt' using errcode = 'P0422';
  end if;

  for r in
    select resp.mock_question_id as qid, q.valid_until
    from public.current_affairs_attempt_responses resp
    join public.mock_question_bank q on q.id = resp.mock_question_id
    where resp.attempt_id = p_attempt_id
      and resp.selected_option_id is not null
      and coalesce(resp.is_correct, false) = false
      and public.ca_question_current_relevant(resp.mock_question_id)
  loop
    insert into public.current_affairs_retry_items as existing (
      user_id, question_id, source_attempt_id, exam_id,
      source_period_end, source_started_at, source_submitted_at,
      due_at, expires_at, status)
    values (
      p_user, r.qid, p_attempt_id, v_att.exam_id,
      v_att.period_end, v_att.started_at,
      coalesce(v_att.submitted_at, v_att.started_at),
      now() + interval '7 days', r.valid_until, 'pending')
    on conflict (user_id, question_id) do update
      set source_attempt_id = excluded.source_attempt_id,
          exam_id = excluded.exam_id,
          source_period_end = excluded.source_period_end,
          source_started_at = excluded.source_started_at,
          source_submitted_at = excluded.source_submitted_at,
          due_at = excluded.due_at,
          expires_at = excluded.expires_at,
          status = 'pending',
          updated_at = now()
      where existing.source_attempt_id is distinct from excluded.source_attempt_id
        and (
          coalesce(existing.source_period_end, '-infinity'::date),
          coalesce(existing.source_started_at, '-infinity'::timestamptz),
          coalesce(existing.source_submitted_at, '-infinity'::timestamptz)
        ) < (
          coalesce(excluded.source_period_end, '-infinity'::date),
          coalesce(excluded.source_started_at, '-infinity'::timestamptz),
          coalesce(excluded.source_submitted_at, '-infinity'::timestamptz)
        );
    if found then v_count := v_count + 1; end if;
  end loop;

  return v_count;
end $$;

-- Scoped service entry point. It validates the bundle authority before reusing an
-- existing attempt, then proves that every supplied retry item belongs to the exact
-- attempt exam before the guarded/authoritative implementation may consume it.
create or replace function public.ca_start_monthly_current_affairs_attempt_scoped(
  p_user uuid,
  p_bundle uuid,
  p_exam uuid,
  p_template_snapshot jsonb,
  p_core_rows jsonb,
  p_retry_rows jsonb
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_bundle public.current_affairs_bundles%rowtype;
  v_existing public.current_affairs_attempts%rowtype;
  v_family uuid;
  v_qid uuid;
begin
  if p_user is null then raise exception 'user_required' using errcode = 'P0422'; end if;
  if p_bundle is null then raise exception 'bundle_not_found' using errcode = 'P0404'; end if;

  perform pg_advisory_xact_lock(hashtextextended(p_user::text || ':' || p_bundle::text, 0));

  select * into v_bundle
  from public.current_affairs_bundles
  where id = p_bundle
  for update;
  if not found then raise exception 'bundle_not_found' using errcode = 'P0404'; end if;
  if v_bundle.cadence <> 'monthly' then
    raise exception 'not_a_monthly_bundle' using errcode = 'P0422';
  end if;
  if v_bundle.status <> 'published' then
    raise exception 'bundle_not_published: %', v_bundle.status using errcode = 'P0422';
  end if;
  if v_bundle.reviewer_status <> 'verified' then
    raise exception 'bundle_not_verified: %', v_bundle.reviewer_status using errcode = 'P0422';
  end if;
  if v_bundle.publish_at is not null and v_bundle.publish_at > now() then
    raise exception 'bundle_not_yet_published' using errcode = 'P0422';
  end if;
  if v_bundle.available_until is not null and v_bundle.available_until <= now() then
    raise exception 'bundle_unavailable' using errcode = 'P0422';
  end if;

  select exam_family_id into v_family
  from public.exams
  where id = p_exam;
  if v_bundle.exam_id is not null then
    if v_bundle.exam_id is distinct from p_exam then
      raise exception 'bundle_scope_mismatch: exam' using errcode = 'P0403';
    end if;
  elsif v_bundle.exam_family_id is not null then
    if v_family is null or v_bundle.exam_family_id is distinct from v_family then
      raise exception 'bundle_scope_mismatch: family' using errcode = 'P0403';
    end if;
  end if;

  select * into v_existing
  from public.current_affairs_attempts
  where user_id = p_user and bundle_id = p_bundle
  for update;
  if found then
    if v_existing.exam_id is distinct from p_exam then
      raise exception 'bundle_scope_mismatch: existing attempt exam' using errcode = 'P0403';
    end if;
    if v_existing.status = 'in_progress' then
      return jsonb_build_object(
        'outcome', 'reused', 'attempt_id', v_existing.id,
        'question_count', v_existing.total_questions,
        'core_count', coalesce((v_existing.template_snapshot->>'core_count')::int,
                               v_existing.total_questions),
        'retry_tail_count', coalesce((v_existing.template_snapshot->>'retry_tail_count')::int, 0));
    end if;
    raise exception 'attempt_already_submitted' using errcode = 'P0409';
  end if;

  for v_qid in
    select (elem->>'question_id')::uuid
    from jsonb_array_elements(coalesce(p_retry_rows, '[]'::jsonb)) elem
  loop
    perform 1
    from public.current_affairs_retry_items ri
    where ri.user_id = p_user
      and ri.question_id = v_qid
      and ri.exam_id is not distinct from p_exam
      and ri.status = 'pending'
      and (ri.due_at is null or ri.due_at <= now())
      and (ri.expires_at is null or ri.expires_at > now())
    for update;
    if not found then
      raise exception 'retry_tail_not_eligible' using errcode = 'P0409';
    end if;
  end loop;

  return public.ca_start_monthly_current_affairs_attempt_guarded(
    p_user, p_bundle, p_exam, p_template_snapshot, p_core_rows, p_retry_rows);
end $$;

revoke all on function public.ca_question_current_relevant(uuid)
  from public, anon, authenticated;
revoke all on function public.ca_eligible_bundle_question_ids(uuid)
  from public, anon, authenticated;
revoke all on function public.ca_eligible_retry_tail(uuid, uuid)
  from public, anon, authenticated;
revoke all on function public.ca_enqueue_weekly_retry_items(uuid, uuid)
  from public, anon, authenticated;
revoke all on function public.ca_start_monthly_current_affairs_attempt_scoped(
  uuid, uuid, uuid, jsonb, jsonb, jsonb) from public, anon, authenticated;

grant execute on function public.ca_question_current_relevant(uuid) to service_role;
grant execute on function public.ca_eligible_bundle_question_ids(uuid) to service_role;
grant execute on function public.ca_eligible_retry_tail(uuid, uuid) to service_role;
grant execute on function public.ca_enqueue_weekly_retry_items(uuid, uuid) to service_role;
grant execute on function public.ca_start_monthly_current_affairs_attempt_scoped(
  uuid, uuid, uuid, jsonb, jsonb, jsonb) to service_role;

-- Migration 259's wrapper remains an internal implementation detail.
revoke execute on function public.ca_start_monthly_current_affairs_attempt_guarded(
  uuid, uuid, uuid, jsonb, jsonb, jsonb) from service_role;

commit;

notify pgrst, 'reload schema';
