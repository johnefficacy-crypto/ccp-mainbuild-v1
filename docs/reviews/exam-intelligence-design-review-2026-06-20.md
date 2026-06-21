---
type: design-review
date: 2026-06-20
source: operator PDF screenshots + codebase verification
verified_against: main @ a2ded8c
status: open
scope: admin exam-intelligence surface (KnowledgeGovernance, ExamIntelligence, ExamWorkspace, ExamIntelCms, console)
---

# Exam Intelligence admin surface — design review 2026-06-20

All defects below are verified against code with file:line references.
No conjectural or assumed findings are included.

---

## Category 1 — Redundant data display

### D1 — Exam identity rendered in three places simultaneously

The same four fields (exam name, slug, type, family/organization) appear in:

| Location | File | Lines | Always visible? |
|---|---|---|---|
| SmartHeader (workspace shell) | `ExamWorkspace.jsx` | 110–128 | Yes — sticky at top of every tab |
| OverviewPanel "Exam identity" section | `OverviewPanel.jsx` | 121–128 | Only on Overview tab |
| SetupPanel "Exam details" section | `SetupPanel.jsx` | 909–924 | Only on Setup tab |

The header is always visible and is the canonical location. OverviewPanel and SetupPanel re-render the same fields without adding new information.

### D2 — Readiness scorecard duplicated in header and OverviewPanel

| Location | File | Lines | Shows |
|---|---|---|---|
| SmartHeader scorecard | `ExamWorkspace.jsx` | 152–204 | score%, overallStatus, nextSec.label, blocker count, "Go to next action" CTA |
| OverviewPanel readiness section | `OverviewPanel.jsx` | 149–164 | score%, overallStatus, per-section readiness (7 rows) |

The header version is actionable (contains the CTA); the panel version is a static summary of the same data. An operator reading the Overview tab sees the readiness count twice with no additional insight in the panel version.

### D3 — "Phases needing dates" is a filtered duplicate of the main phases list

`SetupPanel.jsx:201`:
```js
const phaseDateWorklistPhases = phases.filter(needsPhaseDateAuthoring);
```
`SetupPanel.jsx:816–901`: Renders these phases again as a "Phases needing dates" section with date inputs.

The operator already sees all phases in the main phases section above. The worklist is a filter applied to the same array. It is presented as a distinct section rather than as a row-level state in the main table, making it unclear which section is authoritative and which cycle owns which stub (no cycle label shown).

### D4 — Competition panel "Exam" column always shows the same exam in workspace context

`CompetitionPanel.jsx:43`:
```js
if (exam?.id) qs.set("exam_id", exam.id);
```
`CompetitionMetricsTable.jsx:78`:
```jsx
<td>{c.exam || c.exam_slug || "—"}</td>
```
Within the workspace, competition metrics are pre-filtered to the current exam. Showing an "Exam" column that is always identical adds noise. The column is useful only when the table is viewed without exam context (e.g., in CMS).

---

## Category 2 — Multiple overlapping entry points to the same data

### E1 — KnowledgeGovernance.jsx adds a fifth top-level path to exam setup without adding value

`KnowledgeGovernance.jsx` (the "KG" screen) is a lane directory page. Within "Exam truth & planner readiness" it links to:
- `/admin/exam-intelligence/console`
- `/admin/exam-intelligence` (registry)
- `/admin/exam-intelligence/new` (create exam)

Combined with the AdminShell primary navigation, an operator can reach the registry from at least:
1. KnowledgeGovernance → "Exam Registry" link
2. AdminShell direct nav entry "Exam Intelligence"
3. ExamGovernanceConsole breadcrumb back to registry
4. Browser back from any workspace

The KG lane comment is explicit: `// TODO PR3-BE-enh: add per-lane aggregate counts … no kg metrics are available from the overview endpoint for those two lanes yet`. The "Exam truth & planner readiness" lane has **no metrics** and is just a list of three links. The screen is a directory of links, not an actionable dashboard.

### E2 — ExamIntelligence.jsx exposes five navigation paths simultaneously

`ExamIntelligence.jsx:145–166`:
- "Open console" button → `/admin/exam-intelligence/console`
- "Create exam" button → `/admin/exam-intelligence/new`
- "Advanced import / repair" button → `/admin/exam-intelligence/cms`
- "Overview" tab → `ExamIntelligenceOverviewCards` (aggregate counts)
- "Exams" tab → filtered/paginated exam table → each row links to `/admin/exam-intelligence/workspace/{id}`

Five distinct paths from one screen, each with different framing. No screen communicates the operator's goal — the operator must understand the intent of each path before selecting one.

### E3 — Exam/cycle/phase entities editable from three surfaces with no governance model

