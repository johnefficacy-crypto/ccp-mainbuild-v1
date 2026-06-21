# Exam Management IA — Findings, Locked Decisions, and Execution Gates

**Project:** `ccp-mainbuild-v1`  
**Date:** 2026-06-21  
**Scope:** Complete decision record beginning with the DQ-1 / DQ-2 / I6-gate analysis and ending with the decision to move routine CMS capabilities into contextual blocker-resolution workflows.  
**Purpose:** Freeze the findings, decisions, evidence, dependencies, and unresolved gates before implementation begins.  
**Repository changes:** None. This document is a planning artifact only.

---

## 1. Status vocabulary used in this document

- **VERIFIED** — confirmed against the current repository code.
- **LOCKED** — product/architecture decision accepted in the discussion.
- **GATED** — direction is accepted, but implementation cannot start until a named contract or design lock is completed.
- **DEFERRED** — valid issue, intentionally outside the immediate execution arc.
- **CODE-FIXED, VALIDATION PENDING** — code is present, but redeploy/operator proof is still required.
- **OPEN BUG** — current implementation is incorrect or fails at runtime.
- **SUPERSEDED** — an earlier recommendation was replaced by a later decision.

---

# 2. Executive summary

The core problem is not that Exam Intelligence lacks screens. It has too many peer screens for overlapping work:

1. Knowledge Governance exam lane
2. Exam Registry
3. Exam Governance Console
4. Exam Workspace
5. Advanced Import / Repair CMS

The operator is forced to decide which product surface owns the task before doing the task. The screenshots repeatedly show the resulting questions:

- Where do I begin?
- Is Console different from Workspace?
- Is Knowledge Governance different from Registry?
- Should normal work happen in Advanced Import / Repair?
- Where do cycles, phases, PYQs, syllabus mappings, updates, and competition data belong?
- Which surface is authoritative?

The locked target mental model is:

> **Find the exam → manage the exam → use Advanced Repair only when the normal workflow cannot resolve the problem.**

The target visible hierarchy is:

```text
Admin
└── Exam Management
    ├── Find and triage exams
    │   └── family → exam → cycle → phase
    │
    └── Manage Exam
        ├── blocker / next action
        ├── cycle readiness
        ├── Setup
        ├── Documents
        ├── Syllabus
        ├── PYQs
        ├── Updates
        ├── Competition
        ├── Review & activate
        └── More → Advanced repair
```

The portfolio tree and coverage matrix are **not new surfaces**. They are the content of Exam Management and Manage Exam.

The standing IA rule is:

> **No new top-level destination unless it removes at least two existing top-level destinations.**

The implementation test is not “did the cards look cleaner?” It is:

> **Did the visible surface count go down, and can normal work be completed without opening Advanced Repair?**

---

# 3. Starting distinction: the three blocked gates were different kinds of decisions

The discussion began by separating three gates that had been grouped together incorrectly:

- **DQ-1 / I7** was a page-purpose decision.
- **DQ-2 / I8** was another page-purpose / information-architecture decision.
- **I6-gate / I9** was a workflow-architecture decision.

They therefore required different answers and different implementation readiness.

---

# 4. DQ-1 → I7: Knowledge Governance exam lane

## 4.1 Verified current state

`KnowledgeGovernance.jsx` contains an “Exam truth & planner readiness” lane that duplicates navigation to exam-related destinations.

The lane has no meaningful operational metric ownership. It behaves as a directory.

The Console already owns cross-exam triage and already exposes aggregates for:

- blocked
- needs action
- ready
- workflow flags
- total count

`ConsoleWorkQueue` already renders those values as actionable filters.

## 4.2 Initial options considered

### Option A — keep the KG exam lane and add metrics

Potential metrics included:

- exams blocked from activation
- exams missing cycles or phases
- extraction failures
- pending syllabus mentions
- pending PYQ review
- stale cycles

This was technically feasible because the Console already computes cross-exam classification.

### Option B — remove the lane

The stronger product argument was that copying Console aggregates into KG would still create a second triage surface.

A KG card saying “12 exams blocked” and linking to the Console adds no new operator capability. It duplicates the Console’s job.

## 4.3 Locked decision

**LOCKED: remove the exam lane from the Knowledge Governance landing page.**

Reason:

- Console already owns triage.
- Registry / Exam Management should own discovery.
- Manage Exam should own operational work.
- KG adds another path without adding unique capability.

## 4.4 Scope correction

The original proposal to remove both the KG landing card and the sidebar exam group immediately was corrected.

The current sidebar exam group contains every direct exam entry:

