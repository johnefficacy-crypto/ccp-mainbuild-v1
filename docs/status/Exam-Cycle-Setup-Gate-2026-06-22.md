# Exam Cycle Setup Gate — I6 Design Contract

- Document type: I6 cycle-setup implementation gate
- Status: DRAFT — OPERATOR APPROVAL REQUIRED (rebase-verified against PR #757 at 385912b; all REBASE VERIFY items resolved)
- Effect: I9 remains BLOCKED until every DERIVED — PROPOSED RESOLUTION and UNRESOLVED item receives explicit operator approval, I8-C completes the shared Manage Exam lane, and this document leaves DRAFT status
- Repository scope: documentation and checklist only; no runtime, route, component, API, migration, or test change

## Purpose and non-goals

**Purpose**

- SOURCE-LOCKED: I9 remains blocked until the I6 gate document defines completion source, gate class, deep-link target, resume behavior, selected-cycle behavior, management-mode/cadence applicability, `AddCycleWizard` decision, progress derivation, and manual completion rules. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.4.
- I6 DECISION TO LOCK: This document defines the executable contract for I9 dispatch-readiness, distinguishing current source-backed implementation facts from proposed selected-cycle I9 behavior.
- REBASE COMPLETE: PR #757 merged at 385912b. All route, query-param, tab, current-cycle, and management-read-model REBASE VERIFY items have been verified against merged source. Results are recorded in each affected section and in the rebase verification checklist below.

**Non-goals**

- I6 DECISION TO LOCK: No route, component, API, backend, database migration, automated test, or runtime behavior change is authorized here.
- I6 DECISION TO LOCK: No I9 implementation, I8-C implementation, new top-level surface, checklist completion claim, or operator/live validation claim is authorized here.
- I6 DECISION TO LOCK: PR #761 must remain draft; this document does not make I6 approved, does not unblock I9, and does not authorize merging before the operator closes all DERIVED and UNRESOLVED items.
- SUPERSESSION: PR #761 supersedes PR #758. PR #758 must be closed without merge after PR #761's corrections are confirmed and all checks remain green. Do not merge both PRs; they modify the same I6 gate document and checklist.

## Source authority and decision labels

| Label | Definition |
|---|---|
| SOURCE-LOCKED | Explicitly stated in the merged findings or design-lock document. |
| CURRENT SOURCE FACT | Current local source code or migration behavior observed during this revision; not automatically a product rule. |
| I6 DECISION TO LOCK | A decision this I6 artifact proposes to lock for I9 once approved. |
| DERIVED — OPERATOR APPROVAL REQUIRED | A constrained inference from source behavior or definitions, not yet approved as product policy. |
| DERIVED — PROPOSED RESOLUTION | A specific proposed answer to a formerly UNRESOLVED item; requires operator yes/no approval before I9 implementation begins. |
| UNRESOLVED — OPERATOR DECISION REQUIRED | Source material does not define enough to decide safely; no proposed resolution is available without operator input. |
| REBASE COMPLETE | Previously labeled REBASE VERIFY; verified against merged PR #757 at 385912b; result recorded in this section. |

**Authority discipline**

- I6 DECISION TO LOCK: Current implementation facts may be documented, but code evidence alone is not a product decision.
- I6 DECISION TO LOCK: Selected-cycle activation authority is not SOURCE-LOCKED in the current merged sources. Current activation classification remains exam-scoped; selected-cycle nine-step progress is a proposed I9 backend contract.
- REBASE COMPLETE: Route, query-param, and tab behavior introduced by PR #757 has been verified against merged source at 385912b. All REBASE VERIFY labels in this document have been resolved.

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
| Hard blockers | Current classifier hard blockers are `phase_count == 0` and `locked_coverage_count == 0`; `verified_pyq_count == 0` contributes a `missing_pyq` flag and can produce `needs_action`, not `blocked`. | I9 must preserve existing hard blockers unless the operator approves a changed gate model. | CURRENT SOURCE FACT; selected-cycle hard-gate remapping is DERIVED — PROPOSED RESOLUTION (see matrix). Source: `app/backend/app/exam_intelligence/work_queue.py` `classify_exam`. |
| Action evidence | Most current classifier-owned evidence is exam-scoped because aggregate reads child rows by `exam_id`; current `cycle_id` does not filter classification. | I9 must separate current exam-scoped inherited evidence from selected-cycle evidence in the backend response. | I6 DECISION TO LOCK. |
| Readiness facts | `readiness.py` still produces seven sections: setup, documents, syllabus_mapper, pyq_workbench, updates, competition, review_activate. | I9 must not translate those seven sections into nine frontend-only steps; the backend must own nine-step progress derivation. | CURRENT SOURCE FACT plus I6 DECISION TO LOCK. Source: `app/backend/app/exam_intelligence/readiness.py` `compute_exam_workspace_readiness`. |
| Activation score | Readiness score percentages are advisory and must not authorize activation. | I9 checklist may display backend progress but must not replace `classify_exam` activation authority without an explicit operator-approved contract. | SOURCE-LOCKED for score discipline. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §4.2. |

## AddCycleWizard decision

| Decision / evidence | Label | Source |
|---|---|---|
| Canonical Manage Exam route is `/admin/exam-intelligence/exams/:exam_id`. `AddCycleRedirect` (adminRoutes.jsx:53–59) navigates to `?tab=setup&action=add-cycle` when the `/exams/:exam_id/add-cycle` compatibility route is used. | REBASE COMPLETE — CURRENT SOURCE FACT | `app/frontend/src/routes/adminRoutes.jsx` lines 53–59, 107. |
| `SetupPanel` receives `action` prop (ExamWorkspace.jsx:384: `<SetupPanel action={action} />`); when `action === "add-cycle"`, the create-cycle form opens automatically (SetupPanel.jsx:112–118). | REBASE COMPLETE — CURRENT SOURCE FACT | `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:327,384`; `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx:112–118`. |
| Inline destination combines canonical Manage Exam with `?tab=setup&action=add-cycle`. | SOURCE-LOCKED for Appendix B target shape; REBASE COMPLETE — confirmed in merged source. | `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` Appendix B; adminRoutes.jsx:57. |
| Reuse or extract validation, duplicate-cycle detection, template-phase selection, phase-slug generation, and review-summary logic from `AddCycleWizard.jsx`; do not mount the standalone component unchanged. | I6 DECISION TO LOCK | `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx`; `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx`. |
| Implement the bounded Cycle → Phases → Review & Create flow inside Manage Exam → Setup, with `SetupPanel.jsx` as operational owner. | I6 DECISION TO LOCK; REBASE COMPLETE — tab/action handling confirmed. | Findings §6.2; design-lock Appendix B; SetupPanel.jsx. |
| Retain `AddCycleWizard.jsx` until I9 replacement behavior and compatibility tests pass; retire any standalone dead component only in later cleanup. | I6 DECISION TO LOCK | Design-lock §2.4 and §10.7 compatibility/cleanup sequence. |
| Existing `SetupPanel.jsx` opens the current cycle form when `action=add-cycle`, but it does not already implement the bounded three-step mini-wizard. | CURRENT SOURCE FACT | `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx:112–118`. |

## Progress authority

| Rule | Label |
|---|---|
| I9 progress must be backend-derived and recomputable from canonical evidence. | I6 DECISION TO LOCK |
| Frontend may render progress but must not infer permanent completion, activation authority, or selected-cycle gate state independently. | I6 DECISION TO LOCK |
| Existing `activation_verdict` remains current top-level authority, but it is exam-scoped today. | CURRENT SOURCE FACT |
| Existing `readiness.py` output remains advisory unless a later approved backend contract changes that relationship. | SOURCE-LOCKED for advisory score discipline; CURRENT SOURCE FACT for current seven-section shape. |
| I9-0 must introduce or extend a read-only, idempotent backend contract for the nine selected-cycle checklist steps. | I6 DECISION TO LOCK |
| Field names, endpoint paths, table names, RPC names, override permissions, override tables, and completion thresholds proposed in this document are labeled DERIVED — OPERATOR APPROVAL REQUIRED and must not be implemented until the operator approves them. | I6 DECISION TO LOCK |

## I9 backend contract proposal

**Purpose of this section:** Propose the shape of the backend contract I9-0 must introduce or extend. All items in this section are DERIVED — OPERATOR APPROVAL REQUIRED and must not be implemented until the operator approves each item explicitly.

**Proposed extension point:** The existing `GET /api/admin/exam-intelligence/management/exams/{exam_id}` endpoint (implemented in `management_read_model.get_management_exam_detail`) already accepts a `cycle_id` query parameter and returns `current_cycle`, `cycles`, `activation_verdict`, `action_queue`, and `section_readiness`. I9-0 should extend this response with a `cycle_readiness` field rather than introducing a separate endpoint.

| Proposal item | Proposed value | Label |
|---|---|---|
| Extension point | Add `cycle_readiness` field to `GET /management/exams/{exam_id}?cycle_id={id}` response | DERIVED — OPERATOR APPROVAL REQUIRED |
| Top-level field name | `cycle_readiness` | DERIVED — OPERATOR APPROVAL REQUIRED |
| `cycle_readiness.cycle_id` | Selected cycle UUID or `null` if no cycle is selected | DERIVED — OPERATOR APPROVAL REQUIRED |
| `cycle_readiness.computed_at` | ISO-8601 timestamp at which this field was computed | DERIVED — OPERATOR APPROVAL REQUIRED |
| `cycle_readiness.steps` | Ordered array of nine step objects (one per checklist area) | DERIVED — OPERATOR APPROVAL REQUIRED |

**Proposed step object shape:**

| Field | Type | Proposed meaning |
|---|---|---|
| `step_id` | string enum | One of: `cycle_details`, `phases_schedule`, `source_documents`, `extraction`, `syllabus_mapping`, `pyq_readiness`, `policy_updates`, `competition_context`, `review_activate` |
| `label` | string | Human-readable step name |
| `status` | string enum | One of: `complete`, `incomplete`, `needs_action`, `not_applicable`, `blocked` |
| `gate_class` | string enum | `hard` (must be `complete` before activation) or `advisory` (should be complete; does not hard-block) |
| `evidence_scope` | string enum | `selected_cycle` (evidence filtered to chosen cycle) or `exam_wide` (no cycle filter available in current schema) |
| `action_cta` | object or null | `{ "label": string, "url": string }` pointing to the deep-link target for this step's corrective action; null when no specific action is needed or available |
| `note` | string or null | Operator-readable explanation of current status; null when not needed |

All field names in the step object are DERIVED — OPERATOR APPROVAL REQUIRED.

**Proposed status vocabulary:**

| Status value | Meaning |
|---|---|
| `complete` | Evidence passes all predicates for this step; no corrective action needed |
| `incomplete` | Step has not yet been started or is in progress but not blocked |
| `needs_action` | Specific correctable problem found (e.g., failed extraction job, pending review row) |
| `not_applicable` | Operator-approved N/A for this exam's management_mode; does not block activation |
| `blocked` | A preceding hard-gate step is not `complete`; this step cannot be meaningfully evaluated |

Status vocabulary is DERIVED — OPERATOR APPROVAL REQUIRED.

**Proposed `not_applicable` trigger rules:**

| Step | Proposed trigger for `not_applicable` | Label |
|---|---|---|
| `source_documents` | `management_mode in ('index_only', 'archive')` AND no documents exist | DERIVED — OPERATOR APPROVAL REQUIRED |
| `extraction` | `management_mode in ('index_only', 'archive')` AND `source_documents` is `not_applicable` | DERIVED — OPERATOR APPROVAL REQUIRED |
| `syllabus_mapping` | `management_mode in ('index_only', 'archive')` | DERIVED — OPERATOR APPROVAL REQUIRED |
| `pyq_readiness` | `management_mode in ('index_only', 'archive')` | DERIVED — OPERATOR APPROVAL REQUIRED |
| `competition_context` | `management_mode in ('light', 'index_only', 'archive')` AND no `reviewed`/`locked` competition rows exist for exam | DERIVED — OPERATOR APPROVAL REQUIRED |

All `not_applicable` trigger rules are DERIVED — OPERATOR APPROVAL REQUIRED and must not be implemented until the operator approves them.

**Fail-closed rule:** If the backend cannot compute `cycle_readiness` (database error, missing exam, missing cycle), the field must be omitted from the response or returned as `null` rather than returned with guessed step statuses. The frontend must render an `unavailable` state for all steps rather than inferring completion from local state.

## Nine-step activation matrix

| Step | Authority label | Current implementation scope | Proposed I9 scope | Canonical evidence source | Completion predicate | Base gate class | Deep-link target | Resume / empty / selected-cycle behavior | Progress derivation | Manual mark-complete rule |
|---|---|---|---|---|---|---|---|---|---|---|
| Cycle details | DERIVED — PROPOSED RESOLUTION | Current activation classifier does not require a selected cycle and does not hard-gate on cycle fields. | Selected-cycle checklist requires an explicit selected `exam_cycles` row. | `exam_cycles` schema: `exam_id`, `year`, `cycle_name`, `status`, optional date fields. | DERIVED — PROPOSED: `cycle_name` (non-empty) and `year` (non-null integer) present on selected `exam_cycles` row; `status` defaults to `expected`; date fields advisory. SetupPanel.jsx:220 enforces `cycle_name.trim()` and `year` at creation. OPERATOR APPROVAL REQUIRED. | hard | `/admin/exam-intelligence/exams/{exam_id}?tab=setup` | If no valid selected cycle exists, show Setup/no-current-cycle state; `cycle_id` normalization uses `management_read_model.select_current_cycle` (priority: active > open > expected > highest year > lowest UUID). REBASE COMPLETE. | Proposed `cycle_readiness` backend contract; no frontend-only completion. | Not allowed; any override policy is UNRESOLVED — OPERATOR DECISION REQUIRED. |
| Phases and schedule | DERIVED — PROPOSED RESOLUTION | Current classifier hard-gates only on exam-wide `phase_count == 0`; it does not prove a phase belongs to the selected cycle. | Selected-cycle phase requirement: at least one phase belonging to the selected cycle. | `exam_phases` rows; `exam_phases.exam_cycle_id` column supports per-cycle filtering. `management_read_model._load_phases_for_cycles` filters by `exam_cycle_id`. | DERIVED — PROPOSED: at least one `exam_phases` row with `exam_cycle_id = selected_cycle.id`; date/status requirements for scheduling are advisory; OPERATOR APPROVAL REQUIRED. | hard | `/admin/exam-intelligence/exams/{exam_id}?tab=setup` | Resume to Setup; template-only phases (where `exam_cycle_id IS NULL`) do not satisfy selected-cycle gate. REBASE COMPLETE: Setup tab confirmed. | Proposed `cycle_readiness` backend; distinguish selected-cycle phases from exam-wide template phases using `exam_cycle_id` filter. | Not allowed for evidence-derived completion. |
| Source documents | UNRESOLVED — OPERATOR DECISION REQUIRED | Current console action treats no documents or no extracted documents as advisory `needs_action`; product-required document set is not locked. | I9 must define required document set, inheritance, and selected-cycle sufficiency before this step can be complete. | `document_assets`, `exam_documents`, `syllabus_documents`; human review and extraction are separate concerns. | Exact required document set is UNRESOLVED — OPERATOR DECISION REQUIRED. No proposed resolution is safe without operator definition of which document types are required per exam/management_mode. | unresolved | `/admin/exam-intelligence/exams/{exam_id}?tab=documents` (REBASE COMPLETE: `documents` tab confirmed) | Empty state points to Documents tab; selected-cycle document inheritance from exam-wide pool is UNRESOLVED. | Proposed `cycle_readiness` backend contract must compute from operator-approved document set definition. | Not allowed while required-set predicate is UNRESOLVED. |
| Extraction | DERIVED — PROPOSED RESOLUTION | Current extraction status comes from latest `document_processing_jobs` per asset with `job_type = 'text_extract'`; console considers at least one extracted document advisory evidence. | Advisory step: failed/pending extraction jobs are `needs_action`; all-documents-success threshold is not approved. | `document_processing_jobs.status in ('queued','running','succeeded','failed','needs_review')`, latest text_extract job per asset. Source: `readiness.py` `load_doc_extraction_counts`. | DERIVED — PROPOSED: advisory; at least one `succeeded` `text_extract` job → step is `complete`; any `failed` or `needs_review` job → `needs_action`; `queued`/`running` → `incomplete`; all-documents-success threshold is UNRESOLVED — OPERATOR DECISION REQUIRED. | advisory | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=documents&document={document_id}&status=failed` | Resume by recomputing latest job status; failed jobs use locked deep-link with document ID when known. REBASE COMPLETE: `documents` tab and `document`/`status` params confirmed. | Backend-derived from latest text_extract jobs; no frontend-only completion. | Not allowed; failed/pending extraction needs correction/rerun, not manual completion. |
| Syllabus mapping | DERIVED — PROPOSED RESOLUTION | Current classifier separates hard topic coverage (`locked_coverage_count`) from advisory syllabus mentions (`pending` review). Reads are exam-scoped. | Hybrid: hard locked topic coverage (exam-wide, current schema) plus advisory syllabus mention review. | `exam_topic_coverage.reviewer_status = 'locked'` for hard gate; `syllabus_topic_mentions.reviewer_status` for advisory mentions. | DERIVED — PROPOSED: hard gate uses exam-wide `locked_coverage_count > 0` (no `exam_cycle_id` column on `exam_topic_coverage`; selected-cycle filter deferred to schema extension); advisory: no pending/needs-correction syllabus mention rows; OPERATOR APPROVAL REQUIRED. | hard (exam-wide coverage); advisory (mention review) | Mentions: `/admin/exam-intelligence/exams/{exam_id}?tab=syllabus&status=pending`; coverage: `/admin/exam-intelligence/exams/{exam_id}?tab=syllabus&status=pending_review` REBASE COMPLETE: `syllabus` tab confirmed. | Resume to Syllabus tab; evidence is exam-scoped until selected-cycle schema extension; label `evidence_scope: 'exam_wide'` in backend response. | Backend-derived from classifier/readiness; exam-scoped until schema supports per-cycle coverage. | Not allowed; locked coverage and review lifecycle must be resolved in source data. |
| PYQ readiness | DERIVED — PROPOSED RESOLUTION | Current `verified_pyq_count` is exam-scoped: verified paper + verified question + at least one verified topic tag. Pending question/tag/option rows contribute advisory `needs_action`. | Advisory; exam-wide PYQ evidence (no `exam_cycle_id` on `pyq_papers` schema). | `pyq_papers.trust_status='verified'`; `pyq_questions.reviewer_status='verified'`; at least one `pyq_question_topic_tags.reviewer_status='verified'`; `pyq_options` pending/needs-correction for pending state only. | DERIVED — PROPOSED: advisory; exam-wide `verified_pyq_count > 0` satisfies step (three-gate preserved); `verified_pyq_count == 0` → `needs_action`; pending question/tag/option rows → `needs_action`; selected-cycle filter deferred until schema adds `exam_cycle_id` to `pyq_papers`; label `evidence_scope: 'exam_wide'`; OPERATOR APPROVAL REQUIRED. | advisory | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=pyq&paper={paper_id}&status=pending` REBASE COMPLETE: `pyq` tab, `paper`/`status` params confirmed. | Resume to PYQ tab/paper when backend supplies `paper_id`; evidence is exam-scoped until schema extension. | Backend-derived from exam-scoped aggregate; `evidence_scope: 'exam_wide'` in response. | Not allowed; review rows must be verified/corrected in source data. |
| Policy updates | DERIVED — PROPOSED RESOLUTION | Current aggregate reads `exam_policy_updates` by `exam_id`; pending/needs-correction updates create advisory `needs_action`. | Include both exam-wide and selected-cycle policy updates using `exam_cycle_id` column that exists in schema. | `exam_policy_updates.reviewer_status in ('pending','verified','rejected','needs_correction')`; `exam_policy_updates.exam_cycle_id` column exists (migration 056). | DERIVED — PROPOSED: advisory; include updates where `exam_id = selected_exam.id AND (exam_cycle_id = selected_cycle.id OR exam_cycle_id IS NULL)`; no pending/needs-correction rows → `complete`; any pending/needs-correction → `needs_action`; OPERATOR APPROVAL REQUIRED for inheritance rule. | advisory | `/admin/exam-intelligence/exams/{exam_id}?tab=updates&status=pending` REBASE COMPLETE: `updates` tab confirmed. | Resume to Updates tab; label `evidence_scope: 'selected_cycle'` when filtered, `evidence_scope: 'exam_wide'` for unscoped rows. | Backend-derived; no frontend-only completion. | Not allowed; review lifecycle must resolve rows. |
| Competition context | DERIVED — PROPOSED RESOLUTION | Current `_competition()` filters by `exam_id`, accepts `reviewed`/`locked` rows, prefers `locked`; does not filter by selected cycle. `exam_competition_metrics.exam_cycle_id` column exists (migration 055). | Advisory for `core` exams; `not_applicable` for other management modes when no competition rows exist. | `exam_competition_metrics.reviewer_status in ('reviewed','locked')`; `exam_competition_metrics.exam_cycle_id` column available. | DERIVED — PROPOSED: advisory for `management_mode = 'core'`; at least one `reviewed`/`locked` row by `exam_id` → `complete` (exam-wide, label `evidence_scope: 'exam_wide'`); selected-cycle filter from `exam_cycle_id` available but preferred behavior deferred to I9-0; for `management_mode in ('light', 'index_only', 'archive')`, `not_applicable` when no rows exist; OPERATOR APPROVAL REQUIRED for `not_applicable` rules. | advisory | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=competition` REBASE COMPLETE: `competition` tab confirmed. | Resume to Competition tab; evidence exam-scoped until I9-0 selected-cycle filter is implemented. | Not allowed; `not_applicable` requires operator-approved machine-readable reason in backend response. |
| Review and activate | DERIVED — PROPOSED RESOLUTION | Current `activation_verdict`, hard blockers, flags, and most action evidence are exam-scoped through `work_queue.aggregate()` and `classify_exam()`. Backend returns `activation_verdict` in `management_read_model.get_management_exam_detail`. | Selected-cycle review/activate depends on the nine-step `cycle_readiness` contract; `activation_verdict` remains the authority for the actual activation gate. | `activation_verdict`, `activation_checks`, `action_queue`; current hard blockers: no exam phases, no locked topic coverage. `management_read_model.get_management_exam_detail` already returns these fields. | DERIVED — PROPOSED: step is `complete` when (a) all `hard` steps in `cycle_readiness.steps` are `complete` AND (b) `activation_verdict.status = 'ready'`; score percentage does not authorize activation; OPERATOR APPROVAL REQUIRED. | hard | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=review` REBASE COMPLETE: `review` tab confirmed. | Resume to Review tab with fresh backend verdict; `cycle_id` param preserved on cycle change. | Backend classifier exam-scoped; proposed `cycle_readiness` adds selected-cycle view of hard-gate completion; actual activation authority remains `classify_exam`. | Not allowed; activation override is UNRESOLVED — OPERATOR DECISION REQUIRED and must be permission-gated/audited if later approved. |

## Management-mode × cadence applicability matrix — DERIVED FROM §18.1 — REQUIRES OPERATOR APPROVAL

**Source limitation**

- SOURCE-LOCKED: §18.1 defines management-mode meanings: core = full readiness expected; light = essential facts and major updates; index-only = searchable reference with no deep Study OS; archive = retained with minimal active operations. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.1.
- SOURCE-LOCKED: §18.1 enumerates cadence values only: annual, recurring, irregular, one-off, unknown. It does not define cadence-specific workflow behavior. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.1.
- SOURCE-LOCKED: §18.2 leaves the full governance contract deferred. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.2.

| Management mode | Source meaning | Proposed baseline | Label |
|---|---|---|---|
| core | Full readiness expected. | All nine checklist areas remain candidates for hard/advisory gates; exact selected-cycle predicates follow the matrix above. | DERIVED — OPERATOR APPROVAL REQUIRED |
| light | Essential facts and major updates. | `cycle_details`, `phases_schedule`, `policy_updates`, `review_activate` remain active; `source_documents`, `extraction`, `syllabus_mapping`, `pyq_readiness` advisory; `competition_context` `not_applicable` when no rows exist. | DERIVED — OPERATOR APPROVAL REQUIRED |
| index_only | Searchable reference; no deep Study OS. | `cycle_details`, `phases_schedule`, `review_activate` remain active; `source_documents`, `extraction`, `syllabus_mapping`, `pyq_readiness`, `competition_context` `not_applicable`; `policy_updates` advisory. | DERIVED — OPERATOR APPROVAL REQUIRED |
| archive | Retained with minimal active operations. | Same proposed baseline as `index_only`; all deep Study OS steps `not_applicable`. | DERIVED — OPERATOR APPROVAL REQUIRED |

| Mode \ Cadence | annual | recurring | irregular | one_off | unknown |
|---|---|---|---|---|---|
| core | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. | DERIVED — no cadence modifier in §18.1; inherits proposed core baseline only. |
| light | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved light baseline only. |
| index_only | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved index_only baseline only. |
| archive | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. | DERIVED — no cadence modifier in §18.1; inherits unresolved archive baseline only. |

I6 DECISION TO LOCK: Do not infer cadence-specific `not_applicable` behavior from irregular, one-off, unknown, low-priority, or absent data. I9 remains blocked until the operator approves or replaces all proposed/unresolved management-mode and cadence rules.

## Resume and completion policy

| Situation | Behavior | Label |
|---|---|---|
| Refresh / later session | Recompute from backend `cycle_readiness`; no localStorage completion authority. | I6 DECISION TO LOCK |
| Browser back/forward | URL-owned `exam_id`/`cycle`/`tab` state determines view; backend still owns progress. `?cycle=` param preserved through tab navigation. | I6 DECISION TO LOCK; REBASE COMPLETE: cycle-param preservation confirmed in ExamWorkspace.jsx:63–76. |
| Switching cycles | Recompute `cycle_readiness` from canonical evidence for the new cycle; previous-cycle evidence must not leak. | I6 DECISION TO LOCK; REBASE COMPLETE: ExamWorkspace.jsx cycle-change handler drops `document`/`paper`/`row` but preserves `tab`. |
| Exam-scoped inherited evidence | May appear in selected-cycle view only when labelled `evidence_scope: 'exam_wide'` in backend response. | I6 DECISION TO LOCK |
| No selected/current cycle | Show Setup/no-current-cycle state; all downstream selected-cycle steps show `blocked`; `select_current_cycle` normalization uses priority order (active > open > expected > highest year > lowest UUID). | I6 DECISION TO LOCK; REBASE COMPLETE. |
| Pending extraction | Show `queued`/`running`/`needs_review` as `incomplete` until backend evidence changes. | I6 DECISION TO LOCK |
| Failed extraction | Show `needs_action` with locked failed-document route when document ID is available. | I6 DECISION TO LOCK |
| Rejected/needs-correction review rows | Keep affected evidence `incomplete`/`needs_action` until normal review lifecycle resolves rows. | I6 DECISION TO LOCK |
| Superseded evidence | Remove completion if superseded evidence was the only supporting proof. | I6 DECISION TO LOCK |
| Backend progress unavailable | Fail closed; omit `cycle_readiness` or return it as `null`; frontend renders `unavailable` for all steps rather than frontend-inferred completion. | I6 DECISION TO LOCK |
| Manual mark complete | Evidence-derived steps cannot be manually completed; exceptional override is UNRESOLVED — OPERATOR DECISION REQUIRED and must be permission-gated/audited if ever approved. | I6 DECISION TO LOCK plus UNRESOLVED — OPERATOR DECISION REQUIRED |

## Acceptance scenarios

These scenarios define I9 "done" for the operator. All scenarios are DERIVED — OPERATOR APPROVAL REQUIRED and must not be treated as implemented or tested until I9 ships.

| Scenario | ID | Precondition | Expected backend `cycle_readiness` outcome | Expected frontend behavior |
|---|---|---|---|---|
| No cycle selected | A1 | Exam exists; no `exam_cycles` rows exist or no `?cycle=` and `select_current_cycle` returns `null`. | `cycle_details.status = 'incomplete'`; all other steps `status = 'blocked'`; `cycle_details.action_cta` points to `?tab=setup`. | Checklist shows "Cycle details — incomplete" with Setup CTA; all downstream steps show "blocked — create a cycle first". |
| Cycle created, no phases | A2 | `exam_cycles` row exists with `cycle_name` and `year`; no `exam_phases` row with `exam_cycle_id = selected_cycle.id`. | `cycle_details.status = 'complete'`; `phases_schedule.status = 'blocked'` (hard gate not met); all downstream steps `status = 'blocked'`. | Checklist shows "Cycle details — complete"; "Phases and schedule — blocked" with Setup CTA; all downstream blocked. |
| Phase added to selected cycle | A3 | At least one `exam_phases` row with `exam_cycle_id = selected_cycle.id`. | `cycle_details.status = 'complete'`; `phases_schedule.status = 'complete'`; downstream steps become `incomplete` (no longer `blocked`). | Checklist unlocks downstream steps as `incomplete`; admin can begin working on documents, syllabus, PYQ, etc. |
| Full readiness | A4 | All nine evidence predicates met; `activation_verdict.status = 'ready'`. | All steps `status = 'complete'`; `review_activate.status = 'complete'`. | Checklist shows all nine steps complete; Review & Activate CTA enabled. |
| Resume after refresh | A5 | Admin partially completes steps, refreshes browser (same URL, same `?cycle=`). | Backend recomputes `cycle_readiness` from evidence; returns same step statuses as before refresh. | No step status changes on refresh; localStorage is not consulted; checklist state matches backend. |
| Cycle switch | A6 | Admin changes `?cycle=` param to a different cycle with different evidence. | Backend computes `cycle_readiness` for the newly selected cycle; evidence from previous cycle does not appear. | Checklist fully recomputes; previous-cycle completed steps are not carried over; `evidence_scope` labels reflect the new cycle. |
| Backend unavailable | A7 | Management endpoint returns 5xx or `cycle_readiness` is `null`. | `cycle_readiness` is omitted or `null`. | Frontend renders all steps as `unavailable`; no steps shown as complete; no steps shown as `incomplete` that were previously shown as `complete`. |
| Failed extraction | A8 | At least one `document_processing_jobs` row with `job_type = 'text_extract'` and `status = 'failed'`. | `extraction.status = 'needs_action'`; `action_cta.url = '/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=documents&document={document_id}&status=failed'` when document ID known. | Extraction step shows "needs action" with CTA to the failed document page. |
| index_only exam | A9 | Exam has `management_mode = 'index_only'`; operator has approved `not_applicable` rules for this mode. | `source_documents.status = 'not_applicable'`; `extraction.status = 'not_applicable'`; `syllabus_mapping.status = 'not_applicable'`; `pyq_readiness.status = 'not_applicable'`; `competition_context.status = 'not_applicable'`; `cycle_details`, `phases_schedule`, `policy_updates`, `review_activate` remain active. | Checklist shows five steps as "not applicable"; remaining four active steps follow normal completion rules. |

## Dependency and ordering contract

| Contract statement | Label |
|---|---|
| PR #757 merged at 385912b; post-#757 rebase verification is complete. | REBASE COMPLETE |
| PR #761 must remain draft and must not merge until operator approval of all DERIVED and UNRESOLVED items and I8-C sequencing requirements are satisfied. PR #758 must be closed without merge as superseded. | I6 DECISION TO LOCK |
| I8-C (Advanced Repair isolation) is IN PROGRESS — PR #759; I8-C must complete before I9 implementation is dispatched because it still owns shared Manage Exam lane access/overflow behavior. | SOURCE-LOCKED for serial I8 ownership; I8-C implementation active in PR #759. |
| No I9 runtime work may be hidden inside this docs/checklist PR. | SOURCE-LOCKED |
| No PR #756/PYQ projection behavior is treated as merged source unless it is present on the eventual rebased base. | I6 DECISION TO LOCK |

## Rebase verification checklist — completed against PR #757 at 385912b

| Item | Verification result | Source evidence |
|---|---|---|
| Canonical Manage Exam route `/admin/exam-intelligence/exams/:exam_id`. | VERIFIED | `app/frontend/src/routes/adminRoutes.jsx:106` — Route path confirmed. |
| Legacy redirect behavior. | VERIFIED | adminRoutes.jsx:62–66 (`ExamRedirect`); lines 103 (`console/:exam_id`), 109–110 (`workspace/:exam_id`, `workspace/:exam_id/:cycle_id`) all redirect to canonical route. |
| Query parameters `tab`, `action`, `cycle`, `status`, `document`, `paper`, `row`. | VERIFIED | `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:327–331` — all seven params read from `searchParams`. |
| Tab IDs `setup`, `documents`, `syllabus`, `pyq`, `updates`, `competition`, `review`. | VERIFIED | ExamWorkspace.jsx:40–46 — `TAB_ORDER` array defines exactly these seven IDs. |
| Setup default tab and `action=add-cycle` behavior. | VERIFIED | ExamWorkspace.jsx:323–325 — defaults to `"setup"` when `?tab=` absent; SetupPanel.jsx:112–118 — auto-opens create-cycle form when `action === "add-cycle"`. |
| Overview removal effects. | VERIFIED | CL-6/CL-6b completed (checklist); `ExamWorkspace` no longer branches on `variant="console"`; `ExamTaskRail` deleted. |
| Cycle changes preserving intended task state. | VERIFIED | ExamWorkspace.jsx:63–76 — cycle-change handler preserves `tab`, `status`, `action`; drops `document`, `paper`, `row`. |
| Management endpoint supplying verdict/action queue without duplicate console fetch. | VERIFIED | `management_read_model.get_management_exam_detail` (lines 292–319) returns `activation_verdict`, `action_queue`, `activation_checks`, `stages`, `evidence_refs` from single `build_console_detail` call at line 290; single fetch path. |
| Current-cycle normalization behavior. | VERIFIED | Backend: `work_queue.select_current_cycle` (work_queue.py:415–432) priority: active > open > expected > highest year > lowest UUID. Frontend: ExamWorkspace.jsx:343–350 normalizes `?cycle=` from `mgmt.current_cycle.id` only on first load (guard: `if (searchParams.get("cycle")) return`). |
| Deep-link parameters reaching intended panels. | VERIFIED | ExamWorkspace.jsx:328–331 reads `status`, `documentId`, `paperId`, `rowId` from `searchParams` and passes to panels via props. |
| I8-C completed before I9 dispatch. | NOT YET — I8-C IN PROGRESS (PR #759) | PR #757 merged; I8-C active in PR #759. I9 dispatch remains blocked on I8-C merge. |

## Source index

| Source inspected | Symbols / sections used |
|---|---|
| `AGENTS.md` | Graphify-first rule; shared checklist publication requirement. |
| `graphify-out/GRAPH_REPORT.md` | Repository graph map/freshness. |
| `graphify-out/wiki/index.md` | Graph wiki entry point. |
| `docs/status/career-copilot-checklist.md` | Shared I6/I8/I9 status row. |
| `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` | §2.2–2.4, §4, §7, §10.4–10.7, §13, Appendix B. |
| `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` | §6, §18.1–§18.2, §22.2–§22.4. |
| `.github/workflows/pr-body-check.yml` | PR body check invokes `node scripts/validate-pr-body.js`. |
| `scripts/validate-pr-body.js` | Required PR body sections and checked-item rule. |
| `app/backend/app/exam_intelligence/work_queue.py` | `aggregate`, `classify_exam`, `select_current_cycle` (lines 415–432), hard blockers, PYQ count semantics, pending option state. |
| `app/backend/app/exam_intelligence/console_detail.py` | `build_console_detail`, `_competition`, `_deep_link`, action checks, exam-scoped verdict source. |
| `app/backend/app/exam_intelligence/readiness.py` | Seven-section readiness shape and document extraction counts (`load_doc_extraction_counts`). |
| `app/backend/app/exam_intelligence/management_read_model.py` | `get_management_exam_detail` (lines 231–319): `current_cycle`, `activation_verdict`, `action_queue`, `section_readiness`; `select_current_cycle` delegation; `_load_phases_for_cycles` per-cycle phase evidence. |
| `app/frontend/src/routes/adminRoutes.jsx` | `AddCycleRedirect` (lines 53–59), `ExamRedirect` (lines 62–66), route list (lines 103–110), compat redirects. |
| `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx` | `TAB_ORDER` (lines 40–46), `searchParams` reading (lines 327–331), cycle-change handler (lines 63–76), cycle normalization (lines 343–350), default tab (lines 323–325), `SetupPanel` action prop (line 384). |
| `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` | `action` prop handling (lines 65, 112–118); cycle creation validation (line 220); `exam_cycle_id` for template vs. cycle phases (line 127). |
| `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx` | Standalone add-cycle wizard flow evidence. |
| `app/supabase/migrations/030_exam_registry_cycles_phases.sql` | `exam_cycles`, `exam_phases` (`exam_cycle_id` column), `exam_topic_coverage`. |
| `app/supabase/migrations/031_syllabus_evidence_mapping.sql` | `syllabus_documents`, `syllabus_topic_mentions`. |
| `app/supabase/migrations/032_pyq_question_intelligence.sql` | `pyq_papers`, `pyq_questions`, `pyq_options`, `pyq_question_topic_tags`. |
| `app/supabase/migrations/055_exam_competition_metrics.sql` | `exam_competition_metrics` (`exam_cycle_id` column). |
| `app/supabase/migrations/056_exam_policy_updates.sql` | `exam_policy_updates` (`exam_cycle_id` column). |
| `app/supabase/migrations/111_document_assets.sql` | `document_assets`, `document_processing_jobs`. |
| `app/supabase/migrations/113_document_pages_text_extract.sql` | `text_extract` processing-job evidence. |
| `app/supabase/migrations/157_exam_documents.sql` | `exam_documents`. |
| `app/supabase/migrations/103_pyq_options_review.sql` | `pyq_options.reviewer_status`. |
| `app/supabase/migrations/155_pyq_questions_review_columns.sql` | `pyq_questions` review audit columns. |
