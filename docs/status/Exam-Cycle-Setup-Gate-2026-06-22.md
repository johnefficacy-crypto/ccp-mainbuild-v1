# Exam Cycle Setup Gate — I6 Design Contract

- Document type: I6 cycle-setup implementation gate
- Status: DRAFT — OPERATOR APPROVAL AND POST-#757 REBASE VERIFICATION REQUIRED
- Effect: I9 remains BLOCKED until every unresolved/derived item is approved, PR #757 is merged and rebase-verified, and I8-C completes the shared Manage Exam lane
- Repository scope: documentation and checklist only; no runtime, route, component, API, migration, or test change

## Purpose and non-goals

**Purpose**

- SOURCE-LOCKED: I9 remains blocked until the I6 gate document defines completion source, gate class, deep-link target, resume behavior, selected-cycle behavior, management-mode/cadence applicability, `AddCycleWizard` decision, progress derivation, and manual completion rules. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.4.
- I6 DECISION TO LOCK: This document defines a draft executable contract for I9 dispatch-readiness while distinguishing current source-backed implementation facts from proposed selected-cycle I9 behavior.
- REBASE VERIFY: PR #757 is open and unmerged; final route, query-param, tab, current-cycle, and management-read-model behavior must be reverified after this branch is rebased onto the commit containing merged PR #757.

**Non-goals**

- I6 DECISION TO LOCK: No route, component, API, backend, database migration, automated test, or runtime behavior change is authorized here.
- I6 DECISION TO LOCK: No I9 implementation, I8-C implementation, new top-level surface, checklist completion claim, or operator/live validation claim is authorized here.
- I6 DECISION TO LOCK: PR #758 must remain draft; this document does not make I6 approved, does not unblock I9, and does not authorize merging before the operator closes all derived/unresolved/rebase-dependent items.

## Source authority and decision labels

| Label | Definition |
|---|---|
| SOURCE-LOCKED | Explicitly stated in the merged findings or design-lock document. |
| CURRENT SOURCE FACT | Current local source code or migration behavior observed during this revision; not automatically a product rule. |
| I6 DECISION TO LOCK | A decision this I6 artifact proposes to lock for I9 once approved. |
| DERIVED — OPERATOR APPROVAL REQUIRED | A constrained inference from source behavior or definitions, not yet approved as product policy. |
| UNRESOLVED — OPERATOR DECISION REQUIRED | Source material does not define enough to decide safely. |
| REBASE VERIFY | Depends on final merged PR #757 source or later I8-C source. |

**Authority discipline**

- I6 DECISION TO LOCK: Current implementation facts may be documented, but code evidence alone is not a product decision.
- I6 DECISION TO LOCK: Selected-cycle activation authority is not SOURCE-LOCKED in the current merged sources. Current activation classification remains exam-scoped; selected-cycle nine-step progress is a proposed I9 backend contract.
- I6 DECISION TO LOCK: Route/query/tab behavior that PR #757 owns remains REBASE VERIFY until #757 merges and this branch is rebased.

## Locked architecture recap

| Rule | Authority | Source |
|---|---|---|
| Hybrid architecture: bounded mini-wizard plus persistent activation checklist. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.2 |
| Mini-wizard is limited to cycle identity/dates, phase selection/creation, and review/save. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.2 |
| Persistent nine-step checklist owns activation readiness and is resumable across sessions. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.1–§6.2 |
| After creation, return to Manage Exam with the created cycle selected. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.2 |
| I9 implementation remains blocked until this gate is approved. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.4 |
| No new route or sidebar surface is allowed for cycle setup. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §2.2, §13, Appendix B |

## Current activation authority versus proposed I9 authority

