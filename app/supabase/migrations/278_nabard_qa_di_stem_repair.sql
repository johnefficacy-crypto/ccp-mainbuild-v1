-- Migration 278: restore the DI source data to 17 NABARD Quantitative Aptitude
-- question stems, and take those rows back off needs_correction.
--
-- Three DI sets in the compendium carry their data in a pie chart or line
-- graph rendered as an image. Nothing reached the import, so the stems name
-- "College E", "society D" and "apartment P" with no values anywhere --
-- unanswerable as loaded, and ungradable for difficulty. The values are
-- recoverable: the printed answer explanations restate them on the way to
-- each answer. This migration prepends the recovered data to each stem as a
-- plain labelled list.
--
-- WHERE EACH FIGURE COMES FROM, and how it was checked:
--
-- 2022 Morning Q.71-76 -- pie chart, percentage of applications per
-- college. A 25% and C 20% and E 15% are stated in Q.71's explanation ("25%
-- + 20% + 15% = 60%"); D 24% in Q.72's ("24% of 500"); B 16% in Q.74's
-- ("Percentage of applications received by college B = 16%"). Check:
-- 25+16+20+24+15 = 100. The base total of 500 is NOT added to the stem --
-- it is derived from the printed Note, which is part of the question's work
-- and is restored as written.
--
-- 2022 Evening Q.82-86 -- line graph, people in the public sector per
-- apartment. A 150, B 80, C 160, D 200, E 100, from the working table
-- repeated verbatim in the explanation to all five questions. Check: each
-- value against the public:private ratio table, which the compendium prints
-- as text -- 150 at 3:2 gives 100 private, 80 at 1:2 gives 160, 160 at 4:3
-- gives 120, 200 at 5:3 gives 120, 100 at 2:3 gives 150; every one matches
-- the private column of that same table. The ratio table is restored too:
-- it was in the instruction block, which no more reached the import than
-- the graph did.
--
-- 2023 Q.15-20 -- pie chart, percentage of population per apartment. P
-- 18.5%, Q 20.5%, R 17%, S 20%, T 24%, from the population lines repeated
-- in every explanation in the set ("Total Population of P = 18.5/100x8000 =
-- 1480"). Check: 18.5+20.5+17+20+24 = 100, and each stated product equals
-- the stated total. Total population 8000 and the male percentage table
-- were printed as text in the instruction block and are restored with the
-- chart.
--
-- NOTHING IS INVENTED. Every figure above appears verbatim in the source
-- PDF. No set was left short: all three reconstruct completely, so all 17
-- rows are repaired and none stays needs_correction.
--
-- CONTENT HASH. Changing pyq_questions.question_text changes the content
-- hash these papers would project under. None of the three papers is
-- projected to mock_question_bank yet -- every question on them is
-- reviewer_status pending, and the projection takes verified rows only --
-- so there is nothing to re-sync now. Once they are projected, a later edit
-- to question_text would need a re-sync; this one does not.
--
-- REVIEWER STATUS. The difficulty pass set these 17 to needs_correction,
-- and update_pyq_question_review_atomic (migration 162) cascaded that to
-- their 85 option rows. Statement 2 puts both back to pending. It is here
-- rather than in the worksheet because pyq_question_review.py cannot
-- express it: its DECISIONS vocabulary is {verified, rejected,
-- needs_correction} with no way to clear one. Nor would the CMS review
-- route be enough -- ReviewBody accepts 'pending', but the RPC cascades
-- only for verified/rejected/needs_correction, so setting the question to
-- pending through the API would strand all 85 options at needs_correction.
-- Guarded on the current value, so it is a no-op if the flag was never
-- applied.
--
-- BEFORE AND AFTER, every row:
--
-- QA-2022-Q071  (paper 85e16bb8-514a-4457-99b4-a1de23b91095, question 5a608a66-503b-4bb7-abe8-454d0b4d1047)
--   BEFORE:
--   Q.71) If the ratio of number of applications received by College E and
--   C together to the number of applications received by College X is
--   35:18, find the number of applications received by college X?
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.71 to Q.76): Consider the data below about the number of
--   applications received by five colleges. The pie chart shows the
--   percentage distribution of applications received.
--
--   Percentage distribution of applications received
--   College A - 25%
--   College B - 16%
--   College C - 20%
--   College D - 24%
--   College E - 15%
--
--   Note: The average of number of applications to colleges A, C and E is
--   100.
--
--
--
-- QA-2022-Q072  (paper 85e16bb8-514a-4457-99b4-a1de23b91095, question 2b8e24f8-a535-45a8-8f98-7edd081e6fe8)
--   BEFORE:
--   Q.72) If the number of boys who applied in college D was 40% less than
--   the number of girls who applied in the same college, then find out the
--   number of boys who applied in college D?
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.71 to Q.76): Consider the data below about the number of
--   applications received by five colleges. The pie chart shows the
--   percentage distribution of applications received.
--
--   Percentage distribution of applications received
--   College A - 25%
--   College B - 16%
--   College C - 20%
--   College D - 24%
--   College E - 15%
--
--   Note: The average of number of applications to colleges A, C and E is
--   100.
--
--
--
-- QA-2022-Q073  (paper 85e16bb8-514a-4457-99b4-a1de23b91095, question 47e6098e-f0a0-4a7f-bd6f-e94a4f7fa9b5)
--   BEFORE:
--   Q.73) If the number of students who applied in college C was 10 more
--   than the actual number, then the number of students who applied in
--   college C is what percent of the number of students who applied in
--   college A?
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.71 to Q.76): Consider the data below about the number of
--   applications received by five colleges. The pie chart shows the
--   percentage distribution of applications received.
--
--   Percentage distribution of applications received
--   College A - 25%
--   College B - 16%
--   College C - 20%
--   College D - 24%
--   College E - 15%
--
--   Note: The average of number of applications to colleges A, C and E is
--   100.
--
--
--
-- QA-2022-Q074  (paper 85e16bb8-514a-4457-99b4-a1de23b91095, question c29e7fe7-9dcd-4ec3-9716-90e9a3681eeb)
--   BEFORE:
--   Q.74) The central angle of College B in degrees is
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.71 to Q.76): Consider the data below about the number of
--   applications received by five colleges. The pie chart shows the
--   percentage distribution of applications received.
--
--   Percentage distribution of applications received
--   College A - 25%
--   College B - 16%
--   College C - 20%
--   College D - 24%
--   College E - 15%
--
--   Note: The average of number of applications to colleges A, C and E is
--   100.
--
--
--
-- QA-2022-Q075  (paper 85e16bb8-514a-4457-99b4-a1de23b91095, question e6443373-7ca3-4ab8-a19c-de64976a7fae)
--   BEFORE:
--   Q.75) What is the difference between the number of applications
--   received by colleges A and B together and the number of applications
--   received by college E?
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.71 to Q.76): Consider the data below about the number of
--   applications received by five colleges. The pie chart shows the
--   percentage distribution of applications received.
--
--   Percentage distribution of applications received
--   College A - 25%
--   College B - 16%
--   College C - 20%
--   College D - 24%
--   College E - 15%
--
--   Note: The average of number of applications to colleges A, C and E is
--   100.
--
--
--
-- QA-2022-Q076  (paper 85e16bb8-514a-4457-99b4-a1de23b91095, question d55d19c5-f49d-4377-adba-f5a789d41a53)
--   BEFORE:
--   Q.76) Suppose the cost of application form in college E is Rs 100 for a
--   boy and Rs 75 for a girl. Assume 40 boys applied in college E and the
--   rest were girls. What is the total application amount received by
--   college E?
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.71 to Q.76): Consider the data below about the number of
--   applications received by five colleges. The pie chart shows the
--   percentage distribution of applications received.
--
--   Percentage distribution of applications received
--   College A - 25%
--   College B - 16%
--   College C - 20%
--   College D - 24%
--   College E - 15%
--
--   Note: The average of number of applications to colleges A, C and E is
--   100.
--
--
--
-- QA-2022-Q082  (paper eb45ed17-4461-41df-85b6-aaae0d965c92, question f2bb0b09-d96d-4655-a067-3797cf785df0)
--   BEFORE:
--   Q.82)Find the difference between number of private and public people in
--   society D?
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.82 to Q.86): Answer the questions based on the
--   information given below.
--
--   Number of people working in the public sector, by apartment
--   A - 150
--   B - 80
--   C - 160
--   D - 200
--   E - 100
--
--   Ratio of people working in the public sector to people working in the
--   private sector
--   A - 3 : 2
--   B - 1 : 2
--   C - 4 : 3
--   D - 5 : 3
--   E - 2 : 3
--
--
--
-- QA-2022-Q083  (paper eb45ed17-4461-41df-85b6-aaae0d965c92, question e59e89dd-0dd0-4319-88bb-9064b4b3c365)
--   BEFORE:
--   Q.83)Find the ratio of the total number of people in society E to the
--   number of people who are in private sector from society B.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.82 to Q.86): Answer the questions based on the
--   information given below.
--
--   Number of people working in the public sector, by apartment
--   A - 150
--   B - 80
--   C - 160
--   D - 200
--   E - 100
--
--   Ratio of people working in the public sector to people working in the
--   private sector
--   A - 3 : 2
--   B - 1 : 2
--   C - 4 : 3
--   D - 5 : 3
--   E - 2 : 3
--
--
--
-- QA-2022-Q084  (paper eb45ed17-4461-41df-85b6-aaae0d965c92, question 6c3700e1-d057-4e5f-b599-f67b2cbdd334)
--   BEFORE:
--   Q.84)Find the total number of people in society A, B and D.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.82 to Q.86): Answer the questions based on the
--   information given below.
--
--   Number of people working in the public sector, by apartment
--   A - 150
--   B - 80
--   C - 160
--   D - 200
--   E - 100
--
--   Ratio of people working in the public sector to people working in the
--   private sector
--   A - 3 : 2
--   B - 1 : 2
--   C - 4 : 3
--   D - 5 : 3
--   E - 2 : 3
--
--
--
-- QA-2022-Q085  (paper eb45ed17-4461-41df-85b6-aaae0d965c92, question a82a342a-7b3e-492a-948e-6b98e69c5ba3)
--   BEFORE:
--   Q.85)If number of people who are working in private sector in society F
--   is 50% more than total number of people in society E, then find the
--   number of people who are working in private sector in society F.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.82 to Q.86): Answer the questions based on the
--   information given below.
--
--   Number of people working in the public sector, by apartment
--   A - 150
--   B - 80
--   C - 160
--   D - 200
--   E - 100
--
--   Ratio of people working in the public sector to people working in the
--   private sector
--   A - 3 : 2
--   B - 1 : 2
--   C - 4 : 3
--   D - 5 : 3
--   E - 2 : 3
--
--
--
-- QA-2022-Q086  (paper eb45ed17-4461-41df-85b6-aaae0d965c92, question 0716785d-9937-4012-9bb4-64da0b2d51c6)
--   BEFORE:
--   Q.86)If in Society A, the ratio of number of people who are in private
--   sector was miscalculated as 3:2 instead of 5:4, then find the actual
--   number of people who are in society A.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.82 to Q.86): Answer the questions based on the
--   information given below.
--
--   Number of people working in the public sector, by apartment
--   A - 150
--   B - 80
--   C - 160
--   D - 200
--   E - 100
--
--   Ratio of people working in the public sector to people working in the
--   private sector
--   A - 3 : 2
--   B - 1 : 2
--   C - 4 : 3
--   D - 5 : 3
--   E - 2 : 3
--
--
--
-- QA-2023-Q015  (paper 38b2d867-9679-4637-8b31-c7853f076711, question 0d839d28-7553-486c-aa01-250105b64607)
--   BEFORE:
--   Q.15) Which of the following apartments have the highest number of
--   females.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.15 to Q.20): The pie chart below shows the percentage
--   distribution of the population of five different apartments in a city.
--   Total population = 8000.
--
--   Percentage distribution of population
--   P - 18.5%
--   Q - 20.5%
--   R - 17%
--   S - 20%
--   T - 24%
--
--   Percentage distribution of males in these five apartments
--   P - 70%
--   Q - 85%
--   R - 65%
--   S - 88%
--   T - 75%
--
--
--
-- QA-2023-Q016  (paper 38b2d867-9679-4637-8b31-c7853f076711, question 4abb4365-f32d-480f-bfd7-c064bbfb19e8)
--   BEFORE:
--   Q.16) Total number of males in apartment R is approximately what
--   percentage of total number of females in apartment P.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.15 to Q.20): The pie chart below shows the percentage
--   distribution of the population of five different apartments in a city.
--   Total population = 8000.
--
--   Percentage distribution of population
--   P - 18.5%
--   Q - 20.5%
--   R - 17%
--   S - 20%
--   T - 24%
--
--   Percentage distribution of males in these five apartments
--   P - 70%
--   Q - 85%
--   R - 65%
--   S - 88%
--   T - 75%
--
--
--
-- QA-2023-Q017  (paper 38b2d867-9679-4637-8b31-c7853f076711, question f051d65b-3ab1-4697-9a74-9bfd8bcda4fa)
--   BEFORE:
--   Q.17) If total number of males in apartment T is 40 more that the
--   number of males in apartment R, and the ratio of male to female in
--   apartment U is 3:2, find the number of females in apartment U.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.15 to Q.20): The pie chart below shows the percentage
--   distribution of the population of five different apartments in a city.
--   Total population = 8000.
--
--   Percentage distribution of population
--   P - 18.5%
--   Q - 20.5%
--   R - 17%
--   S - 20%
--   T - 24%
--
--   Percentage distribution of males in these five apartments
--   P - 70%
--   Q - 85%
--   R - 65%
--   S - 88%
--   T - 75%
--
--
--
-- QA-2023-Q018  (paper 38b2d867-9679-4637-8b31-c7853f076711, question 7b5a9a2a-0430-424e-b161-d2c0126be32b)
--   BEFORE:
--   Q.18) Find the average of females living in apartment Q, S and T.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.15 to Q.20): The pie chart below shows the percentage
--   distribution of the population of five different apartments in a city.
--   Total population = 8000.
--
--   Percentage distribution of population
--   P - 18.5%
--   Q - 20.5%
--   R - 17%
--   S - 20%
--   T - 24%
--
--   Percentage distribution of males in these five apartments
--   P - 70%
--   Q - 85%
--   R - 65%
--   S - 88%
--   T - 75%
--
--
--
-- QA-2023-Q019  (paper 38b2d867-9679-4637-8b31-c7853f076711, question 28667b72-f580-4e43-9daf-7e8e24b40e46)
--   BEFORE:
--   Q.19) Find the ratio of male to female in apartment Q and R together.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.15 to Q.20): The pie chart below shows the percentage
--   distribution of the population of five different apartments in a city.
--   Total population = 8000.
--
--   Percentage distribution of population
--   P - 18.5%
--   Q - 20.5%
--   R - 17%
--   S - 20%
--   T - 24%
--
--   Percentage distribution of males in these five apartments
--   P - 70%
--   Q - 85%
--   R - 65%
--   S - 88%
--   T - 75%
--
--
--
-- QA-2023-Q020  (paper 38b2d867-9679-4637-8b31-c7853f076711, question 1708f103-8bd6-472e-9b5b-243c85fd5f64)
--   BEFORE:
--   Q.20) Find out the central angle of Male in apartment Q.
--   AFTER: the block below, then the stem above, unchanged.
--   Directions (Q.15 to Q.20): The pie chart below shows the percentage
--   distribution of the population of five different apartments in a city.
--   Total population = 8000.
--
--   Percentage distribution of population
--   P - 18.5%
--   Q - 20.5%
--   R - 17%
--   S - 20%
--   T - 24%
--
--   Percentage distribution of males in these five apartments
--   P - 70%
--   Q - 85%
--   R - 65%
--   S - 88%
--   T - 75%
--
--

