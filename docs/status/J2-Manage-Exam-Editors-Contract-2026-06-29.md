# J2 — Manage Exam Editors Contract

**Document type:** Operator-approval gate — implementation contract  
**Project:** `ccp-mainbuild-v1`  
**Date:** 2026-06-29  
**Status:** PROPOSED — OPERATOR APPROVAL REQUIRED  
**Track:** J2 — missing operational editors in Manage Exam  
**Parent gate:** `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md`  
**Prerequisite gate cleared:** I8-B merged (PR #757 `385912bd`), I8-C merged (PR #759 `f4378097`), I6 merged (PR #761 `d69602f8`)

> **CRITICAL — SERIAL DELIVERY REQUIREMENT (see §3):** All J2 sub-steps share write scope with `ExamWorkspace.jsx` and the Manage Exam tab/panel layer. They MUST be implemented in strict serial sequence by ONE agent. Fan-out to parallel agents is prohibited.

---

## §1 — Purpose

J2 closes the operational gap between what operators currently do and where the product architecture says they should do it.

Today, operators performing routine exam-management work — correcting topic names, adding aliases, setting up prerequisites, onboarding historical papers, correcting question text, or fixing policy flags — must leave Manage Exam and enter Advanced Repair (the CMS, `ExamIntelCms.jsx`). This is wrong: Advanced Repair is documented as an overflow/recovery surface for exceptional repair work only (Design Lock §9.2). Normal operational work belongs in Manage Exam tabs.

J2 moves each of these editors into the appropriate Manage Exam tab as embedded components or contextual drawers. After J2:

- Advanced Repair is used for exceptional cross-exam or broken-FK repair, not for normal per-exam work.
- Each operational action is reachable via a deep link from the action queue CTA (Design Lock §7).
- The no-new-surface rule is respected: no new top-level route, no new sidebar entry, no new peer destination.

---

## §2 — No-new-surface rule compliance

The following rule is LOCKED from the IA Design Lock (§1.2) and is absolute:

> No new top-level destination unless it removes at least two existing top-level destinations.

Every editor defined in this contract is:

- An **embedded component** inside an existing Manage Exam tab panel, or
- A **contextual drawer or modal** triggered from within a tab panel, or
- A **headless backend endpoint** with no associated nav entry.

None of the editors in §4 add a sidebar entry, a new top-level route, or a new peer destination in any nav group. The surface-count after J2 implementation must remain: 1 visible exam nav entry (Exam Management).

---

## §3 — Serial delivery requirement (LOCKED — absolute)

**ALL J2 sub-steps MUST be implemented serially by ONE agent in one or more sequential PRs. Fan-out to parallel agents is prohibited.**

Reason: the shared write scope across all J2 sub-steps includes:

- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx` — tab routing, deep-link param handling, panel mounting
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx` — shared exam/cycle/readiness state
- All panel components under `app/frontend/src/pages/admin/exam-workspace/panels/` and subdirectories
- `app/backend/app/api/admin_exam_intelligence.py` — exam-scoped endpoints
- Route/nav test files

Parallel agents writing to these files produce merge conflicts, duplicate dead code, and inconsistent tab-routing state — the same failure mode that drove the I8 serial-delivery mandate (Design Lock §10.1). The I8 lesson applies here without modification.

**Dispatch rule:** the Wave 2 `j2-manage-exam-editors` agent receives this contract document, works through the sub-steps in the order defined in §6, and opens PRs sequentially. No sub-step PR may be dispatched or opened while a prior sub-step PR is open.

---

## §4 — Editor inventory and tab assignments

### 4.1 Tab map (current `TAB_ORDER` in `ExamWorkspace.jsx`)

After I8-B, `ExamWorkspace.jsx` defines exactly these tabs:

| `id` | Label | Kind |
|---|---|---|
| `setup` | Setup | open |
| `documents` | Documents | open |
| `syllabus` | Syllabus Mapper | readiness |
| `pyq` | PYQ Workbench | readiness |
| `updates` | Updates | readiness |
| `competition` | Competition | readiness |
| `review` | Review & Activate | terminal |

The Overview tab was eliminated in I8-B. No new tabs are added by J2 without explicit operator approval (§5).

### 4.2 Editor-to-tab assignments

#### Editor A: Topic and microtopic management

**Current state:** Topic editing lives inside `TopicEditDrawer.jsx`, accessible only from `SyllabusMapperPanel.jsx` when a topic row is selected. Topic creation has no contextual UI in Manage Exam (only in the CMS).

**Assigned tab:** `syllabus` (Syllabus Mapper)

**Rationale:** Topics are defined and reviewed in the context of syllabus mapping. The Syllabus Mapper panel already loads exam-scoped topics via `SyllabusMapperPanel.jsx` and `TopicTreePanel.jsx`. Adding create/edit/delete capabilities here is a natural extension of existing context — no new surface.

**What J2 adds:**
- "Add topic" and "Add microtopic" actions in the topic tree panel or as a header action in the Syllabus Mapper tab
- Inline topic deletion with dependency check (guard: topics with locked coverage rows or existing aliases may not be deleted without explicit override)
- Topic edit remains via the existing `TopicEditDrawer.jsx` (extended, not replaced)
- Deep-link: `?tab=syllabus&topic=<topic_id>&action=edit` (or `action=add`)

**PROPOSED — OPERATOR APPROVAL REQUIRED**

#### Editor B: Topic alias management (standalone, not mapper-only)

**Current state:** `TopicAliasesEditor.jsx` is nested inside `TopicEditDrawer.jsx` inside `SyllabusMapperPanel.jsx`. An operator cannot manage aliases without first finding the topic in the syllabus mapper view. This is M2 from the design-review audit (status: CLEANUP PENDING — now resolved by J2).

**Assigned tab:** `syllabus` (Syllabus Mapper)

**Rationale:** Aliases are semantically part of topic management. Placing alias editing in the same tab as topic editing (Syllabus Mapper) keeps all topic-identity work in one place and avoids a separate tab or surface.

**What J2 adds:**
- `TopicAliasesEditor.jsx` is extracted to be usable standalone (not only inside `TopicEditDrawer.jsx`)
- A filterable alias list or search panel accessible directly from the Syllabus Mapper tab (not only through a topic edit drawer)
- Operator can add aliases before running a proposal (closes M2: "Operator cannot add aliases before running a proposal")
- Deep-link: `?tab=syllabus&action=aliases[&topic=<topic_id>]`

**PROPOSED — OPERATOR APPROVAL REQUIRED**

#### Editor C: Topic prerequisite editing

**Current state:** `TopicEditDrawer.jsx` allows editing topic fields, but strength values between topics (prerequisites) have no UI anywhere in the codebase. This is M1 from the design-review audit (status: PLANNED).

**Assigned tab:** `syllabus` (Syllabus Mapper)

**Rationale:** Prerequisites are a property of the topic graph, which is surfaced in the Syllabus Mapper tab. Placing prerequisite editing here is consistent with where topic structure is managed.

**HARD DEPENDENCY — BLOCKED ON SCHEMA DESIGN (see §10, Open Question OQ-1):**

M1 explicitly requires a schema design decision before any UI work. The topic prerequisite data model (which table, what fields, what strength-value range, whether prerequisites are directional, how they interact with the coverage graph) does not exist in any migration or backend model. This editor CANNOT be implemented in J2 until OQ-1 is resolved by the operator.

**J2 scope for prerequisite editing is LIMITED TO:**
- Recording the tab assignment decision (Syllabus Mapper)
- Defining the blocked status: implementation is blocked on OQ-1 (schema design)
- No implementation PR for this editor until OQ-1 is answered and a schema gate document is approved

**PROPOSED — OPERATOR APPROVAL REQUIRED; IMPLEMENTATION BLOCKED ON OQ-1**

#### Editor D: Historical paper creation (PYQ onboarding)

**Current state:** This sub-item has its own gate document: `docs/status/PYQ-Source-and-Paper-Onboarding-Gate-2026-06-25.md` — **APPROVED — IMPLEMENTATION AUTHORIZED** (operator 2026-06-25). OD-1…OD-6 are LOCKED. Implementation is in progress (CODE-FIXED, VALIDATION PENDING per the checklist row for PR #769).

**Assigned tab:** `pyq` (PYQ Workbench)

**What is already done (per checklist as of 2026-06-29):**
- OD-2 (source trust lifecycle): `POST /pyq-sources/{id}/review` + migration `201_pyq_source_review_transaction.sql` is CODE-FIXED, VALIDATION PENDING (PR #769).
- OD-5 (inline upload): `AddPyqPaperModal` "upload new PDF" mode is CODE-FIXED, VALIDATION PENDING (PR #769).
- Core onboarding flow (`POST /pyq-onboarding` + `cms_pyq_onboarding` RPC, migration 192) is CODE-FIXED, VALIDATION PENDING.

**What J2 does NOT add for this editor:**
- J2 does not re-implement or override the PYQ onboarding gate. That gate is approved and its implementation is complete pending operator staging validation.
- J2 does not add new onboarding surfaces beyond what the gate authorizes.
- This editor is listed here for completeness and to confirm tab assignment; its implementation is governed by the onboarding gate document.

**OPERATOR PENDING:** migration 192 staging apply and behavioral validation; migration `201_pyq_source_review_transaction.sql` staging apply + grant matrix + transition/rollback; click-through source review + inline upload.

#### Editor E: Question and option correction

**Current state:** PYQ question text and option text have no correction UI in Manage Exam. Corrections currently require CMS access (`ExamIntelCms.jsx` entity-list editing). Question pagination was addressed in PR #751 (M3), but edit-in-place was not.

**Assigned tab:** `pyq` (PYQ Workbench)

**Rationale:** The PYQ Workbench panel (`PyqWorkbenchPanel.jsx`) is already the primary operator surface for per-question review and verification. Adding inline question and option correction here is a natural in-place extension. The paper + question + option hierarchy is already fully rendered.

**What J2 adds:**
- Inline question text edit (question body, explanation, source reference) from the question detail view inside `PyqPaperWorkspace`
- Inline option text edit (option body, is-correct flag correction) from the same detail view
- Save action uses `PATCH /api/admin/exam-intelligence-cms/pyq-questions/{id}` (existing CMS endpoint, or a new exam-intelligence-scoped equivalent — see §7)
- Edit action is gated behind `reviewer_status != 'verified'` guard or requires explicit unlock with reason (review lifecycle must not be bypassed — Design Lock §9.2)
- Deep-link: `?tab=pyq&paper=<paper_id>&row=<question_id>&action=edit`

**PROPOSED — OPERATOR APPROVAL REQUIRED**

#### Editor F: Policy flag correction (`affects_*` flags)

**Current state:** `PolicyUpdatesTable.jsx` displays six colored-pill boolean `affects_*` flags per policy update row (F5 in the design-review audit, status: CLEANUP PENDING). The comment at line 5–11 of that file explicitly states: "flags set at row creation, gated by DB check constraint — this surface only moves `reviewer_status`." There is no UI correction path if a flag is wrong.

**Assigned tab:** `updates` (Updates)

**Rationale:** The Updates tab (`UpdatesPanel.jsx`) is where operators review policy updates and advance their `reviewer_status`. Flag correction belongs in the same tab as flag review — adding a correction action inline is minimally invasive.

**What J2 adds:**
- An "Edit flags" action on a policy update row (rendered inline or as a drawer)
- The action renders the six `affects_*` fields as editable toggles with a required reason field
- Save action calls `PATCH /api/admin/exam-intelligence/exams/{exam_id}/policy-updates/{update_id}` (new endpoint — see §7)
- The save action does NOT advance `reviewer_status`; that remains a separate action
- If a DB check constraint blocks a flag combination, the UI must surface the constraint violation clearly (not a silent 422)
- Deep-link: `?tab=updates&row=<update_id>&action=edit-flags`

**PROPOSED — OPERATOR APPROVAL REQUIRED**

---

## §5 — Tab assignment decisions

All editors land in existing tabs. No new tabs are added by J2.

| Editor | Tab | Panel component (existing) | New component(s) |
|---|---|---|---|
| A: Topic/microtopic management | `syllabus` | `SyllabusMapperPanel.jsx` → `TopicTreePanel.jsx` | `TopicCreateDrawer.jsx` (new) |
| B: Topic alias management | `syllabus` | `SyllabusMapperPanel.jsx` → `TopicAliasesEditor.jsx` (extracted) | Standalone alias list/search panel |
| C: Topic prerequisite editing | `syllabus` | `SyllabusMapperPanel.jsx` | BLOCKED — OQ-1 |
| D: Historical paper creation | `pyq` | `PyqWorkbenchPanel.jsx` | `AddPyqPaperModal.jsx` (already code-fixed per gate) |
| E: Question/option correction | `pyq` | `PyqWorkbenchPanel.jsx` → `PyqPaperWorkspace` | Inline edit form in question detail |
| F: Policy flag correction | `updates` | `UpdatesPanel.jsx` → `PolicyUpdatesTable.jsx` | Inline flags edit drawer |

**Tab additions:** NONE. Adding a new tab requires a separate operator-approved gate document. This constraint is LOCKED per the no-new-surface rule.

All assignments above are: **PROPOSED — OPERATOR APPROVAL REQUIRED**

---

## §6 — Sub-step delivery order (proposed serial sequence)

Because all sub-steps share write scope, the proposed implementation order is:

1. **Sub-step J2-1:** Editor F — Policy flag correction (`updates` tab). Smallest surface. Validates the pattern of inline-edit-in-existing-panel before touching the larger `syllabus` tab.
2. **Sub-step J2-2:** Editor E — Question/option correction (`pyq` tab). Builds on the existing question detail view; no new panel component.
3. **Sub-step J2-3:** Editor B — Topic alias management (standalone in `syllabus` tab). Extracts `TopicAliasesEditor.jsx` to be standalone-capable; lower risk than adding new create flows.
4. **Sub-step J2-4:** Editor A — Topic/microtopic management (`syllabus` tab). Adds `TopicCreateDrawer.jsx`; depends on alias extraction being complete.
5. **Sub-step J2-5:** Editor C — Topic prerequisite editing. **BLOCKED on OQ-1.** Not dispatched until schema gate is approved by operator.
6. **Sub-step J2-6 (documentation only):** Editor D — PYQ onboarding sub-item. Already governed by the onboarding gate. J2 verifies no regressions and updates the checklist.

Each sub-step is a separate PR. No PR may be opened while the prior sub-step's PR is open or failing CI.

**PROPOSED — OPERATOR APPROVAL REQUIRED**

---

## §7 — Backend contract

### 7.1 New or extended endpoints

| Endpoint | Method | Purpose | New / Extended |
|---|---|---|---|
| `/api/admin/exam-intelligence/exams/{exam_id}/policy-updates/{update_id}` | `PATCH` | Correct `affects_*` flags on a policy update row with reason audit | **New** |
| `/api/admin/exam-intelligence/exams/{exam_id}/topics` | `POST` | Create a new topic or microtopic scoped to an exam | **New** |
| `/api/admin/exam-intelligence/exams/{exam_id}/topics/{topic_id}` | `DELETE` | Delete a topic (with dependency guard) | **New** |
| `/api/admin/exam-intelligence/exams/{exam_id}/topics/{topic_id}/aliases` | `GET` / `POST` / `DELETE` | Standalone alias management (list, add, remove) | **New** (GET may already exist; verify before adding) |
| `/api/admin/exam-intelligence-cms/pyq-questions/{id}` or `/api/admin/exam-intelligence/exams/{exam_id}/pyq-questions/{id}` | `PATCH` | Correct question or option text/flags | **New scoped endpoint** (see note below) |
| `/api/admin/exam-intelligence-cms/pyq-onboarding` | `POST` | PYQ onboarding (source + paper + doc link) | Already code-fixed (PR #769); not re-implemented |
| `/api/admin/exam-intelligence-cms/pyq-sources/{id}/review` | `POST` | Source trust review (OD-2) | Already code-fixed (PR #769); not re-implemented |

**Note on question correction endpoint:** the CMS endpoint (`/exam-intelligence-cms/pyq-questions/{id}`) may be reused if it already supports patching question text. If the CMS endpoint allows unrestricted writes without review lifecycle enforcement, a new scoped endpoint under `/exam-intelligence/exams/{exam_id}/` is preferred to ensure the review lifecycle guard is enforced server-side.

### 7.2 Audit requirements

Every write endpoint added by J2 MUST:
- Accept a `reason` field (8–500 chars) on all mutating requests
- Write an audit record via the existing audit pattern (same pattern as `cms_set_pyq_paper_provenance`, `cms_review_pyq_source`, etc.)
- Never bypass the review lifecycle (`pending → reviewed → locked` / `verified` transition matrix)
- Be gated by the appropriate permission (`exam_intelligence.admin` or a narrower scoped token — operator to confirm)

### 7.3 What is NOT in the backend contract

- Topic prerequisite schema: no migration, no endpoint — BLOCKED on OQ-1
- No new top-level router prefix: all new endpoints are added to existing routers (`admin_exam_intelligence.py` or `admin_exam_intel_cms.py`)
- No changes to `readiness.py`, `work_queue.py`, or `console_detail.py` — these are locked by the readiness authority contract (Design Lock §4)

**PROPOSED — OPERATOR APPROVAL REQUIRED**

---

## §8 — Frontend contract

### 8.1 New panel components

| Component | Location | Type | Depends on |
|---|---|---|---|
| `TopicCreateDrawer.jsx` | `panels/` or `syllabus-mapper/` | New | `TopicEditDrawer.jsx` pattern |
| Standalone alias list/filter | Inside `SyllabusMapperPanel.jsx` (not a new file unless extraction requires it) | Extension | `TopicAliasesEditor.jsx` extracted |
| Inline question edit form | Inside `PyqPaperWorkspace` (question detail area) | Extension | Existing question detail render |
| Inline flags edit drawer | Inside `PolicyUpdatesTable.jsx` | Extension | Existing row action pattern |

### 8.2 Extended panel components

| Component | Extension |
|---|---|
| `SyllabusMapperPanel.jsx` | Add-topic action, standalone alias access, deep-link `?action=add` / `?action=aliases` handler |
| `TopicTreePanel.jsx` | Add-topic / add-microtopic triggers; topic delete with dependency guard |
| `TopicAliasesEditor.jsx` | Extract to allow standalone use (not only inside `TopicEditDrawer.jsx`) |
| `PyqWorkbenchPanel.jsx` / `PyqPaperWorkspace` | Question/option correction triggers; inline edit form |
| `PolicyUpdatesTable.jsx` | "Edit flags" row action; flags edit form/drawer |

### 8.3 Do-not-touch components

The following components MUST NOT be modified by J2 sub-steps:

- `ExamWorkspace.jsx` tab list (`TAB_ORDER`) — no new tabs
- `AdminShell.jsx` — no nav changes
- `adminRoutes.jsx` — no new routes
- `ExamWorkspaceContext.jsx` — only modified if a deep-link param handler requires it (requires explicit justification in the PR)
- `ExamIntelCms.jsx` — J2 adds operational editors to Manage Exam; it does NOT remove CMS entity edit forms (CMS remains as Advanced Repair for recovery)

### 8.4 Deep-link param inventory

J2 adds the following new `?action=` values to the existing Manage Exam URL contract (Design Lock §7.1):

| Tab | New param values | Triggers |
|---|---|---|
| `syllabus` | `?action=add-topic`, `?action=add-microtopic`, `?action=aliases`, `?topic=<id>&action=edit-aliases` | Topic create, alias management |
| `pyq` | `?paper=<id>&row=<question_id>&action=edit-question` | Question/option correction |
| `updates` | `?row=<update_id>&action=edit-flags` | Policy flag correction |

These are additive to the existing param contract. No existing `?tab=`, `?cycle=`, `?status=`, `?document=`, `?paper=`, `?row=` params are changed.

**PROPOSED — OPERATOR APPROVAL REQUIRED**

---

## §9 — PYQ sub-item status (Editor D)

This section summarizes what is already done versus what J2 adds, to prevent double-implementation.

### Already done (per checklist 2026-06-29)

| Item | Status | Gate |
|---|---|---|
| OD-1: `pyq_source_id` optional | LOCKED | Onboarding gate OD-1 |
| OD-2: Source trust lifecycle — `POST /pyq-sources/{id}/review` + migration 201 | CODE-FIXED, VALIDATION PENDING | Onboarding follow-ups contract + PR #769 |
| OD-3: "No reusable source record" advisory copy | LOCKED | Onboarding gate OD-3 |
| OD-4: Picker-only; no UUID fallback | LOCKED | Onboarding gate OD-4 |
| OD-5: Inline upload in `AddPyqPaperModal` | CODE-FIXED, VALIDATION PENDING | PR #769 |
| OD-6: PostgreSQL transactional RPC (`cms_pyq_onboarding`, migration 192) | CODE-FIXED, VALIDATION PENDING | PR #769 |
| Empty-state copy fix (no CMS reference) | CODE-FIXED, VALIDATION PENDING | PR #769 |
| Shared `PyqProvenanceFields` component | CODE-FIXED, VALIDATION PENDING | PR #769 |
| Workbench source-trust summary + Verify/Reject/Re-queue | CODE-FIXED, VALIDATION PENDING | PR #769 |
| Cycle/phase label fix in DocumentsPanel selectors | CODE-FIXED, VALIDATION PENDING | PR #769 |

### What J2 adds for this editor

J2 does **not** re-implement the onboarding flow. J2's role for Editor D is:

1. Confirm tab assignment: `pyq` (PYQ Workbench) — CONFIRMED by gate document
2. Confirm no regression: J2-2 (question correction) PR must not break `PyqWorkbenchPanel.jsx` or `PyqPaperWorkspace`
3. Update checklist when operator staging validation completes (OPERATOR PENDING)

### Operator staging validation still required

| Action | Status |
|---|---|
| Apply migration 192 (`cms_pyq_onboarding` RPC) to staging | OPERATOR PENDING |
| Apply migration 201 (`cms_review_pyq_source` RPC) to staging | OPERATOR PENDING |
| Verify grant matrices (anon/authenticated cannot execute; service_role can) | OPERATOR PENDING |
| Click-through: Add PYQ paper → source creation → document link | OPERATOR PENDING |
| Click-through: Source trust review (verify/reject/re-queue) | OPERATOR PENDING |
| Click-through: Inline upload (including failing extraction case) | OPERATOR PENDING |
| Click-through: Cycle/phase labels readable (no raw UUIDs) | OPERATOR PENDING |

---

## §10 — Open questions (OPERATOR RESOLUTION REQUIRED)

### OQ-1 — Topic prerequisite schema (HARD DEPENDENCY — blocks Editor C)

**Status: UNRESOLVED — Editor C (prerequisite editing) cannot be implemented until this is answered.**

M1 from the design-review audit (PLANNED) confirms: no prerequisite CRUD exists anywhere in the codebase. `TopicEditDrawer.jsx` allows editing topic fields but no strength values between topics.

Before any implementation of Editor C, the operator must answer:

1. **Data model:** Is a prerequisite a directed edge `(topic_A → topic_B, strength: float 0–1)`? Or a named relationship? Does it live in a new `topic_prerequisites` table or extend the existing topic schema?
2. **Scope:** Are prerequisites exam-scoped (one exam's topic graph can have different prerequisites than another) or global (a prerequisite between two topics is universal across all exams)?
3. **Use:** How does the prerequisite graph affect the planner, mastery writer, or coverage scoring? (This determines whether schema is a simple label table or a load-bearing dependency for other systems.)
4. **UI pattern:** Is prerequisite editing a graph editor, a list editor inside `TopicEditDrawer`, or a separate panel?

**Resolution required before Editor C sub-step PR is dispatched. A separate schema gate document is required.**

### OQ-2 — Question/option correction permission gate

**Status: PROPOSED — OPERATOR RESOLUTION REQUIRED**

Editor E (question/option correction) requires a permission gate. Options:

- (a) Reuse `exam_intelligence.cms` (same as Advanced Repair) — correct: this is repair work
- (b) Use `exam_intelligence.review` (if question correction is considered a review action)
- (c) A new `exam_intelligence.edit` or `exam_intelligence.correct` token

The operator must confirm which permission token gates question/option correction.

### OQ-3 — Policy flag correction permission gate

**Status: PROPOSED — OPERATOR RESOLUTION REQUIRED**

Same question as OQ-2 but for Editor F (policy `affects_*` flag correction). The `PolicyUpdatesTable.jsx` comment says flags are set at row creation and gated by a DB check constraint. The edit action needs a permission gate and a DB-side constraint-safe update path.

---

## §11 — Locked decisions

Each item below is PROPOSED and requires operator approval before implementation begins.

| Decision | State |
|---|---|
| J2 sub-steps are serial, owned by one agent — no fan-out | PROPOSED — OPERATOR APPROVAL REQUIRED |
| Editors A, B, C → `syllabus` tab | PROPOSED — OPERATOR APPROVAL REQUIRED |
| Editors D → `pyq` tab (already confirmed by onboarding gate) | LOCKED by `PYQ-Source-and-Paper-Onboarding-Gate-2026-06-25.md` |
| Editor E → `pyq` tab | PROPOSED — OPERATOR APPROVAL REQUIRED |
| Editor F → `updates` tab | PROPOSED — OPERATOR APPROVAL REQUIRED |
| No new tabs added by J2 | PROPOSED — OPERATOR APPROVAL REQUIRED |
| No new sidebar entries or top-level routes | FOLLOWS FROM no-new-surface rule (LOCKED by Design Lock §1.2) |
| Editor C (prerequisite editing) blocked on OQ-1 schema design | PROPOSED — OPERATOR APPROVAL REQUIRED |
| All write endpoints require a `reason` field and write audit records | PROPOSED — OPERATOR APPROVAL REQUIRED |
| Review lifecycle (`pending → reviewed → locked`) is never bypassed | FOLLOWS FROM Design Lock §9.2 (LOCKED) |
| Question/option correction permission gate: operator to choose (OQ-2) | PROPOSED — OPERATOR RESOLUTION REQUIRED |
| Policy flag correction permission gate: operator to choose (OQ-3) | PROPOSED — OPERATOR RESOLUTION REQUIRED |

---

## §12 — What this contract does NOT authorize

- **No implementation PR** may be dispatched before this document is operator-approved.
- **No runtime files** are changed in the PR that introduces this document.
- **No new top-level routes**, sidebar entries, or peer nav destinations.
- **No prerequisite schema work** (Editor C) until OQ-1 is resolved by a separate schema gate.
- **No changes to the PYQ onboarding gate** — that gate is approved and its implementation is governed by `PYQ-Source-and-Paper-Onboarding-Gate-2026-06-25.md`.
- **No changes to readiness, work-queue classification, or activation authority** — those are locked by Design Lock §4.
- **No changes to Advanced Repair (`ExamIntelCms.jsx`) internals** — J2 adds editors to Manage Exam tabs; it does not remove CMS entity forms.
- **No J3 scope** — competition metrics structure, mixed-format PDF extraction, and evidence-based coverage scoring remain deferred to J3 with their own contract-first gates.

---

## §13 — Acceptance tests (per sub-step — must pass before each PR merges)

### J2-1: Policy flag correction (Editor F)

```
[ ] UpdatesPanel renders an "Edit flags" action on policy update rows
[ ] "Edit flags" action opens an inline form/drawer with the six affects_* toggles and a reason field
[ ] Save calls PATCH /api/admin/exam-intelligence/exams/{exam_id}/policy-updates/{update_id} with flags + reason
[ ] reason < 8 chars → blocked with inline validation message
[ ] DB check constraint violation → surfaced as readable error (not silent 422)
[ ] Save does NOT advance reviewer_status
[ ] Deep-link ?tab=updates&row=<id>&action=edit-flags opens the flags editor for that row
[ ] No change to TAB_ORDER or AdminShell nav
[ ] No new routes in adminRoutes.jsx
```

### J2-2: Question/option correction (Editor E)

```
[ ] PyqPaperWorkspace question detail renders "Edit question" / "Edit option" actions
[ ] Edit actions are unavailable when reviewer_status == 'verified' (or require explicit unlock)
[ ] Save calls PATCH endpoint with question/option text + reason
[ ] reason field required (8–500 chars)
[ ] Audit record written on save (verified via backend test)
[ ] Deep-link ?tab=pyq&paper=<id>&row=<question_id>&action=edit-question opens the edit form
[ ] No regression in PyqWorkbenchPanel or AddPyqPaperModal behavior (Editor D not broken)
[ ] No change to TAB_ORDER or AdminShell nav
```

### J2-3: Standalone topic alias management (Editor B)

```
[ ] SyllabusMapperPanel renders alias access without requiring a topic-edit drawer
[ ] TopicAliasesEditor can render standalone (not only nested inside TopicEditDrawer)
[ ] Operator can add an alias to a topic before running a proposal (M2 closed)
[ ] GET /exams/{exam_id}/topics/{topic_id}/aliases returns alias list
[ ] POST /exams/{exam_id}/topics/{topic_id}/aliases creates an alias with reason
[ ] DELETE /exams/{exam_id}/topics/{topic_id}/aliases/{alias_id} removes an alias with reason
[ ] Deep-link ?tab=syllabus&action=aliases opens alias management
[ ] No change to TAB_ORDER or AdminShell nav
```

### J2-4: Topic/microtopic management (Editor A)

```
[ ] SyllabusMapperPanel renders "Add topic" and "Add microtopic" actions
[ ] TopicCreateDrawer creates a topic scoped to the exam with required fields
[ ] Topic deletion is guarded: topics with locked coverage rows or aliases show a blocker before delete
[ ] POST /exams/{exam_id}/topics creates topic with reason
[ ] DELETE /exams/{exam_id}/topics/{topic_id} returns 409 if locked coverage rows exist
[ ] Deep-link ?tab=syllabus&action=add-topic opens the create drawer
[ ] No change to TAB_ORDER or AdminShell nav
```

### J2-5: Topic prerequisite editing (Editor C) — BLOCKED

```
[ ] BLOCKED — not dispatched until OQ-1 schema gate document is operator-approved
```

---

*This document is a planning artifact. No runtime files are changed in the PR that introduces it. All decisions marked PROPOSED require operator approval before any implementation PR is dispatched.*