| Topic | Current source-backed state | Proposed I9 state | Authority / remaining decision |
|---|---|---|---|
| Top-level verdict | `build_console_detail(sb, exam_id, cycle_id)` reads one exam, then calls `work_queue.aggregate(sb, [exam], include_details=True)` and `work_queue.classify_exam(agg)`. The aggregate keys by `exam_id`; the supplied `cycle_id` only affects current deep-link context. | I9-0 must introduce or extend a backend contract that returns all nine activation steps for selected exam and selected cycle. | CURRENT SOURCE FACT for current state; I6 DECISION TO LOCK for proposed selected-cycle backend contract. Source: `app/backend/app/exam_intelligence/console_detail.py` `build_console_detail`; `app/backend/app/exam_intelligence/work_queue.py` `aggregate`, `classify_exam`. |
| Hard blockers | Current classifier hard blockers are `phase_count == 0` and `locked_coverage_count == 0`; `verified_pyq_count == 0` contributes a `missing_pyq` flag and can produce `needs_action`, not `blocked`. | I9 must preserve existing hard blockers unless the operator approves a changed gate model. | CURRENT SOURCE FACT; selected-cycle hard-gate remapping is UNRESOLVED — OPERATOR DECISION REQUIRED. Source: `app/backend/app/exam_intelligence/work_queue.py` `classify_exam`. |
| Action evidence | Most current classifier-owned evidence is exam-scoped because aggregate reads child rows by `exam_id`; current `cycle_id` does not filter classification. | I9 must separate current exam-scoped inherited evidence from selected-cycle evidence in the backend response. | I6 DECISION TO LOCK. |
| Readiness facts | `readiness.py` still produces seven sections: setup, documents, syllabus_mapper, pyq_workbench, updates, competition, review_activate. | I9 must not translate those seven sections into nine frontend-only steps; the backend must own nine-step progress derivation. | CURRENT SOURCE FACT plus I6 DECISION TO LOCK. Source: `app/backend/app/exam_intelligence/readiness.py` `compute_exam_workspace_readiness`. |
| Activation score | Readiness score percentages are advisory and must not authorize activation. | I9 checklist may display backend progress but must not replace `classify_exam` activation authority without an explicit operator-approved contract. | SOURCE-LOCKED for score discipline. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §4.2. |

## AddCycleWizard decision

| Decision / evidence | Label | Source |
|---|---|---|
| Inline destination combines canonical Manage Exam with Appendix B query `?tab=setup&action=add-cycle`. | SOURCE-LOCKED for Appendix B target shape; REBASE VERIFY for final PR #757 handler behavior. | `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` Appendix B; `app/frontend/src/routes/adminRoutes.jsx` `AddCycleRedirect`. |
| Reuse or extract validation, duplicate-cycle detection, template-phase selection, phase-slug generation, and review-summary logic from `AddCycleWizard.jsx`; do not mount the standalone component unchanged. | I6 DECISION TO LOCK | `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx`; `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx`. |
| Implement the bounded Cycle → Phases → Review & Create flow inside Manage Exam → Setup, with `SetupPanel.jsx` as operational owner. | I6 DECISION TO LOCK; REBASE VERIFY for final tab/action handling. | Findings §6.2; design-lock Appendix B; `SetupPanel.jsx`. |
| Retain `AddCycleWizard.jsx` until I9 replacement behavior and compatibility tests pass; retire any standalone dead component only in later cleanup. | I6 DECISION TO LOCK | Design-lock §2.4 and §10.7 compatibility/cleanup sequence. |
| Existing `SetupPanel.jsx` opens the current cycle form when `action=add-cycle`, but it does not already implement the bounded three-step mini-wizard. | CURRENT SOURCE FACT | `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx`. |

## Progress authority

| Rule | Label |
|---|---|
| I9 progress must be backend-derived and recomputable from canonical evidence. | I6 DECISION TO LOCK |
| Frontend may render progress but must not infer permanent completion, activation authority, or selected-cycle gate state independently. | I6 DECISION TO LOCK |
| Existing `activation_verdict` remains current top-level authority, but it is exam-scoped today. | CURRENT SOURCE FACT |
| Existing `readiness.py` output remains advisory unless a later approved backend contract changes that relationship. | SOURCE-LOCKED for advisory score discipline; CURRENT SOURCE FACT for current seven-section shape. |
| I9-0 must introduce or extend a read-only, idempotent backend contract for the nine selected-cycle checklist steps. | I6 DECISION TO LOCK |
| This document does not invent an endpoint path, table name, RPC name, response field, override permission, override table, or completion threshold. | I6 DECISION TO LOCK |

## Nine-step activation matrix

