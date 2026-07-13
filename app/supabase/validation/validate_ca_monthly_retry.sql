-- validate_ca_monthly_retry.sql — GQR-G6 VERIFY DB.
--
-- Exercises the migration 257 PL/pgSQL the unit tests (SBStub-emulated) cannot run for
-- real: the eligible-tail selector, the monthly core+tail start (scope + core degradation
-- + tail overlap/eligibility + per-row bank content verification + consume), idempotent
-- reuse, and the retry-item expiry sweep. Rollback-only.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_monthly_retry.sql

begin;

insert into public.exam_families (id, slug, name)
values ('f0000000-0000-0000-0000-000000000001', 'verify-fam', 'VERIFY family') on conflict (id) do nothing;
insert into public.exams (id, slug, name, exam_family_id, exam_type, is_active)
values ('e0000000-0000-0000-0000-000000000001', 'verify-exam', 'VERIFY exam',
        'f0000000-0000-0000-0000-000000000001', 'recruitment', true) on conflict (id) do nothing;
insert into public.current_affairs_sources (id, name, authority_level, adapter_type, is_active)
values ('50000000-0000-0000-0000-000000000001', 'VERIFY source', 'primary_official', 'rss', true);
insert into public.current_affairs_documents (id, source_id, source_url, content_hash, published_at, raw_text, ingestion_status)
values ('d0000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001',
        'https://example.test/doc', 'sha-m-1', now() - interval '2 days', 'RBI circular.', 'snapshotted');
insert into public.current_affairs_events (id, canonical_title, event_date, status, relevance_from, relevance_until)
values ('60000000-0000-0000-0000-000000000001', 'VERIFY event', current_date - 3, 'active', current_date - 3, current_date + 30);
insert into public.current_affairs_claims (id, event_id, claim_text, factual_status, reviewer_status)
values ('70000000-0000-0000-0000-000000000001', '60000000-0000-0000-0000-000000000001', 'RBI circular.', 'current', 'verified');
insert into public.current_affairs_claim_evidence (claim_id, document_id, evidence_text, start_offset, end_offset, evidence_role)
values ('70000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', 'RBI circular.', 0, 12, 'primary');

-- Two promoted current-event questions: qc (monthly core) and qt (a retry-tail candidate).
insert into public.mock_question_bank
  (id, question_text, question_type, correct_option_id, source_kind, is_current_based, reviewer_status,
   valid_until, current_affairs_item_id)
values
  ('a1000000-0000-0000-0000-0000000000c1', 'Core Q?', 'mcq', 'b1000000-0000-0000-0000-0000000000c1',
   'current_event', true, 'verified', now() + interval '30 days', '60000000-0000-0000-0000-000000000001'),
  ('a1000000-0000-0000-0000-0000000000d1', 'Tail Q?', 'mcq', 'b1000000-0000-0000-0000-0000000000d1',
   'current_event', true, 'verified', now() + interval '30 days', '60000000-0000-0000-0000-000000000001');
insert into public.mock_question_options (id, question_id, option_text, option_index) values
  ('b1000000-0000-0000-0000-0000000000c1', 'a1000000-0000-0000-0000-0000000000c1', 'RBI', 0),
  ('b1000000-0000-0000-0000-0000000000c2', 'a1000000-0000-0000-0000-0000000000c1', 'SEBI', 1),
  ('b1000000-0000-0000-0000-0000000000d1', 'a1000000-0000-0000-0000-0000000000d1', 'RBI', 0),
  ('b1000000-0000-0000-0000-0000000000d2', 'a1000000-0000-0000-0000-0000000000d1', 'SEBI', 1);
insert into public.current_affairs_question_links (candidate_id, event_id, claim_id, mock_question_id) values
  (gen_random_uuid(), '60000000-0000-0000-0000-000000000001', '70000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-0000000000c1'),
  (gen_random_uuid(), '60000000-0000-0000-0000-000000000001', '70000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-0000000000d1');

-- Monthly bundle (draft → add core member → publish; membership is locked once published).
insert into public.current_affairs_bundles
  (id, cadence, period_start, period_end, exam_id, reviewer_status, status, publish_at, available_until)
values ('c1000000-0000-0000-0000-0000000000e1', 'monthly', current_date - 30, current_date,
        'e0000000-0000-0000-0000-000000000001', 'verified', 'draft', now() - interval '1 day', now() + interval '10 days');
insert into public.current_affairs_bundle_questions (bundle_id, mock_question_id, display_order)
values ('c1000000-0000-0000-0000-0000000000e1', 'a1000000-0000-0000-0000-0000000000c1', 0);
update public.current_affairs_bundles set status = 'published' where id = 'c1000000-0000-0000-0000-0000000000e1';

