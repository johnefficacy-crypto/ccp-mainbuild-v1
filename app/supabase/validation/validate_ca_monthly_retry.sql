-- validate_ca_monthly_retry.sql — GQR-G6 migrations 258 + 259 + 260 VERIFY DB.
--
-- Rollback-only proof of the real PL/pgSQL authority:
--   * exact-exam retry selection and guarded monthly start;
--   * every linked claim must remain verified/current/officially grounded;
--   * monthly core+tail freeze, consume, and stale-tail reuse;
--   * weekly submit atomically enqueues mistakes;
--   * same-attempt replay is idempotent, a newer mistake re-arms, and an older
--     replay cannot overwrite the newer source;
--   * expiry stops scheduling without deleting history.
--
-- psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--   -f app/supabase/validation/validate_ca_monthly_retry.sql

begin;

insert into public.exam_families (id, slug, name)
values ('f0000000-0000-0000-0000-000000000001', 'verify-ca-family', 'VERIFY CA family');

insert into public.exams (id, slug, name, exam_family_id, exam_type, is_active)
values
  ('e0000000-0000-0000-0000-000000000001', 'verify-ca-exam-1', 'VERIFY CA exam 1',
   'f0000000-0000-0000-0000-000000000001', 'recruitment', true),
  ('e0000000-0000-0000-0000-000000000002', 'verify-ca-exam-2', 'VERIFY CA exam 2',
   'f0000000-0000-0000-0000-000000000001', 'recruitment', true);

insert into public.current_affairs_sources
  (id, name, authority_level, adapter_type, is_active)
values
  ('50000000-0000-0000-0000-000000000001', 'VERIFY official source',
   'primary_official', 'rss', true);

insert into public.current_affairs_documents
  (id, source_id, source_url, content_hash, published_at, raw_text, ingestion_status)
values
  ('d0000000-0000-0000-0000-000000000001',
   '50000000-0000-0000-0000-000000000001',
   'https://example.test/ca-doc', 'verify-ca-doc-sha', now() - interval '2 days',
   'RBI issued the verified circular.', 'snapshotted');

insert into public.current_affairs_events
  (id, canonical_title, event_date, status, relevance_from, relevance_until)
values
  ('60000000-0000-0000-0000-000000000001', 'VERIFY CA event',
   current_date - 3, 'active', current_date - 3, current_date + 30);

insert into public.current_affairs_claims
  (id, event_id, claim_text, factual_status, reviewer_status)
values
  ('70000000-0000-0000-0000-000000000001',
   '60000000-0000-0000-0000-000000000001',
   'RBI issued the verified circular.', 'current', 'verified');

insert into public.current_affairs_claim_evidence
  (claim_id, document_id, evidence_text, start_offset, end_offset, evidence_role)
values
  ('70000000-0000-0000-0000-000000000001',
   'd0000000-0000-0000-0000-000000000001',
   'RBI issued the verified circular.', 0, 33, 'primary');

-- qc = editorial monthly core; qt = retry-tail / weekly-mistake candidate.
insert into public.mock_question_bank
  (id, question_text, question_type, correct_option_id, source_kind,
   is_current_based, reviewer_status, valid_until, current_affairs_item_id)
values
  ('a1000000-0000-0000-0000-0000000000c1', 'Core question?', 'mcq',
   'b1000000-0000-0000-0000-0000000000c1', 'current_event', true,
   'verified', now() + interval '30 days',
   '60000000-0000-0000-0000-000000000001'),
  ('a1000000-0000-0000-0000-0000000000d1', 'Tail question?', 'mcq',
   'b1000000-0000-0000-0000-0000000000d1', 'current_event', true,
   'verified', now() + interval '30 days',
   '60000000-0000-0000-0000-000000000001');

insert into public.mock_question_options
  (id, question_id, option_text, option_index)
values
  ('b1000000-0000-0000-0000-0000000000c1',
   'a1000000-0000-0000-0000-0000000000c1', 'RBI', 0),
  ('b1000000-0000-0000-0000-0000000000c2',
   'a1000000-0000-0000-0000-0000000000c1', 'SEBI', 1),
  ('b1000000-0000-0000-0000-0000000000d1',
   'a1000000-0000-0000-0000-0000000000d1', 'RBI', 0),
  ('b1000000-0000-0000-0000-0000000000d2',
   'a1000000-0000-0000-0000-0000000000d1', 'SEBI', 1);