| Step | Authority label | Current implementation scope | Proposed I9 scope | Canonical evidence source | Completion predicate / remaining decision | Base gate class | Locked deep-link source | Exact deep-link target or unresolved marker | Resume / empty / selected-cycle behavior | Progress derivation | Manual mark-complete rule |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Cycle details | UNRESOLVED — OPERATOR DECISION REQUIRED | Current activation classifier does not require a selected cycle and does not hard-gate on cycle fields. | Selected-cycle checklist should require an explicit selected `exam_cycles` row, but minimum activation fields are unresolved. | `exam_cycles` schema has `exam_id`, `year`, `cycle_name`, `status`, optional date fields. | Exact minimum field set is unresolved; do not infer mandatory fields from current-cycle normalization. | unresolved | Setup/phases example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?tab=setup` | If no valid selected cycle exists, show Setup/no-current-cycle state; final URL behavior is REBASE VERIFY. | Proposed I9 backend contract; no frontend-only completion. | Not allowed while predicate unresolved; any override policy is UNRESOLVED. |
| Phases and schedule | CURRENT SOURCE FACT plus UNRESOLVED — OPERATOR DECISION REQUIRED | Current classifier hard-gates only on exam-wide `phase_count == 0`; it does not prove a phase belongs to the selected cycle. | Selected-cycle phase/schedule requirements are proposed I9 behavior and need operator-approved predicates. | `exam_phases` rows; current aggregate reads by `exam_id`; schema supports `exam_cycle_id`. | Current exact hard predicate: exam has at least one `exam_phases` row. Selected-cycle phase count/date/status requirements are unresolved. | hard for current exam-wide no-phase blocker; unresolved for selected-cycle scheduling | Setup/phases example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?tab=setup` | Resume to Setup; template-only phases do not satisfy selected-cycle scheduling unless later approved. | Current classifier is exam-scoped; proposed I9 backend must distinguish selected-cycle phase evidence. | Not allowed for evidence-derived completion. |
| Source documents | UNRESOLVED — OPERATOR DECISION REQUIRED | Current console action treats no documents or no extracted documents as advisory needs_action; product-required document set is not locked. | I9 must define required document set, inheritance, and selected-cycle sufficiency before this step can be complete. | `document_assets`, `exam_documents`, `syllabus_documents`; human review and extraction are separate concerns. | Current source fact: document presence/extraction is advisory evidence; exact required document set is unresolved. | unresolved for product completion; advisory in current console | Documents/extraction example in design-lock §7.2 only locks failed entity-level route. | NO LOCKED ENTITY-LEVEL ROUTE — REBASE VERIFY | Empty state may point to Documents tab but must not invent document ID/status; selected-cycle inheritance is unresolved. | Proposed I9 backend contract must compute from approved document set. | Not allowed while required-set predicate is unresolved. |
| Extraction | CURRENT SOURCE FACT plus UNRESOLVED — OPERATOR DECISION REQUIRED | Current extraction status comes from latest `document_processing_jobs` per asset with `job_type = 'text_extract'`; console considers at least one extracted document advisory evidence. | I9 may require selected-cycle/inherited extraction, but the required document set and all-documents-success rule are not approved. | `document_processing_jobs.status in ('queued','running','succeeded','failed','needs_review')`, latest text_extract job per asset. | Current exact evidence: at least one extracted document is advisory done in console detail; failed/pending jobs are not source-complete. Required extraction coverage is unresolved. | advisory currently; unresolved for I9 required coverage | Failed/pending extraction example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=documents&document={document_id}&status=failed` | Resume by recomputing latest job status; failed jobs use locked failed-document route when an ID exists. | Backend-derived from latest text_extract jobs. | Not allowed; failed/pending extraction needs correction/rerun, not manual completion. |
| Syllabus mapping | CURRENT SOURCE FACT plus UNRESOLVED — OPERATOR DECISION REQUIRED | Current classifier separates hard topic coverage from advisory syllabus mentions: no locked `exam_topic_coverage` is hard, pending syllabus mentions are advisory/action evidence. Reads are exam-scoped. | I9 should present this as a hybrid syllabus area: hard locked topic coverage plus advisory syllabus mention review; selected-cycle mapping remains unresolved. | `exam_topic_coverage.reviewer_status = 'locked'` for hard coverage; `syllabus_topic_mentions.reviewer_status` for advisory mentions. | Current exact hard predicate: at least one locked `exam_topic_coverage` row by `exam_id`. Current advisory predicate: pending/needs-correction syllabus mentions require review; verified mention count is advisory. Selected-cycle coverage/mapping predicate is unresolved. | hard for locked topic coverage; advisory for mention review | Pending syllabus and topic-coverage examples in design-lock §7.2. | Mentions: `/admin/exam-intelligence/exams/{exam_id}?tab=syllabus&status=pending`; coverage: `/admin/exam-intelligence/exams/{exam_id}?tab=syllabus&status=pending_review` | Resume to Syllabus tab; label current evidence exam-scoped until I9 selected-cycle filter is approved. | Current classifier/readiness are exam-scoped here; I9 backend must separate hard coverage and advisory mentions. | Not allowed; locked coverage and review lifecycle must be resolved in source data. |
| PYQ readiness | CURRENT SOURCE FACT plus I6 DECISION TO LOCK | Current `verified_pyq_count` is exam-scoped and requires verified paper + verified question + at least one verified topic tag. Pending question/tag/option rows contribute pending-review state; options are not a verified-count gate. | I9 should propose selected-cycle PYQ readiness, but selected-cycle-only filtering must be implemented in backend and rebase-verified. | `pyq_papers.trust_status='verified'`; `pyq_questions.reviewer_status='verified'`; at least one `pyq_question_topic_tags.reviewer_status='verified'`; `pyq_options` pending/needs-correction for pending state only. | Current exact verified eligibility is the three-gate count above. Current missing verified PYQ is needs_action, not hard blocked. Selected-cycle PYQ predicate is proposed and requires I9 backend implementation. | advisory / needs_action currently | Selected PYQ paper example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=pyq&paper={paper_id}&status=pending` | Resume to PYQ tab/paper when backend supplies `paper_id`; do not inherit another cycle under proposed I9 selected-cycle policy. | Current aggregate exam-scoped; proposed I9 backend selected-cycle. | Not allowed; review rows must be verified/corrected in source data. |
| Policy updates | CURRENT SOURCE FACT plus UNRESOLVED — OPERATOR DECISION REQUIRED | Current aggregate reads `exam_policy_updates` by `exam_id`; pending/needs-correction updates create needs_action evidence. | I9 selected-cycle policy update inheritance/filtering is unresolved. | `exam_policy_updates.reviewer_status in ('pending','verified','rejected','needs_correction')`; schema includes `exam_cycle_id`. | Current exact predicate: no pending/needs-correction rows by exam means current console update check is done. Whether selected-cycle updates are required or inherited is unresolved. | advisory / needs_action currently | Pending policy updates example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?tab=updates&status=pending` | Resume to Updates tab; label current evidence exam-scoped until selected-cycle policy is approved. | Backend-derived; no frontend-only completion. | Not allowed; review lifecycle must resolve rows. |
| Competition context | CURRENT SOURCE FACT plus I6 DECISION TO LOCK | Current console `_competition()` filters by `exam_id`, accepts reviewed or locked rows, and prefers locked over reviewed; it does not filter by selected cycle. | Selected-cycle competition behavior is an I6 decision for I9-0 to implement in the selected-cycle backend contract; it must not be presented as current source-backed behavior. | `exam_competition_metrics.reviewer_status in ('reviewed','locked')`; schema includes `exam_cycle_id`. | Current exact predicate: at least one reviewed/locked competition metric by `exam_id` makes current console competition available, locked preferred. Proposed I9 predicate: selected-cycle competition evidence must come from the selected-cycle backend contract introduced/extended by I9-0; exact management-mode not_applicable policy remains operator-governed. | advisory currently; I6-selected-cycle behavior requires I9-0 implementation | Selected-cycle competition example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=competition` | Resume to Competition tab; current evidence must be labelled exam-scoped until I9 selected-cycle behavior is implemented. | Current console evidence exam-scoped; I9-0 must implement selected-cycle backend competition progress before it can be authoritative. | Not allowed; not_applicable policy requires approved machine-readable reason. |
| Review and activate | CURRENT SOURCE FACT plus REBASE VERIFY | Current `activation_verdict`, hard blockers, flags, and most action evidence are exam-scoped through `work_queue.aggregate()` and `classify_exam()`. | I9 selected-cycle review/activate must depend on the new/extended nine-step backend contract; do not label selected-cycle activation SOURCE-LOCKED yet. | `activation_verdict`, `activation_checks`, `action_queue`; current hard blockers: no exam phases, no locked topic coverage. | Current exact completion: classifier status `ready`; score percent does not authorize activation. Selected-cycle activation authority is unresolved until I9 backend contract and post-#757 route verification. | hard for current classifier verdict; unresolved for selected-cycle authority | Review/activation example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=review` | Resume to Review tab with fresh backend verdict; final route/tab behavior is REBASE VERIFY. | Current backend classifier exam-scoped; proposed I9 backend selected-cycle. | Not allowed; activation override is UNRESOLVED and must be permission-gated/audited if later approved. |

