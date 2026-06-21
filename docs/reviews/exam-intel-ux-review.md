# Exam Intelligence Admin UX Review

Date: 2026-06-12  
Branch: `codex/exam-intel-ux-review`  
Scope: read-only UX + gap analysis of Admin Exam Intelligence Review, Exam Intelligence CMS, and Exam Intelligence Workspace. The only repository write made for this task is this report.

## 1. Executive summary

- **[partial] [confirmed]** Exam Intelligence has a coherent primary IA spine (`/admin/exam-intelligence` → `/cms` → `/new` → `/workspace/:exam_id` → optional cycle route), but most Exam Intelligence routes are **not wrapped in `RouteErrorBoundary`** even though governance requires it; only verification-report routes are inside the boundary block. Evidence: `app/frontend/src/routes/adminRoutes.jsx:L80-L98`, `app/frontend/src/routes/adminRoutes.jsx:L106-L110`.
- **[confusing] [confirmed]** The Admin Review page says “Verified-only contract” and “verified or locked,” while coverage lifecycle code and workspace copy use `reviewed|locked`; backend comments also contradict each other about whether only `locked` or `locked|reviewed` reaches planners. Evidence: `app/frontend/src/pages/admin/ExamIntelligence.jsx:L139-L148`, `app/backend/app/api/admin_exam_intelligence.py:L350-L353`, `app/backend/app/api/admin_exam_intelligence.py:L600-L604`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L381-L385`.
- **[implemented] [confirmed]** The Workspace is the strongest surface for one-exam administration: it has a 7-tab progression, a SmartHeader with stage/next action, cycle picker, readiness checklist, document upload/link flow, syllabus mapper, PYQ workbench, and Review & Activate panel. Evidence: `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:L25-L33`, `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:L166-L217`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L260-L356`.
- **[missing] [confirmed]** Several Workspace and CMS user-triggered mutations call `api.post`, `api.patch`, or `api.del` directly instead of `useApiAction`, which violates frontend governance and weakens consistent busy/success/error/rollback handling. Evidence: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L685-L697`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L729-L740`, `app/frontend/src/pages/admin/studyos/ExamIntelDocuments.jsx:L112-L139`, `app/frontend/src/pages/admin/exam-workspace/panels/CompetitionPanel.jsx:L64-L67`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L95-L104`.
- **[partial] [confirmed]** CMS clearly states that rows land pending and requires audit reasons, but the UI is still a raw table editor with database-column labels (`exam_id`, `management_mode`, `reviewer_status`) and no guided “next step” path from entity creation to Workspace review. Evidence: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L887-L890`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L895-L907`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L1025-L1032`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L1094-L1158`.
- **[implemented] [confirmed]** Document upload/extraction/linking has both CMS and Workspace implementations; the Workspace version is more journey-oriented and explicitly says linking does not auto-verify, while CMS exposes a raw document list and manual link actions. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/DocumentsPanel.jsx:L567-L593`, `app/frontend/src/pages/admin/exam-workspace/panels/DocumentsPanel.jsx:L606-L763`, `app/frontend/src/pages/admin/studyos/ExamIntelDocuments.jsx:L310-L391`.
- **[confusing] [confirmed]** PYQ administration is split across a route-level `PyqPaperWorkspace`, the embedded Workspace tab, CMS bulk import, and document upload/link flow; empty copy says “Create one in the CMS” rather than deep-linking or creating the required PYQ paper in context. Evidence: `app/frontend/src/routes/adminRoutes.jsx:L84-L85`, `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/PyqWorkbenchPanel.jsx:L46-L80`, `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L9-L13`.
- **[missing] [confirmed]** The backend has diagnostics endpoints for stuck documents/jobs, but neither CMS nor Workspace surfaces a reset/retry recovery action for failed/stuck extraction; operators can only refresh/status-check from the UI. Evidence: `app/backend/app/api/admin_exam_intel_cms.py:L2883-L2908`, `app/backend/app/api/admin_exam_intel_cms.py:L2911-L2925`, `app/frontend/src/pages/admin/studyos/ExamIntelDocuments.jsx:L333-L337`, `app/frontend/src/pages/admin/exam-workspace/panels/DocumentsPanel.jsx:L758-L763`.

## 2. Files inspected

Discovery order followed: `AGENTS.md` → `graphify-out/GRAPH_REPORT.md` → `graphify-out/wiki/index.md` → confirmed wired source files. `graphify query` was attempted for graph traversal, but the binary was not installed in the container (`/bin/bash: graphify: command not found`), so route files plus graph refs were used.

### Files opened

