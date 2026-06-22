# Exam Cycle Setup Gate — I6 Design Contract

- Document type: I6 cycle-setup implementation gate
- Status: DRAFT — OPERATOR APPROVAL AND POST-#757 REBASE VERIFICATION REQUIRED
- Effect: I9 remains BLOCKED until every unresolved/derived item is approved
- Repository scope: documentation only

## Purpose and non-goals

**Purpose**

- I6 DECISION TO LOCK: Define the executable contract needed to make I9 dispatch-ready without implementing I9.
- I6 DECISION TO LOCK: Distinguish source-locked rules, new I6 decisions, derived proposals, unresolved decisions, and post-#757 verification items before any runtime work begins.
- SOURCE-LOCKED: I9 implementation remains blocked on this gate document. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.4.

**Non-goals**

- I6 DECISION TO LOCK: No route change.
- I6 DECISION TO LOCK: No component change.
- I6 DECISION TO LOCK: No API or backend implementation.
- I6 DECISION TO LOCK: No database migration.
- I6 DECISION TO LOCK: No test change.
- I6 DECISION TO LOCK: No runtime behavior change.
- I6 DECISION TO LOCK: No checklist or `docs/status/agents.md` change in this agent commit.
- I6 DECISION TO LOCK: No I9 implementation.
- SOURCE-LOCKED: No I8-C implementation is authorized by this document. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §13.
- SOURCE-LOCKED: No new top-level surface is introduced; guided cycle setup remains inside Manage Exam, not a new route/sidebar destination. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §2.2, §13, Appendix B.
- REBASE VERIFY: This one-file commit is not publication-ready until the operator rebases after merged PR #757, verifies the final route/component behavior, and performs the checklist update required by `AGENTS.md` in a separate operator commit on the same branch. Source: `AGENTS.md` §Shared checklist status.

## Source authority and decision labels

**Authority labels used in this contract**

| Label | Definition |
|---|---|
| SOURCE-LOCKED | Explicitly stated in the merged findings or design-lock document. |
| I6 DECISION TO LOCK | A decision this I6 artifact is intentionally introducing. |
| DERIVED — OPERATOR APPROVAL REQUIRED | A constrained inference from an existing definition, not yet approved. |
| UNRESOLVED — OPERATOR DECISION REQUIRED | The source material does not define enough to decide safely. |
| REBASE VERIFY | Depends on the final merged PR #757 implementation. |

**Authoritative source sections used**

| Source | Sections / symbols used |
|---|---|
| `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` | §2.2–2.4 canonical routes and redirect sequence; §4 readiness authority; §7 blocker-to-editor deep-link contract; §10.4–10.7 I8-B/I8-C/redirect/cleanup sequence; §13 non-authorized work; Appendix B resolved decisions. |
| `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` | §6 guided cycle setup architecture and I9 gate; §18.1 existing management-mode/cadence definitions; §18.2 deferred governance contract; §22.2–22.4 gate and serial IA sequencing. |
| `app/frontend/src/routes/adminRoutes.jsx` | `AddCycleRedirect`, canonical redirect target currently emitted by the local branch, and existing route ownership evidence. |
| `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` | Current Setup ownership of cycle/phase CRUD and `action="add-cycle"` behavior. |
| `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx` | Existing standalone three-step cycle flow and route-bound state/navigation evidence. |
| `app/backend/app/exam_intelligence/management_read_model.py` | Current management read-model authority and selected/current-cycle normalization evidence. |
| `app/backend/app/exam_intelligence/readiness.py` | Current seven-section workspace readiness evidence and section scoping mismatch. |
| `app/backend/app/exam_intelligence/work_queue.py` | `classify_exam` activation verdict source and aggregate evidence. |
| `app/backend/app/exam_intelligence/console_detail.py` | `activation_verdict`, activation checks, action queue, hard/advisory gate evidence, and current deep-link implementation evidence. |
| `app/supabase/migrations/030_exam_registry_cycles_phases.sql` | `exam_cycles`, `exam_phases`, and `exam_topic_coverage` schema evidence. |
| `app/supabase/migrations/031_syllabus_evidence_mapping.sql` | `syllabus_documents` and `syllabus_topic_mentions` schema evidence. |
| `app/supabase/migrations/032_pyq_question_intelligence.sql` | `pyq_papers`, `pyq_questions`, `pyq_options`, and `pyq_question_topic_tags` schema evidence. |
| `app/supabase/migrations/055_exam_competition_metrics.sql` | `exam_competition_metrics` schema evidence. |
| `app/supabase/migrations/056_exam_policy_updates.sql` | `exam_policy_updates` schema evidence. |
| `app/supabase/migrations/111_document_assets.sql` | `document_assets` and `document_processing_jobs` schema evidence. |
| `app/supabase/migrations/113_document_pages_text_extract.sql` | `text_extract` processing-job uniqueness/evidence. |
| `app/supabase/migrations/157_exam_documents.sql` | Linked exam-intelligence document record evidence. |
| `app/supabase/migrations/103_pyq_options_review.sql` | `pyq_options.reviewer_status` evidence. |