- Exam Governance Console
- Exam Registry
- Create exam
- Advanced Import / Repair

Removing the sidebar group before a replacement Exam Management entry exists would make exam operations harder to discover.

Therefore:

### I7 immediate scope

- Remove the exam lane/card from `KnowledgeGovernance.jsx`.
- Update landing-page count/copy from four lanes to three.
- Update the direct landing-page tests.
- Do not rename Knowledge Governance.
- Do not remove the sidebar exam group yet.
- Do not change backend metrics.
- Do not touch routing.

### Sidebar removal timing

The old sidebar exam group must be removed **atomically in I8-A**, at the same time the new single Exam Management entry is added.

## 4.5 KG rename

Renaming “Knowledge Governance” to “Policy & Trust” or “Rules & Trust” was considered useful because “Knowledge Governance” naturally overlaps with Exam Intelligence.

**Decision: deferred and separated.**

It must not be folded into I7 because it touches:

- sidebar group labels
- masthead/page titles
- breadcrumbs or title resolution
- tests
- potentially documentation

It also collides with I8-A’s navigation edits.

---

# 5. DQ-2 → I8: the primary operator goal

## 5.1 Initial locked goal

The initial decision was:

> **Find an exam and open its operational workspace.**

That matched the existing Registry title, filters, and table better than the competing goals of:

- triage
- portfolio statistics
- exam creation
- raw repair

The original registry-first recommendation was:

- default to the exam list
- remove Overview/Exams tab competition
- demote Console/Create/Repair
- make `Open workspace` the dominant row action

## 5.2 Correction from the screenshots

The screenshots showed that the desired Registry was not merely a flat table.

The operator sketched:

```text
Exam family
└── Exam
    └── Cycle
        └── Phase + dates + status
```

and a coverage view such as:

```text
Exam
└── Cycle × {
      PYQ,
      PYQ analysis,
      mocks,
      syllabus/topic linkage,
      updates,
      readiness
    }
```

The current flat Registry contract does not provide:

- family hierarchy
- cycles
- phases
- phase dates
- cycle-specific paper readiness
- cycle-specific mock readiness
- cycle-specific update readiness

## 5.3 Structural escalation

The later discussion concluded that “Registry versus Console versus Workspace” should not remain a visible product choice.

The correct front-door goal became:

> **One Exam Management page for locating, filtering, triaging, and entering an exam.**

The previous narrow I8 plan that retained Console as a secondary visible destination was **SUPERSEDED**.

## 5.4 Locked end state

**LOCKED: one visible Exam Management front door.**

It combines the purposes currently split between Registry and Console:

- search and discovery
- blocked / needs-action / ready filters
- business filters
- family/exam/cycle context
- first blocker / next action
- one row/drill-in action: `Manage exam`

The visible words “Console” and “Workspace” should not be peer product choices.

Internal filenames and backend route names may remain temporarily during migration, but they should not remain operator-facing destinations.

---

# 6. I6-gate → I9: guided cycle setup

## 6.1 Problem

Complete cycle setup is not a single synchronous form. It spans:

1. create/select cycle
2. define phases and dates
3. upload documents
4. complete extraction
5. map/review syllabus mentions
6. import/review PYQs
7. review updates
8. add competition context
9. resolve readiness and activate

Some steps:

- are asynchronous
- involve extraction jobs
- require human review
- may happen in parallel
- may span multiple sessions

A single full-screen wizard is therefore a poor fit.

## 6.2 Locked architecture

**LOCKED: hybrid architecture.**

### Mini-wizard responsibility

Use a bounded flow only for atomic creation:

1. cycle identity and dates
2. phase selection/creation
3. review and save

After save, return to Manage Exam with the new cycle selected.

### Persistent checklist responsibility

Use a resumable checklist for activation readiness:

1. Cycle details
2. Phases and schedule
3. Source documents
4. Extraction
5. Syllabus mapping
6. PYQ readiness
7. Policy updates
8. Competition context
9. Review and activate

## 6.3 Dependency order

```text
Cycle + phases
      ↓
Documents → extraction → syllabus mapping
      ↓
PYQ review ───────────────┐
Policy updates ───────────┼→ Review and activate
Competition metrics ──────┘
```

Not every step must be strictly sequential:

- setup must precede the rest
- extraction must precede mapping
- PYQ, policy, and competition work can proceed independently after a cycle exists
- activation remains terminal

## 6.4 I9 remains gated

The architecture decision does not close the implementation contract.

The gate document still must define, for all nine steps:

- completion source
- hard gate or advisory
- deep-link target
- resume behaviour
- empty-state behaviour
- selected cycle behaviour
- applicability for core/light/index-only/archive exams
- applicability for annual/irregular/one-off exams
- whether a step may be not applicable
- whether `AddCycleWizard` is reused, embedded, or removed
- whether progress is backend-derived or frontend-composed
- whether any manual “mark complete” state is allowed

**LOCKED: do not dispatch I9 implementation until this gate document is approved.**

---

# 7. What the UI screenshots established

The screenshots were treated as evidence of an operator-model mismatch, not merely visual-polish defects.

## 7.1 Strong product signal

The operator wants:

- a portfolio tree
- cycle and phase visibility
- dates and status
- year-by-year content readiness
- one place to understand what exists and what is missing

That is the content the consolidated pages must render.

## 7.2 Screenshot items already fixed by merged PRs

Several screenshots became stale after PRs #742 and #744.

Code-fixed, validation pending items include:

- UUID/token hiding in audited locations
- PYQ paper overview table
- bulk import selecting/opening the imported paper
- removal of redundant exam identity fields
- removal of duplicate readiness summary
- extraction of `PhaseTimeline`
- inline missing-date badges
- cycle labels on missing-date phases
- removal of the duplicate “Phases needing dates” section
- collapsible guidance / reduced duplicate lifecycle content

These should be re-screenshot after redeploy before being logged as new defects.

## 7.3 H1 syllabus proposal 404

The reported wrong-table 404 was code-fixed by switching the proposer to `syllabus_documents`.

However, end-to-end validation must prove more than “the endpoint no longer returns 404.”

Potential linkage risk remains:

- extraction pages are associated with the uploaded `document_asset.id`
- linking creates a separate `syllabus_documents` row
- proposer page lookup must resolve the correct linked extraction pages

Required validation:

1. upload a real document
2. complete extraction
3. link it to syllabus
4. run proposal
5. confirm non-empty page retrieval
6. confirm proposal output

Status: **CODE-FIXED, VALIDATION PENDING.**

## 7.4 H2 document readiness

H2 remains the live correctness priority.

Current defects:

- `console_detail.py` treats `syllabus_documents.trust_status == verified` as an extraction proxy
- `readiness.py` queries nonexistent `document_assets.exam_id`, `exam_cycle_id`, and `extraction_status`
- trust state is human provenance/review, not extraction completion

Canonical extraction evidence is:

```text
document_processing_jobs
where job_type = 'text_extract'
and latest status determines succeeded / pending / failed / needs_review / not_started
```

The correct implementation requires:

- `document_assets` ownership from metadata
- exam/cycle filtering from metadata
- batched `document_processing_jobs` loading
- latest job per asset
- no trust-status proxy
- shared logic between Console detail and workspace readiness

No matching open H2 PR was found during the review.

Status: **OPEN BUG / P0 / ready to dispatch.**

---

# 8. The five-peer-surface diagnosis

## 8.1 Root problem

The UI currently presents the following as peers:

- Knowledge Governance
- Exam Registry
- Exam Governance Console
- Exam Workspace
- Advanced Import / Repair

This is the central IA defect.

The user should not need to understand internal technical ownership before performing ordinary exam-management work.

## 8.2 Locked mental model

```text
Find exam
   ↓
Manage exam
   ↓
Advanced repair only when the normal workflow fails
```

## 8.3 Surface-count exit test

Starting visible peer count:

1. KG exam lane
2. Registry
3. Console
4. Workspace
5. CMS

Required final structure:

1. Exam Management front door

with:

- Manage Exam as a drill-in, not a peer
- Advanced Repair as overflow, not a peer
- no exam-operations lane inside KG
- no standalone portfolio dashboard
- no standalone coverage-matrix destination

Any implementation that introduces another dashboard, console, workspace, or matrix page fails the IA objective.

---

# 9. No-new-surface rule

## 9.1 Locked rule

> **No new top-level destination unless it removes at least two existing top-level destinations.**

Interpretation:

- a backend endpoint is not a surface
- an embedded component is not a surface
- a drill-in page is not a peer destination
- a hidden compatibility route is not a visible surface
- an overflow action is not a peer destination
- a new sidebar item is a surface
- a new top-level route promoted in navigation is a surface

## 9.2 KG as the cautionary example

KG attempted to organize governance work by adding another page.

It did not eliminate existing ownership ambiguity. It became another path to the same work.

Therefore, new capability must land inside the canonical hierarchy instead of creating another organizational page.

---

# 10. Portfolio tree and readiness matrix

## 10.1 Earlier “I10 lane” recommendation

