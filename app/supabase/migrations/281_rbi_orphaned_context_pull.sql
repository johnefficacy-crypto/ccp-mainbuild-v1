-- Migration 281: pull 71 unanswerable RBI Grade B questions off learners.
--
-- 85 RBI questions ask about a passage, a puzzle setup, a coded-language
-- sample, a data block or an equation that is not in the question and is
-- not stored anywhere. 71 of them are reviewer_status 'verified' and live
-- to aspirants right now. This migration sets all 85, and their option
-- rows, to 'needs_correction'.
--
-- The remaining 14 are already 'needs_correction' and are included only so
-- the metadata note lands on them too; the status guard makes those a no-
-- op. Nothing here is 'pending' -- every row is either live or already
-- flagged.
--
-- WHY THESE 85. RBI's orphans were previously found by regex on stem
-- keywords -- stems that mention "the passage" or "the author". That method
-- found 28. It is the same method that found 28 of NABARD's 129, and it
-- fails the same way: a sibling question in the same set does not mention
-- the missing thing. Two detectors were used instead. (1) Back-reference: a
-- stem under 500 characters pointing at content it does not contain -- the
-- passage, the author, step IV, series (A), equation I, a numbered blank,
-- the data given below. (2) Set-run: two or more consecutive question
-- numbers in one paper and section whose stems are all under 250 characters
-- and carry no declarative setup of their own. Every run the second
-- detector produced was then read by hand, and three were thrown out as
-- self-contained: RBI 2023 English Q.105-106 carries its sentences inside
-- the options, RBI 2025 QA Q.121-123 prints its number series, RBI 2026 QA
-- Q.133-140 prints its arithmetic. The 85 below are what survived.
--
-- NO STIMULI ANYWHERE. All five RBI exports carry an empty
-- stimuli_export.json -- 879 questions, 0 stimulus rows, 0 links. So these
-- passages are not merely absent from the stem; they are absent from the
-- database. There is no view in which a learner can see them.
--
-- THE PULL IS AUTOMATIC, and this matters. Trigger
-- trg_invalidate_pyq_projection_q (migration 184) fires on pyq_questions
-- UPDATE when reviewer_status leaves 'verified', calling
-- fn_invalidate_projection_for_question, which sets
-- pyq_mock_question_projections.sync_status to 'stale' AND demotes
-- mock_question_bank.reviewer_status from verified/published/live to
-- 'draft'. So statement 1 removes these rows from learners inside its own
-- transaction. The option UPDATE fires the equivalent option trigger,
-- idempotently. A projection re-sync afterwards is still worth running --
-- it makes the projection record agree with the gate and reports each row
-- as blocked with reason 'question_not_verified' -- but the learner-facing
-- pull does not wait for it.
--
-- REVIEWED_BY AND REVIEWED_AT ARE LEFT ALONE. These rows were verified by a
-- person; overwriting that with a migration would destroy the provenance of
-- the original review. The flag and its reason go into metadata under
-- 'orphaned_context' with a timestamp, which is additive and reversible.
--
-- PAPERS TOUCHED: 5
--   06712b2e-5003-4d97-9d77-968c0e5be20d  RBI 2022    65 rows,  51 verified
--   e6019bda-45f7-43bf-96d8-aac6f91f383f  RBI 2023    11 rows,  11 verified
--   ba80e989-e6a2-46e2-98da-8da5966e16bf  RBI 2024     5 rows,   5 verified
--   6b4c47a8-6488-4729-83ec-ae0c2e9e410a  RBI 2025     3 rows,   3 verified
--   a2cf30d7-354f-4f88-ac7f-182206519104  RBI 2026     1 rows,   1 verified
--
-- THE 34 SETS, what each is missing, and every row in it:
--
-- RBI 2022 English Language Q.1-10  (10 rows, 2 verified)
--   MISSING: the reading passage(s) for Q.1-8 and the sentence list for the
--   Q.9-10 rearrangement
--   need  Q1    7ab77868-58c2-48cd-ab52-a365a4e0beec  'What can be inferred about the economy of the world from t'
--   veri  Q2    ef384cab-d616-4299-8b68-78568d1dca8c  'Which of the following was/were the objectives of the off '
--   veri  Q3    352bd671-f233-4053-8a94-f5cce5050c70  'Which of the following come(s) under the changes introduce'
--   need  Q4    b6c1b177-a3d2-4ed8-8ae3-245e80d9fe1f  'Which of the following if correct, most invalidates the ar'
--   need  Q5    b3de135a-e124-4dec-a1aa-90585abbdb45  'Which of the following is true according to the data in th'
--   need  Q6    75123782-9979-4c2d-8a7d-73120c797eef  'What is the primary focus of the author in the passage?'
--   need  Q7    df63317c-bdab-4271-9c5a-1b2c2982830c  'From among the following given options, choose the word mo'
--   need  Q8    c6e7a666-52f0-4cd0-b42c-4d3c78066736  'Which of the following words is most opposite in meaning t'
--   need  Q9    25a6d571-f42d-4421-af84-c420f787c889  'Which is the fourth sentence after rearrangement?'
--   need  Q10   a59096b1-7614-42ee-a16c-069d2091d0a7  'What is the correct rearrangement of the given sentences?'
--
-- RBI 2022 English Language Q.14-19  (6 rows, 6 verified)
--   MISSING: the sentence-completion context printed above the set
--   veri  Q14   25c14b8a-2690-493f-b413-f37607227515  'The king released the lion from its cage into the arena wh'
--   veri  Q15   e68143e6-4333-414e-bf1c-493ff2df62f7  'Observing all the reports, the supervisor noted that the p'
--   veri  Q16   8bf962d0-59b7-4432-9b0b-ed8cc1c4d8fd  'As soon as he entered the room, he was unable to see anyth'
--   veri  Q17   5d56b020-e123-4f86-9b50-0838afcb3334  'Noticing how the dimensions of the bridge were different t'
--   veri  Q18   82f16a8f-5894-446b-b16c-b2a82a0f8697  '(i) BIMSTEC has, finally, taken measures to strengthen the'
--   veri  Q19   4ff3c2c3-6c64-4d6c-bf0f-447aa3183c49  '(i) Earlier in March, Musk said he would put the deal "tem'
--
-- RBI 2022 English Language Q.21-27  (7 rows, 3 verified)
--   MISSING: the reading passage on vegetarian diets
--   veri  Q21   dcdc4a16-21c3-4d49-a088-92378686f825  'Which of the following is not a benefit of adopting a vege'
--   veri  Q22   7eabd9c3-f15e-4950-84e7-44ecee473a60  'Which of the following qualifies as a difference between a'
--   veri  Q23   3446de24-1e14-47eb-852f-b83170f6e897  'How is proper planning important for a vegetarian li festy'
--   need  Q24   4c028d7f-9b33-4086-9d43-8d2b5958f84d  'Which of the following ways can help in making vegetarian '
--   need  Q25   4a897f7b-647b-4708-b709-ff7943bb62e7  'Which of the following words can most appropriately be sub'
--   need  Q26   b89cbee0-e42a-4a66-9ac5-eaac6d4fefde  'Which of the following words is the most similar in its de'
--   need  Q27   bd2f12fb-9d9d-4946-ae38-8b2eba66a396  'Choose the word from the following options which most aptl'
--
-- RBI 2022 Quantitative Aptitude Q.105-107  (3 rows, 3 verified)
--   MISSING: the definitions of equation I, equation II, p and q
--   veri  Q105  81da5343-1342-42b1-a837-0a61072d7e5f  'Find the ratio of smallest root of equation I to the small'
--   veri  Q106  114145a9-20b4-47ab-9dba-0d5996458b97  'Find the value of (p + q).'
--   veri  Q107  3e0ea7d9-2960-421b-a530-d917f5e1e89a  'Find the both roots of equation (p+q)2a2 + (3pq +1) a −6=0'
--
-- RBI 2022 Quantitative Aptitude Q.109 (single)  (1 rows, 0 verified)
--   MISSING: the other series of the pair
--   need  Q109  afdbacce-c588-48f8-af3d-1e991d407e80  'Series (A): 1332, 612, 492, Y, 462, 460 If Y−18 5 is a fou'
--
-- RBI 2022 Quantitative Aptitude Q.115-116  (2 rows, 2 verified)
--   MISSING: the car-preference set/Venn data
--   veri  Q115  257b64c1-8b8f-45d3-ae06-aae308be4295  'Find the ratio of people who like only car C to people who'
--   veri  Q116  77751b6a-81ac-4de8-8eee-6c35b9e3969d  'People like only car A&C together is what percentage peopl'
--
-- RBI 2022 Reasoning Q.31-41  (11 rows, 11 verified)
--   MISSING: the class-scheduling puzzle setup (Q.31-35) and the machine
--   input-output input line and steps (Q.36-40)
--   veri  Q31   9b27fd99-4311-42aa-a347-9e9f5bd3044d  'Which of the following time for Chemistry class is schedul'
--   veri  Q32   1118459d-a10b-4e04-b24e-7274fdb65766  'Which of the following subject is scheduled at last?'
--   veri  Q33   e91fd683-367a-4eef-be0f-113ca19135b6  'How many classes scheduled between Chemistry and Maths?'
--   veri  Q34   a7f11e47-0c7a-428b-8762-34b6f61c6a00  '____ class is scheduled 150 minutes after Maths clas s?'
--   veri  Q35   9f5e7f68-7f12-4b78-8917-1f38f8ed8ff9  'The number of classes scheduled between Physics and Chemis'
--   veri  Q36   bd2ec363-02ba-4d19-b1a5-23ed5ff724b1  'Which among the following word is third from the right end'
--   veri  Q37   28000881-0b35-44be-9d28-486f0137e417  'How many letters are there between third letter of the sec'
--   veri  Q38   fcb6316e-4b7f-48cd-ac43-40f6cb97bc9f  'What is the sum of the even numbers appeared in step IV?'
--   veri  Q39   a100c4ea-6496-4532-a977-21775de40e48  'What is the difference between the numbers which are secon'
--   veri  Q40   db6b34e4-2de1-44c4-a7d1-02ea70d4d773  'Which among the following word is second to the left of th'
--   veri  Q41   5a5fb576-c115-485b-87ac-7474820b7a0f  'What could be the fallout of the new excise policy approve'
--
-- RBI 2022 Reasoning Q.42 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q42   968c25b2-48d1-4bf7-901c-3c25b66ee02b  'Which of the following can be postulated from the above st'
--
-- RBI 2022 Reasoning Q.45-51  (7 rows, 7 verified)
--   MISSING: the floor-and-flat puzzle setup, the blood-relation
--   description and the age data
--   veri  Q45   96a1ecb9-6049-4f9d-a048-203f7566ff19  'Which among the following statement(s) is/are not true?'
--   veri  Q46   84c15ec6-0735-48a9-a993-16c0638ba83d  'In which among the following floor and flat does G live?'
--   veri  Q47   a27e98ac-8a2d-4f74-8148-ea86944c341c  'Which a mong the following pair of persons live to the sou'
--   veri  Q48   72689e64-4cf2-4018-a7d7-b24399d16027  'How X is related to W?'
--   veri  Q49   de4707c8-6deb-4b4f-8909-71cb7ab75688  'What is the sum of the ages of X mother’s and K?'
--   veri  Q50   9f53ba44-75bf-4b06-8d6d-31704a74b8b8  'Who among the following is the child of T?'
--   veri  Q51   ba379d86-f144-4f63-8d83-91ba55e1f6fe  'What is the ratio of the ages of P’s uncle and S’s daughte'
--
-- RBI 2022 Reasoning Q.63-64  (2 rows, 2 verified)
--   MISSING: the comparison/ordering setup
--   veri  Q63   204bc12b-6f9f-4786-8c25-02cb317724f8  'Who among the following is the youngest person?'
--   veri  Q64   61555adb-23c8-4bdb-9dc9-1e324d9d5732  'Which among the following statement(s) is/are true?'
--
-- RBI 2022 Reasoning Q.66-71  (6 rows, 6 verified)
--   MISSING: the coded-language sample sentences (Q.66-68) and the
--   direction-and-distance / seating setup (Q.69-71)
--   veri  Q66   d4f02165-e9e3-495e-ae45-b253ea65e79b  'What is the code for “Public Health” in the given code lan'
--   veri  Q67   1dcf7b49-d44c-473f-88d4-2b50e939334f  'The code “9RR 28VI” is coded for which of the following wo'
--   veri  Q68   f54d5545-3b91-4480-a7af-c71a5282ec84  'What is the code for “German language” in the given code l'
--   veri  Q69   55db1819-1aba-4cd7-b3f5-80e6de631ad6  'Find the sum of the distance walk by W and F?'
--   veri  Q70   aec19373-d886-4a49-a548-de39a939ca2a  'In which direction is point C with respect to point Q?'
--   veri  Q71   5fc97189-e9a9-45f6-9b13-41ec20ebb0b8  'What is the total distance between S and the one who sits '
--
-- RBI 2022 Reasoning Q.77 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q77   0dc8f7f3-eb01-4163-a56e-d171d886aa50  'Study the following digit -letter -symbol sequence careful'
--
-- RBI 2022 Reasoning Q.78-80  (3 rows, 2 verified)
--   MISSING: the circular seating setup
--   veri  Q78   c90b371c-7326-4e74-b939-16a6203df5d7  'Who among the following sits 8th to the right of T?'
--   veri  Q79   73d7b2e7-b70b-4b1d-92fd-469b9bdb14cb  '___ faces to the one who likes ____ colour?'
--   need  Q80   bd057ce1-3655-49e3-adb0-bd67a87ded45  'How many persons sit around the table?'
--
-- RBI 2022 Reasoning Q.86-90  (5 rows, 5 verified)
--   MISSING: the box-and-shelf puzzle setup
--   veri  Q86   76ca1621-f5a0-4484-a457-d2ac85385c2e  'Which among the following combination is correct?'
--   veri  Q87   14424d63-fb6b-44e7-a752-46cd178d3f17  'How many boxes are kept between box S and the box which co'
--   veri  Q88   0dc05cfa-a1a9-4d82-991d-1221b354acde  'Which among the following box contains marker?'
--   veri  Q89   75b80d7a-d622-4d6f-ab3c-883f57c814cb  'If all the boxes are arranged from top to bottom in an alp'
--   veri  Q90   8ad554e3-a31b-497c-825d-d07e6e65acd2  'In which of the following shelf does the box contain pen i'
--
-- RBI 2023 English Language Q.103 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q103  0a6d3b53-6b00-47fe-b43a-13b11939310e  'Four statements have been mentioned below. One or more sta'
--
-- RBI 2023 English Language Q.105 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q105  94f4d0c9-6c1d-4fea-8761-2ccf950b36ae  'Which of the following sentences from the options given be'
--
-- RBI 2023 English Language Q.106 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q106  5122b512-4b68-4add-9d15-fb5775115791  'Which of the following sentences from the options given be'
--
-- RBI 2023 Quantitative Aptitude Q.118 (single)  (1 rows, 1 verified)
--   MISSING: the equations referred to
--   veri  Q118  df539926-f76c-4c08-8ed0-22f49d805132  'Read the given information and answer the below questions.'
--
-- RBI 2023 Quantitative Aptitude Q.119 (single)  (1 rows, 1 verified)
--   MISSING: the equations referred to
--   veri  Q119  b8f86f97-9131-4c8b-b334-7f220baaa706  'Read the given information and answer the below questions.'
--
-- RBI 2023 Reasoning Q.142 (single)  (1 rows, 1 verified)
--   MISSING: the passage carrying the numbered blanks
--   veri  Q142  358e221c-e8b9-43e9-8b2f-80f8a1750fe0  'Consider the following words which have one blank each. Yo'
--
-- RBI 2023 Reasoning Q.148 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q148  234dbd84-5690-4873-9ac0-92874577d847  'Read the given information and answer the below questions.'
--
-- RBI 2023 Reasoning Q.149 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q149  348de0ca-be8d-4580-beb7-30ba88ce609c  'Read the given information and answer the below questions.'
--
-- RBI 2023 Reasoning Q.150 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q150  62d64907-3c6a-4f28-b4d5-03956073b837  'Read the given information and answer the below questions.'
--
-- RBI 2023 Reasoning Q.151 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q151  3f7eaa2b-ee6a-43ab-accc-e9730ebed8c6  'Read the given information and answer the below questions.'
--
-- RBI 2023 Reasoning Q.152 (single)  (1 rows, 1 verified)
--   MISSING: the passage carrying the numbered blanks
--   veri  Q152  d78ba3ec-9208-4d76-849c-d69ba1fee4c5  'Which of the following symbols should be placed in the bla'
--
-- RBI 2024 English Language Q.98 (single)  (1 rows, 1 verified)
--   MISSING: the passage carrying the numbered blanks
--   veri  Q98   df732dd2-9004-4cf5-9564-56ef550a32e8  'In the following question, two sentences are given with on'
--
-- RBI 2024 English Language Q.99 (single)  (1 rows, 1 verified)
--   MISSING: the passage carrying the numbered blanks
--   veri  Q99   bbdf93eb-5496-4f5e-bf3e-1edd996041d9  'In the following question, two sentences are given with on'
--
-- RBI 2024 English Language Q.100 (single)  (1 rows, 1 verified)
--   MISSING: the passage carrying the numbered blanks
--   veri  Q100  611b5a1c-39bd-4acc-9e12-b17b06cb9c53  'In the following question, two sentences are given with on'
--
-- RBI 2024 English Language Q.101 (single)  (1 rows, 1 verified)
--   MISSING: the passage carrying the numbered blanks
--   veri  Q101  1ddec204-5695-48db-ad75-f7bcec84e13f  'In the following question, two sentences are given with on'
--
-- RBI 2024 Quantitative Aptitude Q.114 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q114  136a515e-a171-4d1d-807c-45b6ca4cdc71  'Consider the below statement and the two quantities given '
--
-- RBI 2025 English Language Q.103 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q103  9fafc648-0993-4b27-8e59-9a27f5692f29  '(A) She drafted a list of interview questions to keep the '
--
-- RBI 2025 Reasoning Q.182 (single)  (1 rows, 1 verified)
--   MISSING: the reading passage
--   veri  Q182  3693ea82-21f2-457b-9269-3f103d8e1397  'A young entrepreneur started a small online bookstore that'
--
-- RBI 2025 Reasoning Q.183 (single)  (1 rows, 1 verified)
--   MISSING: the reading passage
--   veri  Q183  72955a07-053e-4eff-ad60-208a536b5e46  'A village once known for its beautiful lake saw a gradual '
--
-- RBI 2026 Reasoning Q.191 (single)  (1 rows, 1 verified)
--   MISSING: the data block referred to
--   veri  Q191  67849f20-0f5f-492e-a04d-b3cd13ee4194  'numbered I and II given below it. You have to decide wheth'
--
-- Guarded: statement 1 writes the note to all 85 but only moves a row that
-- is not already flagged; statements 2 and 3 only touch rows still carrying
-- the old status. Re-running changes nothing.

