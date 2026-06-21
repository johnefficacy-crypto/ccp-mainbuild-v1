# Exam Management IA Design Lock

**Document type:** Executable implementation gate  
**Project:** `ccp-mainbuild-v1`  
**Date:** 2026-06-21  
**Scope:** All of I8-A, I8-B, and I8-C  
**Status:** LOCKED — no I8 implementation PR may be dispatched until this document is approved and merged  
**Supersedes:** findings/decisions portions of `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` that are implementation-specific. That document remains the authoritative findings record; this document converts its decisions into implementor obligations.

---

## How to use this document

Every section below states a LOCKED decision. Implementors MUST follow the locked decision exactly. Deviations require a new gate document, not a PR-level justification. Unresolved items are called out explicitly in each section and do not authorize any guess or invention.

---

## Section 1: Product hierarchy

### 1.1 Locked visible hierarchy

The only visible product hierarchy after I8 is:

```
Exam Management                         ← one sidebar entry, one top-level route
  └─ Manage Exam                        ← drill-in (not a peer destination)
       └─ More → Advanced Repair        ← overflow/fallback only (not a peer destination)
```

This is not a label change. It is a structural consolidation. After I8-C is merged and redirects pass:

- the visible peer-destination count for exam operations must be **1** (Exam Management)
- Manage Exam is a drill-in page, not a sidebar entry and not a second top-level destination
- Advanced Repair is an overflow action inside Manage Exam, not a sidebar entry, not a nav peer, and not a primary CTA anywhere

### 1.2 No-new-surface rule (LOCKED — absolute)

**No new top-level destination unless it removes at least two existing top-level destinations.**

The following are classified as surfaces and are therefore prohibited from being added:

- a separate portfolio dashboard
- a separate coverage matrix page or lane
- a second exam console
- a second workspace variant
- a new visible global CMS peer
- an exam-management lane inside Knowledge Governance (removed by I7; must not re-appear)

The following are NOT surfaces and may be added freely:

- backend endpoints (headless)
- embedded components inside an existing page
- drill-in pages reached by navigating within a page
- overflow/More actions
- permission-gated recovery tools with no nav entry

### 1.3 Before/after surface-count acceptance test

**Before (current verified state from AdminShell.jsx):**

The Knowledge Governance sidebar group (`id: "knowledge-governance"`) currently exposes all of the following as visible nav items:

1. KG landing (`/admin/knowledge-governance`) — Knowledge Governance
2. Exam Governance Console (`/admin/exam-intelligence/console`) — primary KG lane item
3. Exam Registry (`/admin/exam-intelligence`) — primary KG lane item
4. Create exam (`/admin/exam-intelligence/new`) — advanced KG lane item
5. Advanced Import / Repair (`/admin/exam-intelligence/cms`) — advanced KG lane item

Plus the now-removed exam lane card on the KG landing page (removed by I7).

Visible exam-operation peer count before I8: **5 nav items** (plus the KG landing as parent, plus the removed KG exam lane card = at minimum 5 distinct operator-navigable exam surfaces).

**After I8-A through I8-C (locked target):**

1. Exam Management (`/admin/exam-intelligence`) — **1 visible sidebar entry**

Manage Exam and Advanced Repair are NOT sidebar entries. They are reached by navigating within Exam Management.

Post-I8 visible exam-operation peer count: **1**.

**Exit test (must pass before any I8-C cleanup merge):**

```
visible_exam_nav_entries == 1
manage_exam_is_drill_in == true
advanced_repair_is_overflow_only == true
no_exam_lane_in_kg == true  (enforced by I7, must not regress)
console_peer_visible == false
workspace_peer_visible == false
cms_nav_visible == false
```

---

## Section 2: Canonical route map

### 2.1 Current routes (verified from adminRoutes.jsx)

The following exam-intelligence routes exist today:

```
/admin/exam-intelligence                           → AdminExamIntelligence (Exam Registry)
/admin/exam-intelligence/console                   → AdminExamGovernanceConsole (work queue)
/admin/exam-intelligence/console/:exam_id          → AdminExamGovernanceConsole (per-exam action console)
/admin/exam-intelligence/cms                       → AdminExamIntelCms
/admin/exam-intelligence/new                       → AdminGuidedExamWizard
/admin/exam-intelligence/exams/:exam_id/add-cycle  → AddCycleRedirect (redirects to workspace)
/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace → AdminPyqPaperWorkspace
/admin/exam-intelligence/workspace/:exam_id        → AdminExamWorkspace
/admin/exam-intelligence/workspace/:exam_id/:cycle_id → AdminExamWorkspace
```

All exam-intelligence routes are nested inside a `<RouteErrorBoundary>` group. This pattern must be preserved for all new canonical routes.

### 2.2 Locked canonical target routes

After I8-A/B/C, the following canonical routes MUST exist:

| Route | Purpose | Component owner |
|---|---|---|
| `/admin/exam-intelligence` | Exam Management front door | `ExamIntelligence.jsx` (evolved) |
| `/admin/exam-intelligence/exams/:exam_id` | Manage Exam | `ExamWorkspace.jsx` (evolved) |
| `/admin/exam-intelligence/exams/:exam_id?cycle=:cycle_id&tab=:tab` | Manage Exam with selected exam/cycle/task state | Same component, query-param driven |
| `/admin/exam-intelligence/cms?exam_id=:exam_id&cycle_id=:cycle_id` | Advanced Repair (overflow entry) | `ExamIntelCms.jsx` (retained, overflow only) |

**Route shape rationale:**

- The move from `/workspace/:exam_id` to `/exams/:exam_id` is a semantic upgrade: the path segment names the entity type (exam) not the UI surface (workspace).
- Tab state and cycle selection are stored in URL query parameters (`?cycle=...&tab=...`) so the URL is bookmarkable and back-navigable.
- The CMS retains its route but acquires `exam_id` and `cycle_id` query params when entered from the overflow action.

### 2.3 Transitional compatibility routes (LOCKED — do NOT delete before redirects)

The following routes MUST remain functional (not 404) during transition, as legacy bookmarks, external links, and tests depend on them:

```
/admin/exam-intelligence/console
/admin/exam-intelligence/console/:exam_id
/admin/exam-intelligence/workspace/:exam_id
/admin/exam-intelligence/workspace/:exam_id/:cycle_id
/admin/exam-intelligence/new
/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace
```

**Treatment:** These routes must serve content (compatibility shell or redirect-to-canonical) until Step 4 of the redirect sequence is complete and redirect tests pass.

