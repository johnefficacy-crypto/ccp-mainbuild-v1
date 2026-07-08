# Database Domain Model: Recruitment vs Exam

_Last updated: 2026-07-02_

## Current model

Career Copilot now has **two separate canonical database entities**:

| Entity | Table | Purpose |
|---|---|---|
| Recruitment notification | `public.recruitments` | A specific recruitment/cycle notification, including posts, eligibility, dates, and applicant-facing application state. |
| Exam master identity | `public.exams` | The persistent exam identity (for example UPSC CSE or SSC CGL) used by Study OS, exam intelligence, cycles, phases, and target-exam planning. |

These entities are intentionally separate. Do **not** merge them, alias one to
the other, or use one table as a drop-in substitute for the other.

## What changed from the old rule

Older docs said "avoid `public.exams`" because the product originally treated
recruitment notifications as the only canonical exam-like entity. That rule is
now superseded. `public.exams` is a real table and is the canonical
exam-master identity for Study OS and exam-intelligence workflows.

The invariant that remains true is narrower:

- `public.recruitments` is canonical for official recruitment notifications,
  posts, eligibility, application tracking, and scraped-notice promotion.
- `public.exams` is canonical for exam identity, cycles, phases, Study OS
  planning, exam intelligence, and target-exam relationships.

## Canonical mapping

| Product/UI term | Database table / field |
|---|---|
| Exam master identity | `public.exams` |
| Recruitment notification | `public.recruitments` |
| Exam cycle | `public.exam_cycles` |
| Exam phase | `public.exam_phases` |
| Post / vacancy role | `public.posts` |
| Organization / exam body | `public.organizations` |
| User eligibility result | `public.eligibility_results` |
| Saved/tracked recruitment | `public.tracked_recruitments` |
| User target exam | `public.user_targets` |
| User activity | `public.user_events` |
| User application/form activity | `public.form_submissions` |

## Portfolio lanes

`public.exams` has portfolio-management fields used by the operator wizard and
exam-governance surfaces:

| Column | Values | Meaning |
|---|---|---|
| `management_mode` | `core`, `light`, `index_only`, `archive` | Operator lane for how much ongoing attention a live exam receives. |
| `cadence` | `annual`, `biannual`, `recurring`, `irregular`, `one_off`, `unknown` | Expected exam cadence. `biannual` (migration 237) covers exams that run twice a year. |
| `is_active` | boolean | Aspirant visibility / retirement flag. |

Retirement and archive are distinct states:

- `is_active = false` means the exam is retired and hidden from aspirant
  catalogue responses.
- `management_mode = 'archive'` means a live exam is in a low-priority operator
  lane.
- Retiring an exam must not automatically set `management_mode = 'archive'`.

## Naming rule

Frontend and API routes may use `exam` where it improves user clarity.

Allowed examples:

- `/api/exams`
- `/app/study/plan`
- `ExamSummaryCard`
- `exam_id` when the row truly references `public.exams.id`

For recruitment-notification data, use recruitment names explicitly:

- `recruitment_id`
- `public.recruitments`
- `public.posts`
- `public.eligibility_results`

## Migration rule

Before adding a foreign key, decide which entity the table belongs to:

- Use `exam_id references public.exams(id)` for exam identity, cycle/phase,
  Study OS, exam-intelligence, and target-exam data.
- Use `recruitment_id references public.recruitments(id)` for notice, post,
  eligibility, application, scrape-promotion, and notification data.

Do not add both columns unless there is a documented bridge use case and a
clear owner for keeping them consistent.

## Shared content vs applicability vs requirements (added 2026-07-02)

Some content is **canonical and reusable across exams** (e.g. the mock question
bank, English writing prompts). For such content, three scopes are kept
**separate** and must not be conflated:

| Scope | Meaning | Keyed by | Example table |
|---|---|---|---|
| **Content (canonical)** | The reusable item itself | subject → topic → microtopic | `writing_prompts`, `mock_question_bank` |
| **Applicability** | Which exams/families/phases may use the item | `is_global` / `exam_family_id` / `exam_id` / `exam_phase_id` | `writing_prompt_targets` |
| **Requirements** | An exam's official cycle/phase rules | `exam_id` / `exam_cycle_id` / `exam_phase_id` | `exam_descriptive_requirements` |

**Applicability precedence:** `phase-specific > exam-specific > exam-family >
global`.

**Applicability is DEFAULT-DENY (fail-closed).** A canonical item is applicable to
an exam/phase context **IFF** it has an `applicability_status='active'` matching
target: an active `is_global` row (applies everywhere) OR an active
family/exam/phase row matching the context. **No active target ⇒ NOT applicable
(unassigned) — never global.** "Global" is an **explicit** capability
(`is_global=true`, all scope columns NULL), never implied by the absence of rows
(the earlier "no mapping row = global" rule was fail-open and is superseded).
Each row names exactly one of {global, family, exam, phase}. `excluded` rows
subtract a narrower scope from an explicit active broader scope; `pending_review`
rows are inert.

**Applicability is evergreen** — it does **not** carry `exam_cycle_id`.
Canonical content survives cycles; cycle-specific rules belong in the
requirements scope, never the applicability mapping. Legacy prompts that carried
an `exam_cycle_id` are **quarantined** (`pending_review`) by the 214 backfill
rather than converted to evergreen targets.

A shared-content table may either keep a **nullable `exam_id`** (so an item can
exist without belonging to any single exam — e.g. `mock_question_bank.exam_id`,
`references exams(id) on delete set null`, migration 136) **or** carry no
exam-scope column at all, deferring applicability entirely to the mapping table.
Migration 214 takes the latter, stronger stance for `writing_prompts`: the
exam-scope columns (`exam_id`, `exam_cycle_id`, `exam_phase_id`) are **DROPPED**,
and exam applicability is carried **solely** by `writing_prompt_targets`. This
eliminates dual authority (no FK column can contradict a mapping row). Migration
214 backfills a target row for each legacy exam-scoped prompt **before** dropping
the columns (non-cycle prompts → `active`; cycle-scoped prompts → `pending_review`
quarantine with the cycle preserved in `metadata`), so no assignment is lost.
Entity canonicity is preserved — the mapping's `exam_id` still references
`public.exams(id)`.

## Agent instruction

When generating SQL, migrations, APIs, or React components:

1. Determine whether the feature is about the **exam identity** or a specific
   **recruitment notification**.
2. Use `public.exams` only for exam-master identity workflows.
3. Use `public.recruitments` only for recruitment/notification workflows.
4. Preserve the distinction in naming, docs, tests, and UI copy.
