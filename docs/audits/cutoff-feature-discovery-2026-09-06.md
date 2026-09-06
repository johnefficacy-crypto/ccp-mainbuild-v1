# CUTOFF-01 — Discovery Report (STOPPED AT PREFLIGHT STOP GATE)

- **Date:** 2026-09-06
- **Repo HEAD sha:** `47382a45050aeb2efbb859da864b0f10a7618e04` (identical to `origin/main`; work branch `claude/cutoff-discovery-scope-yv2log` is at the same commit, zero diff)
- **Scope requested:** discovery for a "previous years cutoffs" feature (UPSC CSE, RBI Grade B, SSC CGL, IBPS, SEBI/PFRDA/IFSCA)
- **Outcome:** **STOP GATE TRIGGERED.** A cutoff table, model, admin CMS resource, review lifecycle, public API field and aspirant-facing UI already exist end to end. Per the task contract, Q1–Q11 were not answered and no design work was done.

---

## 1. Why the gate fired

Preflight grep (`cutoff`, `cut_off`, `cut-off`, `vacanc`, `merit_list`, `qualifying_marks`, `marks_secured`, `normalis`, `normaliz`, `previous_year_result`, case-insensitive, over backend / frontend / migrations / docs) returned an implemented cutoff feature, not a gap.

Terms with **no** repo hits: `qualifying_marks`, `marks_secured`, `previous_year_result`. `merit_list` appears only as prose in `docs/scraping/aggregator-strategy.md`. `normalis`/`normaliz` hits are unrelated (string/text normalisation), **not** exam score normalisation — see §5.

---

## 2. Storage — what exists

### 2.1 Canonical cutoff column

`public.exam_competition_metrics.cutoff_by_category` — `jsonb not null default '{}'`

- Created: `app/supabase/migrations/216_j3_competition_structure.sql:113`
- Documented shape (verbatim, `app/supabase/migrations/216_j3_competition_structure.sql:134-135`):
  > `'Replacement for legacy cutoff_trend. Shape: {"<reservation_categories.code>": {"marks": number>=0, "max_marks": number>0 (optional)}}. See resolutions §1.5.'`

### 2.2 Parent table

`public.exam_competition_metrics` — created `app/supabase/migrations/055_exam_competition_metrics.sql:8`

- Scope FKs: `exam_id` → `public.exams(id)`, `exam_cycle_id` → `public.exam_cycles(id)`, `exam_phase_id` → `public.exam_phases(id)` (`055_exam_competition_metrics.sql:10-12`)
- Review lifecycle column: `reviewer_status in ('draft','pending_review','reviewed','locked','rejected')` (`055_exam_competition_metrics.sql:31-32`)
- `metric_kind` split added at `216_j3_competition_structure.sql:116` and constrained at `:123-124`:
  `check (metric_kind is null or metric_kind in ('cycle_summary', 'phase_cutoff'))`
  — cutoffs live **only** on `phase_cutoff` rows (`exam_phase_id` required); `cycle_summary` rows own vacancy/pressure (`216_j3_competition_structure.sql:137-139`).
- Versioning/publication columns added `216_j3_competition_structure.sql:117-121` (`version_no`, `supersedes_id`, `superseded_at`, `is_current_published`, `breakdown_complete`).

### 2.3 Deprecated predecessor

`public.exam_competition_metrics.cutoff_trend` — `055_exam_competition_metrics.sql:20`, explicitly deprecated in place at `216_j3_competition_structure.sql:142-143` ("do not write new values"). Still read for back-compat (§4.2).

### 2.4 Reservation-category taxonomy (already exists)

- `public.reservation_categories` — `216_j3_competition_structure.sql:55`; columns `code` (unique), `label`, `category_axis in ('vertical','horizontal')`, `sort_order`, `is_active`, `metadata`.
- Seeded codes verbatim (`216_j3_competition_structure.sql:74-81`): `general`, `ews`, `obc`, `sc`, `st`.
- `public.reservation_category_aliases` — `216_j3_competition_structure.sql:67`; seeded aliases `ur→general`, `gen→general`, `obc_ncl→obc` (`:83-87`).
- RLS: service-role only, no `authenticated` grant (`216_j3_competition_structure.sql:89-105`).
- **PwBD sub-categories: NOT FOUND.** The `category_axis='horizontal'` column exists to model them but no horizontal row is seeded.

### 2.5 Evidence table

`public.exam_competition_metric_evidence` — `216_j3_competition_structure.sql:864`. Evidence rows carry `claim_field` + `reservation_category_id`, so a cutoff claim is evidenced per category.

### 2.6 Adjacent tables already landed

- `public.exam_candidate_counts` + `public.exam_candidate_count_evidence` — `app/supabase/migrations/219_j3_applied_vs_appeared.sql:65` and `:328` (applied-vs-appeared counts; `applicant_count` on `exam_competition_metrics` deprecated in favour of these).
- `public.exam_documents` with `doc_type` value `'cutoff_pdf'` — `app/supabase/migrations/157_exam_documents.sql:5,9-17,28` (official cutoff PDF attachment, keyed by exam + optional phase).

---

## 3. Admin write path — what exists

### 3.1 CMS resource (`/api/admin/exam-intelligence-cms`, `app/backend/app/api/admin_exam_intel_cms.py:54`)

