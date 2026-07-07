-- regression_223_pyq_section_stimulus_integrity.sql
--
-- Manual PostgreSQL regression tests for migration 223's cross-parent
-- integrity triggers (checkpost review, PR #892 P0-1).
--
-- Proves:
--   1. A question/stimulus/link within the same exam phase and paper passes.
--   2. A question.section_id from a DIFFERENT exam phase than its paper fails.
--   3. A stimulus.section_id from a DIFFERENT exam phase than its paper fails.
--   4. A question_stimuli link across two DIFFERENT papers fails.
--   5. Moving a verified paper to a different exam phase, after a
--      section-scoped question already exists under it, fails atomically
--      (the paper is not silently left inconsistent with its questions).
--
-- Prerequisites:
--   Migration 223 must be applied.
--
-- Usage:
--   psql "$DATABASE_URL" -f regression_223_pyq_section_stimulus_integrity.sql
--
-- Expected output: five NOTICE "PASS" lines, no unexpected errors.

\set ON_ERROR_STOP on

-- ── Fixture: two exams, each with one phase, one section, one paper ────────

BEGIN;

insert into public.subjects (id, slug, name)
values ('11111111-1111-1111-1111-111111111101'::uuid, 'rg223-subject', 'Regression 223 Subject');

insert into public.exam_families (id, slug, name)
values ('11111111-1111-1111-1111-111111111102'::uuid, 'rg223-family', 'Regression 223 Family');

insert into public.exams (id, exam_family_id, slug, name)
values
  ('11111111-1111-1111-1111-111111111103'::uuid, '11111111-1111-1111-1111-111111111102'::uuid, 'rg223-exam-a', 'Regression 223 Exam A'),
  ('11111111-1111-1111-1111-111111111104'::uuid, '11111111-1111-1111-1111-111111111102'::uuid, 'rg223-exam-b', 'Regression 223 Exam B');

insert into public.exam_phases (id, exam_id, phase_name, phase_slug)
values
  ('11111111-1111-1111-1111-111111111105'::uuid, '11111111-1111-1111-1111-111111111103'::uuid, 'Phase A1', 'phase-a1'),
  ('11111111-1111-1111-1111-111111111106'::uuid, '11111111-1111-1111-1111-111111111103'::uuid, 'Phase A2', 'phase-a2'),
  ('11111111-1111-1111-1111-111111111107'::uuid, '11111111-1111-1111-1111-111111111104'::uuid, 'Phase B1', 'phase-b1');

insert into public.exam_phase_sections (id, exam_phase_id, subject_id, section_label)
values
  -- Section belonging to Phase A1
  ('11111111-1111-1111-1111-111111111108'::uuid, '11111111-1111-1111-1111-111111111105'::uuid, '11111111-1111-1111-1111-111111111101'::uuid, 'Section A1-Reasoning'),
  -- Section belonging to Phase A2 (different phase, same exam) — used for the mismatch test
  ('11111111-1111-1111-1111-111111111109'::uuid, '11111111-1111-1111-1111-111111111106'::uuid, '11111111-1111-1111-1111-111111111101'::uuid, 'Section A2-Reasoning'),
  -- Section belonging to Phase B1 (different exam) — used for the mismatch test
  ('11111111-1111-1111-1111-111111111110'::uuid, '11111111-1111-1111-1111-111111111107'::uuid, '11111111-1111-1111-1111-111111111101'::uuid, 'Section B1-Reasoning');

insert into public.pyq_papers (id, exam_id, exam_phase_id, year)
values
  ('11111111-1111-1111-1111-111111111111'::uuid, '11111111-1111-1111-1111-111111111103'::uuid, '11111111-1111-1111-1111-111111111105'::uuid, 2026),
  ('11111111-1111-1111-1111-111111111112'::uuid, '11111111-1111-1111-1111-111111111104'::uuid, '11111111-1111-1111-1111-111111111107'::uuid, 2026);

-- ── Test 1: valid question + stimulus + link within the same phase/paper ───

insert into public.pyq_questions (id, pyq_paper_id, section_id, question_text)
values ('11111111-1111-1111-1111-111111111113'::uuid, '11111111-1111-1111-1111-111111111111'::uuid, '11111111-1111-1111-1111-111111111108'::uuid, 'valid question');

insert into public.pyq_stimuli (id, pyq_paper_id, section_id, content_text)
values ('11111111-1111-1111-1111-111111111114'::uuid, '11111111-1111-1111-1111-111111111111'::uuid, '11111111-1111-1111-1111-111111111108'::uuid, 'valid passage');

insert into public.pyq_question_stimuli (question_id, stimulus_id)
values ('11111111-1111-1111-1111-111111111113'::uuid, '11111111-1111-1111-1111-111111111114'::uuid);

do $$
begin
  raise notice 'PASS test 1: same-phase/same-paper question, stimulus and link all succeeded';
end;
$$;

-- ── Test 2: question.section_id from a different phase than its paper ─────

do $$
begin
  begin
    insert into public.pyq_questions (pyq_paper_id, section_id, question_text)
    values ('11111111-1111-1111-1111-111111111111'::uuid, '11111111-1111-1111-1111-111111111109'::uuid, 'cross-phase question');
    raise exception 'FAIL test 2: cross-phase question.section_id was accepted';
  exception
    when others then
      if sqlerrm like '%exam_phase does not match%' then
        raise notice 'PASS test 2: cross-phase question.section_id was rejected';
      else
        raise;
      end if;
  end;
end;
$$;

-- ── Test 3: stimulus.section_id from a different exam entirely ─────────────

do $$
begin
  begin
    insert into public.pyq_stimuli (pyq_paper_id, section_id, content_text)
    values ('11111111-1111-1111-1111-111111111111'::uuid, '11111111-1111-1111-1111-111111111110'::uuid, 'cross-exam passage');
    raise exception 'FAIL test 3: cross-exam stimulus.section_id was accepted';
  exception
    when others then
      if sqlerrm like '%exam_phase does not match%' then
        raise notice 'PASS test 3: cross-exam stimulus.section_id was rejected';
      else
        raise;
      end if;
  end;
end;
$$;

-- ── Test 4: question_stimuli link across two different papers ──────────────

do $$
declare
  v_other_question uuid;
begin
  insert into public.pyq_questions (pyq_paper_id, question_text)
  values ('11111111-1111-1111-1111-111111111112'::uuid, 'question in paper B')
  returning id into v_other_question;

  begin
    insert into public.pyq_question_stimuli (question_id, stimulus_id)
    values (v_other_question, '11111111-1111-1111-1111-111111111114'::uuid);
    raise exception 'FAIL test 4: cross-paper question_stimuli link was accepted';
  exception
    when others then
      if sqlerrm like '%across papers%' then
        raise notice 'PASS test 4: cross-paper question_stimuli link was rejected';
      else
        raise;
      end if;
  end;
end;
$$;

-- ── Test 5: moving a paper to a different exam phase after a section-scoped
--    question already exists under it must fail atomically ────────────────

do $$
begin
  begin
    update public.pyq_papers
      set exam_phase_id = '11111111-1111-1111-1111-111111111107'::uuid
      where id = '11111111-1111-1111-1111-111111111111'::uuid;
    raise exception 'FAIL test 5: moving a paper with section-scoped questions to a foreign phase was accepted';
  exception
    when others then
      if sqlerrm like '%would break pyq_questions.section_id integrity%' then
        raise notice 'PASS test 5: cross-phase paper move was rejected atomically';
      else
        raise;
      end if;
  end;
end;
$$;

ROLLBACK;
