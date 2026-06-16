# Exam Governance UX Audit — Findings, Decisions, Learnings (Wave 4.6F–4.6H)

Status: canonical in-repo record.
Generated: 2026-06-16. All repo claims verified against `main` at authoring time (file:line anchors inline).
Scope: admin Exam Governance / Exam Intelligence surfaces in `app/frontend`.

## 1. Executive diagnosis

The 4.6 wave built a better per-exam surface (the console: task rail, blocker-first, no readiness %) but never repointed the operator's doors at it. Every real per-exam path still enters the OLD standalone workspace, so the wave produced almost no felt UX change.

Default path today (bypasses console):
  Knowledge Governance / Registry -> Exams tab -> "Open workspace" -> /admin/exam-intelligence/workspace/:exam_id  (old tabs, "9% ready" %, dense zero panels)
Intended path:
  Exam Governance Console -> open exam -> /admin/exam-intelligence/console/:exam_id  (task rail, blocker-first, no default %)

Through-line: the wave optimized components and information architecture but never owned the journey. The fix is not more intelligence; it is making the already-shipped console reachable on the normal operator path.

## 2. Repo grounding (verified against main)

- `features/admin/exam-intelligence/ExamListTable.jsx:110-116` — `<Link to={/admin/exam-intelligence/workspace/${e.id}}>Open workspace</Link>`. The load-bearing failure: per-exam clicks route to standalone workspace, bypassing the console.
- `pages/admin/KnowledgeGovernance.jsx:16-20` — exam-truth lane chips = Exam Intelligence (/admin/exam-intelligence), Guided Exam (/new), CMS / PYQ (/cms); `metricKey: null` (:20). No console chip. The AI-guardrails lane is also `metricKey: null` (:50), so "counts: not available yet" renders on BOTH null lanes, not exam-truth alone.
- `pages/admin/ExamGovernanceConsole.jsx:30` — `EXAM_LIST_PARAMS = { limit: "200", active_state: "active" }`; plain `items.map` full-width button list. No search/filter/pagination/grouping/readiness/priority.
- `pages/admin/AdminShell.jsx:55` — sidebar still `label: "Raw CMS / Bulk Import"` while page h1 is "Advanced Import / Repair" (4.6E). `:38` surfaces `Recruitments` — DB vocabulary in operator nav (invariant: DB=recruitment, label=exam).
- `pages/admin/ExamIntelligence.jsx:85-91` — /exams supports: limit, offset, q, exam_type, active_state, management_mode, cadence, exam_family_id. NO sort, NO blocker/workflow filters, NO work-queue aggregate. FE holds one server-paginated page, so it cannot honestly sort "blocked-first" across all exams client-side. => search + existing filters + pagination + per-row readiness badge are FE-reusable; blocker-first sort, task filters, landing counts are backend-gated.
- `pages/admin/exam-workspace/ExamWorkspace.jsx` — variant==="console" renders ExamTaskRail; else old tab strip with readiness %. Console hides the cycle picker to avoid leaking to /workspace.
- `pages/admin/exam-workspace/ExamTaskRail.jsx` — rows: Setup, Documents, Syllabus, PYQ, Topic coverage, Updates, Competition, Publish; topic coverage derived from readiness.topic_coverage; one blocker shown per row.

## 3. Findings

### 3A. Architecture / journey failures
1. Orphaned surface: console built with no inbound route from the real workflow; entry rewire belonged to no PR (deferred 4.6A->4.6B; 4.6B only touched sidebar).
2. No cutover: better variant (console) built while worse variant (workspace) stayed the default per-exam destination -> improvement is effectively dead code in prod.
3. Invariant on wrong surface: D-E ("no %") scoped to variant="console" only; the real path is variant="workspace", so the "9% ready" the wave existed to kill is still front-and-center.
4. Two competing per-exam surfaces (/console/:id vs /workspace/:id), no canonical designation; same exam, two experiences.
5. Over-read lock: D-A "four-lane landing untouched" applied as "never edit the landing" instead of "don't restructure the lanes" -> fenced the one chip edit that would surface the console.
6. Missing lock: no decision ever named "per-exam entry routes to console", so no PR owned it.
7. Context-dropping entry: "Open console" lands on a bare picker, discarding the in-context exam.
8. Console-only improvements (task rail, Publish Impact, no-%) are invisible to anyone entering via workspace.
9. Plumbing before payoff: backend reads (4.6D0-BE), publish-impact (4.6D), variant threading (4.6A.1) shipped before the one cheap wire that makes them visible.
10. Tests validated components/routes, not the end-to-end click-through (no assertion that a Registry row click lands in console variant with no %).

