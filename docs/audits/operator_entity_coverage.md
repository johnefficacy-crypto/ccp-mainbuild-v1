# Operator Entity Coverage Audit

**Branch:** `audit/operator-entity-coverage`  
**Date:** 2026-06-07  
**Method:** Read-only audit of live source files. Graph (`graphify-out/GRAPH_REPORT.md`) treated as stale — all cells backed by cited live files. No code was changed.

---

## Entities That Do NOT Exist as Standalone Tables

| Named Entity | Finding | Authority |
|---|---|---|
| `microtopic` | Not a table. Microtopics are rows in `public.topics` with `level = 'microtopic'` and a non-null `parent_topic_id`. The `level` CHECK constraint is `('topic','microtopic','concept')`. | `app/supabase/migrations/029_exam_intelligence_taxonomy.sql` lines 29–44 |
| `important_date` | Not a table. Important dates are columns on `exam_cycles` (`notification_date`, `application_start`, `application_end`, `exam_start`, `exam_end`) and `exam_phases` (`phase_start`, `phase_end`). No standalone entity. | `app/supabase/migrations/030_exam_registry_cycles_phases.sql` lines 31–48, 50–67 |
| `notification` | Not a single entity. Five related tables exist: `notification_alerts`, `notification_preferences`, `notification_generation_runs`, `alert_events`, `notification_group_state`. None are admin-created via exam intel console — all are system-generated. | `app/supabase/migrations/002_core_runtime_schema.sql` lines 59–65; migration 015 |

---

## Coverage Matrix

Columns:
1. **CREATE/EDIT UI** — admin surface to create AND edit. Note if create-only or edit-only.
2. **BULK IMPORT** — any batch/CSV/paste/structured ingestion path. `scripts/import_exam_registry.py` is RETIRED; not counted as live.
3. **VERIFY PIPELINE** — candidate → human gate → apply → audit flow.
4. **FRESHNESS / COVERAGE** — stored indicator of staleness or completeness, plus whether it is surfaced to the operator in a worklist or dashboard.

---

### exam_family

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **YES — create + edit** | `ExamIntelCms.jsx:78–87` defines `ENTITY_CONFIG["exam-families"]` with fields `slug, name, description, is_active`. Entity appears in `EDITABLE_ENTITIES` set (line 395) and `DEACTIVATABLE_ENTITIES` set (line 397). Backend: `admin_exam_intel_cms.py` POST `/exam-families` line 154, PATCH `/exam-families/{family_id}` line 179. |
| **BULK IMPORT** | **YES — live** | Generic POST `/api/admin/exam-intelligence-cms/bulk-import` (`admin_exam_intel_cms.py:2596`) supports `exam-families` via `_IMPORT_CONFIG`. Frontend CSV parser: `app/frontend/src/lib/bulkImportFile.js`. |
| **VERIFY PIPELINE** | **NONE** | No `reviewer_status` column on `exam_families` table (`migration 030:5–14`). Table not in `_REVIEWABLE` dict in `admin_exam_intelligence.py:80–99`. Not targeted by any `registry_action_service.py` action. |
| **FRESHNESS / COVERAGE** | **PARTIAL — field present, not surfaced** | `updated_at` present in table definition (migration 030:14). No worklist, dashboard widget, or admin query exposes `updated_at` to the operator for `exam_families`. |

---

### exam

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **YES — create + edit** | `ExamIntelCms.jsx:89–100` defines `ENTITY_CONFIG["exams"]` with fields `name, conducting_organization_id (org-ref), exam_family_id (ref), exam_type, description, is_active`. In `EDITABLE_ENTITIES` and `DEACTIVATABLE_ENTITIES`. Backend: `admin_exam_intel_cms.py` POST `/exams` line 273, PATCH `/exams/{exam_id}` line 310. |
| **BULK IMPORT** | **YES — live** | Same generic `/bulk-import` endpoint; `exams` listed in `_IMPORT_CONFIG` (`admin_exam_intel_cms.py:2360+`). |
| **VERIFY PIPELINE** | **NONE** | No `reviewer_status` on `exams` (migration 030:16–29). Not in `_REVIEWABLE`. Not targeted by `registry_action_service.py`. |
| **FRESHNESS / COVERAGE** | **PARTIAL — field present, not surfaced** | `updated_at` on table. The related `organizations.calendar_status` (migration 167) is linked via `conducting_organization_id` but is surfaced on the `organizations` entity, not on `exams` themselves. No exam-level staleness worklist. |

