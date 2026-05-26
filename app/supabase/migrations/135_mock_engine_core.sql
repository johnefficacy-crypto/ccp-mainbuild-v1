-- =============================================================================
-- 135_mock_engine_core.sql
-- Mock Engine PR1: server-authoritative attempt loop.
--
-- Tables:
--   mock_templates           — exam template metadata + config
--   mock_question_bank       — question registry (content + scoring rules)
--   mock_question_options    — answer choices per question
--   mock_attempts            — one per user-template active attempt
--   mock_attempt_responses   — per-question answer state within an attempt
--
-- Design rules:
--   * template_snapshot / question_snapshot are frozen JSONB at attempt-start.
--     Scoring always reads from these snapshots, never live tables.
--   * Partial unique index enforces exactly one in_progress attempt per
--     (user_id, template_id) pair — second start → 409.
--   * expires_at = started_at + duration_sec (server clock only).
--   * RLS: aspirants see their own attempts; admins see all.
--
-- Idempotent: safe on fresh DB and re-runnable on existing.
-- =============================================================================

-- ── 1. Types ──────────────────────────────────────────────────────────────────
do $$ begin
  create type mock_attempt_status as enum ('in_progress','submitted','abandoned');
exception when duplicate_object then null; end $$;

do $$ begin
  create type mock_question_type as enum ('mcq','integer','msq');
exception when duplicate_object then null; end $$;

do $$ begin
  create type mock_template_status as enum ('draft','active','archived');
exception when duplicate_object then null; end $$;

do $$ begin
  create type mock_reviewer_status as enum ('draft','reviewed','locked');
exception when duplicate_object then null; end $$;

-- ── 2. mock_templates ─────────────────────────────────────────────────────────
create table if not exists public.mock_templates (
  id                  uuid primary key default gen_random_uuid(),
  slug                text not null unique,
  name                text not null,
  exam_family         text,
  exam_id             uuid references public.exams(id) on delete set null,
  total_questions     int not null default 0,
  duration_sec        int not null default 3600,
  negative_marking    boolean not null default true,
  marks_per_correct   numeric(6,2) not null default 1,
  marks_per_wrong     numeric(6,2) not null default 0.25,
  config              jsonb not null default '{}',
  status              mock_template_status not null default 'active',
  created_at          timestamptz not null default now()
);

