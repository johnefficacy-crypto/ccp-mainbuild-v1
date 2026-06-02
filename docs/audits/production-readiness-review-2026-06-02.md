---
owner: ops
status: live
last_verified_against_code: 2026-06-02
source_of_truth: code
related_code:
  - app/backend/server.py
  - app/backend/app/api
  - app/frontend/src
  - app/supabase/migrations
related_migrations:
  - app/supabase/migrations/014_payments_runtime_schema.sql
  - app/supabase/migrations/098_ai_chat.sql
  - app/supabase/migrations/151_canonical_is_admin_and_force_rls.sql
review_cadence: per-release
---

# Production Readiness Review — 2026-06-02

This audit records the senior full-stack production-readiness review performed
against commit `3b16add077b7e51dbccc426f56e620371ce26096`.

## Verdict

- **Production-ready:** No.
- **Staging-ready:** No, unless the P0 blockers below are fixed first.

Confirmed blockers and gaps are based on repository files only. Items not proven
from code are labelled as not confirmed.

## P0 blockers

### P0-1 — `/api/admin/blogs*` CMS routes are not backend-protected

**Evidence**

- `app/backend/server.py` registers `admin_blogs_router` under `/api`.
- `app/backend/app/api/blogs.py` mounts the admin router at `/admin/blogs`.
- `app/backend/app/api/blogs.py` exposes admin list/read/create/update/publish/archive handlers without `Depends(require_admin)`, `Depends(require_permission(...))`, or an equivalent backend auth dependency.
- `app/frontend/src/pages/admin/Blogs.jsx` calls those same `/api/admin/blogs*` routes from the admin Blog CMS UI.

**Risk**

An unauthenticated caller can create, edit, publish, archive, and list CMS
content through service-role-backed Supabase operations. This is a direct content
integrity and reputational risk.

**Exact fix**

Add a backend auth dependency to every `admin_router` route in
`app/backend/app/api/blogs.py`. Prefer `Depends(require_permission("blogs.manage"))`
if the permission exists; otherwise use `Depends(require_admin)` until a granular
permission is introduced.

**Suggested test**

Add backend route tests asserting unauthenticated requests to `GET /api/admin/blogs`,
`POST /api/admin/blogs`, `PUT /api/admin/blogs/{id}`, and
`POST /api/admin/blogs/{id}/publish` return `401`, non-admin authenticated users
return `403`, and authorized admins can perform the operations.

### P0-2 — Backend can fail at import/startup when Tesseract is missing

**Evidence**

- `app/backend/server.py` imports `admin_exam_intel_documents_router` at module import time.
- `app/backend/app/api/admin_exam_intel_documents.py` imports the exam-intelligence extraction dispatch path.
- `app/backend/app/exam_intelligence/extraction/ocr.py` calls `pytesseract.get_tesseract_version()` at import time and raises `RuntimeError` when the `tesseract` binary is not on `PATH`.
- `.github/workflows/ci.yml` installs `tesseract-ocr` and `tesseract-ocr-eng` for backend CI, but `.github/workflows/e2e.yml` starts the backend without the equivalent system-dependency install.

**Risk**

Any staging/production image that lacks the Tesseract OS package cannot import
`server.py`; the API process exits before `/api/health` can serve.

**Exact fix**

Add the OCR OS packages to the deploy image/runtime and to the E2E workflow, or
lazy-load OCR-specific modules so non-OCR routes can boot even when OCR is
disabled.

**Suggested test**

Add a backend boot check such as `python -c "import server; print('ok')"` in CI
and a staging smoke test that starts `uvicorn server:app` and checks `/api/health`.

## P1 gaps

### P1-1 — AI chat frontend/backend response contract mismatch

**Frontend caller**

- `app/frontend/src/pages/AIChat.jsx` calls `POST /api/ai/chat` and stores
  `r.reply` directly as renderable text.

**Backend route**

- `app/backend/app/api/ai.py` returns `reply: _shape_msg(bot_msg[0])`, a shaped
  message object, plus `user_message`.

**Mismatch / risk**

The UI expects a string-like reply but receives an object, so assistant output
can render as `[object Object]` or otherwise break the message display.

**Exact fix**

Either return `reply_text` / string `reply` from the backend or update the
frontend to render `r.reply.content || r.reply.message || ""`.

### P1-2 — Subscription single-active invariant is not enforced by schema

**Evidence**

- `app/backend/app/api/payments.py` says a partial unique index prevents two
  active/past_due subscriptions for one user.
- `app/supabase/migrations/014_payments_runtime_schema.sql` creates a plain
  `user_subscriptions_user_active_idx`, not a unique index.

**Risk**

Concurrent checkout verification, webhook replay, or manual writes can leave
multiple active/past_due rows because the schema does not enforce the backend's
claimed invariant.

**Exact fix**

Add a forward migration that resolves existing duplicates, then creates a unique
partial index on `user_id` where `status in ('active','past_due')`.

### P1-3 — Placeholder/static/in-memory production surfaces remain mounted

**Evidence**

- `app/backend/app/api/placeholders.py` documents that placeholder routers keep
  screens navigable with deterministic static/in-memory data until real
  Supabase-backed implementations replace them.
- The same file still defines process-local stores for saved items, tracker
  items, focus sessions, mock logs, profile extras, community threads, group
  members, partner requests, mentor bookings, and AI-related legacy state.
- Static admin endpoints remain mounted for sources, scraper runs, eligibility
  queue, and notification toggle.

**Risk**

Process-local state is lost on restart and diverges across backend instances.
Static data can also mask missing real data and produce false confidence during
operator review.

**Exact fix**

Feature-gate or disable placeholder routes in production and replace promoted
surfaces with Supabase-backed handlers before deployment.