**Do NOT authorize immediate deletion** of any of the above. The retirement schedule is governed by Section 12.

### 2.4 Locked redirect sequence (no intermediate 404 allowed)

Implementors MUST follow this exact sequence across I8-A, I8-B, and I8-C:

1. **Canonical targets exist** — add `/admin/exam-intelligence/exams/:exam_id` (and variants) as live routes serving content. Old routes still work. No 404 is possible.
2. **Navigation and internal links move** — update AdminShell sidebar, internal CTAs, action queue links, and back-navigation links to use canonical routes. Old routes still serve content.
3. **Entry points and deep links are validated** — all nav links, action CTAs, blocker links, and external deep links are confirmed to reach the canonical targets. Tests pass.
4. **Legacy routes redirect** — convert old visible URLs (`/workspace/:exam_id`, `/console/:exam_id`, `/console`) to `<Navigate>` redirects pointing at canonical targets. Tests confirm the redirect chain works.
5. **Orphaned components are removed** — retire shells and components that serve only legacy routes, but only after Step 4 tests pass.

**Steps 1-3 land in I8-A and I8-B. Step 4 lands in I8-B (workspace) and I8-C (console/CMS). Step 5 lands in cleanup after I8-C.**

---

## Section 3: Page and component ownership

### 3.1 Locked ownership assignments

| Page/purpose | Owner component | Lifecycle after I8 |
|---|---|---|
| Exam Management front door | `ExamIntelligence.jsx` (evolved in I8-A) | Retained and promoted |
| Manage Exam | `ExamWorkspace.jsx` (evolved in I8-B) | Retained and evolved |
| Advanced Repair | `ExamIntelCms.jsx` (retained in I8-C) | Retained as overflow only |
| Compatibility shells | Inline `<Navigate>` redirects in `adminRoutes.jsx` | Temporary; removed after redirect tests pass |

### 3.2 Per-component role resolution (from code evidence)

**ExamIntelligence.jsx** (current: Exam Registry page at `/admin/exam-intelligence`)

Current state verified from file: renders Overview and Exams tabs, exposes five competing header actions (Open console, Create exam, Advanced import / repair, status dot), fetches `/api/admin/exam-intelligence/overview` and `/api/admin/exam-intelligence/exams`.

Post-I8-A locked role: **Exam Management front door — single-view (no tabs).** The front door is locked as a single view: no Overview vs Exams tab competition. The triage list (family → exam → cycle hierarchy, status, first blocker) is the only content. Header actions Open console, Create exam, and Advanced import / repair must be removed as peer CTAs. Create exam is demoted to overflow only (not a primary header action). See Section 5 for content spec.

**ConsoleWorkQueue.jsx** (current: renders at `/admin/exam-intelligence/console`, fetches `/api/admin/exam-intelligence/console/exams` and `/api/admin/exam-intelligence/console/summary`)

Current state verified: renders cross-exam triage with status chips (blocked/needs_action/ready), filters, sort, and per-row "Open console" + "Advanced workspace" dual actions.

Post-I8-A locked role: **Reused as front-door triage/list content inside ExamIntelligence.jsx**. The "Open console" and "Advanced workspace" row actions must be replaced with a single "Manage exam" action pointing at `/admin/exam-intelligence/exams/:exam_id`. The component may be embedded directly or its data and filter logic may be absorbed into the evolved ExamIntelligence.jsx. The rendering of `ExamGovernanceConsole` as a separate routed page is retired.

**ExamGovernanceConsole.jsx** (current: shell at `/admin/exam-intelligence/console[/:exam_id]`)

Current state verified: thin shell that renders either `ConsoleWorkQueue` (no exam) or `ExamActionConsole` (with exam). Has no substantial logic of its own.

Post-I8 locked role: **Retired after I8-B redirects pass**. Content moves: work queue → ExamIntelligence.jsx front door; per-exam action console → Manage Exam (ExamWorkspace.jsx). Retirement is blocked on redirect tests (see Section 12).

**ExamActionConsole.jsx** (current: per-exam triage view at `/console/:exam_id`, fetches `/api/admin/exam-intelligence/console/exams/{exam_id}`)

Current state verified: renders `activation_verdict`, `action_queue`, `activation_checks`, `stages`, and `mock_readiness` — all from the backend `console_detail.build_console_detail`. All action CTAs currently link to `cta_route` which defaults to `/admin/exam-intelligence/workspace/{exam_id}` (the confirmed blocker deep-link defect).

Post-I8-B locked role: **Embedded/reused inside Manage Exam (ExamWorkspace.jsx)**. Its verdict, action queue, and check state must render within the Manage Exam context. Its standalone route is retired after redirect tests pass. The deep-link defect in `cta_route` is fixed as part of I8-B (see Section 7).

**ExamWorkspace.jsx** (current: eight-tab workspace at `/workspace/:exam_id[/:cycle_id]`)

Current state verified: provides Setup, Documents, Syllabus Mapper, PYQ Workbench, Updates, Competition, Review & Activate, and Overview tabs. Uses `ExamWorkspaceContext` for shared exam/cycle/readiness state. SmartHeader shows readiness percentage, current stage, next action, and cycle selector (navigates to `/workspace/:exam_id/:cycle_id`).

Post-I8-B locked role: **Evolved into Manage Exam** at `/admin/exam-intelligence/exams/:exam_id`. Tab names and structure evolve (see Section 6). Cycle selection moves from path segment to query parameter (`?cycle=:cycle_id`). The Overview tab is resolved per Section 6. All existing panel components (SetupPanel, DocumentsPanel, etc.) are retained in-place unless Section 6 explicitly retires one.

**ExamWorkspaceContext.jsx** (current: shared context for workspace, fetches `/api/admin/exam-intelligence/workspace/:exam_id/context` and `/api/admin/exam-intelligence/workspace/:exam_id/readiness`)

Current state verified: provides exam, cycle, cycles, phases, organization, family, readiness (fetched separately). No variant logic remains (CL-6b is complete). Uses `cycle_id` from URL params.

Post-I8-B locked role: **Retained, evolved**. The cycle selection mechanism changes from `useParams().cycle_id` to `useSearchParams().get("cycle")` as the canonical route uses a query parameter. The context provider is the single source of exam/cycle/readiness state for Manage Exam.

**ExamIntelCms.jsx** (current: Advanced Import / Repair at `/admin/exam-intelligence/cms`)

Current state verified: full-entity-list CMS editor for all exam-intelligence entities. No `+ New guided exam` CTA (CL-3 complete). UUID cells truncated (I3 complete).

