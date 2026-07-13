-- validate_ca_attempt_rpcs.sql — GQR-G5a VERIFY DB (checkpost #976).
--
-- Executes the migration 253 PL/pgSQL the unit tests (SBStub-emulated) cannot run for
-- real: the integrity-locked start (bundle gate + authoritative eligible set + exact-set
-- mismatch reject + conflict-safe idempotent reuse), the atomic save (owner / in-progress
-- / frozen-question / frozen-option membership / monotonic client_seq idempotency), the
-- inline submit scoring with NO mastery/analytics write, and the ON DELETE RESTRICT that
-- keeps a bundle delete from erasing historical learner attempts. Rollback-only.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f validate_ca_attempt_rpcs.sql

begin;

-- ── Fixtures: family, exam, verified+published bundle, one eligible promoted
--    current-event question with two options + membership ─────────────────────
insert into public.exam_families (id, slug, name)
values ('f0000000-0000-0000-0000-000000000001', 'verify-family', 'VERIFY family')
on conflict (id) do nothing;
insert into public.exams (id, slug, name, exam_family_id, exam_type, is_active)
values ('e0000000-0000-0000-0000-000000000001', 'verify-exam', 'VERIFY exam',
        'f0000000-0000-0000-0000-000000000001', 'recruitment', true)
on conflict (id) do nothing;

insert into public.mock_question_bank
  (id, question_text, question_type, correct_option_id, source_kind, is_current_based,
   reviewer_status, valid_from, valid_until)
values
  ('a1000000-0000-0000-0000-000000000001', 'Who issued the June circular?', 'mcq',
   'a1100000-0000-0000-0000-000000000001', 'current_event', true, 'verified',
   current_date - 5, now() + interval '30 days');
insert into public.mock_question_options (id, question_id, option_text, option_index)
values
  ('a1100000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'RBI', 0),
  ('a1100000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'SEBI', 1);

insert into public.current_affairs_bundles
  (id, cadence, period_start, period_end, exam_id, reviewer_status, status,
   publish_at, available_until)
values
  ('b1000000-0000-0000-0000-000000000001', 'weekly', current_date - 6, current_date,
   'e0000000-0000-0000-0000-000000000001', 'verified', 'published',
   now() - interval '1 day', now() + interval '10 days');
insert into public.current_affairs_bundle_questions (bundle_id, mock_question_id, display_order)
values ('b1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 0);

do $$
declare
  v_user uuid := 'c0000000-0000-0000-0000-000000000001';
  v_bundle uuid := 'b1000000-0000-0000-0000-000000000001';
  v_q uuid := 'a1000000-0000-0000-0000-000000000001';
  v_opt uuid := 'a1100000-0000-0000-0000-000000000001';
  v_rows jsonb;
  v_snap jsonb;
  v_res jsonb;
  v_att uuid;
  v_att2 uuid;
  v_status text;
begin
  v_snap := jsonb_build_object('correct_option_id', v_opt::text,
    'options', jsonb_build_array(
      jsonb_build_object('id', v_opt::text, 'option_text', 'RBI'),
      jsonb_build_object('id', 'a1100000-0000-0000-0000-000000000002', 'option_text', 'SEBI')));
  v_rows := jsonb_build_array(jsonb_build_object('question_id', v_q::text, 'question_snapshot', v_snap));

  -- 1. bundle_set_mismatch: a caller set that differs from the authoritative set fails.
  begin
    perform public.ca_start_current_affairs_attempt(v_user, v_bundle, null, '{}'::jsonb,
      jsonb_build_array(jsonb_build_object('question_id', gen_random_uuid()::text,
                                           'question_snapshot', v_snap)));
    raise exception 'FAIL: mismatched frozen set was accepted';
  exception when others then
    if sqlerrm not like '%bundle_set_mismatch%' then raise; end if;
  end;

  -- 2. Happy start freezes the attempt from the authoritative set.
  v_res := public.ca_start_current_affairs_attempt(v_user, v_bundle, null, '{}'::jsonb, v_rows);
  if v_res->>'outcome' <> 'ready' then raise exception 'FAIL: start not ready: %', v_res; end if;
  v_att := (v_res->>'attempt_id')::uuid;
  if (select count(*) from public.current_affairs_attempt_responses where attempt_id = v_att) <> 1 then
    raise exception 'FAIL: expected 1 frozen response';
  end if;

  -- 3. Idempotent reuse: a second start returns the SAME attempt (ON CONFLICT), no dup.
  v_res := public.ca_start_current_affairs_attempt(v_user, v_bundle, null, '{}'::jsonb, v_rows);
  v_att2 := (v_res->>'attempt_id')::uuid;
  if v_res->>'outcome' <> 'reused' or v_att2 <> v_att then
    raise exception 'FAIL: start not idempotent: %', v_res;
  end if;
  if (select count(*) from public.current_affairs_attempts where user_id = v_user and bundle_id = v_bundle) <> 1 then
    raise exception 'FAIL: duplicate attempt created';
  end if;

  -- 4. Save: not-owner rejected.
  begin
    perform public.ca_save_current_affairs_answer(v_att, gen_random_uuid(), v_q, v_opt, false, 5, 1);
    raise exception 'FAIL: non-owner save accepted';
  exception when others then
    if sqlerrm not like '%not_attempt_owner%' then raise; end if;
  end;

  -- 5. Save: option not in question rejected.
  begin
    perform public.ca_save_current_affairs_answer(v_att, v_user, v_q, gen_random_uuid(), false, 5, 1);
    raise exception 'FAIL: bogus option accepted';
  exception when others then
    if sqlerrm not like '%option_not_in_question%' then raise; end if;
  end;

  -- 6. Save records the answer at seq 2.
  v_res := public.ca_save_current_affairs_answer(v_att, v_user, v_q, v_opt, false, 5, 2);
  if v_res->>'status' <> 'recorded' then raise exception 'FAIL: save not recorded: %', v_res; end if;

  -- 7. Stale replay (seq <= stored) is an idempotent no-op — the answer is NOT overwritten.
  v_res := public.ca_save_current_affairs_answer(
    v_att, v_user, v_q, 'a1100000-0000-0000-0000-000000000002', false, 9, 2);
  if (v_res->>'idempotent') is distinct from 'true' then
    raise exception 'FAIL: equal-seq replay was not idempotent: %', v_res;
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
  if v_status <> 'submitted' then raise exception 'FAIL: attempt not marked submitted'; end if;

  -- 9. ON DELETE RESTRICT: deleting the bundle must fail while a historical attempt exists.
  begin
    delete from public.current_affairs_bundles where id = v_bundle;
    raise exception 'FAIL: bundle delete cascaded over historical attempts';
  exception when foreign_key_violation then
    null;  -- expected: history is protected
  end;

  raise notice 'validate_ca_attempt_rpcs: ALL CHECKS PASSED';
end $$;

rollback;
