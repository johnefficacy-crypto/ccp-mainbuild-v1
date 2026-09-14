# STUDIO-01 — where an authoring tool could live without adding a surface

Read-only investigation. No code, migration, route or document changed outside
this file. Line numbers are against `main @ c6962d6a`.

The brief asks what exists, not where a studio should go. Nothing below is a
recommendation.

---

## 1. Top-level nav surfaces, as the router and shells define them

Two distinct things are easy to conflate: **routes** (what `adminRoutes.jsx` /
`appRoutes.jsx` declare) and **nav surfaces** (what a sidebar renders as a
visible destination). The IA lock counts the second — §1.3's exit test is
written in terms of `visible_exam_nav_entries`, not route count. Both are
enumerated here.

### 1.1 Admin — visible sidebar entries

Source: `app/frontend/src/pages/admin/AdminShell.jsx`, `SECTIONS` at `:94`.
Seven groups; the Knowledge Governance group carries a landing plus four lanes.

| Group (`id`) | Entries | Paths |
|---|---:|---|
| `command-center` (`:20-23`) | 2 | `/admin`, `/admin/operations` |
| `trust-pipeline` (`:25-31`) | 5 | `/admin/sources`, `/admin/scraper`, `/admin/recruitments`, `/admin/eligibility-ops`, `/admin/audit` |
| `knowledge-governance` (`:33-54`) | 8 | landing `/admin/knowledge-governance`; lane 1 `/admin/exam-intelligence`; lane 2 `/admin/exam-eligibility`; lane 3 `/admin/organizations`, `/admin/verification-reports`, `/admin/reverification-batches`; lane 4 `/admin/ai-policy`, `/admin/persona` (7 lane items + landing) |
| `community-marketplace` (`:57-65`) | 7 | `/admin/community`, `/admin/community/groups`, `/admin/community/partners`, `/admin/community/resources`, `/admin/mentors`, `/admin/marketplace`, `/admin/plans` |
| `study-os` (`:67-75`) | 7 | `/admin/study-os`, `…/plan-ops`, `…/artifacts`, `…/mocks`, `…/reports`, `…/social`, `…/content-access` |
| `content-studio` (`:80-82`) | 1 | `/admin/content-studio` |
| `safety` (`:84-91`) | 6 | `/admin/moderation`, `/admin/copyright`, `/admin/notifications`, `/admin/rbac`, `/admin/kpis`, `/admin/blogs` |

**Admin visible nav entries: 36** across seven groups
(2 + 5 + 8 + 7 + 7 + 1 + 6). `grep -c 'to: "/admin'` on AdminShell returns 36,
which matches: `KG_LANDING` is declared once at `:33` and reused by reference
inside `SECTIONS`, so it is counted once, not twice.

Two entries are rendered but **absent from the nav-contract list** in
`routes/navContract.test.js:104-145`: `/admin/verification-reports` and
`/admin/reverification-batches` (AdminShell `:43-44`). The contract list is
hand-maintained (`navContract.test.js:9-12` says so), so it is not a reliable
count — it tests that nav paths resolve to routes, not that all nav paths are
listed.

