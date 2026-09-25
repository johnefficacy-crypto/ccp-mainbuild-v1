-- 309_mock_question_bank_authored_metadata.sql
-- REG-CORPUS-02 — authored, multi-exam rows in mock_question_bank.
--
-- Context: workbench/investigations/REG-CORPUS-01_discovery.md (gaps 1, 2, 3, 5, 9).
-- Design (locked): no new question table. An authored row keeps exam_id NULL
-- and is scoped to exams through its primary topic's topics.metadata.exams
-- (app/backend/app/exam_intelligence/authored_scope.py). Difficulty stays
-- easy|medium|hard; the authoring rubric level lives in metadata.rubric_level.
-- A case set is N rows sharing metadata.stimulus_group, each owning its own
-- mock_question_stimuli snapshot rows (no cross-row sharing).
--
-- 1. mock_question_bank.metadata — jsonb object, default '{}'. The table has
--    no metadata column today (135:58-78 and every later ALTER).
-- 2. CHECKs on the two keys this PR writes: rubric_level ∈ L1..L4 when present,
--    stimulus_group a non-empty string when present. Added NOT VALID and then
--    validated, so the scan runs under SHARE UPDATE EXCLUSIVE, not the
--    ACCESS EXCLUSIVE lock of a plain ADD CONSTRAINT.
-- 3. Partial indexes for the authored topic lookups
--    (pyq_practice._authored_rows_for_targets reads topic_id IN (...) and
--    microtopic_id IN (...) under the authored predicate).
--
-- Safe on a DB with live PYQ rows: step 1 is a constant-default ADD COLUMN
-- (catalog-only in PG ≥ 11, no rewrite); every existing row gets '{}', which
-- satisfies both CHECKs; the partial indexes match zero rows today
-- (operator-verified 2026-09-25: no source_kind='authored' rows exist). No
-- existing column, constraint, function or policy is changed; the PYQ
-- projection RPC (307) lists its insert columns explicitly and is unaffected.
-- No new table, so no new RLS policy (mock_question_bank policies unchanged).

begin;

alter table public.mock_question_bank
  add column if not exists metadata jsonb not null default '{}'::jsonb;

comment on column public.mock_question_bank.metadata is
  'Authoring metadata. Known keys: rubric_level (L1-L4, authoring rubric; '
  'difficulty stays easy|medium|hard), stimulus_group (case-set key shared by '
  'the rows of one case set). Not read by the PYQ projection.';

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'mock_question_bank_metadata_shape'
      and conrelid = 'public.mock_question_bank'::regclass
  ) then
    alter table public.mock_question_bank
      add constraint mock_question_bank_metadata_shape check (
        jsonb_typeof(metadata) = 'object'
        and (
          not (metadata ? 'rubric_level')
          or metadata->>'rubric_level' in ('L1', 'L2', 'L3', 'L4')
        )
        and (
          not (metadata ? 'stimulus_group')
          or (
            jsonb_typeof(metadata->'stimulus_group') = 'string'
            and length(btrim(metadata->>'stimulus_group')) > 0
          )
        )
      ) not valid;
  end if;
end $$;

alter table public.mock_question_bank
  validate constraint mock_question_bank_metadata_shape;

create index if not exists idx_mqb_authored_topic
  on public.mock_question_bank (topic_id)
  where source_kind = 'authored' and exam_id is null and pyq_question_id is null;

create index if not exists idx_mqb_authored_microtopic
  on public.mock_question_bank (microtopic_id)
  where source_kind = 'authored' and exam_id is null and pyq_question_id is null;

commit;

notify pgrst, 'reload schema';

-- DOWN (manual):
--   drop index if exists public.idx_mqb_authored_microtopic;
--   drop index if exists public.idx_mqb_authored_topic;
--   alter table public.mock_question_bank drop constraint if exists mock_question_bank_metadata_shape;
--   alter table public.mock_question_bank drop column if exists metadata;
