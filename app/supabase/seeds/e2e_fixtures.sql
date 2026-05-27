-- E2E test fixtures — deterministic, idempotent mock content for Playwright.
--
-- Seeds a section-locked "IBPS PO Prelims (E2E)" template with 3 sections of
-- 5 questions each (15 total, 4 options each, option_index 1 is always
-- correct). Everything uses fixed UUIDs and ON CONFLICT upserts so re-running
-- this file (e.g. `supabase db reset` then seed, or a direct psql apply)
-- converges to the same state without drift.
--
-- This seeds CONTENT only. The auth user is created by the Playwright global
-- setup via the Supabase admin API (passwords can't be seeded as plain SQL),
-- and attempts are created at test time through the real backend API so they
-- exercise the genuine scoring/derivation paths.
--
-- Rows are tagged source_type = 'e2e_fixture' so they are easy to identify and
-- never collide with production catalogue content.

do $$
declare
  v_template_id uuid := 'e2e00000-0000-4000-8000-000000000000';
  -- Slug matches the one the Mocks page "Start IBPS PO Prelims Mock" button
  -- requests, so Flow 1 exercises the real start control end-to-end.
  v_slug        text := 'ibps-po-prelims-mock-1';
  v_section_count int := 3;
  v_per_section   int := 5;
  s int;        -- section index 0..2
  k int;        -- question index within section 1..5
  qn int;       -- global question number 1..15
  o int;        -- option index 1..4
  v_qid uuid;
  v_correct_oid uuid;
  v_section_qids jsonb;
  v_sections jsonb := '[]'::jsonb;
  v_section_names text[] := array['English Language', 'Reasoning Ability', 'Quantitative Aptitude'];
begin
  -- 0) Migration 135 (mock_engine_core) seeds its own "IBPS PO Prelims Mock 1"
  -- template under this same slug with a DB-generated id. Our fixture upserts on
  -- the primary key (id), so that pre-seeded row would survive and the insert
  -- below would trip the slug unique constraint (mock_templates_slug_key). Drop
  -- any row squatting on our slug that isn't our fixed-id fixture row; at seed
  -- time that template has no template_sections and no attempts, so the delete
  -- is safe, and it is a no-op once our own row exists (keeps the seed idempotent).
  delete from public.mock_templates
   where slug = v_slug and id <> v_template_id;

  -- 1) Template shell (config filled in after we know the question ids).
  insert into public.mock_templates
    (id, slug, name, exam_family, total_questions, duration_sec,
     negative_marking, marks_per_correct, marks_per_wrong, config, status)
  values
    (v_template_id, v_slug, 'IBPS PO Prelims (E2E)', 'IBPS', v_section_count * v_per_section, 3600,
     true, 1, 0.25, '{}'::jsonb, 'active')
  on conflict (id) do update set
    name = excluded.name,
    total_questions = excluded.total_questions,
    status = 'active';

  -- 2) Questions, options, and per-section selectors.
  for s in 0 .. v_section_count - 1 loop
    v_section_qids := '[]'::jsonb;
    for k in 1 .. v_per_section loop
      qn := s * v_per_section + k;
      v_qid := ('e2e00000-0000-4000-8000-' || lpad(qn::text, 12, '0'))::uuid;
      v_correct_oid := ('e2e00000-0000-4000-8001-' || lpad((qn * 10 + 1)::text, 12, '0'))::uuid;

      insert into public.mock_question_bank
        (id, exam_family, question_text, question_type, difficulty, marks,
         negative_marks, correct_option_id, explanation, source_type, reviewer_status)
      values
        (v_qid, 'IBPS',
         format('[%s] Q%s — sample question for the E2E mock (section %s).',
                v_section_names[s + 1], k, s + 1),
         'mcq', 'medium', 1, 0.25, v_correct_oid,
         format('Option 1 is correct for Q%s. (E2E fixture explanation.)', qn),
         'e2e_fixture', 'reviewed')
      on conflict (id) do update set
        question_text = excluded.question_text,
        correct_option_id = excluded.correct_option_id,
        explanation = excluded.explanation;

      for o in 1 .. 4 loop
        insert into public.mock_question_options
          (id, question_id, option_text, option_index, is_correct)
        values
          (('e2e00000-0000-4000-8001-' || lpad((qn * 10 + o)::text, 12, '0'))::uuid,
           v_qid, format('Q%s option %s', qn, o), o, (o = 1))
        on conflict (question_id, option_index) do update set
          option_text = excluded.option_text,
          is_correct = excluded.is_correct;
      end loop;

      v_section_qids := v_section_qids || to_jsonb(v_qid::text);
    end loop;

    -- mock_template_sections drives question SELECTION at attempt start.
    insert into public.mock_template_sections
      (template_id, section_index, name, question_count, marks_per_correct,
       marks_per_wrong, allow_switching, selector)
    values
      (v_template_id, s, v_section_names[s + 1], v_per_section, 1, 0.25, false,
       jsonb_build_object('mode', 'fixed', 'question_ids', v_section_qids))
    on conflict (template_id, section_index) do update set
      name = excluded.name,
      question_count = excluded.question_count,
      marks_per_correct = excluded.marks_per_correct,
      selector = excluded.selector;

    -- config.sections drives SECTION LOCKING (read from the attempt snapshot).
    v_sections := v_sections || jsonb_build_object(
      'section_index', s,
      'name', v_section_names[s + 1],
      'question_ids', v_section_qids
    );
  end loop;

  -- 3) Finalise template config: section-locked, simple interface.
  update public.mock_templates
  set config = jsonb_build_object(
        'interface_mode', 'simple',
        'allow_switching', false,
        'sections', v_sections
      )
  where id = v_template_id;
end $$;
