---
owner: ops
status: amended
last_verified_against_code: 2026-06-12
source_of_truth: code
related_code:
  - app/backend
related_migrations:
  - app/supabase/migrations
review_cadence: per-sprint
---

# ADR 0005: Recruitments are canonical; exams are a separate master-identity entity

- Status: Accepted (amended 2026-06-12)
- Date: 2026-05-16

## Original decision

Use `public.recruitments` and `recruitment_id` as canonical keys for
recruitment/notification data; frontend may display exam terminology.

## Amendment (2026-06-12)

`public.exams` is now a live, first-class table — not just UI vocabulary.
It represents the persistent exam-master identity (SSC CGL, UPSC CSE, etc.)
that recruitment cycles, exam phases, study plans, and aspirant targets all
reference. The two entities serve different purposes:

- `public.recruitments` — a specific recruitment notification (year, posts,
  eligibility rules, scraper-origin tracking). Canonical for eligibility.
- `public.exams` — the durable exam identity (exam_type, slug, portfolio
  management_mode/cadence). Canonical for Study OS and exam intelligence.

The original intent of this ADR — do not conflate product-language "exam"
with DB schema — remains valid. What has changed: the prohibition on
`public.exams` no longer applies. Do not merge `public.exams` into
`public.recruitments` or vice versa; they are distinct entities at different
lifecycle scopes.
