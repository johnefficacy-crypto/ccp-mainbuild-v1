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

- **Unauthenticated Blog CMS admin API** — `/api/admin/blogs*` is registered as an admin surface but the backend routes in `app/backend/app/api/blogs.py` do not require `require_admin`, `require_permission`, or an equivalent dependency. See [production readiness review](../audits/production-readiness-review-2026-06-02.md).
- **Backend startup depends on the Tesseract OS binary** — `server.py` imports the exam-intelligence document router, which reaches `ocr.py`; `ocr.py` raises at import time if `tesseract` is missing. Ensure every runtime image and E2E install the OS package, or lazy-load OCR. See [production readiness review](../audits/production-readiness-review-2026-06-02.md).

## In-flight

- **AI chat response contract** — `/api/ai/chat` is now durable, but the frontend expects a text `reply` while the backend returns a shaped message object. Align the shape before production.
- **Placeholder/static runtime surfaces** — `placeholders.py` still mounts static/in-memory fallbacks for non-canonical surfaces and a few static admin endpoints. Gate or remove these in production.

## Real but rough

- **Real LLM provider behind `/api/ai/chat`** — scripted replies today; durable conversation/message persistence exists, but model/provider integration and response-copy accuracy remain pending.
- **Marketplace / community error handling** — several pages silently suppress API failures or keep seed data, which can mask broken production data paths.
- **Subscription active-row invariant** — backend comments describe a unique active-subscription guard, but the current migration creates a non-unique index. Add a forward migration for a unique partial index.
- **Downloadable Reports** — PDF generation still queued only; CSV/JSON work inline. Needs a worker.
- **Leadership KPIs** — recompute is admin-triggered today; nightly snapshot job not yet scheduled.
- **Supabase Auth invite delivery** — `/admin/users/create` writes an audit log but doesn't yet send the email invite. Hook this into the existing notifications dispatcher.

## Operational

- Admin governance gap list requires periodic refresh against implementation evidence.
- Scraper operations need a dedicated day-2 runbook and incident handling playbook.
- Notification templates + retries are partially scoped.
- Production deployment evidence is incomplete in-repo: document runtime OS packages, CORS origins, Supabase/Razorpay env, scheduler singleton ownership, and smoke checks.
