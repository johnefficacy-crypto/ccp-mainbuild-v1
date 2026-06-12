# Knowledge Governance Admin UX Review — Run A (trust-critical)

Date: 2026-06-12
Scope: `/admin/exam-intelligence`, `/admin/exam-intelligence/new`, `/admin/exam-eligibility`, `/admin/organizations`, `/admin/verification-reports`, `/admin/reverification-batches`, `/admin/ai-policy`, `/admin/persona`, plus wired subroutes under Exam Intelligence.

Prior review: `docs/reviews/exam-intel-ux-review.md` not found, deduping best-effort.

Run B status: deferred — run pass 2 for sections 9–13.

## 1. Executive summary

- **[partial]** Knowledge Governance is a plausible umbrella, but it currently mixes exam truth, org trust, verification/corrigendum propagation, read-only AI policy, and persona metadata without a landing page that explains the operator mental model or next action order. The nav places all eight items in one collapsed group and makes `/admin/exam-intelligence` the accidental hub rather than an explicit governance dashboard. [confirmed: `app/frontend/src/pages/admin/AdminShell.jsx:25-34`, `app/frontend/src/pages/admin/AdminShell.jsx:71-79`]
- **[implemented]** Exam Intelligence has the strongest trust copy: the page states verified/locked-only user-facing contract, CMS is labelled as a secondary path, and the workspace has readiness tabs plus a next-action header. [confirmed: `app/frontend/src/pages/admin/ExamIntelligence.jsx:139-149`, `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:96-102`, `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:350-360`]
- **[risky]** Exam Eligibility can push rules directly to `verified` from the form and one-click verify rows without a reason, confirmation, or required source URL, even though verified rules feed the user-facing eligibility summary. [confirmed: `app/frontend/src/pages/admin/ExamEligibility.jsx:96-130`, `app/frontend/src/pages/admin/ExamEligibility.jsx:155-164`, `app/backend/app/api/admin_exam_eligibility.py:23-25`, `app/backend/app/api/admin_exam_eligibility.py:240-242`]
- **[partial]** Organizations is correctly framed as trust, not CRM, and exposes history, but Verify only asks `Verify ${name}?` and the backend records `status=...` notes from URL checks rather than an explicit operator reason/evidence package. [confirmed: `app/frontend/src/pages/admin/Organizations.jsx:200-203`, `app/frontend/src/pages/admin/Organizations.jsx:180-182`, `app/backend/app/api/admin_trust.py:363-377`]
- **[implemented]** Verification Reports/Reverification Batches are the clearest official-change/corrigendum path: listing defaults to active reports, apply-registry-action is explicit, requires reason, and the backend documents it as the only path that applies report values into exam registry rows. [confirmed: `app/frontend/src/pages/admin/VerificationReports.jsx:1014-1017`, `app/frontend/src/pages/admin/VerificationReports.jsx:1049-1052`, `app/backend/app/api/admin_verification_reports.py:847-869`]
- **[confusing]** Verification Reports requires `admin`/`super_admin` in the frontend, while the backend uses `require_admin` for list/promote/reject/batches and `exam_intelligence.cms` for apply-registry-action. The page-level denial copy says role only and does not explain action-level permission differences. [confirmed: `app/frontend/src/pages/admin/VerificationReports.jsx:1071-1088`, `app/backend/app/api/admin_verification_reports.py:164-176`, `app/backend/app/api/admin_verification_reports.py:493-498`, `app/backend/app/api/admin_verification_reports.py:847-852`]
- **[confusing]** AI Governance is read-only in backend but the UI headline says “What the model is allowed to say,” which may overstate enforcement unless operators read the later “Phase-2 wires a real provider” copy. [confirmed: `app/frontend/src/pages/admin/AIPolicy.jsx:16-18`, `app/frontend/src/pages/admin/AIPolicy.jsx:35-39`, `app/backend/app/api/admin_ops.py:118-158`]
- **[implemented]** Persona copy explicitly prevents identity/eligibility misuse, but mutations bypass `useApiAction` and several fetch failures are swallowed into empty state; this weakens operator confidence in governance data. [confirmed: `app/frontend/src/pages/admin/Persona.jsx:187-199`, `app/frontend/src/pages/admin/Persona.jsx:130-158`, `app/frontend/src/pages/admin/Persona.jsx:161-169`]
- **[risky]** Status vocabulary is inconsistent across surfaces: Exam Eligibility uses `verified/archived`, Exam Workspace uses `draft/pending_review/reviewed/locked/rejected`, PYQ uses `pending/needs_correction/verified/rejected`, Verification Reports use lifecycle/recommended-action terms including `superseded`, and Organizations use `is_verified/trust_tier`. This is manageable only with a shared legend/landing page. [confirmed: `app/backend/app/api/admin_exam_eligibility.py:51-56`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:13-15`, `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:80-83`, `app/frontend/src/pages/admin/VerificationReports.jsx:833-838`, `app/frontend/src/pages/admin/Organizations.jsx:244-247`]
- **[missing]** There is no single cross-surface “what changed / what does it affect / what should I do next” board for knowledge governance. The best next-action affordance exists only inside Exam Workspace, not at the Knowledge Governance group level. [confirmed: `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:96-102`, `app/frontend/src/pages/admin/AdminShell.jsx:25-34`]

## 2. Files inspected

Discovery files inspected first:

- `AGENTS.md`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/wiki/index.md`
- `docs/reviews/exam-intel-ux-review.md` — not found.

Frontend route/nav files inspected:

- `app/frontend/src/routes/adminRoutes.jsx`
- `app/frontend/src/pages/admin/AdminShell.jsx`

Frontend wired surfaces inspected:

- `app/frontend/src/pages/admin/ExamIntelligence.jsx`
- `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx`
- `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx`
- `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx`
- `app/frontend/src/pages/admin/ExamEligibility.jsx`
- `app/frontend/src/pages/admin/Organizations.jsx`
- `app/frontend/src/pages/admin/VerificationReports.jsx`
- `app/frontend/src/pages/admin/ReverificationBatches.jsx`
- `app/frontend/src/pages/admin/AIPolicy.jsx`
- `app/frontend/src/pages/admin/Persona.jsx`
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx`
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx`
- `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx`
- `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx`

Backend wired files inspected:

- `app/backend/server.py`
- `app/backend/app/api/admin_exam_intelligence.py`
- `app/backend/app/api/admin_exam_intel_cms.py`
- `app/backend/app/api/admin_exam_intel_documents.py`
- `app/backend/app/api/admin_exam_eligibility.py`
- `app/backend/app/api/admin_trust.py` — actual Organizations backend; hint `app/backend/app/api/admin_organizations.py` not found.
- `app/backend/app/api/admin_verification_reports.py` — actual Verification Reports and Reverification Batches backend; hints `verification_reports.py` and `reverification_batches.py` not found.
- `app/backend/app/api/admin_ops.py` — actual AI policy backend; hint `app/backend/app/api/admin_ai_policy.py` not found.
- `app/backend/app/api/admin_persona.py`

Hint paths not found:

- `app/backend/app/api/organizations.py`
- `app/backend/app/api/admin_organizations.py`
- `app/backend/app/api/verification_reports.py`
- `app/backend/app/api/reverification_batches.py`
- `app/backend/app/api/admin_ai_policy.py`
- `app/backend/app/server.py` — actual path is `app/backend/server.py`.

Tests skimmed: deferred in Run B.

## 3. IA map

| Nav label | Route | Component | Backend endpoint(s) | Operator job | User-facing impact | Status/trust model | UX verdict |
|---|---|---|---|---|---|---|---|
| Exam Intelligence | `/admin/exam-intelligence` plus workspace subroutes | `ExamIntelligence.jsx`, `ExamWorkspace.jsx` | `/api/admin/exam-intelligence/*`, `/api/admin/exam-intelligence-cms/*` | Review exam intel readiness and open workspaces/CMS | Study OS/user-facing exam intelligence consumes verified/locked or reviewed/locked depending entity | verified/locked copy on review page; workspace lifecycle `draft → pending_review → reviewed → locked → rejected` | **Partial/strong:** good local mental model, no group-level landing. |
| New guided exam | `/admin/exam-intelligence/new` | `GuidedExamWizard.jsx` | `/api/admin/organizations`, `/api/admin/exam-intelligence-cms/exams`, `/exam-cycles`, `/exam-phases` | Create org/exam/cycle/phases in guided flow | Creates canonical exam identity and phase graph that later gates planner readiness | Hardcoded reason, create-log statuses `pending/ok/error` | **Partial:** guided, resumable, but no explicit “not planner-ready until workspace locks rows” after create. |
| Add cycle | `/admin/exam-intelligence/exams/:exam_id/add-cycle` | `AddCycleWizard.jsx` | `/api/admin/exam-intelligence-cms/exam-cycles`, `/exam-phases` | Add cycle and clone/create phases | Creates cycle-bound phase truth for exam registry | create-log `pending/ok/error` | **Partial:** good collision checks, but same planner-ready handoff gap. |
| Exam Eligibility | `/admin/exam-eligibility` | `ExamEligibility.jsx` | `/api/admin/exam-eligibility/*` | Set baseline exam-level eligibility rules | Verified rows feed user-facing eligibility summary | `draft/verified/archived` | **Risky:** source fields optional, verify is one click, no audit row visible/confirmed. |
| Organizations | `/admin/organizations` | `Organizations.jsx` | `/api/admin/organizations`, `/verify`, `/audit` from `admin_trust.py` | Maintain official org/domain trust registry | Org trust influences source/recruitment coverage and trust UI | `is_verified`, `trust_tier`, `verified_at`, audit timeline | **Partial:** correct trust framing, verify needs stronger evidence/reason display. |
| Verification Reports | `/admin/verification-reports` | `VerificationReports.jsx` | `/api/admin/verification-reports/*` | Review official-source changes, promote/reject, resolve conflicts, apply registry actions | Can create/promote recruitment truth and apply corrigenda into exam registry | `lifecycle_status`, `criticality_tier`, `recommended_action`, `superseded`, rejection notes | **Implemented/complex:** powerful but dense; permission copy too coarse. |
| Reverification Batches | `/admin/reverification-batches` | `ReverificationBatches.jsx` | `/api/admin/reverification-batches`, `/api/admin/verification-reports/acknowledge-batch/{id}` | Release mass-change batches into verification queue | Controls whether changed official-source reports enter operator queue | acknowledged/unacknowledged, promoted count | **Partial:** clear queue copy, but affected-report navigation is unwired. |
| AI Governance | `/admin/ai-policy` | `AIPolicy.jsx` | `/api/admin/ai-policy` | View guardrail rules and telemetry | Operator perception of AI safety controls | `active`, rule `enabled/off`, model/swap target | **Confusing:** backend is read-only policy/telemetry; headline implies enforceable controls. |
| Persona | `/admin/persona` | `Persona.jsx` | `/api/admin/persona/*` | Inspect/adjust internal persona questions, snapshots, queue, events | Personalization metadata affects Study OS policy outputs, not truth | active/inactive, queue statuses, snapshots | **Partial:** safety copy is strong; mutation/error handling weakens trust. |

## 4. Cross-surface workflow map

### Current actual flow

1. **Identity creation:** Operator starts at New guided exam, selects/creates organization, then creates exam/cycle/phases through CMS endpoints with a fixed reason. [confirmed: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:176-190`, `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:629-665`, `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:693-755`]
2. **Cycle extension:** Existing exam cycles are added through Add Cycle Wizard; it pre-checks slug collisions and creates cycle + template/cycle-bound phases through CMS endpoints. [confirmed: `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx:150-176`, `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx:471-539`, `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx:670-678`]
3. **Readiness work:** Exam Workspace provides Setup, Documents, Syllabus Mapper, PYQ Workbench, Updates, Competition, and Review & Activate tabs; the header computes current stage and next blocker. [confirmed: `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:25-33`, `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:90-110`]
4. **Trust publication:** Review & Activate locks directly reviewable rows; comments state there is no one-click activate endpoint and planner consumes locked preferred or reviewed. [confirmed: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:1-15`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:95-105`]
5. **Baseline eligibility:** Exam Eligibility separately creates/updates/verifies baseline user-facing rules. [confirmed: `app/frontend/src/pages/admin/ExamEligibility.jsx:184-187`, `app/frontend/src/pages/admin/ExamEligibility.jsx:96-130`, `app/frontend/src/pages/admin/ExamEligibility.jsx:155-164`]
6. **Org/source changes:** Organizations separately verifies official domains and exposes audit. [confirmed: `app/frontend/src/pages/admin/Organizations.jsx:200-203`, `app/frontend/src/pages/admin/Organizations.jsx:180-182`]
7. **Official changes/corrigenda:** Reverification Batches release changed official-source reports; Verification Reports review/promote/reject/override/apply registry actions. [confirmed: `app/frontend/src/pages/admin/ReverificationBatches.jsx:39-43`, `app/frontend/src/pages/admin/ReverificationBatches.jsx:22-32`, `app/backend/app/api/admin_verification_reports.py:847-869`]
8. **AI/persona guardrails:** AI policy is view-only; Persona is internal metadata with explicit non-overriding copy. [confirmed: `app/backend/app/api/admin_ops.py:118-158`, `app/frontend/src/pages/admin/Persona.jsx:192-200`]

### Recommended end-to-end flow

- Add a **Knowledge Governance landing page** that is the explicit start point for the group: “Create/changed official truth → review evidence → lock/publish → inspect downstream effects.” [requires-backend only if dashboard aggregates are not already available]
- Keep Exam Intelligence as the advanced/exam-readiness workspace, but make New Guided Exam and Add Cycle conclude with a visible checklist: “Created identity; next required: add documents, map syllabus, import/review PYQs, review updates/competition, lock rows.” [copy/layout]
- Put Exam Eligibility in a separate “User truth” lane and require a source URL or explicit “source unavailable” reason before verify. [requires-backend]
- Put Organizations, Verification Reports, and Reverification Batches in an “Official-source trust and change propagation” lane with cross-links: org → reports using org/source; batch → affected reports; report → affected exam/cycle/eligibility/Study OS. [requires-backend for missing aggregations]
- Keep AI Governance and Persona in an “AI/personalization guardrails” lane with copy that neither surface creates official truth. [copy/layout]

## 5. Deep findings table

| Priority | Surface | File:line | Finding | Code evidence | Admin impact | User-truth risk | Recommendation | Impl type |
|---|---|---|---|---|---|---|---|---|
| P1 | KG IA | `AdminShell.jsx:25-34` | Eight KG items are peers with no landing page or lane explanation. | The nav list places Exam Intelligence, wizard, eligibility, orgs, verification, batches, AI, Persona together. | New operators must infer order and relationships. | Mis-sequencing can leave created exams not planner-ready or eligibility unverified. | Add KG landing/next-action dashboard and group sub-lanes. | route/layout/copy |
| P2 | Routes | `adminRoutes.jsx:80-87`, `adminRoutes.jsx:98-99`, `adminRoutes.jsx:106-110` | Only Verification Reports/Reverification Batches are wrapped in `RouteErrorBoundary`; KG route peers are not. | Routes 80–87 are direct elements, while 107–110 wrap only two routes. | One page crash can blank admin shell for key governance surfaces. | Medium: operators may lose context mid-review. | Wrap all KG routes in `RouteErrorBoundary` per governance. | route/a11y/state |
| P0 | Exam Eligibility | `ExamEligibility.jsx:96-130`, `ExamEligibility.jsx:155-164` | User-facing eligibility rules can be saved or verified without mandatory source/reason/confirmation. | Payload sends optional `source_url/source_notes`; verify sends only `{ reviewer_status: "verified" }`. | Easy to publish unsubstantiated baseline rules. | High: verified rules feed public eligibility summary. | Require evidence URL or explicit reason and confirmation for verify/archive. [requires-backend] | API/state/copy |
| P1 | Exam Eligibility | `admin_exam_eligibility.py:200-251`, `admin_exam_eligibility.py:254-330`, `admin_exam_eligibility.py:333-366` | Backend stamps verified_by/verified_at but no `admin_audit_logs` write is present in inspected create/update/delete paths. | Create/update/delete perform table insert/update/delete and return rule, with cache invalidation. | Operators cannot see who changed what/why in the admin UI. | High for disputed eligibility truth. | Add eligibility audit endpoint/timeline and reason field for trust-changing transitions. [requires-backend] | API/audit |
| P2 | Organizations | `Organizations.jsx:180-182`, `admin_trust.py:363-377` | Verify uses a generic confirm and backend-derived `verification_notes`, not an operator reason/evidence form. | FE calls verify with `{}`; BE runs URL checks and audits before/after payload. | Trust action lacks visible operator rationale. | Medium: org domain trust can validate downstream source/recruitment confidence. | Replace confirm with review dialog showing checks/warnings/errors and reason/evidence. [requires-backend for reason persistence] | copy/state/API |
| P2 | Reverification Batches | `ReverificationBatches.jsx:91-96` | `onOpenAffected` and `onSnooze` are explicitly null. | Batch alert receives no affected-report navigation or snooze handler. | Operators can acknowledge but cannot inspect affected work from this page. | Medium: official changes may be released without understanding blast radius. | Wire “open affected reports” to filtered Verification Reports and hide/disable snooze with explanation. | route/layout |
| P1 | Verification Reports permissions | `VerificationReports.jsx:1071-1088`, `admin_verification_reports.py:847-852` | Page-level role check hides/permits the whole page, but apply-registry-action has a separate `exam_intelligence.cms` permission. | FE says admin/super_admin role required; BE requires permission for registry action. | Operators can be surprised by action-level 403. | Medium: critical corrigendum may stall. | Show action-level permission affordance and disabled states for registry actions. | permission/copy/state |
| P2 | AI Governance | `AIPolicy.jsx:16-18`, `admin_ops.py:118-158` | UI headline implies model-allowance control while backend only returns constants/telemetry. | Backend endpoint is GET-only and returns rules/model/telemetry. | Operators may assume toggles/enforcement exist. | Medium: AI safety posture could be overstated. | Rename to “AI policy viewer” and add “read-only, code-versioned constants” copy. | copy/layout |
| P2 | Persona | `Persona.jsx:130-158`, `Persona.jsx:161-169` | Persona mutations use raw `api.patch/post`; queue processing swallows errors. | Patch/toggle/process queue call API directly; process queue catch is `soft-fail`. | Operator cannot trust whether action happened. | Low/medium: persona must not affect truth, but can affect Study OS personalization. | Convert mutations to `useApiAction`; show failure/success and audit if available. | state/mutation |
| P2 | CMS | `ExamIntelCms.jsx:669-699`, `ExamIntelCms.jsx:701-740`, `ExamIntelCms.jsx:816-824` | CMS create/import/edit use raw API calls rather than `useApiAction`, although reasons/audit IDs are present. | Direct `api.post/patch` with local status. | Busy/error/rollback patterns vary from governance standard. | Medium for bulk import operator confidence. | Incrementally migrate trust-changing CMS mutations to `useApiAction` without weakening reason requirements. | state/mutation |
| P3 | CMS retire | `ExamIntelCms.jsx:830-847` | Retire uses `window.confirm` + `window.prompt`; reason is captured but UX is brittle. | Prompt asks for ≥8 chars and sends reason query param. | Poor audit-quality input and inaccessible modal behavior. | Low/medium: retire hides active identity rows. | Replace with accessible confirmation dialog with downstream effect copy. | a11y/copy/state |
| P2 | Guided exam | `GuidedExamWizard.jsx:611-647`, `GuidedExamWizard.jsx:765-805` | Wizard has resumable create log, but post-success copy does not clearly state planner-ready blockers. | Creation log tracks ok/error; review summary is identity/cycle/phase focused. | Operator may think created exam is done. | Medium: empty/partial exams can remain not planner-ready. | Add success next-step panel to open workspace/readiness and set eligibility. | copy/layout |
| P2 | Workspace terminology | `ExamWorkspace.jsx:47-53`, `ReviewActivatePanel.jsx:13-15` | Workspace legend says verified = reviewed not live and locked = live to aspirants, while page-level Exam Intelligence says verified or locked feed user-facing data. | Two related but different vocabulary contracts appear across EI surfaces. | Operators can confuse `verified` vs `reviewed` vs `locked`. | Medium: wrong status chosen for planner/readiness. | Add per-entity status legend and avoid using `verified` for coverage lifecycle copy. | copy/test |
| P2 | PYQ workspace | `PyqPaperWorkspace.jsx:80-83`, `PyqPaperWorkspace.jsx:470-492` | PYQ review uses `pending/needs_correction/verified/rejected`, separate from workspace coverage `reviewed/locked`. | Sorting/status actions use PYQ-specific lifecycle. | Mixed status terms inside one workspace without cross-legend mapping. | Medium: PYQ scoring/readiness handoff can be misunderstood. | Add PYQ-specific trust legend and downstream effect note. | copy/layout |

## 6. Workflow reviews

### 6.1 New exam zero → planner-ready

- **Route/component:** `/admin/exam-intelligence/new` is wired to `AdminGuidedExamWizard`; workspace routes are wired separately. [confirmed: `app/frontend/src/routes/adminRoutes.jsx:80-86`]
- **API path:** The wizard optionally creates an organization, then creates exam, cycle, and phases through CMS endpoints. [confirmed: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:629-665`, `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:693-755`]
- **Success path:** Creation log can resume partial failures and mark entries ok/error. [confirmed: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:611-647`]
- **Friction/broken path:** Organization lookup failures become an empty list; no explicit error tells the operator org search failed. [confirmed: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:183-190`]
- **Missing next action:** The created identity path does not explicitly require Exam Workspace readiness, row locking, and Exam Eligibility baseline before planner-ready. Recommendation: add a success checklist linking to workspace + eligibility. [requires-backend only for aggregated readiness if not already in readiness endpoint]

### 6.2 Add cycle to existing exam

- **Route/component:** `/admin/exam-intelligence/exams/:exam_id/add-cycle` is wired to `AdminAddCycleWizard`. [confirmed: `app/frontend/src/routes/adminRoutes.jsx:83`]
- **API path:** Creates `exam-cycles` and `exam-phases` through CMS with `REASON`. [confirmed: `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx:471-539`]
- **Good trust control:** It checks template slug collisions and same-year cycle-bound slug collisions before create. [confirmed: `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx:150-176`]
- **Success path:** Success panel opens cycle workspace. [confirmed: `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx:670-678`]
- **Gap:** The flow does not explain that new cycle phases are not enough; updates, PYQs, syllabus, competition, and lock/review steps still determine readiness. Recommendation: add “cycle created, not planner-ready yet” copy.

### 6.3 Set baseline exam eligibility

- **Route/component:** `/admin/exam-eligibility` is wired to `AdminExamEligibility`. [confirmed: `app/frontend/src/routes/adminRoutes.jsx:87`]
- **API path:** `/api/admin/exam-eligibility/exams`, `/rules`, create/update/delete endpoints. [confirmed: `app/backend/app/api/admin_exam_eligibility.py:1-25`]
- **Success path:** Create/update refreshes rules and exam counts. [confirmed: `app/frontend/src/pages/admin/ExamEligibility.jsx:122-134`]
- **Risk:** Verified rows feed user-facing summary, but verify action is a direct PUT with no reason/evidence requirement. [confirmed: `app/frontend/src/pages/admin/ExamEligibility.jsx:184-187`, `app/frontend/src/pages/admin/ExamEligibility.jsx:155-164`]
- **Recommendation:** Require source URL or explicit source waiver, reason, confirmation, and audit timeline before status can become verified. [requires-backend]

### 6.4 Verify an organization

- **Route/component:** `/admin/organizations` is wired to `AdminOrganizations`. [confirmed: `app/frontend/src/routes/adminRoutes.jsx:66`]
- **API path:** FE calls `POST /api/admin/organizations/{id}/verify`; BE requires `organizations.manage`. [confirmed: `app/frontend/src/pages/admin/Organizations.jsx:180-181`, `app/backend/app/api/admin_trust.py:363-377`]
- **Success path:** Backend runs URL checks, updates trust fields, and writes audit. [confirmed: `app/backend/app/api/admin_trust.py:370-377`]
- **Gap:** FE does not preview URL-check warnings/errors before the operator commits, and no reason/evidence is collected. Recommendation: show a verify dialog with check output, reason, and domain/evidence confirmation. [requires-backend if reason must persist]

### 6.5 Official change / corrigendum propagation

- **Route/component:** `/admin/reverification-batches` and `/admin/verification-reports` are wired; reports are behind `RouteErrorBoundary`. [confirmed: `app/frontend/src/routes/adminRoutes.jsx:106-110`]
- **API path:** Reverification batches list unacknowledged rows and acknowledge batches; Verification Reports can promote/reject, resolve conflicts, and apply registry actions. [confirmed: `app/backend/app/api/admin_verification_reports.py:766-808`, `app/backend/app/api/admin_verification_reports.py:493-617`, `app/backend/app/api/admin_verification_reports.py:847-869`]
- **Strong control:** Apply registry action is documented as the only path moving report values into exam registry and requires an explicit reason. [confirmed: `app/backend/app/api/admin_verification_reports.py:853-869`, `app/backend/app/api/admin_verification_reports.py:841-852`]
- **Gap:** Batch UI cannot open affected reports from the batch page. [confirmed: `app/frontend/src/pages/admin/ReverificationBatches.jsx:91-96`]
- **Recommendation:** Add batch → affected reports link and report → affected downstream surfaces (exam/cycle/eligibility/study) panel. [requires-backend if affected-report filtering is not already exposed]

### 6.6 AI policy safety (enforceable vs read-only)

- **Route/component:** `/admin/ai-policy` is wired to `AdminAIPolicy`. [confirmed: `app/frontend/src/routes/adminRoutes.jsx:78`]
- **API path:** `GET /api/admin/ai-policy` from `admin_ops.py` requires admin and returns rules/model/telemetry. [confirmed: `app/frontend/src/pages/admin/AIPolicy.jsx:6-18`, `app/backend/app/api/admin_ops.py:118-158`]
- **Gap:** UI headline implies enforceable model-allowance, but there are no controls and copy later says Phase-2 wires a real provider/logs. Recommendation: label it “AI policy viewer (read-only)” and surface telemetry limitations. [copy]

### 6.7 Persona governance (cannot override deterministic eligibility/official truth)

- **Route/component:** `/admin/persona` is wired to `AdminPersona`. [confirmed: `app/frontend/src/routes/adminRoutes.jsx:79`]
- **API path:** `/api/admin/persona/*` requires `persona.manage`. [confirmed: `app/backend/app/api/admin_persona.py:27-30`, `app/backend/app/api/admin_persona.py:339-344`, `app/backend/app/api/admin_persona.py:580-584`]
- **Strong copy:** Page states persona is internal metadata and must not override deterministic eligibility or official recruitment data. [confirmed: `app/frontend/src/pages/admin/Persona.jsx:187-199`]
- **Gap:** Mutations use raw API and errors can be swallowed. [confirmed: `app/frontend/src/pages/admin/Persona.jsx:130-169`]
- **Recommendation:** Keep non-truth copy, convert mutations to `useApiAction`, and show recompute queue result/error.

## 7. Status vocabulary matrix

| Term | Exam Intelligence / Workspace | CMS / PYQ | Exam Eligibility | Organizations | Verification / Reverification | AI Governance | Persona |
|---|---|---|---|---|---|---|---|
| draft | Workspace lifecycle starts at draft. [confirmed: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:13-15`] | Some rows land pending, not necessarily draft. | Allowed reviewer status. [confirmed: `app/backend/app/api/admin_exam_eligibility.py:51-56`] | — | — | — | — |
| pending | Exam Intelligence page says pending never reaches aspirants. [confirmed: `app/frontend/src/pages/admin/ExamIntelligence.jsx:144-148`] | PYQ status sort includes pending. [confirmed: `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:80-83`] | — | Unverified orgs shown as pending. [confirmed: `app/frontend/src/pages/admin/Organizations.jsx:244-247`] | Reverification pending reports are released to queue. [confirmed: `app/backend/app/api/admin_verification_reports.py:795-799`] | Swap target badge is pending. [confirmed: `app/frontend/src/pages/admin/AIPolicy.jsx:16-18`] | Queue has pending. [confirmed: `app/backend/app/api/admin_persona.py:548-560`] |
| pending_review | Workspace lifecycle term. [confirmed: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:13-15`] | — | — | — | — | — | — |
| reviewed | Workspace lifecycle; planner consumes reviewed/locked. [confirmed: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:13-15`] | — | — | — | — | — | — |
| verified | Exam Intelligence page says verified/locked feed user-facing data. [confirmed: `app/frontend/src/pages/admin/ExamIntelligence.jsx:139-149`] | PYQ questions use verified. [confirmed: `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:80-83`] | Verified rules feed user-facing summary. [confirmed: `app/frontend/src/pages/admin/ExamEligibility.jsx:184-187`] | Org `is_verified` and `trust_tier=verified`. [confirmed: `app/backend/app/api/admin_trust.py:372-376`] | — | — | — |
| locked | Workspace terminal status; planner-ready row lock. [confirmed: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:95-105`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:196-198`] | — | — | — | — | — | — |
| active / is_active | Exam CMS retire hides by `is_active=false`. [confirmed: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:830-847`] | Same. | — | — | Verification list defaults active non-superseded. [confirmed: `app/frontend/src/pages/admin/VerificationReports.jsx:1014-1017`] | Backend returns `active: True`. [confirmed: `app/backend/app/api/admin_ops.py:147-158`] | Question bank has active/inactive toggles. [confirmed: `app/frontend/src/pages/admin/Persona.jsx:148-158`] |
| archived | — | Retire copy distinguishes hidden/inactive. [confirmed: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:830-847`] | Soft-delete status archived. [confirmed: `app/backend/app/api/admin_exam_eligibility.py:19-21`, `app/backend/app/api/admin_exam_eligibility.py:357-366`] | — | — | — | — |
| rejected | Workspace lifecycle rejected. [confirmed: `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:13-15`] | PYQ rejected. [confirmed: `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:80-83`] | — | — | Report reject requires reason and lifecycle update. [confirmed: `app/frontend/src/pages/admin/VerificationReports.jsx:604-620`, `app/backend/app/api/admin_verification_reports.py:593-617`] | — | — |
| needs_correction | — | PYQ status sort/filter includes needs_correction. [confirmed: `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:80-83`, `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx:140-146`] | — | — | — | — | — |
| stale | Not observed in inspected wired UI. | Not observed. | Not observed. | Not observed. | Not observed. | Not observed. | Not observed. |
| superseded | — | — | — | — | Reports default to non-superseded. [confirmed: `app/frontend/src/pages/admin/VerificationReports.jsx:1014-1017`, `app/backend/app/api/admin_verification_reports.py:168-180`] | — | — |
| acknowledged / unacknowledged | — | — | — | — | Batches page is unacknowledged queue; backend filters `acknowledged_at` by default. [confirmed: `app/frontend/src/pages/admin/ReverificationBatches.jsx:39-43`, `app/backend/app/api/admin_verification_reports.py:766-787`] | — | — |
| planner-ready | Workspace uses “ready to activate” and “planner-ready.” [confirmed: `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:100-102`, `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx:196-198`] | — | — | — | — | — | — |
| user-facing | EI and eligibility explicitly state downstream visibility. [confirmed: `app/frontend/src/pages/admin/ExamIntelligence.jsx:139-149`, `app/frontend/src/pages/admin/ExamEligibility.jsx:184-187`] | PYQ source notice references scoring feed. [confirmed: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:293-296`] | yes | indirect | yes for promoted/registry-applied truth | policy perception only | no identity copy. [confirmed: `app/frontend/src/pages/admin/Persona.jsx:196-199`] |
| internal / admin-only | Exam Intelligence header says internal. [confirmed: `app/frontend/src/pages/admin/ExamIntelligence.jsx:112-123`] | CMS secondary/advanced. [confirmed: `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:350-360`] | Admin only via permission. | Admin trust registry. | Admin queue. | Admin policy view. | Persona controls internal. [confirmed: `app/frontend/src/pages/admin/Persona.jsx:181-199`] |

## 8. Permission + audit matrix

| Action | FE file | BE endpoint | Required perm/role | Reason required? | Audit written? | Evidence visible? | Reversal path? | Gap |
|---|---|---|---|---|---|---|---|---|
| Create exam/cycle/phase via wizard | `GuidedExamWizard.jsx` | `/api/admin/exam-intelligence-cms/{entity}` | `exam_intelligence.cms` (CMS backend) | Fixed `REASON` sent by wizard | CMS audit helper writes `admin_audit_logs`. [confirmed: `app/backend/app/api/admin_exam_intel_cms.py:81-104`] | Minimal; identity data only | Manual CMS edit/retire | Reason is generic, not operator-entered. |
| Add cycle | `AddCycleWizard.jsx` | `/api/admin/exam-intelligence-cms/exam-cycles`, `/exam-phases` | `exam_intelligence.cms` | Fixed `REASON` | CMS audit helper | Minimal | Manual CMS edit/retire | Missing post-create readiness handoff. |
| CMS bulk import | `ExamIntelCms.jsx` | `/api/admin/exam-intelligence-cms/bulk-import` | `exam_intelligence.cms` | Yes, ≥8 chars FE | CMS returns `audit_id`. [confirmed: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:669-699`] | Row payload/source fields vary by entity | Entity-specific edit/retire | Raw mutation; no consistent rollback/busy. |
| CMS create/edit | `ExamIntelCms.jsx` | `/api/admin/exam-intelligence-cms/{entity}` and `/{id}` | `exam_intelligence.cms` | Yes, ≥8 chars FE | CMS returns `audit_id`. [confirmed: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:701-740`, `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:816-824`] | Varies | Edit or retire | Raw mutation. |
| CMS retire | `ExamIntelCms.jsx` | `DELETE /api/admin/exam-intelligence-cms/{entity}/{id}?reason=` | `exam_intelligence.cms` | Yes via prompt | CMS returns `audit_id`. [confirmed: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:830-847`] | No effect preview | No obvious restore UI | `window.prompt`/confirm inaccessible and weak. |
| Lock workspace row | `ReviewActivatePanel.jsx` | `PATCH /api/admin/exam-intelligence/{entity}/{id}/review` | `exam_intelligence.review` per comment | No reason in FE | [needs-check: `app/backend/app/api/admin_exam_intelligence.py` review endpoints for audit] | Row evidence varies | Review status can likely be changed | Missing reason/confirmation for planner-ready lock. |
| PYQ question review | `PyqPaperWorkspace.jsx` | `PATCH /api/admin/exam-intelligence/items/pyq_question/{id}/review` | [needs-check: endpoint permission in `admin_exam_intelligence.py`] | Notes optional | [needs-check: endpoint audit] | Source PDF preview for source-backed rows | Can set other statuses | Status model differs from workspace legend. |
| Create/update/archive eligibility rule | `ExamEligibility.jsx` | `/api/admin/exam-eligibility/*` | `exam_eligibility.manage` | No | No `admin_audit_logs` write observed in inspected paths | Source URL/notes optional | Archive/unarchive via status edit | P0/P1 trust gap for user-facing rules. |
| Verify organization | `Organizations.jsx` | `POST /api/admin/organizations/{id}/verify` | `organizations.manage` | No | Yes, `_audit` called | Website/domain/checks returned but not previewed | Edit URL resets `is_verified=false`. [confirmed: `app/backend/app/api/admin_trust.py:1023-1031`] | Needs evidence/reason dialog. |
| Edit organization | `Organizations.jsx` | `PUT /api/admin/organizations/{id}` | `organizations.manage` | No | Yes, `_audit` called | Website/domain visible | Edit URL/domain resets verified false | Good reset; reason missing. |
| View org audit | `Organizations.jsx` | `GET /api/admin/organizations/{id}/audit` | `organizations.manage` | N/A | Reads audit | Yes, before/after/notes available | N/A | Good, but not tied to verify form. |
| Promote verification report | `VerificationReports.jsx` | `POST /api/admin/verification-reports/{id}/promote` | `require_admin` + `user_has_action(ACTION_PROMOTE)` | No FE reason | Promotion flow likely writes downstream audit in canonical path [needs-check: promotion service] | Report detail card | Reject/other lifecycle | Reasonless promote may be acceptable if report is evidence package; add visible “why safe” gate. |
| Reject verification report | `VerificationReports.jsx` | `POST /api/admin/verification-reports/{id}/reject` | `require_admin` + action gate | Yes, 8–500 chars | Rejection notes stored | Report detail | Lifecycle transition matrix | Good reason handling. |
| Override verification conflict | `VerificationReports.jsx` | `POST /api/admin/verification-reports/{id}/override-conflict` | `require_admin` + `recruitments.manage` unless super_admin | Yes | Override row stores audit trail | Optional evidence URL | Conflict marked resolved | Good; FE should expose permission before submit. |
| Apply registry action | `VerificationReports.jsx` | `POST /api/admin/verification-reports/{id}/apply-registry-action` | `exam_intelligence.cms` | Yes, 8–500 chars | Backend says CMS service writes audit + `exam_registry_actions` row | Report detail plus chosen FK | New registry edit action needed | Strongest audit model; permission copy gap. |
| Acknowledge reverification batch | `ReverificationBatches.jsx` | `POST /api/admin/verification-reports/acknowledge-batch/{id}` | `require_admin` + action gate | No | `acknowledge_batch` records acknowledged_by [needs-check: service audit] | Batch card only | No snooze/open affected | Need affected-report inspection before release. |
| AI policy view | `AIPolicy.jsx` | `GET /api/admin/ai-policy` | `require_admin` | N/A | N/A | Rules/telemetry | Read-only | Rename/read-only clarity. |
| Persona question toggle/edit | `Persona.jsx` | `PATCH /api/admin/persona/question-bank/{key}` | `persona.manage` | No | No audit observed in inspected patch path | Question row only | Toggle/edit again | UseApiAction + audit reason if operator-trust critical. |
| Persona queue process | `Persona.jsx` | `POST /api/admin/persona/recompute-queue/process` | `persona.manage` | No | [needs-check: persona queue service audit] | Queue rows | Recompute again | FE soft-fails errors. |

## Operator follow-up (Run A)

These require live DB, credentials, SQL, or production-like data and were not executed by the agent:

1. Verify actual `exam_eligibility_rules` auditability in Supabase: whether triggers or DB-level audit logs exist despite no API `_audit` call in `admin_exam_eligibility.py`.
2. Inspect live permission assignments for `exam_intelligence.cms`, `exam_intelligence.review`, `exam_eligibility.manage`, `organizations.manage`, `persona.manage`, and verification-report action gates to confirm admin/super_admin parity.
3. Use transaction-wrapped RLS checks for direct PostgREST reads of admin-touching KG tables if any frontend ever bypasses FastAPI.
4. Confirm with live data whether “reviewed or locked rows feed planner; locked preferred” is true per entity for topic coverage/competition/PYQ-derived planner inputs.
5. Review live reverification batch records to define affected-report filters and blast-radius summaries before wiring UI.
<!-- Run B appended sections only. Note: this file was not present in the working tree at review time, so sections 9ΓÇô13 are recorded here without rewriting sections 1ΓÇô8. -->

## 9. Cross-surface navigation and route-guard consistency

**Finding:** Needs follow-up. The sidebar correctly groups the knowledge-governance surfaces under one collapsible section: Exam Intelligence, New guided exam, Exam Eligibility, Organizations, Verification Reports, Reverification Batches, AI Governance, and Persona. Evidence: `app/frontend/src/pages/admin/AdminShell.jsx:25-34`. The corresponding admin routes exist for those entries, including the exam workspace and cycle wizard deep links. Evidence: `app/frontend/src/routes/adminRoutes.jsx:78-87`, `app/frontend/src/routes/adminRoutes.jsx:106-110`.

**UX risk:** Route-level error isolation is inconsistent. `RouteErrorBoundary` is imported, but only wraps Verification Reports and Reverification Batches; the main knowledge-governance routes (`/admin/exam-intelligence`, `/admin/exam-intelligence/new`, workspace routes, `/admin/exam-eligibility`, `/admin/organizations`, `/admin/ai-policy`, `/admin/persona`) sit directly inside the protected admin shell. Evidence: `app/frontend/src/routes/adminRoutes.jsx:1-5`, `app/frontend/src/routes/adminRoutes.jsx:78-87`, `app/frontend/src/routes/adminRoutes.jsx:106-110`. That means a render crash in one high-risk governance surface can take down the broader admin shell instead of landing in the standard boundary.

**Recommendation:** Wrap every knowledge-governance route block in `<RouteErrorBoundary>` to match the frontend governance contract and the existing Verification Reports pattern. Keep redirects outside only when they are pure `<Navigate>` compatibility links.

## 10. Mutation interaction model and busy/error semantics

**Finding:** Mixed compliance. Verification Reports and Reverification Batches model operator mutations through `useApiAction`, which gives consistent busy, success, error, and refresh behavior. Evidence: `app/frontend/src/pages/admin/VerificationReports.jsx:212-299`, `app/frontend/src/pages/admin/VerificationReports.jsx:864-893`, `app/frontend/src/pages/admin/ReverificationBatches.jsx:13-32`. Organizations uses `useApiAction` for create, but verify/save operations go through the older `useAdminAction` wrapper with direct `api.post`/`api.put` calls inside the action closure. Evidence: `app/frontend/src/pages/admin/Organizations.jsx:78-97`, `app/frontend/src/pages/admin/Organizations.jsx:172-181`.

**UX risk:** Several high-impact knowledge-governance mutations still bypass `useApiAction` entirely and hand-roll loading/error state. Exam Eligibility saves, archives, and verifies rules with direct `api.post`, `api.put`, and `api.del`. Evidence: `app/frontend/src/pages/admin/ExamEligibility.jsx:122-164`. Persona patches question-bank rows, toggles active state, and processes the recompute queue with direct mutation calls. Evidence: `app/frontend/src/pages/admin/Persona.jsx:130-170`. Guided Exam and Add Cycle execute multi-step identity writes through direct `api.post` calls and nested `try/catch` blocks. Evidence: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:615-747`, `app/frontend/src/pages/admin/studyos/AddCycleWizard.jsx:471-604`.

**Recommendation:** Standardize all user-triggered mutations on `useApiAction`. For multi-step wizards, wrap the whole run in one `run({ action })` and keep the existing per-step log as local progress state; the hook should own top-level busy/error/success semantics while the wizard owns step-by-step detail.

## 11. Collection loading, empty, and error-state contract

**Finding:** Mixed compliance. Exam Intelligence manually implements the required collection lifecycle for the exams table (`idle | loading | data | empty | error`) and renders separate loading/error/data states. Evidence: `app/frontend/src/pages/admin/ExamIntelligence.jsx:45-95`, `app/frontend/src/pages/admin/ExamIntelligence.jsx:272-297`. Reverification Batches uses `useApiCollection` and renders loading, empty, and error states. Evidence: `app/frontend/src/pages/admin/ReverificationBatches.jsx:13-16`, `app/frontend/src/pages/admin/ReverificationBatches.jsx:56-80`. Verification Reports also gates tab-mounted fetching through `useApiCollection`, which avoids fetching an inactive tab. Evidence: `app/frontend/src/pages/admin/VerificationReports.jsx:1215-1229`.

**UX risk:** Persona catches several collection-load failures and silently replaces the collection with an empty list. Evidence: `app/frontend/src/pages/admin/Persona.jsx:65-120`. This blurs ΓÇ£no dataΓÇ¥ and ΓÇ£failed to load,ΓÇ¥ which is particularly risky for governance screens because an operator may interpret missing signals, snapshots, or queue rows as an all-clear state.

**Recommendation:** Migrate PersonaΓÇÖs tab collections to `useApiCollection` or explicitly track `status` and `error` per tab. Do not coerce load failures to `{ items: [], count: 0 }` without rendering an error state and retry affordance.

## 12. Exam-identity lifecycle wording and action availability

**Finding:** Backend semantics are mostly aligned with the current exam-identity contract. The CMS backend excludes `slug` from writable exam fields, generates it from name/org on create, and overwrites payload-supplied slug. Evidence: `app/backend/app/api/admin_exam_intel_cms.py:238-248`, `app/backend/app/api/admin_exam_intel_cms.py:300-307`. Updating an exam accepts `management_mode` and `is_active` as separate fields, while soft-delete writes only `is_active=false`. Evidence: `app/backend/app/api/admin_exam_intel_cms.py:322-348`, `app/backend/app/api/admin_exam_intel_cms.py:351-369`.

**UX risk:** The list view exposes lane, cadence, readiness, and workspace entry, but does not expose an inline lifecycle cue that distinguishes ΓÇ£retiredΓÇ¥ (`is_active=false`) from ΓÇ£archive laneΓÇ¥ (`management_mode='archive'`). Evidence: `app/frontend/src/features/admin/exam-intelligence/ExamListTable.jsx:36-80`. The filter defaults to active exams and an ΓÇ£All (non-archive)ΓÇ¥ lane option, but the operator-facing list copy does not explain that archive is a live-management lane while retired is a separate active-state filter. Evidence: `app/frontend/src/pages/admin/ExamIntelligence.jsx:217-239`.

**Recommendation:** Add a small helper or legend near the active-state and lane filters: ΓÇ£Retired = hidden from aspirants (`is_active=false`); Archive lane = live but low-priority (`management_mode=archive`).ΓÇ¥ Keep slug read-only in all editors and display it as identity metadata, not an editable field.

## 13. Auditability, permission cues, and trust-gate continuity

**Finding:** Backend trust gates are strong in several critical paths. Organization reads/writes are permission-gated and audit-backed. Evidence: `app/backend/app/api/admin_trust.py:460-507`, `app/backend/app/api/admin_trust.py:945-1032`. CMS creates/updates require the exam-intelligence CMS permission and write audit rows with reason and row/patch payloads. Evidence: `app/backend/app/api/admin_exam_intel_cms.py:155-177`, `app/backend/app/api/admin_exam_intel_cms.py:2050-2102`. Verification-report registry actions are permission-gated, report-bound, and single-source through registry action services that write audit trails. Evidence: `app/backend/app/api/admin_verification_reports.py:847-930`.

**UX risk:** Some frontend screens expose backend permission failures only as generic inline errors or silent soft-fails. PersonaΓÇÖs queue processing catches failure and intentionally soft-fails without user feedback. Evidence: `app/frontend/src/pages/admin/Persona.jsx:161-170`. Reverification Batches does show an RBAC hint when the list is empty and the user is not admin/super_admin, which is a better operator cue. Evidence: `app/frontend/src/pages/admin/ReverificationBatches.jsx:18-31`, `app/frontend/src/pages/admin/ReverificationBatches.jsx:63-70`.

**Recommendation:** Mirror backend gates in UI copy consistently: show the required permission/role near disabled or failed actions, and never silently suppress write failures on governance actions. For verification reports, preserve the current explicit conflict/reason/evidence model; conflict overrides record prior value, chosen value, reason, evidence URL, and scope. Evidence: `app/backend/app/api/admin_verification_reports.py:331-398`.