| Entity | CMS (`ExamIntelCms.jsx`) | Workspace (`SetupPanel.jsx`) | Workspace header |
|---|---|---|---|
| Exam metadata | Full CRUD (lines 159–172) | Name/slug display only | Shown in SmartHeader |
| Exam cycles | Full CRUD (lines 174–188) | Add/edit cycle (lines 217–240) | Cycle picker (ExamWorkspace.jsx:136) |
| Exam phases | Full CRUD (lines 190–200) | Add phase / promote template (lines 79–814) | — |

The workspace is the intended operator surface; CMS is "power users only" (`ExamIntelligence.jsx:163`). But no UI makes this governance visible. Operators who discover CMS may edit entities there, bypassing workspace validation and audit logic.

### E4 — PyqPaperWorkspace reachable as standalone route and embedded within workspace tab

`PyqPaperWorkspace.jsx:9`:
```
Routes: /admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace
```
`PyqWorkbenchPanel.jsx:87`: also renders `<PyqPaperWorkspace embedded={true} />` inside the PYQ tab.

Two paths to the same three-pane review interface — the standalone route via CMS and the embedded view via the workspace tab. No link explains which path to use. The standalone route has no exam context in the URL; the embedded version has exam context from `ExamWorkspaceContext`.

### E5 — Three surfaces to create a new exam

- `ExamIntelligence.jsx:153` → `GuidedExamWizard` ("Create exam")
- `KnowledgeGovernance.jsx` → `/admin/exam-intelligence/new` (same wizard)
- `ExamIntelCms.jsx:159` → CMS direct `exams` entity form (bypasses wizard)

The guided wizard enforces multi-step validation; CMS bypasses it. No UI differentiates them.

---

## Category 3 — Workflow gaps and flow inconsistencies

### F1 — No clear operator workflow for the most common task

The most common operator task is: "I have a new exam cycle coming up (e.g., UPSC CSE 2027). Set it up end-to-end."

The current surface provides no workflow entry that covers this task. The operator must:
1. Find the exam in the Registry (or Workspace if they remember the URL)
2. Open the workspace
3. Go to Setup tab → add cycle → add phases → fill dates
4. Go to Documents tab → upload syllabus → confirm extraction
5. Go to Syllabus Mapper tab → propose/accept mentions (currently broken — BUG-EI-1)
6. Go to PYQ tab → select paper → review questions
7. Go to Updates tab → review policy updates
8. Go to Competition tab → add metrics
9. Go to Review & Activate tab → confirm readiness → activate

There is no guided flow that connects these steps. The Console shows "blockers" but links to the full workspace tab, not to the specific action within the tab. The SmartHeader shows the next blocker but only for the top-level section, not the specific row.

### F2 — Bulk import is a modal detached from the paper management workflow

`PyqWorkbenchPanel.jsx:95–101`: `BulkImportModal` is mounted as a conditional overlay alongside the paper picker. After a successful bulk import, the modal closes and the operator must then:
1. Select a paper from the dropdown
2. Use the workspace to review questions

The modal does not auto-navigate to the newly imported paper. No confirmation step shows what was imported before closing. The bulk import and the paper picker are sequential steps in the same workflow but are presented as separate UI elements with no handoff.

### F3 — PYQ tab shows one paper at a time with no overview

`PyqWorkbenchPanel.jsx:87`: `selectedPaperId ? <PyqPaperWorkspace embedded /> : <p>Select a paper</p>`

No table or list of papers exists on the panel. An operator with 10 papers (2016–2025 pre and mains) must:
- Pick each paper from the dropdown one at a time
- Navigate into it
- Return to the picker for the next

No bulk status, no comparison view, no paper-level readiness indicators. The paper picker is a flat dropdown with no context.

### F4 — Topics management not accessible from workspace context

`SyllabusMapperPanel` provides topic mapping (via `TopicTreePanel` and `TopicEditDrawer`). Topic editing is possible within the syllabus mapper context. But:
- The mapper is only accessible from the Syllabus Mapper tab
- Topics cannot be browsed or filtered by exam from the Setup tab
- Topic prerequisites and aliases have no dedicated management surface — `TopicAliasesEditor.jsx` exists but is nested inside `TopicEditDrawer` within the mapper only

An operator who wants to review the topic taxonomy for an exam independently of syllabus mapping has no path to do so from the workspace.

### F5 — Policy affects_* flags displayed prominently but immutable

`PolicyUpdatesTable.jsx:5–11` (comment):
```
// The affects_* flags are set at row creation and gated by a DB check
// constraint — this surface only moves reviewer_status.
```
`PolicyUpdatesTable.jsx:125–148`: Action buttons are Verify / Reject / Needs correction — no flag edit.

Six `affects_*` booleans are rendered per row as colored pills (`AffectsCell`). They communicate "this update affects your plan/deadline/eligibility etc." But the operator cannot change them in the UI. If a flag is wrong, there is no UI-accessible correction path. The flags occupy visual space without providing an action.

