# Essay Builder — migrations 266-267 + endpoint live validation

Use this runbook after the Essay Builder schema/backend PRs are merged and
before marking `essay-builder-266-live-validation` passed. It covers migration
266 (`266_essay_brainstorm_idea_canvas.sql`), migration 267
(`267_essay_brainstorm_canvas_position.sql`) and the aspirant-facing endpoints
in `app/backend/app/api/essay_builder.py`.

Code completion is not operator validation. Every step below needs live proof
captured against the deployed environment.

## Preconditions

- Migrations through 265 are applied on the target Supabase database.
- At least one `public.essay_themes` row exists (15 themes were imported for
  the essay taxonomy; any one of them works as the fixture theme).
- Two real aspirant accounts with permanent (non-anonymous) Supabase identities
  are available — the ownership proof needs a second caller, not a second token
  for the same user.

## 1. Apply migrations 266 and 267

Confirm `266_essay_brainstorm_idea_canvas.sql` is the next unapplied migration
in the live ledger, then apply it through the normal deployment workflow.

Confirm the column and constraints landed:

```sql
select column_name, is_nullable
  from information_schema.columns
 where table_schema = 'public'
   and table_name = 'essay_brainstorm_blocks'
   and column_name = 'lens';
-- expect: lens | YES

select conname, pg_get_constraintdef(oid)
  from pg_constraint
 where conrelid = 'public.essay_brainstorm_blocks'::regclass
   and contype = 'c';
-- expect exactly two CHECKs:
--   essay_brainstorm_blocks_block_type_check — 11 values, including
--     vocab_term / book_reference / stat_to_verify AND all eight from 265
--   essay_brainstorm_blocks_lens_check — null OR the six lens values
```

The migration discovers and drops migration 265's generated `block_type` CHECK
before adding the replacement. If the query above returns a third CHECK
mentioning `block_type`, stop — the old constraint survived and new block types
will be rejected at insert time.

Then apply `267_essay_brainstorm_canvas_position.sql` and confirm the canvas
columns:

```sql
select column_name, data_type, numeric_precision, numeric_scale, is_nullable
  from information_schema.columns
 where table_schema = 'public'
   and table_name = 'essay_brainstorm_blocks'
   and column_name in ('canvas_x', 'canvas_y')
 order by column_name;
-- expect two rows: numeric | 10 | 2 | YES
```

The earlier `pg_constraint` query should now also return
`essay_brainstorm_blocks_canvas_position_check` as
`CHECK (((canvas_x IS NULL) = (canvas_y IS NULL)))`. There must be no CHECK
bounding the coordinate values themselves — canvas size, pan and zoom are
frontend concerns and are deliberately unconstrained in the database.

## 2. Prove the RLS / privilege posture

`essay_brainstorm_blocks` is service-role-only: RLS enabled, zero client
policies, no anon/authenticated table privileges (migration 195 §4 contract).

```sql
select c.relrowsecurity as rls_enabled
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relname = 'essay_brainstorm_blocks';
-- expect: t

select count(*) from pg_policies
 where schemaname = 'public' and tablename = 'essay_brainstorm_blocks';
-- expect: 0

select
  has_table_privilege('anon',          'public.essay_brainstorm_blocks', 'SELECT') as anon_select,
  has_table_privilege('authenticated', 'public.essay_brainstorm_blocks', 'SELECT') as auth_select,
  has_table_privilege('authenticated', 'public.essay_brainstorm_blocks', 'INSERT') as auth_insert,
  has_table_privilege('service_role',  'public.essay_brainstorm_blocks', 'INSERT') as svc_insert;
-- expect: f | f | f | t
```

Then confirm the same from outside the database: a direct PostgREST read with
an aspirant's anon-key JWT must return no rows / be refused.

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  "$SUPABASE_URL/rest/v1/essay_brainstorm_blocks?select=id" \
  -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $ASPIRANT_A_JWT"
```

A 200 carrying rows is a FAIL. Studio's SQL editor bypasses RLS for the
dashboard role, so a Studio read proves nothing here — use the HTTP path.

Migration 267 adds columns but no grants, on the expectation that 266's
TABLE-level privileges already cover columns added later. Confirm that rather
than assuming it — a column-level grant hiding anywhere would break it:

```sql
select grantee, privilege_type, column_name
  from information_schema.column_privileges
 where table_schema = 'public' and table_name = 'essay_brainstorm_blocks'
   and grantee in ('anon', 'authenticated');
