-- Migration 279: restore the continuation lines the parser dropped from
-- NABARD-P1-DECISION-MAKING-2023 Q.7.
--
-- Two defects were reported on this paper. ONE is repaired here. The other is
-- not a defect in the import at all and is deliberately left alone; see the
-- Q.10 section below.
--
-- Q.7 -- REPAIRED. The stem swallowed the tail of option (a), and options (a)
-- and (b) each lost their second source line. (b) is the keyed answer, so the
-- correct option read as an unfinished sentence. Source lines, verbatim from
-- docs/reference/pyq/NABARD-Grade-A-PYQ.pdf:
--
--     Q.7) Which is the most precise definition of a random heuristic among the following
--     options?
--     A. A search algorithm that uses a heuristic function to guide the search towards promising
--     areas of the search space.
--     B. A search algorithm that uses a combination of randomness and a heuristic function to
--     find a  good solution.
--     C. A search algorithm that is guaranteed to find the optimal solution to a problem.
--     D. A search algorithm that is very fast but not very accurate.
--     E. None of the above
--     Answer - B
--
-- Three rows change. Nothing is invented: every added word is the wrapped
-- second line of the row it is appended to. Whitespace is collapsed to single
-- spaces, which is how every other row in this corpus was loaded -- the source
-- prints "find a  good solution." with a double space inside the line.
--
--   pyq_questions 6aff76fe-4883-4ee4-a5c2-6dd55a307245  (stem)
--     BEFORE: Q.7) Which is the most precise definition of a random heuristic
--             among the following options? areas of the search space.
--     AFTER:  Q.7) Which is the most precise definition of a random heuristic
--             among the following options?
--
--   pyq_options c8117bba-0d49-43b9-88b5-c0eb791ae180  (label A)
--     BEFORE: A search algorithm that uses a heuristic function to guide the
--             search towards promising
--     AFTER:  A search algorithm that uses a heuristic function to guide the
--             search towards promising areas of the search space.
--
--   pyq_options 01772553-902e-4aaa-9691-3f3b74b319e7  (label B, KEYED)
--     BEFORE: A search algorithm that uses a combination of randomness and a
--             heuristic function to
--     AFTER:  A search algorithm that uses a combination of randomness and a
--             heuristic function to find a good solution.
--
-- The answer key is untouched. B stays keyed and keeps the same option id, so
-- is_correct and pyq_questions.correct_option_id are unaffected.
--
-- Q.10 -- NOT REPAIRED, and not repairable. Options (b) and (d) both read
-- "2 and 3" in the LOADED rows, and they both read "2 and 3" in the SOURCE:
--
--     Which among the following statement/s is/are incorrect?
--     A. 1 and 2
--     B. 2 and 3
--     C. 2 only
--     D. 2 and 3
--     E. 1,2, and 3
--     Answer - C
--
-- Each option occupies exactly one line, nothing wrapped, nothing dropped: the
-- import is faithful and the compendium itself prints the duplicate. There is
-- no "real option" to restore, so inventing a distinct (d) is the only way to
-- remove the duplicate and this migration will not do that. The keyed answer
-- (c) "2 only" is correct and unambiguous, so the question is answerable as it
-- stands; the duplicate costs a distractor, not correctness.
--
-- CONTENT HASH. This changes pyq_questions.question_text and
-- pyq_options.option_text, and so the content hash the paper would project
-- under. NABARD-P1-DECISION-MAKING-2023 is not projected to
-- mock_question_bank -- every row on it is reviewer_status pending and the
-- projection is verified-only -- so nothing needs re-syncing now.
--
-- BLAST RADIUS. Q.7 is one of three stems in the corpus whose tail is an
-- option fragment; the other two, CK-2023-Q010 ("is closed.") and
-- ESI-2023-Q021 ("on assessing genuine learning."), are untouched here. It is
-- also one of at least 127 options across the corpus that lost a wrapped
-- continuation line, 22 of them keyed. That measurement and its method are in
-- the commit message; this migration repairs the three rows it names and
-- nothing else.
--
-- Guarded on the current value: each statement is a no-op if the row has
-- already been repaired.

BEGIN;

UPDATE public.pyq_questions
SET question_text = 'Q.7) Which is the most precise definition of a random heuristic among the following options?'
WHERE id = '6aff76fe-4883-4ee4-a5c2-6dd55a307245'::uuid
  AND question_text = 'Q.7) Which is the most precise definition of a random heuristic among the following options? areas of the search space.';

UPDATE public.pyq_options
SET option_text = 'A search algorithm that uses a heuristic function to guide the search towards promising areas of the search space.'
WHERE id = 'c8117bba-0d49-43b9-88b5-c0eb791ae180'::uuid
  AND option_text = 'A search algorithm that uses a heuristic function to guide the search towards promising';

UPDATE public.pyq_options
SET option_text = 'A search algorithm that uses a combination of randomness and a heuristic function to find a good solution.'
WHERE id = '01772553-902e-4aaa-9691-3f3b74b319e7'::uuid
  AND option_text = 'A search algorithm that uses a combination of randomness and a heuristic function to';

COMMIT;