BEGIN;

-- 1. Record why each row is being pulled. Additive; reviewed_by/reviewed_at untouched.
UPDATE public.pyq_questions q
SET metadata = q.metadata || jsonb_build_object(
      'orphaned_context', jsonb_build_object(
        'set',        v.set_label,
        'missing',    v.missing,
        'flagged_by', 'migration 281',
        'flagged_at', now()::text))
FROM (VALUES
  ('7ab77868-58c2-48cd-ab52-a365a4e0beec'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('ef384cab-d616-4299-8b68-78568d1dca8c'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('352bd671-f233-4053-8a94-f5cce5050c70'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('b6c1b177-a3d2-4ed8-8ae3-245e80d9fe1f'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('b3de135a-e124-4dec-a1aa-90585abbdb45'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('75123782-9979-4c2d-8a7d-73120c797eef'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('df63317c-bdab-4271-9c5a-1b2c2982830c'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('c6e7a666-52f0-4cd0-b42c-4d3c78066736'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('25a6d571-f42d-4421-af84-c420f787c889'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('a59096b1-7614-42ee-a16c-069d2091d0a7'::uuid,
   'RBI 2022 English Language Q.1-10',
   'the reading passage(s) for Q.1-8 and the sentence list for the Q.9-10 rearrangement'),
  ('25c14b8a-2690-493f-b413-f37607227515'::uuid,
   'RBI 2022 English Language Q.14-19',
   'the sentence-completion context printed above the set'),
  ('e68143e6-4333-414e-bf1c-493ff2df62f7'::uuid,
   'RBI 2022 English Language Q.14-19',
   'the sentence-completion context printed above the set'),
  ('8bf962d0-59b7-4432-9b0b-ed8cc1c4d8fd'::uuid,
   'RBI 2022 English Language Q.14-19',
   'the sentence-completion context printed above the set'),
  ('5d56b020-e123-4f86-9b50-0838afcb3334'::uuid,
   'RBI 2022 English Language Q.14-19',
   'the sentence-completion context printed above the set'),
  ('82f16a8f-5894-446b-b16c-b2a82a0f8697'::uuid,
   'RBI 2022 English Language Q.14-19',
   'the sentence-completion context printed above the set'),
  ('4ff3c2c3-6c64-4d6c-bf0f-447aa3183c49'::uuid,
   'RBI 2022 English Language Q.14-19',
   'the sentence-completion context printed above the set'),
  ('dcdc4a16-21c3-4d49-a088-92378686f825'::uuid,
   'RBI 2022 English Language Q.21-27',
   'the reading passage on vegetarian diets'),
  ('7eabd9c3-f15e-4950-84e7-44ecee473a60'::uuid,
   'RBI 2022 English Language Q.21-27',
   'the reading passage on vegetarian diets'),
  ('3446de24-1e14-47eb-852f-b83170f6e897'::uuid,
   'RBI 2022 English Language Q.21-27',
   'the reading passage on vegetarian diets'),
  ('4c028d7f-9b33-4086-9d43-8d2b5958f84d'::uuid,
   'RBI 2022 English Language Q.21-27',
   'the reading passage on vegetarian diets'),
  ('4a897f7b-647b-4708-b709-ff7943bb62e7'::uuid,
   'RBI 2022 English Language Q.21-27',
   'the reading passage on vegetarian diets'),
  ('b89cbee0-e42a-4a66-9ac5-eaac6d4fefde'::uuid,
   'RBI 2022 English Language Q.21-27',
   'the reading passage on vegetarian diets'),
  ('bd2f12fb-9d9d-4946-ae38-8b2eba66a396'::uuid,
   'RBI 2022 English Language Q.21-27',
   'the reading passage on vegetarian diets'),
  ('81da5343-1342-42b1-a837-0a61072d7e5f'::uuid,
   'RBI 2022 Quantitative Aptitude Q.105-107',
   'the definitions of equation I, equation II, p and q'),
  ('114145a9-20b4-47ab-9dba-0d5996458b97'::uuid,
   'RBI 2022 Quantitative Aptitude Q.105-107',
   'the definitions of equation I, equation II, p and q'),
  ('3e0ea7d9-2960-421b-a530-d917f5e1e89a'::uuid,
   'RBI 2022 Quantitative Aptitude Q.105-107',
   'the definitions of equation I, equation II, p and q'),
  ('afdbacce-c588-48f8-af3d-1e991d407e80'::uuid,
   'RBI 2022 Quantitative Aptitude Q.109 (single)',
   'the other series of the pair'),
  ('257b64c1-8b8f-45d3-ae06-aae308be4295'::uuid,
   'RBI 2022 Quantitative Aptitude Q.115-116',
   'the car-preference set/Venn data'),
  ('77751b6a-81ac-4de8-8eee-6c35b9e3969d'::uuid,
   'RBI 2022 Quantitative Aptitude Q.115-116',
   'the car-preference set/Venn data'),
  ('9b27fd99-4311-42aa-a347-9e9f5bd3044d'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('1118459d-a10b-4e04-b24e-7274fdb65766'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('e91fd683-367a-4eef-be0f-113ca19135b6'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('a7f11e47-0c7a-428b-8762-34b6f61c6a00'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('9f5e7f68-7f12-4b78-8917-1f38f8ed8ff9'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('bd2ec363-02ba-4d19-b1a5-23ed5ff724b1'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('28000881-0b35-44be-9d28-486f0137e417'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('fcb6316e-4b7f-48cd-ac43-40f6cb97bc9f'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('a100c4ea-6496-4532-a977-21775de40e48'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('db6b34e4-2de1-44c4-a7d1-02ea70d4d773'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('5a5fb576-c115-485b-87ac-7474820b7a0f'::uuid,
   'RBI 2022 Reasoning Q.31-41',
   'the class-scheduling puzzle setup (Q.31-35) and the machine input-output input line and steps (Q.36-40)'),
  ('968c25b2-48d1-4bf7-901c-3c25b66ee02b'::uuid,
   'RBI 2022 Reasoning Q.42 (single)',
   'the data block referred to'),
  ('96a1ecb9-6049-4f9d-a048-203f7566ff19'::uuid,
   'RBI 2022 Reasoning Q.45-51',
   'the floor-and-flat puzzle setup, the blood-relation description and the age data'),
  ('84c15ec6-0735-48a9-a993-16c0638ba83d'::uuid,
   'RBI 2022 Reasoning Q.45-51',
   'the floor-and-flat puzzle setup, the blood-relation description and the age data'),
  ('a27e98ac-8a2d-4f74-8148-ea86944c341c'::uuid,
   'RBI 2022 Reasoning Q.45-51',
   'the floor-and-flat puzzle setup, the blood-relation description and the age data'),
  ('72689e64-4cf2-4018-a7d7-b24399d16027'::uuid,
   'RBI 2022 Reasoning Q.45-51',
   'the floor-and-flat puzzle setup, the blood-relation description and the age data'),
  ('de4707c8-6deb-4b4f-8909-71cb7ab75688'::uuid,
   'RBI 2022 Reasoning Q.45-51',
   'the floor-and-flat puzzle setup, the blood-relation description and the age data'),
  ('9f53ba44-75bf-4b06-8d6d-31704a74b8b8'::uuid,
   'RBI 2022 Reasoning Q.45-51',
   'the floor-and-flat puzzle setup, the blood-relation description and the age data'),
  ('ba379d86-f144-4f63-8d83-91ba55e1f6fe'::uuid,
   'RBI 2022 Reasoning Q.45-51',
   'the floor-and-flat puzzle setup, the blood-relation description and the age data'),
  ('204bc12b-6f9f-4786-8c25-02cb317724f8'::uuid,
   'RBI 2022 Reasoning Q.63-64',
   'the comparison/ordering setup'),
  ('61555adb-23c8-4bdb-9dc9-1e324d9d5732'::uuid,
   'RBI 2022 Reasoning Q.63-64',
   'the comparison/ordering setup'),
  ('d4f02165-e9e3-495e-ae45-b253ea65e79b'::uuid,
   'RBI 2022 Reasoning Q.66-71',
   'the coded-language sample sentences (Q.66-68) and the direction-and-distance / seating setup (Q.69-71)'),
  ('1dcf7b49-d44c-473f-88d4-2b50e939334f'::uuid,
   'RBI 2022 Reasoning Q.66-71',
   'the coded-language sample sentences (Q.66-68) and the direction-and-distance / seating setup (Q.69-71)'),
  ('f54d5545-3b91-4480-a7af-c71a5282ec84'::uuid,
   'RBI 2022 Reasoning Q.66-71',
   'the coded-language sample sentences (Q.66-68) and the direction-and-distance / seating setup (Q.69-71)'),
  ('55db1819-1aba-4cd7-b3f5-80e6de631ad6'::uuid,
   'RBI 2022 Reasoning Q.66-71',
   'the coded-language sample sentences (Q.66-68) and the direction-and-distance / seating setup (Q.69-71)'),
  ('aec19373-d886-4a49-a548-de39a939ca2a'::uuid,
   'RBI 2022 Reasoning Q.66-71',
   'the coded-language sample sentences (Q.66-68) and the direction-and-distance / seating setup (Q.69-71)'),
  ('5fc97189-e9a9-45f6-9b13-41ec20ebb0b8'::uuid,
   'RBI 2022 Reasoning Q.66-71',
   'the coded-language sample sentences (Q.66-68) and the direction-and-distance / seating setup (Q.69-71)'),
  ('0dc8f7f3-eb01-4163-a56e-d171d886aa50'::uuid,
   'RBI 2022 Reasoning Q.77 (single)',
   'the data block referred to'),
  ('c90b371c-7326-4e74-b939-16a6203df5d7'::uuid,
   'RBI 2022 Reasoning Q.78-80',
   'the circular seating setup'),
  ('73d7b2e7-b70b-4b1d-92fd-469b9bdb14cb'::uuid,
   'RBI 2022 Reasoning Q.78-80',
   'the circular seating setup'),
  ('bd057ce1-3655-49e3-adb0-bd67a87ded45'::uuid,
   'RBI 2022 Reasoning Q.78-80',
   'the circular seating setup'),
  ('76ca1621-f5a0-4484-a457-d2ac85385c2e'::uuid,
   'RBI 2022 Reasoning Q.86-90',
   'the box-and-shelf puzzle setup'),
  ('14424d63-fb6b-44e7-a752-46cd178d3f17'::uuid,
   'RBI 2022 Reasoning Q.86-90',
   'the box-and-shelf puzzle setup'),
  ('0dc05cfa-a1a9-4d82-991d-1221b354acde'::uuid,
   'RBI 2022 Reasoning Q.86-90',
   'the box-and-shelf puzzle setup'),
  ('75b80d7a-d622-4d6f-ab3c-883f57c814cb'::uuid,
   'RBI 2022 Reasoning Q.86-90',
   'the box-and-shelf puzzle setup'),
  ('8ad554e3-a31b-497c-825d-d07e6e65acd2'::uuid,
   'RBI 2022 Reasoning Q.86-90',
   'the box-and-shelf puzzle setup'),
  ('0a6d3b53-6b00-47fe-b43a-13b11939310e'::uuid,
   'RBI 2023 English Language Q.103 (single)',
   'the data block referred to'),
  ('94f4d0c9-6c1d-4fea-8761-2ccf950b36ae'::uuid,
   'RBI 2023 English Language Q.105 (single)',
   'the data block referred to'),
  ('5122b512-4b68-4add-9d15-fb5775115791'::uuid,
   'RBI 2023 English Language Q.106 (single)',
   'the data block referred to'),
  ('df539926-f76c-4c08-8ed0-22f49d805132'::uuid,
   'RBI 2023 Quantitative Aptitude Q.118 (single)',
   'the equations referred to'),
  ('b8f86f97-9131-4c8b-b334-7f220baaa706'::uuid,
   'RBI 2023 Quantitative Aptitude Q.119 (single)',
   'the equations referred to'),
  ('358e221c-e8b9-43e9-8b2f-80f8a1750fe0'::uuid,
   'RBI 2023 Reasoning Q.142 (single)',
   'the passage carrying the numbered blanks'),
  ('234dbd84-5690-4873-9ac0-92874577d847'::uuid,
   'RBI 2023 Reasoning Q.148 (single)',
   'the data block referred to'),
  ('348de0ca-be8d-4580-beb7-30ba88ce609c'::uuid,
   'RBI 2023 Reasoning Q.149 (single)',
   'the data block referred to'),
  ('62d64907-3c6a-4f28-b4d5-03956073b837'::uuid,
   'RBI 2023 Reasoning Q.150 (single)',
   'the data block referred to'),
  ('3f7eaa2b-ee6a-43ab-accc-e9730ebed8c6'::uuid,
   'RBI 2023 Reasoning Q.151 (single)',
   'the data block referred to'),
  ('d78ba3ec-9208-4d76-849c-d69ba1fee4c5'::uuid,
   'RBI 2023 Reasoning Q.152 (single)',
   'the passage carrying the numbered blanks'),
  ('df732dd2-9004-4cf5-9564-56ef550a32e8'::uuid,
   'RBI 2024 English Language Q.98 (single)',
   'the passage carrying the numbered blanks'),
  ('bbdf93eb-5496-4f5e-bf3e-1edd996041d9'::uuid,
   'RBI 2024 English Language Q.99 (single)',
   'the passage carrying the numbered blanks'),
  ('611b5a1c-39bd-4acc-9e12-b17b06cb9c53'::uuid,
   'RBI 2024 English Language Q.100 (single)',
   'the passage carrying the numbered blanks'),
  ('1ddec204-5695-48db-ad75-f7bcec84e13f'::uuid,
   'RBI 2024 English Language Q.101 (single)',
   'the passage carrying the numbered blanks'),
  ('136a515e-a171-4d1d-807c-45b6ca4cdc71'::uuid,
   'RBI 2024 Quantitative Aptitude Q.114 (single)',
   'the data block referred to'),
  ('9fafc648-0993-4b27-8e59-9a27f5692f29'::uuid,
   'RBI 2025 English Language Q.103 (single)',
   'the data block referred to'),
  ('3693ea82-21f2-457b-9269-3f103d8e1397'::uuid,
   'RBI 2025 Reasoning Q.182 (single)',
   'the reading passage'),
  ('72955a07-053e-4eff-ad60-208a536b5e46'::uuid,
   'RBI 2025 Reasoning Q.183 (single)',
   'the reading passage'),
  ('67849f20-0f5f-492e-a04d-b3cd13ee4194'::uuid,
   'RBI 2026 Reasoning Q.191 (single)',
   'the data block referred to')
) AS v(question_id, set_label, missing)
WHERE q.id = v.question_id;

-- 2. Pull the questions. This fires trg_invalidate_pyq_projection_q, which demotes
--    mock_question_bank to 'draft' and marks the projection stale.
UPDATE public.pyq_questions
SET reviewer_status = 'needs_correction'
WHERE id IN (
  '0a6d3b53-6b00-47fe-b43a-13b11939310e'::uuid,
  '0dc05cfa-a1a9-4d82-991d-1221b354acde'::uuid,
  '0dc8f7f3-eb01-4163-a56e-d171d886aa50'::uuid,
  '1118459d-a10b-4e04-b24e-7274fdb65766'::uuid,
  '114145a9-20b4-47ab-9dba-0d5996458b97'::uuid,
  '136a515e-a171-4d1d-807c-45b6ca4cdc71'::uuid,
  '14424d63-fb6b-44e7-a752-46cd178d3f17'::uuid,
  '1dcf7b49-d44c-473f-88d4-2b50e939334f'::uuid,
  '1ddec204-5695-48db-ad75-f7bcec84e13f'::uuid,
  '204bc12b-6f9f-4786-8c25-02cb317724f8'::uuid,
  '234dbd84-5690-4873-9ac0-92874577d847'::uuid,
  '257b64c1-8b8f-45d3-ae06-aae308be4295'::uuid,
  '25a6d571-f42d-4421-af84-c420f787c889'::uuid,
  '25c14b8a-2690-493f-b413-f37607227515'::uuid,
  '28000881-0b35-44be-9d28-486f0137e417'::uuid,
  '3446de24-1e14-47eb-852f-b83170f6e897'::uuid,
  '348de0ca-be8d-4580-beb7-30ba88ce609c'::uuid,
  '352bd671-f233-4053-8a94-f5cce5050c70'::uuid,
  '358e221c-e8b9-43e9-8b2f-80f8a1750fe0'::uuid,
  '3693ea82-21f2-457b-9269-3f103d8e1397'::uuid,
  '3e0ea7d9-2960-421b-a530-d917f5e1e89a'::uuid,
  '3f7eaa2b-ee6a-43ab-accc-e9730ebed8c6'::uuid,
  '4a897f7b-647b-4708-b709-ff7943bb62e7'::uuid,
  '4c028d7f-9b33-4086-9d43-8d2b5958f84d'::uuid,
  '4ff3c2c3-6c64-4d6c-bf0f-447aa3183c49'::uuid,
  '5122b512-4b68-4add-9d15-fb5775115791'::uuid,
  '55db1819-1aba-4cd7-b3f5-80e6de631ad6'::uuid,
  '5a5fb576-c115-485b-87ac-7474820b7a0f'::uuid,
  '5d56b020-e123-4f86-9b50-0838afcb3334'::uuid,
  '5fc97189-e9a9-45f6-9b13-41ec20ebb0b8'::uuid,
  '611b5a1c-39bd-4acc-9e12-b17b06cb9c53'::uuid,
  '61555adb-23c8-4bdb-9dc9-1e324d9d5732'::uuid,
  '62d64907-3c6a-4f28-b4d5-03956073b837'::uuid,
  '67849f20-0f5f-492e-a04d-b3cd13ee4194'::uuid,
  '72689e64-4cf2-4018-a7d7-b24399d16027'::uuid,
  '72955a07-053e-4eff-ad60-208a536b5e46'::uuid,
  '73d7b2e7-b70b-4b1d-92fd-469b9bdb14cb'::uuid,
  '75123782-9979-4c2d-8a7d-73120c797eef'::uuid,
  '75b80d7a-d622-4d6f-ab3c-883f57c814cb'::uuid,
  '76ca1621-f5a0-4484-a457-d2ac85385c2e'::uuid,
  '77751b6a-81ac-4de8-8eee-6c35b9e3969d'::uuid,
  '7ab77868-58c2-48cd-ab52-a365a4e0beec'::uuid,
  '7eabd9c3-f15e-4950-84e7-44ecee473a60'::uuid,
  '81da5343-1342-42b1-a837-0a61072d7e5f'::uuid,
  '82f16a8f-5894-446b-b16c-b2a82a0f8697'::uuid,
  '84c15ec6-0735-48a9-a993-16c0638ba83d'::uuid,
  '8ad554e3-a31b-497c-825d-d07e6e65acd2'::uuid,
  '8bf962d0-59b7-4432-9b0b-ed8cc1c4d8fd'::uuid,
  '94f4d0c9-6c1d-4fea-8761-2ccf950b36ae'::uuid,
  '968c25b2-48d1-4bf7-901c-3c25b66ee02b'::uuid,
  '96a1ecb9-6049-4f9d-a048-203f7566ff19'::uuid,
  '9b27fd99-4311-42aa-a347-9e9f5bd3044d'::uuid,
  '9f53ba44-75bf-4b06-8d6d-31704a74b8b8'::uuid,
  '9f5e7f68-7f12-4b78-8917-1f38f8ed8ff9'::uuid,
  '9fafc648-0993-4b27-8e59-9a27f5692f29'::uuid,
  'a100c4ea-6496-4532-a977-21775de40e48'::uuid,
  'a27e98ac-8a2d-4f74-8148-ea86944c341c'::uuid,
  'a59096b1-7614-42ee-a16c-069d2091d0a7'::uuid,
  'a7f11e47-0c7a-428b-8762-34b6f61c6a00'::uuid,
  'aec19373-d886-4a49-a548-de39a939ca2a'::uuid,
  'afdbacce-c588-48f8-af3d-1e991d407e80'::uuid,
  'b3de135a-e124-4dec-a1aa-90585abbdb45'::uuid,
  'b6c1b177-a3d2-4ed8-8ae3-245e80d9fe1f'::uuid,
  'b89cbee0-e42a-4a66-9ac5-eaac6d4fefde'::uuid,
  'b8f86f97-9131-4c8b-b334-7f220baaa706'::uuid,
  'ba379d86-f144-4f63-8d83-91ba55e1f6fe'::uuid,
  'bbdf93eb-5496-4f5e-bf3e-1edd996041d9'::uuid,
  'bd057ce1-3655-49e3-adb0-bd67a87ded45'::uuid,
  'bd2ec363-02ba-4d19-b1a5-23ed5ff724b1'::uuid,
  'bd2f12fb-9d9d-4946-ae38-8b2eba66a396'::uuid,
  'c6e7a666-52f0-4cd0-b42c-4d3c78066736'::uuid,
  'c90b371c-7326-4e74-b939-16a6203df5d7'::uuid,
  'd4f02165-e9e3-495e-ae45-b253ea65e79b'::uuid,
  'd78ba3ec-9208-4d76-849c-d69ba1fee4c5'::uuid,
  'db6b34e4-2de1-44c4-a7d1-02ea70d4d773'::uuid,
  'dcdc4a16-21c3-4d49-a088-92378686f825'::uuid,
  'de4707c8-6deb-4b4f-8909-71cb7ab75688'::uuid,
  'df539926-f76c-4c08-8ed0-22f49d805132'::uuid,
  'df63317c-bdab-4271-9c5a-1b2c2982830c'::uuid,
  'df732dd2-9004-4cf5-9564-56ef550a32e8'::uuid,
  'e68143e6-4333-414e-bf1c-493ff2df62f7'::uuid,
  'e91fd683-367a-4eef-be0f-113ca19135b6'::uuid,
  'ef384cab-d616-4299-8b68-78568d1dca8c'::uuid,
  'f54d5545-3b91-4480-a7af-c71a5282ec84'::uuid,
  'fcb6316e-4b7f-48cd-ac43-40f6cb97bc9f'::uuid
)
  AND reviewer_status <> 'needs_correction';

-- 3. Cascade to the option rows, the way update_pyq_question_review_atomic would.
UPDATE public.pyq_options
SET reviewer_status = 'needs_correction'
WHERE question_id IN (
  '0a6d3b53-6b00-47fe-b43a-13b11939310e'::uuid,
  '0dc05cfa-a1a9-4d82-991d-1221b354acde'::uuid,
  '0dc8f7f3-eb01-4163-a56e-d171d886aa50'::uuid,
  '1118459d-a10b-4e04-b24e-7274fdb65766'::uuid,
  '114145a9-20b4-47ab-9dba-0d5996458b97'::uuid,
  '136a515e-a171-4d1d-807c-45b6ca4cdc71'::uuid,
  '14424d63-fb6b-44e7-a752-46cd178d3f17'::uuid,
  '1dcf7b49-d44c-473f-88d4-2b50e939334f'::uuid,
  '1ddec204-5695-48db-ad75-f7bcec84e13f'::uuid,
  '204bc12b-6f9f-4786-8c25-02cb317724f8'::uuid,
  '234dbd84-5690-4873-9ac0-92874577d847'::uuid,
  '257b64c1-8b8f-45d3-ae06-aae308be4295'::uuid,
  '25a6d571-f42d-4421-af84-c420f787c889'::uuid,
  '25c14b8a-2690-493f-b413-f37607227515'::uuid,
  '28000881-0b35-44be-9d28-486f0137e417'::uuid,
  '3446de24-1e14-47eb-852f-b83170f6e897'::uuid,
  '348de0ca-be8d-4580-beb7-30ba88ce609c'::uuid,
  '352bd671-f233-4053-8a94-f5cce5050c70'::uuid,
  '358e221c-e8b9-43e9-8b2f-80f8a1750fe0'::uuid,
  '3693ea82-21f2-457b-9269-3f103d8e1397'::uuid,
  '3e0ea7d9-2960-421b-a530-d917f5e1e89a'::uuid,
  '3f7eaa2b-ee6a-43ab-accc-e9730ebed8c6'::uuid,
  '4a897f7b-647b-4708-b709-ff7943bb62e7'::uuid,
  '4c028d7f-9b33-4086-9d43-8d2b5958f84d'::uuid,
  '4ff3c2c3-6c64-4d6c-bf0f-447aa3183c49'::uuid,
  '5122b512-4b68-4add-9d15-fb5775115791'::uuid,
  '55db1819-1aba-4cd7-b3f5-80e6de631ad6'::uuid,
  '5a5fb576-c115-485b-87ac-7474820b7a0f'::uuid,
  '5d56b020-e123-4f86-9b50-0838afcb3334'::uuid,
  '5fc97189-e9a9-45f6-9b13-41ec20ebb0b8'::uuid,
  '611b5a1c-39bd-4acc-9e12-b17b06cb9c53'::uuid,
  '61555adb-23c8-4bdb-9dc9-1e324d9d5732'::uuid,
  '62d64907-3c6a-4f28-b4d5-03956073b837'::uuid,
  '67849f20-0f5f-492e-a04d-b3cd13ee4194'::uuid,
  '72689e64-4cf2-4018-a7d7-b24399d16027'::uuid,
  '72955a07-053e-4eff-ad60-208a536b5e46'::uuid,
  '73d7b2e7-b70b-4b1d-92fd-469b9bdb14cb'::uuid,
  '75123782-9979-4c2d-8a7d-73120c797eef'::uuid,
  '75b80d7a-d622-4d6f-ab3c-883f57c814cb'::uuid,
  '76ca1621-f5a0-4484-a457-d2ac85385c2e'::uuid,
  '77751b6a-81ac-4de8-8eee-6c35b9e3969d'::uuid,
  '7ab77868-58c2-48cd-ab52-a365a4e0beec'::uuid,
  '7eabd9c3-f15e-4950-84e7-44ecee473a60'::uuid,
  '81da5343-1342-42b1-a837-0a61072d7e5f'::uuid,
  '82f16a8f-5894-446b-b16c-b2a82a0f8697'::uuid,
  '84c15ec6-0735-48a9-a993-16c0638ba83d'::uuid,
  '8ad554e3-a31b-497c-825d-d07e6e65acd2'::uuid,
  '8bf962d0-59b7-4432-9b0b-ed8cc1c4d8fd'::uuid,
  '94f4d0c9-6c1d-4fea-8761-2ccf950b36ae'::uuid,
  '968c25b2-48d1-4bf7-901c-3c25b66ee02b'::uuid,
  '96a1ecb9-6049-4f9d-a048-203f7566ff19'::uuid,
  '9b27fd99-4311-42aa-a347-9e9f5bd3044d'::uuid,
  '9f53ba44-75bf-4b06-8d6d-31704a74b8b8'::uuid,
  '9f5e7f68-7f12-4b78-8917-1f38f8ed8ff9'::uuid,
  '9fafc648-0993-4b27-8e59-9a27f5692f29'::uuid,
  'a100c4ea-6496-4532-a977-21775de40e48'::uuid,
  'a27e98ac-8a2d-4f74-8148-ea86944c341c'::uuid,
  'a59096b1-7614-42ee-a16c-069d2091d0a7'::uuid,
  'a7f11e47-0c7a-428b-8762-34b6f61c6a00'::uuid,
  'aec19373-d886-4a49-a548-de39a939ca2a'::uuid,
  'afdbacce-c588-48f8-af3d-1e991d407e80'::uuid,
  'b3de135a-e124-4dec-a1aa-90585abbdb45'::uuid,
  'b6c1b177-a3d2-4ed8-8ae3-245e80d9fe1f'::uuid,
  'b89cbee0-e42a-4a66-9ac5-eaac6d4fefde'::uuid,
  'b8f86f97-9131-4c8b-b334-7f220baaa706'::uuid,
  'ba379d86-f144-4f63-8d83-91ba55e1f6fe'::uuid,
  'bbdf93eb-5496-4f5e-bf3e-1edd996041d9'::uuid,
  'bd057ce1-3655-49e3-adb0-bd67a87ded45'::uuid,
  'bd2ec363-02ba-4d19-b1a5-23ed5ff724b1'::uuid,
  'bd2f12fb-9d9d-4946-ae38-8b2eba66a396'::uuid,
  'c6e7a666-52f0-4cd0-b42c-4d3c78066736'::uuid,
  'c90b371c-7326-4e74-b939-16a6203df5d7'::uuid,
  'd4f02165-e9e3-495e-ae45-b253ea65e79b'::uuid,
  'd78ba3ec-9208-4d76-849c-d69ba1fee4c5'::uuid,
  'db6b34e4-2de1-44c4-a7d1-02ea70d4d773'::uuid,
  'dcdc4a16-21c3-4d49-a088-92378686f825'::uuid,
  'de4707c8-6deb-4b4f-8909-71cb7ab75688'::uuid,
  'df539926-f76c-4c08-8ed0-22f49d805132'::uuid,
  'df63317c-bdab-4271-9c5a-1b2c2982830c'::uuid,
  'df732dd2-9004-4cf5-9564-56ef550a32e8'::uuid,
  'e68143e6-4333-414e-bf1c-493ff2df62f7'::uuid,
  'e91fd683-367a-4eef-be0f-113ca19135b6'::uuid,
  'ef384cab-d616-4299-8b68-78568d1dca8c'::uuid,
  'f54d5545-3b91-4480-a7af-c71a5282ec84'::uuid,
  'fcb6316e-4b7f-48cd-ac43-40f6cb97bc9f'::uuid
)
  AND reviewer_status <> 'needs_correction';

COMMIT;
