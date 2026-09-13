-- 288_predictability_axis.sql
--
-- PRED-01 — predictability, a difficulty axis that works for descriptive papers.
-- Design: docs/status/2026-09-12-predictability-axis-design.md
--
-- `pyq_questions.observed_difficulty` is null on all 8,188 verified Mains
-- descriptive questions, deliberately: difficulty is judgeable for an MCQ and
-- meaningless for "Discuss the impact of globalisation on informal sector
-- workers", which has no answer key. `planner.py` reads that field, so today
-- it sequences Mains study on nothing.
--
-- Predictability is the axis that does mean something for a descriptive paper:
-- how reliably a topic recurs, measured over the years it was asked across
-- 8,302 questions spanning 1980-2026.
--
-- NEW COLUMNS, NOT A REUSE OF `observed_difficulty`. They are different claims
-- about different objects — difficulty is a property of a QUESTION,
-- predictability a property of a TOPIC. Overwriting one with the other would
-- make every existing consumer silently wrong. `observed_difficulty` stays
-- null on descriptive questions; that is honest, and a future rubric built for
-- descriptive answers may fill it one day.
--
-- Both tables get the pair because the value is derived in
-- `score_snapshots.py` and PROJECTED into `exam_topic_coverage` by
-- `coverage_derivation.py`, through the same review gates and the same lock as
-- every other derived evidence number.
--
-- NULL is meaningful: a topic with no year evidence (a syllabus-only coverage
-- row, or a topic carried by locked coverage alone) gets NULL rather than a
-- fabricated band.

alter table public.exam_topic_score_snapshots
  add column if not exists predictability numeric,
  add column if not exists predictability_band text;

alter table public.exam_topic_coverage
  add column if not exists predictability numeric,
  add column if not exists predictability_band text;

-- The four bands are a closed vocabulary a UI renders directly, so the
-- database is where the guarantee belongs. Deliberately NOT named for
-- likelihood of appearing ("will appear"): predictability says how a topic has
-- behaved, not what UPSC will do next.
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'exam_topic_score_snapshots_predictability_band_check'
  ) then
    alter table public.exam_topic_score_snapshots
      add constraint exam_topic_score_snapshots_predictability_band_check
      check (predictability_band is null
             or predictability_band in ('near_certain','likely','occasional','rare'));
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'exam_topic_coverage_predictability_band_check'
  ) then
    alter table public.exam_topic_coverage
      add constraint exam_topic_coverage_predictability_band_check
      check (predictability_band is null
             or predictability_band in ('near_certain','likely','occasional','rare'));
  end if;
end $$;

comment on column public.exam_topic_score_snapshots.predictability is
  'PRED-01: 0.65*breadth + 0.25*regularity + 0.10*recency over the years this '
  'topic was asked, within its own subject-paper''s evidence span. Not '
  'importance, not difficulty, not a forecast.';
comment on column public.exam_topic_score_snapshots.predictability_band is
  'PRED-01: percentile band within the subject-paper, floored upward by '
  'absolute breadth. The band is what a UI shows; the score sorts within it.';
comment on column public.exam_topic_coverage.predictability is
  'PRED-01: projected verbatim from the locked snapshot. Never recomputed here.';
comment on column public.exam_topic_coverage.predictability_band is
  'PRED-01: projected verbatim from the locked snapshot. Never recomputed here.';

notify pgrst, 'reload schema';
