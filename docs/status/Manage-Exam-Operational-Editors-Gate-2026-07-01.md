# Manage Exam Operational Editors Gate — J2 Contract

- Document type: J2 implementation contract — operational editors in Manage Exam
- Status: **DRAFT — OPERATOR APPROVAL REQUIRED** (no implementation PR may be dispatched until this is OPERATOR APPROVED)
- Date: 2026-07-01
- Parent track: `J2 — missing operational editors in Manage Exam` (`docs/status/career-copilot-checklist.md`)
- Authority: `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §3.2 (per-component role resolution), §6 (Manage Exam content), §7 (blocker-to-editor deep-link contract)
- Gates cleared: I8-A merged (PR #755), I8-B merged (PR #757 `385912bd`), I8-C merged (PR #759 `f4378097`), I6 merged (PR #761 `d69602f8`), J1 merged (PR #820 `d70c33aa`)
- Related prior work: PYQ source/paper onboarding (PR #769, `docs/status/PYQ-Source-and-Paper-Onboarding-Gate-2026-06-25.md`) already delivers historical-paper creation inside the PYQ tab; J2 does not re-scope that.

---

## How to use this document

Every section states a LOCKED decision or an exact specification the implementation must follow. Deviations require a new gate document, not a PR-level justification. Items marked **OPERATOR DECISION REQUIRED** are genuine open choices — they must be resolved by operator approval (GitHub comment on the implementation PR, matching the J1 approval pattern) and must not be guessed or invented before then.

**No implementation PR may be dispatched until this document is OPERATOR APPROVED.**

**Serial delivery rule (locked, AGENTS.md):** J2 work touches `ExamWorkspace.jsx` (shared write scope). All sub-steps are one owner's sequential work — never fan out sub-steps across agents in parallel.

---

## Section 0 — What already exists (post-J1 baseline)

### 0.1 Manage Exam route and tabs

- Route: `/admin/exam-intelligence/exams/:exam_id` (`AdminExamWorkspace`, `adminRoutes.jsx:105`).
- Route protection: `ProtectedRoute role={ADMIN_ROLES}` (super_admin / admin). No per-permission gate on the route today.
- Tab state: URL query param `?tab=<id>` (default `setup`); cycle context via `?cycle=<cycle_id>`.
- `TAB_ORDER` (`ExamWorkspace.jsx:40–48`):

| Tab id | Label | Kind |
|---|---|---|
| `setup` | Setup | open |
| `documents` | Documents | open |
| `syllabus` | Syllabus Mapper | readiness |
| `pyq` | PYQ Workbench | readiness |
| `updates` | Updates | readiness |
| `competition` | Competition | readiness |
| `review` | Review & Activate | terminal |

- Advanced Repair overflow (`AdvancedRepairMenu`, `ExamWorkspace.jsx:61–150`): "More → Advanced Repair" → `/admin/exam-intelligence/cms?exam_id=…&cycle_id=…&entity=documents`. Shown only when `user.role === "super_admin" || user.permissions.includes("exam_intelligence.cms")` (`ExamWorkspace.jsx:165–167`).

### 0.2 Backend editor endpoints already present (gated on `exam_intelligence.cms`)

All defined in `app/backend/app/api/admin_exam_intel_cms.py`, all `Depends(require_permission(PERM_CMS))` where `PERM_CMS = "exam_intelligence.cms"` (line 55):

| Endpoint | Methods | Key params / fields |
|---|---|---|
| `/topics` | GET, POST, PATCH | GET: `subject_id`, `parent_topic_id`, `level`, `is_active`, `q`, `limit`, `offset`. Levels: `topic`, `microtopic`, `concept`. |
| `/topic-aliases` | GET, POST, DELETE | GET: `topic_id`, `limit`, `offset`. POST: `topic_id`, `alias`, `source_context`. DELETE: `reason` (8–500 chars). |
| `/topic-prerequisites` | GET, POST, DELETE | GET: `topic_id`. POST: `topic_id`, `prerequisite_topic_id`, `relation_type`, `strength`, `source_basis`. Relations: `requires`, `recommended_before`, `supports`, `foundation_for`. Self-cycle guard present. |
| `/policy-updates` | GET, POST, PATCH | GET: `exam_id`, `reviewer_status`, `update_type`. Official-source guardrail: non-official sources cannot set `affects_*` flags. |

These endpoints exist and are correct. J2 reuses them; it does not rebuild them.

### 0.3 Permission tokens present in the system

`<domain>.<verb>` convention, confirmed across the backend:

`exam_intelligence.cms`, `exam_intelligence.review`, `exam_eligibility.manage`, `community.manage`, `mentors.manage`, `persona.manage`, `study_os.support`, `study_os.ops`, `study_os.viewer`.

There is **no** `exam_intelligence.manage` token today.

### 0.4 `require_permission` semantics

`app/core/auth.py:338–361`. Accepts a **single** token. `super_admin` bypasses. No OR/alternative logic. Requiring "cms OR manage" needs a new helper (see OD-2).

### 0.5 exam → subject relationship (indirect only)

There is no `subjects.exam_id` column. Subjects belonging to an exam are resolvable two ways:

- **Via phases:** `exams → exam_phases(exam_id) → exam_phase_sections(subject_id) → subjects` (migration 030).
- **Via coverage:** `exams → exam_topic_coverage(exam_id, topic_id) → topics(subject_id) → subjects` (migrations 029/030).

This indirection is the core scoping complexity J2's Syllabus tab must handle (see Section B).

---

## Section A — Gap analysis: what J2 adds

### A.1 The gap

Routine content editing (topics, aliases, prerequisites, policy flags) is only reachable through **Advanced Repair** (`ExamIntelCms.jsx`), which is deliberately positioned as an exceptional, power-user, `exam_intelligence.cms`-gated escape hatch behind an always-on `AdminSafetyBanner`. Per the IA lock (§3.2, §6), normal operational work belongs in Manage Exam tabs — not in the repair surface.

| # | Gap | Target tab |
|---|---|---|
| G-1 | Topic / microtopic management not available in Manage Exam | Syllabus |
| G-2 | Alias management not available in Manage Exam | Syllabus |
| G-3 | Prerequisite editing not available in Manage Exam | Syllabus |
| G-4 | Policy-flag (`affects_*`) correction not available in Manage Exam | Updates |
| G-5 | Cycle-specific entity management not surfaced against the active cycle selector | (later slice) |

### A.2 What J2 does NOT add

- No new route, no new sidebar entry, no new top-level surface (no-new-surface rule, locked 2026-06-21).
- No change to Advanced Repair (`ExamIntelCms.jsx`) — it remains the `exam_intelligence.cms` repair surface with its `collapsible={false}` banner.
- No rebuild of the backend editor endpoints (§0.2) — reuse only, plus the auth-helper addition in OD-2 if the new-tier option is approved.
- No AdminSafetyBanner in Manage Exam (Manage Exam is the normal-operation surface; the repair banner stays in Advanced Repair only).
- Historical-paper creation and question/option correction are **out of J2 scope** — delivered by the PYQ onboarding track (PR #769) in the PYQ tab.

### A.3 Delivery slicing (LOCKED — serial)

J2 ships as sequential slices, one owner, no fan-out (shared `ExamWorkspace.jsx` write scope):

| Slice | Content | Tab | Status |
|---|---|---|---|
| **J2-A** | Topic + microtopic + alias + prerequisite editors | Syllabus | **This contract's first slice** |
| J2-B | Policy-flag (`affects_*`) correction | Updates | Deferred to follow-up gate revision |
| J2-C | Cycle-specific entity management | Setup / cycle selector | Deferred to follow-up gate revision |

This document fully specifies **J2-A**. J2-B and J2-C are scoped at the summary level here and require a gate revision (or a follow-up gate) with the same OD process before implementation.

---

## Section B — Scoping contract (J2-A)

### B.1 Subject resolution for the Syllabus tab (LOCKED)

The Syllabus tab is scoped to one exam (`:exam_id` from the route). Topics are `subject_id`-scoped, so J2-A MUST resolve the exam's subject set before listing topics.

- **Resolution path (LOCKED):** use the **coverage path** — `exam_topic_coverage(exam_id) → topics → distinct subject_id`. Rationale: coverage is the exam's declared syllabus surface and is already the canonical "what this exam tests" set; the phase-section path is a superset that includes structural sections not necessarily mapped to coverage. A backend helper endpoint returning the distinct subjects for an exam is required (see OD-4).
- **Empty coverage (LOCKED):** if the exam has no `exam_topic_coverage` rows, the Syllabus editor shows an empty state ("No subjects mapped to this exam yet") with a link to coverage mapping — it must NOT fall back to the global subject list.

### B.2 Write-safety / fail-closed (LOCKED — inherit J1 pattern)

J2-A reuses the J1 scope-safety model:

- A scope-resolution state machine (`idle | resolving | valid | error`) for the exam→subjects resolution.
- `writesBlocked` is true until the exam's subject set is resolved AND matches the current `:exam_id`; all create/edit/delete handlers early-return while blocked.
- No POST/PATCH/DELETE may fire before subject resolution completes or after it errors.

### B.3 List scoping params (LOCKED)

| Editor | List request scoping |
|---|---|
| Topics | `subject_id=<one of the exam's resolved subjects>` (+ optional `parent_topic_id`, `level`, `q`, `limit`, `offset`) |
| Topic aliases | `topic_id=<selected topic>` |
| Topic prerequisites | `topic_id=<selected topic>` |