### 3B. Granular UI/UX audit (screenshot- + code-grounded)
Sidebar/nav: sidebar "Raw CMS / Bulk Import" vs page "Advanced Import / Repair" vs masthead "Raw CMS" — one route, three labels. "Recruitments" DB term in nav (AdminShell.jsx:38). Exam doors scattered across 3 sidebar groups. ~20 items / 8 groups, long wrapping headers -> telemetry-console feel.
Duplicate routes/clicks: two routes per exam; three doors to /new (sidebar, Registry CTA, CMS "+ New guided exam"); two cycle-add paths (CMS Add cycle, workspace Setup & Phases); console entry is 3 clicks vs the wrong 2-click workspace entry.
Registry table: leads with slug ("Exam key"), name second; ~11 columns; Cadence "Unknown" and Business priority "Managed light" on all rows (dead columns); "Planner-ready topics 0 / 0" cryptic; no sort affordance; row action is the wrong route.
Filters/search: Registry HAS q + 5 filters + pagination (good) but 5 dropdowns is heavy and several are single-value-for-all today; no "needs action"/blocker/missing-PYQ/missing-coverage filters; no clear-filters, no sort, no saved views. Filters are data-model-shaped, not workflow-shaped.
Console picker: full-width single-label rows (huge horizontal waste); five near-duplicate "Assistant Engineer / Junior Engineer" rows disambiguated only by slug state-prefix (DB key doing a State column's job); alphabetical A-Z (low-value exams on top); no action affordance; no search/filter/pagination/grouping/readiness.
Workspace/console split: route architecture leaked into UX; old workspace still dominant.
% leakage: "9% ready · partial" red banner, "Review & Activate 9%" tab, per-section 80/0/50% in READINESS, with redundant pill+% pairs.
Task rail: better than tabs but area-based not task-based; one blocker max per row; topic coverage derived/never-active (can feel broken); no per-row blocker count; no setup-vs-activation grouping; only visible in console route.
Panels: workspace Overview = ~9 fully-expanded cards, mostly zeros; no progressive disclosure/collapse for empty sections; slug wraps across 4 lines in identity card; doesn't answer one central question ("can this exam safely reach aspirants/planner?").
Warnings/banners: LIFECYCLE-GATED CONTRACT paragraph renders on BOTH Registry tabs, always-on (~80px), not collapsible; lifecycle legend duplicated top+bottom of workspace; CMS caution good intent but engineer-voiced ("idempotency", "upsert key"); warnings explain policy instead of pointing to the safer next action.
Color: red banner for a normal early-setup state; red "NOT READY" on every empty row -> alarm fatigue; green used on count=0 (implies "good"); indigo "Open workspace" button outside the clay/earth palette; status conveyed by color + tiny text.
Buttons: too many equal-weight (Registry top 3; landing chips; CMS Reload/New row/Bulk import/New guided exam; workspace "Go to next action" vs tab strip); no clear single primary; picker rows have no affordance; CMS exposes Edit/Retire/Add-cycle on a "do not use" page.
Space: picker wastes horizontal (full-width single labels); landing/Overview waste vertical (~40-50% blank); workspace over-packs (9 zero panels). No consistent density model. Vertical wasted yet content cramped = layout smell.
Typography/fonts: pervasive tracked-uppercase microtext; monospace overused for slugs/counts/statuses/timestamps -> database aesthetic fighting the serif h1s; critical text (blockers, counts, helper) is small; long slugs wrap/crowd cells.
Table row/column expansion: tables flat and dense, no row expansion; all info forced into tiny cryptic columns. Collapsed model should be Exam | Lane | Status | Blockers | Coverage | PYQ | Last touched | Action, with the rest in an expanded row.
Dev/DB leakage: "Live · /api/admin/exam-intelligence" in chrome; "Per spec §12 #4" and "review_status / trust_status" in CMS copy; truncated UUIDs and full ISO timestamps as CMS columns; raw event keys ("exam_intel.cms.cycle.create") in the activity feed; exam_type "recruitment"; "Exams · exams" prints label + endpoint name.
Drawers: AdvancedDrawer removal from workspace was directionally right; missing useful drawers (lifecycle help, evidence trace w/o %, row detail, filter drawer on small screens). Anti-patterns to avoid: raw table editors in the main workspace drawer; primary actions hidden in drawers.

### 3C. Useful today (keep, possibly compress)
Lifecycle-gated contract text; Registry filters; management mode / cadence as compact badges; topic-coverage snapshot (not as a primary task); Publish Impact panel (after console routing is fixed); Advanced Import / Repair caution banner.

### 3D. Irrelevant or over-prominent (demote/remove from main path)
Raw CMS as a sidebar-visible advanced primary; large static lifecycle banners; slug ("Exam key") as the lead Registry column; standalone workspace as the primary row action; decorative uppercase labels; repeated "nothing generated by AI" copy on every screen; "Live · /api/..." status text; the flat console picker.

## 4. Decisions (with reasons)

LOCK 1 — Cycle-in-console: ship the rewire now; /workspace remains the cycle-switching fallback; do NOT pull /console/:exam_id/:cycle_id into 4.6F.
Reason: console hides the cycle picker (deferred); blocking the door-rewire on cycle support would keep the old workspace primary indefinitely. Fix the door first.

LOCK 2 — Readiness %: demote standalone, do NOT strip % globally yet.
Reason: the bug is that default flows ENTER standalone, not that standalone exists. Once Registry routes to console, the % surface stops being the default — satisfying D-E intent without a destructive global edit to variant="workspace".

LOCK 3 — Picker reuse: extract ONE shared exam-list component driven by the existing /exams contract, row action injected. Registry row = console-primary + advanced-workspace-secondary; console picker row = console.
Reason: reuse discipline; avoids two divergent list implementations and reuses Registry's search/filter/pagination.

LOCK 4 — 4.6F scope: three wires only (Registry row route, KG landing chip, naming consistency). Picker upgrade is 4.6G.
Reason: one concern per PR.

Corrections applied to the source draft before adoption:
- The draft's header claimed it was "created outside the repository as a local handoff" — false for an in-repo artifact; removed.
- The draft folded a 4th change into 4.6F (remove CMS "+ New guided exam" CTA) and listed it as P0 — this violates LOCK 4 (three wires, one concern). Moved to the cleanup tier.
- Added per-lock reasons and verified file:line anchors; corrected the "counts: not available yet" note to cover both null-metric lanes.

## 5. Learnings & principles (this session)

- Verify before verdict, even on accurate-looking drafts: all 6 file paths and 5 routing/label claims in the source draft checked out against main — but the draft's self-location header was wrong and would have been enshrined. Confirming is cheap; enshrining a wrong claim is not.
- Per-PR green != wave goal met. Each 4.6 PR passed its own scope and CI; the wave still failed because no PR owned Landing -> Registry -> Exam -> Console. Review the end-to-end deployed journey, not just per-PR scope (this miss required user screenshots to surface).
- Entry/door wiring is load-bearing and must be a NAMED concern owned by one PR. Deferring it across PRs orphaned it.
- Prove FE-vs-backend from the actual query contract, not intuition. Inspecting /exams params was decisive: it split the work cleanly and stopped "blocker-first sort" from being mislabeled as a free FE change.
- Scope-guard locks can over-constrain. D-A was meant to prevent lane restructuring; read literally it blocked the load-bearing chip edit. Record lock INTENT, not just text.
- Demote > strip for risky global invariants (keep the % surface, just stop making it the default).
- Reuse > rebuild (the console picker should reuse the Registry list, not re-implement a worse one).
- Evidence/detail surfaces must not reintroduce a confidence percentage (ExamEvidenceDrawer's ConfidencePill was fenced for exactly this; any evidence redesign keeps that fence).
- PYQ Workbench is reuse-only across every tier, including rail redesign.
- The product's recurring smell: the UI renders the database (slugs, UUIDs, ISO timestamps, endpoints, event keys, spec refs, per-section %), and renders empty state as densely as full state. Design rule in §8 is the antidote.

## 6. Dispatch plan

### 4.6F — Connect operator doors to console (FE-only, three wires)
- ExamListTable.jsx: primary row action "Open console" -> /console/:exam_id; secondary "Advanced workspace" -> /workspace/:exam_id.
- KnowledgeGovernance.jsx: exam-truth chips -> [Exam Governance Console (primary), Exam Registry, Create exam]; remove "CMS / PYQ" from first-row chips.
- Naming: replace remaining visible "Raw CMS / Bulk Import" (AdminShell.jsx:55 sidebar + masthead/title source) with "Advanced Import / Repair"; body h1 already done (4.6E); keep /cms route.
- Out of scope: cycle-in-console, /console/:exam_id/:cycle_id, any backend, blocker-first sort, task filters, % removal, sidebar mode-focus, Publish Impact, CMS CTA removal.
- Acceptance: Registry row primary -> /console/:exam_id; advanced workspace secondary present; KG first exam-truth action = Console; no "Raw CMS / Bulk Import" in nav/masthead; /cms,/new,/console,/workspace resolve.

### 4.6G — Console picker becomes the real list (FE-only)
- Extract/reuse Registry exam-list into a shared component driven by /exams (q, exam_type, active_state, management_mode, cadence, exam_family_id, limit, offset).
- Picker gains search + those filters + pagination + per-row readiness badge; name first, slug/state secondary; row -> Open console.
- Out of scope: blocker-first sort, task/workflow filters, work-queue counts, new backend. Do NOT claim blocker-first sorting.

### 4.6H0 — Backend read preflight (investigation, no code)
- Determine whether /exams can support a `sort` param and computed filters (needs_action, no_pyq, no_locked_coverage, stale_updates, ready_to_activate), and whether a KG/console aggregate can return exam-truth work-queue counts. Define the minimal read shape. No UI.

### 4.6H — Thin backend read + FE work queue (only if preflight confirms)
- Add backend sort/filter + aggregate counts (blocked/ready/pending review/stale); wire into console + KG landing; add blocker-first sorting.
- Out of scope: schema changes, write/mutation changes, planner behavior.

### Cleanup tier (FE-only, parallel-safe where isolated)
- Remove CMS "+ New guided exam" CTA that contradicts the repair warning (moved here from 4.6F per LOCK 4).
- De-leak chrome: drop "Live · /api/..."; replace "§12 #4" and review_status/trust_status copy; humanize event keys (exam_intel.cms.cycle.create -> "Cycle created"); hide UUIDs/ISO timestamps behind details.
- Lifecycle banner collapsible; normalize button hierarchy (one primary/screen); reserve monospace for IDs; slug to secondary line; reduce uppercase microtext; shorten CMS caution; shed dead Registry columns (Cadence, Business priority) via row expansion.

### Redesign tier (separate spec — do NOT fold into 4.6F/4.6G)
- Workspace Overview reframed: can this exam reach aspirants? can planner consume it? what blocks activation? what evidence supports it? mock/template impact?
- Task rail -> action queue (not area list); Registry row-detail drawers; cycle-in-console.
- Evidence detail must NOT reintroduce a confidence-percentage drawer.

## 7. Guardrails (do not, in immediate PRs)
Do not: implement cycle picker in console (4.6F); remove the standalone workspace route; strip % globally in 4.6F; implement backend-gated sort/filter in FE; resurrect a %-rendering evidence drawer; fork/rewrite PYQ Workbench; restructure sidebar behavior / mode-focus; remove CMS functionality; invent work-queue counts the backend does not provide.

## 8. Product design rule going forward
Primary operator UI must answer: (1) what needs action? (2) why is it blocked? (3) what is the safest next click? (4) what evidence supports it?
Implementation vocabulary (slug, UUID, ISO timestamp, endpoint path, review_status/trust_status, spec section, event key, "upsert key", "idempotency") belongs only in advanced/detail contexts: Advanced Import / Repair, evidence/detail views, debug views, explicit advanced drawers.

## 9. Dispatch order
4.6F door rewire + naming -> 4.6G shared list / real picker -> 4.6H0 backend preflight -> 4.6H thin BE + FE work queue. Cleanup tier in parallel where isolated. Redesign tier as a separate spec.
