-- Migration 284: return 19 RBI questions that migration 281 pulled by mistake.
--
-- 281 flagged 85 RBI questions as asking about context that was not in the
-- database. Reading the newly committed source PDFs against them shows 19
-- of those were never orphans: RBI 2023 11, RBI 2024 5, RBI 2025 3. All 19
-- were verified before 281 and are returned to verified here, with their
-- option rows.
--
-- WHY THE DETECTOR WAS WRONG, and it is worth being precise because the
-- same rule found 65 real orphans in the 2022 paper. It flags a short stem
-- that points at content it does not contain -- "the given information",
-- "equation I", "the passage". That is exactly right when the loader
-- dropped the shared block, which is what happened to the 2022 paper. It is
-- exactly wrong when the loader MERGED the block into every stem in its
-- range, which is what happened to 2023, 2024 and 2025: the stem says "Read
-- the given information" and then gives it.
--
-- Checked rather than assumed. The 2023 sources carry 16 "Instruction for
-- Q.x to Q.y" blocks covering 67 questions; every one of those 67 stems
-- already contains the first 60 characters of its own block. 67 of 67, none
-- missing. The five 2023 orphans outside any block (Q.103, Q.105, Q.106,
-- Q.142, Q.152) carry their own statements or word lists inline. For 2024
-- and 2025 each flagged stem was located in the source and the 300
-- characters printed immediately before it read as the previous question's
-- options or explanation -- no block was dropped because none precedes
-- them.
--
-- ROWS RETURNED, with the phrase that misled the detector:
--   RBI 2023 Q103  English Language       'Four statements have been mentioned below. One or mo'
--   RBI 2023 Q105  English Language       'Which of the following sentences from the options gi'
--   RBI 2023 Q106  English Language       'Which of the following sentences from the options gi'
--   RBI 2023 Q118  Quantitative Aptitude  'Read the given information and answer the below ques'
--   RBI 2023 Q119  Quantitative Aptitude  'Read the given information and answer the below ques'
--   RBI 2023 Q142  Reasoning              'Consider the following words which have one blank ea'
--   RBI 2023 Q148  Reasoning              'Read the given information and answer the below ques'
--   RBI 2023 Q149  Reasoning              'Read the given information and answer the below ques'
--   RBI 2023 Q150  Reasoning              'Read the given information and answer the below ques'
--   RBI 2023 Q151  Reasoning              'Read the given information and answer the below ques'
--   RBI 2023 Q152  Reasoning              'Which of the following symbols should be placed in t'
--   RBI 2024 Q98   English Language       'In the following question, two sentences are given w'
--   RBI 2024 Q99   English Language       'In the following question, two sentences are given w'
--   RBI 2024 Q100  English Language       'In the following question, two sentences are given w'
--   RBI 2024 Q101  English Language       'In the following question, two sentences are given w'
--   RBI 2024 Q114  Quantitative Aptitude  'Consider the below statement and the two quantities '
--   RBI 2025 Q103  English Language       '(A) She drafted a list of interview questions to kee'
--   RBI 2025 Q182  Reasoning              'A young entrepreneur started a small online bookstor'
--   RBI 2025 Q183  Reasoning              'A village once known for its beautiful lake saw a gr'
--
-- RBI 2026 Q.191 was also flagged and is NOT returned. It is a real defect,
-- just a different one: its stem begins "numbered I and II given below it",
-- mid-sentence. The 2026 loader merged each Directions block into its stems
-- but lost the opening clause of every block, so that stem is missing
-- "Directions (190-193) - Each of the following consists of a question and
-- two statements". 92 of the 191 questions on that paper start mid-sentence
-- the same way, 89 of them verified and live. That is its own repair and
-- its own migration; see the commit message for the measurement.
--
-- Papers touched: three, one per year. All are projected and live.
-- Returning a row to verified does not republish it -- the projection re-
-- sync is what does, and it should run for RBI 2023, 2024 and 2025 after
-- this.
--
-- Guarded on the current value: only rows still sitting at needs_correction
-- move, so a re-run changes nothing and a row someone has since re-judged
-- is left alone.

BEGIN;