### P1-4 — User-facing surfaces silently hide API failures

**Evidence**

- `app/frontend/src/pages/Marketplace.jsx` suppresses resource/provider/affiliate
  load failures with empty `.catch(() => {})` handlers.
- `app/frontend/src/pages/ResourceDetail.jsx` maps access-check failure to
  `{ state: "not_enrolled" }`.
- `app/frontend/src/features/community/PartnersScreen.jsx` keeps seeded partner
  data on API failure.
- `app/frontend/src/pages/AIChat.jsx` suppresses guidance failure.

**Risk**

Users and operators cannot distinguish "no data" from "backend broken".

**Exact fix**

Render explicit error states and reserve seed/static fallbacks for demo or
prototype mode only.

### P1-5 — Deployment/config readiness is incomplete

**Evidence**

- `app/backend/app/core/config.py` defaults CORS to localhost origins only.
- `app/backend/.env.example` documents that production must set
  `ENABLE_SCHEDULER=true` on exactly one backend instance.
- No Dockerfile, Render/Fly/Railway/Vercel deployment manifest, or production
  process file was found in the inspected repo paths. This is **not confirmed**
  as absent from all external infrastructure; the missing evidence is a deploy
  manifest or platform runbook in the repo.

**Risk**

Production readiness depends on external, undocumented platform settings for
CORS, scheduler singleton behavior, OCR packages, Supabase, Razorpay, and app URLs.

**Exact fix**

Commit a deploy manifest or runtime runbook that installs OS dependencies,
configures CORS and env vars, starts the backend/frontend, and documents the
single scheduler instance.

## Critical backend/frontend contract matrix

| Area | Endpoint | Frontend caller | Backend owner | Status | Required action |
|---|---|---|---|---|---|
| Auth | `GET /api/auth/me` | `app/frontend/src/lib/authContext.jsx` | `app/backend/app/api/auth.py` | OK | Keep backend role authority. |
| Admin RBAC | `/api/admin/users*` | `app/frontend/src/pages/admin/RBAC.jsx` | `app/backend/app/api/admin_ops.py` | OK | Keep `require_admin`/`require_super_admin`. |
| Blog CMS | `/api/admin/blogs*` | `app/frontend/src/pages/admin/Blogs.jsx` | `app/backend/app/api/blogs.py` | **P0 security mismatch** | Add backend auth dependency. |
| AI chat | `POST /api/ai/chat` | `app/frontend/src/pages/AIChat.jsx` | `app/backend/app/api/ai.py` | **P1 shape mismatch** | Align `reply` shape. |
| Pricing | `/api/plans`, `/api/payments/*` | `app/frontend/src/pages/Pricing.jsx` | `app/backend/app/api/payments.py` | Risky | Add schema uniqueness for active subs. |
| Marketplace | `/api/marketplace/resources*` | `app/frontend/src/pages/Marketplace.jsx`, `app/frontend/src/pages/ResourceDetail.jsx` | `app/backend/app/api/marketplace.py` | OK but hidden failures | Add visible error states. |
| Community partner | `/api/community/partner*` | `app/frontend/src/features/community/PartnersScreen.jsx` | `app/backend/app/api/community_runtime.py` | Risky but adapter-aware | Remove seed fallback in prod. |
| Applications | `GET /api/applications/me` | `app/frontend/src/features/dashboard/hooks/useDashboardData.js` | `app/backend/app/api/canonical.py` | OK | Keep contract test. |
| Profile completion | `GET /api/profile/completion` | `app/frontend/src/features/dashboard/hooks/useDashboardData.js` | `app/backend/app/api/canonical.py` | OK | Keep contract test. |
| Copyright | `/api/copyright/submit`, `/api/admin/copyright*` | public/admin copyright pages | `app/backend/app/api/admin_copyright.py` | OK, abuse controls not confirmed | Add rate-limit/captcha evidence. |
| Moderation | `/api/admin/moderation*` | admin moderation route | `app/backend/app/api/admin_moderation.py` | OK | Keep moderator/admin permission gate. |

## Security/RBAC notes

- Confirmed P0: unauthenticated Blog CMS admin API.
- Confirmed positive controls: admin RBAC routes use backend `require_admin` and
  `require_super_admin`; payment and marketplace webhooks verify Razorpay
  signatures; copyright/admin moderation routes have backend role/permission
  gates.
- Not confirmed: repo-wide rate limiting, CAPTCHA on public non-auth API routes,
  and production secret scanning evidence.

## Data/schema notes

- Confirmed mismatch: active subscription uniqueness is documented in backend
  comments but not enforced by the migration.
- Confirmed alignment: migration `151` makes `auth.users.raw_app_meta_data.role`
  the canonical admin source, matching backend role direction.
- Confirmed persistence: AI conversations/messages have durable tables and RLS in
  migration `098`; the remaining AI gap is response shape and scripted behavior,
  not persistence.

## Recommended fix order

### Day 0

1. Protect `/api/admin/blogs*` with backend auth.
2. Make backend boot independent of missing OCR binaries or install Tesseract in
   every CI/staging/production runtime.
3. Add smoke tests for admin auth and backend import/startup.

### Day 1–2

1. Fix AI chat response shape.
2. Add unique active-subscription schema guard.
3. Replace silent frontend catches with visible error states.
4. Production-gate placeholder routes.
5. Add deploy/runtime documentation for CORS, env, scheduler, OCR, Supabase, and
   Razorpay.

### Later

1. Add backend/frontend contract tests for scraper, eligibility, marketplace,
   payments, profile/onboarding, community, blogs/CMS, notifications, reports,
   and admin moderation/copyright.
2. Add route inventory tests proving every `/api/admin/*` route has backend auth.
3. Add public route abuse controls and monitoring evidence.
