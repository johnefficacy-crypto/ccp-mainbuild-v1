-- regression_230_pyq_question_explanations.sql
--
-- Manual PostgreSQL regression tests for migration 230's PYQ explanation layer
-- governance (checkpost review, PR #904).
--
-- Proves:
--   1. A pending explanation with a same-question final_answer_option_id inserts.
--   2. A final_answer_option_id from a DIFFERENT question is rejected (integrity).
--   3. Direct verify with an uncleared licence (permission_pending) is rejected.
--   4. Direct verify with unresolved ambiguity (multiple_possible) is rejected.
--   5. Direct verify with null reviewer identity is rejected.
--   6. Direct verify with a null final answer is rejected.
--   7. Direct verify with all preconditions met succeeds.
--   8. Editing a verified explanation's content downgrades it to needs_correction.
--   9. Two explanations of the same source_type for one question are rejected.
--  10. The fenced RPC verifies a compliant row and writes exactly one audit row;
--      the RPC also refuses to verify an uncleared-licence row.
--
-- Prerequisites: migration 230 applied.
-- Usage: psql "$DATABASE_URL" -f regression_230_pyq_question_explanations.sql
-- Expected output: ten NOTICE "PASS" lines, no unexpected errors.

\set ON_ERROR_STOP on

BEGIN;

-- ── Fixture ────────────────────────────────────────────────────────────────
insert into public.profiles (id)
values ('22222222-2222-2222-2222-222222222201'::uuid);

insert into public.exam_families (id, slug, name)
values ('22222222-2222-2222-2222-222222222202'::uuid, 'rg230-family', 'Regression 230 Family');

insert into public.exams (id, exam_family_id, slug, name)
values ('22222222-2222-2222-2222-222222222203'::uuid, '22222222-2222-2222-2222-222222222202'::uuid, 'rg230-exam', 'Regression 230 Exam');

insert into public.pyq_papers (id, exam_id, year, trust_status, source_type)
values ('22222222-2222-2222-2222-222222222204'::uuid, '22222222-2222-2222-2222-222222222203'::uuid, 2025, 'pending', 'official');

insert into public.pyq_questions (id, pyq_paper_id, question_number, question_text, reviewer_status)
values
  ('22222222-2222-2222-2222-222222222205'::uuid, '22222222-2222-2222-2222-222222222204'::uuid, 1, 'Q1 stem', 'pending'),
  ('22222222-2222-2222-2222-222222222206'::uuid, '22222222-2222-2222-2222-222222222204'::uuid, 2, 'Q2 stem', 'pending');

-- Q1 options A-D; Q2 has one option (used for the cross-question integrity test)
insert into public.pyq_options (id, question_id, option_label, option_text)
values
  ('22222222-2222-2222-2222-2222222220a1'::uuid, '22222222-2222-2222-2222-222222222205'::uuid, 'A', 'Q1-A'),
  ('22222222-2222-2222-2222-2222222220a2'::uuid, '22222222-2222-2222-2222-222222222205'::uuid, 'B', 'Q1-B'),
  ('22222222-2222-2222-2222-2222222220a3'::uuid, '22222222-2222-2222-2222-222222222205'::uuid, 'C', 'Q1-C'),
  ('22222222-2222-2222-2222-2222222220a4'::uuid, '22222222-2222-2222-2222-222222222205'::uuid, 'D', 'Q1-D'),
  ('22222222-2222-2222-2222-2222222220b1'::uuid, '22222222-2222-2222-2222-222222222206'::uuid, 'A', 'Q2-A');

-- ── Test 1: same-question final answer inserts ─────────────────────────────
insert into public.pyq_question_explanations
  (id, question_id, explanation_text, final_answer_option_id, explanation_source_type,
   license_status, reviewer_status)
values
  ('22222222-2222-2222-2222-2222222220c1'::uuid, '22222222-2222-2222-2222-222222222205'::uuid,
   'Q1 rationale', '22222222-2222-2222-2222-2222222220a2'::uuid, 'platform_original', 'owned', 'pending');
do $$ begin raise notice 'PASS 1: pending explanation with same-question final answer inserts'; end $$;

-- ── Test 2: cross-question final answer rejected ───────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_question_explanations
       set final_answer_option_id = '22222222-2222-2222-2222-2222222220b1'::uuid  -- Q2's option
     where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
  exception when others then failed := true;
  end;
  if not failed then raise exception 'FAIL 2: cross-question final_answer_option_id was accepted'; end if;
  raise notice 'PASS 2: cross-question final_answer_option_id rejected';
end $$;

-- ── Test 3: verify with uncleared licence rejected ─────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_question_explanations
       set reviewer_status = 'verified', license_status = 'permission_pending',
           reviewed_by = '22222222-2222-2222-2222-222222222201'::uuid, reviewed_at = now()
     where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
  exception when others then failed := true;
  end;
  if not failed then raise exception 'FAIL 3: verify with permission_pending licence was accepted'; end if;
  raise notice 'PASS 3: verify with uncleared licence rejected';
end $$;

-- ── Test 4: verify with unresolved ambiguity rejected ──────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_question_explanations
       set reviewer_status = 'verified', ambiguity_status = 'multiple_possible',
           reviewed_by = '22222222-2222-2222-2222-222222222201'::uuid, reviewed_at = now()
     where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
  exception when others then failed := true;
  end;
  if not failed then raise exception 'FAIL 4: verify with unresolved ambiguity was accepted'; end if;
  raise notice 'PASS 4: verify with unresolved ambiguity rejected';
end $$;

-- ── Test 5: verify without reviewer identity rejected ──────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_question_explanations
       set reviewer_status = 'verified', reviewed_by = null, reviewed_at = null
     where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
  exception when others then failed := true;
  end;
  if not failed then raise exception 'FAIL 5: verify without reviewer identity was accepted'; end if;
  raise notice 'PASS 5: verify without reviewer identity rejected';
end $$;

-- ── Test 6: verify with null final answer rejected ─────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_question_explanations
       set reviewer_status = 'verified', final_answer_option_id = null,
           reviewed_by = '22222222-2222-2222-2222-222222222201'::uuid, reviewed_at = now()
     where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
  exception when others then failed := true;
  end;
  if not failed then raise exception 'FAIL 6: verify with null final answer was accepted'; end if;
  raise notice 'PASS 6: verify with null final answer rejected';
end $$;

-- ── Test 7: compliant direct verify succeeds ───────────────────────────────
update public.pyq_question_explanations
   set reviewer_status = 'verified', license_status = 'owned', ambiguity_status = 'none',
       final_answer_option_id = '22222222-2222-2222-2222-2222222220a2'::uuid,
       reviewed_by = '22222222-2222-2222-2222-222222222201'::uuid, reviewed_at = now()
 where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
do $$
begin
  if (select reviewer_status from public.pyq_question_explanations
        where id = '22222222-2222-2222-2222-2222222220c1'::uuid) <> 'verified' then
    raise exception 'FAIL 7: compliant verify did not stick';
  end if;
  raise notice 'PASS 7: compliant direct verify succeeds';
end $$;

-- ── Test 8: content edit on verified row downgrades to needs_correction ─────
update public.pyq_question_explanations
   set explanation_text = 'edited rationale'
 where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
do $$
begin
  if (select reviewer_status from public.pyq_question_explanations
        where id = '22222222-2222-2222-2222-2222222220c1'::uuid) <> 'needs_correction' then
    raise exception 'FAIL 8: content edit did not downgrade a verified explanation';
  end if;
  raise notice 'PASS 8: content edit downgrades verified -> needs_correction';
end $$;

-- ── Test 8b-8e: edits to other verified fields also downgrade ──────────────
-- Helper: re-verify the row to a compliant state, edit one field, assert it
-- falls back to needs_correction.
do $$
declare
  fld text;
  cur text;
begin
  foreach fld in array array['formula_used', 'common_traps', 'license_status', 'source_url'] loop
    -- restore to a compliant verified state
    update public.pyq_question_explanations
       set reviewer_status = 'verified', license_status = 'owned', ambiguity_status = 'none',
           source_url = null, formula_used = '[]'::jsonb, common_traps = '[]'::jsonb,
           final_answer_option_id = '22222222-2222-2222-2222-2222222220a2'::uuid,
           reviewed_by = '22222222-2222-2222-2222-222222222201'::uuid, reviewed_at = now()
     where id = '22222222-2222-2222-2222-2222222220c1'::uuid;

    if fld = 'formula_used' then
      update public.pyq_question_explanations set formula_used = '["v = u + at"]'::jsonb
       where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
    elsif fld = 'common_traps' then
      update public.pyq_question_explanations set common_traps = '["sign error"]'::jsonb
       where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
    elsif fld = 'license_status' then
      update public.pyq_question_explanations set license_status = 'permission_pending'
       where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
    else
      update public.pyq_question_explanations set source_url = 'https://example.com/expl'
       where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
    end if;

    select reviewer_status into cur from public.pyq_question_explanations
     where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
    if cur <> 'needs_correction' then
      raise exception 'FAIL 8+: editing % on a verified row left status = %', fld, cur;
    end if;
  end loop;
  raise notice 'PASS 8b-8e: edits to formula_used/common_traps/license_status/source_url each downgrade verified -> needs_correction';
end $$;

-- ── Test 9: duplicate (question_id, source_type) rejected ──────────────────
do $$ declare failed boolean := false; begin
  begin
    insert into public.pyq_question_explanations
      (question_id, explanation_text, explanation_source_type, license_status)
    values ('22222222-2222-2222-2222-222222222205'::uuid, 'dup', 'platform_original', 'owned');
  exception when others then failed := true;
  end;
  if not failed then raise exception 'FAIL 9: duplicate (question_id, source_type) was accepted'; end if;
  raise notice 'PASS 9: duplicate (question_id, explanation_source_type) rejected';
end $$;

-- ── Test 10: fenced review RPC verifies compliant row + audits; refuses uncleared ─
-- Reset to pending, then RPC-verify (row already has a valid final answer + owned licence).
update public.pyq_question_explanations
   set reviewer_status = 'pending', ambiguity_status = 'none', license_status = 'owned',
       reviewed_by = null, reviewed_at = null
 where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
do $$
declare
  v jsonb;
  v_audit_before int;
  v_audit_after int;
  failed boolean := false;
begin
  select count(*) into v_audit_before from public.admin_audit_logs
   where entity_type = 'pyq_question_explanation'
     and entity_id = '22222222-2222-2222-2222-2222222220c1';

  v := public.cms_review_pyq_question_explanation(
        '22222222-2222-2222-2222-2222222220c1', 'pending', 'verified',
        'looks good', '22222222-2222-2222-2222-222222222201', 'reviewer@example.com');

  if (v ->> 'new_status') <> 'verified' then raise exception 'FAIL 10a: RPC did not verify'; end if;
  if (select reviewer_status from public.pyq_question_explanations
        where id = '22222222-2222-2222-2222-2222222220c1'::uuid) <> 'verified' then
    raise exception 'FAIL 10b: RPC verify did not persist';
  end if;

  select count(*) into v_audit_after from public.admin_audit_logs
   where entity_type = 'pyq_question_explanation'
     and entity_id = '22222222-2222-2222-2222-2222222220c1';
  if v_audit_after <> v_audit_before + 1 then
    raise exception 'FAIL 10c: expected exactly one new audit row, got %', v_audit_after - v_audit_before;
  end if;

  -- RPC must refuse to verify an uncleared-licence row.
  update public.pyq_question_explanations
     set reviewer_status = 'needs_correction', license_status = 'permission_pending',
         reviewed_by = null, reviewed_at = null
   where id = '22222222-2222-2222-2222-2222222220c1'::uuid;
  begin
    perform public.cms_review_pyq_question_explanation(
      '22222222-2222-2222-2222-2222222220c1', 'needs_correction', 'verified',
      'try', '22222222-2222-2222-2222-222222222201', 'reviewer@example.com');
  exception when others then failed := true;
  end;
  if not failed then raise exception 'FAIL 10d: RPC verified an uncleared-licence row'; end if;

  raise notice 'PASS 10: fenced RPC verifies compliant row (+1 audit) and refuses uncleared licence';
end $$;

-- ── Test 11: service_role and authenticated hold table-level grants ────────
do $$
begin
  if not has_table_privilege('service_role', 'public.pyq_question_explanations', 'SELECT')
     or not has_table_privilege('service_role', 'public.pyq_question_explanations', 'INSERT')
     or not has_table_privilege('service_role', 'public.pyq_question_explanations', 'UPDATE')
     or not has_table_privilege('service_role', 'public.pyq_question_explanations', 'DELETE') then
    raise exception 'FAIL 11a: service_role is missing table grants (post-173 grant lesson)';
  end if;
  if not has_table_privilege('authenticated', 'public.pyq_question_explanations', 'SELECT')
     or not has_table_privilege('authenticated', 'public.pyq_question_explanations', 'INSERT')
     or not has_table_privilege('authenticated', 'public.pyq_question_explanations', 'UPDATE')
     or not has_table_privilege('authenticated', 'public.pyq_question_explanations', 'DELETE') then
    raise exception 'FAIL 11b: authenticated is missing the table grants that back the admin RLS policy';
  end if;
  if has_table_privilege('anon', 'public.pyq_question_explanations', 'SELECT') then
    raise exception 'FAIL 11c: anon must not hold table privileges';
  end if;
  raise notice 'PASS 11: service_role + authenticated hold table grants; anon does not';
end $$;

ROLLBACK;
