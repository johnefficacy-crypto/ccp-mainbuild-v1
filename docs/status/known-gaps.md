---
owner: ops
status: live
last_verified_against_code: 2026-06-02
last_modified: 2026-06-02
source_of_truth: code
related_code:
  - app/backend
related_migrations:
  - app/supabase/migrations
review_cadence: per-sprint
---

# Known Gaps

## Production-readiness blockers (verified 2026-06-02)

- No P0 production-readiness blockers from Wave 0 PR-001/PR-002 remain open on the current branch; remaining P1 contract/runtime-hardening items remain below.

## Recently resolved

- **Blog CMS admin API backend auth** — `/api/admin/blogs*` now requires backend auth: reads use `require_admin`, and create/update/publish/archive use `require_permission("blogs.manage")`. Regression tests cover unauthenticated, normal-user, admin-read, and content-admin mutation paths.
- **OCR/Tesseract startup guard** — importing `server.py` is no longer blocked by a missing Tesseract binary; OCR checks happen lazily at OCR call time, and E2E installs `tesseract-ocr` / `tesseract-ocr-eng` for OCR-enabled runtime coverage.
- **Subscription active-row invariant** — migration `164_subscription_active_unique_index.sql` retires duplicate active/past_due rows and recreates `user_subscriptions_user_active_idx` as a unique partial index.

## In-flight

- **AI chat response contract** — `/api/ai/chat` is now durable, but the frontend expects a text `reply` while the backend returns a shaped message object. Align the shape before production.
- **Notification CTA route contract** — alert CTAs need a route matrix so every emitted link lands on an existing frontend route before launch.
- **Placeholder/static runtime surfaces** — `placeholders.py` still mounts static/in-memory fallbacks for non-canonical surfaces and a few static admin endpoints. Gate or remove these in production.

## Real but rough

- **Real LLM provider behind `/api/ai/chat`** — scripted replies today; durable conversation/message persistence exists, but model/provider integration and response-copy accuracy remain pending.
- **Marketplace / community error handling** — several pages silently suppress API failures or keep seed data, which can mask broken production data paths.
- **Downloadable Reports** — PDF generation still queued only; CSV/JSON work inline. Needs a worker.
- **Leadership KPIs** — recompute is admin-triggered today; nightly snapshot job not yet scheduled.
- **Supabase Auth invite delivery** — `/admin/users/create` writes an audit log but doesn't yet send the email invite. Hook this into the existing notifications dispatcher.

## Operational

- Admin governance gap list requires periodic refresh against implementation evidence.
- Scraper operations need a dedicated day-2 runbook and incident handling playbook.
- Notification templates + retries are partially scoped.
- Production deployment evidence is incomplete in-repo: document runtime OS packages, CORS origins, Supabase/Razorpay env, scheduler singleton ownership, and smoke checks.
