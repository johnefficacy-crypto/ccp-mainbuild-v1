-- 224_pyq_bulk_import_v2_uniqueness.sql
-- PYQ Intelligence Importer v2 (PR #894), checkpost fix #10 (defense in depth):
-- DB-level uniqueness backstop for the bulk importer's dedup guarantees.
--
-- The Python-level dedup ladder in pyq_bulk_import.py (preflight's existing-row
-- hash/identity checks, commit's idempotency re-check, and the new same-upload
-- batch-local hash check) is the primary guard against duplicate question rows.
-- These two partial unique indexes are an additional safety net, not a
-- replacement: they catch what a concurrency race (two commits interleaving
-- writes for the same source_question_ref/question_number) or a bug in the
-- Python dedup logic would otherwise let through silently. A unique-violation
-- surfacing from either index is caught by commit()'s existing generic
-- per-row `except Exception` handler and reported as an honest "failed" row
-- rather than crashing the whole batch or double-inserting.
--
-- Both indexes are partial (`where ... is not null`) because both identity
-- fields are optional for v2 rows — NULL values must never collide with
-- each other under a plain unique index, and Postgres partial indexes with a
-- `is not null` predicate correctly exclude NULLs from the uniqueness check.

create unique index if not exists pyq_questions_paper_source_ref_uidx
  on public.pyq_questions(pyq_paper_id, source_question_ref)
  where source_question_ref is not null;

create unique index if not exists pyq_questions_paper_question_number_uidx
  on public.pyq_questions(pyq_paper_id, question_number)
  where question_number is not null;

notify pgrst, 'reload schema';