Post-I8-C locked role: **Retained as Advanced Repair overflow only**. Access through normal nav is removed. Access through `Manage Exam → More → Advanced Repair` is added. When entered from Manage Exam, the `exam_id` and `cycle_id` query params pre-scope the entity lists where the CMS supports scoping. Global recovery for super-admin remains available but is not prominently navigable.

### 3.3 Summary

| Component | Post-I8 direction |
|---|---|
| `ExamIntelligence.jsx` | Evolved → Exam Management front door |
| `ConsoleWorkQueue.jsx` | Reused/embedded → front-door triage list |
| `ExamGovernanceConsole.jsx` | Retired → after redirects pass |
| `ExamActionConsole.jsx` | Embedded/reused → inside Manage Exam |
| `ExamWorkspace.jsx` | Evolved → Manage Exam |
| `ExamWorkspaceContext.jsx` | Retained, evolved → cycle from query param |
| `ExamIntelCms.jsx` | Retained → overflow only, not in nav |

---

## Section 4: Canonical readiness authority

### 4.1 The conflict (from code evidence)

There are currently three independent readiness sources:

**Source A — `work_queue.classify_exam`** (in `work_queue.py`):

- Pure classifier that produces `blocked | needs_action | ready`
- Used by both the work queue list (Wave 4.6H) AND the per-exam console detail (Wave 4.6I)
- Status parity is explicitly documented: `activation_verdict.status` in `console_detail.py` uses the SAME classifier over the SAME aggregate
- Produces: `status`, `flags`, `first_blocker_text`, `blocker_count`, `reasons`
- Does NOT produce score percentages

**Source B — `console_detail.build_console_detail`** (in `console_detail.py`):

- Per-exam action view: `activation_verdict`, `action_queue`, `activation_checks`, `stages`, `mock_readiness`
- Uses `classify_exam` for the verdict (same classifier, same data)
- Adds check-level detail (per-area state, reasons, evidence refs), action queue (severity-ordered CTAs), and stage grouping
- Currently: all `cta_route` values default to generic workspace — the confirmed deep-link defect

**Source C — `compute_exam_workspace_readiness`** (in `readiness.py`):