-- 1. The 19 questions.
UPDATE public.pyq_questions
SET reviewer_status = 'verified'
WHERE id IN (
  '0a6d3b53-6b00-47fe-b43a-13b11939310e'::uuid,
  '94f4d0c9-6c1d-4fea-8761-2ccf950b36ae'::uuid,
  '5122b512-4b68-4add-9d15-fb5775115791'::uuid,
  'df539926-f76c-4c08-8ed0-22f49d805132'::uuid,
  'b8f86f97-9131-4c8b-b334-7f220baaa706'::uuid,
  '358e221c-e8b9-43e9-8b2f-80f8a1750fe0'::uuid,
  '234dbd84-5690-4873-9ac0-92874577d847'::uuid,
  '348de0ca-be8d-4580-beb7-30ba88ce609c'::uuid,
  '62d64907-3c6a-4f28-b4d5-03956073b837'::uuid,
  '3f7eaa2b-ee6a-43ab-accc-e9730ebed8c6'::uuid,
  'd78ba3ec-9208-4d76-849c-d69ba1fee4c5'::uuid,
  'df732dd2-9004-4cf5-9564-56ef550a32e8'::uuid,
  'bbdf93eb-5496-4f5e-bf3e-1edd996041d9'::uuid,
  '611b5a1c-39bd-4acc-9e12-b17b06cb9c53'::uuid,
  '1ddec204-5695-48db-ad75-f7bcec84e13f'::uuid,
  '136a515e-a171-4d1d-807c-45b6ca4cdc71'::uuid,
  '9fafc648-0993-4b27-8e59-9a27f5692f29'::uuid,
  '3693ea82-21f2-457b-9269-3f103d8e1397'::uuid,
  '72955a07-053e-4eff-ad60-208a536b5e46'::uuid
)
  AND reviewer_status = 'needs_correction';

-- 2. Their option rows, which 281 cascaded to.
UPDATE public.pyq_options
SET reviewer_status = 'verified'
WHERE question_id IN (
  '0a6d3b53-6b00-47fe-b43a-13b11939310e'::uuid,
  '94f4d0c9-6c1d-4fea-8761-2ccf950b36ae'::uuid,
  '5122b512-4b68-4add-9d15-fb5775115791'::uuid,
  'df539926-f76c-4c08-8ed0-22f49d805132'::uuid,
  'b8f86f97-9131-4c8b-b334-7f220baaa706'::uuid,
  '358e221c-e8b9-43e9-8b2f-80f8a1750fe0'::uuid,
  '234dbd84-5690-4873-9ac0-92874577d847'::uuid,
  '348de0ca-be8d-4580-beb7-30ba88ce609c'::uuid,
  '62d64907-3c6a-4f28-b4d5-03956073b837'::uuid,
  '3f7eaa2b-ee6a-43ab-accc-e9730ebed8c6'::uuid,
  'd78ba3ec-9208-4d76-849c-d69ba1fee4c5'::uuid,
  'df732dd2-9004-4cf5-9564-56ef550a32e8'::uuid,
  'bbdf93eb-5496-4f5e-bf3e-1edd996041d9'::uuid,
  '611b5a1c-39bd-4acc-9e12-b17b06cb9c53'::uuid,
  '1ddec204-5695-48db-ad75-f7bcec84e13f'::uuid,
  '136a515e-a171-4d1d-807c-45b6ca4cdc71'::uuid,
  '9fafc648-0993-4b27-8e59-9a27f5692f29'::uuid,
  '3693ea82-21f2-457b-9269-3f103d8e1397'::uuid,
  '72955a07-053e-4eff-ad60-208a536b5e46'::uuid
)
  AND reviewer_status = 'needs_correction';

-- 3. Drop the note 281 wrote; it no longer describes these rows.
UPDATE public.pyq_questions
SET metadata = metadata - 'orphaned_context'
WHERE id IN (
  '0a6d3b53-6b00-47fe-b43a-13b11939310e'::uuid,
  '94f4d0c9-6c1d-4fea-8761-2ccf950b36ae'::uuid,
  '5122b512-4b68-4add-9d15-fb5775115791'::uuid,
  'df539926-f76c-4c08-8ed0-22f49d805132'::uuid,
  'b8f86f97-9131-4c8b-b334-7f220baaa706'::uuid,
  '358e221c-e8b9-43e9-8b2f-80f8a1750fe0'::uuid,
  '234dbd84-5690-4873-9ac0-92874577d847'::uuid,
  '348de0ca-be8d-4580-beb7-30ba88ce609c'::uuid,
  '62d64907-3c6a-4f28-b4d5-03956073b837'::uuid,
  '3f7eaa2b-ee6a-43ab-accc-e9730ebed8c6'::uuid,
  'd78ba3ec-9208-4d76-849c-d69ba1fee4c5'::uuid,
  'df732dd2-9004-4cf5-9564-56ef550a32e8'::uuid,
  'bbdf93eb-5496-4f5e-bf3e-1edd996041d9'::uuid,
  '611b5a1c-39bd-4acc-9e12-b17b06cb9c53'::uuid,
  '1ddec204-5695-48db-ad75-f7bcec84e13f'::uuid,
  '136a515e-a171-4d1d-807c-45b6ca4cdc71'::uuid,
  '9fafc648-0993-4b27-8e59-9a27f5692f29'::uuid,
  '3693ea82-21f2-457b-9269-3f103d8e1397'::uuid,
  '72955a07-053e-4eff-ad60-208a536b5e46'::uuid
)
  AND metadata ? 'orphaned_context';

COMMIT;
