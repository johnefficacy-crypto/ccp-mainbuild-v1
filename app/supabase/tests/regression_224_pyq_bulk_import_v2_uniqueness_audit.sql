-- regression_224_pyq_bulk_import_v2_uniqueness_audit.sql
--
-- Pre-deployment duplicate audit for migration 224's checkpost-round-3 fix #1
-- (pyq_questions_paper_hash_uidx: unique on (pyq_paper_id, normalized_question_hash)
-- where normalized_question_hash is not null).
--
-- Unlike the other three partial unique indexes added by migration 224
-- (pyq_questions_paper_source_ref_uidx, pyq_questions_paper_question_number_uidx,
-- pyq_stimuli_paper_import_ref_uidx), this one is scoped to a column
-- (normalized_question_hash) that has existed and been populated since BEFORE
-- this PR — the v1 bulk importer already computes it for every row on every
-- paper. It is therefore possible for live production data to already contain
-- an exact-hash duplicate pair: an operator could have used
-- override_errors=true in the past to force through a row that preflight had
-- already flagged as "duplicate" (exact hash match).
--
-- If this migration's CREATE UNIQUE INDEX for pyq_questions_paper_hash_uidx is
-- applied while such a duplicate pair exists, the CREATE will fail outright
-- (Postgres refuses to build a unique index over data that violates it).
--
-- Usage (run BEFORE applying migration 224's pyq_questions_paper_hash_uidx
-- index, against the target environment):
--   psql "$DATABASE_URL" -f regression_224_pyq_bulk_import_v2_uniqueness_audit.sql
--
-- Expected output: zero rows. If any rows are returned, DO NOT apply the
-- pyq_questions_paper_hash_uidx index yet — for each (pyq_paper_id,
-- normalized_question_hash) pair returned, manually review the duplicate
-- pyq_questions rows (their reviewer_status, source_question_ref,
-- question_number, and any dependent pyq_options / pyq_question_stimuli /
-- mock_question_bank rows) and resolve the conflict before re-running this
-- audit — typically by deleting or merging the duplicate (keeping whichever
-- row has the more complete/verified review state), never by silently
-- deleting the query's evidence. Re-run this audit until it returns zero rows,
-- then apply the index.

select
  pyq_paper_id,
  normalized_question_hash,
  count(*) as duplicate_count,
  array_agg(id order by created_at) as duplicate_question_ids
from public.pyq_questions
where normalized_question_hash is not null
group by pyq_paper_id, normalized_question_hash
having count(*) > 1;
