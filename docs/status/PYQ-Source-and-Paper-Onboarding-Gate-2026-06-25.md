# PYQ Source and Paper Onboarding Gate — J2 Contract

- Document type: J2 sub-gate — contextual PYQ onboarding implementation contract
- Status: DRAFT — OPERATOR APPROVAL REQUIRED
- Date: 2026-06-25
- Parent track: `J2 — missing operational editors in Manage Exam` (`docs/status/career-copilot-checklist.md` row "J2"), specifically the **historical paper creation** sub-item.
- Effect: No PYQ-onboarding implementation PR may be dispatched until every `DERIVED — PROPOSED RESOLUTION` and `UNRESOLVED — OPERATOR DECISION REQUIRED` item below receives explicit operator approval and this document leaves DRAFT status.
- Repository scope of the PR that introduces this document: **documentation and checklist only**. No runtime, route, component, API, migration, or test change is authorized by this file.

---

## Purpose and non-goals

**Purpose**

- Convert the 25 June 2026 "PYQ Source and Paper Onboarding: Codebase Verification Report" into an operator-approvable, codebase-verified implementation contract, consistent with this repo's contract-first discipline (the same model used for the I6 cycle-setup gate and the I8 IA design-lock).
- Lock the contract for: the contextual onboarding flow inside the PYQ Workbench, the orchestration endpoint, the document picker that replaces manual UUID entry, the PYQ source trust lifecycle, and the `pyq_source_id` enforcement policy.
- Bound the write scope of the eventual implementation PR so it cannot drift into a new surface, a schema redesign, or a Raw CMS restoration.

**Non-goals**

- This document does NOT authorize any runtime, route, component, API, backend, migration, or automated-test change. It is a planning artifact.
- This document does NOT restore Raw CMS (`ExamIntelCms.jsx`) to primary navigation. Finding 1 is confirmed and the IA lock holds.
- This document does NOT authorize a new top-level surface. The onboarding flow is an embedded component inside the existing PYQ Workbench tab of Manage Exam.
- This document does NOT make `pyq_source_id` mandatory on `pyq_papers`, does NOT change the extraction pipeline, and does NOT redesign competition or coverage schema (those are J3).
- This document does NOT implement inline PDF capture as a single database transaction (see §6.7 for the locked atomicity boundary).

---

## Source authority and decision labels

| Label | Definition |
|---|---|
| SOURCE-LOCKED | Explicitly stated in a merged findings, design-lock, or APPROVED decision document. |
| CURRENT SOURCE FACT | Current local source code or migration behavior observed during this revision; not automatically a product rule. |
| DECISION TO LOCK | A decision this artifact proposes to lock once approved. |
| DERIVED — PROPOSED RESOLUTION | A specific proposed answer to an open question; requires operator yes/no approval before implementation begins. |
| UNRESOLVED — OPERATOR DECISION REQUIRED | Source material does not define enough to decide safely; no proposed resolution is offered without operator input. |

**Authority discipline:** code evidence alone is not a product decision. Every `CURRENT SOURCE FACT` below was re-verified against the working tree at the head of branch `claude/pyq-onboarding-workflow-gaps-gnhnuh`.

---

## Locked architecture recap (IA compliance)

| Rule | Authority | Source |
|---|---|---|
| One visible exam-operation destination: Exam Management → Manage Exam → More → Advanced Repair. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §1.1 |
| No new top-level destination unless it removes at least two existing ones. Embedded components, drill-in pages, overflow actions, and backend endpoints are NOT surfaces. | SOURCE-LOCKED | Design-Lock §1.2; `AGENTS.md` §18 |
| Advanced Repair (`ExamIntelCms.jsx`) is retained as a permission-gated recovery surface, reached only via Manage Exam → More → Advanced Repair. Routine creation must move into contextual workflows. | SOURCE-LOCKED | Design-Lock §3.2, §9 |
| PYQ corpus readiness is exam-wide; `pyq_papers.exam_cycle_id` is provenance, not a corpus filter. | SOURCE-LOCKED | `docs/status/Exam-Cycle-Setup-D10-PYQ-Readiness-Scope-Decision-2026-06-23.md` |
| Required exam evidence (incl. minimum verified PYQ paper per active written phase for `core`) derives from `management_mode + exam_type + selected cycle + phase_kind`; no per-slug lists. | SOURCE-LOCKED | `docs/status/Exam-Cycle-Setup-D05-Document-Requirements-Decision-2026-06-23.md` |

