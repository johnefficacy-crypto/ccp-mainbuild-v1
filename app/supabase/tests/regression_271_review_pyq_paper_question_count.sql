-- regression_271_review_pyq_paper_question_count.sql
--
-- Manual PostgreSQL regression tests for Migration 271
-- (review_pyq_paper: block verifying a paper that has no questions).
--
-- Before 271 the DB function re-validated source_type, the provenance anchor
-- and the attached document on the locked row, but never counted questions.
-- The Python endpoint had counted them since the 2026-08-25 audit, so the two
-- paths disagreed and a direct /rpc/ call could verify an empty paper —
-- which is how b06305ad and c82f3e64 came to be verified with zero questions.
--
-- Proves:
--   1. A paper with NO questions is refused at pending -> verified, with
--      'no_questions' in blocking_fields, and its trust_status is unchanged.
--   2. A paper WITH a question verifies normally (the check is not a blanket
--      block).
--   3. The new check COMPOSES with the existing ones rather than replacing
--      them: a paper missing source_type, anchor and questions reports all
--      three, in step order.
--   4. The gate is verify-only. An empty paper can still be rejected, and a
--      rejected one reopened to pending — otherwise an empty paper would be
--      unmanageable.
--   5. Adding a question unblocks a previously refused verify, with no other
--      change.
--   6. Everything else in the function is untouched: reason length, the
--      transition table (verified -> pending still refused), the
--      concurrent-modification guard, the audit row and the return shape.
--
-- Prerequisites:
--   Migrations up to and including 271 must be applied.
--
-- Usage:
--   psql "$DATABASE_URL" -f regression_271_review_pyq_paper_question_count.sql
--
-- The whole script runs inside one transaction and ROLLS BACK at the end, so
-- it leaves no rows behind. Each RPC call that is expected to raise is wrapped
-- in a savepoint block so the script continues past it.

\set ON_ERROR_STOP on
\pset pager off

BEGIN;

-- ── Fixtures ──────────────────────────────────────────────────────────────────
INSERT INTO auth.users (id, email)
VALUES ('aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com');

INSERT INTO public.exams (id, slug, name, exam_type, is_active)
VALUES ('bbbbbbbb-0000-4000-8000-0000000271b1', 'regression-271-exam',
        'Regression 271 Exam', 'recruitment', true);

-- EMPTY: complete provenance, zero questions — the case 271 exists for.
-- FULL:  complete provenance, one question.
-- BARE:  no provenance at all and no questions — proves the checks compose.
--        source_type is NOT NULL DEFAULT 'unknown', so 'unknown' is the only
--        way check (a) can ever fire; a NULL there is impossible.
INSERT INTO public.pyq_papers (id, exam_id, year, trust_status, source_type, source_url)
VALUES
  ('cccccccc-0000-4000-8000-00000271e0e0', 'bbbbbbbb-0000-4000-8000-0000000271b1',
   2024, 'pending', 'official', 'https://example.gov/regression-271.pdf'),
  ('cccccccc-0000-4000-8000-00000271f0f0', 'bbbbbbbb-0000-4000-8000-0000000271b1',
   2024, 'pending', 'official', 'https://example.gov/regression-271.pdf'),
  ('cccccccc-0000-4000-8000-000002710aa0', 'bbbbbbbb-0000-4000-8000-0000000271b1',
   2024, 'pending', 'unknown', NULL);

INSERT INTO public.pyq_questions (id, pyq_paper_id, question_number, question_text)
VALUES ('dddddddd-0000-4000-8000-00000271d1d1',
        'cccccccc-0000-4000-8000-00000271f0f0',
        1, 'A question, so this paper is not empty.');

-- ── 1. Empty paper is refused, and stays pending ─────────────────────────────
\echo ''
\echo '1. empty paper, pending -> verified  (expect: no_questions)'
DO $$
DECLARE v_msg text;
BEGIN
    PERFORM public.review_pyq_paper(
        'cccccccc-0000-4000-8000-00000271e0e0', 'pending', 'verified',
        'attempt to verify an empty paper',
        'aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com');
    RAISE EXCEPTION 'FAIL: an empty paper was verified';
EXCEPTION WHEN SQLSTATE 'P0422' THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    IF v_msg NOT LIKE '%no_questions%' THEN
        RAISE EXCEPTION 'FAIL: expected no_questions, got: %', v_msg;
    END IF;
    RAISE NOTICE 'PASS: %', v_msg;
END $$;

DO $$
BEGIN
    IF (SELECT trust_status FROM public.pyq_papers
        WHERE id = 'cccccccc-0000-4000-8000-00000271e0e0') <> 'pending' THEN
        RAISE EXCEPTION 'FAIL: refused verify still moved trust_status';
    END IF;
    RAISE NOTICE 'PASS: trust_status unchanged after the refusal';
END $$;

-- ── 2. A populated paper still verifies ──────────────────────────────────────
\echo ''
\echo '2. paper with a question, pending -> verified  (expect: ok)'
DO $$
DECLARE v_res jsonb;
BEGIN
    v_res := public.review_pyq_paper(
        'cccccccc-0000-4000-8000-00000271f0f0', 'pending', 'verified',
        'verify a populated paper',
        'aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com');
    IF (v_res->>'ok') <> 'true' THEN
        RAISE EXCEPTION 'FAIL: populated paper did not verify: %', v_res;
    END IF;
    -- 6b. Return shape is exactly 187's three keys.
    IF NOT (v_res ? 'ok' AND v_res ? 'audit_id' AND v_res ? 'row')
       OR (SELECT count(*) FROM jsonb_object_keys(v_res)) <> 3 THEN
        RAISE EXCEPTION 'FAIL: return shape changed: %', v_res;
    END IF;
    RAISE NOTICE 'PASS: verified, return shape is {ok, audit_id, row}';