A separate “portfolio/coverage matrix” lane or screen was initially proposed.

That recommendation was rejected because it would repeat the KG mistake:

- new route
- new peer
- new “where does this live?” question

## 10.2 Locked correction

**LOCKED: I10 does not exist as a visible product lane.**

The useful capability is folded into I8:

### Exam Management content

The front door should render:

```text
family → exam → cycle → phase
```

with:

- phase status
- key dates
- current/active cycle
- first blocker
- readiness summary
- management mode/cadence where useful

### Manage Exam content

Inside a selected exam, show per-cycle readiness such as:

- PYQ
- PYQ analysis
- mocks
- documents/extraction
- syllabus mapping
- topic coverage
- updates
- competition
- activation state

## 10.3 Backend requirement

A new headless read-model endpoint may be required.

It is not a new UI surface.

The contract should return:

- family
- exam
- cycles
- phases
- dates
- phase states
- per-cycle content readiness
- explicit status values

Recommended status vocabulary:

```text
missing
uploaded
extracting
review_pending
ready
stale
failed
not_applicable
```

The exact endpoint path and response schema are not yet locked.

## 10.4 Sequencing correction

The backend contract must land before or with the frontend that needs it.

A frontend matrix implementation is not parallel-safe with I8-A because both would likely edit the canonical Exam Management page.

Safe split:

- contract/audit section — parallel-safe
- backend read model — likely parallel-safe after contract approval
- frontend integration — after I8-A establishes page ownership

---

# 11. Registry, Console, and Workspace consolidation

## 11.1 Current route split

Current routes separately expose:

```text
/admin/exam-intelligence
/admin/exam-intelligence/console
/admin/exam-intelligence/console/:exam_id
/admin/exam-intelligence/workspace/:exam_id
/admin/exam-intelligence/workspace/:exam_id/:cycle_id
/admin/exam-intelligence/cms
/admin/exam-intelligence/new
/admin/exam-intelligence/pyq-papers/:paper_id/workspace
```

The code also documents intentional separation between Registry, Console, and Workspace.

Therefore consolidation is a structural refactor, not a text cleanup.

## 11.2 I8-A — Exam Management front door

Goal:

- one sidebar entry
- discovery plus triage in one page
- family/exam/cycle structure
- status filters
- one row/drill-in action: `Manage exam`

I8-A must atomically:

- add the new Exam Management sidebar entry
- remove the old KG sidebar exam group
- remove visible Registry/Console peer navigation
- preserve legacy route compatibility during transition

## 11.3 I8-B — Manage Exam

Goal:

- merge per-exam Console information into the normal exam-management drill-in
- show blocker, status, next action, and readiness in the selected exam context
- remove visible “Open console” versus “Advanced workspace” choice
- remove or repurpose the competing Overview tab

This is the largest redesign.

Current duplication exists because:

- `ExamActionConsole` consumes backend-owned `activation_verdict`, `action_queue`, checks, and stages
- `ExamWorkspace` independently displays readiness, blockers, score, current stage, and next action

The IA lock must choose one canonical readiness contract.

Open decision:

- Console detail/action queue as canonical
- workspace readiness sections as canonical
- or a unified read model replacing both

Do not merge components before this authority is locked.

## 11.4 I8-C — Advanced Repair isolation

Goal:

- remove CMS from normal navigation
- expose selected-exam `Advanced repair` from an overflow menu
- pre-scope it to the selected exam
- permission-gate it
- clearly warn that it is low-level repair

Global super-admin recovery may remain available, but it must not be presented as the normal workflow.

## 11.5 Redirect strategy

Redirects land last.

Correct migration order:

1. add canonical routes while old routes still work
2. change navigation and internal links
3. validate all entry points
4. convert old visible URLs to redirects
5. remove orphaned shells/components only after redirect tests pass

Do not create an intermediate state where links 404.

---

# 12. I8 blast radius and ownership

## 12.1 Why I8 is not a cleanup PR

The merge touches or influences:

- `AdminShell.jsx`
- `adminRoutes.jsx`
- `ExamIntelligence.jsx`
- `ExamGovernanceConsole.jsx`
- `ConsoleWorkQueue.jsx`
- `ExamActionConsole.jsx`
- `ExamWorkspace.jsx`
- `ExamWorkspaceContext.jsx`
- action CTA generation
- route/title tests
- navigation active-state tests
- readiness contracts
- status documents

## 12.2 Locked delivery model

**LOCKED: I8-A, I8-B, and I8-C must be serial and owned by one lane/owner.**