- Field allowlist `_COMPETITION_FIELDS` — `admin_exam_intel_cms.py:2813-2830` (includes `cutoff_by_category`; excludes deprecated `cutoff_trend`, `applicant_count`, `selection_ratio`, `difficulty_trend`, and server-controlled lifecycle columns).
- `POST /exam-competition-metrics` — `admin_exam_intel_cms.py:2892`
- `PATCH /exam-competition-metrics/{metric_id}` — `admin_exam_intel_cms.py:2947`
- `GET /exam-competition-metrics` — `admin_exam_intel_cms.py:3982`
- Cutoff payload validation (422s) — `admin_exam_intel_cms.py:2860-2873`: object required, unknown category rejected, `{marks, max_marks?}` object required (bare value rejected), `stage` key forbidden.
- Field-ownership enforcement — `admin_exam_intel_cms.py:2916-2924` (create) and `:2978-2991` (patch): phase-scoped row is `phase_cutoff` and may not carry vacancy/pressure; cycle-scoped row may not carry `cutoff_by_category`/`difficulty_assessment`.

### 3.2 Review + evidence (`/api/admin/exam-intelligence`, `app/backend/app/api/admin_exam_intelligence.py:58`)

- `POST /competition-metrics/{row_id}/evidence` — `admin_exam_intelligence.py:1030`; `claim_field` pattern includes `cutoff_by_category` (`:1013`) and requires a `reservation_category_code` for category-scoped claims (`:1052`, `:1059`).
- `GET /competition-metrics/{row_id}/evidence` — `admin_exam_intelligence.py:1092`
- `GET /competition-metrics` — `admin_exam_intelligence.py:1146`
- `PATCH /competition-metrics/{row_id}/review` — `admin_exam_intelligence.py:1192`, delegates to RPC `cms_review_competition_metric` (`:1229`; defined `216_j3_competition_structure.sql:1018`).
- `POST /competition-metrics/{row_id}/reopen-for-edit` — `admin_exam_intelligence.py:1288`, RPC `cms_reopen_competition_metric_for_edit` (`:1303`; defined `216_j3_competition_structure.sql:1244`).
- Evidence registry entry for the table — `app/backend/app/api/evidence.py:98-102`.

### 3.3 Admin UI

- `app/frontend/src/pages/admin/exam-workspace/panels/CompetitionPanel.jsx` — cutoff editor; hardcoded `CATEGORIES` at `:9`, claim-field option at `:54`, per-category `{marks, max_marks}` payload build at `:319-327`, editor inputs at `:506` / `:513`, mounted from `ExamWorkspace.jsx:504`.
- `app/frontend/src/features/admin/exam-intelligence/CompetitionMetricsTable.jsx:116` — read-only cutoff column in the review surface.
- Test pinning the write payload: `app/frontend/src/pages/admin/exam-workspace/panels/__tests__/PanelWritePayloads.test.jsx:334-369`.

---

## 4. Aspirant read path — what exists

### 4.1 Public endpoint

`GET /api/exam-intelligence/exams/{slug}` — `app/backend/app/api/exam_intelligence.py:143` (router prefix `:42`), returns a `cutoff_series` key (`:160`).

### 4.2 Series builders

- `app/backend/app/exam_intelligence/status.py:130-131` — calls `competition_series()` then `cutoff_series()`.
- `app/backend/app/exam_intelligence/competition.py:279` — `cutoff_series()`; prefers `cutoff_by_category`, falls back to legacy `cutoff_trend` (`:282-299`). Reads gated to `reviewer_status in ('reviewed','locked')` (`:109`).
- `app/backend/app/study_os/competition_context.py:144` — Study OS pressure block; same verified-only gate (`:173`), exposes `cutoff_by_category` (`:236`). Surfaced via `app/backend/app/api/study_os.py:536`.
- `GET /api/exam-intelligence/exams/{slug}/documents` — `app/backend/app/api/exam_intelligence.py:1178` (serves `cutoff_pdf` documents).

### 4.3 Aspirant UI

- `app/frontend/src/features/exams/ExamIntelligenceTab.jsx` — fetches `/api/exam-intelligence/exams/${examSlug}` (`:147`), builds the chart from `data.cutoff_series` (`:164-166`), renders the "Cutoff history" card (`:279-289`, testid `cutoff-trend-card`). Mounted from `app/frontend/src/pages/ExamDetail.jsx:541`.
- `app/frontend/src/features/exams/ExamDocumentsSection.jsx:11,22` — "Cutoff PDFs" group.

---

## 5. Explicit NOT FOUND

| Requested concept | Status |
| --- | --- |
| `qualifying_marks` column/field | NOT FOUND |
| `marks_secured` column/field | NOT FOUND |
| `previous_year_result` table/field | NOT FOUND |
| `merit_list` table/model/endpoint | NOT FOUND (prose only: `docs/scraping/aggregator-strategy.md`) |
| Score **normalisation** (SSC CGL Tier-normalised marks) logic | NOT FOUND — all `normalis`/`normaliz` hits are text/string normalisation |
| PwBD / horizontal reservation sub-categories | NOT FOUND as data (only the unused `reservation_categories.category_axis='horizontal'` slot, `216_j3_competition_structure.sql:59-60`) |
| Per-exam cutoff seed data for RBI Grade B / SSC CGL / IBPS / SEBI / PFRDA / IFSCA | NOT FOUND in migrations/seeds |
| Operator-validation gate for the J3 competition/cutoff work | NOT FOUND in `docs/operator-validation/registry.json` |

---

## 6. Questions not answered

Q1–Q11 were not researched: the preflight stop gate instructs a full stop on discovering an existing cutoff table/model/endpoint, and all three exist. Note also that the task text delivered to this session was **truncated mid-Q3** — Q4 through Q11 were never supplied and are unknown.
