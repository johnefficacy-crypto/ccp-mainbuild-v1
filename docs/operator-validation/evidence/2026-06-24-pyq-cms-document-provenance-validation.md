# Operator validation evidence — PYQ CMS document/provenance staging validation

## Record

| Field | Value |
|---|---|
| Gate ID | `pyq-cms-provenance-staging-validation` |
| Result | `passed` |
| Environment | staging |
| Deployment SHA | `01240c4ca9617f9837170e5c28b327169ce7940a` as recorded by PR #756 |
| Database migration range | 183–190 |
| Completed at | 2026-06-24; exact UTC time was not preserved |
| Source | PR #756 body, merge/checklist commit `399896fc3bf2450c3f1f7d53ac9b742f07081796`, and operator-provided completion record |

No access tokens, cookies, authorization headers, secrets, or disposable fixture identifiers are retained here.

## Proven acceptance conditions

- Migrations 183–190 were applied and synchronized.
- Provenance RPC execution was restricted to `service_role`.
- `idx_document_assets_scope_kind_status` was present.
- PDF upload and complete-upload succeeded.
- A document was linked through the atomic RPC; link audit and `source_document_id` were verified.
- Paper review moved `pending → verified` atomically.
- Generic provenance PATCH returned `422 provenance_locked`.
- `set-provenance` demoted `verified → pending` and wrote the audit row atomically.
- Archiving the document caused signed-PDF access to return `403 source_document_id_bad_status`.
- Frontend **Replace Doc** used `set-provenance` and refreshed `Verified → Pending`.
- Disposable paper, document, processing, Storage, and audit fixtures were removed.
- The deployed staging path was exercised against the recorded commit.
- Graphify was refreshed after the implementation series.

## Defects found and fixed

| ID | Defect | Fix |
|---|---|---|
| `pyq-prov-01` | RPC grants were broader than service role. | Migration 190 explicitly revoked `PUBLIC`, `anon`, and `authenticated` execution. |
| `pyq-prov-02` | Document validation could race between Python precheck and mutation. | Migration 189 locks and rechecks document invariants in the transaction. |
| `pyq-prov-03` | Provenance/link update and audit insertion were separate writes. | Migration 188 made mutation and audit atomic. |

## Evidence limitations

The exact Vercel-specific SHA and exact UTC start/end timestamps were not preserved separately. The PR records staging validation at `01240c4…`; this reconstruction does not invent missing timestamps or credentials.

## Disposition

**PASSED.** This is a closed historical gate. A new gate is required only if the acceptance contract materially changes.