BEGIN;

-- 1. Prepend the recovered chart data to each stem.
UPDATE public.pyq_questions q
SET question_text = v.question_text
FROM (VALUES
  ('5a608a66-503b-4bb7-abe8-454d0b4d1047'::uuid,
   'Directions (Q.71 to Q.76): Consider the data below about the number of applications received by five colleges. The pie chart shows the percentage distribution of applications received.

Percentage distribution of applications received
  College A - 25%
  College B - 16%
  College C - 20%
  College D - 24%
  College E - 15%

Note: The average of number of applications to colleges A, C and E is 100.

Q.71) If the ratio of number of applications received by College E and C together to the number of applications received by College X is 35:18, find the number of applications received by college X?'),
  ('2b8e24f8-a535-45a8-8f98-7edd081e6fe8'::uuid,
   'Directions (Q.71 to Q.76): Consider the data below about the number of applications received by five colleges. The pie chart shows the percentage distribution of applications received.

Percentage distribution of applications received
  College A - 25%
  College B - 16%
  College C - 20%
  College D - 24%
  College E - 15%

Note: The average of number of applications to colleges A, C and E is 100.

Q.72) If the number of boys who applied in college D was 40% less than the number of girls who applied in the same college, then find out the number of boys who applied in college D?'),
  ('47e6098e-f0a0-4a7f-bd6f-e94a4f7fa9b5'::uuid,
   'Directions (Q.71 to Q.76): Consider the data below about the number of applications received by five colleges. The pie chart shows the percentage distribution of applications received.

Percentage distribution of applications received
  College A - 25%
  College B - 16%
  College C - 20%
  College D - 24%
  College E - 15%

Note: The average of number of applications to colleges A, C and E is 100.

Q.73) If the number of students who applied in college C was 10 more than the actual number, then the number of students who applied in college C is what percent of the number of students who applied in college A?'),
  ('c29e7fe7-9dcd-4ec3-9716-90e9a3681eeb'::uuid,
   'Directions (Q.71 to Q.76): Consider the data below about the number of applications received by five colleges. The pie chart shows the percentage distribution of applications received.

Percentage distribution of applications received
  College A - 25%
  College B - 16%
  College C - 20%
  College D - 24%
  College E - 15%

Note: The average of number of applications to colleges A, C and E is 100.

Q.74) The central angle of College B in degrees is'),
  ('e6443373-7ca3-4ab8-a19c-de64976a7fae'::uuid,
   'Directions (Q.71 to Q.76): Consider the data below about the number of applications received by five colleges. The pie chart shows the percentage distribution of applications received.

Percentage distribution of applications received
  College A - 25%
  College B - 16%
  College C - 20%
  College D - 24%
  College E - 15%

Note: The average of number of applications to colleges A, C and E is 100.

Q.75) What is the difference between the number of applications received by colleges A and B together and the number of applications received by college E?'),
  ('d55d19c5-f49d-4377-adba-f5a789d41a53'::uuid,
   'Directions (Q.71 to Q.76): Consider the data below about the number of applications received by five colleges. The pie chart shows the percentage distribution of applications received.

Percentage distribution of applications received
  College A - 25%
  College B - 16%
  College C - 20%
  College D - 24%
  College E - 15%

Note: The average of number of applications to colleges A, C and E is 100.

Q.76) Suppose the cost of application form in college E is Rs 100 for a boy and Rs 75 for a girl. Assume 40 boys applied in college E and the rest were girls. What is the total application amount received by college E?'),
  ('f2bb0b09-d96d-4655-a067-3797cf785df0'::uuid,
   'Directions (Q.82 to Q.86): Answer the questions based on the information given below.

Number of people working in the public sector, by apartment
  A - 150
  B - 80
  C - 160
  D - 200
  E - 100

Ratio of people working in the public sector to people working in the private sector
  A - 3 : 2
  B - 1 : 2
  C - 4 : 3
  D - 5 : 3
  E - 2 : 3

Q.82)Find the difference between number of private and public people in society D?'),
  ('e59e89dd-0dd0-4319-88bb-9064b4b3c365'::uuid,
   'Directions (Q.82 to Q.86): Answer the questions based on the information given below.

Number of people working in the public sector, by apartment
  A - 150
  B - 80
  C - 160
  D - 200
  E - 100

Ratio of people working in the public sector to people working in the private sector
  A - 3 : 2
  B - 1 : 2
  C - 4 : 3
  D - 5 : 3
  E - 2 : 3

Q.83)Find the ratio of the total number of people in society E to the number of people who are in private sector from society B.'),
  ('6c3700e1-d057-4e5f-b599-f67b2cbdd334'::uuid,
   'Directions (Q.82 to Q.86): Answer the questions based on the information given below.

Number of people working in the public sector, by apartment
  A - 150
  B - 80
  C - 160
  D - 200
  E - 100

Ratio of people working in the public sector to people working in the private sector
  A - 3 : 2
  B - 1 : 2
  C - 4 : 3
  D - 5 : 3
  E - 2 : 3

Q.84)Find the total number of people in society A, B and D.'),
  ('a82a342a-7b3e-492a-948e-6b98e69c5ba3'::uuid,
   'Directions (Q.82 to Q.86): Answer the questions based on the information given below.

Number of people working in the public sector, by apartment
  A - 150
  B - 80
  C - 160
  D - 200
  E - 100

Ratio of people working in the public sector to people working in the private sector
  A - 3 : 2
  B - 1 : 2
  C - 4 : 3
  D - 5 : 3
  E - 2 : 3

Q.85)If number of people who are working in private sector in society F is 50% more than total number of people in society E, then find the number of people who are working in private sector in society F.'),
  ('0716785d-9937-4012-9bb4-64da0b2d51c6'::uuid,
   'Directions (Q.82 to Q.86): Answer the questions based on the information given below.

Number of people working in the public sector, by apartment
  A - 150
  B - 80
  C - 160
  D - 200
  E - 100

Ratio of people working in the public sector to people working in the private sector
  A - 3 : 2
  B - 1 : 2
  C - 4 : 3
  D - 5 : 3
  E - 2 : 3

Q.86)If in Society A, the ratio of number of people who are in private sector was miscalculated as 3:2 instead of 5:4, then find the actual number of people who are in society A.'),
  ('0d839d28-7553-486c-aa01-250105b64607'::uuid,
   'Directions (Q.15 to Q.20): The pie chart below shows the percentage distribution of the population of five different apartments in a city. Total population = 8000.

Percentage distribution of population
  P - 18.5%
  Q - 20.5%
  R - 17%
  S - 20%
  T - 24%

Percentage distribution of males in these five apartments
  P - 70%
  Q - 85%
  R - 65%
  S - 88%
  T - 75%

Q.15) Which of the following apartments have the highest number of females.'),
  ('4abb4365-f32d-480f-bfd7-c064bbfb19e8'::uuid,
   'Directions (Q.15 to Q.20): The pie chart below shows the percentage distribution of the population of five different apartments in a city. Total population = 8000.

Percentage distribution of population
  P - 18.5%
  Q - 20.5%
  R - 17%
  S - 20%
  T - 24%

Percentage distribution of males in these five apartments
  P - 70%
  Q - 85%
  R - 65%
  S - 88%
  T - 75%

Q.16) Total number of males in apartment R is approximately what percentage of total number of females in apartment P.'),
  ('f051d65b-3ab1-4697-9a74-9bfd8bcda4fa'::uuid,
   'Directions (Q.15 to Q.20): The pie chart below shows the percentage distribution of the population of five different apartments in a city. Total population = 8000.

Percentage distribution of population
  P - 18.5%
  Q - 20.5%
  R - 17%
  S - 20%
  T - 24%

Percentage distribution of males in these five apartments
  P - 70%
  Q - 85%
  R - 65%
  S - 88%
  T - 75%

Q.17) If total number of males in apartment T is 40 more that the number of males in apartment R, and the ratio of male to female in apartment U is 3:2, find the number of females in apartment U.'),
  ('7b5a9a2a-0430-424e-b161-d2c0126be32b'::uuid,
   'Directions (Q.15 to Q.20): The pie chart below shows the percentage distribution of the population of five different apartments in a city. Total population = 8000.

Percentage distribution of population
  P - 18.5%
  Q - 20.5%
  R - 17%
  S - 20%
  T - 24%

Percentage distribution of males in these five apartments
  P - 70%
  Q - 85%
  R - 65%
  S - 88%
  T - 75%

Q.18) Find the average of females living in apartment Q, S and T.'),
  ('28667b72-f580-4e43-9daf-7e8e24b40e46'::uuid,
   'Directions (Q.15 to Q.20): The pie chart below shows the percentage distribution of the population of five different apartments in a city. Total population = 8000.

Percentage distribution of population
  P - 18.5%
  Q - 20.5%
  R - 17%
  S - 20%
  T - 24%

Percentage distribution of males in these five apartments
  P - 70%
  Q - 85%
  R - 65%
  S - 88%
  T - 75%

Q.19) Find the ratio of male to female in apartment Q and R together.'),
  ('1708f103-8bd6-472e-9b5b-243c85fd5f64'::uuid,
   'Directions (Q.15 to Q.20): The pie chart below shows the percentage distribution of the population of five different apartments in a city. Total population = 8000.

Percentage distribution of population
  P - 18.5%
  Q - 20.5%
  R - 17%
  S - 20%
  T - 24%

Percentage distribution of males in these five apartments
  P - 70%
  Q - 85%
  R - 65%
  S - 88%
  T - 75%

Q.20) Find out the central angle of Male in apartment Q.')
) AS v(question_id, question_text)
WHERE q.id = v.question_id
  AND q.question_text IS DISTINCT FROM v.question_text;

