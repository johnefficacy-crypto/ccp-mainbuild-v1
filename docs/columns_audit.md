# Columns Audit — `recruitments` schema drift (Bug 1)

Pre-flight artifact for the admin-trust API fix. Audits the four columns that
`app/backend/app/api/admin_trust.py::admin_recruitments` selected from
`public.recruitments` but which do **not** exist on that table, producing a
deterministic PostgREST `42703` error (`column recruitments.min_age does not
exist`) → HTTP 500.

## Method

- Schema of record: `docs/schema/supabase-current.md` (the `recruitments`
  `CREATE TABLE` block, lines 1823–1851).
- Migration history: `app/supabase/migrations/*.sql`.
- Backend usage: `grep -rn` over `app/backend/**/*.py`.
- Frontend usage: `grep -rn` over `app/frontend/src/**/*.{js,jsx,ts,tsx}`.

The canonical `recruitments` columns are: `id, organization_id, name, status,
publish_status, apply_start_date, apply_end_date, notification_date, year,
total_vacancies, created_at, updated_at, slug, official_notification_url,
official_apply_url, source_pdf_url, source_id, published_by, published_at,
review_notes, exam_id, notification_number`. None of the four audited columns
appear there, and no migration ever adds them to `recruitments`.

---

## `min_age`

- **Frontend references** (all `age_criteria`, per-post — NOT recruitment-level):
  - `app/frontend/src/features/admin/recruitments/RecruitmentCriteriaPanel.jsx:147,156,178,179`
  - `app/frontend/src/features/admin/workflow/FieldReviewGroup.jsx:13`
  - `app/frontend/src/features/admin/workflow/PostEligibilityReviewGroup.jsx:20`
  - `app/frontend/src/features/admin/workflow/PromotionPreviewPanel.jsx:169`
- **Backend references**:
  - `app/backend/app/api/admin_trust.py:189,392` (the drift — reads/selects from `recruitments`)
  - `app/backend/app/api/admin_trust.py:652,718,726,727` (legitimate — `age_criteria` table)
  - `age_criteria` / extracted-post usage: `eligibility/schemas.py:181`, `eligibility/runner.py:266`, `eligibility/engine.py:419`, `scraping/schemas.py:40`, `scraping/normalizer.py:133`, `scraping/runner.py:3328`, `admin_scrape.py:1386` (all `age_criteria` or extracted-post JSON, never `recruitments`)
- **Migration references**: `002_core_runtime_schema.sql:38` (`age_criteria`), `043/044/048/058/059_*` promote RPCs insert into `age_criteria` from extracted-post JSON. No `recruitments.min_age` anywhere.
- **Schema doc**: `supabase-current.md:75` — belongs to `age_criteria`, not `recruitments`.
- **Decision: REMOVE.** The recruitment-level `min_age` never existed. Age data lives on `age_criteria` (per post). The `_evaluate_readiness` fallback `rec.get("min_age")` always resolved to `None`, so removing it is behaviour-preserving. Eligibility-rule presence is already derived from the `age_criteria`/`education_criteria` joins via `has_post_rules`.

## `max_age`

- **Frontend references**: same files/lines as `min_age` above — all `age_criteria`/per-post, none recruitment-level.
- **Backend references**: `admin_trust.py:189,392` (drift); `admin_trust.py:652,718,726,727` (`age_criteria`); plus `eligibility/*` and `scraping/*` (`age_criteria` / extracted-post). `max_age_cap` (`age_relaxation_rules`) is a different column and is not in scope.
- **Migration references**: `age_criteria` only (same set as `min_age`).
- **Schema doc**: `supabase-current.md:76` — `age_criteria`.
- **Decision: REMOVE.** Same rationale as `min_age`.

## `posts_unavailable`

- **Frontend references**: none.
- **Backend references**: `app/backend/app/api/admin_trust.py:186,392` only.
- **Migration references**: none (column never created).
- **Schema doc**: none.
- **Decision: REMOVE.** Never a real column. Read as `rec.get("posts_unavailable")`, which always returned `None`, so `not posts and not rec.get("posts_unavailable")` was equivalent to `not posts`. Behaviour-preserving.

## `rules_unavailable`

- **Frontend references**: none.
- **Backend references**: `app/backend/app/api/admin_trust.py:188,209,392` only. (Also present in the existing test fixture `tests/test_admin_trust.py:15`, which is updated in this PR.)
- **Migration references**: none.
- **Schema doc**: none.
- **Decision: REMOVE.** Never a real column. `not rec.get("rules_unavailable")` always evaluated `True`, so the guarded blocks ran unconditionally anyway. Behaviour-preserving.

---

## Summary

| column | exists in schema | frontend reads recruitment-level field | decision |
|---|---|---|---|
| `min_age` | no (only on `age_criteria`) | no | REMOVE |
| `max_age` | no (only on `age_criteria`) | no | REMOVE |
| `posts_unavailable` | no | no | REMOVE |
| `rules_unavailable` | no | no | REMOVE |

All four are **Case A (code drift, REMOVE)** per the fix order's default. No
migration is added and no frontend change is required: the dropped fields were
never returned in the `admin_recruitments` response payload, and the only
frontend `min_age`/`max_age` usages bind to the `age_criteria` (per-post)
editor, which is unaffected.

Readiness semantics are unchanged because every removed `rec.get(...)` lookup
already resolved to `None`/falsy at runtime (the columns were absent from the
row), so the simplified predicates are equivalent:

- `if not posts and not rec.get("posts_unavailable")` → `if not posts`
- `if not rec.get("rules_unavailable"): if not has_post_rules and not rec.get("min_age") and not rec.get("max_age")` → `if not has_post_rules`
- `if post_ids and not rec.get("rules_unavailable")` → `if post_ids`