---

### exam_cycle

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **YES — create + edit** | `ExamIntelCms.jsx:101–116` defines `ENTITY_CONFIG["exam-cycles"]` with fields `exam_id, year, cycle_name, status, notification_date, application_start, application_end, exam_start, exam_end, source_url`. Also exposed in `SetupPanel.jsx:62–440` with date fields editable. Backend: `admin_exam_intel_cms.py` POST `/exam-cycles` line 391, PATCH `/exam-cycles/{cycle_id}` line 418. |
| **BULK IMPORT** | **YES — live** | `/bulk-import` supports `exam-cycles` via `_IMPORT_CONFIG`. |
| **VERIFY PIPELINE** | **PARTIAL — registry action target only** | `registry_action_service.py:35–44` defines `apply_cycle_date_update` which mutates `exam_cycles`. However cycles themselves do not carry `reviewer_status`; the mutation is triggered from a verification report apply-action (`admin_verification_reports.py`), not from a CMS-side human gate. No `candidate → pending → review` flow on the cycle entity itself. |
| **FRESHNESS / COVERAGE** | **PARTIAL — field present, not surfaced** | `updated_at` present (migration 030:48). `status` column exists (`draft/active/completed/cancelled`). `SetupPanel.jsx` renders status inline but there is no dedicated staleness worklist for cycles with `status='draft'` or cycles missing date fields (unlike phases which have an explicit worklist). |

---

### exam_phase

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **YES — create + edit** | `ExamIntelCms.jsx:117–134` defines `ENTITY_CONFIG["exam-phases"]` with fields `exam_id, phase_name, phase_slug, exam_cycle_id, phase_order, mode, duration_mins, total_questions, total_marks, status, phase_start, phase_end`. `SetupPanel.jsx:442–567` renders phase rail with edit UI. Backend: `admin_exam_intel_cms.py` POST `/exam-phases` line 477, PATCH `/exam-phases/{phase_id}` line 499. |
| **BULK IMPORT** | **YES — live** | `/bulk-import` supports `exam-phases` via `_IMPORT_CONFIG`. |
| **VERIFY PIPELINE** | **PARTIAL — registry action target only** | `registry_action_service.py:46–53` defines `apply_phase_date_update`. Same caveat as exam_cycle: phases are mutated by apply-action from a verification report, but do not carry their own `reviewer_status` gate. |
| **FRESHNESS / COVERAGE** | **YES — surfaced** | `SetupPanel.jsx:569–640` explicitly implements `needsPhaseDateAuthoring()` worklist that surfaces phases missing `phase_start` to the operator. `updated_at`, `phase_start`, `phase_end` are stored. This is the only entity in the registry tier with an explicit operator-facing completeness worklist. |

---

### subject

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **YES — create + edit** | `ExamIntelCms.jsx:219–229` defines `ENTITY_CONFIG["subjects"]` with fields `slug, name, subject_group, default_difficulty_level, description, is_active`. In `EDITABLE_ENTITIES`. Backend: `admin_exam_intel_cms.py` POST `/subjects` line 1530, PATCH `/subjects/{subject_id}` line 1556. |
| **BULK IMPORT** | **YES — live** | `/bulk-import` supports `subjects` via `_IMPORT_CONFIG`. |
| **VERIFY PIPELINE** | **NONE** | No `reviewer_status` on `subjects` table (migration 029:6–17). Not in `_REVIEWABLE`. Subjects are reference taxonomy only. |
| **FRESHNESS / COVERAGE** | **PARTIAL — field present, not surfaced** | `updated_at` on table. No operator-facing staleness worklist. |

---

### topic

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **YES — create + edit** | `ExamIntelCms.jsx:231–247` defines `ENTITY_CONFIG["topics"]` with fields `subject_id, level (enum: topic\|microtopic\|concept), parent_topic_id, slug, name, default_difficulty_level, description, is_active`. In `EDITABLE_ENTITIES`. Backend: `admin_exam_intel_cms.py` POST `/topics` line 1626, PATCH `/topics/{topic_id}` line 1672. |
| **BULK IMPORT** | **YES — live** | `/bulk-import` supports `topics` via `_IMPORT_CONFIG`. Microtopic-level rows are created via the same endpoint with `level='microtopic'`. |
| **VERIFY PIPELINE** | **NONE (direct); YES (indirect via coverage/PYQ tags)** | `topics` table has no `reviewer_status`. However, `exam_topic_coverage` and `pyq_question_topic_tags` (both reference topics) do carry `reviewer_status` and flow through `_REVIEWABLE` in `admin_exam_intelligence.py:80–99`. The topic record itself is not gated. |
| **FRESHNESS / COVERAGE** | **PARTIAL — field present, not surfaced** | `updated_at` on table. Coverage of a topic (how many questions, syllabus mentions) is computed dynamically in `admin_exam_intelligence.py:~330` and is not stored as a column. No stored `coverage_count`. No operator worklist for orphaned or uncovered topics. |

