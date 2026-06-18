---
owner: ops
status: live
last_verified_against_code: 2026-06-17
source_of_truth: code
related_code:
  - app/backend
related_migrations:
  - app/supabase/migrations
review_cadence: per-sprint
---

# Career Copilot — Docs

_Last updated: 2026-06-17_

This directory is the single source of context for the product, engineering strategy, and operations of Career Copilot.

## How to navigate

| If you want to know... | Read... |
|---|---|
| What the product is and where it is going | [product/vision.md](product/vision.md) |
| The full phased build roadmap | [product/roadmap.md](product/roadmap.md) |
| Pricing tiers and paywall design | [product/monetization.md](product/monetization.md) |
| Forum, mentor sessions, and community strategy | [product/community-platform.md](product/community-platform.md) |
| Database canonical rules (recruitment vs exam-master identity) | [architecture/domain-model.md](architecture/domain-model.md) |
| Admin, RBAC, and automation strategy | [engineering/admin-strategy.md](engineering/admin-strategy.md) |
| AI governance, personalization, and PYQ strategy | [engineering/ai-strategy.md](engineering/ai-strategy.md) |
| Source taxonomy and scraper intelligence | [scraping/source-intelligence.md](scraping/source-intelligence.md) |
| Mock Engine v2 ↔ Study OS integration (decisions + plan) | [study_os/mock-engine-v2-study-os-integration.md](study_os/mock-engine-v2-study-os-integration.md) |
| Current implementation status and gaps | [status/known-gaps.md](status/known-gaps.md) |
| How to operate the system (runbook) | [operations/runbook.md](operations/runbook.md) |
| Manual click-through review discipline (process) | [process/click_through_review.md](process/click_through_review.md) |
| Production readiness blockers and contract risks | [audits/production-readiness-review-2026-06-02.md](audits/production-readiness-review-2026-06-02.md) |
| SSC CGL generated-mock off/shadow validation (failed; live blocked) | [audits/ssc-cgl-generated-mock-shadow-validation-2026-06-18.md](audits/ssc-cgl-generated-mock-shadow-validation-2026-06-18.md) |
| AI/agent context summary | [00-ai-context.md](00-ai-context.md) |

## Doc types

- **Product docs** — live strategy documents. Updated as direction changes.
- **Engineering docs** — technical decisions and architectural constraints. Updated when a decision changes.
- **Operations docs** — current implementation state and procedures. Updated every sprint.
- **History** — immutable sprint reports and strategy chat summaries. Never edited after filing.

## Non-negotiable domain rules

```
Recruitment notification = public.recruitments
Exam master identity     = public.exams
Do not conflate the two entities
```

See [architecture/domain-model.md](architecture/domain-model.md).

## Strategic rule

```
Trust > Speed
Control > Automation
Determinism > Heuristics
```

See [engineering/admin-strategy.md](engineering/admin-strategy.md).

