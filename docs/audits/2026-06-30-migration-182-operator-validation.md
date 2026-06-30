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
| Deployed application SHA | PENDING | Must be copied from the deployment record for this environment. |
| Migration file SHA | PASS | Full SHA-256 recorded above. |
| Migration ledger | PASS | Exactly one version-182 row. |
| RPC metadata and privileges | PASS | Signatures, ownership, configuration, overload count, and privilege comparisons passed. |
| Rollback-safe functional test | PASS | Guard checks held and no row persisted. |

## Final status rule

Do not change the shared checklist to `OPERATOR VALIDATED` until the following are recorded:

1. Supabase project ref, URL, region, and environment label.
2. Operator identity.
3. Exact deployed application SHA.
4. Operator signature and UTC sign-off time.

After those fields are supplied, migration 182 may be removed from the unresolved live blockers. Scheduler, repeat validation, shadow-window, staging, and canary gates remain independently open.