do $$
declare
  v_exam uuid := 'e0000000-0000-0000-0000-000000000001';
  v_user uuid := 'c0000000-0000-0000-0000-000000000001';
  v_bundle uuid := 'c1000000-0000-0000-0000-0000000000e1';
  v_qc uuid := 'a1000000-0000-0000-0000-0000000000c1';
  v_qt uuid := 'a1000000-0000-0000-0000-0000000000d1';
  v_core jsonb;
  v_tail jsonb;
  v_res jsonb;
  v_att uuid;
  v_n int;
begin
  v_core := jsonb_build_array(jsonb_build_object('question_id', v_qc::text, 'question_snapshot',
    jsonb_build_object('question_text', 'Core Q?', 'correct_option_id', 'b1000000-0000-0000-0000-0000000000c1'::text,
      'options', jsonb_build_array(
        jsonb_build_object('id', 'b1000000-0000-0000-0000-0000000000c1', 'option_text', 'RBI'),
        jsonb_build_object('id', 'b1000000-0000-0000-0000-0000000000c2', 'option_text', 'SEBI')))));
  v_tail := jsonb_build_array(jsonb_build_object('question_id', v_qt::text, 'question_snapshot',
    jsonb_build_object('question_text', 'Tail Q?', 'correct_option_id', 'b1000000-0000-0000-0000-0000000000d1'::text,
      'options', jsonb_build_array(
        jsonb_build_object('id', 'b1000000-0000-0000-0000-0000000000d1', 'option_text', 'RBI'),
        jsonb_build_object('id', 'b1000000-0000-0000-0000-0000000000d2', 'option_text', 'SEBI')))));

  -- 1. Seed a pending retry item for the learner (qt).
  insert into public.current_affairs_retry_items (user_id, question_id, status, due_at, expires_at)
  values (v_user, v_qt, 'pending', now() - interval '1 day', now() + interval '30 days');

  -- 2. Eligible-tail selector returns the relevant pending item.
  if not exists (select 1 from public.ca_eligible_retry_tail(v_user) where question_id = v_qt) then
    raise exception 'FAIL: eligible tail did not surface the pending relevant item';
  end if;

  -- 3. Tail overlapping the core is rejected.
  begin
    perform public.ca_start_monthly_current_affairs_attempt(v_user, v_bundle, v_exam, '{}'::jsonb, v_core,
      jsonb_build_array(jsonb_build_object('question_id', v_qc::text,
        'question_snapshot', v_core->0->'question_snapshot')));
    raise exception 'FAIL: tail overlapping core accepted';
  exception when others then
    if sqlerrm not like '%retry_tail_overlaps_core%' then raise; end if;
  end;

  -- 4. Happy monthly start: core + tail frozen, tail item consumed.
  v_res := public.ca_start_monthly_current_affairs_attempt(v_user, v_bundle, v_exam, '{}'::jsonb, v_core, v_tail);
  if v_res->>'outcome' <> 'ready' or (v_res->>'core_count')::int <> 1 or (v_res->>'retry_tail_count')::int <> 1 then
    raise exception 'FAIL: monthly start wrong: %', v_res;
  end if;
  v_att := (v_res->>'attempt_id')::uuid;
  if (select count(*) from public.current_affairs_attempt_responses where attempt_id = v_att and item_role = 'retry_tail') <> 1 then
    raise exception 'FAIL: retry_tail row not frozen';
  end if;
  if (select status from public.current_affairs_retry_items where user_id = v_user and question_id = v_qt) <> 'consumed' then
    raise exception 'FAIL: retry item not consumed';
  end if;

  -- 5. Idempotent reuse.
  v_res := public.ca_start_monthly_current_affairs_attempt(v_user, v_bundle, v_exam, '{}'::jsonb, v_core, '[]'::jsonb);
  if v_res->>'outcome' <> 'reused' or (v_res->>'attempt_id')::uuid <> v_att then
    raise exception 'FAIL: monthly start not idempotent: %', v_res;
  end if;

  -- 6. Sweep expires a stale pending item (past expires_at); never deletes.
  insert into public.current_affairs_retry_items (user_id, question_id, status, expires_at)
  values (v_user, v_qc, 'pending', now() - interval '1 day');
  v_n := public.ca_sweep_expired_retry_items();
  if v_n < 1 then raise exception 'FAIL: sweep expired nothing'; end if;
  if (select status from public.current_affairs_retry_items where user_id = v_user and question_id = v_qc) <> 'expired' then
    raise exception 'FAIL: stale item not marked expired';
  end if;

  raise notice 'validate_ca_monthly_retry: ALL CHECKS PASSED';
end $$;

rollback;
