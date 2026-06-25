# PYQ Source and Paper Onboarding Gate — J2 Contract

- Document type: J2 sub-gate — contextual PYQ onboarding implementation contract
- Status: DRAFT — OD-1…OD-6 RESOLVED by operator review (2026-06-25); **final approval still pending PR #763 merge + rebase + re-verification**
- Date: 2026-06-25 (rev. 2 — rebaselined onto PR #763)
- Parent track: `J2 — missing operational editors in Manage Exam` (`docs/status/career-copilot-checklist.md` row "J2"), specifically the **historical paper creation** sub-item.
- Baseline: This revision describes the **post-PR-#763** codebase. PR #763 is not yet merged at the time of writing; its diff was read directly from `refs/pull/763/head` and every "POST-#763 SOURCE FACT" below was verified against that ref. Before this gate leaves DRAFT, the implementation branch MUST be rebased onto the `main` that results from merging #763, and every POST-#763 SOURCE FACT re-verified against merged source.
- Effect: No PYQ-onboarding implementation PR may be dispatched until (a) PR #763 is merged, (b) this gate is rebased and re-verified against the resulting `main`, and (c) the operator moves this document out of DRAFT.
- Repository scope of the PR that introduces this document: **documentation and checklist only**. No runtime, route, component, API, migration, or test change is authorized by this file.

---

## Purpose and non-goals

**Purpose**

- Convert the 25 June 2026 "PYQ Source and Paper Onboarding: Codebase Verification Report" into an operator-approvable, codebase-verified implementation contract, consistent with this repo's contract-first discipline (the I6 cycle-setup gate and the I8 IA design-lock).
- Re-baseline the contract onto PR #763, which already implements part of the onboarding foundation (the document picker, the source selector, the provenance-completeness contract, and the atomic provenance RPC extension).
- Record the operator's resolutions of OD-1…OD-6 (review of 2026-06-25).
- Bound the write scope of the eventual implementation PR so it cannot drift into a new surface, a duplicate provenance form, or a Raw CMS restoration.

**Non-goals**

- This document does NOT authorize any runtime, route, component, API, backend, migration, or automated-test change. It is a planning artifact.
- This document does NOT restore Raw CMS (`ExamIntelCms.jsx`) to primary navigation. Finding 1 is confirmed and the IA lock holds.
- This document does NOT authorize a new top-level surface. The onboarding flow is an embedded component inside the existing PYQ Workbench tab of Manage Exam.
- This document does NOT make `pyq_source_id` mandatory on `pyq_papers` (OD-1), does NOT introduce source-trust promotion (OD-2), and does NOT change the extraction pipeline or competition/coverage schema (J3).

---

## Source authority and decision labels

| Label | Definition |
|---|---|
| SOURCE-LOCKED | Explicitly stated in a merged findings, design-lock, or APPROVED decision document. |
| POST-#763 SOURCE FACT | Behavior present on `refs/pull/763/head`, verified during this revision; becomes a current source fact once #763 merges. Not automatically a product rule. |
| DECISION TO LOCK | A decision this artifact proposes to lock once approved. |
| OPERATOR-RESOLVED (2026-06-25) | A formerly-open decision (OD-n) that the operator resolved in the 2026-06-25 review. |

**Authority discipline:** code evidence alone is not a product decision. Every POST-#763 SOURCE FACT below was re-verified against `refs/pull/763/head` (merge-base `dca3ec57`). These MUST be re-verified against merged `main` after #763 lands.

---

## Locked architecture recap (IA compliance)

| Rule | Authority | Source |
|---|---|---|
| One visible exam-operation destination: Exam Management → Manage Exam → More → Advanced Repair. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §1.1 |
| No new top-level destination unless it removes at least two existing ones. Embedded components, drill-in pages, overflow actions, and backend endpoints are NOT surfaces. | SOURCE-LOCKED | Design-Lock §1.2; `AGENTS.md` §18 |
| Advanced Repair (`ExamIntelCms.jsx`) is retained as a permission-gated recovery surface, reached only via Manage Exam → More → Advanced Repair. Routine creation must move into contextual workflows. | SOURCE-LOCKED | Design-Lock §3.2, §9 |
| PYQ corpus readiness is exam-wide; `pyq_papers.exam_cycle_id` is provenance, not a corpus filter. | SOURCE-LOCKED | `docs/status/Exam-Cycle-Setup-D10-PYQ-Readiness-Scope-Decision-2026-06-23.md` |
| Required exam evidence (incl. minimum verified PYQ paper per active written phase for `core`) derives from `management_mode + exam_type + selected cycle + phase_kind`; no per-slug lists. | SOURCE-LOCKED | `docs/status/Exam-Cycle-Setup-D05-Document-Requirements-Decision-2026-06-23.md` |

**Consequence (DECISION TO LOCK):** the onboarding flow is an **embedded component** inside the PYQ Workbench panel of Manage Exam (`PyqWorkbenchPanel.jsx`). It adds **no** route and **no** sidebar entry, so it passes the no-new-surface test by construction.

---

## Section 0 — Baseline: what PR #763 already provides

PR #763 ("PYQ provenance: include source") changes runtime provenance behavior. The following are POST-#763 SOURCE FACTs (verified from `refs/pull/763/head`). The onboarding implementation MUST reuse and extend these, not reimplement or contradict them.

| Capability | POST-#763 state | Evidence |
|---|---|---|
| Exam-scoped document picker | `PaperProvenanceModal` replaces the raw-UUID `AttachDocModal`; renders a human-readable source-document picker (`data-testid="provenance-document-id"`). | `PyqWorkbenchPanel.jsx` (#763) lines 95-96, 198-205 |
| PYQ source selector | The same modal exposes a `pyq_source` selector (`data-testid="provenance-pyq-source-id"`). | `PyqWorkbenchPanel.jsx` (#763) line 229 |
| Source/document fetchers | Hook adds `fetchPyqDocuments()` (exam-scoped, `document_kind=pyq_paper`) and `fetchPyqSources()` (exam-scoped). | `usePyqWorkbench.js` (#763) |
| Provenance completeness contract | Exported `isPaperProvenanceComplete(paper)`; row shows "Verify" when complete, "Confirm provenance" when not. | `PyqWorkbenchPanel.jsx` (#763) lines 26, 345-346, 433-458 |
| `pyq_source_id` as protected provenance | `_PROVENANCE_FIELDS` now includes `pyq_source_id`; set-provenance validates existence + exam match; routed through the atomic RPC. | `admin_exam_intel_cms.py` (#763) lines 730, 892-897; migration `191_pyq_provenance_include_source.sql` |
| Exam-wide paper list | `fetchPapers()` no longer passes `exam_cycle_id` (D10). | `usePyqWorkbench.js` (#763) |
| `useApiAction` wiring | `reviewPaper`/`patchPaper`/`saveProvenance` use `useApiAction`. | `usePyqWorkbench.js` (#763) |
| Atomic provenance mutation | `cms_set_pyq_paper_provenance` RPC extended (migration 191) to accept/validate `pyq_source_id` under the row lock. | migration `191_…sql` |

**What PR #763 does NOT do (the residual J2 onboarding gap):**

1. It does not create a `pyq_sources` row from the normal flow — only selects existing sources.
2. It does not create a `pyq_papers` row from the normal flow — the Workbench still only loads existing papers; `PaperProvenanceModal` edits existing papers.
3. The empty state still reads "No PYQ papers for this exam. Create one in the CMS." (`PyqWorkbenchPanel.jsx` #763 line 388).
4. There is no atomic create-source + create-paper + link-document orchestration.

This residual gap is the entire scope of the onboarding implementation.

---

## Section A — Codebase-verified findings (post-#763)

| # | Finding | Post-#763 verdict | Evidence |
|---|---|---|---|
| 1 | Raw CMS removal from normal nav is intentional and correctly implemented. | CONFIRMED — SOURCE-LOCKED (unchanged by #763) | Design-Lock §1.1/§3.2/§9; checklist "I8-C" MERGED. |
| 2 | PYQ **source creation** has no normal contextual UI. | STILL OPEN after #763 — #763 adds source *selection*, not *creation*. | `usePyqWorkbench.js` (#763) `fetchPyqSources` exists; no create-source method anywhere but `ExamIntelCms.jsx`. |
| 3 | PYQ **paper creation** has no normal contextual UI. | STILL OPEN after #763 — Workbench loads/edits existing papers only. | `PyqWorkbenchPanel.jsx` (#763) has no "Add PYQ paper" action; empty state line 388 still points to CMS. |
| 4 | Document `source_kind` ≠ `pyq_sources.source_type`. | CONFIRMED (unchanged). | `admin_exam_intel_documents.py` `DocUploadUrlRequest.source_kind` vs `admin_exam_intel_cms.py` `_PYQ_SOURCE_TYPES` (line 2588 on the #763 ref; ~2574 on pre-#763 main — re-verify post-merge per Section F). |
| 5 | Paper/source creation + document upload fragmented across surfaces. | PARTIALLY CLOSED by #763 (picker + selector are now contextual); creation still fragmented. | §0 above. |
| 6 | Manual `document_assets` UUID entry in the attach modal. | CLOSED by #763 — replaced by the picker. | `PaperProvenanceModal` (#763) "Replaces the old raw-UUID AttachDocModal". |
| 7 | PYQ source review ownership unclear. | CONFIRMED (unchanged) — #763 does not promote or synchronize `pyq_sources.trust_status`. | `admin_exam_intel_cms.py:2567-2569`; #763 validates source exists/exam-match only. |
| 8 | `pyq_source_id` optional in paper creation. | CONFIRMED (unchanged) — #763 makes it *protected provenance when present*, not *required*. | `admin_exam_intel_cms.py:778-780`; #763 `_PROVENANCE_FIELDS` addition. |
| 9 | Existing backend safety contracts must be preserved. | CONFIRMED — #763 strengthens them (atomic RPC now covers `pyq_source_id`). | migrations 185/186/189/191; `create_pyq_paper:783`; `WriteEnvelope.reason:121`. |

**Conclusion:** after #763, the gap narrows to **contextual source creation, paper creation, and an atomic orchestration that links to #763's existing picker/selector/provenance machinery**, plus the empty-state copy fix.

---

## Section B — Onboarding contract (revised for the operator's OD decisions)

### B.1 Contextual flow placement (DECISION TO LOCK)

- Owned by `PyqWorkbenchPanel.jsx` as an embedded modal/stepper. No new route, no sidebar entry.
- Entry points: (1) a primary "Add PYQ paper" action in the panel header beside "Bulk import questions"; (2) the empty state's "Add the first PYQ paper" CTA.
- The exam is prefilled and immutable from `ExamWorkspaceContext`. A selected cycle MAY prefill the paper's `exam_cycle_id`/`exam_phase_id` **provenance**, but the paper list and empty state are **exam-wide** (D10); selecting a cycle never filters the corpus.

### B.2 Empty-state copy (DECISION TO LOCK)

`PyqWorkbenchPanel.jsx` line 388 (post-#763) still reads "No PYQ papers for this exam. Create one in the CMS." The onboarding PR replaces this so it (a) states no papers exist **for this exam** (exam-wide, not exam/cycle) and (b) offers the in-context "Add the first PYQ paper" action. It must NOT reference the CMS or Advanced Repair.

### B.3 Document and source selection (OPERATOR-RESOLVED — OD-4, OD-5)

- **Picker-only in the normal Workbench (OD-4 resolved: reject manual-UUID fallback).** The onboarding flow reuses #763's exam-scoped document picker and `pyq_source` selector. No raw-UUID interaction is exposed in the normal flow. Manual/ID-level recovery remains exclusively in `Manage Exam → More → Advanced Repair`.
- Picker requirements (per OD-4): exam-scoped; `document_kind=pyq_paper`; filename/title as the primary label; page count; status; creation/upload date; linkability state; no bare UUID.
- **Select-only upload for v1 (OD-5 resolved).** The onboarding flow consumes an already-uploaded exam-scoped document via the picker; it does NOT re-implement upload-url → PUT → complete-upload → extraction-polling. The bounded v1 journey is: *Documents tab → upload PDF → PYQ Workbench → Add PYQ paper → select uploaded PDF → create source/paper/link.* Inline upload is a separately bounded follow-up.
- The document list is **exam-wide**, not cycle-filtered (D10). Cycle metadata may appear as a presentation hint only.

### B.4 Orchestration endpoint and atomicity (OPERATOR-RESOLVED — OD-6)

- **Transactional RPC, not application-level rollback (OD-6 resolved: reject app rollback as the locked target).** Because every post-upload step is a database operation (source insert, paper insert, document linkage, three audit writes), the onboarding operation MUST commit atomically inside a PostgreSQL `SECURITY DEFINER` RPC. Object-storage upload stays outside the transaction (the acknowledged boundary).

Endpoint (CMS router, prefix `/admin/exam-intelligence-cms`, `PERM_CMS`, flag `ADMIN_STUDY_OS_ENABLED`):

```
POST /api/admin/exam-intelligence-cms/pyq-onboarding
```

Flow:

```
Python validates request shape (reason 8–500 chars; exam_id resolves; cycle/phase FKs)
  → PostgreSQL RPC (new migration, numbered from post-#763 main):
      lock/validate referenced rows (exam, optional cycle/phase, optional document, optional existing source)
      create optional pyq_source (trust_status forced 'pending')         [skip if existing_pyq_source_id given]
      create pyq_paper (trust_status forced 'pending'; pyq_source_id set when resolved)
      attach document via source_document_id (re-run the six provenance invariants; reuse the migration-191 validation path)
      write source / paper / onboarding-envelope audits
      return the created records
  → any failure rolls back ALL database changes
```

Request body:

```jsonc
{
  "reason": "Added official 2024 paper from commission archive",
  "exam_id": "...",
  "exam_cycle_id": "...",            // optional provenance
  "exam_phase_id": "...",            // optional provenance
  "source": {                        // optional; see OD-1 / B.5
    "existing_pyq_source_id": null,  // when set, reuse; do NOT create or mutate its trust_status
    "source_registry_id": "...",
    "source_type": "official",       // must be in _PYQ_SOURCE_TYPES
    "title": "...", "source_url": "...", "metadata": {}
  },
  "paper": {                         // required
    "year": 2024, "paper_date": "...", "shift": "...", "paper_code": "...",
    "source_url": "...", "source_type": "official",   // must be in _PAPER_SOURCE_TYPES
    "metadata": { "expected_question_count": 100 }
  },
  "document_id": "..."               // optional; already-uploaded document_assets row
}
```

Response on success returns `{ ok, audit_id, source:{id,created,trust_status}, paper:{id,trust_status,pyq_source_id}, document_link }`. All rows are born `pending`; nothing is auto-verified (Finding 9; `AGENTS.md` §8).

### B.5 PYQ source: optional, no trust promotion in v1 (OPERATOR-RESOLVED — OD-1, OD-2)

- **OD-1 resolved (approve, tightened):** `pyq_source_id` is **optional**. A paper may be created and verified without it when its paper-level provenance is complete — i.e. `source_type` is valid AND (`source_url` OR `source_document_id`). This matches #763's `isPaperProvenanceComplete()`. The source step is offered first and encouraged, but never required. No migration/backfill is introduced for enforcement.
- **OD-2 resolved (reject folded-trust wording):** the onboarding PR does NOT introduce source-trust promotion and does NOT claim source trust is "derived" from paper verification. `pyq_sources` is treated as an **optional reusable provenance grouping record**: created `pending`, shown read-only in the paper provenance UI, not required for paper verification, and not claimed verified merely because a linked paper was verified. A source-level trust lifecycle is a **separate future contract** (out of scope here).

### B.6 Source-link advisory, not "provenance debt" (OPERATOR-RESOLVED — OD-3)

- **OD-3 resolved (approve, renamed + narrowed):** a paper with complete paper-level provenance but no `pyq_source_id` is NOT provenance-incomplete. The advisory uses neutral copy — **"No reusable source record"** (or "Source record not linked") — and is visually distinct from true blockers. It must not duplicate or contradict #763's "Verify" vs "Confirm provenance" logic.

| Condition | UI treatment |
|---|---|
| Missing/unknown `source_type` | Blocking — provenance incomplete (#763) |
| No URL and no document | Blocking — provenance incomplete (#763) |
| Valid type + URL/document, no `pyq_source_id` | Advisory — "No reusable source record" |
| Invalid/mismatched `pyq_source_id` | Blocking (#763 validation) |
| Complete provenance | No warning |

---

## Section C — OD decisions (resolved 2026-06-25)

| ID | Decision | Operator resolution |
|---|---|---|
| OD-1 | Paper creation without a `pyq_source`. | **APPROVED (tightened).** Optional; verifiable when `source_type` valid AND (`source_url` OR `source_document_id`). Source offered first, not required. |
| OD-2 | Source trust: fold into paper verification vs separate lifecycle. | **REJECTED folded-trust wording.** v1: source trust unchanged and out of scope; `pyq_sources` is an optional reusable grouping record. Source lifecycle is a separate contract. |
| OD-3 | Surface source-less papers. | **APPROVED with rename.** Neutral advisory "No reusable source record", narrowed to the advisory case; distinct from blockers. |
| OD-4 | Manual UUID fallback vs picker-only. | **REJECTED fallback. Picker-only** in the normal Workbench; ID-level recovery stays in Advanced Repair. |
| OD-5 | Inline upload vs select-only v1. | **APPROVED select-only** for v1; document list exam-wide; inline upload a separate follow-up. |
| OD-6 | Application rollback vs DB transaction/RPC. | **REJECTED app rollback. Use a PostgreSQL RPC transaction**; permit one forward migration numbered from post-#763 `main` (do not preassign). |

---

## Section D — Acceptance tests (must pass before the implementation PR merges)

**Backend (`app/backend/tests/exam_intelligence/test_pyq_onboarding.py`, new):**

```
[ ] POST /pyq-onboarding with new source + paper creates both pending; source.created=true
[ ] existing_pyq_source_id reuses the source (source.created=false) and does not mutate its trust_status
[ ] paper.pyq_source_id is set to the resolved/created source id
[ ] paper created WITHOUT a source but WITH valid source_type + (source_url|source_document_id) succeeds (OD-1)
[ ] a failure in any RPC step rolls back ALL rows (no orphan source/paper/audit) (OD-6)
[ ] document_id failing an invariant -> 422 {error, blocking_fields}; whole op rolled back
[ ] missing/unresolved exam_id -> 422; reason < 8 chars -> 422; bad source_type enum -> 422
[ ] paper is never born verified
```

**Frontend (`PyqWorkbench.test.jsx` / new):**

```
[ ] empty state renders "Add the first PYQ paper" and does NOT contain "CMS"; copy is exam-wide ("for this exam")
[ ] panel header renders an "Add PYQ paper" action beside Bulk import
[ ] the onboarding modal reuses the #763 document picker + pyq_source selector (no raw-UUID input) (OD-4)
[ ] a paper with valid provenance but no pyq_source_id shows the "No reusable source record" advisory, NOT a blocker (OD-3)
[ ] submitting calls POST /pyq-onboarding and selects the returned paper
[ ] no new route is registered (navContract.test.js unchanged for exam-intelligence paths)
```

---

## Section E — Bounded write scope for the implementation PR

| Layer | Allowed | Not allowed |
|---|---|---|
| Backend | `admin_exam_intel_cms.py` (add `/pyq-onboarding` only); **one** new migration adding the onboarding RPC, numbered MAX(main)+1 **after #763 merges** (do not preassign); new `tests/exam_intelligence/test_pyq_onboarding.py` | Changes to `review_pyq_paper`/projection RPCs; extraction pipeline; making `pyq_source_id` NOT NULL |
| Frontend | `PyqWorkbenchPanel.jsx`, `usePyqWorkbench.js`, a new `AddPyqPaperModal.jsx`; **extract a shared `PyqProvenanceFields` component** used by BOTH `PaperProvenanceModal` (#763) and `AddPyqPaperModal` so the source-type selector, document picker, `pyq_source` selector, URL field, and blocker formatting exist once; reuse `useApiAction` and #763's error handling; workbench tests | `AdminShell.jsx`, `adminRoutes.jsx`, any sidebar/route file; `ExamIntelCms.jsx`; a second independent provenance/picker/selector implementation |
| Docs | `docs/status/career-copilot-checklist.md` (J2 sub-row), this gate doc | — |

**Reuse mandate (DECISION TO LOCK):** the onboarding modal MUST NOT independently re-implement the source-type selector, document picker, PYQ source selector, URL field, provenance-completeness rule, or blocker formatting introduced by #763. It composes the shared `PyqProvenanceFields` component and reuses `isPaperProvenanceComplete()`. Any change outside this scope re-opens the IA problem or creates a drifting duplicate form and must be rejected in review.

---

## Section F — Sequencing and checklist

**Required sequence (operator review 2026-06-25):**

1. Complete and merge PR #763.
2. Rebase this gate / its branch onto the resulting `main`.
3. Re-verify every POST-#763 SOURCE FACT against merged source; update if #763 changed before merge.
4. Confirm OD-1…OD-6 resolutions (Section C) still hold.
5. Operator moves this document out of DRAFT; only then dispatch the onboarding implementation PR.

**Checklist:** the J2 row in `docs/status/career-copilot-checklist.md` is annotated to say this gate **proposes** (not "locks") the contextual flow; implementation remains gated on PR #763 merge + the OD resolutions + this document leaving DRAFT. No completion or operator-validation claim is made.

**Overlap with PR #763:** the only shared file is `docs/status/career-copilot-checklist.md` (separate hunks — #763 adds a provenance-fix row near the projection section; this PR edits the later J2 row). Rebase after #763 regardless. There is no runtime file collision (this PR has no runtime changes).

---

*This document is a planning artifact. No runtime files were changed in the PR that introduced it. It does not unblock implementation until PR #763 merges, this gate is rebased and re-verified, and the operator moves it out of DRAFT.*