Topic editing is always entered through a selected subject (from the exam's resolved subject set); alias/prerequisite editing is always entered through a selected topic. No global (unscoped) topic list is ever shown in Manage Exam.

---

## Section C — UI contract (J2-A)

### C.1 Placement (LOCKED)

Inside the existing Syllabus (`syllabus`) tab of `ExamWorkspace.jsx`. No new tab. The editor is a panel within the Syllabus tab, below the existing Syllabus Mapper readiness content.

```
[Syllabus tab]
  [Existing Syllabus Mapper readiness content — unchanged]
  [Subject selector — exam's resolved subjects only]
    [Topic list for subject — search (q), level filter, pagination 50/page]
      [Topic row → expand] [Aliases editor] [Prerequisites editor]
      [New topic] [Edit topic] [Retire topic]
```

### C.2 Reuse mandate (LOCKED)

The topic / alias / prerequisite editor UI already exists in `ExamIntelCms.jsx`. J2-A MUST extract the reusable editor components (form, table, alias editor, prerequisite editor) into shared modules and consume them in BOTH surfaces. No copy-paste fork. This mirrors the PYQ onboarding `PyqProvenanceFields` reuse precedent. Shared components live under `app/frontend/src/pages/admin/studyos/editors/` (new directory) and are imported by both `ExamIntelCms.jsx` and the new Syllabus panel.

### C.3 Controls (LOCKED)

- Topic search: `q` param, 300 ms debounce (reuse J1 pattern).
- Level filter: `<select>` over `topic | microtopic | concept`, plus "(all levels)".
- Pagination: 50/page, `limit`+`offset`, Previous/Next, reset to page 1 on subject/search/filter change (reuse J1 pattern).
- Alias editor: list + add (`alias`, `source_context`) + delete-with-reason (8–500 chars).
- Prerequisite editor: list + add (`prerequisite_topic_id`, `relation_type`, `strength`) + delete-with-reason; prerequisite target picker limited to topics within the exam's resolved subjects.
- In-memory control state only (search/filter/page not reflected in URL), matching J1 OD-5.

### C.4 No AdminSafetyBanner (LOCKED)

The Syllabus editor panel must NOT render `AdminSafetyBanner`. Manage Exam is the normal-operation surface. The banner remains exclusive to Advanced Repair.

---

## Section D — Permission contract

**OPERATOR DECISION REQUIRED — this is the pivotal J2 decision.**

The backend editor endpoints (§0.2) are gated on `exam_intelligence.cms` (the Advanced Repair permission). Surfacing them in normal Manage Exam tabs forces a choice:

| Option | Description | Cost | Recommendation |
|---|---|---|---|
| **D-opt-1** | New `exam_intelligence.manage` operate-tier token. Editor endpoints accept `manage` OR `cms`. Add `require_any_permission([...])` helper to `auth.py`. RBAC migration to define/grant the token; audit wiring. | Medium — new token, new auth helper, one migration, grant matrix, audit. | **RECOMMENDED.** Preserves the operate-vs-repair separation the entire IA is built on (§0.1, IA lock §9). Idiomatic (`.manage` matches `exam_eligibility.manage`, `community.manage`, etc.). Governance/RBAC is P0. |
| D-opt-2 | Reuse `exam_intelligence.cms` on the Manage Exam editors. | Low — no backend change. | Collapses the operate/repair tiers: routine editing then requires the repair permission. Weakens the IA. Not recommended. |
| D-opt-3 | Reuse `exam_intelligence.review`. | Low — no new token. | Conflates review-authority with edit-authority (different scopes). Not recommended. |

If **D-opt-1** is approved, the implementation adds:
- `require_any_permission(permissions: list[str])` in `app/core/auth.py` (super_admin bypass; 403 if none present).
- A forward migration defining `exam_intelligence.manage` and granting it per the operator's role matrix.
- The editor endpoints in `admin_exam_intel_cms.py` change from `require_permission(PERM_CMS)` to `require_any_permission([PERM_MANAGE, PERM_CMS])`, so existing `cms` holders retain access and new `manage` holders gain operate-tier access.
- Every new table/grant verified via `pg_policies` / grant matrix before the checklist row is marked complete (migration discipline).

**No implementation of Section D may proceed until one of D-opt-1 / D-opt-2 / D-opt-3 is explicitly approved.**

---

## Section E — Decisions

| ID | Decision | Status |
|---|---|---|
| OD-1 | Placement — editors go into existing tabs (Syllabus for J2-A), no new tab/route/sidebar entry. | **LOCKED** (no-new-surface rule). |
| OD-2 | Permission tier. | **OPERATOR DECISION REQUIRED** — see Section D (D-opt-1 recommended). Requires `require_any_permission` helper + `exam_intelligence.manage` token + migration if D-opt-1. |
| OD-3 | Reuse mandate — extract shared topic/alias/prerequisite editor components; consume in both `ExamIntelCms.jsx` and the Syllabus panel. No fork. | **LOCKED.** |
| OD-4 | Subject resolution — new backend helper endpoint returning the exam's distinct subjects via the `exam_topic_coverage` path. | **LOCKED** (path). Endpoint shape (`GET /exams/{id}/subjects` under the CMS router vs. exam-intelligence router) is an implementation detail; confirm router placement in the PR. |
| OD-5 | Empty-coverage behavior — empty state + link to coverage mapping; never fall back to global subject list. | **LOCKED.** |
| OD-6 | Write-safety — inherit J1 fail-closed `writesBlocked` model keyed on subject resolution. | **LOCKED.** |
| OD-7 | No AdminSafetyBanner in Manage Exam editors. | **LOCKED.** |
| OD-8 | In-memory control state (search/filter/page not in URL). | **LOCKED** (matches J1 OD-5). |
| OD-9 | Delivery slicing — J2-A (Syllabus) first; J2-B (policy flags) and J2-C (cycle entities) each require a gate revision before code. | **LOCKED.** |
| OD-10 | Advanced Repair unchanged — `ExamIntelCms.jsx` retains `exam_intelligence.cms` gate and `collapsible={false}` banner. | **LOCKED.** |
| OD-11 | No new migrations except the RBAC token migration required by D-opt-1 (if approved). No schema changes to topics/aliases/prerequisites. | **LOCKED** (conditional on OD-2). |

---

## Section F — Acceptance tests (J2-A)

### F.1 Subject resolution

```
[ ] Syllabus editor resolves the exam's subjects via exam_topic_coverage (not the global subject list)
[ ] exam with no coverage rows shows the empty state, not a global subject list
[ ] subject resolution state machine: idle → resolving → valid on success, → error on failure
[ ] writesBlocked=true until subjects resolve and match the current :exam_id
```

### F.2 Topic / alias / prerequisite editing

```
[ ] topic list is scoped to a selected subject from the exam's resolved set
[ ] topic search sends q= after 300ms debounce; page resets to 1 on search change
[ ] level filter sends level=; "(all levels)" sends none
[ ] pagination: 50/page, Previous disabled on page 1, Next disabled on last page
[ ] alias add/delete works; delete requires reason 8–500 chars
[ ] prerequisite add/delete works; target picker limited to exam's resolved subjects' topics
[ ] prerequisite self-cycle guard is respected (B→A rejected when A→B exists)
[ ] no POST/PATCH/DELETE fires before subject resolution completes or after it errors
```

### F.3 Reuse / invariants

```
[ ] shared editor components are imported by BOTH ExamIntelCms.jsx and the Syllabus panel (no fork)
[ ] Advanced Repair (ExamIntelCms.jsx) behavior unchanged: exam_intelligence.cms gate + collapsible={false} banner
[ ] Syllabus editor renders NO AdminSafetyBanner
[ ] no new route in navContract test; no sidebar/nav entry added
[ ] permission gate enforced per approved OD-2 option (manage OR cms if D-opt-1)
```

### F.4 Permission (if D-opt-1 approved)

```
[ ] require_any_permission grants access to holders of either manage or cms
[ ] require_any_permission denies (403) users with neither
[ ] super_admin bypasses
[ ] editor endpoints reachable with exam_intelligence.manage; existing exam_intelligence.cms holders retain access
[ ] RBAC token migration: token defined, grant matrix verified via pg_policies / role grants
```

---

## Section G — Files to be changed (J2-A)

| File | Change | Layer |
|---|---|---|
| `app/frontend/src/pages/admin/studyos/editors/` (new) | Extract shared topic/alias/prerequisite editor components. | Frontend |
| `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx` | Consume the extracted shared editor components (replace inline editors). | Frontend |
| `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx` | Add the Syllabus-tab editor panel (subject selector → topic/alias/prereq editors). Serial-owner change. | Frontend |
| `app/frontend/src/pages/admin/exam-workspace/__tests__/…` | New tests covering Section F. | Frontend tests |
| `app/backend/app/api/admin_exam_intel_cms.py` | Add `GET /exams/{id}/subjects` helper (OD-4); change editor endpoints to `require_any_permission` (if D-opt-1). | Backend |
| `app/backend/app/core/auth.py` | Add `require_any_permission` helper (if D-opt-1). | Backend |
| `app/supabase/migrations/<next>_exam_intelligence_manage_permission.sql` | Define + grant `exam_intelligence.manage` (if D-opt-1). | Migration |
| `docs/status/career-copilot-checklist.md` | Update J2 row to reflect this gate + slicing. | Docs |

**Must NOT change:** `AdminShell.jsx`, `adminRoutes.jsx` (no route/nav changes), the topics/aliases/prerequisites table schemas.

---

## Appendix A — Code evidence index

- `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:40–48, 61–150, 165–167` — TAB_ORDER, AdvancedRepairMenu, cms-permission check.
- `app/frontend/src/routes/adminRoutes.jsx:71, 105` — ProtectedRoute role gate, Manage Exam route (no per-permission gate).
- `app/backend/app/api/admin_exam_intel_cms.py:55–56, 2208–2299 (topics), 2330–2395 (aliases), 2410–2479 (prerequisites), 1893–1956 (policy-updates)` — editor endpoints + PERM_CMS/PERM_REVIEW tokens.
- `app/backend/app/core/auth.py:338–361` — `require_permission` single-token semantics.
- `app/supabase/migrations/029_exam_intelligence_taxonomy.sql`, `030_exam_registry_cycles_phases.sql` — subjects/topics, exam_phases/exam_phase_sections(subject_id), exam_topic_coverage(exam_id, topic_id).
- `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §3.2, §6, §7, §9 — Manage Exam role resolution, tab content, deep-link contract, Advanced Repair access model.

---

*Status: DRAFT — OPERATOR APPROVAL REQUIRED. The pivotal open decision is OD-2 (Section D — permission tier; D-opt-1 `exam_intelligence.manage` recommended). J2-A (Syllabus editors) is fully specified; J2-B (policy flags) and J2-C (cycle entities) require a gate revision before implementation. J3 is a separate schema/domain-redesign track and is intentionally NOT covered here — it requires its own contract(s) per sub-item.*