- `AGENTS.md`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/wiki/index.md`
- `app/frontend/src/routes/adminRoutes.jsx`
- `app/frontend/src/pages/admin/AdminShell.jsx`
- `app/frontend/src/pages/admin/ExamIntelligence.jsx`
- `app/frontend/src/features/admin/exam-intelligence/ExamIntelligenceOverviewCards.jsx`
- `app/frontend/src/features/admin/exam-intelligence/ExamListTable.jsx`
- `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx`
- `app/frontend/src/pages/admin/studyos/ExamIntelDocuments.jsx`
- `app/frontend/src/features/admin/shared/CmsRefField.jsx`
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx`
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx`
- `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/panels/DocumentsPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/panels/CompetitionPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/syllabus-mapper/SyllabusMapperPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/syllabus-mapper/useSyllabusMapper.js`
- `app/frontend/src/pages/admin/exam-workspace/syllabus-mapper/DocumentSelector.jsx`
- `app/frontend/src/pages/admin/exam-workspace/syllabus-mapper/AcceptPreviewModal.jsx`
- `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/PyqWorkbenchPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/usePyqWorkbench.js`
- `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx`
- `app/backend/app/api/admin_exam_intelligence.py`
- `app/backend/app/api/admin_exam_intel_cms.py`
- `app/backend/app/api/admin_exam_intel_documents.py`
- `app/backend/app/exam_intelligence/readiness.py`
- `app/backend/app/exam_intelligence/syllabus_mapper.py`
- `app/backend/app/study_os/plan_impact.py`

### Hint paths not found

None. All user-provided hint paths checked for existence were found. `SmartHeader` was discovered in `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:L72-L75`.

## 3. IA map

| Route | Page purpose | Primary admin task | Backend dependency |
|---|---|---|---|
| `/admin/exam-intelligence` | Admin Exam Intelligence Review overview/list | Monitor verified/pending counts, filter exams, open Workspace | `GET /api/admin/exam-intelligence/overview`; `GET /api/admin/exam-intelligence/exams` in `app/frontend/src/pages/admin/ExamIntelligence.jsx:L55-L80` |
| `/admin/exam-intelligence/cms` | Raw CMS entity CRUD/import + document panel | Create/import exam intelligence rows; upload/link documents | `GET/POST/PATCH/DELETE /api/admin/exam-intelligence-cms/*` in `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L627-L645`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L669-L740`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L774-L852` |
| `/admin/exam-intelligence/new` | Guided exam wizard | Create new exam identity via guided flow | Confirmed route, page not reviewed because scope emphasized the three existing surfaces. Route evidence: `app/frontend/src/routes/adminRoutes.jsx:L82-L83` |
| `/admin/exam-intelligence/exams/:exam_id/add-cycle` | Add cycle wizard | Add a cycle to an existing exam | Confirmed route, page not reviewed. Route evidence: `app/frontend/src/routes/adminRoutes.jsx:L83-L84` |
| `/admin/exam-intelligence/workspace/:exam_id` | Exam Workspace | One-exam setup, docs, syllabus, PYQ, updates, competition, activation | `GET /api/admin/exam-intelligence/workspace/{exam_id}/context`; `GET /readiness` in `app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx:L24-L61` |
| `/admin/exam-intelligence/workspace/:exam_id/:cycle_id` | Exam Workspace scoped to cycle | Same as above for a selected cycle | Cycle query param added in context/readiness fetches in `app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx:L29-L33`, `app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx:L50-L54` |
| `/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace` | Route-level PYQ paper workspace | Review/edit a single PYQ paper | `GET /api/admin/exam-intelligence-cms/pyq-papers/{id}`, `GET /pyq-questions`, `GET /progress` in `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L1106-L1137` |
| `/admin/study-os/exam-intel-cms` | Legacy redirect | Redirect old Study OS CMS link | Redirects to `/admin/exam-intelligence`, not `/cms`, in `app/frontend/src/routes/adminRoutes.jsx:L98-L99` |

IA note: Admin nav exposes “Exam Intelligence” and “New guided exam,” but not a direct “CMS” or “Workspace” entry; CMS is linked inside the Review page header. Evidence: `app/frontend/src/pages/admin/AdminShell.jsx:L25-L34`, `app/frontend/src/pages/admin/ExamIntelligence.jsx:L125-L134`.

## 4. Journey review

### 4.1 New exam → planner-ready

**Current flow.**  
[confirmed] The admin can enter through `/admin/exam-intelligence/new`, `/admin/exam-intelligence/cms`, or the Exam Review list. The CMS page gives a guided-exam escape hatch only when the entity is `exams`, while the Review table opens `/workspace/{id}` for an existing exam. Evidence: `app/frontend/src/routes/adminRoutes.jsx:L80-L86`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L932-L939`, `app/frontend/src/features/admin/exam-intelligence/ExamListTable.jsx:L73-L80`.

[confirmed] Backend creates an exam from `name`, defaults lane/cadence, and overwrites payload slug from name/org. Evidence: `app/backend/app/api/admin_exam_intel_cms.py:L277-L306`.

[confirmed] Workspace has Setup → Documents → Syllabus Mapper/PYQ → Updates/Competition → Review & Activate tabs. Evidence: `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:L25-L33`.

[confirmed] Planner readiness is presented as requiring row locks/reviews rather than creation alone. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L228-L244`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L381-L385`.

**Friction.**

- [confirmed] The old Study OS CMS redirect sends admins to `/admin/exam-intelligence`, not `/admin/exam-intelligence/cms`, which is a surprising target for a path named `exam-intel-cms`. Evidence: `app/frontend/src/routes/adminRoutes.jsx:L98-L99`.
- [confirmed] CMS row creation exposes raw DB labels and a raw table, so an admin creating an exam still has to know which entities and statuses matter next. Evidence: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L895-L907`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L1025-L1032`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L1094-L1158`.
- [confirmed] Route-level governance is not met for Exam Intelligence routes because they are siblings of the only `RouteErrorBoundary` block. Evidence: `app/frontend/src/routes/adminRoutes.jsx:L80-L99`, `app/frontend/src/routes/adminRoutes.jsx:L106-L110`.

**Recommendation.**

- [confirmed] Make Workspace the primary “continue setup” path after guided exam creation and after CMS exam create. Add explicit “Created → Open workspace” affordance; do not auto-mark any row live.
- [confirmed] Rename/redirect legacy `/admin/study-os/exam-intel-cms` to `/admin/exam-intelligence/cms` or label the redirect as the Review dashboard if keeping it.
- [confirmed] Wrap Exam Intelligence routes in `RouteErrorBoundary` in `adminRoutes.jsx`.

### 4.2 Update existing exam after corrigendum

**Current flow.**  
[confirmed] UpdatesPanel loads policy updates for the exam, supports adding an update via CMS create, and verifies via review endpoint. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx:L33-L63`, `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx:L65-L90`.

[confirmed] Updates copy says aggregator updates cannot affect the plan until paired with an official source. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx:L121-L134`.

[confirmed] Backend review for policy updates accepts only `pending|verified|rejected|needs_correction` and says only official verified rows reach `policy_update_context` as plan-affecting. Evidence: `app/backend/app/api/admin_exam_intelligence.py:L907-L924`.

**Friction.**

- [confirmed] UpdatesPanel mutation calls are direct `api.patch`/`api.post`, not `useApiAction`. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx:L50-L63`, `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx:L65-L90`.
- [confirmed] “Verify” action has no reason field despite the CMS create path recording a reason. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx:L50-L56`, `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx:L70-L82`.
- [confirmed] The table displays source URL and plan impact, but does not show explicit “official verified and affects_plan” gating language per row. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx:L181-L238`.

**Recommendation.**

- [confirmed] Convert update create/review mutations to `useApiAction`, add success/error toasts, and require/reuse an audit reason for status promotion.
- [confirmed] Add per-row copy: “Plan-impact only when source_type=official and reviewer_status=verified.”
- **[requires-backend] [needs-check: app/backend/app/study_os/* policy context]** If operators need to preview Study OS plan changes from a corrigendum before verifying, expose/confirm a policy-update plan-impact endpoint; current reviewed backend endpoint in this scope is coverage-specific (`/plan-impact/{coverage_id}`). Evidence: `app/backend/app/api/admin_exam_intelligence.py:L953-L976`.

### 4.3 Import PYQ paper content

**Current flow.**  
[confirmed] Workspace PYQ tab loads papers from CMS by exam/cycle and embeds `PyqPaperWorkspace` when a paper is selected. Evidence: `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/usePyqWorkbench.js:L12-L26`, `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/PyqWorkbenchPanel.jsx:L83-L101`.

[confirmed] The route-level PYQ workspace supports question list filters, editing, option edits, duplicate checks, source preview, and verify/reject/needs-correction actions. Evidence: `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L132-L163`, `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L242-L274`, `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L330-L357`, `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L431-L500`.

[confirmed] CMS bulk import forces PYQ questions and tags to pending, preserving trust gate. Evidence: `app/backend/app/api/admin_exam_intel_cms.py:L2648-L2667`.

**Friction.**

- [confirmed] Empty PYQ tab says “Create one in the CMS” but offers only “Bulk import questions,” so the missing prerequisite (PYQ paper record) is not solved in context. Evidence: `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/PyqWorkbenchPanel.jsx:L46-L80`.
- [confirmed] Question/option save and review mutations use direct `api.patch`/`api.post`, not `useApiAction`. Evidence: `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L242-L274`, `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L431-L500`.
- [confirmed] Review uses a constant `AUDIT_REASON = "workspace reviewer action"`, which is audit-light for sensitive PYQ verification. Evidence: `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L49-L50`, `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L453-L456`.

**Recommendation.**

- [confirmed] Add an in-context “Create PYQ paper” action in the PYQ tab before bulk import, using the CMS endpoint and `useApiAction`.
- [confirmed] Keep bulk import as advanced, but show the trust-gate result (“questions land pending”) right next to the import button.
- [confirmed] Add reason capture for verify/reject/needs-correction or confirm backend audit model can safely infer reason.

### 4.4 Trace why Study OS can/can't use an exam topic

**Current flow.**  
[confirmed] Review & Activate explains that created rows are not planner-ready and that planner consumption requires locked/reviewed topic coverage. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L219-L244`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L381-L385`.

[confirmed] Readiness checklist lists section blockers and offers Resolve/View actions. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L260-L356`.

[confirmed] Backend exam list counts topic coverage `reviewed|locked` as verified topic count. Evidence: `app/backend/app/api/admin_exam_intelligence.py:L350-L353`.

**Friction.**

- [confirmed] Backend `plan_impact.py` ranks only `locked` rows, while Review & Activate says `locked` or `reviewed` rows feed the planner; that creates a high-risk operator mental-model mismatch unless another Study OS path handles reviewed rows. Evidence: `app/backend/app/study_os/plan_impact.py:L76-L90`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L381-L385`.
- [confirmed] Admin Review overview shows low-confidence/stale counts but no drilldown to the exact rows/topics causing planner non-use. Evidence: `app/frontend/src/features/admin/exam-intelligence/ExamIntelligenceOverviewCards.jsx:L112-L124`.
- [needs-check: app/backend/app/study_os/mission_control.py] The prompt scope included `plan_impact.py`; full aspirant mission-control topic consumption should be verified before changing copy from `reviewed|locked` to `locked` or vice versa.

**Recommendation.**

- [confirmed] Add a topic-level “Why not planner-ready?” drawer in Workspace that shows coverage row status, source basis, syllabus mention status, PYQ verified counts, and plan-impact preview.
- [confirmed] Align all user-facing copy and backend comments to one status contract: “reviewed or locked rows feed the planner; locked preferred” if that is the intended Study OS contract, or update Review & Activate if actual runtime is locked-only. **[requires-backend if runtime changes]**

## 5. UX gap table

| Priority | Surface | File:line | Finding | Evidence(code) | Admin impact | Recommendation | Impl type |
|---|---|---:|---|---|---|---|---|
| P1 | IA/routes | `app/frontend/src/routes/adminRoutes.jsx:L80-L99` | Exam Intelligence routes are not inside the `RouteErrorBoundary` block. | Boundary is only opened for verification routes at `L106-L110`. | Route-level crashes can blank the admin shell and violates governance. | Wrap Exam Intelligence route cluster in `RouteErrorBoundary`. | route/test |
| P1 | Review/Workspace trust | `app/frontend/src/pages/admin/ExamIntelligence.jsx:L139-L148` | Review page says “verified or locked” but coverage lifecycle uses `reviewed|locked`. | Backend exam list counts `reviewed|locked` at `app/backend/app/api/admin_exam_intelligence.py:L350-L353`. | Operators may promote/use wrong status vocabulary. | Normalize copy by entity: reviewable items use `verified`; coverage uses `reviewed|locked`; planner uses reviewed/locked if confirmed. | copy/API contract test |
| P0 | Planner trust | `app/backend/app/study_os/plan_impact.py:L76-L90` | Plan impact ranks only `locked` rows while Workspace says reviewed also feeds planner. | Workspace copy: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L381-L385`. | Could incorrectly approve or diagnose Study OS visibility. | Audit Study OS consumption and align copy/backend comments. **[requires-backend if changing runtime]** | API/test/copy |
| P1 | CMS governance | `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L685-L697` | Bulk import mutation bypasses `useApiAction`. | Direct `api.post` in submit handler. | Inconsistent busy/error/success behavior and review rejection risk. | Wrap in `useApiAction`; keep per-row result drawer. | state |
| P1 | CMS governance | `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L729-L740` | Create mutation bypasses `useApiAction`. | Direct `api.post`; status state is local. | Same as above. | Use `useApiAction` with success/error messages; no optimistic state needed. | state |
| P1 | CMS governance | `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L816-L852` | Edit/retire mutations bypass `useApiAction`; retire uses `window.confirm/prompt`. | Direct `api.patch` and `api.del`. | Inconsistent a11y/focus and audit capture. | Replace prompt with controlled modal and use `useApiAction`. | state/a11y |
| P2 | CMS IA | `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L895-L907` | CMS entity selector is raw and includes technical slugs. | Options show `{label} · {key}`. | Slows non-technical operators, increases wrong-entity edits. | Split “Guided” entities from “Advanced raw tables”; hide raw labels under details. | layout/copy |
| P2 | CMS forms | `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L1025-L1032` | Required fields are marked but no pre-submit checklist or grouped flow. | Raw field loop renders all fields uniformly. | Admin discovers missing FK/enum only after submit. | Add per-entity helper/checklist and group required fields first. | layout/state |
| P2 | CMS table | `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L1094-L1158` | Raw row table truncates values and has limited context. | Values sliced to 60 chars at `L1115-L1117`. | Hard to verify row identity before edit/retire. | Add row detail drawer with full values and source/trust summary. | layout |
| P1 | Documents | `app/backend/app/api/admin_exam_intel_cms.py:L2883-L2925` | Stuck-document/job reset backend exists but UI does not expose it. | UI only has Status/Refresh in `ExamIntelDocuments.jsx:L333-L337`. | Failed extraction recovery requires operator/API knowledge. | Add “Reset stuck extraction” advanced action with reason. | API/state |
| P2 | Documents | `app/frontend/src/pages/admin/exam-workspace/panels/DocumentsPanel.jsx:L758-L763` | Processing warning has no “what to do if stuck/failed” action. | Static warning only. | Operators cannot recover from stuck extraction in Workspace. | Add retry/reset link or deep link to CMS diagnostics. | layout/API |
| P1 | Workspace mutations | `app/frontend/src/pages/admin/exam-workspace/panels/CompetitionPanel.jsx:L64-L67` | Competition lock bypasses `useApiAction`. | Direct `api.patch`. | Inconsistent mutation handling for trust-changing action. | Wrap lock/save in `useApiAction`. | state |
| P1 | Review activation | `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L95-L104` | Row lock bypasses `useApiAction`. | Direct `api.patch`. | Critical trust action lacks standard success/error behavior. | Use `useApiAction` and refresh readiness on success. | state |
| P2 | Workspace SmartHeader | `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:L96-L110` | “Next action” chooses highest-weight blocked section, which can skip earlier sequence prerequisites. | Sort by section weight only. | Admin may be sent to a later tab before completing documents/setup. | Prefer first blocker in tab order, with weight shown as severity. | state |
| P2 | Workspace cycle clarity | `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:L146-L162` | Cycle picker includes “All cycles” but panels vary in how cycle filters are applied. | Context/readiness include cycle query; Docs/PYQ also filter by cycle. | Admin may confuse aggregate vs cycle-bound readiness. | Add helper copy under picker: “All cycles = aggregate; selecting cycle filters docs/PYQ/readiness.” | copy |
| P2 | PYQ | `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/PyqWorkbenchPanel.jsx:L46-L80` | Empty PYQ state tells admins to create a paper in CMS but does not provide a path/action. | Only bulk-import button is present. | Core PYQ import journey stalls. | Add “Create PYQ paper” in context, then enable import. | layout/API |
| P1 | PYQ trust | `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:L49-L50` | Sensitive question edits/reviews use generic audit reason. | `AUDIT_REASON = "workspace reviewer action"`. | Audit trail may be insufficient for approvals/rejections. | Capture reason for review actions or structured review notes. | copy/state/API |
| P2 | Admin Review | `app/frontend/src/features/admin/exam-intelligence/ExamIntelligenceOverviewCards.jsx:L112-L124` | Low-confidence/stale counts are not actionable. | Cards show counts only. | Admin cannot find rows causing stale/low-confidence risk. | Link cards to filtered queue/workspace row lists. **[requires-backend for aggregate drilldown if missing]** | route/API |
| P2 | Admin Review | `app/frontend/src/features/admin/exam-intelligence/ExamListTable.jsx:L44-L48` | Table is count-oriented, not review-oriented. | Columns are counts/readiness only. | Admin lacks next approval context. | Add “next blocker” and “last reviewed/stale” columns. | layout/API |
| P3 | A11y | `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:L231-L304` | Tabs have `role=tab` but no `aria-controls`/`id` pairing and panels are not `tabpanel`. | Tab strip buttons only set `aria-selected`. | Screen-reader tab semantics are incomplete. | Add proper tab/panel attributes and keyboard arrow handling. | a11y |
| P3 | Modal a11y | `app/frontend/src/pages/admin/exam-workspace/syllabus-mapper/AcceptPreviewModal.jsx:L7-L15` | Modal focuses and handles Escape but does not trap tab loop. | Comment says “Trap focus” but code only focuses and listens for Escape. | Keyboard users can tab behind modal. | Use shared focus trap or implement cycling. | a11y |

## 6. Consistency audit

| Term | Where used | Observed meaning/mismatch |
|---|---|---|
| `verified` | Review page copy and reviewable item backend statuses. `ExamIntelligence.jsx:L121-L122`; `_ALLOWED_STATUSES` in `admin_exam_intelligence.py:L119-L120`; PYQ verify action in `PyqPaperWorkspace.jsx:L482-L493`. | Correct for syllabus mentions/PYQ questions/tags/policy updates, but confusing when used near coverage lifecycle where `verified` is invalid. |
| `locked` | Workspace trust legend and competition lock. `ExamWorkspace.jsx:L47-L54`; `CompetitionPanel.jsx:L56-L67`; `ReviewActivatePanel.jsx:L381-L385`. | Preferred live/planner state in Workspace; backend comments for topic coverage say only locked planner-ready at `admin_exam_intelligence.py:L600-L604`. |
| `reviewed` | Coverage lifecycle and Review & Activate copy. `ReviewActivatePanel.jsx:L42-L51`, `ReviewActivatePanel.jsx:L381-L385`; backend coverage pattern `admin_exam_intelligence.py:L588-L591`. | Coverage lifecycle uses reviewed; Admin Review top banner omits reviewed and says verified/locked. |
| `pending` | CMS force state for many item rows. `admin_exam_intel_cms.py:L12-L16`, `admin_exam_intel_cms.py:L2624-L2635`, `admin_exam_intel_cms.py:L2648-L2667`. | Correct for reviewable item rows, but coverage bulk import forces `pending_review`, not `pending`. |
| `pending_review` | Coverage lifecycle in frontend and backend. `ExamIntelCms.jsx:L52-L57`; `ReviewActivatePanel.jsx:L368-L385`; `admin_exam_intelligence.py:L588-L591`. | Correct for coverage, but CMS intro says “review_status / trust_status land at pending,” which is imprecise for coverage (`pending_review`) and competition (`draft`). Evidence: `ExamIntelCms.jsx:L887-L890`, `admin_exam_intel_cms.py:L2576-L2600`. |
| `needs_correction` | Reviewable item status maps. `SetupPanel.jsx:L8-L17`; `UpdatesPanel.jsx:L5-L14`; `PyqPaperWorkspace.jsx:L25-L30`. | Used as “needs fix” in badges. Coverage lifecycle does not include it; rejected/draft/reviewed/locked does. |
| `rejected` | Reviewable items and coverage lifecycle. `ReviewActivatePanel.jsx:L42-L51`; `PyqPaperWorkspace.jsx:L25-L30`. | Consistent as non-user-facing. |
| `active` | Exam active filter and cycle status. `ExamIntelligence.jsx:L217-L227`; `ExamWorkspace.jsx:L155-L160`. | “Active” can mean exam visible (`is_active`) or active cycle; UI should distinguish “Visible exam” vs “Active cycle.” |
| `activated` | Review & Activate title. `ExamWorkspace.jsx:L32-L33`; `ReviewActivatePanel.jsx:L178-L180`. | There is no one-click activation endpoint; activation is per-row lock. Copy mostly clarifies this at `ReviewActivatePanel.jsx:L186-L216`. |
| `planner-ready` | Review & Activate note and competition empty copy. `ReviewActivatePanel.jsx:L228-L244`; `CompetitionPanel.jsx:L117-L120`. | Good operator-facing concept; must be aligned with actual reviewed/locked runtime. |
| `user-facing` | Admin Review helper and safety banner. `ExamIntelligence.jsx:L33-L35`; `ExamIntelligence.jsx:L144-L148`; overview card `ExamIntelligenceOverviewCards.jsx:L127-L131`. | Good concept, but “verified or locked” should mention reviewed for coverage. |
| `CMS` | Admin CMS page, nav link “Create / Import CMS”. `ExamIntelligence.jsx:L125-L133`; `ExamIntelCms.jsx:L881-L890`. | Means both raw CRUD and document upload, causing raw DB editing feel. |
| `Workspace` | Exam list action and route. `ExamListTable.jsx:L73-L80`; `ExamWorkspace.jsx:L1-L10`. | Strong one-exam primary surface; should be the default journey after creation. |
| `Review queue` | CMS intro says promote through existing review queue. `ExamIntelCms.jsx:L887-L890`. | There is no obvious standalone queue route in the reviewed IA; Review & Activate and panels perform row locks. Clarify “Workspace Review & Activate / row review actions.” |

## 7. Data-state audit

| Page/panel | Loading | Empty | Error | Stale/retry | Mutation busy | Success/error msg | Demo-leak risk |
|---|---|---|---|---|---|---|---|
| Admin Review overview | No skeleton; cards render zero defaults while overview is null. Evidence: `ExamIntelligence.jsx:L182-L190`, `ExamIntelligenceOverviewCards.jsx:L46-L64`. | Not applicable. | Inline error if overview fails. Evidence: `ExamIntelligence.jsx:L184-L187`. | Refresh only by switching tab/reload; no overview retry button. | No mutations. | Error only. | No seed/demo fallback found. |
| Admin Review exams | `examsStatus` has idle/loading/data/empty/error. Evidence: `ExamIntelligence.jsx:L45-L47`, `ExamIntelligence.jsx:L272-L296`. | Table empty message. Evidence: `ExamListTable.jsx:L26-L31`. | Inline error. | Refresh button. Evidence: `ExamIntelligence.jsx:L261-L268`. | No mutations. | Error only. | No seed/demo fallback found. |
| CMS main | Busy flag and “Loading…” table row. Evidence: `ExamIntelCms.jsx:L627-L645`, `ExamIntelCms.jsx:L1107-L1110`. | “No rows.” row. | Inline err. Evidence: `ExamIntelCms.jsx:L951-L953`. | Reload button. Evidence: `ExamIntelCms.jsx:L911-L913`. | Local busy/editBusy; not `useApiAction`. | Status with audit_id for create/bulk/edit/retire. Evidence: `ExamIntelCms.jsx:L945-L948`. | No seed/demo fallback found. |
| CMS documents | No explicit list loading state; docs empty when exam missing or request pending. Evidence: `ExamIntelDocuments.jsx:L73-L84`, `ExamIntelDocuments.jsx:L310-L324`. | “No documents.” | Status error. | Reload/status buttons. Evidence: `ExamIntelDocuments.jsx:L310-L337`. | Busy upload/link local; not `useApiAction`. | Status live region. Evidence: `ExamIntelDocuments.jsx:L306-L308`. | No seed/demo fallback found. |
| Workspace shell | Skeleton. Evidence: `ExamWorkspace.jsx:L395-L405`. | No global empty. | Error with Retry. Evidence: `ExamWorkspace.jsx:L408-L416`. | Context retry; readiness errors are stored but not surfaced in shell. Evidence: `ExamWorkspaceContext.jsx:L19-L23`, `ExamWorkspaceContext.jsx:L45-L61`. | Panel-specific. | Panel-specific. | No seed/demo fallback found. |
| Workspace Documents | Loading skeleton, empty state, populated state. Evidence: `DocumentsPanel.jsx:L545-L593`, `DocumentsPanel.jsx:L599-L775`. | Strong empty copy. | Inline list/upload/link errors. Evidence: `DocumentsPanel.jsx:L573-L575`, `DocumentsPanel.jsx:L241-L241`, `DocumentsPanel.jsx:L372-L375`. | Refresh and polling; no reset UI. | Busy local; not `useApiAction`. | Errors only; upload success becomes in-flight row. | No seed/demo fallback found. |
| Syllabus Mapper | Proposal runner errors via hook; document selector disables when no docs. Evidence: `SyllabusMapperPanel.jsx:L53-L59`, `DocumentSelector.jsx:L42-L62`. | “No documents” select option. | Error passed to ProposalRunner; page text fetch silently empties. Evidence: `SyllabusMapperPanel.jsx:L23-L30`. | Re-run propose. | Direct `api.post`; not `useApiAction`. Evidence: `useSyllabusMapper.js:L17-L87`. | Modal preview and commit; commit errors stored in hook but not visibly cited in panel. | No seed/demo fallback found. |
| PYQ Workbench tab | Loading papers text. Evidence: `PyqWorkbenchPanel.jsx:L40-L50`. | “No PYQ papers…Create one in CMS.” | Inline error. | No retry button visible. | Bulk modal not reviewed here; embedded workspace direct mutations. | Embedded workspace local errors. | No seed/demo fallback found. |
| Updates | Loading button state. Evidence: `UpdatesPanel.jsx:L33-L45`, `UpdatesPanel.jsx:L112-L116`. | “No updates yet.” Evidence: `UpdatesPanel.jsx:L174-L179`. | Inline error. | Refresh. | Local busyId/savingNew; not `useApiAction`. | Error only; no explicit success. | No seed/demo fallback found. |
| Competition | Loading button state and empty card. Evidence: `CompetitionPanel.jsx:L38-L52`, `CompetitionPanel.jsx:L107-L129`. | Strong empty copy. | Inline error. | Refresh. | Local busyId/savingNew; not `useApiAction`. | Error only; no explicit success. | No seed/demo fallback found. |
| Review & Activate | Skeleton when readiness loading/missing. Evidence: `ReviewActivatePanel.jsx:L137-L152`. | Not applicable. | Row lock inline error. Evidence: `ReviewActivatePanel.jsx:L90-L127`. | Refetch after lock; no visible readiness_error. | Local loading; not `useApiAction`. | Error only. | No seed/demo fallback found. |

## 8. Accessibility + ergonomics

- [confirmed] Route-level error boundaries are incomplete for the reviewed routes; this is both resilience and governance. Evidence: `app/frontend/src/routes/adminRoutes.jsx:L80-L99`, `app/frontend/src/routes/adminRoutes.jsx:L106-L110`.
- [confirmed] Workspace tabs use `role="tablist"` and `role="tab"`, but lack `id`/`aria-controls`/`tabpanel` wiring and arrow-key behavior. Evidence: `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:L231-L304`.
- [confirmed] `AcceptPreviewModal` claims focus trap but only focuses the dialog and handles Escape, with no tab-loop trap. Evidence: `app/frontend/src/pages/admin/exam-workspace/syllabus-mapper/AcceptPreviewModal.jsx:L7-L15`, `app/frontend/src/pages/admin/exam-workspace/syllabus-mapper/AcceptPreviewModal.jsx:L20-L30`.
- [confirmed] Many form fields are technically labeled through wrapping `<label>`, but labels are database names (`exam_id`, `source_kind`, `reviewer_status`) rather than operator language. Evidence: `app/frontend/src/pages/admin/studyos/ExamIntelDocuments.jsx:L214-L300`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L1025-L1032`.
- [confirmed] Workspace Review & Activate is a good a11y pattern because status dots are paired with visible text and blockers are text labels, not color-only. Evidence: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L53-L68`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:L298-L321`.
- [confirmed] Raw CMS tables are dense and horizontally scrollable; good for advanced operators, but poor as a default guided path. Evidence: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L1094-L1158`.
- [confirmed] Retire uses `window.confirm` + `window.prompt`, which is not ideal for focus management or structured reason capture. Evidence: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:L830-L852`.

## 9. Redesign direction

- **Keep** `/admin/exam-intelligence` as the dashboard/review landing, but make the cards actionable and align status vocabulary.
- **Keep and promote** `/admin/exam-intelligence/workspace/:exam_id` as the primary one-exam admin surface. It already maps to operator workflow and readiness.
- **Hide under advanced** the raw table editor in CMS. CMS should default to guided entity flows (Exam, Cycle, Document, PYQ Paper, Topic Coverage), then expose raw CRUD/import for advanced fixes.
- **Rename/clarify** “Review queue” copy to “Workspace Review & Activate / row review actions” unless a separate queue route is added.
- **Merge conceptually** CMS Documents into Workspace Documents for normal flows; keep CMS Documents as advanced/library-level fallback.
- **Raw-admin fallback** should retain audit reason, forced pending states, and row detail views, but not be the first path for new exams.
- **Primary path proposal:** New guided exam → Workspace Setup → Documents → Syllabus Mapper/PYQ → Competition/Updates → Review & Activate → back to Review dashboard.

## 10. PR plan

1. **PR1 — Copy + IA alignment**
   - Wrap Exam Intelligence routes in `RouteErrorBoundary`.
   - Fix legacy redirect target or label.
   - Align status copy: verified vs reviewed vs locked, active vs retired vs archive.
   - Add direct CMS nav item only if renamed “Advanced CMS.”

2. **PR2 — State/error/loading governance**
   - Convert direct user mutations in CMS, Documents, Updates, Competition, ReviewActivate, Syllabus accept, and PYQ workspace to `useApiAction`.
   - Surface `readiness_error` in Workspace shell.
   - Add retries where missing.

3. **PR3 — Workspace next-action/readiness**
   - Make SmartHeader next action follow tab order with severity indicators.
   - Add cycle-scope helper copy.
   - Add “Why not planner-ready?” topic/section detail drawer.
   - Add row drilldowns from readiness blockers.

4. **PR4 — CMS guided flow**
   - Split CMS into Guided and Advanced modes.
   - Add in-context PYQ paper creation from PYQ Workbench.
   - Add row detail drawer and safer retire modal.
   - Expose stuck extraction reset/retry action with reason.

5. **PR5 — Tests**
   - Route-boundary tests for Exam Intelligence routes.
   - Mutation-governance tests or lint rule coverage for admin mutations.
   - Status vocabulary contract tests for coverage/policy/PYQ.
   - Journey tests for new exam → planner-ready and PYQ import.

## 11. Test plan

- **Route tests**
  - Assert `/admin/exam-intelligence`, `/cms`, `/workspace/:exam_id`, `/workspace/:exam_id/:cycle_id`, and `/pyq-papers/:id/workspace` render inside route error boundaries.
  - Assert `/admin/study-os/exam-intel-cms` redirects to the intended target.

- **Component tests**
  - Admin Review: filters produce expected query params and pagination labels.
  - ExamListTable: readiness/count columns and Workspace deep link render correctly.
  - CMS: required-field notices, reason validation, JSON metadata parse errors, forced-pending copy.
  - Workspace SmartHeader: blocker ordering and “Go to next action” tab routing.
  - Review & Activate: permission-gated lock buttons and blocker labels.
  - Documents: upload validation, in-flight polling states, failed/stuck recovery UI.
  - Syllabus Mapper modal: focus trap, reason validation, preview counts.
  - PYQ Workbench: empty state includes “Create PYQ paper” and bulk import disabled until paper exists.

- **API contract tests**
  - Coverage lifecycle accepts only `draft|pending_review|reviewed|locked|rejected`.
  - Policy/PYQ item review accepts only `pending|verified|rejected|needs_correction`.
  - CMS bulk import forces the documented status per entity.
  - Document link-to-syllabus creates/updates trust_status without auto-verifying.
  - Plan-impact/planner consumption contract pinned for `reviewed` vs `locked` rows. **[requires-backend if changing runtime]**

- **A11y smoke**
  - Keyboard tab/arrow navigation across Workspace tabs.
  - Modal focus trap and Escape behavior.
  - Retire/reset confirmation modal focus restore.
  - Table headers/labels for dense CMS tables.

- **Journey coverage**
  - New exam → add cycle/phase → upload/link syllabus → accept mentions → lock/review coverage → planner-ready note clears.
  - Corrigendum update → add policy update → verify official row → observe plan-impact copy.
  - PYQ import → create paper → upload/link PDF → bulk/import questions → verify rows → PYQ readiness changes.
  - Topic trace → open blocker drawer → inspect coverage/PYQ/syllabus evidence → resolve or explain non-use.

## Operator follow-up (separate; agent does none of these)

- Verify in a live/staging environment which Study OS runtime paths consume `exam_topic_coverage.reviewer_status='reviewed'` versus only `locked`; do not rely on Supabase Studio reads outside a wrapped transaction.
- Run SQL or authenticated PostgREST checks to list current stale/low-confidence rows and validate that dashboard counts match production data.
- Inspect live document-processing queues for stuck `document_assets`/`document_processing_jobs` before enabling reset actions broadly.
- Validate with real admin credentials that permission gates differ correctly between `exam_intelligence.cms` and `exam_intelligence.review`.
- If changing planner visibility semantics, run live/staging plan-generation smoke tests for an exam with only reviewed rows and an exam with locked rows.