-- 2. Take the repaired rows, and the options the RPC cascaded to, back to pending.
UPDATE public.pyq_questions q
SET reviewer_status = 'pending', reviewed_by = NULL, reviewed_at = NULL
WHERE q.id IN (
  '5a608a66-503b-4bb7-abe8-454d0b4d1047'::uuid,
  '2b8e24f8-a535-45a8-8f98-7edd081e6fe8'::uuid,
  '47e6098e-f0a0-4a7f-bd6f-e94a4f7fa9b5'::uuid,
  'c29e7fe7-9dcd-4ec3-9716-90e9a3681eeb'::uuid,
  'e6443373-7ca3-4ab8-a19c-de64976a7fae'::uuid,
  'd55d19c5-f49d-4377-adba-f5a789d41a53'::uuid,
  'f2bb0b09-d96d-4655-a067-3797cf785df0'::uuid,
  'e59e89dd-0dd0-4319-88bb-9064b4b3c365'::uuid,
  '6c3700e1-d057-4e5f-b599-f67b2cbdd334'::uuid,
  'a82a342a-7b3e-492a-948e-6b98e69c5ba3'::uuid,
  '0716785d-9937-4012-9bb4-64da0b2d51c6'::uuid,
  '0d839d28-7553-486c-aa01-250105b64607'::uuid,
  '4abb4365-f32d-480f-bfd7-c064bbfb19e8'::uuid,
  'f051d65b-3ab1-4697-9a74-9bfd8bcda4fa'::uuid,
  '7b5a9a2a-0430-424e-b161-d2c0126be32b'::uuid,
  '28667b72-f580-4e43-9daf-7e8e24b40e46'::uuid,
  '1708f103-8bd6-472e-9b5b-243c85fd5f64'::uuid
)
  AND q.reviewer_status = 'needs_correction';

