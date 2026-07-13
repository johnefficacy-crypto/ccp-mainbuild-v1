-- validate_ca_promotion_rpcs.sql — GQR-G4a VERIFY DB (checkpost #970).
--
-- Executes the migration 249+251 PL/pgSQL the unit tests (router-only) cannot: the
-- review transition (dual CAS status + updated_at + reason + audit), the audited
-- promotion into mock_question_bank (current_event isolation + options + correct
-- option + one provenance link PER claim + audit), the Stage-D REVALIDATION gates
-- (validation ok, evidence/claim/source integrity, structural payload), and the
-- content-token / non-approved rejections. Seeds a real auth.users actor so the
-- created_by/last_reviewed_by FKs resolve. Rollback-only; leaves no data.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_promotion_rpcs.sql

begin;

-- Real actor (created_by / last_reviewed_by / reviewed_by FK -> auth.users).
insert into auth.users (id, instance_id, aud, role, email)
values ('eeeeeeee-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
        'ca-verify@example.com')
on conflict (id) do nothing;

-- Evidence chain: authoritative source -> document -> event -> current claim -> evidence.
insert into public.current_affairs_sources (id, name, authority_level, adapter_type, is_active)
values ('aaaaaaaa-0000-0000-0000-000000000001', 'VERIFY source', 'primary_official', 'rss', true);
insert into public.current_affairs_documents (id, source_id, source_url, raw_text, ingestion_status)
values ('bbbbbbbb-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001',
        'https://example.test/doc', 'RBI issued a digital lending circular.', 'snapshotted');
insert into public.current_affairs_events (id, canonical_title, event_date, status, relevance_from, relevance_until)
values ('cccccccc-0000-0000-0000-000000000001', 'VERIFY event', '2026-06-01', 'active',
        '2026-06-01', current_date + 30);
insert into public.current_affairs_claims (id, event_id, claim_text, factual_status, reviewer_status)
values ('ffffffff-0000-0000-0000-000000000001', 'cccccccc-0000-0000-0000-000000000001',
        'RBI issued a digital lending circular.', 'current', 'verified');
insert into public.current_affairs_claim_evidence (claim_id, document_id, evidence_text, start_offset, end_offset, evidence_role)
values ('ffffffff-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000001',
        'RBI issued a digital lending circular.', 0, 38, 'primary');

insert into public.current_affairs_question_candidates (id, event_id, question_payload, question_fingerprint, status, validation_result)
values ('dddddddd-0000-0000-0000-000000000001', 'cccccccc-0000-0000-0000-000000000001',
        jsonb_build_object(
          'stem', 'Which body issued the June 2026 digital lending circular?',
          'explanation', 'RBI per the cited claim.',
          'difficulty', 'medium',
          'correct_option_id', 'a',
          'resolved_claim_ids', jsonb_build_array('ffffffff-0000-0000-0000-000000000001'),
          'options', jsonb_build_array(
            jsonb_build_object('id','a','text','RBI'),
            jsonb_build_object('id','b','text','SEBI'),
            jsonb_build_object('id','c','text','IRDAI'),
            jsonb_build_object('id','d','text','PFRDA'))),
        'verify-promote-1', 'review_ready', jsonb_build_object('ok', true));

do $$
declare
  v_actor uuid := 'eeeeeeee-0000-0000-0000-000000000001';
  v_cid uuid := 'dddddddd-0000-0000-0000-000000000001';
  v_tok timestamptz;
  v_res jsonb;
  v_mq uuid;
  v_bank public.mock_question_bank%rowtype;
  v_opt_count int;
  v_correct_ok boolean;
  v_link_count int;
  v_cand_status text;
begin
  select updated_at into v_tok from public.current_affairs_question_candidates where id = v_cid;

  -- reason gate: too-short reason is rejected.
  begin
    perform public.ca_review_candidate(v_cid, 'review_ready', v_tok, 'approved', 'short', null, v_actor, 'op@example.com');
    raise exception 'FAIL: short reason should be rejected';
  exception when others then
    if sqlerrm not like 'invalid_reason%' then raise;
    raise notice 'PASS review reason gate';
  end;

  -- content-token CAS: a stale updated_at loses.
  begin
    perform public.ca_review_candidate(v_cid, 'review_ready', now() - interval '1 day', 'approved',
      'a valid audit reason', null, v_actor, 'op@example.com');
    raise exception 'FAIL: stale content token should conflict';
  exception when others then
    if sqlerrm not like 'concurrent_modification%' then raise;
    raise notice 'PASS review content-token CAS';
  end;

  -- review review_ready -> approved
  v_res := public.ca_review_candidate(v_cid, 'review_ready', v_tok, 'approved',
             'accurate and current', null, v_actor, 'op@example.com');
  if v_res->>'new_status' <> 'approved' then raise exception 'FAIL review: %', v_res; end if;
  raise notice 'PASS review review_ready->approved';

  select updated_at into v_tok from public.current_affairs_question_candidates where id = v_cid;

  -- promote: approved -> bank (current_event) + options + link + candidate promoted
  v_res := public.ca_promote_candidate(v_cid, 'approved', v_tok, 'evidence checks out', v_actor, 'op@example.com');
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
  select count(*) into v_link_count from public.current_affairs_question_links
    where mock_question_id = v_mq and candidate_id = v_cid;
  select status into v_cand_status from public.current_affairs_question_candidates where id = v_cid;
  if v_opt_count <> 4 or not v_correct_ok or v_link_count <> 1 or v_cand_status <> 'promoted' then
    raise exception 'FAIL promote artefacts: opts=% correct=% links=% status=%',
      v_opt_count, v_correct_ok, v_link_count, v_cand_status;
  end if;
  if (select count(*) from public.admin_audit_logs where entity_id = v_cid
      and action in ('ca_candidate_status_transition','ca_candidate_promoted')) < 2 then
    raise exception 'FAIL audit rows missing';
  end if;
  raise notice 'PASS promote (current_event + 4 opts + correct + per-claim link + audit)';

  -- re-promote must fail (candidate no longer approved).
  begin
    perform public.ca_promote_candidate(v_cid, 'approved', v_tok, 'evidence checks out', v_actor, 'op@example.com');
    raise exception 'FAIL: re-promote should reject';
  exception when others then
    if sqlerrm not like 'concurrent_modification%' and sqlerrm not like 'candidate_not_approved%' then raise;
    raise notice 'PASS re-promote rejected';
  end;
end $$;

-- ── F4 negatives: evidence-free and discovery_only-only candidates must NOT promote ──
insert into public.current_affairs_question_candidates (id, event_id, question_payload, question_fingerprint, status, validation_result)
values ('dddddddd-0000-0000-0000-000000000002', 'cccccccc-0000-0000-0000-000000000001',
        jsonb_build_object('stem','Q?','explanation','x','correct_option_id','a',
          'resolved_claim_ids', jsonb_build_array(),
          'options', jsonb_build_array(
            jsonb_build_object('id','a','text','RBI'), jsonb_build_object('id','b','text','SEBI'),
            jsonb_build_object('id','c','text','IRDAI'), jsonb_build_object('id','d','text','PFRDA'))),
        'verify-promote-2', 'approved', jsonb_build_object('ok', true));

do $$
declare
  v_actor uuid := 'eeeeeeee-0000-0000-0000-000000000001';
  v_cid uuid := 'dddddddd-0000-0000-0000-000000000002';
  v_tok timestamptz;
begin
  select updated_at into v_tok from public.current_affairs_question_candidates where id = v_cid;
  begin
    perform public.ca_promote_candidate(v_cid, 'approved', v_tok, 'attempt evidence-free', v_actor, 'op@example.com');
    raise exception 'FAIL: evidence-free candidate must not promote';
  exception when others then
    if sqlerrm not like 'no_linked_claim%' then raise;
    raise notice 'PASS promote rejects evidence-free candidate (F4)';
  end;
end $$;

-- discovery_only sole source: a claim backed only by a discovery_only source.
insert into public.current_affairs_sources (id, name, authority_level, adapter_type, is_active)
values ('aaaaaaaa-0000-0000-0000-000000000002', 'aggregator', 'discovery_only', 'rss', true);
insert into public.current_affairs_documents (id, source_id, source_url, raw_text, ingestion_status)
values ('bbbbbbbb-0000-0000-0000-000000000002', 'aaaaaaaa-0000-0000-0000-000000000002',
        'https://aggregator.test/x', 'aggregated blurb', 'snapshotted');
insert into public.current_affairs_claims (id, event_id, claim_text, factual_status, reviewer_status)
values ('ffffffff-0000-0000-0000-000000000002', 'cccccccc-0000-0000-0000-000000000001',
        'aggregated claim', 'current', 'pending');
insert into public.current_affairs_claim_evidence (claim_id, document_id, evidence_text, start_offset, end_offset, evidence_role)
values ('ffffffff-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000002', 'blurb', 0, 5, 'supporting');
insert into public.current_affairs_question_candidates (id, event_id, question_payload, question_fingerprint, status, validation_result)
values ('dddddddd-0000-0000-0000-000000000003', 'cccccccc-0000-0000-0000-000000000001',
        jsonb_build_object('stem','Q?','explanation','x','correct_option_id','a',
          'resolved_claim_ids', jsonb_build_array('ffffffff-0000-0000-0000-000000000002'),
          'options', jsonb_build_array(
            jsonb_build_object('id','a','text','RBI'), jsonb_build_object('id','b','text','SEBI'),
            jsonb_build_object('id','c','text','IRDAI'), jsonb_build_object('id','d','text','PFRDA'))),
        'verify-promote-3', 'approved', jsonb_build_object('ok', true));

do $$
declare
  v_actor uuid := 'eeeeeeee-0000-0000-0000-000000000001';
  v_cid uuid := 'dddddddd-0000-0000-0000-000000000003';
  v_tok timestamptz;
begin
  select updated_at into v_tok from public.current_affairs_question_candidates where id = v_cid;
  begin
    perform public.ca_promote_candidate(v_cid, 'approved', v_tok, 'attempt discovery-only', v_actor, 'op@example.com');
    raise exception 'FAIL: discovery_only sole-source candidate must not promote';
  exception when others then
    if sqlerrm not like 'sole_evidence_discovery_only%' then raise;
    raise notice 'PASS promote rejects discovery_only sole evidence (F4/ADR-0007)';
  end;
end $$;

do $$ begin raise notice 'ALL PASS'; end $$;

rollback;