## Management-mode × cadence applicability matrix — DERIVED FROM §18.1 — REQUIRES OPERATOR APPROVAL AT REBASE

**Source limitation**

- SOURCE-LOCKED: §18.1 defines management-mode meanings: core = full readiness expected; light = essential facts and major updates; index-only = searchable reference with no deep Study OS; archive = retained with minimal active operations. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.1.
- SOURCE-LOCKED: §18.1 enumerates cadence values only: annual, recurring, irregular, one-off, unknown. It does not define cadence-specific workflow behavior. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.1.
- SOURCE-LOCKED: §18.2 leaves the full governance contract deferred. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.2.

| Management mode | Source meaning | Proposed baseline | Label |
|---|---|---|---|
| core | Full readiness expected. | All nine checklist areas remain candidates for hard/advisory gates; exact selected-cycle predicates still follow the matrix above. | DERIVED — OPERATOR APPROVAL REQUIRED |
| light | Essential facts and major updates. | Essential facts and updates remain expected; which deep evidence steps may be advisory or not_applicable is unresolved. | UNRESOLVED — OPERATOR DECISION REQUIRED |
| index_only | Searchable reference; no deep Study OS. | Deep Study OS steps may become advisory/not_applicable only after operator-approved mapping. | UNRESOLVED — OPERATOR DECISION REQUIRED |
| archive | Retained with minimal active operations. | Active-operation-heavy steps may become advisory/not_applicable only after operator-approved mapping. | UNRESOLVED — OPERATOR DECISION REQUIRED |

