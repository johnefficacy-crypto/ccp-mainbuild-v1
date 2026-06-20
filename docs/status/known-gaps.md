---
owner: ops
status: live
last_verified_against_code: 2026-06-20
last_modified: 2026-06-20
source_of_truth: code
related_code:
  - app/backend
  - app/frontend
related_migrations:
  - app/supabase/migrations
review_cadence: per-sprint
---

# Known Gaps

This file lists gaps re-checked against the current codebase. Historical audit
findings in `docs/audits/` are point-in-time evidence; re-verify them before
treating them as open work.

## Recently resolved / no longer open

- **AI chat durability** — `/api/ai/*` is backed by `ai_conversations` and `ai_messages`; the old in-memory chat placeholder is superseded.
- **Admin overview durability** — `/api/admin/overview` and the unconstrained audit feed read Supabase-backed tables through `admin_overview.py`.
- **Accountability route extraction** — partners, groups, and mentor booking routes are owned by `accountability.py` / `study_compare.py`; the placeholder accountability router is intentionally empty.
- **Duplicate admin placeholders** — placeholder `/admin/notifications`, `/admin/marketplace`, and `/admin/ai-policy` read endpoints were removed in favor of real routers.
- **Blog CMS admin API backend auth** — `/api/admin/blogs*` requires backend auth and permissioned mutations.
- **OCR/Tesseract startup guard** — importing `server.py` is no longer blocked by a missing Tesseract binary.
- **Subscription active-row invariant** — duplicate active/past_due subscription rows are retired by the unique active-row migration.
- **Community reply vote** — `POST …/replies/{id}/vote` is now DB-backed in `community_runtime.py`; the old seed-memory handler in `community_people.py` no longer applies.
- **Community admin "Hide" action** — `admin_resolve_community_flag` with `action="hide"` now flips the target entity's `status="hidden"` before updating the report row.
- **Mentor badge crash** — `MentorsScreen.jsx` now applies an `adaptMentor()` adapter that fills `badge`, `color`, `blurb`, and `served` before rendering, preventing `TypeError` on missing fields.
- **Community counter races** — five atomic RPC functions in migration `089_community_counter_rpcs.sql` replace client-side read-modify-write; all counter update sites route through `_rpc_inc`.
- **`community_people` router** — `community_people.py` was deleted; `server.py` now serves all community routes exclusively from `community_runtime_router`.

## Open contract/runtime gaps

- **AI chat response contract** — `/api/ai/chat` persists messages, but returns `reply` as a shaped message object. Any frontend surface that expects a plain text `reply` must be aligned before production.
- **Real LLM provider behind `/api/ai/chat`** — responses are scripted (`scripted-v1`). Provider integration, prompt governance, and response-quality evaluation remain pending.
- **Residual placeholder/static routes** — `placeholders.py` is still mounted for a small set of static/demo surfaces and an admin notification toggle compatibility path. Do not use it for new canonical behavior.
- **Notification CTA route contract** — emitted alert CTAs need a route matrix so every link lands on an existing frontend route.
- **Marketplace/community error handling** — several screens still need stronger API error states so production failures do not look like empty/seed data.
- **Downloadable reports** — CSV/JSON are inline; PDF generation and signed-URL storage still need a worker path.
- **Leadership KPIs** — recompute is admin-triggered; a nightly snapshot job is not yet scheduled.
- **Supabase Auth invite delivery** — `/admin/users/create` records/audits users but still needs email invite delivery through the auth/notification path.

## Operational gaps

- Admin governance gap lists require periodic refresh against code evidence.
- Scraper operations need recurring day-2 review of source SLAs and incident procedures.
- Production deployment evidence is incomplete in-repo: document runtime OS packages, CORS origins, Supabase/Razorpay env, scheduler singleton ownership, and smoke checks.
