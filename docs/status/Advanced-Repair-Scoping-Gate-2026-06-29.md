# Advanced Repair Scoping Gate — J1 Contract

- Document type: J1 implementation contract — Advanced Repair scoping
- Status: **OPERATOR APPROVED — IMPLEMENTATION COMPLETE (PR #820)**
- Date: 2026-06-29
- Approval date: 2026-06-30 (operator johnefficacy-crypto, verbal "J1" selection)
- Parent track: `J1 — Advanced Repair scoping` (`docs/status/career-copilot-checklist.md` row "J1 — Advanced Repair scoping")
- Authority: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §9 (Advanced Repair access model)
- Gates cleared: I8-C merged (PR #759 `f4378097`); I6 merged (PR #761 `d69602f8`)
- Implementation PR: #820 (`claude/j1-advanced-repair-scoping`)

---

## How to use this document

Every section states a LOCKED decision or an exact specification that the implementation PR must follow. Deviations require a new gate document, not a PR-level justification. Unresolved items are called out explicitly and must not be guessed or invented.

**No implementation PR may be dispatched until this document is OPERATOR APPROVED.**

---

## Section 0 — What already exists in ExamIntelCms.jsx (post-I8-C baseline)

The following capabilities are **already present** on `main` after PR #759. The J1 implementation must extend them, not duplicate or contradict them.

### 0.1 Route and entry point

- Route: `/admin/exam-intelligence/cms` — retained from I8 (must not 404).
- Entry: exclusively via `Manage Exam → More → Advanced Repair` overflow menu (`AdvancedRepairMenu` component, landed in I8-C).
- No sidebar entry (removed atomically in I8-A; must not be restored).

### 0.2 Search params already read on mount

`ExamIntelCms.jsx` reads the following query parameters from the URL via `useSearchParams`:

| Param | Purpose |
|---|---|
| `exam_id` | Pre-scopes entity lists to the selected exam |
| `cycle_id` | Pre-scopes entity lists to the selected cycle (where the entity type supports it) |

These params are already wired. The URL shape when entering from Manage Exam is:

```
/admin/exam-intelligence/cms?exam_id=:exam_id[&cycle_id=:cycle_id]
```

### 0.3 Permission gate (already present)

`ExamIntelCms.jsx` requires `exam_intelligence.cms` permission. The token is defined in `admin_exam_intel_cms.py` at `PERM_CMS = "exam_intelligence.cms"` (line 55). This gate was implemented in I8-C and must not be changed or duplicated.

### 0.4 AdminSafetyBanner (already present)

An `AdminSafetyBanner` is already rendered at the top of `ExamIntelCms.jsx` with `collapsible={false}`, warning operators that this tool is for exceptional repair work and that normal operational work belongs in Manage Exam. This must remain `collapsible={false}`.

### 0.5 Entity list and scope sets (already present)

`ExamIntelCms.jsx` defines two scope sets:

**`ENTITY_EXAM_SCOPE`** — entities whose list endpoint accepts `exam_id`:

```
exam-cycles, exam-phases, syllabus-documents, pyq-papers, exam-topic-coverage,
policy-updates, exam-competition-metrics, pyq-sources, syllabus-topic-mentions
```

**`ENTITY_CYCLE_SCOPE`** — entities whose list endpoint also accepts `exam_cycle_id`:

```
exam-phases, pyq-papers
```

When `exam_id` is present in search params and the selected entity is in `ENTITY_EXAM_SCOPE`, the list request already includes `exam_id`. When `cycle_id` is also present and the entity is in `ENTITY_CYCLE_SCOPE`, the list request already includes `exam_cycle_id`. These scope sets are the implementation foundation for J1.

### 0.6 Entities NOT in any scope set (global-only lists)

The following entities are not scoped by exam or cycle and always return global lists:

```
exam-families, exams, subjects, topics, topic-aliases, topic-prerequisites,
pyq-questions, pyq-options, pyq-question-tags, exam-phase-sections,
source-registry, documents
```

---

## Section A — Gap analysis: what J1 adds

### A.1 What does NOT yet exist

The current implementation applies scope params to list requests but has no search, filtering, or pagination controls in the `ExamIntelCms.jsx` UI. The operator sees all rows returned by the backend for the scoped entity without any way to narrow them further within the page.

**Specific gaps J1 must close:**

| # | Gap | Description |
|---|---|---|
| G-1 | No search input | No text search field to filter entity rows by name, slug, title, or other text fields within the page |
| G-2 | No status/type filter | No UI filter for `reviewer_status`, `trust_status`, `source_type`, or similar categorical fields |
| G-3 | No pagination | All rows for the scoped entity/exam/cycle are loaded at once; no page-size control or next/prev navigation |
| G-4 | Scope state not visible | The operator cannot see which exam/cycle scope is active at a glance from the CMS page header |

### A.2 What J1 does NOT add

- No new route, no new sidebar entry, no new top-level surface.
- No changes to the permission gate (`exam_intelligence.cms` — unchanged).
- No changes to `AdminSafetyBanner` (`collapsible={false}` — unchanged).
- No changes to the `ENTITY_EXAM_SCOPE` or `ENTITY_CYCLE_SCOPE` sets (already correct after I8-C).
- No changes to entity field definitions or CRUD logic.
- No changes to backend endpoint signatures (search/filter params already accepted by all relevant list endpoints).
- No new database migrations.
- No changes to `AdminShell.jsx`, `adminRoutes.jsx`, `ExamWorkspace.jsx`, or any routing file.

---

## Section B — Scoping contract

### B.1 Active scope indicator (LOCKED)

When `exam_id` is present in search params, `ExamIntelCms.jsx` MUST display a visible scope indicator in the page header/subheader area showing:

- The name of the selected exam (resolved from the `exam_id`)
- The name of the selected cycle, if `cycle_id` is also present (resolved from `cycle_id`)
- A "Clear scope" action that removes both params from the URL (returns to global/super-admin recovery mode)

The scope indicator must be rendered above the entity selector, so the operator knows before selecting an entity which scope is active.

### B.2 Endpoint scope params — which endpoints get exam_id / cycle_id (LOCKED)

The following table is the authoritative contract. It derives from the existing `ENTITY_EXAM_SCOPE` and `ENTITY_CYCLE_SCOPE` sets in `ExamIntelCms.jsx`, verified against backend route signatures.

| Entity key | Accepts `exam_id` | Accepts `exam_cycle_id` | Notes |
|---|---|---|---|
| `exam-cycles` | Yes | No | `exam_id` scopes cycles to one exam |
| `exam-phases` | Yes | Yes | Both params narrow phases |
| `syllabus-documents` | Yes | No | `exam_id` required for syllabus docs |
| `pyq-papers` | Yes | Yes | Both params narrow papers |
| `exam-topic-coverage` | Yes | No | `exam_id` required |
| `policy-updates` | Yes | No | `exam_id` required |
| `exam-competition-metrics` | Yes | No | `exam_id` required |
| `pyq-sources` | Yes | No | `exam_id` required |
| `syllabus-topic-mentions` | Yes | No | `exam_id` required |
| All others | No | No | Global list; scope params silently ignored by backend |

### B.3 Default behavior (LOCKED)

| Condition | Behavior |
|---|---|
| `exam_id` present, entity is in `ENTITY_EXAM_SCOPE` | List request includes `exam_id=:exam_id`; search/filter/pagination scoped to that exam |
| `exam_id` present, entity NOT in `ENTITY_EXAM_SCOPE` | List request has no `exam_id`; full global list; scope indicator shows a note that this entity is not scopable |
| `exam_id` absent | Global recovery mode; all entities return global lists; no scope indicator shown |
| `cycle_id` present without `exam_id` | `cycle_id` is ignored; same as no scope; operator must provide `exam_id` for scoping to be active |

### B.4 Search param naming (LOCKED)

The backend column name is `exam_cycle_id`, NOT `cycle_id`. The URL query param uses `cycle_id` (shorter, already wired in I8-C). The frontend MUST translate `cycle_id` (from URL) → `exam_cycle_id` (to backend) when constructing list requests for entities in `ENTITY_CYCLE_SCOPE`. This translation is already present in the I8-C implementation and must not be broken.

---

## Section C — UI contract

### C.1 Search input (LOCKED)

- A text input labeled "Search" (or "Filter rows") appears at the top of the entity list, below the scope indicator and entity selector.
- The search input sends a `search` query param to the backend list endpoint.
- Debounce: 300 ms minimum between keystrokes and request dispatch.
- The search input clears when the selected entity changes.
- Placeholder text: `"Search <entity label>…"` (uses the entity's `label` from `ENTITY_CONFIG`).
- The search input is NOT shown for entities that are not in `ENTITY_EXAM_SCOPE` AND no `exam_id` is present (global recovery mode); it MAY still be shown in global recovery mode for operator convenience — this is an implementation choice, not a locked requirement.

### C.2 Status / categorical filter (LOCKED)

- A `<select>` filter for `reviewer_status` appears for entities that have a `reviewer_status` column:
  - `syllabus-topic-mentions`, `exam-topic-coverage`, `policy-updates`, `pyq-questions`
- A `<select>` filter for `trust_status` appears for entities that have a `trust_status` column:
  - `syllabus-documents`, `pyq-papers`, `pyq-sources`
- The filter sends the status value as a query param (`reviewer_status` or `trust_status`) to the backend list endpoint.
- A "(all statuses)" default option must be available (empty/no filter).
- The filter clears when the selected entity changes.

### C.3 Pagination (LOCKED)

- Page size: 50 rows per page (constant; no user-configurable page size in J1).
- Backend params: `limit=50&offset=<(page-1)*50>`.
- Controls: "Previous" and "Next" buttons, a page indicator (`Page N of M` or `Showing N–M of total`), rendered below the entity table.
- `total_count` is expected from the backend (all list endpoints return it); if absent, disable "Next" when fewer than 50 rows are returned.
- Pagination resets to page 1 when the search input changes, when the status filter changes, when the entity selection changes, or when the scope params change.

### C.4 Query params used (LOCKED)

The following URL/request query params are used by the J1 controls:

| Control | Backend param | Notes |
|---|---|---|
| Search input | `search` | Text string; passed as-is |
| Status filter | `reviewer_status` or `trust_status` | Depends on entity type |
| Page navigation | `limit`, `offset` | Always integers; `limit=50` constant |
| Scope (existing) | `exam_id`, `exam_cycle_id` | Already implemented pre-J1 |

The URL (browser address bar) is NOT updated with search/filter/page state in J1. These controls are in-memory only (component state). Deep-linking to a specific search/filter/page is out of scope for J1.

### C.5 Control placement (LOCKED)

```
[Scope indicator: "Scoped to: <Exam Name> · <Cycle Name>" | [Clear scope]]
[Entity selector dropdown]
[Search input]  [Status filter (if applicable)]
[Entity table — rows]
[Previous] [Page N of M] [Next]
[New row / Bulk import / Reload controls — unchanged]
```

The New row, Bulk import, and Reload controls remain in their current positions (below the table, or in the header — not changed by J1).

---

## Section D — Permission gate contract

**LOCKED — no change from I8-C.**

- Required permission: `exam_intelligence.cms` (token: `PERM_CMS` at `admin_exam_intel_cms.py` line 55).
- Super-admin bypass applies (matching the rest of the admin surface).
- Users without `exam_intelligence.cms` must not reach the Advanced Repair UI; they receive a permission error or are redirected.
- J1 must NOT introduce a new permission token.
- J1 must NOT change or weaken the existing gate.

---

## Section E — AdminSafetyBanner contract

**LOCKED — no change from I8-C.**

- `AdminSafetyBanner` is rendered at the top of `ExamIntelCms.jsx`.
- `collapsible={false}` — the banner must always be visible; it must not be made collapsible or dismissible.
- Banner text (existing): warns that this tool is for exceptional repair work and that normal operational work belongs in Manage Exam.
- J1 must NOT change banner text, collapsibility, or placement.

---

## Section F — Decisions (LOCKED)

| ID | Decision | Status |
|---|---|---|
| OD-1 | Scope params wiring | **LOCKED** — `exam_id` / `cycle_id` already wired in I8-C. J1 extends the UI with search/filter/pagination built on the existing scoped list requests. No new scope wiring is needed. |
| OD-2 | Search param name sent to backend | **LOCKED** — `search`. All relevant CMS list endpoints accept a `search` query param. If an endpoint does not support it, the frontend omits it and the control is hidden for that entity. |
| OD-3 | Status filter field selection | **LOCKED** — `reviewer_status` for mention/coverage/policy/question entities; `trust_status` for document/paper/source entities. Determined by which field is present in the entity's `ENTITY_CONFIG.fields` array. |
| OD-4 | Page size | **LOCKED** — 50 rows per page, constant. Not user-configurable in J1. |
| OD-5 | URL state for search/filter/page | **LOCKED** — in-memory only in J1. Browser URL reflects `exam_id` / `cycle_id` scope params (existing) but not search/filter/page state. Deep-linking to search state is deferred. |
| OD-6 | Non-scopable entity behavior | **LOCKED** — when `exam_id` is present but the selected entity is not in `ENTITY_EXAM_SCOPE`, the list loads globally AND the scope indicator shows a note: "This entity is not scoped by exam." No error; no hidden entity. |
| OD-7 | Scope indicator placement | **LOCKED** — above the entity selector, always visible when `exam_id` is present. |
| OD-8 | "Clear scope" action | **LOCKED** — removes `exam_id` and `cycle_id` from search params. Does not navigate away from `/admin/exam-intelligence/cms`. |
| OD-9 | AdminSafetyBanner | **LOCKED** — `collapsible={false}`, no text change, no placement change. |
| OD-10 | Permission gate | **LOCKED** — `exam_intelligence.cms`, no change. |
| OD-11 | New routes or nav entries | **LOCKED** — none. J1 adds zero routes and zero sidebar/nav entries. |
| OD-12 | No new backend migrations | **LOCKED** — J1 is frontend-only (search/filter/pagination controls in `ExamIntelCms.jsx`). Backend list endpoints already accept `search`, `limit`, `offset`, and status filter params. |

---

## Section G — Acceptance tests

The following tests must pass before the J1 implementation PR may merge.

### G.1 Scope indicator tests

```
[ ] when exam_id is present in URL, scope indicator renders with the exam's name
[ ] when cycle_id is also present, scope indicator includes the cycle's name
[ ] when neither param is present, scope indicator is not rendered
[ ] "Clear scope" removes exam_id and cycle_id from the URL (search params)
[ ] after clearing scope, the entity list reloads with the global (unscoped) list
```

### G.2 Search input tests

```
[ ] search input is rendered for scoped entities when exam_id is present
[ ] typing in search input sends a list request with search=<value> after debounce
[ ] search input clears when the entity selection changes
[ ] list reloads with the search param included alongside existing exam_id and status filter
[ ] page resets to 1 when search value changes
```

### G.3 Status filter tests

```
[ ] reviewer_status filter is rendered for: syllabus-topic-mentions, exam-topic-coverage, policy-updates
[ ] trust_status filter is rendered for: syllabus-documents, pyq-papers, pyq-sources
[ ] no status filter is rendered for entities without reviewer_status or trust_status
[ ] selecting a status value sends the correct param in the list request
[ ] selecting "(all statuses)" sends no status filter param
[ ] filter clears when entity changes
[ ] page resets to 1 when filter changes
```

### G.4 Pagination tests

```
[ ] entity table shows at most 50 rows per page
[ ] "Next" button is enabled when total_count > current_offset + 50
[ ] "Next" button is disabled on the last page
[ ] "Previous" button is disabled on page 1
[ ] "Previous" advances backward by 50 rows
[ ] page indicator shows correct range (e.g. "Showing 1–50 of 120")
[ ] page resets to 1 when entity, search, or filter changes
[ ] pagination works correctly under active scope (exam_id + cycle_id params included in all page requests)
```

### G.5 Invariant / regression tests

```
[ ] AdminSafetyBanner is visible and collapsible={false} (unchanged)
[ ] permission gate blocks users without exam_intelligence.cms (unchanged)
[ ] no new route appears in navContract.test.js
[ ] no sidebar/nav entry is added or removed
[ ] ENTITY_EXAM_SCOPE and ENTITY_CYCLE_SCOPE sets are unchanged
[ ] New row, Bulk import, and Reload controls still function
[ ] CRUD (create/edit/delete) still functions for all entity types
```

---

## Section H — Files to be changed

| File | Change | Layer |
|---|---|---|
| `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx` | Add scope indicator, search input, status filter, and pagination controls. Add scope name resolution (fetch exam/cycle name from context or lightweight endpoint when params are present). | Frontend |
| `app/frontend/src/pages/admin/studyos/__tests__/ExamIntelCms.scope.test.jsx` | New test file covering scope indicator, search, filter, and pagination (acceptance tests from Section G). | Frontend tests |
| `docs/status/career-copilot-checklist.md` | Update J1 row from "DEFERRED — READY TO PLAN" to "DRAFT CONTRACT — OPERATOR APPROVAL PENDING" (this PR). After operator approval: update to "APPROVED — IMPLEMENTATION AUTHORIZED". | Docs |

**Files that must NOT be changed by the J1 implementation PR:**

- `app/frontend/src/pages/admin/AdminShell.jsx` — no nav changes
- `app/frontend/src/routes/adminRoutes.jsx` — no route changes
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx` — no workspace changes
- Any backend file in `app/backend/` — no backend changes
- Any database migration file — no migrations

---

## Appendix A — Code evidence index

The following files were read to verify the decisions in this document:

- `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx` — confirmed `ENTITY_EXAM_SCOPE`, `ENTITY_CYCLE_SCOPE`, `useSearchParams` wiring for `exam_id`/`cycle_id`, `ENTITY_CONFIG` entity list, `AdminSafetyBanner` presence, `PERM_CMS` guard, `renderCellValue` UUID truncation
- `app/backend/app/api/admin_exam_intel_cms.py` lines 1–100 — confirmed `PERM_CMS = "exam_intelligence.cms"` (line 55), router prefix `/admin/exam-intelligence-cms`, `ADMIN_STUDY_OS_ENABLED` flag gate
- `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §9 — confirmed Advanced Repair access model, entry path, permission gate token, `AdminSafetyBanner` requirement, no-nav-entry constraint
- `docs/status/career-copilot-checklist.md` — confirmed J1 row status, I8-C and I6 gates cleared

---

*This document is a planning artifact. No runtime files were changed in the PR that introduced it. The gate is DRAFT — AWAITING OPERATOR APPROVAL. No J1 implementation PR may be dispatched until the operator approves this document.*
