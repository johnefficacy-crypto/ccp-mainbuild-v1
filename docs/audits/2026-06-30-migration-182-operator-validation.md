# Migration 182 — Operator Validation Record

**Migration file:** `app/supabase/migrations/182_mock_correction_draft_atomic_rpcs.sql`
**Status at time of record:** OPERATOR PENDING — this document must be completed with live DB evidence before migration 182 can be marked DONE.

Do NOT mark migration 182 complete from code inspection alone. Each item below requires a real query run against the target environment and the raw output pasted in.

---

## 1. Target Supabase environment

```
Project ref:   <FILL IN: e.g. abcdefghij>
Project URL:   <FILL IN: e.g. https://abcdefghij.supabase.co>
Region:        <FILL IN>
Validation ran by: <FILL IN: operator identity>
```

---

## 2. Reviewed / deployed SHA

The migration was applied at this commit SHA:

```
Deployed application SHA: <FILL IN: git rev from Render deploy log or `git log --oneline -1` at deploy time>
```

Migration file SHA256 (repo side — verify matches deployed file):

```
sha256sum app/supabase/migrations/182_mock_correction_draft_atomic_rpcs.sql
```

Expected output will differ if the file was modified after the original commit. Record actual output:

```
<FILL IN: actual sha256sum output>
```

---

## 3. UTC validation time

```
Validation started (UTC): <FILL IN: e.g. 2026-06-30T14:00:00Z>
Validation completed (UTC): <FILL IN>
```

---

## 4. Migration 182 history row

Run in the Supabase SQL editor or psql:

```sql
SELECT version, name, statements, execution_time
FROM supabase_migrations.schema_migrations
WHERE version = '182'
   OR name ILIKE '%182%'
ORDER BY version;
```

Paste output:

```
<FILL IN: raw query output>
```

Pass condition: a single row with `version = '182'` (or equivalent slot), `name` matching `182_mock_correction_draft_atomic_rpcs`, and a non-null `execution_time`.

---

## 5. Exact three RPC signatures

Expected signatures from the migration source:

| Function | Argument types | Return type |
|---|---|---|
| `ensure_mock_correction_draft` | `uuid, uuid, text, text, text, jsonb` | `mock_correction_tasks` |
| `ensure_mock_correction_drafts` | `uuid, uuid, jsonb` | `SETOF mock_correction_tasks` |
| `replace_manual_mock_correction_drafts` | `uuid, uuid, jsonb` | `SETOF mock_correction_tasks` |

Run against the live DB to confirm:

```sql
SELECT
    p.proname                                    AS function_name,
    pg_catalog.pg_get_function_arguments(p.oid)  AS argument_types,
    pg_catalog.pg_get_function_result(p.oid)     AS return_type,
    p.prosecdef                                  AS security_definer,
    p.proowner::regrole::text                    AS owner,
    p.proconfig                                  AS config_overrides
FROM pg_catalog.pg_proc p
JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proname IN (
      'ensure_mock_correction_draft',
      'ensure_mock_correction_drafts',
      'replace_manual_mock_correction_drafts'
  )
ORDER BY p.proname;
```

Paste output:

```
<FILL IN: raw query output — must show all three rows>
```

Pass condition: all three functions present with the exact argument types listed above.

---

## 6. Owner, SECURITY DEFINER, and search_path

Expected (from migration source):
- Owner: `postgres` (migration runner; Supabase default)
- `prosecdef = true` for all three functions
- `search_path = public, pg_temp` for all three functions

The query in §5 above (`proowner`, `prosecdef`, `proconfig`) covers this. Additionally confirm `search_path` is pinned:

```sql
SELECT proname, proconfig
FROM pg_proc
WHERE proname IN (
    'ensure_mock_correction_draft',
    'ensure_mock_correction_drafts',
    'replace_manual_mock_correction_drafts'
)
AND pronamespace = 'public'::regnamespace;
```

Paste output:

```
<FILL IN: raw query output>
```

Pass condition:
- `prosecdef = true` for all three (confirmed in §5 output)
- `proconfig` contains `search_path=public, pg_temp` for all three

---

## 7. Effective EXECUTE privilege for anon, authenticated, and service_role

Run the grantee query:

```sql
SELECT
    p.proname                                               AS function_name,
    pg_catalog.pg_get_function_arguments(p.oid)            AS args,
    r.rolname                                              AS grantee,
    has_function_privilege(r.oid, p.oid, 'EXECUTE')        AS can_execute
FROM pg_catalog.pg_proc p
JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
CROSS JOIN (
    SELECT oid, rolname FROM pg_roles
    WHERE rolname IN ('anon', 'authenticated', 'service_role')
) r
WHERE n.nspname = 'public'
  AND p.proname IN (
      'ensure_mock_correction_draft',
      'ensure_mock_correction_drafts',
      'replace_manual_mock_correction_drafts'
  )
ORDER BY p.proname, r.rolname;
```

Paste output:

```
<FILL IN: raw query output — 9 rows: 3 functions × 3 roles>
```

Expected result matrix:

| Function | anon | authenticated | service_role |
|---|---|---|---|
| `ensure_mock_correction_draft` | false | false | true |
| `ensure_mock_correction_drafts` | false | false | true |
| `replace_manual_mock_correction_drafts` | false | false | true |

Pass condition: `can_execute = false` for `anon` and `authenticated` on all three functions; `can_execute = true` for `service_role` on all three.

---

## 8. Rollback-safe smoke-test — no mutation

Run a `BEGIN` / `ROLLBACK` dry-run to confirm the migration SQL executes without error and leaves no permanent change. Use a read-only call wrapped in a transaction that you roll back.

### 8a. BEGIN / ROLLBACK dry-run of the migration block (if not yet applied)

If the migration has not yet been applied to this environment, run:

```sql
BEGIN;

-- Paste the full contents of 182_mock_correction_draft_atomic_rpcs.sql here,
-- or run: \i app/supabase/migrations/182_mock_correction_draft_atomic_rpcs.sql

ROLLBACK;
```

Expected output: `ROLLBACK` with no errors. Paste:

```
<FILL IN: psql output — should end with "ROLLBACK">
```

### 8b. Ownership / source-type guard smoke-test (post-apply, read-only safe)

After the migration is applied, verify the ownership guard rejects an invalid call without mutating any data:

```sql
-- This SHOULD raise 'platform_attempt mock not found for user' and change nothing.
SELECT public.ensure_mock_correction_drafts(
    '00000000-0000-0000-0000-000000000000'::uuid,   -- nonexistent mock_test_id
    '00000000-0000-0000-0000-000000000000'::uuid,   -- nonexistent user_id
    '[{"category":"conceptual","title":"test","source_questions":[]}]'::jsonb
);
```

Expected: raises `no_data_found` error. Paste actual output:

```
<FILL IN: error output — must show "platform_attempt mock not found for user" or equivalent>
```

Pass condition: the call raises an error (guard fired); no rows inserted into `mock_correction_tasks` for those UUIDs.

Confirm no mutation:

```sql
SELECT COUNT(*) FROM mock_correction_tasks
WHERE mock_test_id = '00000000-0000-0000-0000-000000000000'::uuid;
```

Expected: `0`. Paste:

```
<FILL IN: count output — must be 0>
```

---

## Sign-off

All 8 items above must be completed with real DB output before this record counts as durable evidence.

| Item | Pass? | Notes |
|---|---|---|
| 1. Target environment | ☐ | |
| 2. Deployed SHA | ☐ | |
| 3. UTC validation time | ☐ | |
| 4. Migration 182 history row | ☐ | |
| 5. Three RPC signatures confirmed | ☐ | |
| 6. SECURITY DEFINER + search_path confirmed | ☐ | |
| 7. Privilege matrix: anon/authenticated=false, service_role=true | ☐ | |
| 8. Smoke-test: no mutation, guard fires | ☐ | |

Operator sign-off:

```
Signed:    <FILL IN: operator identity>
Date/time: <FILL IN: UTC>
```

Once all items are ☑ and signed, update `docs/status/career-copilot-checklist.md` row "Correction idempotency guard (23505) / atomic persistence" from `CODE-FIXED, MIGRATION VALIDATION PENDING` to `OPERATOR VALIDATED (YYYY-MM-DD)` and update the `FF_MOCK_MASTERY_WRITES=live` blocked-gate item (b) from `OPERATOR PENDING — durable audit required` to `OPERATOR VALIDATED`.