They must not be fanned out to parallel agents.

The shared write scope is too large and includes the same routing/navigation files.

## 12.3 IA design-lock requirement

The IA design-lock document gates **all** of I8-A/B/C.

It must define:

- canonical visible route map
- canonical route ownership
- page/component ownership
- front-door content
- selected-exam content
- canonical readiness source
- blocker/action CTA contract
- Advanced Repair access model
- portfolio/readiness data contract
- legacy URL strategy
- redirect timing
- component retirement plan
- test migration plan
- surface-count acceptance test
- no-new-surface rule

---

# 13. Advanced Import / Repair CMS

## 13.1 What the screenshots revealed

The operator was using the generic CMS for primary work because normal workflows did not expose all required actions.

The CMS shows a long entity list including:

- exam families
- exams
- cycles
- phases
- documents
- papers
- questions
- options
- coverage
- policy updates
- subjects
- topics
- aliases
- prerequisites
- mentions
- tags
- metrics

This is a database-oriented editor, not a task-oriented workflow.

## 13.2 Locked responsibility split

**LOCKED: move capabilities, not the CMS page.**

A blocker should identify the problem and open the exact operational editor required to resolve it.

The generic entity selector must not be embedded next to blockers.

## 13.3 Normal operational capabilities

These belong in Manage Exam:

| Problem | Operational destination |
|---|---|
| define phases | Setup → phases |
| fix dates | Setup → selected phase |
| upload/extract documents | Documents → upload/status |
| resolve extraction failure | Documents → failed document |
| review syllabus mentions | Syllabus → pending mentions |
| edit topic aliases | Syllabus → topic details |
| edit prerequisites | Syllabus → topic details |
| lock topic coverage | Syllabus/coverage → unlocked rows |
| add historical PYQ paper | PYQ → create/select cycle and paper |
| review PYQ questions/options | PYQ → selected paper/pending rows |
| review policy updates | Updates → pending updates |
| add/review competition metric | Competition → selected cycle |
| activation blocker | Review & Activate → unresolved gate |

## 13.4 Advanced Repair-only capabilities

Keep CMS for exceptional work:

- malformed records
- cross-exam reassignment
- raw JSON/metadata correction
- deduplication
- broken foreign-key/reference repair
- bulk import
- record reconstruction
- exceptional migration/backfill
- issues the guided workflow cannot repair

Target access:

```text
Manage Exam → More → Advanced repair
```

Default behaviour:

- scoped to selected exam
- selected cycle where applicable
- permission-gated
- warning displayed
- not a primary CTA
- not a sidebar peer

## 13.5 Global/shared entities

Some entities are shared across exams:

- exam families
- subjects
- topics
- aliases
- prerequisites

They should be editable contextually where possible, for example:

```text
Syllabus → Topic details → Edit aliases/prerequisites
```

Global repair may remain for power users, but it should not be the normal route for resolving an exam-specific blocker.

## 13.6 Review lifecycle protection

Reviewer status must not become arbitrary generic CMS CRUD.

The current architecture intentionally separates:

- content creation/correction
- review/approval/locking

Correct approach:

- operational editors may correct content
- review actions remain permission-gated
- blocker rows deep-link to the correct review action
- Advanced Repair must not bypass lifecycle governance

## 13.7 Raw IDs correction

The claim that the generic CMS still exposes full UUIDs across all entities was found to be stale.

The shared table renderer now truncates UUID-shaped ID/FK cells for all CMS entities.

Remaining problems may include poor labels or specific components outside the generic table, but “all CMS rows still show raw UUIDs” is not current evidence.

---

# 14. Blocker-to-editor action contract

## 14.1 Current defect

Every action built in `console_detail.py` currently gets:

```text
cta_label = "Open workspace"
cta_route = /admin/exam-intelligence/workspace/{exam_id}
```

This loses the task context.

“Review syllabus mentions,” “Verify PYQ,” and “Upload documents” all open the same generic destination.

## 14.2 Locked direction

**LOCKED: action CTAs must deep-link to the exact task state.**

Examples:

### Syllabus

```json
{
  "area": "syllabus",
  "title": "Review syllabus mentions",
  "cta_label": "Review 14 mentions",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?tab=syllabus&status=pending"
}
```

### Documents

```json
{
  "area": "documents",
  "title": "Resolve extraction failure",
  "cta_label": "Open failed document",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?tab=documents&document={document_id}"
}
```

### PYQ

```json
{
  "area": "pyq",
  "title": "Verify PYQ questions",
  "cta_label": "Review pending questions",
  "cta_route": "/admin/exam-intelligence/exams/{exam_id}?tab=pyq&paper={paper_id}&status=pending"
}
```