-- ── 3. mock_question_bank ─────────────────────────────────────────────────────
create table if not exists public.mock_question_bank (
  id                  uuid primary key default gen_random_uuid(),
  exam_family         text,
  exam_id             uuid references public.exams(id) on delete set null,
  subject_id          uuid references public.subjects(id) on delete set null,
  topic_id            uuid references public.topics(id) on delete set null,
  microtopic_id       uuid,
  question_text       text not null,
  question_type       mock_question_type not null default 'mcq',
  difficulty          text check (difficulty in ('easy','medium','hard')),
  marks               numeric(6,2) not null default 1,
  negative_marks      numeric(6,2) not null default 0.25,
  correct_option_id   uuid,
  explanation         text,
  language            text not null default 'en',
  source_type         text,
  reviewer_status     mock_reviewer_status not null default 'reviewed',
  expected_time_sec   int,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

-- ── 4. mock_question_options ──────────────────────────────────────────────────
create table if not exists public.mock_question_options (
  id              uuid primary key default gen_random_uuid(),
  question_id     uuid not null references public.mock_question_bank(id) on delete cascade,
  option_text     text not null,
  option_index    int not null,
  is_correct      boolean not null default false
);

create unique index if not exists uq_mqo_question_index
  on public.mock_question_options(question_id, option_index);

-- ── 5. mock_attempts ─────────────────────────────────────────────────────────
create table if not exists public.mock_attempts (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references auth.users(id) on delete cascade,
  template_id         uuid not null references public.mock_templates(id) on delete restrict,
  template_snapshot   jsonb not null,
  status              mock_attempt_status not null default 'in_progress',
  started_at          timestamptz not null default now(),
  expires_at          timestamptz not null,
  submitted_at        timestamptz,
  score_raw           numeric(8,2),
  score_percentage    numeric(6,2),
  total_correct       int,
  total_wrong         int,
  total_unattempted   int,
  created_at          timestamptz not null default now()
);

-- Enforce one active attempt per (user_id, template_id).
create unique index if not exists uq_mock_attempts_active
  on public.mock_attempts(user_id, template_id)
  where status = 'in_progress';

-- ── 6. mock_attempt_responses ─────────────────────────────────────────────────
create table if not exists public.mock_attempt_responses (
  id                    uuid primary key default gen_random_uuid(),
  attempt_id            uuid not null references public.mock_attempts(id) on delete cascade,
  question_id           uuid not null references public.mock_question_bank(id) on delete restrict,
  question_snapshot     jsonb not null,
  selected_option_id    uuid,
  is_marked_for_review  boolean not null default false,
  is_visited            boolean not null default false,
  time_spent_sec        int not null default 0,
  is_correct            boolean,
  marks_awarded         numeric(6,2),
  client_seq            int not null default 0,
  updated_at            timestamptz not null default now()
);

create unique index if not exists uq_mar_attempt_question
  on public.mock_attempt_responses(attempt_id, question_id);

-- ── 7. Indexes ────────────────────────────────────────────────────────────────
create index if not exists idx_mock_attempts_user_id on public.mock_attempts(user_id);
create index if not exists idx_mock_attempts_template_id on public.mock_attempts(template_id);
create index if not exists idx_mock_attempt_responses_attempt_id on public.mock_attempt_responses(attempt_id);
create index if not exists idx_mock_question_bank_exam_id on public.mock_question_bank(exam_id);
create index if not exists idx_mock_question_options_question_id on public.mock_question_options(question_id);

-- ── 8. RLS ────────────────────────────────────────────────────────────────────
alter table public.mock_templates enable row level security;
alter table public.mock_question_bank enable row level security;
alter table public.mock_question_options enable row level security;
alter table public.mock_attempts enable row level security;
alter table public.mock_attempt_responses enable row level security;

-- Templates: all authenticated users can read active templates.
drop policy if exists "mock_templates_read_active" on public.mock_templates;
create policy "mock_templates_read_active"
  on public.mock_templates for select
  using (status = 'active');

-- Question bank: authenticated users read reviewed/locked questions.
drop policy if exists "mock_question_bank_read_reviewed" on public.mock_question_bank;
create policy "mock_question_bank_read_reviewed"
  on public.mock_question_bank for select
  using (reviewer_status in ('reviewed','locked'));

-- Question options: readable alongside question bank.
drop policy if exists "mock_question_options_read" on public.mock_question_options;
create policy "mock_question_options_read"
  on public.mock_question_options for select
  using (true);

-- Attempts: users see only their own; admins see all.
drop policy if exists "mock_attempts_user_own" on public.mock_attempts;
create policy "mock_attempts_user_own"
  on public.mock_attempts for all
  using (
    user_id = auth.uid()
    or (auth.jwt()->'app_metadata'->>'role') in ('admin','super_admin')
  );

-- Responses: user sees own attempt's responses.
drop policy if exists "mock_attempt_responses_user_own" on public.mock_attempt_responses;
create policy "mock_attempt_responses_user_own"
  on public.mock_attempt_responses for all
  using (
    attempt_id in (
      select id from public.mock_attempts
      where user_id = auth.uid()
    )
    or (auth.jwt()->'app_metadata'->>'role') in ('admin','super_admin')
  );

-- ── 9. Seed: IBPS PO Prelims Mock 1 ─────────────────────────────────────────
-- One template + 20 reviewed questions (English/Quant/Reasoning).
-- Questions are fully self-contained seeds — no FK to subjects/topics required.
-- subject_id / topic_id columns left null for seed simplicity (PR1 has no
-- section breakdown; those are added in PR4).

do $$
declare
  v_template_id uuid;
  v_q1  uuid; v_q2  uuid; v_q3  uuid; v_q4  uuid; v_q5  uuid;
  v_q6  uuid; v_q7  uuid; v_q8  uuid; v_q9  uuid; v_q10 uuid;
  v_q11 uuid; v_q12 uuid; v_q13 uuid; v_q14 uuid; v_q15 uuid;
  v_q16 uuid; v_q17 uuid; v_q18 uuid; v_q19 uuid; v_q20 uuid;
  v_o uuid;
begin
  -- Template
  insert into public.mock_templates(slug, name, exam_family, total_questions, duration_sec, negative_marking, marks_per_correct, marks_per_wrong, status)
  values ('ibps-po-prelims-mock-1', 'IBPS PO Prelims Mock 1', 'IBPS', 20, 1200, true, 1, 0.25, 'active')
  on conflict (slug) do nothing
  returning id into v_template_id;

  if v_template_id is null then
    select id into v_template_id from public.mock_templates where slug = 'ibps-po-prelims-mock-1';
    -- Already seeded — skip question seeding to stay idempotent.
    return;
  end if;

  -- ── English (Q1–7) ──────────────────────────────────────────────────────

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Choose the correct synonym of ABUNDANT.', 'mcq', 'easy', 1, 0.25, 'Plentiful is the correct synonym.', 'reviewed')
  returning id into v_q1;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q1, 'Scarce', 1, false), (v_q1, 'Plentiful', 2, true),
    (v_q1, 'Sparse', 3, false), (v_q1, 'Meagre', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q1 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q1;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Select the antonym of LUCID.', 'mcq', 'easy', 1, 0.25, 'Vague is the antonym of lucid.', 'reviewed')
  returning id into v_q2;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q2, 'Clear', 1, false), (v_q2, 'Transparent', 2, false),
    (v_q2, 'Vague', 3, true), (v_q2, 'Obvious', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q2 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q2;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Fill in the blank: She was ______ by the enormous workload.', 'mcq', 'medium', 1, 0.25, 'Overwhelmed fits the context.', 'reviewed')
  returning id into v_q3;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q3, 'Energised', 1, false), (v_q3, 'Overwhelmed', 2, true),
    (v_q3, 'Thrilled', 3, false), (v_q3, 'Comforted', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q3 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q3;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Identify the correctly spelt word.', 'mcq', 'easy', 1, 0.25, 'Occurrence is the correct spelling.', 'reviewed')
  returning id into v_q4;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q4, 'Occurance', 1, false), (v_q4, 'Occurence', 2, false),
    (v_q4, 'Occurrence', 3, true), (v_q4, 'Occurrance', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q4 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q4;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Choose the correctly punctuated sentence.', 'mcq', 'medium', 1, 0.25, 'Option B uses a comma correctly before the conjunction in a compound sentence.', 'reviewed')
  returning id into v_q5;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q5, 'She left early, and he stayed late.', 1, true),
    (v_q5, 'She left early and, he stayed late.', 2, false),
    (v_q5, 'She left, early and he stayed late.', 3, false),
    (v_q5, 'She left early and he, stayed late.', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q5 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q5;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'The phrase "to burn the midnight oil" means:', 'mcq', 'easy', 1, 0.25, 'It means to work or study late into the night.', 'reviewed')
  returning id into v_q6;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q6, 'To waste fuel', 1, false),
    (v_q6, 'To work late at night', 2, true),
    (v_q6, 'To be careless', 3, false),
    (v_q6, 'To celebrate', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q6 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q6;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Which sentence is in passive voice? I. The teacher praised the student. II. The student was praised by the teacher.', 'mcq', 'easy', 1, 0.25, 'Sentence II uses passive voice.', 'reviewed')
  returning id into v_q7;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q7, 'Only I', 1, false), (v_q7, 'Only II', 2, true),
    (v_q7, 'Both I and II', 3, false), (v_q7, 'Neither', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q7 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q7;

  -- ── Quantitative Aptitude (Q8–14) ────────────────────────────────────────

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'A train covers 360 km in 4 hours. What is its speed in km/h?', 'mcq', 'easy', 1, 0.25, 'Speed = 360 / 4 = 90 km/h.', 'reviewed')
  returning id into v_q8;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q8, '80', 1, false), (v_q8, '90', 2, true),
    (v_q8, '100', 3, false), (v_q8, '72', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q8 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q8;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'If 20% of a number is 50, what is the number?', 'mcq', 'easy', 1, 0.25, '50 / 0.20 = 250.', 'reviewed')
  returning id into v_q9;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q9, '200', 1, false), (v_q9, '250', 2, true),
    (v_q9, '300', 3, false), (v_q9, '150', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q9 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q9;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Simple interest on ₹5000 at 8% per annum for 3 years is:', 'mcq', 'medium', 1, 0.25, 'SI = 5000 × 8 × 3 / 100 = ₹1200.', 'reviewed')
  returning id into v_q10;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q10, '₹1000', 1, false), (v_q10, '₹1200', 2, true),
    (v_q10, '₹1500', 3, false), (v_q10, '₹1100', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q10 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q10;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'A can do work in 12 days, B in 18 days. Together they finish in:', 'mcq', 'medium', 1, 0.25, '1/12 + 1/18 = 5/36 per day → 36/5 = 7.2 days.', 'reviewed')
  returning id into v_q11;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q11, '7 days', 1, false), (v_q11, '7.2 days', 2, true),
    (v_q11, '8 days', 3, false), (v_q11, '6 days', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q11 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q11;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'The ratio of boys to girls is 3:2. If there are 30 boys, how many girls?', 'mcq', 'easy', 1, 0.25, '30/3 × 2 = 20 girls.', 'reviewed')
  returning id into v_q12;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q12, '15', 1, false), (v_q12, '20', 2, true),
    (v_q12, '25', 3, false), (v_q12, '18', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q12 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q12;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'What is the LCM of 12 and 18?', 'mcq', 'easy', 1, 0.25, 'LCM(12,18) = 36.', 'reviewed')
  returning id into v_q13;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q13, '24', 1, false), (v_q13, '36', 2, true),
    (v_q13, '72', 3, false), (v_q13, '6', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q13 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q13;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'A shopkeeper gives 10% discount on ₹500. Final price?', 'mcq', 'easy', 1, 0.25, '500 × 0.90 = ₹450.', 'reviewed')
  returning id into v_q14;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q14, '₹400', 1, false), (v_q14, '₹450', 2, true),
    (v_q14, '₹460', 3, false), (v_q14, '₹480', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q14 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q14;

  -- ── Reasoning (Q15–20) ───────────────────────────────────────────────────

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Series: 2, 6, 12, 20, 30, __?', 'mcq', 'easy', 1, 0.25, 'Differences: 4,6,8,10,12 → next = 42.', 'reviewed')
  returning id into v_q15;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q15, '36', 1, false), (v_q15, '40', 2, false),
    (v_q15, '42', 3, true), (v_q15, '44', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q15 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q15;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'If MANGO is coded as OCPIQ, then GRAPE is coded as?', 'mcq', 'medium', 1, 0.25, 'Each letter is shifted +2 → ITCRG.', 'reviewed')
  returning id into v_q16;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q16, 'HSASD', 1, false), (v_q16, 'ITCRG', 2, true),
    (v_q16, 'JSDTH', 3, false), (v_q16, 'HSBQF', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q16 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q16;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Choose the odd one out: Apple, Mango, Carrot, Banana.', 'mcq', 'easy', 1, 0.25, 'Carrot is a vegetable; the rest are fruits.', 'reviewed')
  returning id into v_q17;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q17, 'Apple', 1, false), (v_q17, 'Mango', 2, false),
    (v_q17, 'Carrot', 3, true), (v_q17, 'Banana', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q17 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q17;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'Pointing to a woman, Ram says, "She is the mother of my father''s only son." How is the woman related to Ram?', 'mcq', 'medium', 1, 0.25, 'Mother of Ram''s father''s only son = Ram''s mother.', 'reviewed')
  returning id into v_q18;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q18, 'Sister', 1, false), (v_q18, 'Mother', 2, true),
    (v_q18, 'Aunt', 3, false), (v_q18, 'Wife', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q18 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q18;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'A is taller than B; B is taller than C; D is taller than A. Who is the tallest?', 'mcq', 'easy', 1, 0.25, 'D > A > B > C, so D is tallest.', 'reviewed')
  returning id into v_q19;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q19, 'A', 1, false), (v_q19, 'B', 2, false),
    (v_q19, 'C', 3, false), (v_q19, 'D', 4, true);
  select id into v_o from public.mock_question_options where question_id = v_q19 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q19;

  insert into public.mock_question_bank(id, exam_family, question_text, question_type, difficulty, marks, negative_marks, explanation, reviewer_status)
  values (gen_random_uuid(), 'IBPS', 'In a row of 40 students, Riya is 15th from the left. What is her position from the right?', 'mcq', 'easy', 1, 0.25, '40 - 15 + 1 = 26.', 'reviewed')
  returning id into v_q20;
  insert into public.mock_question_options(question_id, option_text, option_index, is_correct) values
    (v_q20, '24th', 1, false), (v_q20, '25th', 2, false),
    (v_q20, '26th', 3, true), (v_q20, '27th', 4, false);
  select id into v_o from public.mock_question_options where question_id = v_q20 and is_correct;
  update public.mock_question_bank set correct_option_id = v_o where id = v_q20;

  -- ── Link questions to template via config ─────────────────────────────────
  update public.mock_templates
  set
    total_questions = 20,
    config = jsonb_build_object(
      'question_ids', jsonb_build_array(
        v_q1, v_q2, v_q3, v_q4, v_q5, v_q6, v_q7,
        v_q8, v_q9, v_q10, v_q11, v_q12, v_q13, v_q14,
        v_q15, v_q16, v_q17, v_q18, v_q19, v_q20
      )
    )
  where id = v_template_id;

end $$;
