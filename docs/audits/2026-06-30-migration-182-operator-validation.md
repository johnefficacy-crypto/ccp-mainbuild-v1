# Migration 182 — Operator Validation Record

**Migration file:** `app/supabase/migrations/182_mock_correction_draft_atomic_rpcs.sql`
**Status at time of record:** OPERATOR PENDING — this document must be completed with live DB evidence before migration 182 can be marked DONE.

Do NOT mark migration 182 complete from code inspection alone. Each item below requires a real query run against the target environment and the raw output pasted in.

---

## 1. Target Supabase environment

Run in the Supabase SQL editor or psql to capture the execution context:

```sql
select
  current_database() as database_name,
  current_user as executing_role,
  now() at time zone 'utc' as validation_utc;
```

Paste output:

```
<FILL IN: raw query output>
```

Also record:

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

Record actual output:

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
select *
from supabase_migrations.schema_migrations
where version::text = '182';
```

Paste output:

```
<FILL IN: raw query output>
```

Pass condition: exactly one row exists for version 182.

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
with targets(signature) as (
  values
    ('public.ensure_mock_correction_draft(uuid,uuid,text,text,text,jsonb)'),
    ('public.ensure_mock_correction_drafts(uuid,uuid,jsonb)'),
    ('public.replace_manual_mock_correction_drafts(uuid,uuid,jsonb)')
)
select
  t.signature,
  p.oid::regprocedure as resolved_function,
  pg_get_userbyid(p.proowner) as owner,
  p.prosecdef as security_definer,
  p.proconfig as function_config,
  pg_get_function_result(p.oid) as return_type
from targets t
left join pg_proc p
  on p.oid = to_regprocedure(t.signature)
order by t.signature;
```

Paste output:

```
<FILL IN: raw query output — must show all three rows with non-null resolved_function>
```

Pass condition: all three functions resolve (`resolved_function` is not null) with the exact argument types listed above.

---

## 6. Owner, SECURITY DEFINER, and search_path

The above query in §5 covers `owner`, `security_definer`, and `function_config`. Record the owner here:

```
owner (all three functions): <FILL IN: record the actual owner; must be a trusted migration/runtime role>
```

Pass conditions (all enforced by the migration source):
- `security_definer = true` for all three functions
- `function_config` contains `search_path=public, pg_temp` for all three functions
- Owner is a trusted migration/runtime role (not anon, authenticated, or an untrusted role)

---

## 7. Effective EXECUTE privilege for anon, authenticated, and service_role

Run the grantee query:

```sql
with targets(signature) as (
  values
    ('public.ensure_mock_correction_draft(uuid,uuid,text,text,text,jsonb)'),
    ('public.ensure_mock_correction_drafts(uuid,uuid,jsonb)'),
    ('public.replace_manual_mock_correction_drafts(uuid,uuid,jsonb)')
),
roles(role_name) as (
  values ('anon'), ('authenticated'), ('service_role')
)
select
  t.signature,
  r.role_name,
  has_function_privilege(r.role_name, t.signature, 'EXECUTE') as can_execute
from targets t
cross join roles r
order by t.signature, r.role_name;
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

Migration 182 was applied previously. Do NOT re-execute the migration file. Perform only post-apply metadata and rollback-safe functional checks.

### 8a. Find a disposable platform_attempt mock for smoke-testing

```sql
select id, user_id, source_type
from public.mock_tests
where source_type = 'platform_attempt'
order by created_at desc
limit 5;
```

Paste output (choose one `id` as `<DISPOSABLE_PLATFORM_MOCK_UUID>` below):

```
<FILL IN: raw query output>
```

### 8b. Ownership / source-type guard smoke-test

Replace `<DISPOSABLE_PLATFORM_MOCK_UUID>` with the `id` selected above, then run the entire block:

```sql
begin;

do $audit$
declare
  v_mock_id    uuid := '<DISPOSABLE_PLATFORM_MOCK_UUID>';
  v_wrong_user uuid := gen_random_uuid();
  v_before     bigint;
  v_after      bigint;
begin
  select count(*)
  into v_before
  from public.mock_correction_tasks
  where mock_test_id = v_mock_id;

  -- Test 1: singular RPC rejects wrong user (D2 ownership guard)
  begin
    perform public.ensure_mock_correction_draft(
      v_mock_id,
      v_wrong_user,
      'operator_test',
      null,
      'Operator validation',
      '[]'::jsonb
    );
    raise exception 'AUDIT FAIL: singular RPC accepted wrong user';
  exception
    when no_data_found then
      raise notice 'AUDIT PASS: singular RPC rejected wrong user';
  end;

  -- Test 2: plural RPC rejects wrong user (D2 ownership guard)
  begin
    perform public.ensure_mock_correction_drafts(
      v_mock_id,
      v_wrong_user,
      '[]'::jsonb
    );
    raise exception 'AUDIT FAIL: plural RPC accepted wrong user';
  exception
    when no_data_found then
      raise notice 'AUDIT PASS: plural RPC rejected wrong user';
  end;

  -- Test 3: manual replacement rejects platform_attempt source_type
  begin
    perform public.replace_manual_mock_correction_drafts(
      v_mock_id,
      (select user_id from public.mock_tests where id = v_mock_id),
      '[]'::jsonb
    );
    raise exception 'AUDIT FAIL: manual replacement accepted platform_attempt';
  exception
    when raise_exception then
      raise notice 'AUDIT PASS: manual replacement rejected platform_attempt';
  end;

  -- Confirm no rows were inserted or deleted
  select count(*)
  into v_after
  from public.mock_correction_tasks
  where mock_test_id = v_mock_id;

  if v_before <> v_after then
    raise exception
      'AUDIT FAIL: row count changed from % to %',
      v_before,
      v_after;
  end if;

  raise notice
    'AUDIT PASS: no mutation; before=%, after=%',
    v_before,
    v_after;
end
$audit$;

rollback;
```

Paste the complete output (notices + final statement):

```
<FILL IN: must show three AUDIT PASS notices and end with "ROLLBACK">
```

Pass conditions:
- `AUDIT PASS: singular RPC rejected wrong user`
- `AUDIT PASS: plural RPC rejected wrong user`
- `AUDIT PASS: manual replacement rejected platform_attempt`
- `AUDIT PASS: no mutation; before=N, after=N`
- Final statement: `ROLLBACK`

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
| 8. Smoke-test: three guards fire, no mutation, ROLLBACK | ☐ | |

Operator sign-off:

```
Signed:    <FILL IN: operator identity>
Date/time: <FILL IN: UTC>
```

Once all items are ☑ and signed, update `docs/status/career-copilot-checklist.md`:
- Row "Correction idempotency guard (23505) / atomic persistence": `CODE-FIXED, MIGRATION VALIDATION PENDING` → `OPERATOR VALIDATED — 2026-06-30`
- `FF_MOCK_MASTERY_WRITES=live` blocked-gate item (b): remove migration 182 from unresolved blockers (scheduler, PR-6, PR-7, and canary blockers remain)