**Consequence (DECISION TO LOCK):** the entire onboarding flow specified here is an **embedded component** inside the PYQ Workbench panel of Manage Exam (`PyqWorkbenchPanel.jsx`). It adds **no** route and **no** sidebar entry. It therefore passes the no-new-surface test by construction.

---

## Section A — Codebase-verified findings

Each row confirms or qualifies a finding from the 25 June report against current source.

| # | Finding | Verdict | Evidence (file:line) |
|---|---|---|---|
| 1 | Raw CMS removal from normal nav is intentional and correctly implemented. | CONFIRMED — SOURCE-LOCKED | Design-Lock §1.1, §3.2, §9; `ExamIntelCms.jsx` retained as overflow-only (checklist row "I8-C — Advanced Repair isolation", MERGED PR #759). |
| 2 | PYQ source creation has no normal contextual UI; only Advanced Repair has the form. | CONFIRMED — CURRENT SOURCE FACT | `usePyqWorkbench.js:6-51` exposes only fetch/review/patch/setProvenance/getPaperSignedPdf — no create-source method. Source form lives only in `ExamIntelCms.jsx`. |
| 3 | PYQ paper creation has no normal contextual UI; the Workbench can only load existing papers. | CONFIRMED — CURRENT SOURCE FACT | `PyqWorkbenchPanel.jsx` has a "Bulk import questions" button (line ~212) but no "Add PYQ paper" action; `usePyqWorkbench.js` has no create-paper method. Empty state reads "No PYQ papers for this exam/cycle. Create one in the CMS." (`PyqWorkbenchPanel.jsx:227`). |
| 4 | Document upload (`document_assets`) and PYQ source creation (`pyq_sources`) are distinct concepts; `source_kind` ≠ `pyq_sources.source_type`. | CONFIRMED — CURRENT SOURCE FACT | `admin_exam_intel_documents.py` `DocUploadUrlRequest.source_kind` (free classification field) vs `admin_exam_intel_cms.py:2574` `_PYQ_SOURCE_TYPES = (official, memory_based, coaching, community, aggregator, unknown)`. Different enums, different tables. |
| 5 | Paper creation, source creation, and document upload are fragmented across surfaces. | CONFIRMED — CURRENT SOURCE FACT | Source create + paper create only in `ExamIntelCms.jsx`; document upload only in `ExamIntelDocuments.jsx`; attach only in `PyqWorkbenchPanel.jsx` `AttachDocModal`. No single contextual flow. |
| 6 | Manual `document_assets` UUID entry in the Workbench attach modal is inappropriate for normal operations. | CONFIRMED — CURRENT SOURCE FACT | `PyqWorkbenchPanel.jsx:113-124` `AttachDocModal` renders a free-text "Document ID (UUID of document_assets row)" input. An exam-scoped list already exists: `GET /api/admin/exam-intelligence-cms/documents?exam_id=&document_kind=pyq_paper` (`admin_exam_intel_documents.py:407-430`). |
| 7 | PYQ source review ownership is unclear; sources land pending but there is no contextual review/promote action. | CONFIRMED — CURRENT SOURCE FACT | `admin_exam_intel_cms.py:2567-2569` comment: "pyq_sources has no separate review queue … trust_status is forced 'pending' on create … but is PATCH-editable." No source-review action in the Workbench. |
| 8 | `pyq_source_id` is optional in current paper creation. | CONFIRMED — CURRENT SOURCE FACT | `admin_exam_intel_cms.py:778-780` create requires only `exam_id` and `year`; `pyq_source_id` is in `_PAPER_FIELDS` (line 723) but not required. Bulk-import config likewise requires only exam_id + year. |
| 9 | Existing backend safety contracts (born-pending, provenance lock on verified, document-replacement demotion, atomic review RPC, mandatory reason, audit, bulk-import-stays-pending, question/option cascade rollback) must be preserved. | CONFIRMED — SOURCE-LOCKED | `create_pyq_paper` forces `trust_status="pending"` (`:783`); `update_pyq_paper` provenance lock (`:812-824`); `set_pyq_paper_provenance` re-validation + demotion (`:834-939`); `review_pyq_paper` RPC (migrations 185/186); `WriteEnvelope.reason` min 8 chars (`:121`); `_audit` (`:74-105`); cascade pattern (`AGENTS.md` §7, `create_pyq_question`). |

**Conclusion:** the report's nine findings are accurate against the code. The gap is real: routine PYQ onboarding capabilities remain exclusively in Advanced Repair. The remedy is contextual, not navigational.

---

## Section B — Onboarding contract (proposed for lock)

### B.1 Contextual flow placement (DECISION TO LOCK)

- The flow is owned by `PyqWorkbenchPanel.jsx` as an embedded modal/stepper component. No new route, no sidebar entry, no second console.
- Entry points (both inside the existing panel):
  1. A primary "Add PYQ paper" action in the panel header, beside "Bulk import questions".
  2. The empty state resolves itself: the "Create one in the CMS" copy is replaced with an "Add the first PYQ paper" call-to-action that opens the same flow.
- The exam is prefilled and immutable from `ExamWorkspaceContext` (`exam.id`). The cycle (`cycle.id`) is prefilled when one is selected and is optional (consistent with D10: `exam_cycle_id` is provenance, not a corpus gate).

### B.2 Empty-state copy (DECISION TO LOCK)

`PyqWorkbenchPanel.jsx:226-230` must stop instructing operators to leave for the CMS. The replacement empty state must (a) state that no papers exist for the exam/cycle and (b) offer the in-context "Add the first PYQ paper" action. It must NOT reference the CMS or Advanced Repair.

### B.3 Document selection replaces UUID entry (DECISION TO LOCK)

- The `AttachDocModal` raw-UUID input and the onboarding flow's "evidence" step MUST use an exam-scoped document picker backed by `GET /api/admin/exam-intelligence-cms/documents?exam_id={exam.id}&document_kind=pyq_paper`.
- Each option shows operator-readable identity (title / original_filename, status, page_count, created_at) — never a bare UUID as the primary label.
- DERIVED — PROPOSED RESOLUTION: a manual-UUID fallback field is retained behind a "Enter ID manually" affordance for recovery parity, but is not the default interaction. (Operator may instead require the picker exclusively; see Open Decision OD-4.)
- The picker must surface documents whose `status` is linkable; non-linkable documents (failed/archived, wrong kind, missing storage) are either hidden or shown disabled with the reason, mirroring the six invariants in `set_pyq_paper_provenance` (`admin_exam_intel_cms.py:874-895`).

### B.4 Orchestration endpoint (DECISION TO LOCK)

Add one contextual endpoint to the existing CMS router (`admin_exam_intel_cms.py`, prefix `/admin/exam-intelligence-cms`, gated by `PERM_CMS = "exam_intelligence.cms"`, flag `ADMIN_STUDY_OS_ENABLED`):

```
POST /api/admin/exam-intelligence-cms/pyq-onboarding
```

**Request body (extends `WriteEnvelope`-style `reason` discipline):**

```jsonc
{
  "reason": "Added official 2024 paper from commission archive",   // required, 8–500 chars
  "exam_id": "...",                 // required; must resolve in `exams`
  "exam_cycle_id": "...",           // optional; validated FK if present
  "exam_phase_id": "...",           // optional; validated FK if present
  "source": {                       // optional block; see B.5
    "existing_pyq_source_id": null, // when set, reuse; do NOT create
    "source_registry_id": "...",    // -> pyq_sources.source_id (Source Registry ref)
    "source_type": "official",      // must be in _PYQ_SOURCE_TYPES
    "title": "...",
    "source_url": "...",
    "metadata": {}
  },
  "paper": {                        // required
    "year": 2024,                   // required
    "paper_date": "...",
    "shift": "...",
    "paper_code": "...",
    "source_url": "...",
    "source_type": "official",      // must be in _PAPER_SOURCE_TYPES
    "metadata": { "expected_question_count": 100 }
  },
  "document_id": "..."              // optional; already-uploaded document_assets row
}
```

**Operation order and invariants (DECISION TO LOCK):**

1. Validate `exam_id` resolves (`_safe_select(exams)`); 422 otherwise. Validate `exam_cycle_id`/`exam_phase_id` FKs when present.
2. **Source resolution:**
   - If `source.existing_pyq_source_id` is set: validate it exists and `pyq_sources.exam_id == exam_id`; reuse it. Do not mutate its `trust_status`.
   - Else if a `source` block with creatable fields is provided: create a `pyq_sources` row via the SAME path as `create_pyq_source` — `trust_status` forced `pending`, `source_type` enum-validated, audit written. The created `source.id` becomes the paper's `pyq_source_id`.
   - Else: no source (permitted today; see B.6 / OD-1).
3. **Paper creation:** create a `pyq_papers` row via the SAME rules as `create_pyq_paper` — `trust_status` forced `pending`, `source_type` enum-validated, `pyq_source_id` set from step 2 when available. `exam_cycle_id`/`exam_phase_id` carried through as provenance (D10).
4. **Document linkage (when `document_id` present):** re-run the six provenance invariants used by `set_pyq_paper_provenance` (`admin_exam_intel_cms.py:874-895`) / `link_to_pyq_paper` (scope, kind, status, storage, exam match). Because the paper is freshly `pending`, set `source_document_id` directly on the create row (no verified→pending demotion is needed). 422 with `{error, blocking_fields}` on any invariant failure — and roll back per step 6.
5. **Audit:** write an `admin_audit_logs` row per created entity plus one `exam_intel.cms.pyq_onboarding` envelope carrying `reason` and the created IDs.
6. **Atomic cascade (AGENTS.md §7 pattern):** if any dependent step fails after a row was created in THIS request, delete the rows this request created (paper, then the source only if this request created it) and return `{ "ok": false, "child_errors": [...] }`. Application-level rollback is acceptable; a DB transaction/RPC is preferred if added.
7. **Response on success:**

```jsonc
{
  "ok": true,
  "audit_id": "...",
  "source": { "id": "...", "created": true|false, "trust_status": "pending" },
  "paper":  { "id": "...", "trust_status": "pending", "pyq_source_id": "..." },
  "document_link": { "document_id": "...", "linked": true } | null
}
```

The frontend then selects the created paper (`setSelectedPaperId`) and offers bulk import / extractor proposals. All rows remain `pending`; nothing is auto-verified (Finding 9; `AGENTS.md` §8).

### B.5 PYQ source trust lifecycle (DERIVED — PROPOSED RESOLUTION)

Today `pyq_sources` has no review queue and `trust_status` is PATCH-editable (Finding 7). Proposed resolution for operator approval:

- Sources created through onboarding land `pending` (unchanged).
- The PYQ Workbench gains a **read-only source-trust summary** for the selected paper's source (shows `trust_status`, title, type, URL).
- Source promotion is **folded into paper verification**: a paper cannot be verified unless its provenance is complete (existing gate, migrations 185/186). The source's trust is treated as derived from the paper's validated provenance rather than a separate review action — avoiding a second review queue.
- Alternative (OD-2): add a dedicated source verify/reject/re-queue action mirroring paper review. This requires a contract for the source review RPC and is heavier. Proposed default is the folded model.

### B.6 `pyq_source_id` enforcement policy (DECISION TO LOCK + DERIVED)

- DECISION TO LOCK: do NOT make `pyq_source_id` mandatory on `pyq_papers` in this work. Existing source-less papers must remain readable; bulk-import and extraction flows must not break (Finding 8; `AGENTS.md` migration discipline).
- DECISION TO LOCK: new contextual paper creation SHOULD create or select a source by default (the onboarding flow always offers it first).
- DERIVED — PROPOSED RESOLUTION: source-less papers surface as **provenance debt** in the Workbench (an advisory badge), not a hard error. Hard enforcement, if ever desired, is a separate forward migration after backfill + compatibility analysis (OD-3).

### B.7 Atomicity boundary for PDF capture (DECISION TO LOCK)

PDF bytes are uploaded to object storage before any DB orchestration can complete; a single DB transaction spanning upload + orchestration is impossible. The locked boundary is:

```
upload asset first (existing Documents upload sequence)
  → call POST /pyq-onboarding with the resulting document_id
  → if onboarding fails, the asset remains unlinked and recoverable
```

For this contract, the onboarding flow consumes an **already-uploaded** exam-scoped document via the picker (§B.3). Whether the modal also embeds the full upload sequence inline (re-using the Documents tab's upload-url → PUT → complete-upload → poll path) is OD-5; it is not required to close the core gap.

---

## Section C — Open decisions requiring operator approval

| ID | Decision | Proposed default | Label |
|---|---|---|---|
| OD-1 | May onboarding create a paper with no source at all (just URL/document evidence)? | Yes — keep parity with current `create_pyq_paper`; encourage but do not require a source. | DERIVED — PROPOSED RESOLUTION |
| OD-2 | Source trust lifecycle: fold into paper verification (B.5 default) vs dedicated source review action. | Fold into paper verification; no second review queue. | DERIVED — PROPOSED RESOLUTION |
| OD-3 | Surface source-less papers as advisory "provenance debt" vs leave silent. | Advisory badge only; no enforcement. | DERIVED — PROPOSED RESOLUTION |
| OD-4 | Retain manual-UUID fallback in the document step, or picker-only. | Retain fallback behind an affordance for recovery parity. | DERIVED — PROPOSED RESOLUTION |
| OD-5 | Inline PDF upload inside the onboarding modal vs select-only (upload stays in Documents tab). | Select-only for v1; inline upload is a follow-up. | UNRESOLVED — OPERATOR DECISION REQUIRED |
| OD-6 | Atomic cascade via application-level rollback (B.4 step 6) vs a new Postgres RPC/transaction. | Application-level rollback for v1, matching the existing cascade pattern. | DERIVED — PROPOSED RESOLUTION |

---

## Section D — Acceptance tests (must pass before the implementation PR merges)

**Backend (`app/backend/tests/exam_intelligence/test_pyq_onboarding.py`, new):**

```
[ ] POST /pyq-onboarding with new source + paper creates both pending; returns source.created=true, paper.trust_status="pending"
[ ] existing_pyq_source_id reuses the source (source.created=false) and does not mutate its trust_status
[ ] paper.pyq_source_id is set to the resolved/created source id
[ ] document_id that fails an invariant returns 422 {error, blocking_fields} AND rolls back any row created this request
[ ] missing exam_id / unresolved exam_id -> 422; reason < 8 chars -> 422
[ ] source_type outside _PYQ_SOURCE_TYPES / _PAPER_SOURCE_TYPES -> 422
[ ] every successful create writes an admin_audit_logs row (source, paper, onboarding envelope)
[ ] paper is never born verified (trust_status forced pending even if caller sends verified)
```

**Frontend (`PyqWorkbench.test.jsx` / new test):**

```
[ ] empty state renders an "Add the first PYQ paper" action and does NOT contain the string "CMS"
[ ] panel header renders an "Add PYQ paper" action beside Bulk import
[ ] the document step renders an exam-scoped picker (options labeled by title/filename, not bare UUID)
[ ] submitting the flow calls POST /pyq-onboarding and selects the returned paper
[ ] no new route is registered (navContract.test.js unchanged for exam-intelligence paths)
```

---

## Section E — Bounded write scope for the implementation PR

| Layer | Allowed files | Not allowed |
|---|---|---|
| Backend | `app/backend/app/api/admin_exam_intel_cms.py` (add `/pyq-onboarding` only); new `app/backend/tests/exam_intelligence/test_pyq_onboarding.py` | New migrations; changes to `review_pyq_paper`/projection RPCs; extraction pipeline |
| Frontend | `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/PyqWorkbenchPanel.jsx`, `usePyqWorkbench.js`, a new `AddPyqPaperModal.jsx` + document-picker in the same dir; workbench tests | `AdminShell.jsx`, `adminRoutes.jsx`, any sidebar/route file; `ExamIntelCms.jsx` |
| Docs | `docs/status/career-copilot-checklist.md` (J2 sub-row), this gate doc | — |

Any change outside this scope re-opens the IA problem and must be rejected in review.

---

## Section F — Checklist update

The J2 row in `docs/status/career-copilot-checklist.md` is annotated to reference this gate as the contract for the **historical paper creation** sub-item. The J2 row remains `DEFERRED` overall; only the PYQ-onboarding sub-item gains a contract pointer. No completion or operator-validation claim is made by this document.

---

*This document is a planning artifact. No runtime files were changed in the PR that introduced it. It does not unblock implementation until the operator closes every `DERIVED — PROPOSED RESOLUTION` and `UNRESOLVED — OPERATOR DECISION REQUIRED` item above and moves this document out of DRAFT.*