- Per-exam per-cycle weighted readiness: `score_percent`, `status`, per-section `blockers`, `counts`, `metrics`
- BUG-EI-2 fixed (PR #750 merged): now uses `load_doc_extraction_counts` from `document_processing_jobs`
- Used by `ExamWorkspaceContext` and the workspace SmartHeader
- Produces a `score_percent` that currently gates SmartHeader display

### 4.2 Locked resolution

**LOCKED: `work_queue.classify_exam` owns the top-level blocked/needs_action/ready verdict.**

This is already the implementation in both the list and the per-exam console detail. This pattern MUST be preserved in Manage Exam. The `activation_verdict.status` that flows through `ExamActionConsole` is the authoritative top-level verdict.

**LOCKED: a unified backend read model owns per-cycle and per-section status.**

BUG-EI-2 is fixed — PR #750 merged on main. `load_doc_extraction_counts` in `readiness.py` sources extraction from `document_processing_jobs` (job_type='text_extract', latest job per asset, deterministic by (created_at, id)). `console_detail.py` uses it with `strict=True` (fail-closed); workspace path uses `strict=False` (fail-soft). The H2 gate is cleared. `compute_exam_workspace_readiness` is now the reliable source of per-section facts used by Manage Exam. The `console_detail` per-area check states may be reused as inputs to or cross-checks on the readiness facts, but they do NOT replace them.

**LOCKED: `console_detail` checks/actions may be reused as inputs.**

The check-level detail from `activation_checks` (per-area state, reasons, evidence refs) and the action queue from `action_queue` (severity, title, why, CTA) provide operator-readable actionable detail that readiness.py currently does not provide. These MAY be retained and rendered inside Manage Exam alongside the workspace panels.

**LOCKED: workspace readiness section facts may be retained.**

Per-section blockers, counts, and metrics from `compute_exam_workspace_readiness` are useful facts for the Manage Exam UI. They MUST remain available after I8-B; they must not be deleted.

**LOCKED: readiness score percentages must NOT independently authorize activation.**

`score_percent` from `readiness.py` is an advisory display metric. It MUST NOT be used as a gate condition for activation. The `work_queue.classify_exam` verdict is the gate. The SmartHeader currently shows `score_percent` as a display-only metric; this is acceptable only if it is clearly labeled as non-authoritative. A future cleanup may remove it entirely.

**LOCKED: the frontend must NOT calculate activation authority.**

All verdict, status, blocker classification, and gate logic must originate from the backend. The frontend renders what the backend provides. It does not recompute `status` from section states.

### 4.3 Why this follows from code evidence

`console_detail.py` explicitly documents: "Status parity is load-bearing: `activation_verdict.status` is produced by the SAME pure classifier the 4.6H list uses." This is a deliberate architectural decision in the existing code. Replacing or duplicating the classifier in the frontend would violate this documented invariant.

BUG-EI-2 is fixed (PR #750 merged). `readiness.py` now uses `load_doc_extraction_counts` sourced from `document_processing_jobs`; the non-existent `document_assets.extraction_status` column is no longer queried. The `score_percent` output is reliable. Score percentages MAY be used as advisory display metrics but MUST NOT authorize activation — the `work_queue.classify_exam` verdict is the gate.

### 4.4 Locked section-state vocabulary

The backend read model and any frontend status display MUST use only these values for section/document/task state:

| Value | Meaning |
|---|---|
| `missing` | Entity or artifact does not exist yet |
| `uploaded` | Artifact uploaded, not yet processed |
| `extracting` | Extraction job in progress |
| `review_pending` | Extraction complete, awaiting human review |
| `ready` | Review complete, ready for activation |
| `stale` | Previously ready, now outdated |
| `failed` | Extraction or processing job failed |
| `not_applicable` | Step is not required for this exam/management mode |

### 4.5 Old vocabulary — compatibility mapping

The existing `readiness.py` uses `empty | partial | ready | locked`. The existing `work_queue.py` uses `blocked | needs_action | ready`. These are top-level status tokens, not section-state values.

BUG-EI-2 is fixed (PR #750 merged). Old section status tokens (`empty`, `partial`, `locked`) from `readiness.py` were temporary during H2 remediation. They are now superseded:

- `empty` maps to `missing`
- `partial` maps to `review_pending` or `extracting` depending on the actual extraction state
- `locked` maps to `ready`

The I8-B implementation MUST NOT introduce new section-state tokens outside the locked vocabulary above.

---

## Section 5: Exam Management front-door content

### 5.1 Data and UI contract (LOCKED)

The Exam Management front door (`/admin/exam-intelligence`) MUST render:

**Hierarchy level:**

```
Family
  └─ Exam (name, management mode, cadence, active state)
       └─ Current/active cycle (year, cycle name)
            └─ Phases (name, phase slug, start date, end date, status)
```

**Per-exam fields visible at the front door:**

- Exam name and family name
- Organization name
- Management mode (`core | light | index_only | archive | null`)
- Cadence (`annual | recurring | irregular | one-off | unknown`)
- Active state (`active | inactive`)
- Current/active cycle (the cycle the operator is most likely to work on)
- Phase dates and phase status summary for the active cycle
- Top-level verdict (`blocked | needs_action | ready`) — from `work_queue.classify_exam`
- First blocker text — from `first_blocker_text`
- Blocker count — from `blocker_count`
- Readiness summary (advisory) — may include section completeness

**Filters and search (retained from ConsoleWorkQueue and ExamIntelligence.jsx):**

- Text search (name or slug)
- Exam type / purpose filter
- Active state filter
- Exam family filter
- Management mode filter
- Cadence filter
- Workflow filter (`blocked | needs_action | ready | pending_review | stale_review_queue | missing_pyq | missing_coverage`)
- Sort (`blockers_first | management_lane | name`)

**Per-row action (exactly one):**

```
Manage exam  →  /admin/exam-intelligence/exams/:exam_id
```

### 5.2 What must NOT appear as competing actions

The following MUST NOT appear on the front door as competing actions or CTAs:

- Open console (must not exist as a separate action after I8-A)
- Advanced workspace (must not exist as a separate action after I8-A)
- Advanced import / repair as a primary CTA on the front door
- Create exam as a primary header-level CTA visible at all times (it may be demoted or moved to a secondary/overflow position)
- Global CMS as a primary action

---

## Section 6: Manage Exam content

### 6.1 Selected-exam contract (LOCKED)

The Manage Exam page (`/admin/exam-intelligence/exams/:exam_id`) MUST render:

**Identity header (from ExamWorkspaceContext):**

- Exam name, family name, organization name
- Active state, management mode, cadence
- Cycle selector — stored in URL as `?cycle=:cycle_id`; changing cycle updates URL without full page reload

**Verdict header (from ExamActionConsole/console_detail data):**

- Top-level verdict (`blocked | needs_action | ready`)
- First blocker text and blocker count
- Next action label and link (deep-linked, see Section 7)

**Action queue sections (in order, from ExamActionConsole):**

| Section ID | Label | Source area |
|---|---|---|
| `setup` | Setup | phases existence, phase dates |
| `documents` | Documents / Extraction | document upload, extraction job status |
| `syllabus` | Syllabus | syllabus mention review |
| `topic_coverage` | Topic Coverage | locked coverage rows |
| `pyq` | PYQ | verified questions, verified topic tags |
| `updates` | Updates | pending policy updates |
| `competition` | Competition | competition metrics for selected cycle |
| `review` | Review & Activate | terminal gate, activation verdict |

**Advanced Repair overflow action:**

```
More → Advanced Repair  →  /admin/exam-intelligence/cms?exam_id=:exam_id[&cycle_id=:cycle_id]
```

### 6.2 Overview tab — locked decision

**LOCKED: the Overview tab is removed as a standalone competing tab.**

Current evidence: `ExamWorkspace.jsx` defines `TAB_ORDER` with `overview` as the first tab alongside `setup`, `documents`, `syllabus`, `pyq`, `updates`, `competition`, `review`. The overview tab renders `OverviewPanel` which duplicates SmartHeader content (D1/D2 defects, now partially fixed).

After I8-B, the Overview tab is eliminated as a separate tab. Its useful content is:

- Concise status summary — absorbed into the verdict header at the top of Manage Exam
- Per-section readiness rows — retained as a read-only summary section within the verdict header or as a collapsible readiness card
- Identity fields not already in the header — removed (already fixed by D1)

The workspace then opens directly to the action queue / first blocker view, not to an Overview tab. This removes the tab-competition problem that makes Manage Exam feel like a reporting surface before it is a workflow surface.

---

## Section 7: Blocker-to-editor deep-link contract

### 7.1 Semantic requirements (LOCKED)

**Every action CTA from the action queue and activation checks MUST deep-link to the exact task state.**

The confirmed defect: `console_detail.py` currently emits `cta_route = "/admin/exam-intelligence/workspace/{exam_id}"` for every action, losing all task context. This is fixed in I8-B.

**URL pattern:**

```
/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab={tab}[&status={status}][&document={id}][&paper={id}][&row={id}]
```

Not every parameter is required for every action. Each action MUST preserve at minimum: exam identity, cycle where applicable, and exact operational destination (tab).

### 7.2 Locked deep-link examples by action type

**Setup / phases:**
```json
{
  "area": "setup",
  "title": "No exam phases defined",
  "cta_label": "Go to Setup",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?tab=setup"
}
```

**Failed or pending document extraction:**
```json
{
  "area": "documents",
  "title": "Resolve extraction failure",
  "cta_label": "Open failed document",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=documents&document={document_id}&status=failed"
}
```

**Pending syllabus mentions:**
```json
{
  "area": "syllabus",
  "title": "Review syllabus mentions",
  "cta_label": "Review {N} pending mentions",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?tab=syllabus&status=pending"
}
```

**Unlocked or pending topic coverage:**
```json
{
  "area": "topic_coverage",
  "title": "Lock topic coverage",
  "cta_label": "Review unlocked rows",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?tab=syllabus&status=pending_review"
}
```

**Selected PYQ paper / pending questions:**
```json
{
  "area": "pyq",
  "title": "Verify PYQ questions",
  "cta_label": "Review {N} pending questions",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=pyq&paper={paper_id}&status=pending"
}
```

**Pending policy updates:**
```json
{
  "area": "updates",
  "title": "Review policy updates",
  "cta_label": "Review {N} pending updates",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?tab=updates&status=pending"
}
```

**Selected-cycle competition context:**
```json
{
  "area": "competition",
  "title": "Add competition context",
  "cta_label": "Open competition for {cycle_year}",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=competition"
}
```

**Review and activation gate:**
```json
{
  "area": "publish",
  "title": "Activate exam",
  "cta_label": "Go to Review & Activate",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}&tab=review"
}
```

### 7.3 Acceptance test

The acceptance test for deep-link quality:

> Can an operator receive a blocker notification and navigate directly to the exact unresolved task without first opening the Overview tab or searching for the problem manually?

Generic "Open workspace" or "Manage exam" CTAs that do NOT include tab or entity context are NOT acceptable for action queue items.

---

## Section 8: Portfolio/readiness backend read-model contract

### 8.1 Purpose

The front-door content (Section 5) and Manage Exam verdict header (Section 6) require a backend read model that does not currently exist in unified form.

The current `work_queue` list endpoint provides cross-exam status but not per-cycle phases, dates, and section readiness. The current `readiness.py` provides per-cycle section readiness but not the family/exam hierarchy or phase dates. A unified read model is required.

**Note: this is a backend prerequisite. It is NOT a UI surface. Do NOT implement the endpoint in this PR.**

### 8.2 Endpoint shape (LOCKED contract)

**Two endpoints (minimum):**

| Endpoint | Purpose |
|---|---|
| `GET /api/admin/exam-intelligence/management/exams` | Paginated list — family/exam/cycle/phase hierarchy with top-level status |
| `GET /api/admin/exam-intelligence/management/exams/{exam_id}` | Single-exam detail — full per-cycle section readiness |

**Path rationale:** `/management/` reflects the product-level purpose (exam management operations), is distinct from `/console/` and `/workspace/` legacy paths, and avoids the `/portfolio` label which implies a reporting surface rather than an operational read model.

Alternative: a single endpoint with an `include_detail` parameter is acceptable if it avoids a double roundtrip for the front door. Justify in the backend PR.

### 8.3 Deterministic current-cycle selection rule (LOCKED)

The list endpoint MUST return exactly one "current cycle" per exam. When no cycle is explicitly selected, the backend MUST apply this deterministic selection rule in priority order:

1. Any cycle where `status = 'active'` — most common case for live exams
2. Any cycle where `status = 'open'` — notification/recruitment phase
3. Any cycle where `status = 'expected'` — announced but not yet open
4. Highest `year` among remaining cycles — most recent historical
5. Lowest UUID tie-breaker — deterministic when year is equal

The backend, not the frontend, applies this rule. The frontend receives `current_cycle` as a pre-selected field. The frontend MUST NOT recompute or override this selection on initial load.

### 8.4 List endpoint response responsibilities

The list endpoint MUST return (per exam):

- `id`, `name`, `slug`, `family_id`, `family_name`
- `organization_id`, `organization_name`
- `management_mode`, `cadence`, `is_active`
- Top-level verdict: `status` (`blocked | needs_action | ready`) — from `classify_exam`
- `first_blocker_text`, `blocker_count`
- Readiness summary: `readiness_summary` (per-section high-level state, advisory)
- Active/current cycle: `{ id, name, year, phases: [{slug, label, start_date, end_date, status}] }`
- All exam flags from `classify_exam`

The list endpoint MUST support:

- Pagination (`limit`, `offset`, `total_count`, `has_next`)
- Same filters as `ConsoleWorkQueue` (search, exam_type, active_state, management_mode, cadence, exam_family_id, workflow, sort)
- Failure semantics: any correctness-critical read that fails MUST raise an error — never silently return empty/fabricated data

### 8.5 Detail endpoint response responsibilities

The detail endpoint MUST return, for one exam:

- All fields from the list endpoint for that exam
- All cycles (not just active): `[{ id, name, year, phases: [...] }]`
- Per-cycle section readiness for the selected cycle (or all cycles if no cycle specified):
  - `setup`: phase count, status
  - `documents`: per-document upload/extraction state using the locked vocabulary from Section 4.4
  - `syllabus`: pending/reviewed mention count
  - `topic_coverage`: locked/total row count
  - `pyq`: verified/total question count, per-paper summary
  - `updates`: pending/reviewed update count
  - `competition`: metric count for selected cycle
  - `review_activate`: composite readiness state
- Per-section blockers (text, severity)
- Evidence references per blocker (document ID, paper ID, topic ID, etc.)
- The exact section-state vocabulary from Section 4.4

### 8.6 No second classifier

The detail endpoint MUST use `work_queue.classify_exam` for the top-level verdict. It MUST NOT introduce a second classification algorithm, even for advisory purposes. Advisory per-section state is computed from section-level evidence, not from a parallel top-level classifier.

### 8.7 Failure semantics

- A missing exam → 404
- A failed correctness-critical read → 5xx (via `execute_or_raise`)
- A failed advisory/optional read → null field in the response, not 5xx
- The frontend MUST handle null advisory fields gracefully

---

## Section 9: Advanced Repair access model

### 9.1 Entry path (LOCKED)

```
Manage Exam → More (overflow button/menu) → Advanced Repair
```

**There is no other entry path from normal navigation.**

### 9.2 Locked constraints

- **Exam scope:** when entered from Manage Exam, Advanced Repair receives `exam_id` and `cycle_id` (where applicable) as query parameters and MUST pre-scope entity lists to that exam/cycle where the CMS supports scoping.
- **Permission gate (LOCKED):** Advanced Repair MUST require permission `exam_intelligence.cms`. This token is already defined in `admin_exam_intel_cms.py` at `PERM_CMS = "exam_intelligence.cms"` (line 55). I8-C MUST reuse this exact token — do not introduce a new token. The gate is non-negotiable; users without `exam_intelligence.cms` must not reach the Advanced Repair UI.
- **Explicit warning:** when entering Advanced Repair, the operator MUST see an explicit warning (existing `AdminSafetyBanner` pattern) stating that this tool is for exceptional repair work and that normal operational work belongs in Manage Exam. This is not a tooltip; it must be a visible UI element.
- **NOT a sidebar peer:** Advanced Repair MUST have no sidebar entry after I8-C.
- **NOT a primary CTA:** Advanced Repair MUST NOT appear as a primary or prominent button on any page except the overflow menu inside Manage Exam.
- **No generic entity selector next to normal blocker cards:** the generic CMS entity picker MUST NOT be embedded in or near the normal blocker resolution flow.
- **Review and locking lifecycle must NOT be bypassed:** Advanced Repair provides entity editing, but it does not provide unrestricted `reviewer_status` promotion. The review lifecycle (pending → reviewed → locked) remains enforced in all paths, including Advanced Repair.

### 9.3 Global super-admin recovery

A global super-admin recovery path (accessing `/admin/exam-intelligence/cms` directly without an `exam_id` parameter) may remain available for:

- cross-exam entity repair
- deduplication
- broken foreign-key repair
- exceptional migration backfills

This path MUST be:
- Navigable only by explicit URL entry or from a super-admin-only control
- Not exposed in the normal KG sidebar or any primary nav after I8-C
- Protected by the same permission gate and warning as the exam-scoped path

---

## Section 10: I8 delivery sequence and write scopes

### 10.1 Strict serial delivery (LOCKED)

I8-A, I8-B, and I8-C MUST be dispatched to one owner in strict sequence. They MUST NOT be fanned out to parallel agents.

Reason: all three PRs edit the same routing and navigation files (`AdminShell.jsx`, `adminRoutes.jsx`, `ExamIntelligence.jsx`, `ExamWorkspace.jsx`, `ExamWorkspaceContext.jsx`, route tests, navigation active-state tests). Parallel agents on these files produce merge conflicts, duplicate dead code, and broken active-nav state.

### 10.2 Backend read-model prerequisite

Before I8-A can be fully tested and before I8-B can display real data:

- The management/readiness read-model backend endpoints (Section 8) must be implemented
- H2 (BUG-EI-2 extraction readiness fix) — **DONE. PR #750 merged on main.** No further action required.
- The backend is parallel-safe with documentation work; it must not be delayed by waiting for I8-A

**Backend prerequisite PR write scope:**
- `app/backend/app/api/admin_exam_intelligence.py` (new management endpoints at `/management/exams`)
- `app/backend/app/exam_intelligence/readiness.py` (share logic; H2 fix already present on main)
- `app/backend/app/exam_intelligence/console_detail.py` (fix deep-link routes, see Section 7)
- `app/backend/tests/exam_intelligence/` (tests for new endpoints and fixes)

### 10.3 I8-A: Exam Management front door

**Goal:** single sidebar entry replacing KG exam group; front door with triage list and family/exam/cycle content; Manage exam row action.

**CRITICAL ATOMIC SCOPE:** I8-A MUST remove ALL existing exam sidebar items in the SAME PR. Do not split removal across I8-B or I8-C. The items that must disappear atomically in I8-A:
- Exam Governance Console (`/admin/exam-intelligence/console`)
- Exam Registry (`/admin/exam-intelligence`)
- Create exam (`/admin/exam-intelligence/new`) — demote to overflow, not a peer nav item
- Advanced Import / Repair (`/admin/exam-intelligence/cms`) — remove from nav; I8-C handles access model

After I8-A merges, exactly 1 exam-related nav item must exist: Exam Management. There is no intermediate state with 4 items becoming 2 items. The atomic removal prevents dead nav entries from confusing operators during the transition.

**Likely write scope:**
- `app/frontend/src/pages/admin/AdminShell.jsx` — remove KG exam group items; add single Exam Management entry; update `HAS_OWN_NAV` array
- `app/frontend/src/routes/adminRoutes.jsx` — add `/admin/exam-intelligence/exams/:exam_id` canonical route; preserve all legacy routes (no 404s)
- `app/frontend/src/pages/admin/ExamIntelligence.jsx` — evolve into Exam Management front door (single-view, no tabs)
- `app/frontend/src/features/admin/exam-intelligence/ConsoleWorkQueue.jsx` — integrate as front-door triage list or absorb logic
- `app/frontend/src/routes/navContract.test.js` — update nav path list and route list
- `app/frontend/src/pages/admin/__tests__/AdminShell.nav.test.js` — update for new nav structure
- `app/frontend/src/pages/admin/__tests__/ExamIntelligenceNav.test.jsx` — update or migrate
- `docs/status/career-copilot-checklist.md` — update I8-A status

**Do-not-touch boundaries for I8-A:**
- `ExamWorkspace.jsx`, `ExamWorkspaceContext.jsx`, all workspace panels (owned by I8-B)
- `ExamIntelCms.jsx` component internals (owned by I8-C; I8-A only removes nav entry)
- Backend API files (owned by prerequisite PR)

### 10.4 I8-B: Manage Exam consolidation

**Goal:** evolve ExamWorkspace into Manage Exam at canonical route; embed ExamActionConsole content; implement deep-link blocker CTAs; resolve Overview tab; update cycle selector to query param.

**Likely write scope:**
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx` — evolve; add canonical route; embed action console content; remove Overview tab; fix cycle selector
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx` — update cycle selection to query param
- `app/frontend/src/features/admin/exam-intelligence/ExamActionConsole.jsx` — embed/inline inside workspace; update CTA routes
- `app/frontend/src/routes/adminRoutes.jsx` — add legacy `<Navigate>` redirects for `/workspace/:exam_id` → `/exams/:exam_id`
- `app/frontend/src/pages/admin/ExamGovernanceConsole.jsx` — compatibility shell or retire
- `app/frontend/src/pages/admin/exam-workspace/__tests__/ExamWorkspace.test.jsx` — update for new route and structure
- `app/frontend/src/pages/admin/__tests__/ExamGovernanceConsole.test.jsx` — update or retire
- Backend: `console_detail.py` CTA route fixes (or confirm done in prerequisite PR)
- `docs/status/career-copilot-checklist.md` — update I8-B status

**Do-not-touch boundaries for I8-B:**
- `AdminShell.jsx` nav entries (locked by I8-A; do not regress)
- `ExamIntelCms.jsx` (owned by I8-C)
- Workspace panel components other than `OverviewPanel` (must not be disrupted)

### 10.5 I8-C: Advanced Repair isolation

**Goal:** add overflow entry in Manage Exam; add `exam_intelligence.cms` permission gate and warning inside CMS component.

**SCOPE BOUNDARY:** I8-C does NOT re-do sidebar removal. Sidebar removal of `ExamIntelCms.jsx` nav entry is already done atomically by I8-A. I8-C scope is limited to: (a) adding the overflow action inside Manage Exam, (b) adding the permission gate (`exam_intelligence.cms`) to the CMS component entry, and (c) adding the explicit safety warning.

**Likely write scope:**
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx` — add More → Advanced Repair overflow action pointing to `/admin/exam-intelligence/cms?exam_id=:exam_id`
- `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx` — add entry-point guard for `exam_intelligence.cms` permission; add `AdminSafetyBanner` warning; add exam-scoped pre-filtering when `exam_id` query param is present; retain global recovery path for super-admin
- `app/frontend/src/routes/adminRoutes.jsx` — verify `/cms` route is retained (must not 404) but not in nav
- `docs/status/career-copilot-checklist.md` — update I8-C status

**Do-not-touch boundaries for I8-C:**
- `AdminShell.jsx` nav entries (locked by I8-A — do not re-remove or re-add anything)
- All workspace panels (locked by I8-B)
- Front-door content (locked by I8-A)

### 10.6 Compatibility redirects

Land redirects for legacy routes in I8-B (workspace) and I8-C (console, CMS nav):

```
/admin/exam-intelligence/workspace/:exam_id       →  /admin/exam-intelligence/exams/:exam_id
/admin/exam-intelligence/workspace/:exam_id/:cid  →  /admin/exam-intelligence/exams/:exam_id?cycle=:cid
/admin/exam-intelligence/console                  →  /admin/exam-intelligence
/admin/exam-intelligence/console/:exam_id         →  /admin/exam-intelligence/exams/:exam_id
```

Redirects go in `adminRoutes.jsx` using `<Navigate replace />`.

### 10.7 Dead/orphan component cleanup

After redirects pass and redirect tests are green:

- Remove `ExamGovernanceConsole.jsx` (if reduced to a thin shell with no logic)
- Remove or archive `OverviewPanel.jsx` (if Overview tab is eliminated)
- Remove any `HAS_OWN_NAV` entries in `AdminShell.jsx` that no longer apply
- These cleanups happen in a post-I8-C cleanup PR, not in I8-A/B/C themselves

---

## Section 11: Test migration plan

### 11.1 Existing tests that must be migrated

| Test file | Migration obligation |
|---|---|
| `app/frontend/src/routes/navContract.test.js` | Update ADMIN_NAV_PATHS to replace old console/workspace/cms paths with canonical paths; add `/admin/exam-intelligence/exams/:exam_id` shape test |
| `app/frontend/src/pages/admin/__tests__/AdminShell.nav.test.js` | Update group count if KG exam lane collapses; update testId assertions for new Exam Management single entry |
| `app/frontend/src/pages/admin/__tests__/ExamIntelligenceNav.test.jsx` | Update for new front-door structure; remove assertions about Open console / Advanced workspace header CTAs |
| `app/frontend/src/pages/admin/ExamIntelligence.test.jsx` | Update or merge with ExamIntelligenceNav.test.jsx |
| `app/frontend/src/pages/admin/__tests__/ExamGovernanceConsole.test.jsx` | Update if console becomes compatibility shell; retire if console is fully removed |
| `app/frontend/src/pages/admin/exam-workspace/__tests__/ExamWorkspace.test.jsx` | Update for new route (`/exams/:exam_id`), query-param cycle selection, removed Overview tab, embedded action console |
| E2E workspace tests (if any) | Update route assertions; ensure no hardcoded `/workspace/` paths remain |

### 11.2 Required acceptance tests (new or updated)

Each item below is a named acceptance test that MUST pass before the corresponding I8 sub-PR can merge:

**I8-A acceptance tests:**

```
[ ] admin nav renders exactly 1 Exam Management sidebar entry (testId: admin-nav-exam-management)
[ ] KG sidebar group has no Exam Governance Console item
[ ] KG sidebar group has no Exam Registry item
[ ] KG sidebar group has no Create exam advanced item (or it is demoted to non-primary)
[ ] KG sidebar group has no Advanced Import / Repair advanced item
[ ] /admin/exam-intelligence renders the Exam Management front door
[ ] Manage exam row action links to /admin/exam-intelligence/exams/:exam_id
[ ] All old exam-intel routes still return 200 (not 404)
```

**I8-B acceptance tests:**

```
[ ] /admin/exam-intelligence/exams/:exam_id renders the Manage Exam page
[ ] Cycle selector stores selection in URL query param ?cycle=:cycle_id
[ ] Active-nav highlights Exam Management entry when on /exams/:exam_id path
[ ] Overview tab does not appear as a standalone tab
[ ] Action queue renders with at least one blocker CTA containing a tab parameter
[ ] CTA for syllabus action links to ?tab=syllabus
[ ] CTA for documents action links to ?tab=documents&document=...
[ ] CTA for PYQ action links to ?tab=pyq&paper=...
[ ] /admin/exam-intelligence/workspace/:exam_id redirects to /admin/exam-intelligence/exams/:exam_id (no 404)
[ ] /admin/exam-intelligence/workspace/:exam_id/:cycle_id redirects with ?cycle=:cycle_id
[ ] /admin/exam-intelligence/console/:exam_id redirects to /admin/exam-intelligence/exams/:exam_id
```

**I8-C acceptance tests:**

```
[ ] /admin/exam-intelligence/cms has no sidebar entry
[ ] Manage Exam page renders More → Advanced Repair overflow action
[ ] Advanced Repair overflow action links to /admin/exam-intelligence/cms?exam_id=:exam_id
[ ] Accessing Advanced Repair without permission shows a 403 or permission error
[ ] AdminSafetyBanner (warning) is visible on entry to Advanced Repair
[ ] /admin/exam-intelligence/console redirects to /admin/exam-intelligence (no 404)
[ ] Surface-count exit test passes: visible exam nav entries == 1
```

**Post-I8-C cleanup acceptance tests:**

```
[ ] No component import for ExamGovernanceConsole remains in active routes (if retired)
[ ] No OverviewPanel import remains in active workspace tabs (if retired)
[ ] All redirect tests remain green
[ ] navContract.test.js passes with updated path lists
```

---

## Section 12: Component retirement plan

Retirement is blocked on redirect tests passing. No component may be deleted before its redirect test is green.

| Component | Retirement status | Blocked on |
|---|---|---|
| `ExamIntelligence.jsx` | Retained — evolved in I8-A | N/A |
| `ConsoleWorkQueue.jsx` | Retained — embedded/reused in I8-A | N/A |
| `ExamGovernanceConsole.jsx` | Retired after redirects pass | I8-B redirect tests green |
| `ExamActionConsole.jsx` | Embedded/reused inside ExamWorkspace in I8-B; standalone route retired | I8-B redirect test for `/console/:exam_id` |
| `ExamWorkspace.jsx` | Retained — evolved in I8-B; old route redirected | N/A (route changes, component stays) |
| `ExamWorkspaceContext.jsx` | Retained — evolved in I8-B | N/A |
| `ExamIntelCms.jsx` | Retained — access model changed in I8-C; no deletion | N/A |
| `OverviewPanel.jsx` | Retired after I8-B if Overview tab eliminated | I8-B completion |
| `AddCycleRedirect` in adminRoutes.jsx | Decision deferred — may redirect to new canonical route | I8-B |
| `AdminGuidedExamWizard` at `/new` | Decision deferred — may remain or be demoted | I8-A UX decision |

### 12.1 Retirement sequence guarantee

The implementor MUST NOT delete any component in the list above until:

1. The redirect for that component's route is live in `adminRoutes.jsx`
2. The redirect test for that route is passing in CI
3. All internal links that pointed to that component's old route have been updated

This sequence is non-negotiable. Deleting before redirect tests pass creates 404 states that violate the redirect sequence in Section 2.4.

---

## Section 13: Non-goals

This document and the I8-A/B/C PRs MUST NOT implement or authorize any of the following:

- **I9 implementation** — the guided cycle-setup workflow (hybrid mini-wizard + persistent 9-step checklist). Blocked on the I6 cycle-setup gate document. Do not implement any part of I9 under the I8 label.
- **J1/J2/J3 implementation** — Advanced Repair scoping, missing operational editors, schema redesign. Blocked on I8-C. Do not implement CMS entity CRUD improvements in I8 PRs.
- **KG rename** — renaming "Knowledge Governance" to "Policy & Trust" or any other label. Separate later PR. Must not be folded into I7 or I8-A.
- **Competition schema redesign** — the opaque JSONB for `cutoff_trend` and `vacancy_by_category` is a deferred contract-first problem. Do not add structured competition fields in I8.
- **Mixed-format PDF architecture** — current extraction pipeline assigns one format per document. Do not change extraction behavior in I8.
- **Coverage-governance policy** — who assigns management mode, cadence, coverage depth, priority score, high-yield designation. Deferred product contract. Do not implement governance rules in I8.
- **New portfolio page** — any new route that serves as a portfolio dashboard or coverage matrix view. Cancelled. These capabilities are content inside Exam Management and Manage Exam, not new routes.
- **New coverage matrix** — same as above.
- **Runtime code changes in this PR** — this document is a planning artifact. No runtime files are changed in this PR. The branch contains only documentation and tracker updates.

---

## Appendix A: Code evidence index

The following files were read to verify the decisions in this document:

### Routes and navigation

- `app/frontend/src/routes/adminRoutes.jsx` — confirmed all current exam-intel route paths and component assignments
- `app/frontend/src/pages/admin/AdminShell.jsx` — confirmed `KG_LANE_1`, `KG_LANE_1_ADVANCED`, the `HAS_OWN_NAV` list, and the sidebar section structure

### Existing surfaces

- `app/frontend/src/pages/admin/ExamIntelligence.jsx` — confirmed Overview/Exams tab split, five competing header CTAs, filter/search state
- `app/frontend/src/pages/admin/ExamGovernanceConsole.jsx` — confirmed thin shell pattern, branches on examId, renders ConsoleWorkQueue or ExamActionConsole
- `app/frontend/src/features/admin/exam-intelligence/ConsoleWorkQueue.jsx` — confirmed work-queue endpoints, filter/sort state, "Open console" + "Advanced workspace" dual row actions
- `app/frontend/src/features/admin/exam-intelligence/ExamActionConsole.jsx` — confirmed `console_detail` data model, `cta_route` generic workspace defect, evidence/reason rendering
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx` — confirmed TAB_ORDER (8 tabs including Overview), SmartHeader readiness percentage, score_percent display, cycle navigation via path segment
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx` — confirmed context fetches, cycle_id from useParams, readiness fetched separately
- `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx` — confirmed entity-list CMS, renderCellValue UUID truncation, no guided exam CTA

### Backend readiness and classification

- `app/backend/app/exam_intelligence/work_queue.py` — confirmed `classify_exam` as single classifier; `blocked | needs_action | ready` status; no score_percent
- `app/backend/app/exam_intelligence/console_detail.py` — confirmed status parity with work_queue classifier; confirmed BUG-EI-2 Option A fix comment; confirmed `_documents()` now queries `syllabus_documents`
- `app/backend/app/exam_intelligence/readiness.py` — confirmed `_documents()` queries `document_assets.extraction_status` (BUG-EI-2 still present here); confirmed `score_percent` computation
- `app/backend/app/api/admin_exam_intelligence.py` — confirmed ADMIN_PERM, router prefix, coverage status vocabulary

### Test files

- `app/frontend/src/routes/navContract.test.js` — confirmed static path list pattern
- `app/frontend/src/pages/admin/__tests__/AdminShell.nav.test.js` — confirmed 7-group test, section expansion tests
- `app/frontend/src/pages/admin/__tests__/ExamIntelligenceNav.test.jsx` — exists; content confirms nav assertions exist
- `app/frontend/src/pages/admin/__tests__/ExamGovernanceConsole.test.jsx` — exists; must be migrated in I8-B
- `app/frontend/src/pages/admin/exam-workspace/__tests__/ExamWorkspace.test.jsx` — exists; must be migrated in I8-B

---

## Appendix B: Resolved decisions

All previously deferred items are now resolved. No items block I8-A/B/C.

| Item | Resolution | Resolved by |
|---|---|---|
| Permission token for Advanced Repair gate | **LOCKED: `exam_intelligence.cms`** — already defined in `admin_exam_intel_cms.py` line 55. I8-C must reuse this exact token; do not introduce a new permission string. | Section 9.2 |
| `AdminGuidedExamWizard` at `/new` / Create Exam placement | **LOCKED: overflow only.** Create Exam is demoted from a primary header CTA to an overflow action (not a peer nav item, not a primary button on the front door). The `/new` route is preserved for compatibility but removed from `HAS_OWN_NAV`. | Section 3.2, Section 10.3 |
| `ExamIntelligence.jsx` front-door tab structure | **LOCKED: single-view, no tabs.** The front door is a single view (triage list with family/exam/cycle hierarchy). No Overview vs Exams tab competition. No tabs at the front door level. | Section 3.2 |
| `AddCycleRedirect` at `/exams/:exam_id/add-cycle` | **LOCKED: redirect target is `/exams/:exam_id?tab=setup&action=add-cycle`.** The `action=add-cycle` query param is meaningful after I8-B — it signals the Setup tab should open the Add Cycle wizard inline. I8-B must implement this handler in the Setup tab. | Section 2.4, Section 10.4 |
| AdminShell group count in `AdminShell.nav.test.js` | **NOT BLOCKING.** The group count test is an implementation detail, not a design gate. The implementor updates this test as part of I8-A when the nav structure changes. No design decision is required in advance. | Section 10.3 |

---

*This document is a planning artifact. No runtime files were changed in the PR that introduced it.*
