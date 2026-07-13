-- validate_ca_monthly_retry.sql — GQR-G6 migrations 258 + 259 VERIFY DB.
--
-- Exercises the real PL/pgSQL that SBStub cannot prove:
--   * monthly eligible-tail selection + guarded core/tail start;
--   * stale-tail idempotent reuse after the first start consumed the item;
--   * weekly submit atomically creates retry items;
--   * the same submit stays idempotent after consumption;
--   * a NEW weekly mistake re-arms the consumed item;
--   * expiry marks pending rows expired without deleting history.
-- Rollback-only.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_monthly_retry.sql

begin;

insert into public.exam_families (id, slug, name)
values ('f0000000-0000-0000-0000-000000000001', 'verify-fam', 'VERIFY family')
on conflict (id) do nothing;
insert into public.exams (id, slug, name, exam_family_id, exam_type, is_active)
values ('e0000000-0000-0000-0000-000000000001', 'verify-exam', 'VERIFY exam',
        'f0000000-0000-0000-0000-000000000001', 'recruitment', true)
on conflict (id) do nothing;
insert into public.current_affairs_sources
  (id, name, authority_level, adapter_type, is_active)
values
  ('50000000-0000-0000-0000-000000000001', 'VERIFY source',
   'primary_official', 'rss', true);
insert into public.current_affairs_documents
  (id, source_id, source_url, content_hash, published_at, raw_text, ingestion_status)
values
  ('d0000000-0000-0000-0000-000000000001',
   '50000000-0000-0000-0000-000000000001',
   'https://example.test/doc', 'sha-m-1', now() - interval '2 days',
   'RBI circular.', 'snapshotted');
insert into public.current_affairs_events
  (id, canonical_title, event_date, status, relevance_from, relevance_until)
values
  ('60000000-0000-0000-0000-000000000001', 'VERIFY event',
   current_date - 3, 'active', current_date - 3, current_date + 30);
insert into public.current_affairs_claims
  (id, event_id, claim_text, factual_status, reviewer_status)
values
  ('70000000-0000-0000-0000-000000000001',
   '60000000-0000-0000-0000-000000000001',
   'RBI circular.', 'current', 'verified');
insert into public.current_affairs_claim_evidence
  (claim_id, document_id, evidence_text, start_offset, end_offset, evidence_role)
values
  ('70000000-0000-0000-0000-000000000001',
   'd0000000-0000-0000-0000-000000000001',
   'RBI circular.', 0, 12, 'primary');

-- qc = monthly core; qt = retry-tail / weekly-mistake candidate.
insert into public.mock_question_bank
  (id, question_text, question_type, correct_option_id, source_kind,
   is_current_based, reviewer_status, valid_until, current_affairs_item_id)
