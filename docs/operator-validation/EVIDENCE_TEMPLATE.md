# Operator validation evidence — <gate title>

Do not store access tokens, cookies, API keys, authorization headers, passwords, or unnecessary personal data.

## Record

| Field | Value |
|---|---|
| Gate ID | `<registry gate id>` |
| Result | `passed / partial_pass / failed / cancelled` |
| Environment | `<production / staging / local-live-stack>` |
| Frontend deployment SHA | `<sha or n/a>` |
| Backend deployment SHA | `<sha or n/a>` |
| Database migration maximum | `<version or n/a>` |
| Operator | `<GitHub handle or approved role>` |
| Started at (UTC) | `<YYYY-MM-DDTHH:mm:ssZ>` |
| Completed at (UTC) | `<YYYY-MM-DDTHH:mm:ssZ>` |

For a historical reconstruction, use `unknown / not preserved` for any field that was not durably recorded (deployment SHAs, environment, migration head, exact start/completion timestamps, operator, JWT identities). Never invent these values.

## Preconditions

State the exact data, roles, feature flags, migrations, and deployment state required by the runbook. Record identifiers only where needed to reproduce the result.

## Execution record

| Step | Expected | Actual | Result | Artifact |
|---|---|---|---|---|
| `<runbook step>` | `<acceptance condition>` | `<observed result>` | `PASS / FAIL / BLOCKED` | `<redacted response, screenshot, query output, or log reference>` |

## Defects found

| Defect ID | Severity | Affected contract | Finding | Tracking PR/issue |
|---|---|---|---|---|
| `<stable-kebab-id>` | `<P0/P1/P2/P3>` | `<contract>` | `<finding>` | `<reference>` |

## Defects fixed

| Defect ID | Remediation | Code/data reference | Revalidated? |
|---|---|---|---|
| `<same id from defects found>` | `<fix>` | `<PR/commit/migration>` | `yes / no` |

A code-fixed defect remains unvalidated until the deployed path is rerun.

## Disposition

State the evidence-backed gate result and exact next action. A pass must identify every proven acceptance condition. A partial pass or failure must identify remaining blockers.

## Registry update

- Registry gate ID: `<id>`
- New status: `<status>`
- Next review timestamp: `<YYYY-MM-DDTHH:mm:ssZ or terminal>`
- Defect IDs added/fixed: `<ids or none>`
- Added evidence path: `<this file>`