---

## Category 4 — Missing CRUD / management capabilities

### M1 — Topic prerequisites: no editable surface

`TopicEditDrawer.jsx` (inside the syllabus mapper): allows editing topic fields, but topic prerequisites (strength values between two topics) have no dedicated UI. The operator screenshot asks "CRUD? how to update the existing strength?" — there is no answer in the current codebase.

### M2 — Topic aliases: exists but only in mapper context

`TopicAliasesEditor.jsx` is nested inside `TopicEditDrawer` inside `SyllabusMapperPanel`. Aliases can only be viewed/edited in the context of syllabus proposal acceptance. No standalone alias management exists. An operator who wants to add aliases proactively before running a proposal has no path.

### M3 — PYQ question view: all pages/sections rendered simultaneously

`PyqPaperWorkspace.jsx:1131`: loads all 200 questions in one request:
```js
`${CMS_BASE}/pyq-questions?pyq_paper_id=${encodeURIComponent(pyq_paper_id)}&limit=200`
```
All questions render simultaneously with no pagination. For a paper with 100+ questions (common for UPSC pre), this renders hundreds of question cards at once with no page/section navigation.

### M4 — Subjects surface shows IDs, no exam-scoped management

The subjects CMS entity (`ExamIntelCms.jsx:115`) loads all subjects globally. There is no exam-family or exam filter on the subjects endpoint (confirmed in earlier audit). `subject_id` is visible in the rendered table. Subjects cannot be managed in the context of an exam.

---

## Category 5 — Identifier leakage and display hygiene

| Location | File | Line | Leaked field |
|---|---|---|---|
| ReviewQueueTable "Row id" button | `ReviewQueueTable.jsx` | 92 | `{r.id}` raw UUID |
| SetupPanel phase error message | `SetupPanel.jsx` | 803 | `{ptError.phaseId}` raw UUID |
| ExamIntelCms table rows | `ExamIntelCms.jsx` | (multiple entity tables) | entity `id` fields in table cells |
| Competition table in workspace | `CompetitionMetricsTable.jsx` | 78 | `exam_slug` already shown in workspace header |
| Subjects CMS surface | `ExamIntelCms.jsx` | subjects entity | `subject_id` column visible |

`operatorChrome.humanizeToken` and `formatOperatorActor` exist and enforce no-UUID-in-UI. These five sites violate that contract.

---

## Summary: defect count by category

| Category | Count | Severity |
|---|---|---|
| Redundant data display | 4 (D1–D4) | Medium — clutters UI, slows comprehension |
| Multiple overlapping entry points | 5 (E1–E5) | High — no workflow coherence |
| Workflow gaps / flow inconsistency | 5 (F1–F5) | High — operator cannot complete common tasks without context-switching |
| Missing CRUD | 4 (M1–M4) | Medium-High — operator is blocked from data maintenance tasks |
| Identifier leakage | 5 (I1–I5) | Low-Medium — UX hygiene, confusing but not blocking |

Total verified design defects: **23**

---

## Root causes

1. **No "operator journey" design.** The surface was built tab-by-tab and screen-by-screen to match a technical readiness model, not an operator workflow. Tabs mirror the backend readiness sections (`setup`, `documents`, `syllabus`, `pyq`, `updates`, `competition`, `review`) rather than the operator's goals.

2. **No clear governance tier for each surface.** CMS = repair, Workspace = operation, Console = triage — but this is not communicated in the UI, so operators discover all three and use them interchangeably.

3. **Header context not propagated.** The SmartHeader provides exam identity and readiness context but child panels re-fetch and re-render the same data rather than consuming the parent context.

4. **KnowledgeGovernance is a link directory with placeholder metrics.** Two of four lanes have `metricKey: null` — explicitly `counts: not available yet`. The screen is pre-built infrastructure without real data.

5. **PYQ workspace designed for single-paper review, not paper management.** The PyqWorkbenchPanel focuses on reviewing one paper rather than managing a set of papers across years/exams.

---

## Recommended remediation priorities

| Priority | Defect cluster | Suggested approach |
|---|---|---|
| P0 (blocking operators) | F1 — no workflow for cycle setup, BUG-EI-1, BUG-EI-2 | Fix bugs first (Lane H1/H2); then define operator journey |
| P1 (high operator cost) | E2 — 5 nav paths from registry; F3 — no PYQ paper overview; M1/M2 — no prerequisites/aliases CRUD | Single-focus PRs per surface (Lane I) |
| P2 (clarity/hygiene) | D1–D4 — redundant data; I1–I5 — identifier leakage; F5 — immutable flags displayed | Collapse OverviewPanel metadata; apply operatorChrome to leaked IDs |
| P3 (product design needed) | E1 — KG value; F4 — topics in workspace; M3 — question pagination; M4 — subject management | Design decision required before implementation |
