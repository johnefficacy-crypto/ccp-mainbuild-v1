# Operator validation evidence — v1 P1/P2/P4 reconciliation

## Record

| Field | Value |
|---|---|
| Registry gates | `v1-p1-migration-chain`, `v1-p2-rpc-rls-live-proof`, `v1-p4-migration-204-snapshot-review` |
| Result | P1 `operator_pending`; P2 `partial_pass`; P4 `partial_pass` |
| Recorded at | 2026-07-15 |
| Basis | Repository release tracker/runbook, PR #807, and operator-provided June 30 execution history |

This is a reconciliation of preserved evidence. It does not claim that missing staging/production or real-JWT steps were performed.

## P1 — not performed

Missing evidence:

- staging and production `schema_migrations` heads;
- both heads matching the intended repository migration set;
- no holes or divergence;
- application through the approved migration runner rather than individual SQL execution;
- post-application checkpoints.

Applying selected migrations does not close P1.

## P2 — partially performed

Checks performed for selected RPCs/tables included `SECURITY DEFINER`, fixed `search_path`, denial for `anon/authenticated`, service-role access, and selected direct-grant/RLS inspection.

Still required:

- run `scripts/v1_release_verification.sql`;
- complete the release-wide RPC grant audit;
- run RLS introspection on staging and production;
- use a real normal-user JWT and preserve only-allowed-row output;
- use a real admin JWT and preserve draft/admin-row output.

## P4 — core staging validation performed

The June 30 staging history records:

- migration 204 present in the migration ledger;
- `cms_review_exam_topic_snapshot` was `SECURITY DEFINER` with `search_path = public`;
- `anon=false`, `authenticated=false`, `service_role=true` execution matrix;
- seven draft snapshots computed for exam `22222222-2222-2222-2222-222222222222` and phase `44444444-4444-4444-4444-444444444441`;
- snapshot `55e096bd-468d-4d0a-88c4-5c6c1dc8fbff` exercised through review, lock, and locked-to-reviewed behavior with notes;
- atomic audit rows and reviewer-note preservation observed.

Not durably proven in the available record:

- concurrency outcome;
- all negative direct-RPC cases from PR #807's operator checklist;
- a complete fresh rerun after P1.

## Defects and documentation corrections

| ID | Finding | Current disposition |
|---|---|---|
| `v1-p1-01` | Full chain reconciliation was previously susceptible to being inferred from individual migration checks. | Registry now states P1 `operator_pending`; no false closure. |
| `v1-p2-01` | Narrow grant checks were being conflated with release-wide verification. | Registry now states P2 `partial_pass` and lists the missing real-JWT/release script proof. |
| `v1-p4-01` | The June 30 P4 run had no durable audit snapshot and tracker status remained stale. | This evidence record and registry row preserve the core run as `partial_pass`. |
| `v1-p4-02` | Concurrency and all negative direct-RPC cases remain unpreserved. | Still open; requires a fresh captured run. |

## Disposition

```text
P1: OPERATOR PENDING — not performed
P2: PARTIAL PASS — selected checks only; release-wide real-JWT proof pending
P4: PARTIAL PASS — core staging lifecycle/grants/audit proven; edge-case and fresh-run proof pending
```