UPDATE public.pyq_options o
SET reviewer_status = 'pending', reviewed_by = NULL, reviewed_at = NULL
WHERE o.question_id IN (
  '5a608a66-503b-4bb7-abe8-454d0b4d1047'::uuid,
  '2b8e24f8-a535-45a8-8f98-7edd081e6fe8'::uuid,
  '47e6098e-f0a0-4a7f-bd6f-e94a4f7fa9b5'::uuid,
  'c29e7fe7-9dcd-4ec3-9716-90e9a3681eeb'::uuid,
  'e6443373-7ca3-4ab8-a19c-de64976a7fae'::uuid,
  'd55d19c5-f49d-4377-adba-f5a789d41a53'::uuid,
  'f2bb0b09-d96d-4655-a067-3797cf785df0'::uuid,
  'e59e89dd-0dd0-4319-88bb-9064b4b3c365'::uuid,
  '6c3700e1-d057-4e5f-b599-f67b2cbdd334'::uuid,
  'a82a342a-7b3e-492a-948e-6b98e69c5ba3'::uuid,
  '0716785d-9937-4012-9bb4-64da0b2d51c6'::uuid,
  '0d839d28-7553-486c-aa01-250105b64607'::uuid,
  '4abb4365-f32d-480f-bfd7-c064bbfb19e8'::uuid,
  'f051d65b-3ab1-4697-9a74-9bfd8bcda4fa'::uuid,
  '7b5a9a2a-0430-424e-b161-d2c0126be32b'::uuid,
  '28667b72-f580-4e43-9daf-7e8e24b40e46'::uuid,
  '1708f103-8bd6-472e-9b5b-243c85fd5f64'::uuid
)
  AND o.reviewer_status = 'needs_correction';

COMMIT;