The final route shape remains subject to the IA route lock, but the semantic requirement is locked.

## 14.3 Action card content

A useful action should include:

- problem
- why it matters
- affected cycle/phase
- pending count
- evidence count
- primary `Resolve` action
- selected row/document/paper when known

## 14.4 Acceptance test

> Can an operator resolve every common blocker without opening Advanced Repair?

If not, normal operational capability is still missing.

---

# 15. CMS scoping and CRUD findings

## 15.1 Valid cluster

The screenshots correctly identified that the generic CMS is difficult to maintain because many entity lists are global rather than exam-scoped.

Examples include:

- subjects
- topics
- aliases
- prerequisites
- mentions
- coverage
- questions
- options

## 15.2 Incorrect solution to avoid

Do not respond by adding full inline CRUD for every entity inside the global CMS.

That would make the repair CMS the primary product and worsen the IA problem.

## 15.3 Correct decomposition

### Track J1 — Advanced Repair scoping

- selected exam scope
- selected cycle scope where applicable
- search
- filters
- pagination
- explicit advanced warning
- permission gate

### Track J2 — missing operational editors

Move ordinary work into Manage Exam:

- topic/microtopic management
- alias management
- prerequisite editing
- historical paper creation
- question/option correction
- policy flag correction
- cycle-specific entity management

### Track J3 — schema/domain redesign

These are not ordinary CRUD:

- phase/category competition cutoffs
- applied versus appeared candidate counts
- mixed-format PDF extraction
- evidence-based coverage scoring
- structured competition breakdowns

They need contracts and potentially schema changes.

---

# 16. PYQ pagination and historical papers

## 16.1 I5 endpoint audit result

Backend pagination already exists for PYQ questions:

- paper filter
- reviewer-status filter
- `limit`
- `offset`
- exact `total`
- deterministic question-number ordering

The frontend still requests `limit=200` and handles some filters/sorts locally.

## 16.2 Pagination implementation risk

After server pagination, client-only filtering/sorting would become page-local and misleading.

Before implementing I5:

- move supported filters server-side
- keep deterministic server ordering
- add `source_kind` server filter if required
- remove or defer confidence/status sort controls unless globally correct
- reset offset on filter/paper changes
- clamp page after mutations
- show total after filters
- refetch after review actions

I5 is an isolated implementation and does not require the IA redesign, but its UI must not hardcode old routes that the IA arc will immediately remove.

## 16.3 Historical papers

The schema can store old papers by year/cycle/phase.

The practical gap is workflow:

- no clear normal `Add paper` path
- current workspace filters to selected cycle
- empty states send operators toward CMS
- old cycles must first exist and be selected
- Prelims/Mains paper creation is not explained

This belongs in Manage Exam → PYQ, not Advanced Repair.

---

# 17. Mock error-pattern semantics

## 17.1 Verified current meaning

For manually logged mocks, the user enters counts for:

- concept gap
- calculation error
- time pressure
- misread question
- guesswork

These values are stored as supplied. They are not system-inferred from answer sheets.

## 17.2 Trust issue

Without explicit copy, the UI can look as if the platform inferred these causes.

That is a trust defect.

## 17.3 Locked immediate correction

Relabel:

```text
Error patterns
```

to:

```text
Self-reported error patterns
```

Explain that:

- time pressure
- misread
- guesswork
- concept gap

are entered by the user for manually logged mocks.

## 17.4 Average score

The current average is calculated across all mocks returned in the current collection.

It is not necessarily:

- same exam
- same template
- repeated attempts
- same phase

Immediate label:

```text
Average across N logged mocks
```

Later improvement:

- exam filter
- template filter
- date range
- platform versus self-logged separation

## 17.5 Evidence-derived labels

For platform attempts, derive only what telemetry supports.

Examples:

- time pressure requires timing/timeout/incomplete-tail evidence
- guesswork requires confidence input or a documented proxy
- misread usually requires user review classification
- concept gap requires repeated topic-level evidence

Do not infer unsupported causal labels from correctness alone.

---

# 18. Active state, management mode, cadence, coverage, and high-yield fields

## 18.1 Existing partial definitions

The code already defines:

### Active

- visible/usable
- inactive means hidden but retained
- not the same as planner readiness

### Management mode

- core — full readiness expected
- light — essential facts and major updates
- index-only — searchable reference, no deep Study OS
- archive — retained with minimal active operations

### Cadence

- annual
- recurring
- irregular
- one-off
- unknown