**Discipline rule**

I6 DECISION TO LOCK: A table name, component name, route currently present on this local branch, or current implementation detail does not automatically make a product rule SOURCE-LOCKED. Only merged findings/design-lock text is SOURCE-LOCKED; code evidence may support an I6 decision, a derived proposal, or a rebase-verification item.

## Locked architecture recap

| Rule | Authority | Source |
|---|---|---|
| Hybrid architecture is locked. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.2 |
| Mini-wizard is limited to atomic cycle creation: cycle identity and dates; phase selection/creation; review and save. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.2 |
| Persistent nine-step checklist owns activation readiness. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.2 |
| Checklist work may span multiple sessions and must be resumable. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.1–§6.2 |
| No new route or sidebar surface is introduced by I6/I9 cycle setup. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §2.2, §13, Appendix B |
| After creation, return to Manage Exam with the created cycle selected. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.2 |
| I9 remains blocked until this gate is approved. | SOURCE-LOCKED | `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §6.4 |

## AddCycleWizard decision

**Inline destination**

SOURCE-LOCKED: The inline destination combines the canonical Manage Exam route `/admin/exam-intelligence/exams/:exam_id` with Appendix B query `?tab=setup&action=add-cycle`. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` Appendix B; `app/frontend/src/routes/adminRoutes.jsx` `AddCycleRedirect`.

**I6 decisions to lock**

| Decision | Authority label | Source / evidence |
|---|---|---|
| Reuse or extract validation, duplicate-cycle detection, template-phase selection, phase-slug generation, and review-summary logic from `AddCycleWizard.jsx`. | I6 DECISION TO LOCK | `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx` route-bound standalone flow evidence. |
| Do not mount the existing standalone component unchanged inside Manage Exam. | I6 DECISION TO LOCK | `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx` uses route-bound navigation/state; `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` owns Setup operations. |
| Implement the bounded Cycle → Phases → Review & Create flow inside Manage Exam → Setup. | I6 DECISION TO LOCK | Source-locked architecture plus Appendix B handler requirement. |
| `SetupPanel.jsx` remains the operational owner. | I6 DECISION TO LOCK | `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` current cycle/phase CRUD evidence. |
| No standalone Add Cycle route or sidebar destination is introduced. | I6 DECISION TO LOCK | Source-locked no-new-surface rule and Appendix B inline destination. |
| Retain `AddCycleWizard.jsx` until the I9 replacement behavior and compatibility tests pass. | I6 DECISION TO LOCK | Design-lock redirect/dead-component cleanup sequence requires compatibility before removal. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §2.4, §10.7. |
| Retire the standalone dead component only in a later cleanup commit. | I6 DECISION TO LOCK | Cleanup after redirects/tests pass. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §2.4, §10.7. |

**Current code evidence**

| Evidence | Authority label | Source |
|---|---|---|
| `AddCycleWizard.jsx` contains a three-step flow. | DERIVED — OPERATOR APPROVAL REQUIRED | `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx` step/review/navigation code evidence. |
| `AddCycleWizard.jsx` uses route-bound navigation/state and should not be assumed directly embeddable. | DERIVED — OPERATOR APPROVAL REQUIRED | `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx` `useNavigate`/route-state code evidence. |
| `SetupPanel.jsx` currently handles cycle/phase CRUD and opens its current cycle form when `action=add-cycle`. | DERIVED — OPERATOR APPROVAL REQUIRED | `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` `action` prop and cycle/phase form code evidence. |
| Existing Setup does not already implement the bounded three-step wizard. | DERIVED — OPERATOR APPROVAL REQUIRED | Difference between `SetupPanel.jsx` forms and the source-locked mini-wizard responsibilities. |

