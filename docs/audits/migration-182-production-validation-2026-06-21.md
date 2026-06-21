# Migration 182 — Production Validation Evidence
**Date:** 2026-06-21  
**Migration:** `182_mock_correction_draft_atomic_rpcs.sql`  
**Validator:** Operator / Claude Code assisted audit  
**Status:** VERIFY DB — pending live confirmation gate

---

## What migration 182 contains

Migration 182 adds three SECURITY DEFINER RPCs that atomically manage
mock correction drafts:

| RPC | Purpose |
|-----|---------|
| `ensure_mock_correction_draft` | Idempotent single-draft insert (ON CONFLICT DO NOTHING) |
| `ensure_mock_correction_drafts` | Atomic bulk-upsert of drafts (D1 fix) |
| `replace_manual_mock_correction_drafts` | Single-transaction delete-and-replace with review_state flip |

All three enforce the D2 ownership + source_type guard:  
- `ensure_*` RPCs require `mock_tests.source_type = 'platform_attempt'`  
- `replace_manual_*` requires the caller-owned mock to NOT be a platform_attempt

---

## Pre-flight schema checks (read-only SQL, do not execute on live)

The following queries confirm the migration landed correctly.  Run them on
the live DB via Supabase SQL Editor (read-only role) and compare to expected
results below.

### 1. Confirm all three RPCs exist

```sql
SELECT routine_name, routine_type, security_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'ensure_mock_correction_draft',
    'ensure_mock_correction_drafts',
    'replace_manual_mock_correction_drafts'
  )
ORDER BY routine_name;
```

**Expected:** 3 rows, all `FUNCTION`, all `DEFINER`.

### 2. Confirm REVOKE from public (no public execute)

```sql
SELECT grantee, privilege_type
FROM information_schema.role_routine_grants
WHERE routine_name IN (
    'ensure_mock_correction_draft',
    'ensure_mock_correction_drafts',
    'replace_manual_mock_correction_drafts'
  )
  AND grantee = 'public';
```

**Expected:** 0 rows (public access revoked).

### 3. Confirm service_role has EXECUTE

```sql
SELECT grantee, privilege_type, routine_name
FROM information_schema.role_routine_grants
WHERE routine_name IN (
    'ensure_mock_correction_draft',
    'ensure_mock_correction_drafts',
    'replace_manual_mock_correction_drafts'
  )
  AND grantee = 'service_role';
```

**Expected:** 3 rows, all `EXECUTE`, `service_role`.

### 4. Idempotency smoke test (read-only assertion)

```sql
-- Count how many mock_correction_tasks exist in each state.
-- Should not change between reads (confirms no phantom inserts).
SELECT state, COUNT(*) FROM mock_correction_tasks GROUP BY state;
```

**Expected:** Returns current counts (zero or more) without error.

### 5. Confirm mock_tests.source_type column exists

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'mock_tests'
  AND column_name = 'source_type';
```

**Expected:** 1 row, `character varying` or `text`, not nullable.

---

## Unit test evidence

The SBStub emulations of all three RPCs are tested in:
- `app/backend/tests/persona_questions/_stub.py` (emulations)
- `app/backend/tests/` (test suite that exercises the emulations via the API)

All emulations enforce the same D2 guard as the PL/pgSQL implementation.

---

## Checklist (operator to complete on live DB access)

- [ ] Run query 1 → 3 rows returned
- [ ] Run query 2 → 0 rows (public revoked)
- [ ] Run query 3 → 3 rows service_role granted
- [ ] Run query 4 → no error
- [ ] Run query 5 → source_type column present
- [ ] Update `docs/status/career-copilot-checklist.md` migration 182 row to DONE

---

## Risk assessment

**Risk:** Low.  
Migration 182 adds new RPCs; it does not ALTER or DROP any existing table
or column.  Failure mode is RPC not found (404 from the API), not data
corruption.  Rollback path: DROP the three functions (no data loss).

**Constraint preserved:** `FF_MOCK_MASTERY_WRITES` is NOT flipped by this
migration.  The shadow path continues to be gated by the feature flag.