### Coverage fields

- coverage depth describes how strongly a topic belongs
- priority score influences planner timing/frequency
- high-yield should be supported by syllabus/PYQ evidence

## 18.2 Still-open governance question

The UI definitions do not answer who assigns these fields or how.

The lock still needs:

- deterministic rule
- admin judgement
- model suggestion
- evidence threshold
- reviewer lifecycle
- reassessment cadence

These are not tooltip-only questions.

Suggested decision inputs:

- aspirant demand
- recurrence
- content maintenance cost
- PYQ availability
- strategic value
- operational SLA
- evidence quality

Status: **DEFERRED PRODUCT CONTRACT.**

---

# 19. Mixed-format PDF support

## 19.1 Verified current limitation

The current extraction pipeline assigns one structural format to the whole document.

The v1 extractor supports only a narrow eligible format, notably bilingual two-column MCQ.

It does not robustly support a single PDF that changes between:

- bilingual and monolingual
- single-column and two-column
- objective and subjective
- tables/figures and plain text

## 19.2 Decision

Do not silently make manual PDF splitting an undocumented operator responsibility.

The product must either:

1. support page-range/page-level layout classification, or
2. reject unsupported mixed files clearly and document the temporary workaround

Status: **DEFERRED EXTRACTION ARCHITECTURE.**

---

# 20. Competition metrics

## 20.1 Verified limitation

Current competition fields include opaque JSON for values such as:

- cutoff trends
- category vacancy breakdowns

There is no locked structure for:

- phase/category cutoffs
- applied versus appeared
- category counts
- selection ratios by stage
- historical trend semantics

## 20.2 Decision

Do not treat this as generic CMS CRUD.

It requires:

- domain contract
- JSON/schema decision
- evidence model
- reviewer lifecycle
- frontend table/edit design

Status: **DEFERRED CONTRACT-FIRST WORK.**

---

# 21. I7, I8, I9, H2, and I5 final status

| Item | Final decision/status |
|---|---|
| H1 | Code-fixed; redeploy and linked-document E2E validation required |
| H2/D2 | P0 correctness bug; immediate backend fix |
| I5 | Backend pagination exists; frontend/server semantics implementation remains |
| I7 | Unblocked; landing-page exam lane removal only |
| KG sidebar exam group | Remove only in I8-A when replacement nav entry lands |
| KG rename | Separate later PR |
| I8 old registry-first cleanup | Superseded |
| I8-A/B/C | Gated by IA design lock; serial one-owner lane |
| I9 architecture | Hybrid locked |
| I9 implementation | Blocked on detailed gate doc |
| portfolio/coverage “I10 surface” | Cancelled |
| portfolio/coverage backend read model | Required inside I8, no visible route |
| mock semantics | Isolated trust fix; dispatchable |
| Advanced Repair | Retained only as scoped overflow/fallback |

---

# 22. Correct execution sequence

## 22.1 Immediate, isolated work

These runtime areas are independent:

1. **H2/D2 real extraction readiness**
2. **I7 KG landing-card removal only**
3. **Mock semantics trust fix**
4. **I5 PYQ question pagination**, if it does not introduce route assumptions that conflict with the IA lock

Each implementation PR still touches the shared checklist, so branches must rebase or assign one tracker owner.

## 22.2 Documentation gates

Next document:

### Exam Management IA design lock

Must include:

- no-new-surface rule
- surface-count baseline and exit test
- canonical route map
- canonical page names
- component ownership
- readiness source of truth
- blocker/deep-link contract
- portfolio/readiness read-model contract
- Advanced Repair access model
- old-route compatibility
- redirect sequence
- component retirement
- test migration
- I8-A/B/C write scopes

Separate or linked document:

### I6 cycle-setup gate

Must include:

- checklist steps
- completion sources
- hard/advisory/N-A rules
- deep links
- resume behaviour
- `AddCycleWizard` decision
- management-mode/cadence applicability

## 22.3 Serial IA implementation

After the IA lock:

1. backend read model needed by consolidated pages
2. I8-A — Exam Management front door + sidebar relocation
3. I8-B — per-exam Console/Workspace consolidation
4. I8-C — Advanced Repair isolation
5. compatibility redirects
6. orphan/dead component cleanup

One owner, strict sequence.

## 22.4 Deferred feature contracts

Do not interleave with I8 navigation work:

- CMS domain CRUD redesign
- mixed-format PDF extraction
- competition metrics structure
- evidence-derived coverage governance
- full management-mode assignment policy
- old-cycle UX beyond basic paper creation
- KG rename

---

