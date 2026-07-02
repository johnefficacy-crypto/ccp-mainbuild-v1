# Content Studio — Architecture Contract

**Status:** DESIGN DECISION (2026-07-02). Encodes the content-scoping revision
that accompanies migration `214_writing_prompt_content_scoping.sql`.
**Supersedes:** the "prompts authored in Exam Workspace CMS" instruction
(§17 of `docs/architecture/english-writing-practice.md`) and the
"PYQ Workbench | Prompt Bank | Updates" tab plan for `ExamWorkspace`.
**Scope of this doc:** architecture + IA only. The resolver and the Content
Studio UI are **later PRs** (see §7 Follow-ups). This PR ships docs + schema.

---

## 1. Why Content Studio exists

Career Copilot has multiple kinds of **canonical, reusable content** —
objective questions, writing prompts, grammar drills, quant/reasoning drills,
passage sets, descriptive prompts. Historically these were being pulled toward
per-exam ownership (e.g. "author prompts inside Exam Workspace"). That is wrong:
canonical content is **subject-scoped and reusable across many exams**, so it
must not be owned by any single exam surface.

**Content Studio** is the single consolidated admin surface that creates and
governs canonical content. Exam surfaces *consume* it; they do not own it.

### 1.1 Division of responsibility (the load-bearing rule)

| Surface | Owns | Does NOT do |
|---|---|---|
| **Content Studio** | Create + govern canonical content (subject-scoped); run the review lifecycle | Does not decide exam-specific official rules |
| **Manage Exam** | Applicability (assign content to exams/families/phases) + practice-content coverage | Does NOT own or edit canonical content |
| **Study OS** | Select + deliver verified content to aspirants | Does not author or assign |

One sentence: **Content Studio = create/govern; Manage Exam = applicability +
coverage; Study OS = select/deliver.**

---

## 2. The three scopes (shared with domain-model.md and EWP §17)

| Scope | Storage | Keyed by |
|---|---|---|
| **Content (canonical)** | `writing_prompts`, `mock_question_bank`, … | `subject_id` → `topic_id` → `microtopic_id` |
| **Applicability** | `writing_prompt_targets` (migration 214) | `exam_family_id` / `exam_id` / `exam_phase_id` |
| **Requirements** | `exam_descriptive_requirements` | `exam_id` / `exam_cycle_id` / `exam_phase_id` |

`writing_prompts` carries **no exam-scope column** — migration 214 **drops**
`exam_id`, `exam_cycle_id`, and `exam_phase_id`. `writing_prompt_targets` is the
**sole** applicability authority (no dual authority; nothing on the content row
can contradict a mapping row).

Applicability precedence: `phase-specific > exam-specific > exam-family >
globally-applicable (baseline)`. Applicability is **evergreen** — no
`exam_cycle_id`; cycle rules stay in requirements.

**Global-with-exclusions (baseline + overrides — the single precise rule).** A
prompt is globally applicable as its **baseline** when it has no
`applicability_status='active'` target row restricting it to a narrower scope
("no target rows at all" is the trivial case). An `excluded` row for scope X is
an **override** that subtracts X only, leaving the global baseline intact
elsewhere — so a global prompt may carry `excluded` rows without contradiction.
Each target row names **exactly one** scope (`CHECK num_nonnulls(...) = 1`), and
a null-safe unique index makes `(prompt, scope)` unique, so statuses are never
self-contradictory for a prompt+scope.

Verified-only reads are preserved end to end: aspirant/planner surfaces read
only `reviewer_status='verified' AND is_active=true` content, resolved through
the applicability model server-side. Raw applicability rows are not exposed to
clients (RLS: service-role-managed, no client allow policy).

---

## 3. Surface consolidation — no-new-surface justification

The no-new-surface rule
(`docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` §1.2, LOCKED):

> **No new top-level destination unless it removes at least two existing
> top-level destinations.**

Content Studio **removes 3** existing admin "Mock Content" top-level
destinations and **adds 1**:

| Removed (today) | Route |
|---|---|
| Question Bank | `/admin/mocks/questions` |
| Review Queue | `/admin/mocks/review-queue` |
| Bulk Import | `/admin/mocks/import` |

→ replaced by a single **Content Studio** destination. Net change: −3 +1.
This **satisfies** the rule (removes ≥ 2, adds 1). The routing/nav change is a
later serial-delivery PR (§7), owned by one owner per the serial-delivery rule.

### 3.1 Route contract (canonical route + back-compat redirects)

Canonical destination (one top-level route, tabs as query param):