values
  ('a1000000-0000-0000-0000-0000000000c1', 'Core Q?', 'mcq',
   'b1000000-0000-0000-0000-0000000000c1', 'current_event', true,
   'verified', now() + interval '30 days',
   '60000000-0000-0000-0000-000000000001'),
  ('a1000000-0000-0000-0000-0000000000d1', 'Tail Q?', 'mcq',
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

-- Two weekly bundle identities for repeated-mistake re-arm validation.
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
  v_monthly_user uuid := 'c0000000-0000-0000-0000-000000000001';
  v_weekly_user uuid := 'c0000000-0000-0000-0000-000000000002';
  v_bundle uuid := 'c1000000-0000-0000-0000-0000000000e1';
  v_qc uuid := 'a1000000-0000-0000-0000-0000000000c1';
  v_qt uuid := 'a1000000-0000-0000-0000-0000000000d1';
  v_core jsonb;
  v_tail jsonb;
  v_res jsonb;
  v_att uuid;
  v_weekly_att_1 uuid := 'a2000000-0000-0000-0000-000000000001';
  v_weekly_att_2 uuid := 'a2000000-0000-0000-0000-000000000002';
  v_n int;
begin
  v_core := jsonb_build_array(
    jsonb_build_object(
      'question_id', v_qc::text,
      'question_snapshot', jsonb_build_object(
        'question_text', 'Core Q?',
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
        'question_text', 'Tail Q?',
        'correct_option_id',
          'b1000000-0000-0000-0000-0000000000d1'::text,
        'options', jsonb_build_array(
          jsonb_build_object(
            'id', 'b1000000-0000-0000-0000-0000000000d1',
            'option_text', 'RBI'),
          jsonb_build_object(
            'id', 'b1000000-0000-0000-0000-0000000000d2',
            'option_text', 'SEBI')))));

  -- 1. Pending relevant retry item is selectable.
  insert into public.current_affairs_retry_items
    (user_id, question_id, status, due_at, expires_at)
  values
    (v_monthly_user, v_qt, 'pending',
     now() - interval '1 day', now() + interval '30 days');
  if not exists (
    select 1 from public.ca_eligible_retry_tail(v_monthly_user)
    where question_id = v_qt
  ) then
    raise exception 'FAIL: eligible tail did not surface relevant pending item';
  end if;

  -- 2. Guarded monthly start freezes core+tail and consumes the queue row.
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

  -- 3. Reusing with the original now-stale tail returns the frozen attempt before
  --    tail re-validation; this is the race/idempotency guarantee from migration 259.
  v_res := public.ca_start_monthly_current_affairs_attempt_guarded(
    v_monthly_user, v_bundle, v_exam, '{}'::jsonb, v_core, v_tail);
  if v_res->>'outcome' <> 'reused'
     or (v_res->>'attempt_id')::uuid <> v_att
     or (v_res->>'retry_tail_count')::int <> 1 then
    raise exception 'FAIL: stale-tail guarded reuse failed: %', v_res;
  end if;

  -- 4. Weekly submit scores and creates the retry item in the SAME RPC transaction.
  insert into public.current_affairs_attempts
    (id, user_id, exam_id, bundle_id, cadence, status,
     template_snapshot, total_questions)
  values
    (v_weekly_att_1, v_weekly_user, v_exam,
     'c2000000-0000-0000-0000-0000000000e1',
     'weekly', 'in_progress', '{}'::jsonb, 1);
  insert into public.current_affairs_attempt_responses
    (attempt_id, mock_question_id, question_snapshot, selected_option_id,
     is_visited)
  values
    (v_weekly_att_1, v_qt,
     jsonb_build_object(
       'correct_option_id',
         'b1000000-0000-0000-0000-0000000000d1'::text,
       'options', jsonb_build_array()),
     'b1000000-0000-0000-0000-0000000000d2', true);
  v_res := public.ca_submit_current_affairs_attempt(
    v_weekly_att_1, v_weekly_user);
  if v_res->>'outcome' <> 'submitted'
     or (v_res->>'retry_enqueued')::int <> 1 then
    raise exception 'FAIL: weekly submit did not enqueue retry: %', v_res;
  end if;
  if not exists (
    select 1 from public.current_affairs_retry_items
    where user_id = v_weekly_user and question_id = v_qt
      and source_attempt_id = v_weekly_att_1 and status = 'pending'
  ) then
    raise exception 'FAIL: weekly submit retry row missing';
  end if;

  -- 5. Same-attempt retry cannot re-arm an item consumed after that submit.
  update public.current_affairs_retry_items
  set status = 'consumed'
  where user_id = v_weekly_user and question_id = v_qt;
  v_res := public.ca_submit_current_affairs_attempt(
    v_weekly_att_1, v_weekly_user);
  if v_res->>'outcome' <> 'already_submitted'
     or (v_res->>'retry_enqueued')::int <> 0 then
    raise exception 'FAIL: repeated weekly submit was not idempotent: %', v_res;
  end if;
  if (
    select status from public.current_affairs_retry_items
    where user_id = v_weekly_user and question_id = v_qt
  ) <> 'consumed' then
    raise exception 'FAIL: same attempt re-armed consumed retry item';
  end if;

  -- 6. A NEW weekly mistake for the same question re-arms that queue item.
  insert into public.current_affairs_attempts
    (id, user_id, exam_id, bundle_id, cadence, status,
     template_snapshot, total_questions)
  values
    (v_weekly_att_2, v_weekly_user, v_exam,
     'c3000000-0000-0000-0000-0000000000e1',
     'weekly', 'in_progress', '{}'::jsonb, 1);
  insert into public.current_affairs_attempt_responses
    (attempt_id, mock_question_id, question_snapshot, selected_option_id,
     is_visited)
  values
    (v_weekly_att_2, v_qt,
     jsonb_build_object(
       'correct_option_id',
         'b1000000-0000-0000-0000-0000000000d1'::text,
       'options', jsonb_build_array()),
     'b1000000-0000-0000-0000-0000000000d2', true);
  v_res := public.ca_submit_current_affairs_attempt(
    v_weekly_att_2, v_weekly_user);
  if (v_res->>'retry_enqueued')::int <> 1 then
    raise exception 'FAIL: new weekly mistake did not re-arm retry: %', v_res;
  end if;
  if not exists (
    select 1 from public.current_affairs_retry_items
    where user_id = v_weekly_user and question_id = v_qt
      and source_attempt_id = v_weekly_att_2 and status = 'pending'
  ) then
    raise exception 'FAIL: re-armed retry row has wrong source/status';
  end if;

  -- 7. Sweep expires stale pending rows and never deletes them.
  insert into public.current_affairs_retry_items
    (user_id, question_id, status, expires_at)
  values
    (v_monthly_user, v_qc, 'pending', now() - interval '1 day');
  v_n := public.ca_sweep_expired_retry_items();
  if v_n < 1 then
    raise exception 'FAIL: sweep expired nothing';
  end if;
  if (
    select status from public.current_affairs_retry_items
    where user_id = v_monthly_user and question_id = v_qc
  ) <> 'expired' then
    raise exception 'FAIL: stale retry item not marked expired';
  end if;

  raise notice 'validate_ca_monthly_retry: ALL CHECKS PASSED';
end $$;

rollback;