| Mode \ Cadence | annual | recurring | irregular | one_off | unknown |
|---|---|---|---|---|---|
| core | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. |
| light | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. |
| index_only | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. |
| archive | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. |

I6 DECISION TO LOCK: Do not infer cadence-specific not_applicable behavior from irregular, one-off, unknown, low-priority, or absent data. I9 remains blocked until the operator approves or replaces all proposed/unresolved management-mode and cadence rules.

## Resume and completion policy

| Situation | Draft behavior | Label |
|---|---|---|
| Refresh / later session | Recompute from backend evidence; no localStorage completion authority. | I6 DECISION TO LOCK |
| Browser back/forward | URL-owned exam/cycle/tab state determines view; backend still owns progress. | I6 DECISION TO LOCK; REBASE VERIFY for final PR #757 query behavior |
| Switching cycles | Recompute checklist from canonical evidence; cycle-scoped evidence must not leak across cycles. | I6 DECISION TO LOCK |
| Exam-scoped inherited evidence | May appear in selected-cycle view only when labelled `exam-scoped`. | I6 DECISION TO LOCK |
| No selected/current cycle | Show Setup/no-current-cycle state; downstream selected-cycle steps cannot be complete. | I6 DECISION TO LOCK |
| Pending extraction | Show queued/running/needs_review as incomplete until backend evidence changes. | I6 DECISION TO LOCK |
| Failed extraction | Show failed state and locked failed-document route when document ID exists. | I6 DECISION TO LOCK |
| Rejected/needs-correction review rows | Keep affected evidence incomplete/needs_action until normal review lifecycle resolves rows. | I6 DECISION TO LOCK |
| Superseded evidence | Remove completion if superseded evidence was the only supporting proof. | I6 DECISION TO LOCK |
| Backend progress unavailable | Fail closed; render unavailable/error rather than frontend-inferred completion. | I6 DECISION TO LOCK |
| Manual mark complete | Evidence-derived steps cannot be manually completed; exceptional override remains UNRESOLVED and must be permission-gated/audited if approved. | I6 DECISION TO LOCK plus UNRESOLVED — OPERATOR DECISION REQUIRED |

## Dependency and ordering contract

| Contract statement | Label |
|---|---|
| PR #757 is currently open and unmerged; do not perform or claim post-#757 rebase verification now. | REBASE VERIFY |
| PR #758 must remain draft and must not merge until corrections, rebase verification, checklist/operator approval, and I8-C sequencing requirements are satisfied. | I6 DECISION TO LOCK |
| After PR #757 merges, this branch must be rebased onto updated `main`; every route, tab ID, query parameter, deep link, current-cycle behavior, and management-data assumption must be reverified. | REBASE VERIFY |
| I8-C must complete before I9 implementation is dispatched because it still owns shared Manage Exam lane access/overflow behavior. | SOURCE-LOCKED for serial I8 ownership; REBASE VERIFY for completion. |
| No I9 runtime work may be hidden inside this docs/checklist PR. | SOURCE-LOCKED |
| No PR #756/PYQ projection behavior is treated as merged source unless it is present on the eventual rebased base. | I6 DECISION TO LOCK |

## Rebase verification checklist for the operator

After PR #757 merges and before PR #758 can leave draft, verify all of the following against merged source:

