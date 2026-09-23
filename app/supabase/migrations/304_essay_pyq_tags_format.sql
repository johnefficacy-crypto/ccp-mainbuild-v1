-- 304_essay_pyq_tags_format.sql
--
-- essay_pyq_tags gains a `format` axis, and `essay_type` stops mislabelling the
-- rows that have no essay type at all.
--
-- WHY
-- ---
-- The table was built for the UPSC Essay paper, where every row IS an essay
-- (265_essay_theme_taxonomy.sql:31-53). RBI Grade B Phase II English is not:
-- one paper carries an essay, a precis and a comprehension, and the worksheet
-- that feeds this table splits 24 rows as essay 16 / precis 4 / comprehension 4
-- (workbench/worksheets/RBI-ENGLISH-DESCRIPTIVE-tags.csv). Two defects block it,
-- both recorded as G1 and G4 in workbench/worksheets/RBI-ENGLISH-SCHEME.md §7:
--
--   G1  no column carries the format axis, so a precis row is indistinguishable
--       from an essay row once stored.
--   G4  `essay_type text not null default 'quote_abstract'` (265:36-37) cannot
--       be satisfied honestly by a precis or comprehension row. They have no
--       essay type. An insert that omits it does not fail — it SILENTLY records
--       the row as a quote-abstract essay.
--
-- WHAT THIS DOES, AND THE TWO JUDGEMENT CALLS
-- -------------------------------------------
-- A. `format` is NOT NULL, backfilled, and deliberately has NO DEFAULT.
--
--    100 UPSC essay rows are live in this table. Every one of them is an essay
--    by construction — the table has only ever held UPSC Essay-paper tags — so
--    the backfill to 'essay' is unambiguous and loses nothing. That makes
--    NOT NULL reachable without a nullable interregnum, and a nullable `format`
--    would have left those 100 rows permanently unclassified, which is the
--    state this column exists to remove.
--
--    No DEFAULT is the deliberate half. A default is exactly what produced G4:
--    a column that quietly answers for a caller who never said anything. Giving
--    `format` a DEFAULT 'essay' would reintroduce the identical failure one
--    column over — a precis row inserted without `format` would come back an
--    essay. With no default, such an insert raises a NOT NULL violation. Loud
--    beats silent. The CMS write path is updated in the same PR to require
--    `format` and return 422, so operators see a clear message rather than a
--    raw constraint error.
--
-- B. `essay_type` gets a CHECK tied to `format`, not merely a relaxed NOT NULL.
--
--    The brief allowed either. A bare "make it nullable" fixes only the default
--    half of G4: it would still permit a precis row carrying
--    essay_type='quote_abstract', because nothing would forbid it. The pairing
--    CHECK closes both directions — an essay must state its type, a precis and
--    a comprehension must not pretend to have one.
--
--    Against the 100 live rows the CHECK is satisfied before it is added: each
--    is format='essay' after the backfill in A, and each already has a non-null
--    essay_type because the column was NOT NULL until this migration. The
--    constraint therefore validates without rejecting a single existing row.
--    The DEFAULT is dropped alongside the NOT NULL; leaving it would mean an
--    omitted essay_type on a precis row became 'quote_abstract' and then failed
--    the new CHECK with a confusing error instead of simply being NULL.
--
-- C. `quote_source_type` needs NO change — checked, and it does not have the
--    problem. 265:38-42 already declares it nullable with a null-tolerant CHECK
--    (`quote_source_type is null or quote_source_type in (...)`), so a precis or
--    comprehension row satisfies it by leaving it NULL. The worksheet agrees:
--    all 24 rows carry an empty quote_source_type. It is left untouched.
--
-- NOT IN SCOPE (locked before this migration was written)
-- -------------------------------------------------------
--   * No `parent_question_id`, no `prompt_index`. Split prompts get their own
--     pyq_questions rows, one per prompt, the same convention UPSC map-item
--     rows use. The parent/child link lives in pyq_questions, not here.
--   * `unique(question_id, theme_id)` (265:52) is UNCHANGED. With one
--     question_id per prompt it no longer blocks two prompts of one container
--     sharing a theme, so there is nothing to relax.
--   * essay_themes rows and theme codes are untouched — a separate data task.
--   * Creating the 16 child pyq_questions rows is a separate operator load.
--     The numbering block IS now decided, and is recorded below so the load
--     spec and this schema cannot drift apart.
--
-- CHILD-ROW NUMBERING (operator load spec — decided, NOT executed here)
-- ---------------------------------------------------------------------
-- The four RBI Phase II English papers occupy question_number 1-15 only, with
-- display_order null throughout. The highest number seen anywhere on RBI is 200
-- (question_number and display_order, on a Phase I paper); uniqueness is per
-- paper so that does not constrain these, but the block below stays clear of it.
--
--   Block: 301-316 — per paper, one contiguous run of 4 per essay container.
--     2022 essay (question_number 1) -> children 301, 302, 303, 304
--     2023 essay (question_number 1) -> children 301, 302, 303, 304
--     2024 essay (question_number 1) -> children 301, 302, 303, 304
--     2025 essay (question_number 1) -> children 301, 302, 303, 304
--
--   Each paper is independent — reusing the same numbers across papers is fine
--   because uniqueness is per paper. The 300-block leaves 16-299 free and clears
--   the 200 already in use elsewhere on RBI.
--
--   display_order = the same value as question_number. display_order is also
--   globally unique per paper; leaving it null or reusing a value is what caused
--   the 2022 UPSC Essay bug, so it is set explicitly and identically.
--
--   question_ref extends the existing section-prefixed shape (ENG-Q1,
--   ESI-15-Q1, FM-10-Q2) with the prompt index: ENG-Q1-P1 … ENG-Q1-P4. No
--   collision with the parent's ENG-Q1.
--
--   The parent row is KEPT. Its question_text stays the container instruction
--   and it carries metadata.is_container = true. Each child carries
--   metadata.parent_question_id and metadata.prompt_index. Theme tags are
--   written against CHILD rows only — never the container — which is what makes
--   265:52's unique(question_id, theme_id) a non-issue for same-theme prompts.
--
--   Precis (question_number 2) and comprehension (question_number 3) are
--   unchanged and get no children.
--
-- Applied version = MAX(filesystem)+1 at authoring (303_answer_structures).
-- Reconcile against the deployed state with
--   SELECT MAX(version) FROM schema_migrations;
-- before applying. Migrations are immutable once merged.

