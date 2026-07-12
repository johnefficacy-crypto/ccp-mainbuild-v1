-- validate_ca_promotion_rpcs.sql — GQR-G4a VERIFY DB.
--
-- Executes the migration 248 PL/pgSQL the unit tests (router-only) cannot: the
-- review transition (CAS + audit), the audited promotion into mock_question_bank
-- (current_event isolation + options + correct option + provenance link + candidate
-- terminal state + audit), and the guards (CAS conflict, non-approved reject).
-- Rollback-only; leaves no data.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_promotion_rpcs.sql

begin;

insert into public.current_affairs_events (id, canonical_title, event_date, status, relevance_from, relevance_until)
values ('cccccccc-0000-0000-0000-000000000001', 'VERIFY event', '2026-06-01', 'active',
        '2026-06-01', current_date + 30);

insert into public.current_affairs_question_candidates (id, event_id, question_payload, question_fingerprint, status)
values ('dddddddd-0000-0000-0000-000000000001', 'cccccccc-0000-0000-0000-000000000001',
        jsonb_build_object(
          'stem', 'Which body issued the June 2026 circular?',
          'explanation', 'RBI per the cited claim.',
          'difficulty', 'medium',
          'correct_option_id', 'a',
          'resolved_claim_ids', jsonb_build_array(),
          'options', jsonb_build_array(
            jsonb_build_object('id','a','text','RBI'),
            jsonb_build_object('id','b','text','SEBI'),
            jsonb_build_object('id','c','text','IRDAI'),
            jsonb_build_object('id','d','text','PFRDA'))),
        'verify-promote-1', 'review_ready');

do $$
declare
  v_actor uuid := gen_random_uuid();
  v_res jsonb;
  v_mq uuid;
  v_bank public.mock_question_bank%rowtype;
  v_opt_count int;
  v_correct_ok boolean;
  v_link_count int;
  v_cand_status text;
begin
  -- review: review_ready -> approved
  v_res := public.ca_review_candidate('dddddddd-0000-0000-0000-000000000001',
             'review_ready', 'approved', null, v_actor, 'op@example.com');
  if v_res->>'new_status' <> 'approved' then raise exception 'FAIL review: %', v_res; end if;
  raise notice 'PASS review review_ready->approved';

  -- CAS conflict: replaying the same expected_status must 409.
  begin
    perform public.ca_review_candidate('dddddddd-0000-0000-0000-000000000001',
              'review_ready', 'approved', null, v_actor, 'op@example.com');
    raise exception 'FAIL: stale expected_status should conflict';
  exception when others then
    if sqlerrm not like 'concurrent_modification%' then raise;
    raise notice 'PASS review CAS conflict';
  end;

  -- promote: approved -> bank row (current_event) + options + link + candidate promoted
  v_res := public.ca_promote_candidate('dddddddd-0000-0000-0000-000000000001',
             'approved', v_actor, 'op@example.com');
  v_mq := (v_res->>'mock_question_id')::uuid;
  if v_mq is null then raise exception 'FAIL promote: %', v_res; end if;

  select * into v_bank from public.mock_question_bank where id = v_mq;
  if v_bank.source_kind <> 'current_event' or not v_bank.is_current_based
     or v_bank.current_affairs_item_id <> 'cccccccc-0000-0000-0000-000000000001' then
    raise exception 'FAIL bank isolation: kind=% cur=% item=%',
      v_bank.source_kind, v_bank.is_current_based, v_bank.current_affairs_item_id;
  end if;
  select count(*) into v_opt_count from public.mock_question_options where question_id = v_mq;
  select exists(select 1 from public.mock_question_options
    where id = v_bank.correct_option_id and question_id = v_mq and is_correct) into v_correct_ok;
  if v_opt_count <> 4 or not v_correct_ok then
    raise exception 'FAIL options: count=% correct_ok=%', v_opt_count, v_correct_ok;
  end if;
  select count(*) into v_link_count from public.current_affairs_question_links
    where mock_question_id = v_mq and candidate_id = 'dddddddd-0000-0000-0000-000000000001';
  select status into v_cand_status from public.current_affairs_question_candidates
    where id = 'dddddddd-0000-0000-0000-000000000001';
  if v_link_count <> 1 or v_cand_status <> 'promoted' then
    raise exception 'FAIL link/terminal: link=% status=%', v_link_count, v_cand_status;
  end if;
  raise notice 'PASS promote (bank current_event + 4 options + correct + link + promoted)';

  -- audit rows: transition + promotion
  if (select count(*) from public.admin_audit_logs
      where entity_id = 'dddddddd-0000-0000-0000-000000000001'
        and action in ('ca_candidate_status_transition','ca_candidate_promoted')) < 2 then
    raise exception 'FAIL audit rows missing';
  end if;
  raise notice 'PASS audit lineage';

  -- re-promote must fail (candidate no longer approved).
  begin
    perform public.ca_promote_candidate('dddddddd-0000-0000-0000-000000000001',
              'approved', v_actor, 'op@example.com');
    raise exception 'FAIL: re-promote should reject non-approved candidate';
  exception when others then
    if sqlerrm not like 'concurrent_modification%' and sqlerrm not like 'candidate_not_approved%' then raise;
    raise notice 'PASS re-promote rejected';
  end;

  raise notice 'ALL PASS';
end $$;

rollback;
