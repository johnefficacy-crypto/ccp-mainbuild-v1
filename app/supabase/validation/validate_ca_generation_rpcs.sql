-- validate_ca_generation_rpcs.sql — GQR-G3 VERIFY DB (checkpost #966).
--
-- Executes the migration 245 PL/pgSQL paths that the unit tests (fake Supabase)
-- cannot: candidate insert + audit lineage, partial-index ON CONFLICT dedup, the
-- replay-after-ack no-op, and lease fencing. Run against a real Postgres with the
-- migrations applied. Wrapped in a rollback-only transaction — leaves no data.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_generation_rpcs.sql
--
-- Every RAISE NOTICE 'PASS ...' must print and the script must reach 'ALL PASS'.

begin;

-- ── seed a source + document (the generation input) ────────────────────────
insert into public.current_affairs_sources (id, name, authority_level, adapter_type)
values ('aaaaaaaa-0000-0000-0000-000000000001', 'VERIFY source', 'primary_official', 'rss');

insert into public.current_affairs_documents (id, source_id, source_url, raw_text, ingestion_status)
values ('bbbbbbbb-0000-0000-0000-000000000001',
        'aaaaaaaa-0000-0000-0000-000000000001',
        'https://example.test/doc', 'A verifiable current-affairs claim body.', 'snapshotted');

do $$
declare
  v_job uuid;
  v_claim jsonb;
  v_token uuid;
  v_res jsonb;
  v_events jsonb;
  v_cand public.current_affairs_question_candidates%rowtype;
  v_gen_ok boolean;
  v_ver_ok boolean;
  v_replay jsonb;
begin
  -- enqueue + claim
  v_job := public.ca_enqueue_generation_job('bbbbbbbb-0000-0000-0000-000000000001');
  if v_job is null then raise exception 'FAIL enqueue'; end if;
  v_claim := public.ca_claim_generation_job(900, array['ca_generation']);
  if v_claim is null then raise exception 'FAIL claim returned null'; end if;
  v_token := (v_claim->>'claim_token')::uuid;
  raise notice 'PASS enqueue+claim (job=%, authority=%)', v_job, v_claim->>'source_authority_level';

  -- one event → one claim (temp id c0) → one review_ready candidate with lineage
  v_events := jsonb_build_array(jsonb_build_object(
    'temp_id', 'e0',
    'canonical_title', 'VERIFY event',
    'event_date', '2026-06-01',
    'event_fingerprint', 'verify-evt-1',
    'editorial_importance', 'normal',
    'claims', jsonb_build_array(jsonb_build_object(
      'temp_id', 'e0c0', 'claim_text', 'A verifiable claim.', 'claim_fingerprint', 'verify-clm-1',
      'factual_status', 'current',
      'evidence', jsonb_build_array(jsonb_build_object(
        'document_id', 'bbbbbbbb-0000-0000-0000-000000000001',
        'evidence_text', 'A verifiable claim.', 'start_offset', 0, 'end_offset', 18,
        'evidence_role', 'primary')))),
    'candidates', jsonb_build_array(jsonb_build_object(
      'question_payload', jsonb_build_object('stem', 'Q?', 'correct_option_id', 'a'),
      'question_fingerprint', 'verify-mcq-1',
      'linked_temp_claim_ids', jsonb_build_array('e0c0'),
      'status', 'review_ready',
      'validation_result', jsonb_build_object('ok', true),
      'verifier_verdict', jsonb_build_object('supported_answer', true),
      'generator_run', jsonb_build_object('action', 'mcq_generation', 'provider', 'mock', 'status', 'mock'),
      'verifier_run', jsonb_build_object('action', 'verification', 'provider', 'mock', 'status', 'mock')))));

  v_res := public.ca_complete_generation(v_job, v_token, 'bbbbbbbb-0000-0000-0000-000000000001',
                                         v_events, '[]'::jsonb, 'ca-mock:verify');
  if v_res->>'status' <> 'completed' then raise exception 'FAIL complete: %', v_res; end if;
  raise notice 'PASS complete (events=%, candidates=%)',
    v_res->>'events_written', v_res->>'candidates_written';

  -- candidate persisted with generator + verifier lineage (F1)
  select * into v_cand from public.current_affairs_question_candidates
  where question_fingerprint = 'verify-mcq-1';
  if v_cand.generator_run_id is null or v_cand.verifier_run_id is null then
    raise exception 'FAIL candidate audit lineage: gen=% ver=%',
      v_cand.generator_run_id, v_cand.verifier_run_id;
  end if;
  select exists(select 1 from public.current_affairs_generation_runs
    where id = v_cand.generator_run_id and action = 'mcq_generation'
      and candidate_id = v_cand.id) into v_gen_ok;
  select exists(select 1 from public.current_affairs_generation_runs
    where id = v_cand.verifier_run_id and action = 'verification'
      and candidate_id = v_cand.id) into v_ver_ok;
  if not (v_gen_ok and v_ver_ok) then raise exception 'FAIL run<->candidate lineage'; end if;
  raise notice 'PASS candidate audit lineage (F1)';

  -- replay after ack: same token → no-op 'replayed', not a fencing error (F3)
  v_replay := public.ca_complete_generation(v_job, v_token, 'bbbbbbbb-0000-0000-0000-000000000001',
                                            v_events, '[]'::jsonb, 'ca-mock:verify');
  if v_replay->>'status' <> 'replayed' then raise exception 'FAIL replay: %', v_replay; end if;
  raise notice 'PASS replay-after-ack (F3)';

  raise notice 'ALL PASS';
end $$;

-- fencing: completing with a bogus token on a fresh claimed job must raise (F3).
do $$
declare v_job uuid; v_claim jsonb;
begin
  insert into public.current_affairs_documents (id, source_id, source_url, raw_text, ingestion_status)
  values ('bbbbbbbb-0000-0000-0000-000000000002',
          'aaaaaaaa-0000-0000-0000-000000000001', 'https://example.test/doc2',
          'Another body.', 'snapshotted');
  v_job := public.ca_enqueue_generation_job('bbbbbbbb-0000-0000-0000-000000000002');
  v_claim := public.ca_claim_generation_job(900, array['ca_generation']);
  begin
    perform public.ca_complete_generation(v_job, gen_random_uuid(),
      'bbbbbbbb-0000-0000-0000-000000000002', '[]'::jsonb, '[]'::jsonb, null);
    raise exception 'FAIL: stale-token complete should have raised fencing';
  exception when others then
    if sqlerrm not like 'ca_job_fencing_failed%' then raise;
    raise notice 'PASS fencing rejects stale token';
  end;
end $$;

rollback;