-- ─── A. format: add, backfill, then constrain ────────────────────────────
alter table public.essay_pyq_tags
  add column if not exists format text;

-- Backfill before NOT NULL. Idempotent: a re-run finds nothing null.
update public.essay_pyq_tags
   set format = 'essay'
 where format is null;

alter table public.essay_pyq_tags
  alter column format set not null;

-- No DEFAULT is set on purpose — see note A above.
alter table public.essay_pyq_tags
  drop constraint if exists essay_pyq_tags_format_check;
alter table public.essay_pyq_tags
  add constraint essay_pyq_tags_format_check
  check (format in ('essay', 'precis', 'comprehension'));

-- ─── B. essay_type: drop default + NOT NULL, tie it to format ────────────
alter table public.essay_pyq_tags
  alter column essay_type drop default;
alter table public.essay_pyq_tags
  alter column essay_type drop not null;

-- 265:36-37's value CHECK (`essay_type in ('quote_abstract','issue_concrete')`)
-- is intentionally left in place. A CHECK fails only on FALSE, and a NULL
-- essay_type evaluates it to NULL, so a precis row passes it untouched.
alter table public.essay_pyq_tags
  drop constraint if exists essay_pyq_tags_essay_type_format_check;
alter table public.essay_pyq_tags
  add constraint essay_pyq_tags_essay_type_format_check
  check (
    (format = 'essay' and essay_type is not null)
    or (format in ('precis', 'comprehension') and essay_type is null)
  );

-- ─── Index ───────────────────────────────────────────────────────────────
-- The Essay Builder reads essay-format rows only; the RBI English worksheet
-- reads by format. Both are equality filters on a low-cardinality column.
create index if not exists idx_essay_pyq_tags_format
  on public.essay_pyq_tags(format);

comment on column public.essay_pyq_tags.format is
  'Descriptive prompt format: essay | precis | comprehension. NOT NULL with no '
  'default — a caller must state it. essay_type is required when format=''essay'' '
  'and must be NULL otherwise (essay_pyq_tags_essay_type_format_check).';

notify pgrst, 'reload schema';
