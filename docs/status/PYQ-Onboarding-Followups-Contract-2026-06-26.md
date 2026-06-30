# PYQ Onboarding Follow-ups Contract — OD-2 + OD-5

- Document type: bounded follow-up contract draft (records the scope implemented by PR #769; formal approval not yet recorded)
- Status: DRAFT — OPERATOR APPROVAL REQUIRED
- Date: 2026-06-26
- Parent gate: `docs/status/PYQ-Source-and-Paper-Onboarding-Gate-2026-06-25.md` (APPROVED). That gate locked OD-2 and OD-5 as **out of scope for v1 / separate future contract**. This document records the scope of that follow-up as implemented by PR #769.
- Effect: Once operator approval is recorded (approver, date, scope, conditions), OD-2 (source trust lifecycle) and OD-5 (inline PDF upload) will move from "deferred" to "in scope," bounded exactly as below. No new top-level surface; no change to the locked IA. The runtime is already merged; this document is the outstanding authorization artifact.

---

## Why this document exists

The parent gate deliberately deferred two decisions to keep v1 small:

- **OD-2** — "no source-trust promotion in v1; `pyq_sources` is an optional reusable grouping record; source lifecycle is a separate future contract."
- **OD-5** — "select-existing document only in v1; inline upload is a separately bounded follow-up."

The implementation was directed and has merged via PR #769. Under the repo's contract-first discipline, implementing a decision the parent gate locked as "out of scope" requires an approved contract first. This draft records the bounded scope, acceptance criteria, permissions, failure handling, and operator validation for each follow-up. It does not constitute that approval — a durable approval record (approver, date, approved scope, any conditions) is still required before this document's status can advance from DRAFT.

---

## Contract A — PYQ source trust lifecycle (supersedes OD-2 deferral)

**Decision (to lock):** add a dedicated source review action mirroring the existing PYQ *paper* review (the recommended ownership in the parent gate's Finding 7: "PYQ Workbench → source summary → verify/reject/re-queue source"). Source trust is **not** auto-derived from paper verification.

**Backend contract:**
- Endpoint `POST /api/admin/exam-intelligence-cms/pyq-sources/{source_id}/review`, body `{ status: "verified"|"rejected"|"pending", reason: ">=8 chars" }`.
- Permission: **`exam_intelligence.review`** (same gate as `review_pyq_paper`; super_admin bypass). NOT `exam_intelligence.cms`.
- Transition matrix (identical to paper review): `pending→verified`, `pending→rejected`, `verified→rejected`, `rejected→pending`. All other transitions (incl. no-ops) → 422.
- Backed by a transactional `SECURITY DEFINER` RPC (`cms_review_pyq_source`, migration 201 — renumbered from 193 due to duplicate migration conflict resolved via PR #782): `SET search_path=public`, `SELECT … FOR UPDATE` lock, expected-status concurrency guard, atomic audit INSERT + `trust_status` UPDATE, full REVOKE-from-PUBLIC/anon/authenticated + GRANT-to-service_role. `pyq_sources` has no `updated_at` (migration 032) — not set.
- Response `{ ok, audit_id, row }`. Errors: 404 missing / 422 invalid transition or reason / 409 concurrent modification.

**Frontend contract:** when a selected paper has a `pyq_source_id`, render a read-only source-trust summary (title/type/url + status chip) with `canReview`-gated Verify/Reject/Re-queue actions opening a reason modal (≥8 chars), calling the endpoint via `useApiAction`, then refetching. The "No reusable source record" advisory for source-less papers is unchanged.

**Acceptance criteria:** each allowed transition succeeds + writes audit + updates `trust_status`; disallowed/no-op → 422; reason <8 → 422; missing source → 404; permission enforced; concurrent-modification → 409 with no false audit. (24 backend tests + frontend gating tests in PR #769.)

**Out of scope (still deferred):** auto-derivation of source trust from paper verification; cross-paper source trust rollups; bulk source review.

---

## Contract B — Inline PDF upload in the onboarding modal (supersedes OD-5 deferral)

**Decision (to lock):** the AddPyqPaperModal evidence step gains an "upload new PDF" mode beside the existing select-existing picker. Select-existing remains the default. The object-storage upload boundary from the parent gate (§B.7) is unchanged — upload happens first, then the resulting `document_id` feeds onboarding.

**Frontend contract:**
- Reuse the Documents upload sequence: `POST documents/upload-url` → raw `PUT` bytes → `POST documents/complete-upload` → poll `GET documents/{id}` until terminal, scoped to `document_kind=pyq_paper` + `exam_id` from context.
- **Governance:** the two state-changing POSTs (`upload-url`, `complete-upload`) run inside `useApiAction`. The binary `PUT` uses raw `fetch` (raw bytes, not JSON — AGENTS.md #4). The status poll is a background read (exempt).
- **Failure handling (mandatory):** a terminal extraction failure (`result.ok === false`) MUST NOT set/link the `document_id` and MUST NOT present a linked-success state; it surfaces an error and leaves the evidence step unset (the backend provenance gate rejects failed documents, so a "success" UI for a guaranteed-reject input is forbidden). Binary-PUT failure surfaces an error and never reaches `complete-upload`.
- No backend change (reuses existing document endpoints). No inline retry surface — failures route the operator to retry or use the Documents tab.

**Acceptance criteria (PR #769 tests):** happy path links the new `document_id` and onboarding submits with it; binary-PUT failure → error, no link, no `complete-upload`; **terminal extraction failure → error, no link, onboarding submit carries no `document_id`.**

**Out of scope (still deferred):** inline extraction-retry UX; multi-file upload; non-PDF formats.

---

## Operator validation (required before operator-complete claim)

Same discipline as migration 191/192:

1. Apply migration **201** to staging (reconcile number vs deployed `schema_migrations`; renumbered from 193 via PR #782 duplicate migration hotfix).
2. Confirm `cms_review_pyq_source` exists; grant matrix (`anon`/`authenticated` denied, `service_role` allowed).
3. Behavioral: each transition; disallowed transition; concurrent-modification guard; audit + rollback.
4. Browser click-through: source Verify/Reject/Re-queue; inline upload happy path + a deliberately failing extraction (confirm it is NOT linked); cycle/phase labels readable.

Until recorded, the checklist row stays `CODE-FIXED, VALIDATION PENDING` / `OPERATOR PENDING`.

---

*Planning artifact. The runtime change lives in PRs #769 and #812; migrations 192 (onboarding RPC) and 201 (source review RPC) are OPERATOR VALIDATED on staging (2026-06-30; evidence in PR #806 body). Database validation does not retroactively constitute product-contract approval. This document requires an explicit operator approval record naming the approver, exact date, approved scope, and any retained conditions before its status can advance from DRAFT. Browser validation — Add PYQ paper flow, source Verify/Reject/Re-queue, inline upload (including deliberately failed extraction), cycle/phase label display — also remains pending.*
