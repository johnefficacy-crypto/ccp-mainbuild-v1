-- 259_ca_monthly_retry_hardening.sql
-- GQR-G6 checkpost hardening over migration 258.
--
-- 1. Weekly submission atomically enqueues still-relevant wrong answers. The queue upsert is
--    idempotent for the same source attempt but re-arms a question after a NEW weekly mistake.
-- 2. Monthly start is serialized per learner+bundle and returns an existing attempt before
--    re-validating a caller tail that another concurrent request may already have consumed.
-- 3. The guarded start canonicalises the frozen core/tail ids in template_snapshot from the
--    verified row payloads instead of trusting caller-supplied list metadata.

begin;

-- Re-arm a consumed/expired/pending item only when a DIFFERENT weekly attempt records the
-- mistake. Re-submitting the same attempt remains a true idempotent no-op.
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
  select * into v_att from public.current_affairs_attempts where id = p_attempt_id;
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
    select resp.mock_question_id as qid, q.valid_until as valid_until
    from public.current_affairs_attempt_responses resp
    join public.mock_question_bank q on q.id = resp.mock_question_id
    where resp.attempt_id = p_attempt_id
      and resp.selected_option_id is not null
      and coalesce(resp.is_correct, false) = false
      and public.ca_question_current_relevant(resp.mock_question_id)
  loop
    insert into public.current_affairs_retry_items as existing (
      user_id, question_id, source_attempt_id, exam_id, due_at, expires_at, status)
    values (
      p_user, r.qid, p_attempt_id, v_att.exam_id,
      now() + interval '7 days', r.valid_until, 'pending')
    on conflict (user_id, question_id) do update
      set source_attempt_id = excluded.source_attempt_id,
          exam_id = excluded.exam_id,
          due_at = case
            when existing.status = 'pending' and existing.due_at is not null
              then least(existing.due_at, excluded.due_at)
            else excluded.due_at
          end,
          expires_at = excluded.expires_at,
          status = 'pending',
          updated_at = now()
      -- Same-attempt retries must not re-arm an item already consumed by a monthly attempt.
      where existing.source_attempt_id is distinct from excluded.source_attempt_id;
    if found then v_count := v_count + 1; end if;
  end loop;

  return v_count;
end $$;

