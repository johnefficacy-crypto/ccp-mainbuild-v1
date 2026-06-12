# Database Domain Model: Recruitment vs Exam

_Last updated: 2026-06-12_

## Dual-entity model (current)

Career Copilot has **two distinct canonical entities** at the DB level:

| Entity | Table | Purpose |
|---|---|---|
| Recruitment notification | `public.recruitments` | A specific recruitment cycle/notification (year, posts, eligibility) |
| Exam master identity | `public.exams` | The persistent exam (SSC CGL, UPSC CSE, …) that recruitments belong to |

These are **separate entities**. Do not conflate or merge them. `public.exams`
is a live table with FK dependents: `exam_cycles`, `exam_phases`, `study_plans`,
exam-intelligence tables, and aspirant target tables all reference `exams.id`.

The word `exam` may be used freely in frontend/UI copy. At the database level,
always be explicit about which table you mean.

> **Historical note:** The original guidance ("do not introduce public.exams")
> was correct at project start. It was superseded when the exam-master table was
> introduced to support Study OS and exam-intelligence. ADR 0005 remains valid
> for its core intent — recruitments are canonical for notification/eligibility
> data — but the prohibition on `public.exams` no longer applies.

## Canonical entity model

| Product/UI term | Database table / field |
|---|---|
| Exam (master identity) | `public.exams` |
| Recruitment notification | `public.recruitments` |
| Exam cycle | `public.exam_cycles` |
| Exam phase | `public.exam_phases` |
| Post / vacancy role | `public.posts` |
| Organization / exam body | `public.organizations` |
| User eligibility result | `public.eligibility_results` |
| Saved/tracked exam | `public.tracked_recruitments` |
| User target exam | `public.user_targets` |
| User activity | `public.user_events` |
| User application/form activity | `public.form_submissions` |

## Portfolio lanes (migration 172, merged 2026-06)

`public.exams` has two nullable portfolio-management columns:

| Column | Type | Values | Default |
|---|---|---|---|
| `management_mode` | enum | `core`, `light`, `index_only`, `archive` | `light` (on create) |
| `cadence` | enum | `annual`, `recurring`, `irregular`, `one_off`, `unknown` | `unknown` (on create) |

**Retire semantics:** `is_active = false` = retired (hidden from aspirants).
`management_mode = 'archive'` = low-priority lane for exams that are still
LIVE. These are **independent** — retiring an exam NEVER writes `archive`.

## Naming rule

Frontend and API routes may use `exam` where it improves user clarity.

Allowed examples:

- `/dashboard/exams`
- `/api/exams/summary`
- `ExamSummaryCard`
- `user_exam_summary`

For recruitment-specific data, use:

- `recruitment_id`
- `public.recruitments`
- `public.posts`
- `public.eligibility_results`

## Migration dependency order

Telemetry must exist before user state views.

Correct order:

```txt
027_user_events_and_form_submissions.sql
028_user_recruitment_state.sql
029_exam_summary_support.sql
```

Reason:

1. `user_recruitment_state` depends on `public.user_events`.
2. `exam_summary` / `user_exam_summary` depends on `public.user_recruitment_state`.
3. `public.exams` does not exist, so exam summary views must be built on `public.recruitments`.

## Do not do this

Do not reference:

```sql
public.exams
```

Do not create a duplicate `public.exams` table just to satisfy old migration code.

Do not use `exam_id` as the main foreign key for new tables.

## Preferred pattern

Use:

```sql
recruitment_id uuid references public.recruitments(id)
```

If legacy compatibility is required, `exam_id` may temporarily exist as a nullable field, but it should not be the source of truth.

## AI / agent instruction

When generating SQL, migrations, APIs, or React components for Career Copilot:

- Treat `recruitments` as the canonical exam/recruitment entity.
- Use `recruitment_id` for joins and foreign keys.
- Use `exam` only as a user-facing label.
- Never assume `public.exams` exists.
- Check migration dependency order before creating views or materialized views.

## Practical project rule

```txt
Database = recruitment
Frontend language = exam
Foreign key = recruitment_id
Avoid = public.exams
```
