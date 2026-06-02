# Cross-language contracts

## Mastery engine (PR5a) output shapes

**Source of truth:** `app/backend/app/study_os/mastery_engine/schemas.py` (Pydantic).

**Shared frontend contract:** `app/frontend/src/types/masteryEngine.schema.json` — a
hand-synced, field-for-field mirror of the Pydantic models (`MasteryDelta`,
`ErrorPatternSignal`, `CorrectionTaskDraft`, `CorrectionEvidence`, `DerivationResult`
and the input analytics shapes). Each field records its type token, whether it is
required, and whether it is nullable.

**Frontend adoption:** `app/frontend/src/types/masteryEngine.js` imports the JSON
contract and derives runtime PropTypes validators from it (e.g. `CorrectionTaskDraft`).
Consumers such as `reports/CorrectionTaskCard.jsx` import these validators instead of
re-declaring local JSDoc/PropTypes shapes. Because the PropTypes are generated from the
JSON, they cannot drift from the contract.

**Drift detection:** `app/backend/.../mastery_engine/tests/test_schema_frontend_parity.py`
introspects the live Pydantic models and asserts the JSON contract matches them
model-for-model and field-for-field (name, type token, required, nullable). Adding,
removing, renaming or retyping a field in `schemas.py` without updating the JSON
contract fails CI.

Wire-format note: Pydantic serializes `Decimal` and `UUID` to JSON strings, so those
fields validate as `string` on the frontend.

### Why this approach (hand-synced + drift test)

The three options considered were (1) Python→TS/JS codegen, (2) a hand-synced types
file guarded by a parity test, and (3) OpenAPI-derived client types.

We chose **option 2**. The repo has no existing Python→JS codegen pipeline, and the
frontend is plain JavaScript (Create React App, PropTypes, no TypeScript), so option 1
would mean introducing a new build dependency for a small set of shapes. The backend
exposes FastAPI/OpenAPI, but there is no client-generation step wired up, so option 3
would likewise be net-new infrastructure. A committed JSON contract plus a pytest parity
gate keeps the backend as the single source of truth, adds zero build dependencies, and
fails CI on drift — the goal of this contract.

When updating `schemas.py`, regenerate/update the JSON contract so the parity test
passes; the JS PropTypes follow automatically.

## Mock attempt → `mock_tests` compat row

`mock_tests.analysis_payload` (jsonb, migration 034) is the canonical field for the
Study OS → Mocks.jsx compat row written by `mock_engine._emit_mock_tests_row`; the
table has no `metadata` column, and the legacy `/api/study/mocks` reader treats a
missing payload as `{}`.

## Production readiness contract exceptions (verified 2026-06-02)

The following cross-surface contracts are known exceptions and must be fixed before production deploy. Detailed evidence lives in [audits/production-readiness-review-2026-06-02.md](audits/production-readiness-review-2026-06-02.md).

| Surface | Frontend expectation | Backend behavior | Status | Required fix |
|---|---|---|---|---|
| Blog CMS admin | `app/frontend/src/pages/admin/Blogs.jsx` calls `/api/admin/blogs*` as an admin-only CMS surface. | `app/backend/app/api/blogs.py` exposes list/read/create/update/publish/archive without backend auth dependencies. | P0 security mismatch | Add `require_admin` or `require_permission("blogs.manage")` to every admin blog route and add 401/403 tests. |
| AI chat | `app/frontend/src/pages/AIChat.jsx` stores `r.reply` as renderable text. | `app/backend/app/api/ai.py` returns `reply` as a shaped message object. | P1 shape mismatch | Return a string `reply`/`reply_text` or update the frontend to render `reply.content`. |
| Subscription activation | Backend comments say a partial unique index prevents multiple active subscriptions. | `app/supabase/migrations/014_payments_runtime_schema.sql` creates a non-unique active-subscription index. | P1 schema invariant mismatch | Add a forward migration with a unique partial index after deduplicating existing active rows. |
| Marketplace/community failure states | Pages should distinguish backend failure from empty/locked/seed data. | Several callers swallow errors or keep seed data. | P1 operational risk | Render explicit error states and reserve fallback seed data for prototype/demo mode. |