```
/admin/content-studio?tab=library|review-queue|bulk-import|exam-assignments
```

`tab=library` is the default when `tab` is absent. The three removed Mock
Content routes **redirect** (301/client-side) to the equivalent tab, preserving
deep links and back-button history:

| Legacy route (removed) | Redirects to |
|---|---|
| `/admin/mocks/questions`     | `/admin/content-studio?tab=library` |
| `/admin/mocks/review-queue`  | `/admin/content-studio?tab=review-queue` |
| `/admin/mocks/import`        | `/admin/content-studio?tab=bulk-import` |

Query params on the legacy routes (e.g. filters, `exam_id`, pagination) are
carried through the redirect. The Manage-Exam deep link (§5) targets the
canonical route: `/admin/content-studio?tab=exam-assignments&exam_id=…`.
Implementing these routes/redirects is the serial-delivery UI PR (§7), not this
docs+migration PR.

---

## 4. Content Studio internal IA (one content system, subject as a filter)

Content Studio is **one** content system, not a family of per-subject products.
There is explicitly **NO** separate `/admin/english`, `/admin/quant`, or
`/admin/reasoning` product.

**Content types** (the `content_type` facet):
`objective_question`, `writing_prompt`, `grammar_drill`, `quant_drill`,
`reasoning_puzzle`, `passage_set`, `descriptive_prompt`.

**Subjects** (a filter, not a separate app): English, Quant, Reasoning, GA, …

Sub-surfaces (drill-in tabs inside the single destination — NOT new top-level
destinations):

| Tab | Purpose |
|---|---|
| **Library** | Browse/create/govern canonical content; **subject is a filter**, content type is a facet |
| **Review Queue** | The `pending → verified \| rejected \| needs_correction` lifecycle (replaces `/admin/mocks/review-queue`) |
| **Bulk Import** | Import canonical items (replaces `/admin/mocks/import`) |
| **Exam Assignments** | Manage applicability (`writing_prompt_targets` and analogous mappings) |

---

## 5. How Manage Exam consumes Content Studio

Manage Exam does **not** own or edit canonical content. It shows a
**Practice-Content-Coverage summary** (how many verified, active, applicable
items exist per subject/microtopic for the exam/cycle/phase) and links out to
Content Studio for assignment:

```
Manage assignments → /admin/content-studio?tab=exam-assignments&exam_id=…&phase=…
```

The deep link pre-filters Content Studio's Exam Assignments tab to that context.
Editing content or its applicability happens in Content Studio; Manage Exam only
reads coverage and hands off.

---

## 6. Explicit withdrawals (locked-decision supersession)

These earlier instructions are **withdrawn**, explicitly and with a dated note
rather than silently:

1. **"Prompts authored as embedded content in the Exam Workspace CMS / no new
   admin destination"** (EWP §17, original). Superseded: canonical prompts are
   subject-scoped and live in Content Studio.
2. **The `ExamWorkspace` "PYQ Workbench | Prompt Bank | Updates" tab plan.**
   The **Prompt Bank does NOT live in the exam-scoped `ExamWorkspace`.** Prompt
   authoring/governance is a Content Studio (Library, subject=English filter)
   responsibility. `ExamWorkspace` may show coverage + an assignment hand-off,
   but not a prompt-authoring tab.

Any residual "Prompt Bank tab in Exam Workspace" frontend task is **PAUSED /
SUPERSEDED** by this decision (tracked in the checklist).

---

## 7. Follow-ups (explicitly later PRs — NOT in this PR)

This PR is docs + one migration + checklist only. Deferred:

1. **Applicability resolver** — service-role function that, given
   `(exam_id, exam_phase_id)`, returns the applicable verified/active prompt set
   using the §2 precedence. Consumes `writing_prompt_targets`. **The resolver PR
   MUST also replace/remove `writing_prompts_public_read`** (migration 205),
   which currently exposes verified+active prompts directly to clients and would
   bypass the applicability model. Until then, **no prompt may be activated for
   aspirant launch** — see the activation gate in the checklist.
2. **Content Studio UI** — the consolidated admin surface (Library / Review
   Queue / Bulk Import / Exam Assignments) and the nav consolidation that
   removes the 3 Mock Content destinations. Serial-delivery, single owner
   (touches routing/nav/AdminShell).
3. **Manage Exam coverage panel + deep link** into Content Studio.
4. **Prompt-bank seed** (~270 items) authored/governed in Content Studio.

No frontend, backend endpoint, route, or seed data ships in this PR.