**Exam-operation peer count (what §1.3's exit test measures): 1** —
`/admin/exam-intelligence` "Exam Management" (`AdminShell.jsx:36`). No console
peer, no workspace peer, no CMS nav entry. `/admin/exam-intelligence/console`
now redirects to the front door (`adminRoutes.jsx:103`) and the CMS route
(`:105`) has no sidebar entry. The post-I8 target in §1.3 holds.

### 1.2 Admin routes (not surfaces)

`adminRoutes.jsx` declares **57** `path=` entries, of which 8 are `<Navigate>`
redirects or redirect components (`:81`, `:82`, `:103`, `:104`, `:108`, `:110`,
`:111`, `:124`, plus the three `MockContentRedirect` mounts at `:132`, `:135`,
`:136`). Exam-intelligence routes: `:102-111`. Drill-in routes with no nav entry
include `/admin/exam-intelligence/exams/:exam_id` (`:107`),
`/admin/exam-intelligence/cms` (`:105`), `/admin/exam-intelligence/new`
(`:106`), `/admin/mocks/questions/:id` (`:134`).

### 1.3 Aspirant — visible sidebar entries

Source: `app/frontend/src/pages/DashShell.jsx`, `SECTIONS` (`:20-83`).

| Group | Entries | Paths |
|---|---:|---|
| (first) | 2 | `/app/today`, `/app/eligibility` |
| Study | 9 | `/app/exam-intelligence`, `/app/study`, `/app/study/subjects`, `/app/study/resources`, `/app/notes`, `/app/flashcards`, `/app/study/revision`, `/app/study/mocks`, `/app/study/mistakes` |
| Progress | 3 | `/app/study/review`, `/app/study/compare`, `/app/reports` |
| Community | 5 | `/app/community`, `/app/groups`, `/app/partners`, `/app/mentors`, `/app/resources` |
| More | 5 | `/app/marketplace`, `/app/ai`, `/app/notifications`, `/app/pricing`, `/app/saved` |

**Aspirant visible nav entries: 24.** Everything under `/app/study/*` that is
not in this list — `plan`, `learning`, `progress`, `improvement-lab`, `essay`,
`focus`, `mock attempts` — is reached inside `StudyShell`
(`appRoutes.jsx:95-131`), i.e. drill-in, not a surface.

**The number the lock constrains: 36 admin, 24 aspirant.** Adding one
destination to either requires removing two from the same nav.

---

## 2. Tab and drawer patterns inside the EI admin surface

### 2.1 Manage Exam — a 7-tab strip, URL-driven

`pages/admin/exam-workspace/ExamWorkspace.jsx`.

- Registry: `TAB_ORDER` (`:40-48`) — `setup`, `documents`, `syllabus`, `pyq`,
  `updates`, `competition`, `review`. Each entry carries `kind`
  (`open` | `readiness` | `terminal`) and, for readiness tabs, the
  `section` key it reads blockers from (`sectionByKey`, `:50`).
- Rendering: `TabStrip` (`:335-…`) maps `TAB_ORDER`; a tab shows a blocker
  count when its readiness section has `blockers.length > 0` (`:344`).
- State: **the URL is the single source of tab state** (`:427-430`) —
  `?tab=` validated against `TAB_ORDER`, defaulting to `setup`. Sibling params
  `action`, `status`, `document`, `paper`, `row` (`:432-436`) carry deep-link
  destination. `gotoTab` (`:438`) rewrites the query string, never the path.
- **Adding a tab is contained**: one entry in `TAB_ORDER` plus a panel render
  branch. No route, no nav entry, no `AdminShell` change. The IA lock names
  this shape explicitly (`§2.2`, `?cycle=…&tab=…`, "Same component,
  query-param driven").

### 2.2 Content Studio — a 4-tab strip crossed with a content-type facet

`pages/admin/content-studio/ContentStudio.jsx`.

- Registry: `TABS` (`:39-44`) — `library`, `review-queue`, `bulk-import`,
  `exam-assignments`; and `CONTENT_TYPES` (`:46-52`) — `objective_question`,
  `writing_prompt`, `quant_heuristic`, `reasoning_strategy`,
  `current_affairs_question`.
- State: `?tab=` and `?type=` (`:59-61`), both validated against their lists.
- **Tabs are permission-gated per type** (`:85-96`): a `content_studio.author`
  without `review` sees `library` + `review-queue`; a reviewer without author
  sees `review-queue` only; some types drop `exam-assignments`. The active tab
  is then re-resolved against the *typed* list (`:97-99`), so a gated-away tab
  cannot be reached by typing the URL.
- Panels are `lazy()` imports (`:26-37`), so a tab costs nothing until opened.
- **Adding a tab or a content type is contained**: one array entry plus a lazy
  import. This is the pattern the IA lock's applied note (`§1.2`,
  2026-07-02) authorised when Content Studio absorbed three Mock Content
  destinations.

### 2.3 Drawers and overflow

- **Advanced Repair overflow**: `AdvancedRepairMenu` (`ExamWorkspace.jsx:59-…`)
  — a `role="menu"` popover inside Manage Exam that links to the CMS route with
  `exam_id`/`cycle_id` carried. This is the "overflow/More action" the lock
  classifies as *not* a surface (`§1.2`).
- **Shared drawer primitive**: `shared/ui/studyos` exports `Drawer`, used by the
  aspirant surfaces; admin pages mostly use inline panels and modals
  (`AcceptPreviewModal.jsx` in the syllabus mapper).

---

## 3. The EI CMS after its demotion to a fallback drawer

`pages/admin/studyos/ExamIntelCms.jsx`, 2,326 lines. Route
`/admin/exam-intelligence/cms` (`adminRoutes.jsx:105`), **no nav entry**;
reached from the Advanced Repair overflow, and from the legacy redirect
`/admin/study-os/exam-intel-cms` (`:124`).

### What it still does

A generic table-and-form over 16 entities. `ENTITY_CONFIG` (`:268-593`) declares
each entity's columns and field types; `ENTITY_KEYS` (`:594`) is its key list:

```
exam-families, exam-cycles, exam-phases, syllabus-documents, pyq-papers,
exam-topic-coverage, policy-updates, topic-aliases, topic-prerequisites,
syllabus-topic-mentions, pyq-sources, pyq-question-topic-tags, pyq-questions,
pyq-options, exam-phase-sections, exam-competition-metrics
```

Per entity it offers: list with filters, create, bulk import (paste or file),
bulk edit, bulk retire, and — for a subset — edit and soft-delete.

- `EDITABLE_ENTITIES` (`:599-606`): `exam-families`, `exams`, `exam-cycles`,
  `exam-phases`, `subjects`, `topics`, `pyq-sources`. The comment at `:595-598`
  states the rule: everything else is create-only because "lifecycle rows go
  through the review queue, not here".
- `DEACTIVATABLE_ENTITIES` (`:607`): `exam-families`, `exams` only.

### What it authors vs. what it edits

It **authors identity and structure** — families, exams, cycles, phases,
sections, subjects, topics, aliases, prerequisites — and **edits intelligence
rows** (coverage, mentions, PYQ questions/options/tags, competition metrics)
through the same generic form. It has no notion of content: no rich text, no
preview, no per-field domain validation beyond types.

### Is any of it a reusable editor?

**Not as it stands.** The editing surface is a field loop over
`ENTITY_CONFIG[entity].fields`, with:

- `required` flags declared per field (`:272`, `:282`, `:298-300`, …) and
  enforced inline;
- `NULLABLE_ON_EDIT` (`:615-…`) — a per-entity allow-list of columns that may
  legitimately be cleared to null, derived from `docs/schema/supabase-current.md`;
  anything else cleared is blocked;
- `BULK_EDIT_EXCLUDED_FIELDS` / `bulkEditableFields` (`:651-680`) — mirrors
  the backend's exclusion set so the picker never offers a field
  `/bulk-update` would reject, with a comment (`:660-663`) explaining that
  bulk update is a generic direct UPDATE that skips FK/scope validation;
- `CmsRefField` (`features/admin/shared/CmsRefField.jsx`, 62 lines) — the one
  genuinely reusable piece: a typeahead that resolves a FK to an existing row.

The validation is **entity-table validation, not content validation**, and it is
expressed as data (`ENTITY_CONFIG`) rather than as a component API. `CmsRefField`
and `lib/bulkImportFile.js` (167 lines, paste/CSV/JSON parsing) are reusable;
the form itself is not a component anyone else can mount.

---

## 4. Existing editor components with validation

| Editor | Path | What it validates | Where the validation lives | Reusable? |
|---|---|---|---|---|
| **Writing-prompt editor** | `pages/admin/content-studio/PromptEditor.jsx` | Required-word tokens, prompt content, word counts | `content-studio/validation.js` — deliberate **backend parity**: it reuses `tokenizeWords` from `features/study/english-practice/requiredWords` so `foo!`, `a.b`, `under_score` fail identically to `_canonicalize_required_words` / `ewp_assert_prompt_content` (migration 215) | **Yes** — pure module, no React, already shared between the editor and bulk import |
| **Prompt bulk import** | `content-studio/PromptBulkImport.jsx` + `content-studio/csv.js` (79 lines) | CSV shape, then the same `validation.js` rules per row | Same module | Yes |
| **CMS create / edit / bulk** | `studyos/ExamIntelCms.jsx` | `required`, type coercion, nullable-on-edit allow-list, bulk-field exclusions, reason ≥ 8 chars | Inline, driven by `ENTITY_CONFIG` data | **No** as a component; `CmsRefField` and `lib/bulkImportFile.js` are |
| **Syllabus topic editor** | `exam-workspace/syllabus-mapper/SyllabusTopicEditorPanel.jsx` (336 lines) | Subject resolution (`subjectState: idle\|resolving\|valid\|error`, `:33`), **fail-closed on a failed topic fetch** (`:51`), reason ≥ 8 chars (`:118-119`) | Inline in the panel | Partially — the fail-closed subject resolver is the pattern, not a module |
| **Topic prerequisite editor** | `syllabus-mapper/TopicPrerequisiteEditor.jsx` | Edge shape + relation type | Inline | No |
| **Syllabus mapper proposal flow** | `syllabus-mapper/ProposalRunner.jsx`, `AcceptPreviewModal.jsx`, `proposalKey.js` (19 lines) | Proposal identity hash, cross-side parity with the backend | `proposalKey.js` — the hash both sides compute (AGENTS.md "Patterns and Lessons" §3 cites this as the hash-parity precedent) | Yes, as a hash helper |
| **Mock question editor** | `pages/admin/mocks/…` mounted at `/admin/mocks/questions/:id` (`adminRoutes.jsx:133-134`) | Question/option shape | Inline | Not examined further — out of the EI surface |

The single strongest reusable asset is `content-studio/validation.js` +
`csv.js`: one validator, two consumers (editor and bulk import), written
explicitly to mirror the server so inline errors match what the API will accept.

---

## 5. Review-queue precedent — one role drafts, another approves

**Yes, and it is the dominant pattern in Content Studio.** Two separate state
machines exist.

### 5.1 Content review lifecycle

`content-studio/contentStudioApi.js:155-163`:

```js
REVIEWER_STATUSES = ["pending", "verified", "rejected", "needs_correction"]

REVIEW_TRANSITIONS = {
  pending:          ["verified", "rejected", "needs_correction"],
  needs_correction: ["verified", "rejected", "pending"],
  verified:         ["rejected", "needs_correction"],
  rejected:         [],            // terminal
}
```

Current-affairs questions run a second, narrower machine
(`CA_REVIEW_TRANSITIONS`, `:137-141`): `review_ready ↔ approved`,
`review_ready ↔ rejected`, `rejected → review_ready`.

Mechanics, from `PromptReviewQueue.jsx`:

- the queue offers only the transitions legal for the row's current status
  (`:68`, `:94`, `:291`);
- every transition sends `expected_status` — the status the client last saw —
  as a **compare-and-set** (`:108`, backend `content_studio.py:293`,
  `:1022`), so a second reviewer acting on a stale list is rejected rather than
  silently overwriting;
- `isValidReason` (`contentStudioApi.js:165`) requires 8–500 characters;
- `needs_correction` carries `reviewer_notes` back to the author
  (`content_studio.py:968`, `:982`).

### 5.2 Assignment authority split (§J2)

`content_studio.py:73`, `:319`, `:334`, `:734`, `:760`:

- `exam_intelligence.manage` may **propose** an assignment, which lands
  **inert** in `pending_review`;
- `exam_intelligence.review` may **promote** it to `active | excluded`.

Proposing and approving are different permissions on the same row. That is the
closest existing precedent to a draft/approve authoring flow.

### 5.3 Activation as a third authority

`content-studio/permissions.js:26-29`: neither author nor reviewer may flip
`is_active` — that needs `content_studio.activate` (EWP-SP2), and the server RPC
(migration 226) is the sole eligibility authority; the UI only renders the RPC's
`{eligible, blockers}` verdict (`ContentStudio.jsx:15-19`).

The EI side has its own coverage lifecycle —
`draft | pending_review | reviewed | locked | rejected` (AGENTS.md
"Patterns and Lessons" §11) — with `locked` as the only learner-visible state.

---

## 6. Permission model, and where the route/endpoint mismatch sits

### 6.1 Tokens

| Token | Declared | Gates |
|---|---|---|
| `exam_intelligence.cms` | `admin_exam_intel_cms.py:56` (`PERM_CMS`) | **Every** endpoint in the CMS router (`:192`, `:213`, `:239`, …), and the Advanced Repair page's own check |
| `exam_intelligence.manage` | `core/permissions.py:103` | Coverage derivation (`admin_exam_intelligence.py:3199`), assignment *proposal* (`content_studio.py:734`) |
| `exam_intelligence.review` | `core/permissions.py:124` | Assignment *promotion* (`content_studio.py:760`) |
| `content_studio.author` / `.review` / `.activate` | `content-studio/permissions.js:11-30` | Studio tabs and actions; backend authoritative |
| `mock_questions:publish` | `content-studio/permissions.js:32` | Promoting a CA candidate into the objective bank |

EI authoring today is gated by **`exam_intelligence.cms`** — it is the only
permission that admits writes to families, exams, cycles, phases, sections,
subjects, topics and the intelligence tables.

### 6.2 The mismatch

Three layers, gated differently:

1. **Route**: `/admin/exam-intelligence/cms` sits inside
   `<ProtectedRoute role={ADMIN_ROLES} requireBackend>` (`adminRoutes.jsx:73`),
   which checks a **role**, not a permission. Any `admin` reaches the route.
2. **Component**: `ExamIntelCms.jsx:861-864` then self-gates on
   `super_admin || permissions.includes("exam_intelligence.cms")`, rendering
   "Advanced Repair requires the `exam_intelligence.cms` permission." (`:1598`)
   after a "Checking permissions…" state (`:1591`).
3. **Endpoint**: `require_permission(PERM_CMS)` on every CMS route.

So the page is role-gated and the actions are permission-gated. The **known,
documented** instance of this is on a neighbouring surface, recorded as P1 in
`docs/reviews/knowledge-governance-ux-review.md:17` and `:122`: Verification
Reports requires `admin`/`super_admin` in the frontend while
`apply-registry-action` requires `exam_intelligence.cms`
(`VerificationReports.jsx:1071-1088`,
`admin_verification_reports.py:847-852`) — "page-level role check hides/permits
the whole page, but apply-registry-action has a separate permission… Operators
can be surprised by action-level 403."

`ExamIntelCms.jsx` has the same shape but closes it in-component; Verification
Reports does not.

---

## 7. The IA lock, quoted

`docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md`.

### 7.1 The surface-count rule (§1.2, `:36-38`)

> ### 1.2 No-new-surface rule (LOCKED — absolute)
>
> **No new top-level destination unless it removes at least two existing top-level destinations.**

With the applied precedent (`:40-47`):

> **Applied 2026-07-02 — Content Studio consolidation.** A new **Content Studio**
> admin destination is authorized under this rule because it **removes 3**
> existing top-level Mock Content destinations (`/admin/mocks/questions`,
> `/admin/mocks/review-queue`, `/admin/mocks/import`) and **adds 1** (net −2).
> Canonical content (incl. writing prompts) is authored there, not in
> Exam Workspace. The nav/routing consolidation is a later serial-delivery PR.

What counts as a surface (`:49-56`):

> The following are classified as surfaces and are therefore prohibited from being added:
>
> - a separate portfolio dashboard
> - a separate coverage matrix page or lane
> - a second exam console
> - a second workspace variant
> - a new visible global CMS peer
> - an exam-management lane inside Knowledge Governance (removed by I7; must not re-appear)

What does not (`:58-64`):

> The following are NOT surfaces and may be added freely:
>
> - backend endpoints (headless)
> - embedded components inside an existing page
> - drill-in pages reached by navigating within a page
> - overflow/More actions
> - permission-gated recovery tools with no nav entry

### 7.2 The exit test (§1.3, `:88-98`)

> ```
> visible_exam_nav_entries == 1
> manage_exam_is_drill_in == true
> advanced_repair_is_overflow_only == true
> no_exam_lane_in_kg == true  (enforced by I7, must not regress)
> console_peer_visible == false
> workspace_peer_visible == false
> cms_nav_visible == false
> ```

### 7.3 The tab-gating model (§2.2, `:131-137`)

> | `/admin/exam-intelligence/exams/:exam_id?cycle=:cycle_id&tab=:tab` | Manage Exam with selected exam/cycle/task state | Same component, query-param driven |
>
> - Tab state and cycle selection are stored in URL query parameters (`?cycle=...&tab=...`) so the URL is bookmarkable and back-navigable.

And the front door's own constraint (§5, `:188`):

> Post-I8-A locked role: **Exam Management front door — single-view (no tabs).**
> The front door is locked as a single view: no Overview vs Exams tab
> competition.

Plus the tab-competition rationale that removed the Overview tab (§6.2, `:426`,
`:436`):

> **LOCKED: the Overview tab is removed as a standalone competing tab.**
>
> The workspace then opens directly to the action queue / first blocker view,
> not to an Overview tab. This removes the tab-competition problem that makes
> Manage Exam feel like a reporting surface before it is a workflow surface.

There is no general "tab-gating model" beyond these: tabs are permitted inside a
drill-in (Manage Exam, Content Studio), forbidden on the Exam Management front
door, and tab state belongs in the query string.

---

## Observed while reading — stated, not chased

- `routes/navContract.test.js:104-145` omits `/admin/verification-reports` and
  `/admin/reverification-batches`, both rendered by `AdminShell.jsx:43-44`. The
  test only asserts that listed nav paths resolve to routes, so the omission
  does not fail anything — but the list cannot be used as a surface census.
- `ContentStudio.jsx` declares five content types (`:46-52`) against four tabs
  (`:39-44`), and `:85-96` drops `exam-assignments` for some types. The tab set
  is therefore type-dependent, which the IA lock does not describe either way.
- `pages/admin/ExamGovernanceConsole.jsx` still exists as a component while its
  route redirects to the front door (`adminRoutes.jsx:103`). Dead as a
  destination, live as a file.
