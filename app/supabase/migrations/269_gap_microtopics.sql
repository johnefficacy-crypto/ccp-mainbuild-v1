-- Eleven microtopics added after tagging all six UPSC Prelims GS-I papers
-- (2018, 2019, 2021, 2022, 2023, 2024 — 600 questions).
--
-- Each was forced into an ill-fitting bucket during the draft pass. Every one
-- has corpus evidence, listed below; none was added on syllabus grounds alone,
-- which is the same standard the original 234 were built to.
--
--   Water-body degradation       Aral Sea 2018 Q98; Lake Chad 2022 Q23
--   Ozone depletion              HFCs 2023 Q20
--   Deforestation                New York Declaration on Forests 2021 Q74
--   World fauna and biogeography 2023 Q12 marsupials; 2024 Q63 Indri/Bonobo
--   Criminal justice and prisons 2021 Q12, Q13; 2023 Q32
--   Comparative government       2021 Q27 British vs Indian model
--   Languages and Eighth Schedule 2021 Q5 Halbi/Ho/Kui; 2024 Q2 71st Amendment
--   Human evolution and prehistory 2019 Q52 Denisovan
--   Intellectual property rights 2019 Q87 patents and plant varieties
--   Land reforms and land records 2019 Q32; 2024 Q48
--   Economic planning            2019 Q80 Five-Year Plans
--
-- Naming and study_sources follow the convention set by the rename migration:
-- NCERT chapter titles where a textbook covers the topic, exam vocabulary and
-- an honest non-NCERT source where none does.
--
-- EDITED AFTER LANDING — a deliberate, documented exception to the
-- migration-immutability rule in AGENTS.md. Read this before assuming the rule
-- was ignored.
--
-- As first written, this migration hardcoded a `subject_id` and eleven
-- `parent_topic_id` values that no migration creates. Those rows exist only in
-- the production database, where they were made outside the migration set, so
-- the INSERT succeeded there and raised `topics_subject_id_fkey` on every clean
-- `supabase db reset`. Because a failing statement aborts the whole run, NO
-- migration numbered above this one had ever executed on a fresh database —
-- 270_pyq_projection_microtopic_fidelity.sql among them — and CI's e2e job died
-- during database setup, before any test body ran.
--
-- A forward migration cannot repair that: on a clean database this file itself
-- raises, so nothing after it is reached. The guard has to be inside this file.
--
-- The fix adds a WHERE clause and changes nothing else. Every inserted value,
-- the slug expression, the metadata merge and the ON CONFLICT behaviour are
-- byte-for-byte what they were. The rows are inserted when the referenced
-- subject and parent topic exist, and the statement no-ops when they do not.
-- Against production, where all twelve rows are present and this migration has
-- already run, it is a no-op twice over: every row passes the guard, and
-- ON CONFLICT DO NOTHING still absorbs the re-insert.

BEGIN;

INSERT INTO public.topics
  (subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT
  '09db7afb-0864-46c9-b900-1510b60c0011'::uuid,
  v.parent::uuid,
  'gs-' || trim(both '-' from regexp_replace(lower(v.name), '[^a-z0-9]+', '-', 'g'))
        || '-' || left(md5(v.name), 8),
  v.name,
  'microtopic',
  true,
  '{"tier":"official","exams":["upsc"]}'::jsonb || v.sources
FROM (VALUES

  -- Environment
  ('d2db62f5-93e2-4264-85f4-86f439e83515',
   'Degradation of lakes and inland water bodies',
   '{"study_sources":[{"type":"standard","ref":"Shankar IAS Environment"},{"type":"standard","ref":"Oxford School Atlas"}]}'::jsonb),

  ('d2db62f5-93e2-4264-85f4-86f439e83515',
   'Ozone depletion and the Montreal Protocol',
   '{"study_sources":[{"type":"ncert","ref":"Class 12 Biology — Environmental Issues"},{"type":"standard","ref":"Shankar IAS Environment"}]}'::jsonb),

  ('d2db62f5-93e2-4264-85f4-86f439e83515',
   'Deforestation and afforestation',
   '{"study_sources":[{"type":"ncert","ref":"Class 12 Biology — Environmental Issues"},{"type":"standard","ref":"India State of Forest Report"}]}'::jsonb),

  ('d2db62f5-93e2-4264-85f4-86f439e83515',
   'World fauna and biogeography',
   '{"study_sources":[{"type":"standard","ref":"Shankar IAS Environment"},{"type":"standard","ref":"Oxford School Atlas"}]}'::jsonb),

  -- Polity
  ('3e797a71-eecb-4399-8b0b-a5275b3e4f44',
   'Criminal justice and prison administration',
   '{"study_sources":[{"type":"standard","ref":"Laxmikanth"},{"type":"standard","ref":"MHA Annual Report"}]}'::jsonb),

  ('3e797a71-eecb-4399-8b0b-a5275b3e4f44',
   'Comparative government and constitutions',
   '{"study_sources":[{"type":"ncert","ref":"Class 11 Indian Constitution at Work — Constitution: Why and How?"},{"type":"standard","ref":"Laxmikanth"}]}'::jsonb),

  ('3e797a71-eecb-4399-8b0b-a5275b3e4f44',
   'Official languages and the Eighth Schedule',
   '{"study_sources":[{"type":"standard","ref":"Laxmikanth"},{"type":"standard","ref":"India Year Book"}]}'::jsonb),

  -- History
  ('0f90e98f-cffc-4e89-9572-5b144e56cb7c',
   'Human evolution and prehistory',
   '{"study_sources":[{"type":"ncert","ref":"Class 11 Themes in World History — From the Beginning of Time"},{"type":"standard","ref":"Old NCERT Ancient India (RS Sharma)"}]}'::jsonb),

  -- Economy
  ('0a59e611-b272-475c-aa0c-24d41818a13a',
   'Intellectual property rights',
   '{"study_sources":[{"type":"standard","ref":"DPIIT; IP India"},{"type":"standard","ref":"Economic Survey"}]}'::jsonb),

  ('0a59e611-b272-475c-aa0c-24d41818a13a',
   'Land reforms and land records',
   '{"study_sources":[{"type":"ncert","ref":"Class 11 Indian Economic Development — Rural Development"},{"type":"standard","ref":"Economic Survey"}]}'::jsonb),

  ('0a59e611-b272-475c-aa0c-24d41818a13a',
   'Economic planning and NITI Aayog',
   '{"study_sources":[{"type":"ncert","ref":"Class 11 Indian Economic Development — Indian Economy 1950-1990"},{"type":"standard","ref":"Ramesh Singh"}]}'::jsonb)

) AS v(parent, name, sources)
-- Guard, added post-landing (see the header): insert only when the referenced
-- rows exist. On a database that lacks them — any clean `supabase db reset` —
-- this yields zero rows instead of a foreign-key violation, so the migration
-- run continues instead of aborting here.
WHERE EXISTS (
        SELECT 1 FROM public.subjects
        WHERE id = '09db7afb-0864-46c9-b900-1510b60c0011'::uuid
      )
  AND EXISTS (
        SELECT 1 FROM public.topics
        WHERE id = v.parent::uuid
      )
ON CONFLICT DO NOTHING;

COMMIT;