| Item | Status before verification |
|---|---|
| Canonical Manage Exam route `/admin/exam-intelligence/exams/:exam_id`. | REBASE VERIFY |
| Legacy redirect behavior. | REBASE VERIFY |
| Query parameters `tab`, `action`, `cycle`, `status`, `document`, `paper`, `row`. | REBASE VERIFY |
| Tab IDs `setup`, `documents`, `syllabus`, `pyq`, `updates`, `competition`, `review`. | REBASE VERIFY |
| Setup default tab and `action=add-cycle` behavior. | REBASE VERIFY |
| Overview removal effects. | REBASE VERIFY |
| Cycle changes preserving intended task state. | REBASE VERIFY |
| Management endpoint supplying verdict/action queue without duplicate console fetch. | REBASE VERIFY |
| Current-cycle normalization behavior. | REBASE VERIFY |
| Deep-link parameters reaching intended panels. | REBASE VERIFY |
| I8-C completed before I9 dispatch. | REBASE VERIFY |

**Approval procedure**

1. Rebase onto the commit containing merged PR #757.
2. Re-read `AGENTS.md` and Graphify artifacts.
3. Verify every REBASE VERIFY item against actual merged source.
4. Resolve every UNRESOLVED item with an explicit operator decision.
5. Approve, revise, or reject every DERIVED item.
6. Update document status from DRAFT only after all decisions are closed.
7. Keep `career-copilot-checklist.md` updated in the same branch.
8. Confirm I8-C completion before dispatching I9.
9. Keep PR #758 draft until all conditions are satisfied.

## Source index

| Source inspected | Symbols / sections used |
|---|---|
| `AGENTS.md` | Graphify-first rule; shared checklist publication requirement. |
| `graphify-out/GRAPH_REPORT.md` | Repository graph map/freshness. |
| `graphify-out/wiki/index.md` | Graph wiki entry point. |
| `docs/status/career-copilot-checklist.md` | Shared I6/I8/I9 status row. |
| `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` | §2.2–2.4, §4, §7, §10.4–10.7, §13, Appendix B. |
| `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` | §6, §18.1–§18.2, §22.2–§22.4. |
| PR #758 GitHub conversation | Review verdict and required fixes visible in PR discussion. |
| PR #758 current diff | One-file I6 document diff visible in PR files/diff context. |
| `.github/workflows/pr-body-check.yml` | PR body check invokes `node scripts/validate-pr-body.js`. |
| `scripts/validate-pr-body.js` | Required PR body sections and checked-item rule. |
| `app/backend/app/exam_intelligence/work_queue.py` | `aggregate`, `classify_exam`, hard blockers, PYQ count semantics, pending option state. |
| `app/backend/app/exam_intelligence/console_detail.py` | `build_console_detail`, `_competition`, `_deep_link`, action checks, exam-scoped verdict source. |
| `app/backend/app/exam_intelligence/readiness.py` | Seven-section readiness shape and document extraction counts. |
| `app/backend/app/exam_intelligence/management_read_model.py` | Current-cycle/read-model evidence. |
| `app/frontend/src/routes/adminRoutes.jsx` | `AddCycleRedirect`, route list, compatibility routes. |
| `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` | Setup panel cycle/phase CRUD and `action` behavior. |
| `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx` | Standalone add-cycle wizard flow evidence. |
| `app/supabase/migrations/030_exam_registry_cycles_phases.sql` | `exam_cycles`, `exam_phases`, `exam_topic_coverage`. |
| `app/supabase/migrations/031_syllabus_evidence_mapping.sql` | `syllabus_documents`, `syllabus_topic_mentions`. |
| `app/supabase/migrations/032_pyq_question_intelligence.sql` | `pyq_papers`, `pyq_questions`, `pyq_options`, `pyq_question_topic_tags`. |
| `app/supabase/migrations/055_exam_competition_metrics.sql` | `exam_competition_metrics`. |
| `app/supabase/migrations/056_exam_policy_updates.sql` | `exam_policy_updates`. |
| `app/supabase/migrations/111_document_assets.sql` | `document_assets`, `document_processing_jobs`. |
| `app/supabase/migrations/113_document_pages_text_extract.sql` | `text_extract` processing-job evidence. |
| `app/supabase/migrations/157_exam_documents.sql` | `exam_documents`. |
| `app/supabase/migrations/103_pyq_options_review.sql` | `pyq_options.reviewer_status`. |
| `app/supabase/migrations/155_pyq_questions_review_columns.sql` | `pyq_questions` review audit columns. |
