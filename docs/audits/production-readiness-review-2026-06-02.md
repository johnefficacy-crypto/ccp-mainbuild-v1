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

## Parallel execution-ready PR plan

Use this plan to split the production-readiness work into independently
reviewable PRs. Branch names are descriptive by design so the merge log remains
readable.

### Wave 0 — hard blockers

#### PR-001 — Protect Blog/CMS admin API

- **Branch:** `fix/admin-blog-auth`
- **Priority:** P0
- **Parallel:** yes
- **Files:** `app/backend/app/api/blogs.py`, `app/backend/tests/test_blogs_admin_auth.py`
- **Evidence:** `server.py` registers `admin_blogs_router`; the Codex review and
  this audit confirm `/api/admin/blogs*` admin routes lack backend auth.
- **Work:** Add `Depends(require_admin)` or `Depends(require_permission("blogs.manage"))`
  to every admin blog route.
- **Acceptance:** unauthenticated callers get 401/403; normal users get 403;
  admins can list/read; authorized content admins can create/update/publish/archive;
  tests cover `GET`, `POST`, `PUT`, `publish`, and `archive`.

#### PR-002 — Make backend startup independent of missing Tesseract

- **Branch:** `fix/ocr-startup-guard`
- **Priority:** P0
- **Parallel:** yes
- **Files:** `app/backend/server.py`, `app/backend/app/api/admin_exam_intel_documents.py`,
  `app/backend/app/exam_intelligence/extraction/ocr.py`, `.github/workflows/ci.yml`,
  `.github/workflows/e2e.yml` if present, backend deploy manifest if present,
  `app/backend/tests/test_server_import.py`
- **Evidence:** `server.py` imports the document router at module import time;
  `ocr.py` calls `pytesseract.get_tesseract_version()` at import and raises when
  Tesseract is missing.
- **Work:** Prefer lazy-loading OCR inside OCR-specific extraction paths rather
  than server import. Also install `tesseract-ocr` and `tesseract-ocr-eng` in any
  runtime where OCR is enabled.
- **Acceptance:** `python -c "import server; print('ok')"` passes without Tesseract
  when OCR is disabled; OCR endpoint/job returns a clear 503/config error when the
  binary is missing; E2E/runtime image installs Tesseract when OCR is expected.

#### PR-003 — Add active subscription unique partial index

- **Branch:** `fix/subscription-active-unique-index`
- **Priority:** P1, revenue-critical
- **Parallel:** yes, but coordinate with payment tests
- **Files:** new migration under `app/supabase/migrations/`,
  `app/backend/app/api/payments.py`, `app/backend/tests/test_subscription_active_invariant.py`
- **Evidence:** backend comments claim `user_subscriptions_user_active_idx` is a
  partial unique index, but migration `014` creates a plain non-unique index.
- **Work:** Add a forward migration that detects/resolves duplicates for
  `status in ('active','past_due')`, then creates a unique partial index:
  `create unique index if not exists user_subscriptions_user_active_unique_idx on public.user_subscriptions(user_id) where status in ('active','past_due');`
- **Acceptance:** the DB rejects two active/past_due subscriptions for one user;
  payment verify/webhook tests still pass; duplicate active rows are resolved
  safely before index creation.

### Wave 1 — contract fixes

#### PR-004 — Fix AI chat response shape

- **Branch:** `fix/ai-chat-response-contract`
- **Priority:** P1
- **Parallel:** yes
- **Files:** `app/frontend/src/pages/AIChat.jsx`, `app/backend/app/api/ai.py`,
  `app/frontend/src/pages/AIChat.test.jsx`, `app/backend/tests/test_ai_contract.py`
- **Evidence:** frontend stores `r.reply` as renderable text while backend returns
  a shaped message object.
- **Work:** Prefer the minimal-compatible response shape:
  `{"conversation_id":"...","reply":"text","reply_message":{...},"user_message":{...}}`.
- **Acceptance:** no `[object Object]`; existing history still renders; backend
  and frontend contract tests pin the shape.

#### PR-005 — Notification CTA route contract

- **Branch:** `fix/notification-cta-routes`
- **Priority:** P1
- **Parallel:** yes
- **Files:** `app/backend/app/api/notifications.py`,
  `app/frontend/src/pages/Notifications.jsx`, `app/frontend/src/routes/appRoutes.jsx`
  only if a redirect is added, tests
- **Work:** Normalize emitted links to existing frontend routes:
  `/app/eligibility/exams/:slug`, `/app/eligibility/recruitments/:id`,
  `/app/eligibility/tracker`, and `/app/profile`.
- **Acceptance:** every alert type routes to a valid frontend page; add a route
  matrix test for all alert types.

### Wave 2 — production runtime/fallback cleanup

#### PR-006 — Gate or remove placeholder/static routes in production

- **Branch:** `fix/prod-placeholder-gate`
- **Priority:** P1
- **Parallel:** yes, backend-focused
- **Files:** `app/backend/app/api/placeholders.py`, `app/backend/server.py`,
  `app/backend/app/core/config.py`, tests
- **Evidence:** this audit confirms placeholder/static/in-memory surfaces remain
  mounted and process-local stores still exist.
- **Work:** Add an `ENABLE_PLACEHOLDERS` config flag that defaults off in
  production; include `placeholders_router` only when explicitly enabled or in
  dev/test.