REBASE VERIFY: PR #757 must be checked after merge to confirm the final `tab=setup` and `action=add-cycle` handler behavior before I9 runtime work begins.

## Progress authority

**I6 decisions to lock**

| Rule | Authority label | Source / evidence |
|---|---|---|
| Progress is backend-derived. | I6 DECISION TO LOCK | Aligns with design-lock backend authority. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §4. |
| The frontend renders progress but does not independently infer completion. | I6 DECISION TO LOCK | Frontend must not calculate activation authority. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §4.2. |
| Existing `activation_verdict` and action queue remain the top-level activation authority. | I6 DECISION TO LOCK | `work_queue.classify_exam` owns the top-level verdict. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §4.2; `app/backend/app/exam_intelligence/work_queue.py` `classify_exam`; `app/backend/app/exam_intelligence/console_detail.py` `build_console_detail`. |
| Existing `readiness.py` output remains advisory. | I6 DECISION TO LOCK | Readiness score percentages must not authorize activation. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §4.2. |
| I9-0 must introduce or extend a backend contract returning all nine activation steps for the selected exam and cycle. | I6 DECISION TO LOCK | Required to avoid frontend-only translation from current seven-section readiness. |
| This document does not invent an endpoint path, table name, RPC name, or response-field name for the I9 progress contract. | I6 DECISION TO LOCK | Runtime/API implementation is out of scope. |
| The implementation contract must be idempotent and read-only for progress derivation. | I6 DECISION TO LOCK | Consistent with existing read-only console/detail and readiness reads. Source: `app/backend/app/exam_intelligence/console_detail.py` module contract. |
| Progress must be recomputable from canonical evidence. | I6 DECISION TO LOCK | Required for backend-derived, non-localStorage resume state. |

**Present mismatch to resolve in I9-0**

| Mismatch | Authority label | Source |
|---|---|---|
| `readiness.py` exposes seven sections: setup, documents, syllabus_mapper, PYQ workbench, updates, competition, and review/activate. | DERIVED — OPERATOR APPROVAL REQUIRED | `app/backend/app/exam_intelligence/readiness.py` `compute_exam_workspace_readiness`. |
| Setup, syllabus, and updates are currently exam-scoped in readiness behavior. | DERIVED — OPERATOR APPROVAL REQUIRED | `app/backend/app/exam_intelligence/readiness.py` `_setup`, `_syllabus_mapper`, `_updates`. |
| Documents, PYQ, and competition are currently cycle-scoped when a cycle is provided. | DERIVED — OPERATOR APPROVAL REQUIRED | `app/backend/app/exam_intelligence/readiness.py` `_documents`, `_pyq_workbench`, `_competition`. |
| Review/activate is derived from upstream section state. | DERIVED — OPERATOR APPROVAL REQUIRED | `app/backend/app/exam_intelligence/readiness.py` `_review_activate`. |
| I9 must not translate those seven sections into nine frontend-only steps. | I6 DECISION TO LOCK | Prevents frontend-derived completion authority. |

## Nine-step activation matrix

