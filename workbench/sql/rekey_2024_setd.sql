-- Re-key UPSC Prelims GS Paper I 2024 against Set D.
--
-- The paper in the DB is Set D. It was keyed against Set C, so 2024 was the one
-- paper of the seven whose key came from the wrong series. UPSC shuffles option
-- order between series, so a Set C letter points at the wrong option text: an
-- independent read of eight questions whose answer is unambiguous from the
-- option text alone (Q9 longest border, Q11 provisional President, Q30 largest
-- SO2 source, Q40 latest ICH inscription, Q55 cocoa producers, Q68 fig wasp,
-- Q95 fifth-generation aircraft, Q97 fuel cell exhaust) gave the pattern
-- a d d c c a d d, which matches Set D on 8 of 8 and Set C on 0 of 8.
--
-- The dropped questions confirm it independently. Set D drops Q32, Q37 and Q80;
-- Set C drops Q42, Q47 and Q90. The DB currently has the Set C drops unkeyed.
--
-- This clears all existing keys for the paper and rewrites them from Set D:
-- 97 keyed, Q32/Q37/Q80 left NULL.
--
-- Source: AnsKey-CivilServicesPExam-2024-GeneralStudies-I-210525.pdf, Series D
-- ("Total Questions 100, No. of Questions Dropped 3, taken for Scoring 97").
--
-- Written by label, matched to option_id inside the transaction, so it cannot
-- inherit a stale option id.

BEGIN;

-- 1. Clear every existing key on this paper.
UPDATE public.pyq_options o
SET is_correct = false
FROM public.pyq_questions q
WHERE q.id = o.question_id
  AND q.pyq_paper_id = '4d0bed5e-3b8a-4143-92c3-614ede901af5'
  AND o.is_correct;

UPDATE public.pyq_questions
SET correct_option_id = NULL
WHERE pyq_paper_id = '4d0bed5e-3b8a-4143-92c3-614ede901af5';

-- 2. Mark the correct option for each keyed question, by Set D label.
UPDATE public.pyq_options o
SET is_correct = true
FROM public.pyq_questions q,
     (VALUES
  (1, 'd'),
  (2, 'a'),
  (3, 'b'),
  (4, 'd'),
  (5, 'c'),
  (6, 'd'),
  (7, 'd'),
  (8, 'c'),
  (9, 'a'),
  (10, 'c'),
  (11, 'd'),
  (12, 'a'),
  (13, 'c'),
  (14, 'c'),
  (15, 'b'),
  (16, 'd'),
  (17, 'a'),
  (18, 'c'),
  (19, 'd'),
  (20, 'b'),
  (21, 'd'),
  (22, 'c'),
  (23, 'c'),
  (24, 'b'),
  (25, 'c'),
  (26, 'd'),
  (27, 'b'),
  (28, 'd'),
  (29, 'c'),
  (30, 'd'),
  (31, 'a'),
  (33, 'd'),
  (34, 'b'),
  (35, 'b'),
  (36, 'a'),
  (38, 'b'),
  (39, 'a'),
  (40, 'c'),
  (41, 'd'),
  (42, 'd'),
  (43, 'c'),
  (44, 'b'),
  (45, 'c'),
  (46, 'c'),
  (47, 'd'),
  (48, 'd'),
  (49, 'b'),
  (50, 'b'),
  (51, 'd'),
  (52, 'b'),
  (53, 'c'),
  (54, 'a'),
  (55, 'c'),
  (56, 'b'),
  (57, 'a'),
  (58, 'c'),
  (59, 'a'),
  (60, 'b'),
  (61, 'c'),
  (62, 'a'),
  (63, 'd'),
  (64, 'd'),
  (65, 'c'),
  (66, 'a'),
  (67, 'b'),
  (68, 'a'),
  (69, 'c'),
  (70, 'd'),
  (71, 'b'),
  (72, 'a'),
  (73, 'd'),
  (74, 'c'),
  (75, 'b'),
  (76, 'b'),
  (77, 'd'),
  (78, 'b'),
  (79, 'c'),
  (81, 'c'),
  (82, 'c'),
  (83, 'b'),
  (84, 'd'),
  (85, 'b'),
  (86, 'a'),
  (87, 'b'),
  (88, 'c'),
  (89, 'd'),
  (90, 'a'),
  (91, 'b'),
  (92, 'd'),
  (93, 'a'),
  (94, 'b'),
  (95, 'd'),
  (96, 'a'),
  (97, 'd'),
  (98, 'c'),
  (99, 'd'),
  (100, 'b')
     ) AS k(qnum, label)
WHERE q.pyq_paper_id = '4d0bed5e-3b8a-4143-92c3-614ede901af5'
  AND q.question_number = k.qnum
  AND o.question_id = q.id
  AND lower(o.option_label) = k.label;

-- 3. Point each question at its correct option.
UPDATE public.pyq_questions q
SET correct_option_id = o.id
FROM public.pyq_options o
WHERE o.question_id = q.id
  AND o.is_correct
  AND q.pyq_paper_id = '4d0bed5e-3b8a-4143-92c3-614ede901af5';

-- 4. Abort unless the result is exactly right.
DO $$
DECLARE keyed_n int; marked_n int; bad_n int;
BEGIN
  SELECT count(*) INTO keyed_n FROM public.pyq_questions
   WHERE pyq_paper_id = '4d0bed5e-3b8a-4143-92c3-614ede901af5'
     AND correct_option_id IS NOT NULL;

  SELECT count(*) INTO marked_n FROM public.pyq_options o
    JOIN public.pyq_questions q ON q.id = o.question_id
   WHERE q.pyq_paper_id = '4d0bed5e-3b8a-4143-92c3-614ede901af5'
     AND o.is_correct;

  SELECT count(*) INTO bad_n FROM public.pyq_questions q
   WHERE q.pyq_paper_id = '4d0bed5e-3b8a-4143-92c3-614ede901af5'
     AND (SELECT count(*) FROM public.pyq_options o
           WHERE o.question_id = q.id AND o.is_correct) > 1;

  IF keyed_n <> 97 THEN
    RAISE EXCEPTION 'expected 97 keyed questions, got %', keyed_n;
  END IF;
  IF marked_n <> 97 THEN
    RAISE EXCEPTION 'expected 97 marked options, got %', marked_n;
  END IF;
  IF bad_n > 0 THEN
    RAISE EXCEPTION '% question(s) have more than one correct option', bad_n;
  END IF;
END $$;

COMMIT;