---

### microtopic

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **YES — via topic entity** | Microtopics are created as `topics` rows with `level='microtopic'`. Same UI, same endpoint. No dedicated surface. `ExamIntelCms.jsx:231–247`; `admin_exam_intel_cms.py:1626`. |
| **BULK IMPORT** | **YES — via topic entity** | `/bulk-import` with `level='microtopic'` in the row. |
| **VERIFY PIPELINE** | **NONE** | Same as topics — no `reviewer_status` on the row itself. |
| **FRESHNESS / COVERAGE** | **PARTIAL — field present, not surfaced** | `updated_at` inherited from topics table. No standalone worklist. |

---

### pyq (covers pyq_source, pyq_paper, pyq_question, pyq_option, pyq_question_topic_tag)

| Sub-entity | Column | Result | Evidence |
|---|---|---|---|
| **pyq_source** | CREATE/EDIT UI | YES — create + edit | `ExamIntelCms.jsx` ENTITY_CONFIG["pyq-sources"]; backend `admin_exam_intel_cms.py` POST line 2164, PATCH line 2194. |
| **pyq_source** | BULK IMPORT | YES — live | `/bulk-import` supports `pyq-sources`. |
| **pyq_source** | VERIFY PIPELINE | NONE | No `reviewer_status` on `pyq_sources` (migration 032:5–17). |
| **pyq_source** | FRESHNESS | PARTIAL | No `updated_at` or staleness field on `pyq_sources`. Not surfaced. |
| **pyq_paper** | CREATE/EDIT UI | YES — create + edit | `ExamIntelCms.jsx` ENTITY_CONFIG["pyq-papers"]; backend `admin_exam_intel_cms.py` POST line 637, PATCH line 660. |
| **pyq_paper** | BULK IMPORT | YES — dedicated two-phase + generic | Dedicated preflight/commit: `admin_exam_intel_cms.py:886` (POST `/pyq-papers/{paper_id}/bulk-import/preflight`), line 920 (POST `.../commit`). Generic `/bulk-import` also supports `pyq-papers`. Frontend: `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/bulk-import/`. |
| **pyq_paper** | VERIFY PIPELINE | PARTIAL — trust_status only | `pyq_papers.trust_status` (pending/verified/rejected) exists (migration 032:19–38) but is mutated via direct PATCH, not via the `_REVIEWABLE` review queue in `admin_exam_intelligence.py`. Not in the candidate→human→apply→audit spine. |
| **pyq_paper** | FRESHNESS | PARTIAL — field present, partially surfaced | `trust_status` shown in ExamIntelCms list view (columns line 171). `content_hash` present for dedup. No `updated_at`. No staleness worklist for papers with `trust_status='pending'`. |
| **pyq_question** | CREATE/EDIT UI | YES — create + edit | `ExamIntelCms.jsx` ENTITY_CONFIG["pyq-questions"]; backend `admin_exam_intel_cms.py` POST line 1003, PATCH line 1075. |
| **pyq_question** | BULK IMPORT | YES — dedicated two-phase + generic | Same two-phase bulk import as pyq_paper. |
| **pyq_question** | VERIFY PIPELINE | YES — full spine | `pyq_questions.reviewer_status` (pending/verified/rejected/needs_correction) (migration 032:44–62). In `_REVIEWABLE` dict (`admin_exam_intelligence.py:80–99`). Reviewed via `/admin/exam-intelligence` queue. Registry action path: `admin_verification_reports.py` `/apply-registry-action`. |
| **pyq_question** | FRESHNESS | YES — surfaced | `reviewer_status` shown in `/admin/exam-intelligence` review queue. `updated_at` on table. Pending questions appear in review worklist. |
| **pyq_option** | CREATE/EDIT UI | YES — create + edit | `ExamIntelCms.jsx` ENTITY_CONFIG["pyq-options"]; backend endpoints in `admin_exam_intel_cms.py`. |
| **pyq_option** | BULK IMPORT | YES — as inline child of pyq_question | Created as inline children in pyq_question bulk import; rollback if any child fails. |
| **pyq_option** | VERIFY PIPELINE | NONE direct | No `reviewer_status` on `pyq_options` (migration 032:64–75). Inherits from parent `pyq_question` review. |
| **pyq_option** | FRESHNESS | NONE | No staleness field. Not surfaced. |
| **pyq_question_topic_tag** | CREATE/EDIT UI | YES — create + edit | `ExamIntelCms.jsx` ENTITY_CONFIG["pyq-question-topic-tags"]; backend `admin_exam_intel_cms.py`. |
| **pyq_question_topic_tag** | BULK IMPORT | YES — live | `/bulk-import` supports `pyq-question-topic-tags`. |
| **pyq_question_topic_tag** | VERIFY PIPELINE | YES — full spine | `pyq_question_topic_tags.reviewer_status` present (migration 032:91–108). In `_REVIEWABLE` (`admin_exam_intelligence.py:80–99`). Review queue + apply-action path. Also has `reviewed_at`. |
| **pyq_question_topic_tag** | FRESHNESS | YES — surfaced | `reviewer_status` in review queue worklist. `reviewed_at` stored (migration 032:108). |

