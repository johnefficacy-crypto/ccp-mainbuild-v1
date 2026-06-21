---
owner: ops
status: live
last_verified_against_code: 2026-06-17
source_of_truth: code
related_code:
  - app/backend
  - app/frontend
related_migrations:
  - app/supabase/migrations
review_cadence: per-sprint
---

# Career Copilot — AI/Agent Context

_Last updated: 2026-06-17 — docs cleanup after code verification_

This file gives AI agents and new contributors the minimum context needed to work effectively on this codebase. Read this first, then follow the links for depth.

---

## What this product is

Career Copilot is an eligibility-first, recruitment-discovery and exam-preparation operating system for Indian government-job aspirants.

It helps aspirants:

1. Discover official government recruitment notifications from verified sources.
2. Check personalized eligibility matched to their profile.
3. Understand exams via PYQ trends, cutoff analysis, vacancy history, and competition metrics.
4. Prepare using Study OS plans, mock-test tracking, focus sessions, and review loops.
5. Track applications, deadlines, admit cards, and results.
6. Connect with peers, accountability partners, and verified mentors.

See [product/vision.md](product/vision.md) for product positioning and [architecture/domain-model.md](architecture/domain-model.md) for the current recruitment-vs-exam entity model.

---

## Non-negotiable domain rules

Career Copilot has two separate canonical DB entities:

```txt
Recruitment notification = public.recruitments
Exam master identity     = public.exams
```

- Use `public.recruitments` for official notices, posts, eligibility, application tracking, and scrape promotion.
- Use `public.exams` for exam-master identity, cycles, phases, Study OS plans, exam intelligence, and user target exams.
- Do not conflate the two entities or add both `exam_id` and `recruitment_id` without a documented bridge use case.
- Eligibility verdicts must come from the deterministic engine, not AI or heuristics.
- AI may propose, summarize, score, and explain. AI must not publish, verify, or override deterministic gates.

See [architecture/domain-model.md](architecture/domain-model.md).

---

## Current implementation snapshot

### Operational surfaces verified in code

- Deterministic eligibility engine and recompute flows.
- Scraper ingestion, queue review, trust-gated promotion, and admin scrape workflows.
- Notifications feed/preferences/admin kill switch with APScheduler jobs gated by `ENABLE_SCHEDULER`.
- Payments and subscriptions through Razorpay-backed backend routes.
- Study OS mission control, study plan, focus timer, mocks, mistakes, flashcards, revision, notes, and report endpoints.
- Exam-intelligence CMS/review APIs, document upload/extraction routes, and Study OS planner-facing intelligence reads.
- Community/forum runtime, marketplace catalogue, accountability partners/groups, mentor booking routes, moderation, copyright, blogs, KPIs, and admin overview.
- AI chat persistence in `ai_conversations` / `ai_messages`; responses are still scripted until a real LLM provider is wired.

### Still rough / do not overstate

- AI chat returns a shaped message object in `reply`; frontend contracts that expect `reply` as plain text need alignment.
- Placeholder routes are still mounted for a small set of static/demo admin paths, although many formerly shadowed endpoints now have real routers registered before placeholders.
- Downloadable reports support inline CSV/JSON; PDF worker/storage remains pending.
- KPI recompute is admin-triggered; a nightly snapshot job is still pending.
- Supabase Auth invite email delivery is not yet wired behind admin user creation.

See [status/known-gaps.md](status/known-gaps.md) for the current gap list.

---

## Governance rules that apply to all code changes

- Governance before automation. RBAC, audit, and eligibility queue monitoring are P0.
- Admin route visibility is not enough. Backend routes/actions must enforce permissions independently.
- Admin mutations should write audit rows where the relevant audit utility/table exists.
- Eligibility-triggered alerts must come from engine verdicts, not blind broadcasts.
- Official sources are canonical. Aggregator URLs must never be user-facing primary URLs.
- AI-generated content in admin flows must pass the AI action policy layer before use.

See [engineering/admin-strategy.md](engineering/admin-strategy.md).

---

## Before editing code — read order

1. `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` when present.
2. This file (`docs/00-ai-context.md`).
3. [architecture/domain-model.md](architecture/domain-model.md).
4. [status/known-gaps.md](status/known-gaps.md).
5. [operations/runbook.md](operations/runbook.md).
6. The module-specific doc if one exists.

---

## Verification commands

For code changes, run the relevant backend/frontend tests and linters for the touched surface. For docs-only changes, run lightweight link/file-existence checks instead of the full code test suite.
