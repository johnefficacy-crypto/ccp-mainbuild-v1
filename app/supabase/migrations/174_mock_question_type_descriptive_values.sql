-- =============================================================================
-- 174_mock_question_type_descriptive_values.sql
-- B-PR1: descriptive-answer schema foundation (enum values only).
--
-- Adds the descriptive question-type values to the mock_question_type enum so
-- that future PRs can introduce typed-answer attempts (essay / precis / letter
-- and a generic descriptive bucket).  This migration is intentionally limited
-- to enum ADD VALUE statements:
--
--   * No table ALTERs.
--   * No DDL or DML that references the new values (a new enum value cannot be
--     used in the same transaction that adds it).
--   * No DO/BEGIN wrapper — ALTER TYPE ... ADD VALUE IF NOT EXISTS is itself
--     idempotent and is safest run outside an explicit transaction block.
--
-- The columns and behaviour that consume these values land in later PRs.
-- =============================================================================

alter type mock_question_type add value if not exists 'descriptive';
alter type mock_question_type add value if not exists 'essay';
alter type mock_question_type add value if not exists 'precis';
alter type mock_question_type add value if not exists 'letter';
