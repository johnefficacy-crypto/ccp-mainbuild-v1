-- regression_309_310_authored_corpus.sql
--
-- Manual PostgreSQL regression tests for REG-CORPUS-02 migrations 309 + 310.
--
-- Proves:
--   1. mock_question_bank.metadata defaults to '{}' (existing-row shape).
--   2. metadata.rubric_level outside L1..L4 is rejected; L3 is accepted.
--   3. metadata.stimulus_group must be a non-empty string.
--   4. An authored explanation keyed to mock_question_id with a same-question
--      final_answer_mock_option_id inserts.
--   5. A row keyed to BOTH question_id and mock_question_id is rejected.
--   6. A row keyed to NEITHER is rejected.
--   7. A mock option from a different mock question is rejected (integrity).
--   8. An authored row cannot carry a pyq_options answer (answer family).
--   9. Direct verify of an authored row without final_answer_mock_option_id is
--      rejected; with it, verify succeeds.
--  10. Content edit on a verified authored row downgrades to needs_correction.
--  11. Two authored explanations of one source_type for one question rejected.
--  12. The fenced RPC verifies a compliant authored row and writes one audit row.
--
-- Prerequisites: migrations 230, 309, 310 applied.
-- Usage: psql "$DATABASE_URL" -f regression_309_310_authored_corpus.sql
-- Expected output: twelve NOTICE "PASS" lines, no unexpected errors. Rolls back.

\set ON_ERROR_STOP on

BEGIN;

-- ── Fixture ────────────────────────────────────────────────────────────────
insert into public.profiles (id)
values ('30930930-0000-0000-0000-000000000001'::uuid);

insert into public.exam_families (id, slug, name)
values ('30930930-0000-0000-0000-0000000000a2'::uuid, 'rg309-family', 'Regression 309 Family');
insert into public.exams (id, exam_family_id, slug, name)
values ('30930930-0000-0000-0000-0000000000a3'::uuid, '30930930-0000-0000-0000-0000000000a2'::uuid, 'rg309-exam', 'Regression 309 Exam');
insert into public.pyq_papers (id, exam_id, year, trust_status, source_type)
values ('30930930-0000-0000-0000-0000000000a4'::uuid, '30930930-0000-0000-0000-0000000000a3'::uuid, 2025, 'pending', 'official');
insert into public.pyq_questions (id, pyq_paper_id, question_number, question_text, reviewer_status)
values ('30930930-0000-0000-0000-0000000000a5'::uuid, '30930930-0000-0000-0000-0000000000a4'::uuid, 1, 'rg309 pyq stem', 'pending');
insert into public.pyq_options (id, question_id, option_label, option_text)
values ('30930930-0000-0000-0000-0000000000a6'::uuid, '30930930-0000-0000-0000-0000000000a5'::uuid, 'A', 'P-A');

insert into public.mock_question_bank (id, question_text, question_type, difficulty, source_kind, reviewer_status)
values
  ('30930930-0000-0000-0000-0000000000b1'::uuid, 'rg309 authored Q1', 'mcq', 'hard', 'authored', 'draft'),
  ('30930930-0000-0000-0000-0000000000b2'::uuid, 'rg309 authored Q2', 'mcq', 'medium', 'authored', 'draft');

insert into public.mock_question_options (id, question_id, option_text, option_index, is_correct)
values
  ('30930930-0000-0000-0000-0000000000c1'::uuid, '30930930-0000-0000-0000-0000000000b1'::uuid, 'A', 0, false),
  ('30930930-0000-0000-0000-0000000000c2'::uuid, '30930930-0000-0000-0000-0000000000b1'::uuid, 'B', 1, true),
  ('30930930-0000-0000-0000-0000000000c3'::uuid, '30930930-0000-0000-0000-0000000000b2'::uuid, 'A', 0, true);

-- ── 1 ──────────────────────────────────────────────────────────────────────
do $$ begin
  if (select metadata from public.mock_question_bank
        where id = '30930930-0000-0000-0000-0000000000b1'::uuid) <> '{}'::jsonb then
    raise exception 'FAIL 1: metadata did not default to {}';
  end if;
  raise notice 'PASS 1: metadata defaults to {}';
end $$;

-- ── 2 ──────────────────────────────────────────────────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.mock_question_bank set metadata = '{"rubric_level":"L5"}'::jsonb
     where id = '30930930-0000-0000-0000-0000000000b1'::uuid;
  exception when check_violation then failed := true;
  end;
  if not failed then raise exception 'FAIL 2: rubric_level L5 accepted'; end if;
  update public.mock_question_bank set metadata = '{"rubric_level":"L3"}'::jsonb
   where id = '30930930-0000-0000-0000-0000000000b1'::uuid;
  raise notice 'PASS 2: rubric_level constrained to L1..L4';
end $$;

-- ── 3 ──────────────────────────────────────────────────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.mock_question_bank set metadata = '{"stimulus_group":""}'::jsonb
     where id = '30930930-0000-0000-0000-0000000000b2'::uuid;
  exception when check_violation then failed := true;
  end;
  if not failed then raise exception 'FAIL 3: empty stimulus_group accepted'; end if;
  update public.mock_question_bank set metadata = '{"stimulus_group":"CST-CASE-PROC"}'::jsonb
   where id = '30930930-0000-0000-0000-0000000000b2'::uuid;
  raise notice 'PASS 3: stimulus_group must be a non-empty string';
end $$;

-- ── 4 ──────────────────────────────────────────────────────────────────────
insert into public.pyq_question_explanations
  (id, mock_question_id, solution_steps, formula_used, common_traps, option_rationales,
   final_answer_mock_option_id, explanation_source_type, license_status, reviewer_status)
