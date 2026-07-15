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
| Started at (UTC) | `<timestamp>` |
| Completed at (UTC) | `<timestamp>` |

## Preconditions

State the exact data, roles, feature flags, migrations, and deployment state required by the runbook. Record identifiers only where they are needed to reproduce the result.

## Execution record

| Step | Expected | Actual | Result | Artifact |
|---|---|---|---|---|
| `<runbook step>` | `<acceptance condition>` | `<observed result>` | `PASS / FAIL / BLOCKED` | `<redacted response, screenshot, query output, or log reference>` |

## Findings

Record defects with severity, affected contract, and required correction. Do not turn findings into a second delivery checklist; link issues or PRs where implementation work is tracked.

## Disposition

State the evidence-backed gate result and the exact next action. A pass must identify every acceptance condition that was proven. A partial pass or failure must identify the remaining blocker.

## Registry update

- Registry gate ID: `<id>`
- New status: `<status>`
- Next review date: `<YYYY-MM-DD or terminal>`
- Added evidence path: `<this file>`
