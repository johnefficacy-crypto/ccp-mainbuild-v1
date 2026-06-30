# Migration 182 — Operator Validation Record

**Migration file:** `app/supabase/migrations/182_mock_correction_draft_atomic_rpcs.sql`

**Status:** LIVE DATABASE CHECKS PASSED; FINAL METADATA SIGN-OFF PENDING

## Validation summary

Validation ran from `2026-06-30T08:15:41.311640Z` through `2026-06-30T08:21:33.937902Z` against PostgreSQL 17.6. The database and executing role both reported `postgres`.

Migration file SHA-256:

```text
3BADF456FC7914468BC3A004FA01DD51E8D0C02C48B7F3D403B1805F4DE22B71
```

## Results

| Check | Result | Evidence |
|---|---|---|
| Migration ledger | PASS | Exactly one row exists for version 182; name is `mock_correction_draft_atomic_rpcs`. |
| RPC signatures | PASS | All three expected signatures and return types resolved. |
| Unexpected overloads | PASS | Count was exactly 3. |
| Function ownership | PASS | All three functions are owned by `postgres`. |
| Security configuration | PASS | All three functions use the expected definer mode and pinned search path. |
| Effective privileges | PASS | All nine role/function comparisons matched the migration contract. |
| Ownership guards | PASS | Both generated-path functions rejected a deliberately wrong user. |
| Source-type guard | PASS | Manual replacement rejected a platform attempt. |
| Rollback safety | PASS | The test transaction completed successfully and was rolled back. |
| Post-rollback mutation check | PASS | Correction row count remained 0. |

Selected disposable record for the rollback-safe test:

```text
mock_test_id: a41fa7dc-3e50-4f0b-8370-72081af83738
source_type: platform_attempt
rows before test: 0
rows after rollback: 0
```

Supabase SQL Editor result:

```text
Success. No rows returned
```

The test block was fail-closed: any forbidden accepted call, unexpected guard result, or before/after state difference would have raised an uncaught error.

## Sign-off checklist

| Item | Status | Notes |
|---|---|---|
| Target database context | PASS | Database, role, version, and UTC start captured. |
| Target project identity | PENDING | Project ref, project URL, region, and staging/production label not supplied. |
| Operator identity | PENDING | Name or accountable operator identity not supplied. |
| Deployed application SHA | NOT APPLICABLE TO MIGRATION 182 DB VALIDATION | Migration 182 is a database migration whose live state is proven by the ledger row, stored migration statement, function metadata, privileges, and functional checks. Application deploy SHA is not required to prove this already-applied database state. |
| Migration file SHA | PASS | Full SHA-256 recorded above. |
| Migration ledger | PASS | Exactly one version-182 row. |
| RPC metadata and privileges | PASS | Signatures, ownership, configuration, overload count, and privilege comparisons passed. |
| Rollback-safe functional test | PASS | Guard checks held and no row persisted. |

## Final status rule

The remaining fields required before changing the shared checklist to `OPERATOR VALIDATED` are:

1. Supabase project ref, project URL, region, and environment label.
2. Operator identity.
3. Operator signature and UTC sign-off time.

A deployed application SHA is tracked separately for application/staging validation and is not a blocker for migration 182 database validation.

After the remaining target/operator fields are recorded, migration 182 may be removed from the unresolved live blockers. Scheduler, repeat validation, shadow-window, staging, and canary gates remain independently open.