-- Replace the landed submit RPC in place so scoring + retry enqueue commit atomically.
-- Repeating submit also heals a missing queue entry, while the source-attempt guard above
-- prevents an old weekly attempt from re-arming an already-consumed item.
create or replace function public.ca_submit_current_affairs_attempt(
  p_attempt_id uuid,
  p_user uuid
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_att public.current_affairs_attempts%rowtype;
  v_correct int := 0;
  v_wrong int := 0;
  v_unattempted int := 0;
  v_retry_enqueued int := 0;
begin
  select * into v_att from public.current_affairs_attempts where id = p_attempt_id for update;
  if not found then raise exception 'attempt_not_found' using errcode = 'P0404'; end if;
  if v_att.user_id is distinct from p_user then
    raise exception 'not_attempt_owner' using errcode = 'P0403';
  end if;

  if v_att.status = 'submitted' then
    if v_att.cadence = 'weekly' then
      v_retry_enqueued := public.ca_enqueue_weekly_retry_items(p_attempt_id, p_user);
    end if;
    return jsonb_build_object(
      'outcome', 'already_submitted', 'attempt_id', p_attempt_id,
      'cadence', v_att.cadence, 'score_raw', v_att.score_raw,
      'total_correct', v_att.total_correct,
      'total_wrong', v_att.total_wrong,
      'total_unattempted', v_att.total_unattempted,
      'retry_enqueued', v_retry_enqueued);
  end if;

  update public.current_affairs_attempt_responses r
  set is_correct = (r.selected_option_id is not null
      and r.selected_option_id::text = (r.question_snapshot->>'correct_option_id'))
  where r.attempt_id = p_attempt_id;

  select
    count(*) filter (where is_correct),
    count(*) filter (where selected_option_id is not null and not coalesce(is_correct, false)),
    count(*) filter (where selected_option_id is null)
  into v_correct, v_wrong, v_unattempted
  from public.current_affairs_attempt_responses where attempt_id = p_attempt_id;

  update public.current_affairs_attempts
  set status = 'submitted', submitted_at = now(),
      total_correct = v_correct, total_wrong = v_wrong, total_unattempted = v_unattempted,
      score_raw = v_correct
  where id = p_attempt_id;

  if v_att.cadence = 'weekly' then
    v_retry_enqueued := public.ca_enqueue_weekly_retry_items(p_attempt_id, p_user);
  end if;

  return jsonb_build_object(
    'outcome', 'submitted', 'attempt_id', p_attempt_id,
    'cadence', v_att.cadence,
    'total_correct', v_correct, 'total_wrong', v_wrong,
    'total_unattempted', v_unattempted, 'score_raw', v_correct,
    'retry_enqueued', v_retry_enqueued);
end $$;

-- Guarded entry point used by the backend. The advisory lock serializes identical
-- learner+bundle starts. Once the first request commits, a second request returns the frozen
-- attempt before inspecting its now-consumed retry items.
create or replace function public.ca_start_monthly_current_affairs_attempt_guarded(
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
  v_core uuid[];
  v_tail uuid[];
  v_all uuid[];
  v_template jsonb;
begin
  if p_user is null then raise exception 'user_required' using errcode = 'P0422'; end if;
  if p_bundle is null then raise exception 'bundle_not_found' using errcode = 'P0404'; end if;

  perform pg_advisory_xact_lock(hashtextextended(p_user::text || ':' || p_bundle::text, 0));

  select * into v_bundle from public.current_affairs_bundles where id = p_bundle for update;
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

  select exam_family_id into v_family from public.exams where id = p_exam;
  if v_bundle.exam_id is not null then
    if v_bundle.exam_id is distinct from p_exam then
      raise exception 'bundle_scope_mismatch: exam' using errcode = 'P0403';
    end if;
  elsif v_bundle.exam_family_id is not null then
    if v_family is null or v_bundle.exam_family_id is distinct from v_family then
      raise exception 'bundle_scope_mismatch: family' using errcode = 'P0403';
    end if;
  end if;

  select * into v_existing from public.current_affairs_attempts
    where user_id = p_user and bundle_id = p_bundle for update;
  if found then
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

  select array_agg((elem->>'question_id')::uuid order by ord) into v_core
    from jsonb_array_elements(coalesce(p_core_rows, '[]'::jsonb))
      with ordinality as t(elem, ord);
  select array_agg((elem->>'question_id')::uuid order by ord) into v_tail
    from jsonb_array_elements(coalesce(p_retry_rows, '[]'::jsonb))
      with ordinality as t(elem, ord);
  v_core := coalesce(v_core, array[]::uuid[]);
  v_tail := coalesce(v_tail, array[]::uuid[]);
  v_all := v_core || v_tail;

  v_template := coalesce(p_template_snapshot, '{}'::jsonb) || jsonb_build_object(
    'source', 'current_affairs_bundle',
    'practice', true,
    'practice_mode', 'monthly_current_affairs',
    'bundle_id', p_bundle,
    'cadence', v_bundle.cadence,
    'period_start', v_bundle.period_start,
    'period_end', v_bundle.period_end,
    'question_ids', to_jsonb(v_all),
    'core_question_ids', to_jsonb(v_core),
    'retry_tail_question_ids', to_jsonb(v_tail),
    'total_questions', cardinality(v_all));

  return public.ca_start_monthly_current_affairs_attempt(
    p_user, p_bundle, p_exam, v_template, p_core_rows, p_retry_rows);
end $$;

revoke all on function public.ca_start_monthly_current_affairs_attempt_guarded(
  uuid, uuid, uuid, jsonb, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.ca_start_monthly_current_affairs_attempt_guarded(
  uuid, uuid, uuid, jsonb, jsonb, jsonb) to service_role;

-- Keep the original implementation internal to the guarded wrapper.
revoke execute on function public.ca_start_monthly_current_affairs_attempt(
  uuid, uuid, uuid, jsonb, jsonb, jsonb) from service_role;

-- Reassert the existing service-role grants after CREATE OR REPLACE.
revoke all on function public.ca_enqueue_weekly_retry_items(uuid, uuid)
  from public, anon, authenticated;
revoke all on function public.ca_submit_current_affairs_attempt(uuid, uuid)
  from public, anon, authenticated;
grant execute on function public.ca_enqueue_weekly_retry_items(uuid, uuid) to service_role;
grant execute on function public.ca_submit_current_affairs_attempt(uuid, uuid) to service_role;

commit;

notify pgrst, 'reload schema';