---

### notification

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **NONE — system-generated only** | No admin CRUD for notification entities in `ExamIntelCms.jsx`, `SetupPanel.jsx`, or `adminRoutes.jsx`. `notification_alerts` are generated by backend scheduled tasks (`notification_generation_runs`). Kill-switch only: `admin_notifications.py` POST `/admin/notifications/kill-switch` line 221. |
| **BULK IMPORT** | **NONE** | No bulk import path. Generation is via scheduled fanout triggered by `alert_events`. |
| **VERIFY PIPELINE** | **NONE** | Not in exam intel verification flow. Delivery tracked by `email_sent`, `email_sent_at`, `delivery_error` on `notification_alerts` but these are system-written, not operator-reviewed. |
| **FRESHNESS / COVERAGE** | **PARTIAL — system fields only, not an operator worklist** | `notification_generation_runs.finished_at`, `notification_alerts.sent_at`, `alert_events.fanout_status` exist (migration 002, 015). Admin GET `/admin/notifications` (line 156) shows history but is a log view, not a staleness worklist. |

---

### important_date

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **N/A — not a standalone entity** | Dates are columns on `exam_cycles` and `exam_phases`. Edited via those entities' UI (`ExamIntelCms.jsx`, `SetupPanel.jsx`). No standalone "important_date" create/edit surface. |
| **BULK IMPORT** | **N/A — not a standalone entity** | Imported as fields within `exam-cycles` or `exam-phases` rows via `/bulk-import`. |
| **VERIFY PIPELINE** | **N/A — not a standalone entity** | Date mutations flow through `apply_cycle_date_update` / `apply_phase_date_update` in `registry_action_service.py:35–53`. |
| **FRESHNESS / COVERAGE** | **N/A — not a standalone entity** | `SetupPanel.jsx:569–640` `needsPhaseDateAuthoring()` partially surfaces missing dates for phases. Cycle dates have no equivalent worklist. |

---

### vacancy

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **NONE** | `public.vacancies(id, post_id, category, vacancy_count)` defined in migration 002:37. No admin CRUD in `admin_exam_intel_cms.py`, `ExamIntelCms.jsx`, or any admin route. Vacancies are child rows of recruitment posts populated by the scraper pipeline. |
| **BULK IMPORT** | **NONE** | No bulk import path. Vacancies are created via the recruitment scraper (`admin_scrape.py`, `promotion_gate.py`) not via CMS. |
| **VERIFY PIPELINE** | **INDIRECT only** | `vacancy_total` appears as a field in `exam_competition_metrics` (migration 033), which is a reviewable entity. The `vacancies` table itself carries no `reviewer_status` and is not in `_REVIEWABLE`. |
| **FRESHNESS / COVERAGE** | **NONE** | No `updated_at` on `vacancies` table (migration 002:37 — only `id, post_id, category, vacancy_count`). Not surfaced to operator. Vacancy count staleness is tracked at the `recruitment_verification_reports` level (migration 075 `staleness_status`, `last_checked_at`) — one level up from the vacancies table. |

---

### policy_update