# 23. IA acceptance criteria

The final arc passes only if all are true:

## Navigation

- one visible Exam Management entry
- no visible Console peer
- no visible Workspace peer
- no exam-management lane inside KG
- no visible global CMS peer
- Manage Exam is a drill-in
- Advanced Repair is overflow

## Work completion

- each common blocker has a precise Resolve action
- blockers preserve exam/cycle/phase context
- syllabus review opens pending syllabus work
- PYQ review opens the relevant paper/questions
- document failures open the failed document
- competition actions open the selected cycle
- operators do not need the generic CMS for normal work

## Data presentation

- front door shows family → exam → cycle → phase
- Manage Exam shows per-cycle readiness
- readiness uses explicit states
- no second portfolio/coverage route exists

## Governance

- review/lock lifecycle cannot be bypassed through repair
- CMS remains permission-gated
- global/shared taxonomy changes remain auditable
- H2 uses processing-job evidence, not trust state
- manually logged mock causal labels are presented as self-reported

## Compatibility

- existing deep links continue to work during migration
- redirects land only after targets exist
- no intermediate 404 state
- tests cover active nav state and redirects

## Surface-count test

Before:

```text
KG exam lane + Registry + Console + Workspace + CMS
```

After:

```text
Exam Management
  → Manage Exam drill-in
  → Advanced Repair overflow
```

If the number of visible peers stays equal or increases, the arc fails.

---

# 24. Explicit non-goals

This decision record does not authorize:

- a new portfolio dashboard
- a new coverage-matrix page
- a second exam console
- another workspace variant
- embedding the full CMS inside blocker cards
- unrestricted reviewer-status editing
- deleting old routes before compatibility targets exist
- implementing I9 before its gate document
- changing mixed-PDF behaviour without an extraction contract
- inventing exam-readiness metrics unsupported by backend data
- marking code-fixed items live-complete without redeploy proof

---

# 25. Repository evidence index

The following current repository files substantiate the findings:

## Baseline and status

- `AGENTS.md`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/wiki/index.md`
- `docs/status/career-copilot-checklist.md`
- `docs/status/career-copilot-pr-plan.md`
- `docs/reviews/exam-intelligence-design-review-2026-06-20.md`
- `docs/audits/document-readiness-2026-06-21.md`

## Routes and navigation

- `app/frontend/src/routes/adminRoutes.jsx`
- `app/frontend/src/pages/admin/AdminShell.jsx`
- `app/frontend/src/pages/admin/__tests__/AdminShell.nav.test.js`

## Existing surfaces

- `app/frontend/src/pages/admin/KnowledgeGovernance.jsx`
- `app/frontend/src/pages/admin/ExamIntelligence.jsx`
- `app/frontend/src/pages/admin/ExamGovernanceConsole.jsx`
- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx`
- `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx`

## Console and readiness

- `app/frontend/src/features/admin/exam-intelligence/ConsoleWorkQueue.jsx`
- `app/frontend/src/features/admin/exam-intelligence/ExamActionConsole.jsx`
- `app/backend/app/exam_intelligence/console_detail.py`
- `app/backend/app/exam_intelligence/readiness.py`
- `app/backend/app/api/admin_exam_intelligence.py`

## Workspace operational editors

- `app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/panels/CompetitionPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/panels/DocumentsPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/syllabus-mapper/SyllabusMapperPanel.jsx`
- `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/PyqWorkbenchPanel.jsx`

## CMS and lifecycle

- `app/backend/app/api/admin_exam_intel_cms.py`
- `app/backend/app/api/admin_exam_intel_documents.py`
- `app/frontend/src/features/admin/exam-intelligence/ExamIntelGlossary.jsx`

## PYQ

- `app/frontend/src/pages/admin/studyos/PyqPaperWorkspace.jsx`
- `app/backend/app/api/admin_exam_intel_cms.py`

## Mock semantics

- `app/frontend/src/pages/study/Mocks.jsx`
- `app/backend/app/api/study_os.py`

## Extraction format

- `app/backend/app/exam_intelligence/extraction/dispatch.py`

---

# 26. Final locked statement

The product must not solve exam-management confusion by adding another surface.

The final architecture is:

> **One Exam Management front door. One Manage Exam drill-in. Advanced Repair only as scoped overflow.**

Portfolio hierarchy, coverage readiness, blockers, next actions, and ordinary CRUD are content inside that hierarchy.

The implementation order is controlled by the IA design lock. Until route ownership, readiness authority, deep-link contracts, and migration sequencing are written and approved, I8-A/B/C must not be dispatched.