values
  ('30930930-0000-0000-0000-0000000000e1'::uuid, '30930930-0000-0000-0000-0000000000b1'::uuid,
   '["step 1","step 2"]'::jsonb, '["F = ma"]'::jsonb, '["unit slip"]'::jsonb,
   '{"30930930-0000-0000-0000-0000000000c1":"ignores the fixed cost"}'::jsonb,
   '30930930-0000-0000-0000-0000000000c2'::uuid, 'platform_original', 'owned', 'pending');
do $$ begin raise notice 'PASS 4: authored explanation with same-question mock answer inserts'; end $$;

-- ── 5 / 6 ──────────────────────────────────────────────────────────────────
do $$ declare failed boolean := false; begin
  begin
    insert into public.pyq_question_explanations (question_id, mock_question_id, explanation_source_type)
    values ('30930930-0000-0000-0000-0000000000a5'::uuid,
            '30930930-0000-0000-0000-0000000000b2'::uuid, 'imported');
  exception when check_violation then failed := true;
  end;
  if not failed then raise exception 'FAIL 5: row keyed to both question ids accepted'; end if;
  raise notice 'PASS 5: row keyed to both question ids rejected';
end $$;

do $$ declare failed boolean := false; begin
  begin
    insert into public.pyq_question_explanations (explanation_source_type) values ('official');
  exception when check_violation then failed := true;
  end;
  if not failed then raise exception 'FAIL 6: row keyed to no question accepted'; end if;
  raise notice 'PASS 6: row keyed to no question rejected';
end $$;

-- ── 7 ──────────────────────────────────────────────────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_question_explanations
       set final_answer_mock_option_id = '30930930-0000-0000-0000-0000000000c3'::uuid  -- Q2's option
     where id = '30930930-0000-0000-0000-0000000000e1'::uuid;
  exception when others then failed := true;
  end;
  if not failed then raise exception 'FAIL 7: cross-question mock option accepted'; end if;
  raise notice 'PASS 7: cross-question final_answer_mock_option_id rejected';
end $$;

-- ── 8 ──────────────────────────────────────────────────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_question_explanations
       set final_answer_option_id = '30930930-0000-0000-0000-0000000000a6'::uuid
     where id = '30930930-0000-0000-0000-0000000000e1'::uuid;
  exception when others then failed := true;  -- check_violation, FK, or guard
  end;
  if not failed then raise exception 'FAIL 8: authored row accepted a pyq_options answer'; end if;
  raise notice 'PASS 8: authored row cannot carry a pyq_options answer';
end $$;

-- ── 9 ──────────────────────────────────────────────────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_question_explanations
       set reviewer_status = 'verified', final_answer_mock_option_id = null,
           reviewed_by = '30930930-0000-0000-0000-000000000001'::uuid, reviewed_at = now()
     where id = '30930930-0000-0000-0000-0000000000e1'::uuid;
  exception when others then failed := true;
  end;
  if not failed then raise exception 'FAIL 9a: authored verify without final answer accepted'; end if;
end $$;
update public.pyq_question_explanations
   set reviewer_status = 'verified',
       final_answer_mock_option_id = '30930930-0000-0000-0000-0000000000c2'::uuid,
       reviewed_by = '30930930-0000-0000-0000-000000000001'::uuid, reviewed_at = now()
 where id = '30930930-0000-0000-0000-0000000000e1'::uuid;
do $$ begin
  if (select reviewer_status from public.pyq_question_explanations
        where id = '30930930-0000-0000-0000-0000000000e1'::uuid) <> 'verified' then
    raise exception 'FAIL 9b: compliant authored verify did not stick';
  end if;
  raise notice 'PASS 9: authored verify requires final_answer_mock_option_id';
end $$;

-- ── 10 ─────────────────────────────────────────────────────────────────────
update public.pyq_question_explanations
   set common_traps = '["edited trap"]'::jsonb
 where id = '30930930-0000-0000-0000-0000000000e1'::uuid;
do $$ begin
  if (select reviewer_status from public.pyq_question_explanations
        where id = '30930930-0000-0000-0000-0000000000e1'::uuid) <> 'needs_correction' then
    raise exception 'FAIL 10: edit did not downgrade a verified authored explanation';
  end if;
  raise notice 'PASS 10: edit downgrades verified authored explanation';
end $$;

-- ── 11 ─────────────────────────────────────────────────────────────────────
do $$ declare failed boolean := false; begin
  begin
    insert into public.pyq_question_explanations (mock_question_id, explanation_source_type)
    values ('30930930-0000-0000-0000-0000000000b1'::uuid, 'platform_original');
  exception when unique_violation then failed := true;
  end;
  if not failed then raise exception 'FAIL 11: duplicate authored source_type accepted'; end if;
  raise notice 'PASS 11: one authored explanation per (question, source_type)';
end $$;

-- ── 12 ─────────────────────────────────────────────────────────────────────
do $$
declare
  v_before int;
  v_after int;
  v_res jsonb;
begin
  select count(*) into v_before from public.admin_audit_logs
   where entity_id = '30930930-0000-0000-0000-0000000000e1';
  v_res := public.cms_review_pyq_question_explanation(
    '30930930-0000-0000-0000-0000000000e1', 'needs_correction', 'verified', 'rg310',
    '30930930-0000-0000-0000-000000000001', 'rg310@example.test');
  select count(*) into v_after from public.admin_audit_logs
   where entity_id = '30930930-0000-0000-0000-0000000000e1';
  if (v_res->>'new_status') <> 'verified' or v_after - v_before <> 1 then
    raise exception 'FAIL 12: RPC verify result % audit delta %', v_res, v_after - v_before;
  end if;
  raise notice 'PASS 12: fenced RPC verifies an authored explanation with one audit row';
end $$;

ROLLBACK;