| Column | Result | Evidence |
|---|---|---|
| **CREATE/EDIT UI** | **YES — create + edit** | `ExamIntelCms.jsx:193–218` defines `ENTITY_CONFIG["policy-updates"]` with fields `exam_id, update_type, title, summary, source_type, source_url, exam_cycle_id, source_id, claim_status, affects_plan, affects_deadline, affects_eligibility, affects_documents, affects_syllabus, affects_vacancy, change_summary, evidence, published_at, effective_from`. In `EDITABLE_ENTITIES`. Backend: `admin_exam_intel_cms.py` POST `/policy-updates` line 1302, PATCH `/policy-updates/{policy_id}` line 1335. |
| **BULK IMPORT** | **YES — live** | `/bulk-import` supports `policy-updates` via `_IMPORT_CONFIG`. All rows land at `reviewer_status='pending'` on create (CMS guard `admin_exam_intel_cms.py:12–19`). |
| **VERIFY PIPELINE** | **YES — full spine** | `exam_policy_updates.reviewer_status` (pending/verified/rejected/needs_correction) (migration 056:36–37). In `_REVIEWABLE` (`admin_exam_intelligence.py:80–99`). Review queue at `admin_exam_intelligence.py:789, 847`. Registry action path: `apply_policy_update_create` / `apply_policy_update_edit` in `registry_action_service.py:113–200`. Triggered via `admin_verification_reports.py` `/apply-registry-action`. Full candidate→human gate→apply→audit spine confirmed. |
| **FRESHNESS / COVERAGE** | **YES — surfaced** | `updated_at`, `reviewed_at`, `reviewer_status` stored (migration 056). `reviewer_status` shown in ExamIntelCms list view (columns line 217) and in `/admin/exam-intelligence` review queue. Pending policy updates appear in review worklist. |

---

## Gap Summary — Entities Ranked by Operator Burden

Flags:
- 🔴 **MANUAL-ONLY** — no bulk import path (operator must create records one by one)
- 🟠 **NO-VERIFY-SPINE** — no reviewer_status gate; changes go live immediately on PATCH
- 🟡 **NO-SURFACED-FRESHNESS** — a staleness/completeness field exists but is not exposed in any operator worklist or dashboard

### High Burden

| Entity | Burden Flags | Notes |
|---|---|---|
| `vacancy` | 🔴 MANUAL-ONLY · 🟠 NO-VERIFY-SPINE · 🟡 NO-SURFACED-FRESHNESS | No admin CRUD at all; entirely scraper-populated. Zero operator touchpoints. |
| `notification` | 🔴 MANUAL-ONLY · 🟠 NO-VERIFY-SPINE · 🟡 NO-SURFACED-FRESHNESS | System-generated only; no exam-intel admin surface; no staleness worklist. Delivery errors exist in DB but are not surfaced to the exam operator. |

### Medium Burden

| Entity | Burden Flags | Notes |
|---|---|---|
| `exam_family` | 🟠 NO-VERIFY-SPINE · 🟡 NO-SURFACED-FRESHNESS | Has UI + bulk import. Changes go live immediately (no pending→review gate). `updated_at` stored but not in any worklist. |
| `exam` | 🟠 NO-VERIFY-SPINE · 🟡 NO-SURFACED-FRESHNESS | Has UI + bulk import. No gate; no staleness surface. `conducting_organization_id` calendar status is on the org entity, not the exam. |
| `exam_cycle` | 🟠 NO-VERIFY-SPINE · 🟡 NO-SURFACED-FRESHNESS | Has UI + bulk import. Registry action can mutate cycles but only as a downstream target, not as a guarded create/edit path. Cycles with `status='draft'` or missing dates have no operator worklist (unlike phases). |
| `subject` | 🟠 NO-VERIFY-SPINE · 🟡 NO-SURFACED-FRESHNESS | Has UI + bulk import. Pure reference taxonomy; no staleness surface. |
| `topic` / `microtopic` | 🟠 NO-VERIFY-SPINE · 🟡 NO-SURFACED-FRESHNESS | Has UI + bulk import. Topic coverage computed dynamically (not stored). Orphaned/uncovered topics have no operator worklist. |
| `pyq_source` | 🟠 NO-VERIFY-SPINE · 🟡 NO-SURFACED-FRESHNESS | Has UI + bulk import. No `reviewer_status`, no `updated_at`, not in review queue. |
| `pyq_paper` | 🟠 NO-VERIFY-SPINE (partial) · 🟡 NO-SURFACED-FRESHNESS (partial) | Has `trust_status` shown in list view but it is mutated via direct PATCH, not the review queue spine. No staleness worklist for `trust_status='pending'` papers. |
| `pyq_option` | 🟠 NO-VERIFY-SPINE · 🟡 NO-SURFACED-FRESHNESS | No `reviewer_status`. Correctness depends entirely on parent `pyq_question` review. |