- **Acceptance:** production config does not mount placeholder routes; tests verify
  placeholder routes are unavailable when disabled; dev/demo can still enable them.

#### PR-007 — Replace silent frontend failures with visible error states

- **Branch:** `fix/frontend-visible-api-errors`
- **Priority:** P1
- **Parallel:** yes
- **Files:** `app/frontend/src/pages/Marketplace.jsx`,
  `app/frontend/src/pages/ResourceDetail.jsx`,
  `app/frontend/src/features/community/PartnersScreen.jsx`,
  `app/frontend/src/pages/AIChat.jsx`, plus earlier verified surfaces
  `app/frontend/src/pages/Saved.jsx`, `app/frontend/src/pages/Blogs.jsx`,
  `app/frontend/src/features/dashboard/hooks/useDashboardData.js`, and
  `app/frontend/src/pages/Today.jsx`
- **Work:** Separate `loading`, `error`, `empty`, and `data` states.
- **Acceptance:** API failure is never shown as empty/locked/not-enrolled unless
  the backend explicitly returns that state; seed fallback is only behind a
  demo/prototype flag.

#### PR-008 — Production deployment/runbook manifest

- **Branch:** `chore/production-runtime-runbook`
- **Priority:** P1
- **Parallel:** yes
- **Files:** `docs/operations/runbook.md`, `README.md`, `app/backend/.env.example`,
  deploy manifest if available, `.github/workflows/e2e.yml` if present
- **Evidence:** scheduler is in-process and must be enabled on exactly one backend
  instance; this audit flags incomplete in-repo runtime evidence.
- **Work:** Document CORS origins, Supabase env, Razorpay env, OCR packages,
  scheduler singleton ownership, health checks, backend import smoke, frontend
  build vars, and prototype-disabled production settings.
- **Acceptance:** a new operator can deploy from repo docs without hidden
  assumptions; CI has import/startup smoke coverage.

### Wave 3 — revenue validation

#### PR-009 — Razorpay subscription E2E + invariant test

- **Branch:** `test/razorpay-subscription-e2e`
- **Priority:** P1
- **Parallel:** after or alongside PR-003
- **Files:** `app/backend/tests/test_razorpay_payments.py`,
  `docs/operations/payment-runbook.md`
- **Work:** Pin the flow: plan list → order → bad signature rejected → valid
  signature activates → subscription visible → payment history visible → webhook
  signature verified → duplicate active blocked.
- **Depends:** PR-003 should merge before the final unique-active-subscription
  assertion.

#### PR-010 — Marketplace entitlement E2E

- **Branch:** `test/marketplace-entitlement-e2e`
- **Priority:** P1
- **Parallel:** yes
- **Files:** `app/backend/tests/test_marketplace_purchase.py`,
  `docs/operations/marketplace-runbook.md`
- **Evidence:** marketplace backend states server price authority, enrollment
  entitlement, idempotency, and no AI in payment/access decisions.
- **Acceptance:** published course visible; draft course invisible; order uses
  server price; verify grants enrollment; refund does not leave invalid access;
  affiliate external validates partner/domain.

### Wave 4 — launch hardening

#### PR-011 — Admin route auth inventory test

- **Branch:** `test/admin-route-auth-inventory`
- **Priority:** P1
- **Parallel:** yes
- **Files:** `app/backend/tests/test_admin_route_auth_inventory.py`
- **Work:** Inspect FastAPI routes and assert every `/api/admin/*` route has an
  auth dependency or is explicitly allowlisted.
- **Acceptance:** future unauthenticated admin route regressions fail CI.

#### PR-012 — Blog SEO/CMS launch readiness

- **Branch:** `feat/blog-cms-launch-readiness`
- **Priority:** P2
- **Depends:** PR-001
- **Files:** `app/frontend/src/pages/Blogs.jsx`, `app/frontend/src/pages/BlogDetail.jsx`,
  `app/frontend/src/pages/admin/Blogs.jsx`, `app/backend/app/api/blogs.py`
- **Work:** Ensure public pages show only published posts, hide draft/archived
  content, distinguish public error vs empty states, show missing SEO/CTA in admin,
  and render basic meta fields where supported.

## Recommended merge order

1. PR-001 Blog admin auth
2. PR-002 OCR startup guard
3. PR-003 active subscription unique index
4. PR-004 AI chat contract
5. PR-005 notification CTA routes
6. PR-006 placeholder production gate
7. PR-007 visible API failure states
8. PR-008 production runtime runbook
9. PR-009 Razorpay E2E
10. PR-010 marketplace entitlement E2E
11. PR-011 admin route auth inventory
12. PR-012 Blog SEO/CMS readiness

## Work allocation

- **Backend security:** PR-001, PR-011
- **Backend platform:** PR-002, PR-006, PR-008
- **Payments:** PR-003, PR-009
- **Frontend:** PR-004, PR-005, PR-007, PR-012
- **Marketplace QA:** PR-010

## Updated launch gate

Production deploy stays blocked until all of the following are true:

- Blog admin API is protected.
- `import server` passes in the deployment runtime.
- Tesseract is either installed where OCR is enabled or lazy-loaded behind a clear
  unavailable/configured-off path.
- Active subscription uniqueness is enforced by the database.
- AI chat response shape is aligned.
- No production placeholder routes are mounted.
- No critical user-facing page hides backend failure as empty data.
- Payment and marketplace E2E pass.
- Admin route auth inventory test exists.
