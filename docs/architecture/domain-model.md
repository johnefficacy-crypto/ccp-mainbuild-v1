# Database Domain Model: Recruitment vs Exam

_Last updated: 2026-06-17_

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
| `cadence` | `annual`, `recurring`, `irregular`, `one_off`, `unknown` | Expected exam cadence. |
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

## Agent instruction

When generating SQL, migrations, APIs, or React components:

1. Determine whether the feature is about the **exam identity** or a specific
   **recruitment notification**.
2. Use `public.exams` only for exam-master identity workflows.
3. Use `public.recruitments` only for recruitment/notification workflows.
4. Preserve the distinction in naming, docs, tests, and UI copy.