insert into public.current_affairs_question_links
  (candidate_id, event_id, claim_id, mock_question_id)
values
  (gen_random_uuid(), '60000000-0000-0000-0000-000000000001',
   '70000000-0000-0000-0000-000000000001',
   'a1000000-0000-0000-0000-0000000000c1'),
  (gen_random_uuid(), '60000000-0000-0000-0000-000000000001',
   '70000000-0000-0000-0000-000000000001',
   'a1000000-0000-0000-0000-0000000000d1');

-- Monthly bundle: add membership while draft, then publish.
insert into public.current_affairs_bundles
  (id, cadence, period_start, period_end, exam_id, reviewer_status,
   status, publish_at, available_until)
values
  ('c1000000-0000-0000-0000-0000000000e1', 'monthly',
   current_date - 30, current_date,
   'e0000000-0000-0000-0000-000000000001', 'verified', 'draft',
   now() - interval '1 day', now() + interval '10 days');

insert into public.current_affairs_bundle_questions
  (bundle_id, mock_question_id, display_order)
values
  ('c1000000-0000-0000-0000-0000000000e1',
   'a1000000-0000-0000-0000-0000000000c1', 0);

update public.current_affairs_bundles
set status = 'published'
where id = 'c1000000-0000-0000-0000-0000000000e1';

-- Two ordered weekly bundle identities for stale-replay validation.
insert into public.current_affairs_bundles
  (id, cadence, period_start, period_end, exam_id, reviewer_status,
   status, publish_at, available_until)
values
  ('c2000000-0000-0000-0000-0000000000e1', 'weekly',
   current_date - 14, current_date - 8,
   'e0000000-0000-0000-0000-000000000001', 'verified', 'published',
   now() - interval '14 days', now() + interval '10 days'),
  ('c3000000-0000-0000-0000-0000000000e1', 'weekly',
   current_date - 7, current_date - 1,
   'e0000000-0000-0000-0000-000000000001', 'verified', 'published',
   now() - interval '7 days', now() + interval '10 days');

do $$
declare
  v_exam uuid := 'e0000000-0000-0000-0000-000000000001';
  v_other_exam uuid := 'e0000000-0000-0000-0000-000000000002';
  v_monthly_user uuid := 'c0000000-0000-0000-0000-000000000001';
  v_weekly_user uuid := 'c0000000-0000-0000-0000-000000000002';
  v_foreign_user uuid := 'c0000000-0000-0000-0000-000000000003';
  v_bundle uuid := 'c1000000-0000-0000-0000-0000000000e1';
  v_qc uuid := 'a1000000-0000-0000-0000-0000000000c1';
  v_qt uuid := 'a1000000-0000-0000-0000-0000000000d1';
  v_bad_claim uuid := '70000000-0000-0000-0000-000000000002';
  v_core jsonb;
  v_tail jsonb;
  v_res jsonb;
  v_att uuid;
  v_weekly_att_old uuid := 'a2000000-0000-0000-0000-000000000001';
  v_weekly_att_new uuid := 'a2000000-0000-0000-0000-000000000002';
  v_n int;
