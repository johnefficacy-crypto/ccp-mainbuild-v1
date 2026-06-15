# UPSC CSE canary compiler preconditions

Status captured for Wave 4.5B before Compiler v1 work. This is a diagnosis and gate document only; it does not implement compiler behavior, planner behavior, trust promotion, or locked coverage creation.

## Canonical exam identity

- Canonical UPSC CSE survivor exam ID: `5466e62f-7382-4a38-ba96-2fe5fbfeaba2`.
- Merged-from/stale exam ID checked: `a0000002-0000-0000-0000-000000000001`.
- Strict `upsc-cse` resolver result: exactly one active canonical row.
- Merged-from row status: gone from the active canonical resolver result.

## FK fan-out summary

- Merged-from child counts: zero across exam-linked child tables checked during the canary diagnosis.
- UPSC CSE PYQ papers: all attached to the canonical survivor exam ID.
- Cycle/phase FK consistency: the UPSC 2026 PYQ paper points to a cycle and phase that both belong to the canonical survivor exam.

## PYQ completeness summary

Known live UPSC CSE 2026 PYQ paper state:

- Questions: 100 distinct questions.
- Options: 400 options.
- Correct options: 97.
- Verified questions: 98.
- Rejected questions: 2.
- Topic tags: 0.

## Current compiler input blocker

The remaining compiler input blocker is missing verified topic tags for verified 2026 UPSC CSE PYQ questions. The canary paper has verified question content and options, but zero topic tags means compiler inputs cannot yet produce topic-grounded coverage or study-plan signals safely.

## Compiler gate status

Compiler v1 remains **blocked** for UPSC CSE until verified topic tags exist for the verified PYQ questions. The smoke check at `app/supabase/checks/upsc_cse_compiler_preconditions.sql` is intentionally expected to fail while the verified topic-tag count is zero.