| Step | Authority label | Canonical evidence source | Completion predicate | Evidence scope | Base gate class | Locked deep-link source | Exact deep-link target or explicit unresolved marker | Resume behavior | Empty-state behavior | Selected-cycle behavior | Progress derivation | Manual-mark-complete rule |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cycle details | I6 DECISION TO LOCK | Selected `exam_cycles` row. Source: `app/supabase/migrations/030_exam_registry_cycles_phases.sql` `exam_cycles`; `app/backend/app/exam_intelligence/management_read_model.py` current-cycle evidence. | Complete when the selected cycle exists and carries enough identity/date fields for Manage Exam to normalize it; exact required fields are REBASE VERIFY because PR #757 final cycle normalization is not merged. | selected-cycle | hard | Setup/phases example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?tab=setup` | Resume by recomputing selected-cycle evidence from backend; no local state. | Show Setup empty state prompting cycle creation; if no selected cycle exists, show no-current-cycle state. | Must bind all evidence to selected cycle; if selected cycle is removed, recompute and require operator selection. | backend-derived via I9-0 selected-cycle contract; no endpoint name invented. | Not allowed for evidence-derived completion; exceptional override is UNRESOLVED — OPERATOR DECISION REQUIRED. |
| Phases and schedule | I6 DECISION TO LOCK | Cycle-bound `exam_phases` rows for the selected cycle. Source: `app/supabase/migrations/030_exam_registry_cycles_phases.sql` `exam_phases`; `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` phase CRUD. | Complete when the selected cycle has at least one cycle-bound phase with schedule evidence sufficient for activation; template-only phases do not complete cycle scheduling unless later source explicitly authorizes it. | selected-cycle | hard | Setup/phases example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?tab=setup` | Resume to Setup with selected cycle and phase list recomputed. | Show empty phase schedule state and offer inline cycle/phase setup; do not count templates as completed cycle schedule. | Only phases whose `exam_cycle_id` matches the selected cycle count. | backend-derived via I9-0 selected-cycle contract; no endpoint name invented. | Not allowed for evidence-derived completion; exceptional override is UNRESOLVED — OPERATOR DECISION REQUIRED. |
| Source documents | DERIVED — OPERATOR APPROVAL REQUIRED | `document_assets` ownership plus linked exam-intelligence document records. Source: `app/supabase/migrations/111_document_assets.sql` `document_assets`; `app/supabase/migrations/157_exam_documents.sql` `exam_documents`; `app/supabase/migrations/031_syllabus_evidence_mapping.sql` `syllabus_documents`. | Complete when at least one relevant source document is linked to the exam or selected cycle and is eligible for extraction/review; row existence alone is not sufficient without linkage and current status. | hybrid | advisory | Documents/extraction area is covered by design-lock §7.2, but only an entity-level failed extraction example is locked. | NO LOCKED ENTITY-LEVEL ROUTE — REBASE VERIFY | Resume to Documents tab after backend recomputation; exact entity focus is rebase-dependent. | Use generic Documents tab destination without inventing document ID/status; show upload/link empty state. | Cycle-linked documents must match selected cycle; exam-scoped inherited documents must be labelled `exam-scoped`. | backend-derived via I9-0 evidence contract. | Not allowed for evidence-derived completion; exceptional override is UNRESOLVED — OPERATOR DECISION REQUIRED. |
| Extraction | DERIVED — OPERATOR APPROVAL REQUIRED | Latest `document_processing_jobs` row per asset where `job_type = 'text_extract'`. Source: `app/supabase/migrations/111_document_assets.sql` `document_processing_jobs`; `app/supabase/migrations/113_document_pages_text_extract.sql`; `app/backend/app/exam_intelligence/readiness.py` `load_doc_extraction_counts`. | Complete when required selected-cycle/inherited source documents have current successful text extraction; pending, failed, missing, or superseded extraction is not complete. | hybrid | advisory | Failed or pending document extraction example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=documents&document={document_id}&status=failed` | Resume by recomputing latest extraction job status per relevant asset. | Show queued/running/pending extraction state; failed extraction gets the locked failed-document destination when document ID exists. | Cycle-linked extraction must match selected cycle; exam-scoped inherited documents must be labelled `exam-scoped`. | backend-derived using latest text-extract job evidence. | Not allowed for evidence-derived completion; failed jobs require correction or rerun, not manual completion. |
| Syllabus mapping | DERIVED — OPERATOR APPROVAL REQUIRED | `syllabus_topic_mentions`, noting schema supports cycle and phase scope while current readiness treats syllabus as exam-scoped. Source: `app/supabase/migrations/031_syllabus_evidence_mapping.sql`; `app/backend/app/exam_intelligence/readiness.py` `_syllabus_mapper`; `app/backend/app/exam_intelligence/console_detail.py` syllabus checks. | Complete when syllabus mentions required by the selected exam/cycle contract are reviewed/verified and no blocking pending/needs-correction rows remain; exact cycle-vs-exam inheritance rule is UNRESOLVED — OPERATOR DECISION REQUIRED. | exam-scoped inherited | advisory | Pending syllabus mentions example in design-lock §7.2; pending topic coverage example may also apply to coverage rows. | `/admin/exam-intelligence/exams/{exam_id}?tab=syllabus&status=pending` | Resume to Syllabus tab with backend-filtered pending/verified state. | Show no syllabus mentions state; do not fabricate topic coverage completion. | Current readiness is exam-scoped; I9 must label inherited evidence and rebase-verify final tab filters. | backend-derived; current seven-section readiness cannot be frontend-expanded into nine steps. | Not allowed for evidence-derived completion; rejected/needs-correction rows require review resolution. |
| PYQ readiness | DERIVED — OPERATOR APPROVAL REQUIRED | `pyq_papers`, `pyq_questions`, `pyq_options`, and `pyq_question_topic_tags` for the selected cycle where applicable. Source: `app/supabase/migrations/032_pyq_question_intelligence.sql`; `app/supabase/migrations/103_pyq_options_review.sql`; `app/backend/app/exam_intelligence/readiness.py` `_pyq_workbench`; `app/backend/app/exam_intelligence/work_queue.py` aggregate. | Complete when selected-cycle PYQ evidence satisfies verified paper + verified question + verified option/tag requirements used by the backend contract; exact option gate is DERIVED — OPERATOR APPROVAL REQUIRED from schema and current review columns. | selected-cycle | advisory | Selected PYQ paper / pending questions example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=pyq&paper={paper_id}&status=pending` | Resume to PYQ tab and selected paper when backend supplies `paper_id`; otherwise use tab-level work queue. | Show no PYQ papers/questions state for selected cycle; do not inherit another cycle's PYQ. | Only selected-cycle papers/questions count unless operator approves inherited PYQ behavior. | backend-derived using PYQ tables and action queue evidence. | Not allowed for evidence-derived completion; rejected/needs-correction rows require review resolution. |
| Policy updates | DERIVED — OPERATOR APPROVAL REQUIRED | `exam_policy_updates`, noting schema supports `exam_cycle_id` while current readiness treats updates as exam-scoped. Source: `app/supabase/migrations/056_exam_policy_updates.sql`; `app/backend/app/exam_intelligence/readiness.py` `_updates`; `app/backend/app/exam_intelligence/console_detail.py` update checks. | Complete when there are no pending policy updates requiring verification for the applicable exam/cycle scope; current code treats no pending updates as done, but cycle inheritance is UNRESOLVED — OPERATOR DECISION REQUIRED. | exam-scoped inherited | advisory | Pending policy updates example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?tab=updates&status=pending` | Resume to Updates tab with backend-filtered pending/verified state. | Show no pending updates state; distinguish no updates from unreviewed updates. | Current readiness is exam-scoped; I9 must label inherited evidence and rebase-verify final cycle filters. | backend-derived from policy update review state. | Not allowed for evidence-derived completion; pending/needs-correction rows require review resolution. |
| Competition context | DERIVED — OPERATOR APPROVAL REQUIRED | `exam_competition_metrics` for the selected cycle. Source: `app/supabase/migrations/055_exam_competition_metrics.sql`; `app/backend/app/exam_intelligence/readiness.py` `_competition`; `app/backend/app/exam_intelligence/console_detail.py` competition checks. | Complete when selected-cycle competition metrics are reviewed or locked according to the backend contract; row existence alone is insufficient. | selected-cycle | advisory | Selected-cycle competition context example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=competition` | Resume to Competition tab for selected cycle. | Show no reviewed competition metrics state and prompt review/import. | Only selected-cycle competition metrics count unless operator approves inheritance. | backend-derived from selected-cycle competition rows. | Not allowed for evidence-derived completion; exceptional not-applicable handling is governed by management-mode decisions below. |
| Review and activate | SOURCE-LOCKED | Backend `activation_verdict`, activation checks, and action queue for the selected exam/cycle. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §4; `app/backend/app/exam_intelligence/work_queue.py` `classify_exam`; `app/backend/app/exam_intelligence/console_detail.py` `build_console_detail`. | Complete when backend activation verdict is ready and hard gates pass; score percent never authorizes activation. | derived | hard | Review and activation gate example in design-lock §7.2. | `/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=review` | Resume to Review tab with fresh backend verdict/action queue. | Show blocker summary and first actionable deep link; do not allow activation when backend verdict is non-ready. | Verdict must be recomputed for selected exam/cycle context; final selected-cycle behavior is REBASE VERIFY. | backend-derived from classifier/verdict/action queue. | Not allowed for evidence-derived completion; activation override, if any, is UNRESOLVED — OPERATOR DECISION REQUIRED and must be permission-gated/audited. |

## Management-mode × cadence applicability matrix — DERIVED FROM §18.1 — REQUIRES OPERATOR APPROVAL AT REBASE

**Source limitation**

- SOURCE-LOCKED: §18.1 defines management-mode intent. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.1.
- SOURCE-LOCKED: §18.1 enumerates cadence values only. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.1.
- SOURCE-LOCKED: §18.1 does not define cadence-specific workflow behavior. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.1.
- SOURCE-LOCKED: §18.2 says the full governance contract remains deferred. Source: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §18.2.

**Management-mode baseline table**

| Management mode | Source meaning | Proposed baseline | Authority label | Not-applicable discipline |
|---|---|---|---|---|
| core | Full readiness expected. | Full nine-step checklist applies; no proposed N-A by mode. | DERIVED — OPERATOR APPROVAL REQUIRED | No N-A proposed because source phrase directly implies full readiness. |
| light | Essential facts and major updates. | Cycle details, phases/schedule, source documents, extraction, policy updates, and review/activate remain expected; syllabus, PYQ, and competition gate class remains UNRESOLVED where not essential. | DERIVED — OPERATOR APPROVAL REQUIRED | PROPOSED N-A only if operator maps non-essential deep evidence to light mode; semantic mapping is not direct, so unresolved for syllabus/PYQ/competition. |
| index_only | Searchable reference; no deep Study OS. | Cycle details, source documents, policy updates, and review/activate remain expected; phases/schedule, extraction depth, syllabus, PYQ, and competition are proposed advisory-or-N-A pending operator decision. | DERIVED — OPERATOR APPROVAL REQUIRED | PROPOSED N-A may apply to deep Study OS evidence because source phrase says no deep Study OS; exact steps require operator approval. |
| archive | Retained with minimal active operations. | Cycle details, source documents, policy updates, and review/activate remain minimal; most activation-readiness evidence may be proposed N-A only where active operations are not required. | DERIVED — OPERATOR APPROVAL REQUIRED | PROPOSED N-A may apply to active-operation-heavy steps because source phrase says minimal active operations; exact steps require operator approval. |

**Complete mode × cadence grid**

| Mode \ Cadence | annual | recurring | irregular | one_off | unknown |
|---|---|---|---|---|---|
| core | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits core baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits core baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits core baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits core baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits core baseline only; cadence may not alter hard/advisory/N-A behavior. |
| light | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits light baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits light baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits light baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits light baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits light baseline only; cadence may not alter hard/advisory/N-A behavior. |
| index_only | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits index_only baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits index_only baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits index_only baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits index_only baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits index_only baseline only; cadence may not alter hard/advisory/N-A behavior. |
| archive | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits archive baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits archive baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits archive baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits archive baseline only; cadence may not alter hard/advisory/N-A behavior. | DERIVED — OPERATOR APPROVAL REQUIRED: §18.1 defines no cadence modifier; inherits archive baseline only; cadence may not alter hard/advisory/N-A behavior. |

I6 DECISION TO LOCK: Do not create cadence-specific `not_applicable` rules. Cadence may not alter hard/advisory/N-A behavior until the operator approves an explicit rule. Do not infer N-A merely from low business priority, irregular cadence, unknown cadence, or lack of current data. I9 remains blocked until the operator approves or replaces all proposed and unresolved applicability rules.

## Resume and completion policy

**Rules to lock**

| Rule | Authority label |
|---|---|
| Resume state comes from backend evidence, never localStorage. | I6 DECISION TO LOCK |
| The checklist is displayed in the context of one selected cycle. | I6 DECISION TO LOCK |
| Exam-scoped evidence may be inherited into the selected-cycle view but must be labelled `exam-scoped`. | I6 DECISION TO LOCK |
| Cycle-scoped evidence must never leak from another cycle. | I6 DECISION TO LOCK |
| Switching cycles recomputes the checklist from canonical evidence. | I6 DECISION TO LOCK |
| After successful cycle creation, return to Manage Exam with the new cycle selected. | I6 DECISION TO LOCK |
| Evidence-derived steps cannot be manually marked complete. | I6 DECISION TO LOCK |
| A not-applicable result requires a machine-readable reason. | I6 DECISION TO LOCK |
| Exceptional override must be permission-gated and audited. | I6 DECISION TO LOCK |
| Do not invent the override permission token, endpoint, table, or schema. | I6 DECISION TO LOCK |
| Override design remains an I9-0 implementation contract unless an existing source defines it. | I6 DECISION TO LOCK |
| No frontend-only completion state. | I6 DECISION TO LOCK |
| No optimistic permanent completion state. | I6 DECISION TO LOCK |
| Stale or superseded evidence must not remain complete. | I6 DECISION TO LOCK |

**Behavior definitions**

| Situation | Behavior | Authority label |
|---|---|---|
| Refresh | Re-fetch/recompute backend progress for selected exam and cycle; do not restore local completion state. | I6 DECISION TO LOCK |
| Browser back/forward | URL-owned exam/cycle/tab state determines view; progress still comes from backend evidence. | I6 DECISION TO LOCK |
| Returning after a later session | Resume from backend evidence and latest action queue; localStorage is not authority. | I6 DECISION TO LOCK |
| Selected cycle removed or no longer valid | Recompute current-cycle normalization; show invalid-cycle/no-current-cycle state if no valid selected cycle remains. | REBASE VERIFY |
| No current cycle | Show Setup-focused empty state; no downstream cycle-scoped steps can be complete. | I6 DECISION TO LOCK |
| No evidence | Show missing/empty state for each relevant step; do not mark complete from absence unless backend returns approved not_applicable. | I6 DECISION TO LOCK |
| Asynchronous extraction pending | Show extraction pending/in-progress and keep extraction incomplete until backend evidence changes. | I6 DECISION TO LOCK |
| Failed extraction | Show failed extraction state and locked failed-document deep link when a document ID exists. | I6 DECISION TO LOCK |
| Rejected or needs-correction review rows | Keep affected step incomplete or needs_action until rows are resolved by normal review flow. | I6 DECISION TO LOCK |
| Superseded evidence | Recompute and remove completion if superseded evidence was the only supporting proof. | I6 DECISION TO LOCK |
| Backend progress endpoint unavailable | Fail closed for completion authority; render an error/unavailable state rather than frontend-inferred completion. | I6 DECISION TO LOCK |

## Dependency and ordering contract

| Contract statement | Authority label | Source |
|---|---|---|
| This document may be authored while PR #757 is open. | I6 DECISION TO LOCK | Docs-only and no runtime overlap. |
| This document cannot be approved as final before post-#757 rebase verification. | REBASE VERIFY | PR #757 owns final I8-B route/tab/workspace behavior. |
| I9 implementation must not begin while I8-C still owns shared Manage Exam routing/workspace files. | SOURCE-LOCKED | I8-A/B/C serial ownership. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §10.1, §10.5. |
| No I9 runtime implementation may be hidden inside this docs PR. | SOURCE-LOCKED | I9 implementation blocked by I6 gate. Source: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §13. |
| No PR #756/PYQ projection behavior is treated as merged source unless it is present on the eventual rebased base. | I6 DECISION TO LOCK | Unmerged PR behavior is not trusted local source. |

## Rebase verification checklist for the operator

**Items to verify after PR #757 merges**

| Item | Authority claim needing verification |
|---|---|
| Canonical Manage Exam route `/admin/exam-intelligence/exams/:exam_id`. | REBASE VERIFY |
| Legacy redirect behavior from workspace/console routes. | REBASE VERIFY |
| Query parameter `tab=setup`. | REBASE VERIFY |
| Query parameter `action=add-cycle`. | REBASE VERIFY |
| Query parameter `cycle`. | REBASE VERIFY |
| Query parameter `status`. | REBASE VERIFY |
| Query parameter `document`. | REBASE VERIFY |
| Query parameter `paper`. | REBASE VERIFY |
| Query parameter `row`. | REBASE VERIFY |
| Tab ID `setup`. | REBASE VERIFY |
| Tab ID `documents`. | REBASE VERIFY |
| Tab ID `syllabus`. | REBASE VERIFY |
| Tab ID `pyq`. | REBASE VERIFY |
| Tab ID `updates`. | REBASE VERIFY |
| Tab ID `competition`. | REBASE VERIFY |
| Tab ID `review`. | REBASE VERIFY |
| Setup is the default tab. | REBASE VERIFY |
| Overview is removed. | REBASE VERIFY |
| Cycle changes preserve intended task state. | REBASE VERIFY |
| Management endpoint supplies verdict/action-queue authority. | REBASE VERIFY |
| No duplicate console fetch is required. | REBASE VERIFY |
| Deep-link parameters reach intended panels. | REBASE VERIFY |
| Current-cycle normalization behavior. | REBASE VERIFY |
| Add Cycle still resolves into Setup. | REBASE VERIFY |
| I8-C is merged before I9 implementation dispatch. | REBASE VERIFY |

**Approval procedure**

1. Rebase onto the commit containing merged PR #757.
2. Re-read `AGENTS.md` and Graphify artifacts.
3. Verify every REBASE VERIFY item against actual merged source.
4. Resolve every UNRESOLVED item with an explicit operator decision.
5. Approve, revise, or reject every DERIVED item.
6. Update document status from DRAFT only after all decisions are closed.
7. Add the required `career-copilot-checklist.md` update in a separate operator commit on the same branch.
8. Confirm I8-C sequencing before dispatching I9.
9. Only then open the draft PR.

## Source index

| Source inspected | Symbols / sections used |
|---|---|
| `AGENTS.md` | Graphify-first rule; shared checklist publication requirement. |
| `graphify-out/GRAPH_REPORT.md` | Repository graph map/freshness. |
| `graphify-out/wiki/index.md` | Graph wiki entry point. |
| `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` | §2.2–2.4, §4, §7, §10.4–10.7, §13, Appendix B. |
| `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` | §6, §18.1–§18.2, §22.2–§22.4. |
| `app/frontend/src/routes/adminRoutes.jsx` | `AddCycleRedirect`, route list, compatibility routes. |
| `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` | Setup panel cycle/phase CRUD and `action` handling. |
| `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx` | Standalone add-cycle wizard step/navigation evidence. |
| `app/backend/app/exam_intelligence/management_read_model.py` | Management read-model/current-cycle evidence. |
| `app/backend/app/exam_intelligence/readiness.py` | Seven-section readiness and section scope evidence. |
| `app/backend/app/exam_intelligence/work_queue.py` | `aggregate`, `classify_exam`, pending/verified evidence aggregation. |
| `app/backend/app/exam_intelligence/console_detail.py` | `build_console_detail`, `activation_verdict`, `_deep_link`, activation checks and gates. |
| `app/supabase/migrations/030_exam_registry_cycles_phases.sql` | `exam_cycles`, `exam_phases`, `exam_topic_coverage`. |
| `app/supabase/migrations/031_syllabus_evidence_mapping.sql` | `syllabus_documents`, `syllabus_topic_mentions`. |
| `app/supabase/migrations/032_pyq_question_intelligence.sql` | `pyq_papers`, `pyq_questions`, `pyq_options`, `pyq_question_topic_tags`. |
| `app/supabase/migrations/055_exam_competition_metrics.sql` | `exam_competition_metrics`. |
| `app/supabase/migrations/056_exam_policy_updates.sql` | `exam_policy_updates`. |
| `app/supabase/migrations/111_document_assets.sql` | `document_assets`, `document_processing_jobs`. |
| `app/supabase/migrations/113_document_pages_text_extract.sql` | `text_extract` job uniqueness and document pages. |
| `app/supabase/migrations/157_exam_documents.sql` | `exam_documents`. |
| `app/supabase/migrations/103_pyq_options_review.sql` | `pyq_options.reviewer_status`. |
| `app/supabase/migrations/155_pyq_questions_review_columns.sql` | `pyq_questions` review audit columns. |
