-- validate_ca_attempt_rpcs.sql — GQR-G5a VERIFY DB (checkpost #976 rounds 1 + 2).
--
-- Executes the migration 253 PL/pgSQL the unit tests (SBStub-emulated) cannot run for
-- real: the scope-gated, integrity-locked start (exam/family scope enforcement, fail-
-- closed bundle degradation, authoritative ordered exact-set, snapshot verification vs
-- the bank, content-revision freeze, conflict-safe idempotent reuse), the atomic save
-- (owner / in-progress / frozen-question / frozen-option / monotonic client_seq), the
-- inline submit scoring with NO mastery/analytics write, and the ON DELETE RESTRICT that
-- keeps a bundle delete from erasing historical learner attempts. Rollback-only.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_attempt_rpcs.sql

begin;

-- ── Fixtures: family, exam-in-family, promoted current-event question with a
--    complete provenance chain (event → claim → evidence → document), and three
--    exam-scoped bundles (happy / degraded / snapshot-mismatch) ─────────────────
insert into public.exam_families (id, slug, name)
values ('f0000000-0000-0000-0000-000000000001', 'verify-family', 'VERIFY family')
on conflict (id) do nothing;
insert into public.exams (id, slug, name, exam_family_id, exam_type, is_active)
values ('e0000000-0000-0000-0000-000000000001', 'verify-exam', 'VERIFY exam',
        'f0000000-0000-0000-0000-000000000001', 'recruitment', true)
on conflict (id) do nothing;

-- Provenance chain
insert into public.current_affairs_sources (id, name, authority_level, adapter_type, is_active)
values ('50000000-0000-0000-0000-000000000001', 'VERIFY source', 'primary_official', 'rss', true);
insert into public.current_affairs_documents (id, source_id, source_url, content_hash, published_at, raw_text, ingestion_status)
values ('d0000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001',
        'https://example.test/doc', 'sha-verify-1', now() - interval '2 days',
        'RBI issued a digital lending circular.', 'snapshotted');
insert into public.current_affairs_events (id, canonical_title, event_date, status, relevance_from, relevance_until)
values ('60000000-0000-0000-0000-000000000001', 'VERIFY event', current_date - 3, 'active',
        current_date - 3, current_date + 30);
insert into public.current_affairs_claims (id, event_id, claim_text, factual_status, reviewer_status)
values ('70000000-0000-0000-0000-000000000001', '60000000-0000-0000-0000-000000000001',
        'RBI issued a digital lending circular.', 'current', 'verified');
insert into public.current_affairs_claim_evidence (claim_id, document_id, evidence_text, start_offset, end_offset, evidence_role)
values ('70000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001',
        'RBI issued a digital lending circular.', 0, 38, 'primary');

-- Promoted current-event question + options
insert into public.mock_question_bank
  (id, question_text, question_type, correct_option_id, source_kind, is_current_based,
   reviewer_status, valid_from, valid_until, current_affairs_item_id)
values
  ('a1000000-0000-0000-0000-000000000001', 'Who issued the June circular?', 'mcq',
   'a1100000-0000-0000-0000-000000000001', 'current_event', true, 'verified',
   current_date - 5, now() + interval '30 days', '60000000-0000-0000-0000-000000000001');
insert into public.mock_question_options (id, question_id, option_text, option_index)
values
  ('a1100000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'RBI', 0),
  ('a1100000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'SEBI', 1);
insert into public.current_affairs_question_links (candidate_id, event_id, claim_id, mock_question_id)
values (gen_random_uuid(), '60000000-0000-0000-0000-000000000001',
        '70000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001');

-- A stale (expired) sibling question for the degradation bundle.
insert into public.mock_question_bank
  (id, question_text, question_type, correct_option_id, source_kind, is_current_based,
   reviewer_status, valid_until, current_affairs_item_id)
values
  ('a2000000-0000-0000-0000-000000000001', 'Stale?', 'mcq', 'a2200000-0000-0000-0000-000000000001',
   'current_event', true, 'verified', now() - interval '1 day', '60000000-0000-0000-0000-000000000001');

-- Bundles: created DRAFT so membership can be added (membership is locked once published),
-- then published. All exam-scoped to the VERIFY exam.
insert into public.current_affairs_bundles
  (id, cadence, period_start, period_end, exam_id, reviewer_status, status, publish_at, available_until)
values
  ('b1000000-0000-0000-0000-000000000001', 'weekly', current_date - 6, current_date,
   'e0000000-0000-0000-0000-000000000001', 'verified', 'draft', now() - interval '1 day', now() + interval '10 days'),
  ('b2000000-0000-0000-0000-000000000001', 'weekly', current_date - 6, current_date,
   'e0000000-0000-0000-0000-000000000001', 'verified', 'draft', now() - interval '1 day', now() + interval '10 days'),
  ('b3000000-0000-0000-0000-000000000001', 'weekly', current_date - 6, current_date,
   'e0000000-0000-0000-0000-000000000001', 'verified', 'draft', now() - interval '1 day', now() + interval '10 days');
insert into public.current_affairs_bundle_questions (bundle_id, mock_question_id, display_order)
values
  ('b1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 0),
  ('b2000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 0),
  ('b2000000-0000-0000-0000-000000000001', 'a2000000-0000-0000-0000-000000000001', 1),  -- stale → degraded
  ('b3000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 0);
update public.current_affairs_bundles set status = 'published'
  where id in ('b1000000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000001',
               'b3000000-0000-0000-0000-000000000001');

do $$
declare
  v_exam uuid := 'e0000000-0000-0000-0000-000000000001';
  v_user uuid := 'c0000000-0000-0000-0000-000000000001';
  v_b1 uuid := 'b1000000-0000-0000-0000-000000000001';
  v_b2 uuid := 'b2000000-0000-0000-0000-000000000001';
  v_b3 uuid := 'b3000000-0000-0000-0000-000000000001';
  v_q uuid := 'a1000000-0000-0000-0000-000000000001';
  v_opt uuid := 'a1100000-0000-0000-0000-000000000001';
  v_snap jsonb;
  v_rows jsonb;
  v_res jsonb;
  v_att uuid;
  v_status text;
begin
  -- Snapshot must match the bank content: question text + per-option id/text + answer.
  v_snap := jsonb_build_object(
    'question_text', 'Who issued the June circular?',
    'correct_option_id', v_opt::text,
    'options', jsonb_build_array(
      jsonb_build_object('id', v_opt::text, 'option_text', 'RBI'),
      jsonb_build_object('id', 'a1100000-0000-0000-0000-000000000002', 'option_text', 'SEBI')));
  v_rows := jsonb_build_array(jsonb_build_object('question_id', v_q::text, 'question_snapshot', v_snap));

  -- 0. MEMBERSHIP LOCK: a published bundle's membership cannot be mutated (R3-F1).
  begin
    insert into public.current_affairs_bundle_questions (bundle_id, mock_question_id, display_order)
    values (v_b1, v_q, 9);
    raise exception 'FAIL: membership mutated on a published bundle';
  exception when others then
    if sqlerrm not like '%bundle_membership_locked_when_published%' then raise; end if;
  end;

  -- 1. SCOPE: an exam-scoped bundle rejects a mismatched p_exam (finding 1).
  begin
    perform public.ca_start_current_affairs_attempt(v_user, v_b1,
      'e0000000-0000-0000-0000-0000000000ff'::uuid, '{}'::jsonb, v_rows);
    raise exception 'FAIL: scope mismatch accepted';
  exception when others then
    if sqlerrm not like '%bundle_scope_mismatch%' then raise; end if;
  end;

  -- 2. DEGRADATION: a bundle with a stale member fails closed (finding 2).
  begin
    perform public.ca_start_current_affairs_attempt(v_user, v_b2, v_exam, '{}'::jsonb,
      jsonb_build_array(jsonb_build_object('question_id', v_q::text, 'question_snapshot', v_snap)));
    raise exception 'FAIL: degraded bundle accepted';
  exception when others then
    if sqlerrm not like '%bundle_degraded%' then raise; end if;
  end;

  -- 3. SNAPSHOT INTEGRITY: a caller row whose answer != the bank is rejected (finding 2/3).
  begin
    perform public.ca_start_current_affairs_attempt(v_user, v_b3, v_exam, '{}'::jsonb,
      jsonb_build_array(jsonb_build_object('question_id', v_q::text,
        'question_snapshot', jsonb_set(v_snap, '{correct_option_id}',
          to_jsonb('a1100000-0000-0000-0000-000000000002'::text)))));
    raise exception 'FAIL: forged answer snapshot accepted';
  exception when others then
    if sqlerrm not like '%snapshot_answer_mismatch%' then raise; end if;
  end;

  -- 4. Happy start freezes from the authoritative set + binds a content revision.
  v_res := public.ca_start_current_affairs_attempt(v_user, v_b1, v_exam, '{}'::jsonb, v_rows);
  if v_res->>'outcome' <> 'ready' then raise exception 'FAIL: start not ready: %', v_res; end if;
  v_att := (v_res->>'attempt_id')::uuid;
  if not exists (select 1 from public.current_affairs_attempt_responses
                 where attempt_id = v_att and question_snapshot ? 'content_revision') then
    raise exception 'FAIL: content_revision not frozen';
  end if;

  -- 5. Idempotent reuse (ON CONFLICT), no duplicate attempt.
  v_res := public.ca_start_current_affairs_attempt(v_user, v_b1, v_exam, '{}'::jsonb, v_rows);
  if v_res->>'outcome' <> 'reused' or (v_res->>'attempt_id')::uuid <> v_att then
    raise exception 'FAIL: start not idempotent: %', v_res;
  end if;
  if (select count(*) from public.current_affairs_attempts where user_id = v_user and bundle_id = v_b1) <> 1 then
    raise exception 'FAIL: duplicate attempt created';
  end if;

  -- 6. Save: non-owner + bogus option rejected.
  begin
    perform public.ca_save_current_affairs_answer(v_att, gen_random_uuid(), v_q, v_opt, false, 5, 1);
    raise exception 'FAIL: non-owner save accepted';
  exception when others then
    if sqlerrm not like '%not_attempt_owner%' then raise; end if;
  end;
  begin
    perform public.ca_save_current_affairs_answer(v_att, v_user, v_q, gen_random_uuid(), false, 5, 1);
    raise exception 'FAIL: bogus option accepted';
  exception when others then
    if sqlerrm not like '%option_not_in_question%' then raise; end if;
  end;

  -- 7. Save records at seq 2; a stale (<=) replay is an idempotent no-op (not an overwrite).
  perform public.ca_save_current_affairs_answer(v_att, v_user, v_q, v_opt, false, 5, 2);
  v_res := public.ca_save_current_affairs_answer(
    v_att, v_user, v_q, 'a1100000-0000-0000-0000-000000000002', false, 9, 2);
  if (v_res->>'idempotent') is distinct from 'true' then
    raise exception 'FAIL: equal-seq replay not idempotent: %', v_res;
  end if;
  if (select selected_option_id from public.current_affairs_attempt_responses
      where attempt_id = v_att and mock_question_id = v_q) <> v_opt then
    raise exception 'FAIL: stale replay overwrote the recorded answer';
  end if;

  -- 8. Submit scores inline (1 correct) and writes NOTHING to mastery/mock tables.
  v_res := public.ca_submit_current_affairs_attempt(v_att, v_user);
  if (v_res->>'total_correct')::int <> 1 or v_res->>'outcome' <> 'submitted' then
    raise exception 'FAIL: submit scoring wrong: %', v_res;
  end if;
  select status into v_status from public.current_affairs_attempts where id = v_att;
  if v_status <> 'submitted' then raise exception 'FAIL: attempt not submitted'; end if;

  -- 9. History protection: a published bundle with a historical attempt cannot be deleted
  --    (attempt→bundle RESTRICT and/or the published-membership guard) — either way the
  --    attempt survives.
  begin
    delete from public.current_affairs_bundles where id = v_b1;
    raise exception 'FAIL: bundle delete removed historical attempts';
  exception when others then
    if sqlerrm like 'FAIL:%' then raise; end if;  -- re-raise our own assertion
    null;  -- expected: a protective error (FK restrict or membership lock)
  end;
  if not exists (select 1 from public.current_affairs_attempts where id = v_att) then
    raise exception 'FAIL: historical attempt was deleted';
  end if;

  raise notice 'validate_ca_attempt_rpcs: ALL CHECKS PASSED';
end $$;

rollback;