begin
  v_core := jsonb_build_array(
    jsonb_build_object(
      'question_id', v_qc::text,
      'question_snapshot', jsonb_build_object(
        'question_text', 'Core question?',
        'correct_option_id',
          'b1000000-0000-0000-0000-0000000000c1'::text,
        'options', jsonb_build_array(
          jsonb_build_object(
            'id', 'b1000000-0000-0000-0000-0000000000c1',
            'option_text', 'RBI'),
          jsonb_build_object(
            'id', 'b1000000-0000-0000-0000-0000000000c2',
            'option_text', 'SEBI')))));
  v_tail := jsonb_build_array(
    jsonb_build_object(
      'question_id', v_qt::text,
      'question_snapshot', jsonb_build_object(
        'question_text', 'Tail question?',
        'correct_option_id',
          'b1000000-0000-0000-0000-0000000000d1'::text,
        'options', jsonb_build_array(
          jsonb_build_object(
            'id', 'b1000000-0000-0000-0000-0000000000d1',
            'option_text', 'RBI'),
          jsonb_build_object(
            'id', 'b1000000-0000-0000-0000-0000000000d2',
            'option_text', 'SEBI')))));

  -- 1. Exact-exam selector includes the owned item only for its source exam.
  insert into public.current_affairs_retry_items
    (user_id, question_id, exam_id, status, due_at, expires_at)
  values
    (v_monthly_user, v_qt, v_exam, 'pending',
     now() - interval '1 day', now() + interval '30 days');
  if not exists (
    select 1 from public.ca_eligible_retry_tail(v_monthly_user, v_exam)
    where question_id = v_qt
  ) then
    raise exception 'FAIL: exact-exam retry selector omitted eligible item';
  end if;
  if exists (
    select 1 from public.ca_eligible_retry_tail(v_monthly_user, v_other_exam)
    where question_id = v_qt
  ) then
    raise exception 'FAIL: retry selector leaked an item across exams';
  end if;

  -- 2. One valid claim cannot mask another linked claim that is not current/grounded.
  insert into public.current_affairs_claims
    (id, event_id, claim_text, factual_status, reviewer_status)
  values
    (v_bad_claim, '60000000-0000-0000-0000-000000000001',
     'Superseded linked claim.', 'superseded', 'verified');
  insert into public.current_affairs_question_links
    (candidate_id, event_id, claim_id, mock_question_id)
  values
    (gen_random_uuid(), '60000000-0000-0000-0000-000000000001',
     v_bad_claim, v_qt);
  if public.ca_question_current_relevant(v_qt) then
    raise exception 'FAIL: a good claim masked a superseded/ungrounded linked claim';
  end if;
  delete from public.current_affairs_question_links where claim_id = v_bad_claim;
  delete from public.current_affairs_claims where id = v_bad_claim;
  if not public.ca_question_current_relevant(v_qt) then
    raise exception 'FAIL: question did not recover after removing bad link';
  end if;

  -- 3. Guarded monthly start freezes core+tail and consumes the exact-exam queue row.
  v_res := public.ca_start_monthly_current_affairs_attempt_guarded(
    v_monthly_user, v_bundle, v_exam, '{}'::jsonb, v_core, v_tail);
  if v_res->>'outcome' <> 'ready'
     or (v_res->>'core_count')::int <> 1
     or (v_res->>'retry_tail_count')::int <> 1 then
    raise exception 'FAIL: guarded monthly start wrong: %', v_res;
  end if;
  v_att := (v_res->>'attempt_id')::uuid;
  if (
    select count(*) from public.current_affairs_attempt_responses
    where attempt_id = v_att and item_role = 'retry_tail'
  ) <> 1 then
    raise exception 'FAIL: retry-tail row not frozen';
  end if;
  if (
    select status from public.current_affairs_retry_items
    where user_id = v_monthly_user and question_id = v_qt
  ) <> 'consumed' then
    raise exception 'FAIL: retry item not consumed';
  end if;

  -- 4. Reusing with the now-stale original tail returns the same frozen attempt.
  v_res := public.ca_start_monthly_current_affairs_attempt_guarded(
    v_monthly_user, v_bundle, v_exam, '{}'::jsonb, v_core, v_tail);
  if v_res->>'outcome' <> 'reused'
     or (v_res->>'attempt_id')::uuid <> v_att
     or (v_res->>'retry_tail_count')::int <> 1 then
    raise exception 'FAIL: stale-tail guarded reuse failed: %', v_res;
  end if;

  -- 5. A foreign-exam retry row cannot be consumed into the exam-1 monthly bundle.
  insert into public.current_affairs_retry_items
    (user_id, question_id, exam_id, status, due_at, expires_at)
  values
    (v_foreign_user, v_qt, v_other_exam, 'pending',
     now() - interval '1 day', now() + interval '30 days');
  begin
    perform public.ca_start_monthly_current_affairs_attempt_guarded(
      v_foreign_user, v_bundle, v_exam, '{}'::jsonb, v_core, v_tail);
    raise exception 'FAIL: guarded start accepted a foreign-exam retry item';
  exception when others then
    if sqlerrm not like '%retry_tail_not_eligible%' then raise; end if;
  end;

  -- 6. OLD weekly submit atomically creates the retry item.
  insert into public.current_affairs_attempts
    (id, user_id, exam_id, bundle_id, cadence, period_start, period_end,
     status, template_snapshot, total_questions, started_at)
  values
    (v_weekly_att_old, v_weekly_user, v_exam,
     'c2000000-0000-0000-0000-0000000000e1', 'weekly',
     current_date - 14, current_date - 8,
     'in_progress', '{}'::jsonb, 1, now() - interval '14 days');
  insert into public.current_affairs_attempt_responses
    (attempt_id, mock_question_id, question_snapshot, selected_option_id, is_visited)
  values
    (v_weekly_att_old, v_qt,
     jsonb_build_object(
       'correct_option_id',
         'b1000000-0000-0000-0000-0000000000d1'::text,
       'options', jsonb_build_array()),
     'b1000000-0000-0000-0000-0000000000d2', true);
  v_res := public.ca_submit_current_affairs_attempt(v_weekly_att_old, v_weekly_user);
  if v_res->>'outcome' <> 'submitted'
     or (v_res->>'retry_enqueued')::int <> 1 then
    raise exception 'FAIL: old weekly submit did not enqueue retry: %', v_res;
  end if;

  -- Same-attempt replay cannot re-arm after consumption.
  update public.current_affairs_retry_items
  set status = 'consumed'
  where user_id = v_weekly_user and question_id = v_qt;
  v_res := public.ca_submit_current_affairs_attempt(v_weekly_att_old, v_weekly_user);
  if v_res->>'outcome' <> 'already_submitted'
     or (v_res->>'retry_enqueued')::int <> 0 then
    raise exception 'FAIL: same-attempt replay was not idempotent: %', v_res;
  end if;

  -- 7. A NEWER weekly mistake re-arms and owns the queue row.
  insert into public.current_affairs_attempts
    (id, user_id, exam_id, bundle_id, cadence, period_start, period_end,
     status, template_snapshot, total_questions, started_at)
  values
    (v_weekly_att_new, v_weekly_user, v_exam,
     'c3000000-0000-0000-0000-0000000000e1', 'weekly',
     current_date - 7, current_date - 1,
     'in_progress', '{}'::jsonb, 1, now() - interval '7 days');
  insert into public.current_affairs_attempt_responses
    (attempt_id, mock_question_id, question_snapshot, selected_option_id, is_visited)
  values
    (v_weekly_att_new, v_qt,
     jsonb_build_object(
       'correct_option_id',
         'b1000000-0000-0000-0000-0000000000d1'::text,
       'options', jsonb_build_array()),
     'b1000000-0000-0000-0000-0000000000d2', true);
  v_res := public.ca_submit_current_affairs_attempt(v_weekly_att_new, v_weekly_user);
  if (v_res->>'retry_enqueued')::int <> 1 then
    raise exception 'FAIL: newer weekly mistake did not re-arm retry: %', v_res;
  end if;
  if not exists (
    select 1 from public.current_affairs_retry_items
    where user_id = v_weekly_user and question_id = v_qt
      and source_attempt_id = v_weekly_att_new and status = 'pending'
      and source_period_end = current_date - 1
  ) then
    raise exception 'FAIL: re-armed retry row has wrong source/order metadata';
  end if;

  -- Delayed replay of the OLD attempt must not replace or re-arm the NEW source.
  v_res := public.ca_submit_current_affairs_attempt(v_weekly_att_old, v_weekly_user);
  if (v_res->>'retry_enqueued')::int <> 0 then
    raise exception 'FAIL: older replay reported a queue mutation: %', v_res;
  end if;
  if not exists (
    select 1 from public.current_affairs_retry_items
    where user_id = v_weekly_user and question_id = v_qt
      and source_attempt_id = v_weekly_att_new and status = 'pending'
  ) then
    raise exception 'FAIL: older replay overwrote the newer retry source';
  end if;

  -- 8. Sweep marks stale pending rows expired and never deletes them.
  insert into public.current_affairs_retry_items
    (user_id, question_id, exam_id, status, expires_at)
  values
    (v_monthly_user, v_qc, v_exam, 'pending', now() - interval '1 day');
  v_n := public.ca_sweep_expired_retry_items();
  if v_n < 1 then raise exception 'FAIL: sweep expired nothing'; end if;
  if (
    select status from public.current_affairs_retry_items
    where user_id = v_monthly_user and question_id = v_qc
  ) <> 'expired' then
    raise exception 'FAIL: stale retry item not marked expired';
  end if;

  raise notice 'validate_ca_monthly_retry: ALL CHECKS PASSED';
end $$;

rollback;