### Low Burden (Well-Covered)

| Entity | Status | Notes |
|---|---|---|
| `exam_phase` | ✅ UI + bulk + partial verify spine + surfaced worklist | `SetupPanel.jsx` `needsPhaseDateAuthoring()` explicitly surfaces missing dates. Registry action target. Best-covered registry entity. |
| `pyq_question` | ✅ UI + bulk + full verify spine + surfaced queue | Full `reviewer_status` gate, review queue, registry apply-action. |
| `pyq_question_topic_tag` | ✅ UI + bulk + full verify spine + surfaced queue | Full `reviewer_status` gate + `reviewed_at`. |
| `policy_update` | ✅ UI + bulk + full verify spine + surfaced queue | Richest verify spine: pending→review→apply-action→audit. `affects_*` flags + `claim_status` provide coverage semantics. |

---

## Pre-flight: Files Read to Fill This Matrix

| File | Purpose |
|---|---|
| `app/supabase/migrations/002_core_runtime_schema.sql` | `vacancies`, `notification_alerts`, `notification_preferences` table definitions |
| `app/supabase/migrations/015_*.sql` | Notification generation tables |
| `app/supabase/migrations/029_exam_intelligence_taxonomy.sql` | `subjects`, `topics` table definitions |
| `app/supabase/migrations/030_exam_registry_cycles_phases.sql` | `exam_families`, `exams`, `exam_cycles`, `exam_phases` table definitions |
| `app/supabase/migrations/032_pyq_question_intelligence.sql` | `pyq_sources`, `pyq_papers`, `pyq_questions`, `pyq_options`, `pyq_question_topic_tags` table definitions |
| `app/supabase/migrations/033_exam_competition_metrics.sql` | `exam_competition_metrics` (`vacancy_total` denormalized field) |
| `app/supabase/migrations/056_exam_policy_updates.sql` | `exam_policy_updates` table definition + `reviewer_status` enum |
| `app/supabase/migrations/075_*.sql` | `recruitment_verification_reports` (`staleness_status`, `last_checked_at`) |
| `app/supabase/migrations/083_add_staleness_fields.sql` | Staleness field additions |
| `app/supabase/migrations/167_exam_registry_conducting_org_calendar_status.sql` | `conducting_organization_id` + `organizations.calendar_status` |
| `app/backend/app/api/admin_exam_intel_cms.py` | All CMS CRUD endpoints + `/bulk-import` + `_IMPORT_CONFIG` + `_REVIEWABLE` guard |
| `app/backend/app/api/admin_exam_intelligence.py` | Review queue endpoints + `_REVIEWABLE` dict (lines 80–99) |
| `app/backend/app/api/admin_verification_reports.py` | Verification report apply-action endpoint |
| `app/backend/app/api/admin_notifications.py` (notifications.py) | Notification admin endpoints |
| `app/backend/app/exam_intelligence/registry_action_service.py` | `apply_cycle_date_update`, `apply_phase_date_update`, `apply_policy_update_*` action handlers |
| `app/backend/app/scraping/verification_gateway.py` | Scrape verification gateway |
| `app/backend/app/scraping/promotion_gate.py` | Scrape promotion gate |
| `app/backend/app/api/admin_scrape.py` | Scrape admin routes (vacancy population path) |
| `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx` | `ENTITY_CONFIG`, `EDITABLE_ENTITIES`, `DEACTIVATABLE_ENTITIES`, column definitions |
| `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` | Cycle + phase editor, `needsPhaseDateAuthoring()` worklist |
| `app/frontend/src/pages/admin/VerificationReports.jsx` | Verification reports operator surface |
| `app/frontend/src/routes/adminRoutes.jsx` | Admin route definitions |
| `app/frontend/src/lib/bulkImportFile.js` | Frontend CSV bulk import parser |
| `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/bulk-import/` | PYQ two-phase bulk import frontend |
| `AGENTS.md` | Repo context / agent instructions |
| `graphify-out/wiki/index.md` | Stale graph context (used for orientation only; all cells verified against live source) |
