# Migration 182 — Operator Validation Record

**Status:** OPERATOR VALIDATED — 2026-06-30

## Target environment

```text
Project ref:       ylfnbxyqiyiqvxtthhum
Project URL:       https://ylfnbxyqiyiqvxtthhum.supabase.co
Database:          PostgreSQL 17.6
Region:            Southeast Asia
Cloud region:      ap-southeast-1 (Singapore)
Executing DB role: postgres
```

## Reviewed deployment

```text
Deployed application SHA: b7ca717fc156a3c988197673b3a6a1b291616b43
Canonical Git blob SHA-256:
39e7c12c1bec50cb634cb39c2449ddf9bfa113f97e83d4a52d8c6923f7c18819

Operator Windows checkout SHA-256:
3BADF456FC7914468BC3A004FA01DD51E8D0C02C48B7F3D403B1805F4DE22B71

Checkout line-ending mode:
index=LF, working-tree=CRLF, core.autocrlf=true
```

## Validation window

```text
Started:   2026-06-30T08:15:41.311640Z
Completed: 2026-06-30T08:21:33.937902Z
```

## Results

| Check | Result |
|---|---|
| Migration ledger | PASS — exactly one version-182 row |
| Expected functions and return types | PASS |
| Extra overload check | PASS — exactly three definitions |
| Ownership and runtime configuration | PASS |
| Role/function access comparison | PASS — 9/9 |
| Wrong-user guards | PASS |
| Platform-attempt manual-replacement guard | PASS |
| Rollback-safe no-mutation test | PASS |
| Post-rollback correction-row count | PASS — zero |

Smoke-test record:

```text
mock_test_id: a41fa7dc-3e50-4f0b-8370-72081af83738
rows before: 0
SQL Editor result: Success. No rows returned
rows after rollback: 0
```

## Operator sign-off

Only the minimum accountable identity is recorded. Unrelated profile data was intentionally excluded.

```text
Signed by: PRASHANT WAGHMARE
Signed at: 2026-06-30T08:21:33.937902Z
```

## Final result

All migration-182 operator checks and sign-off fields are complete. Migration 182 may be removed from the unresolved live blockers. Scheduler, repeat validation, shadow-window, staging, and canary gates remain independently open.
