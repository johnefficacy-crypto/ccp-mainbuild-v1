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
--
-- Checkpost review, third pass, adds two more partial unique indexes to this
-- same file (not merged yet at time of writing, so amending in place is
-- correct rather than a new migration):
--   fix #1  pyq_questions_paper_hash_uidx — backstops the no-identity dedup
--           hole across two SEPARATE commit() calls. REQUIRES a pre-deployment
--           duplicate audit (VERIFY DB) since normalized_question_hash is an
--           old, already-populated column — see that index's own comment.
--   fix #3c pyq_stimuli_paper_import_ref_uidx — backstops concurrent commit()
--           calls racing to create a pyq_stimuli row for the same import_ref.
--           NEW infrastructure (round 2 of this PR); no pre-existing data can
--           violate it, so no audit is required before applying it.

create unique index if not exists pyq_questions_paper_source_ref_uidx
  on public.pyq_questions(pyq_paper_id, source_question_ref)
  where source_question_ref is not null;

create unique index if not exists pyq_questions_paper_question_number_uidx
  on public.pyq_questions(pyq_paper_id, question_number)
  where question_number is not null;

-- Checkpost review (PR #894), third pass, fix #1 (DB-level backstop for the
-- no-identity duplicate hole): two SEPARATE preflight+commit round-trips for
-- the same paper, both lacking source_question_ref AND question_number, can
-- each independently preflight "ok" (each only sees its own batch) and each
-- pass commit()'s Python-level idempotency re-check if that re-check only
-- ever looked at question_number/source_question_ref — neither index above
-- helps, since both indexed columns are NULL for both rows. The Python-level
-- fix (commit() now also re-checks normalized_question_hash before inserting)
-- is the primary guard; this index is the same defense-in-depth backstop
-- pattern as the two indexes above, this time keyed on question content.
--
-- IMPORTANT — pre-deployment audit required (VERIFY DB, not yet proven safe):
-- unlike the two indexes above (which only constrain NEW v2 rows that omit
-- both identity fields — nothing existing could have violated them), this
-- index is scoped to a column (normalized_question_hash) that has existed
-- and been populated since before this PR — v1 already computes it for every
-- row on every paper. Applying this index live therefore requires first
-- confirming no EXISTING duplicate (pyq_paper_id, normalized_question_hash)
-- pairs already exist in production data: an operator could have used
-- override_errors=true in the past to force through an exact-hash duplicate
-- that preflight had already flagged as "duplicate". If any such pairs exist,
-- this index's CREATE will fail outright until they are resolved/merged
-- manually. See the companion audit query in
-- app/supabase/tests/regression_224_pyq_bulk_import_v2_uniqueness_audit.sql
-- — run it BEFORE applying this migration and resolve any rows it returns.
create unique index if not exists pyq_questions_paper_hash_uidx
  on public.pyq_questions(pyq_paper_id, normalized_question_hash)
  where normalized_question_hash is not null;

-- Checkpost review (PR #894), third pass, fix #3c (DB-level backstop for
-- durable stimulus identity): two concurrent commit() calls can both fetch
-- an empty existing_stimuli_by_ref (neither has committed yet) and both
-- create a NEW pyq_stimuli row for the same ref. This index is NEW
-- infrastructure — the metadata.import_ref convention was introduced in
-- round 2 of this PR's checkpost fixes, so unlike pyq_questions_paper_hash_uidx
-- above, NOTHING pre-existing in production could already violate it. No
-- pre-deployment duplicate audit is required for this one.
create unique index if not exists pyq_stimuli_paper_import_ref_uidx
  on public.pyq_stimuli(pyq_paper_id, (metadata->>'import_ref'))
  where metadata->>'import_ref' is not null;

notify pgrst, 'reload schema';