-- expect: zero rows
```

## 3. Exercise the aspirant CRUD path

As aspirant A, against the deployed API:

1. `POST /api/essay-brainstorm-blocks` with a Spine block
   (`block_type=thesis`, no `lens`) — expect 200 and `lens: null`.
2. `POST /api/essay-brainstorm-blocks` with each Idea Canvas resource type
   (`vocab_term`, `book_reference`, `stat_to_verify`) and a `lens` — expect 200.
   This is the step that fails if migration 266's constraint swap did not land.
3. `GET /api/essay-brainstorm-blocks?theme_id=…&lens=…&block_type=…` — confirm
   each filter and their combination narrow the result set.
4. `PATCH /api/essay-brainstorm-blocks/{id}` — edit `block_text`; send
   `{"lens": null}` and confirm the lens clears without touching other fields.
5. `DELETE /api/essay-brainstorm-blocks/{id}` — confirm the row is gone on a
   follow-up `GET /api/essay-brainstorm-blocks/{id}` (404).

Record the block IDs and the theme ID used.

## 3b. Exercise the canvas position

Still as aspirant A:

1. `POST` a block with `canvas_x` / `canvas_y` — expect them echoed back on the
   response and on a follow-up `GET`, at full stored precision (send something
   like `190.5` / `250.25`, not round numbers, so a silent rounding to integer
   would show).
2. `POST` a block with no position at all — expect `canvas_x: null`,
   `canvas_y: null`. Unplaced is a permanently valid state; if this 4xxs, the
   columns were made required somewhere they should not have been.
3. `POST` a negative coordinate (e.g. `canvas_x: -42.75`) — expect success.
   Nothing clamps a drag in the mockup, so negative positions are real.
4. `PATCH` both axes together — expect the new position, and confirm
   `block_text` and `lens` are unchanged by the move.
5. `PATCH` **one** axis alone — expect **422**. A position is one point; a row
   with x but no y cannot be rendered.
6. `PATCH` `{"canvas_x": null, "canvas_y": null}` — expect the position cleared
   back to unplaced, with the rest of the block intact (the same
   explicit-null-clears semantic `lens` already has).
7. `PATCH` some other field without mentioning the canvas keys — expect the
   position preserved.
8. Try to write a half-placed row directly through the service-role client
   (`update essay_brainstorm_blocks set canvas_x = 1 where id = ...`) — expect
   Postgres to reject it with
   `essay_brainstorm_blocks_canvas_position_check`. This proves the invariant
   holds below the API, not just in it.

## 4. Prove cross-aspirant isolation on the deployed API

Using aspirant B's token against a block ID created by aspirant A:

- `GET /api/essay-brainstorm-blocks/{a_block_id}` — expect **404**.
- `PATCH /api/essay-brainstorm-blocks/{a_block_id}` — expect **404**, and
  re-read as A to confirm the text is unchanged.
- `DELETE /api/essay-brainstorm-blocks/{a_block_id}` — expect **404**, and
  re-read as A to confirm the row still exists.
- `GET /api/essay-brainstorm-blocks` — A's blocks must not appear.
- `PATCH` a canvas position onto `{a_block_id}` — expect **404**, and confirm
  as A that the block has not moved.

403 instead of 404 is a FAIL: it confirms the block exists to a caller who does
not own it.

## 5. Validate the shared essay-PYQ-tag read

- `GET /api/essay-pyq-tags?theme_id=<theme>` as aspirant A and as aspirant B —
  both must return the **same** rows (shared reference data, no ownership
  scoping).
- Confirm the verified-only invariant holds conjunctively. The 100 imported
  essay PYQ tags were forced to `reviewer_status='pending'` by the CMS
  bulk-import trust gate, so until they are promoted this endpoint correctly
  returns `{"items": [], "count": 0}`. An empty response here is a PASS, not a
  defect — record it as such.
- After promoting one tag to `verified` through the admin CMS, re-read and
  confirm it appears **only** when its `pyq_questions` row is
  `reviewer_status='verified'` and its `pyq_papers` row is
  `trust_status='verified'`. Flip either parent away from verified and confirm
  the tag disappears.

## 6. Record evidence

Write one evidence record under `docs/operator-validation/evidence/` covering
steps 1–5 (3b included) with the environment, timestamps, request/response excerpts, and the
account IDs used. Then update the gate in `registry.json`, regenerate the index,
and run:

```bash
node --test scripts/__tests__/operator-validation.test.js
node scripts/operator-validation.js --check
```