END $$;

-- ── 3. Checks compose, in step order ─────────────────────────────────────────
\echo ''
\echo '3. paper with nothing  (expect: source_type,source_url,no_questions)'
DO $$
DECLARE v_msg text;
BEGIN
    PERFORM public.review_pyq_paper(
        'cccccccc-0000-4000-8000-000002710aa0', 'pending', 'verified',
        'attempt to verify a paper with nothing',
        'aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com');
    RAISE EXCEPTION 'FAIL: a paper with no provenance was verified';
EXCEPTION WHEN SQLSTATE 'P0422' THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    IF v_msg NOT LIKE '%source_type,source_url,no_questions%' THEN
        RAISE EXCEPTION 'FAIL: expected all three in step order, got: %', v_msg;
    END IF;
    RAISE NOTICE 'PASS: %', v_msg;
END $$;

-- ── 4. The gate is verify-only ───────────────────────────────────────────────
\echo ''
\echo '4. empty paper: pending -> rejected -> pending  (expect: both ok)'
DO $$
BEGIN
    IF (public.review_pyq_paper(
            'cccccccc-0000-4000-8000-00000271e0e0', 'pending', 'rejected',
            'reject the empty paper',
            'aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com')
        ->> 'ok') <> 'true' THEN
        RAISE EXCEPTION 'FAIL: could not reject an empty paper';
    END IF;
    IF (public.review_pyq_paper(
            'cccccccc-0000-4000-8000-00000271e0e0', 'rejected', 'pending',
            'reopen the empty paper',
            'aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com')
        ->> 'ok') <> 'true' THEN
        RAISE EXCEPTION 'FAIL: could not reopen an empty paper';
    END IF;
    RAISE NOTICE 'PASS: an empty paper is still rejectable and reopenable';
END $$;

-- ── 5. Adding a question unblocks the verify ─────────────────────────────────
\echo ''
\echo '5. add a question to the empty paper, then verify  (expect: ok)'
INSERT INTO public.pyq_questions (id, pyq_paper_id, question_number, question_text)
VALUES ('dddddddd-0000-4000-8000-00000271d2d2',
        'cccccccc-0000-4000-8000-00000271e0e0',
        1, 'The question that unblocks the gate.');

DO $$
BEGIN
    IF (public.review_pyq_paper(
            'cccccccc-0000-4000-8000-00000271e0e0', 'pending', 'verified',
            'verify now that the paper has a question',
            'aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com')
        ->> 'ok') <> 'true' THEN
        RAISE EXCEPTION 'FAIL: paper still blocked after a question was added';
    END IF;
    RAISE NOTICE 'PASS: the same paper verifies once it carries a question';
END $$;

-- ── 6. Everything else is untouched ──────────────────────────────────────────
\echo ''
\echo '6a. transition table: verified -> pending  (expect: transition_not_allowed)'
DO $$
DECLARE v_msg text;
BEGIN
    PERFORM public.review_pyq_paper(
        'cccccccc-0000-4000-8000-00000271f0f0', 'verified', 'pending',
        'attempt to unverify directly',
        'aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com');
    RAISE EXCEPTION 'FAIL: verified -> pending was permitted';
EXCEPTION WHEN SQLSTATE 'P0422' THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    IF v_msg NOT LIKE '%transition_not_allowed%' THEN
        RAISE EXCEPTION 'FAIL: expected transition_not_allowed, got: %', v_msg;
    END IF;
    RAISE NOTICE 'PASS: %', v_msg;
END $$;

\echo ''
\echo '6b. reason length  (expect: invalid_reason)'
DO $$
DECLARE v_msg text;
BEGIN
    PERFORM public.review_pyq_paper(
        'cccccccc-0000-4000-8000-000002710aa0', 'pending', 'rejected',
        'short',
        'aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com');
    RAISE EXCEPTION 'FAIL: a 5-character reason was accepted';
EXCEPTION WHEN SQLSTATE 'P0422' THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    IF v_msg NOT LIKE '%invalid_reason%' THEN
        RAISE EXCEPTION 'FAIL: expected invalid_reason, got: %', v_msg;
    END IF;
    RAISE NOTICE 'PASS: %', v_msg;
END $$;

\echo ''
\echo '6c. concurrent-modification guard  (expect: concurrent_modification)'
DO $$
DECLARE v_msg text;
BEGIN
    PERFORM public.review_pyq_paper(
        'cccccccc-0000-4000-8000-00000271f0f0', 'pending', 'rejected',
        'call with a stale expected status',
        'aaaaaaaa-0000-4000-8000-0000000271a1', 'regression-271@example.com');
    RAISE EXCEPTION 'FAIL: a stale expected_status was accepted';
EXCEPTION WHEN SQLSTATE 'P0409' THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    RAISE NOTICE 'PASS: %', v_msg;
END $$;

\echo ''
\echo '6d. audit trail: one row per successful transition, none for refusals'
DO $$
DECLARE v_count int;
BEGIN
    SELECT count(*) INTO v_count
    FROM public.admin_audit_logs
    WHERE action = 'exam_intel.cms.pyq_paper.review'
      AND actor_email = 'regression-271@example.com';
    -- 4 successes: FULL verified, EMPTY rejected, EMPTY reopened, EMPTY verified.
    IF v_count <> 4 THEN
        RAISE EXCEPTION 'FAIL: expected 4 audit rows, found %', v_count;
    END IF;
    RAISE NOTICE 'PASS: 4 audit rows, none written for the refused calls';
END $$;

\echo ''
\echo 'All regression checks passed. Rolling back.'
ROLLBACK;
