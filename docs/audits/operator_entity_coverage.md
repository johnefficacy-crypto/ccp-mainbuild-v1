# Operator Entity Coverage Audit

**Branch requested:** `audit/operator-entity-coverage`
**Audit date:** 2026-06-07
**Mode:** read-only auditor. The only repository change is this audit document. The graph was used only for orientation after reading `graphify-out/GRAPH_REPORT.md`; every matrix cell below is based on live source files.

## Pre-flight findings: files read

- `AGENTS.md` — repo instructions and audit constraints.
- `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` — required orientation; treated as stale.
- `app/supabase/migrations/002_core_runtime_schema.sql` — core `vacancies`, `alert_events`, `notification_alerts`, `notification_preferences`, `notification_generation_runs`, and `notification_group_state` tables.
- `app/supabase/migrations/011_verified_domain_gap_p1.sql` — canonical `vacancy_reservations` table.
- `app/supabase/migrations/015_notifications_runtime_schema.sql` — notification runtime columns and admin read policies.
- `app/supabase/migrations/029_exam_intelligence_taxonomy.sql` — `subjects` and `topics` definitions.
- `app/supabase/migrations/030_exam_registry_cycles_phases.sql` — `exam_families`, `exams`, `exam_cycles`, `exam_phases`, `exam_phase_sections`, `exam_topic_coverage` definitions.
- `app/supabase/migrations/032_pyq_question_intelligence.sql` — `pyq_sources`, `pyq_papers`, `pyq_questions`, `pyq_options`, `pyq_question_topic_tags` definitions.
- `app/supabase/migrations/056_exam_policy_updates.sql` — `exam_policy_updates` definition and review/status checks.
- `app/supabase/migrations/103_pyq_options_review.sql` — later `pyq_options` review columns.
- `app/supabase/migrations/119_policy_updates_publish_status.sql` — `exam_policy_updates.publish_status` freshness/publish field.
- `app/supabase/migrations/165_exam_phase_structured_dates.sql` and `166_phase_window_flag_backfill.sql` — structured phase date fields and worklist metadata.
- `app/supabase/migrations/167_exam_registry_conducting_org_calendar_status.sql` — exam-to-organization calendar metadata.
- `app/supabase/migrations/170_exam_registry_actions.sql` — registry action audit table for verification-report applies.
- `app/backend/app/api/admin_exam_intel_cms.py` — CMS CRUD, entity import allowlist, PYQ bulk endpoints.
- `app/backend/app/api/admin_exam_intelligence.py` — review queues, review endpoints, overview counts/readiness.
- `app/backend/app/api/admin_verification_reports.py` — verification-gateway report listing/apply actions.
- `app/backend/app/api/admin_scrape.py` — scrape queue operator surface and freshness columns.
- `app/backend/app/api/notifications.py` — notification admin overview and generation run endpoints.
- `app/backend/app/exam_intelligence/registry_action_service.py` — single-sourced registry apply functions and audit logging.
- `app/backend/app/exam_intelligence/pyq_bulk_import.py` — PYQ preflight/commit bulk service.
- `app/backend/app/scraping/runner.py` — promotion path that persists vacancies.
- `app/backend/app/scraping/promotion_gate.py` and `app/backend/app/scraping/verification_gateway.py` — scrape verification/promotion gates.
- `app/frontend/src/routes/adminRoutes.jsx` — admin routes.
- `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx` — CMS entity config, create/edit, generic bulk UI.
- `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` — cycle/phase workspace editor and phase-date worklist.
- `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/PyqWorkbenchPanel.jsx` and `app/frontend/src/pages/admin/exam-workspace/pyq-workbench/bulk-import/useBulkImport.js` — PYQ bulk UI.
- `app/frontend/src/pages/admin/VerificationReports.jsx` — verification reports operator UI.
- `app/frontend/src/pages/admin/Notifications.jsx` — notification operator UI.
- `app/frontend/src/pages/admin/Scraper.jsx` and `app/frontend/src/pages/admin/OperationsConsole.jsx` — scrape queue operator UI.

## Entities that do not exist as standalone schema tables

| Requested entity | Schema finding | Evidence |
|---|---|---|
| `microtopic` | **No standalone table.** Microtopics are `public.topics` rows where `level = 'microtopic'`; the same table also allows `topic` and `concept`. | `app/supabase/migrations/029_exam_intelligence_taxonomy.sql:topics` creates `public.topics` with `parent_topic_id` and `level check (level in ('topic', 'microtopic', 'concept'))`. |
| `important_date` | **No standalone table.** Important dates are fields on `exam_cycles` (`notification_date`, `application_start`, `application_end`, `exam_start`, `exam_end`) and `exam_phases` (`phase_start`, `phase_end`). | `app/supabase/migrations/030_exam_registry_cycles_phases.sql:exam_cycles`; `app/supabase/migrations/165_exam_phase_structured_dates.sql:exam_phases.phase_start/phase_end`. |
| `notification` | **No single table named `notification`.** Runtime tables are `notification_alerts`, `notification_preferences`, `notification_generation_runs`, `notification_group_state`, plus `alert_events`. | `app/supabase/migrations/002_core_runtime_schema.sql:notification_*`; `app/supabase/migrations/015_notifications_runtime_schema.sql:notification runtime columns`. |
| `pyq` | **No standalone table named `pyq`.** The real hierarchy is `pyq_sources` → `pyq_papers` → `pyq_questions` → `pyq_options`, with `pyq_question_topic_tags` as question-topic mapping. | `app/supabase/migrations/032_pyq_question_intelligence.sql:pyq_* tables`. |
| `vacancy` | **`vacancies` exists, but the live richer promotion path writes `vacancy_reservations`.** This audit treats the requested entity as the vacancy data domain and cites both schema tables. | `app/supabase/migrations/002_core_runtime_schema.sql:vacancies`; `app/supabase/migrations/011_verified_domain_gap_p1.sql:vacancy_reservations`. |

## Coverage matrix

Legend: **YES** = explicit operator path exists; **PARTIAL** = only part of the requested column exists; **NO** = none found in live source.

| Entity | CREATE / EDIT UI | BULK IMPORT | VERIFY PIPELINE | FRESHNESS / COVERAGE |
|---|---|---|---|---|
| `exam_family` (`exam_families`) | **YES — create + edit.** CMS fields and columns are in `ExamIntelCms.jsx:ENTITY_CONFIG.exam-families`; the UI enables editing only for `exam-families`, `exams`, `exam-cycles`, and `exam-phases` via `EDITABLE_ENTITIES`; admin route is `/admin/exam-intelligence/cms`; backend routes are `admin_exam_intel_cms.py:list_exam_families`, `create_exam_family`, `update_exam_family`, `deactivate_exam_family`. | **YES.** Generic `admin_exam_intel_cms.py:bulk_import` includes `_IMPORT_CONFIG['exam-families']`; `ExamIntelCms.jsx:submitBulk` posts to `/api/admin/exam-intelligence-cms/bulk-import`. | **NO.** Table has no `reviewer_status`; `admin_exam_intelligence.py:_REVIEWABLE` includes only syllabus mentions, PYQ tags/questions/options; `registry_action_service.py` targets only cycle dates, phase dates, and policy updates. | **PARTIAL — field present, not surfaced as worklist.** `exam_families` has `updated_at`; CMS list columns show `created_at`, not `updated_at`, and no family freshness worklist was found. |
| `exam` (`exams`) | **YES — create + edit.** CMS fields are in `ExamIntelCms.jsx:ENTITY_CONFIG.exams`; edit is enabled by `EDITABLE_ENTITIES`; admin route is `/admin/exam-intelligence/cms`; backend routes are `list_exams`, `create_exam`, `update_exam`, `deactivate_exam`. | **YES.** `_IMPORT_CONFIG['exams']` supports generic `bulk_import`; CMS bulk UI posts to the same endpoint. | **NO.** `exams` has no `reviewer_status`; not present in `_REVIEWABLE`; no registry action function targets whole-exam rows. | **PARTIAL — fields nearby, not surfaced as exam worklist.** `exams` has `updated_at`; `conducting_organization_id` links to `organizations.calendar_status`, but the cited calendar status field is on organizations, not an exam-level operator worklist. |
| `exam_cycle` (`exam_cycles`) | **YES — create + edit.** CMS fields include dates/status in `ENTITY_CONFIG['exam-cycles']`; edit is enabled by `EDITABLE_ENTITIES`; `SetupPanel.jsx:createCycle` and `saveCycleEdit` also create/edit cycles; backend routes are `list_exam_cycles`, `create_exam_cycle`, `update_exam_cycle`. | **YES.** `_IMPORT_CONFIG['exam-cycles']` supports generic `bulk_import`. | **PARTIAL — registry-action target, not self-gated CMS entity.** `admin_verification_reports.py:apply_registry_action` dispatches `cycle_date_update` to `registry_action_service.py:apply_cycle_date_update` and records `exam_registry_actions`; `exam_cycles` itself has no `reviewer_status`. | **PARTIAL — fields surfaced inline, no dedicated freshness worklist.** `exam_cycles` has status/date fields and `updated_at`; `SetupPanel.jsx` renders cycle status/date editor, but no cycle-specific stale/missing-date worklist was found. |
| `exam_phase` (`exam_phases`) | **YES — create + edit.** CMS fields include phase dates/status in `ENTITY_CONFIG['exam-phases']`; edit is enabled by `EDITABLE_ENTITIES`; `SetupPanel.jsx:addPhase` and `patchPhaseDate` create/update phases; backend routes are `list_exam_phases`, `create_exam_phase`, `update_exam_phase`. | **YES.** `_IMPORT_CONFIG['exam-phases']` supports generic `bulk_import`. | **PARTIAL — registry-action target, not self-gated CMS entity.** `apply_registry_action` dispatches `phase_date_update` to `registry_action_service.py:apply_phase_date_update` and records `exam_registry_actions`; `exam_phases` itself has no `reviewer_status`. | **YES — surfaced worklist.** `exam_phases` has `phase_start`/`phase_end`; `SetupPanel.jsx:needsPhaseDateAuthoring` derives a missing-date worklist and renders “Phases needing dates.” |
| `subject` (`subjects`) | **PARTIAL — create backend + UI, backend edit exists, UI edit not exposed.** `ENTITY_CONFIG.subjects` defines a create form; backend has `list_subjects`, `create_subject`, `update_subject`; however `EDITABLE_ENTITIES` excludes `subjects`, so the CMS UI is create/list-only for subjects. | **YES.** `_IMPORT_CONFIG['subjects']` supports generic `bulk_import` and upserts by `slug`. | **NO.** `subjects` has no `reviewer_status`; not present in `_REVIEWABLE`; no registry action target. | **PARTIAL — field present, not surfaced as worklist.** `subjects` has `is_active` and `updated_at`; CMS columns show `is_active`, but no subject freshness/completeness dashboard was found. |
| `topic` (`topics`) | **PARTIAL — create backend + UI, backend edit exists, UI edit not exposed.** `ENTITY_CONFIG.topics` defines the form including `level`; backend has `list_topics`, `create_topic`, `update_topic`; `EDITABLE_ENTITIES` excludes `topics`, so CMS UI is create/list-only. | **YES.** `_IMPORT_CONFIG['topics']` supports generic `bulk_import` and upserts by `subject_id,parent_topic_id,slug`. | **NO.** `topics` has no `reviewer_status`; not present in `_REVIEWABLE`; no registry action target. | **PARTIAL — fields present, not topic-row freshness worklist.** `topics` has `is_active`/`updated_at`; exam topic coverage counts are surfaced in `admin_exam_intelligence.py:overview`, but that is coverage rows, not stale topic taxonomy rows. |
| `microtopic` (resolved as `topics.level='microtopic'`) | **PARTIAL — same as topic.** UI supports `level` values including `microtopic` and requires a parent for microtopic/concept in `ExamIntelCms.jsx:submitCreate`; backend edit exists through `update_topic`, but UI edit is excluded by `EDITABLE_ENTITIES`. | **YES.** Same `topics` bulk path via `_IMPORT_CONFIG['topics']`. | **NO.** Same as `topic`: no reviewer gate on taxonomy rows. | **PARTIAL — fields present, not surfaced as microtopic freshness.** Same `topics` `is_active`/`updated_at`; no microtopic-specific worklist found. |
| `pyq` (`pyq_sources`, `pyq_papers`, `pyq_questions`, `pyq_options`, `pyq_question_topic_tags`) | **PARTIAL — split by subentity.** CMS defines create forms for all five real PYQ entities; backend PATCH routes exist for all five. The generic CMS edit UI is not exposed because `EDITABLE_ENTITIES` excludes PYQ entities; the paper workspace route `/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace` provides a PYQ operator surface. | **YES.** Generic `_IMPORT_CONFIG` supports `pyq-papers`, `pyq-sources`, `pyq-question-topic-tags`, `pyq-questions` (with inline options), and `pyq-options`; specialized two-phase paper import uses `pyq_bulk_import.py:preflight` and `commit`, called by `useBulkImport.js`. | **PARTIAL / YES by child.** `pyq_questions`, `pyq_options`, and `pyq_question_topic_tags` are in `_REVIEWABLE` and reviewed by `review_item`; `pyq_question` review cascades to options via RPC. `pyq_sources` and `pyq_papers` use `trust_status` but are not in `_REVIEWABLE`. | **PARTIAL — surfaced for review queue, not every PYQ row.** Reviewable PYQ rows contribute status counts, low-confidence, stale-review counts, and user-facing readiness in `admin_exam_intelligence.py:overview`; `pyq_papers` show `trust_status` in CMS columns, but no paper/source freshness worklist was found. |
| `notification` (resolved notification runtime tables) | **PARTIAL — admin controls, not create/edit notification records.** `/admin/notifications` route renders `Notifications.jsx`; backend `notifications.py:admin_notifications` surfaces overview and `toggle_kill` updates kill switch, but no UI/backend path was found to create or edit individual `notification_alerts`. | **YES — generator batch path.** `notifications.py:generate_next_actions` inserts a `notification_generation_runs` row and can generate next-action alerts for one/all users; `Notifications.jsx:runNextActions` calls it. No CSV/paste import path found. | **NO for candidate→human gate→apply.** Notification generation is permissioned and audited through generation runs/kill switch, but no human verification spine for individual alerts was found. | **YES — surfaced operational freshness.** Admin overview returns `pending_dispatch`, `sent_24h`, `recent_generation`, and `recent_runs`; `Notifications.jsx` renders those counts and recent generation rows. |
| `important_date` (resolved cycle/phase date fields) | **YES through parent entities.** Cycle important dates are created/edited in `ENTITY_CONFIG['exam-cycles']` and `SetupPanel.jsx:createCycle/saveCycleEdit`; phase dates are created/edited in `ENTITY_CONFIG['exam-phases']` and `SetupPanel.jsx:addPhase/patchPhaseDate`. | **YES through parent entities.** Generic bulk import supports `exam-cycles` and `exam-phases` date fields. | **PARTIAL — verification-report apply path exists for cycle/phase date changes.** `apply_registry_action` supports `cycle_date_update` and `phase_date_update`; `exam_registry_actions` stores the report-tied action. Direct CMS date edits do not require this verification spine. | **YES for phase dates; PARTIAL for cycle dates.** Phase date gaps are surfaced by `SetupPanel.jsx:needsPhaseDateAuthoring` and the “Phases needing dates” worklist; cycle date/status fields are shown inline but no cycle missing-date worklist was found. |
| `vacancy` (`vacancies` / `vacancy_reservations`) | **NO standalone admin create/edit UI found.** `vacancies` and `vacancy_reservations` exist in schema, but no `ExamIntelCms.jsx` entity config or `admin_exam_intel_cms.py` route targets them; scrape queue UI operates on candidates before promotion, not direct vacancy rows. | **PARTIAL — live scrape/promotion ingestion, no CSV/paste import found.** Scrape extraction/promotion persists post vacancy data to `vacancy_reservations` via `runner.py:_persist_post_vacancies`; no direct vacancy bulk import endpoint was found. | **YES through scrape pipeline, not direct row review.** Scrape queue rows flow through field review and `evaluate_promotion_gate`; `promote_run` promotes gated candidates and writes `reviewed_at`/`promoted_recruitment_id`; vacancy rows themselves do not carry reviewer status. | **PARTIAL — source freshness surfaced, vacancy-row freshness not.** `scrape_queue` list selects `confidence_score`, `data_quality_score`, `reviewed_at`, `scraped_at`, and risk filters for operator freshness; `vacancy_reservations` only has `created_at`, and no vacancy-row freshness worklist was found. |
| `policy_update` (`exam_policy_updates`) | **PARTIAL — create UI, backend edit exists, UI edit not exposed.** CMS defines `ENTITY_CONFIG['policy-updates']`; backend has `create_policy_update` and `update_policy_update`; `EDITABLE_ENTITIES` excludes policy updates, so generic CMS edit UI is not exposed. Review UI exists under `/admin/exam-intelligence` via policy review endpoints. | **YES.** `_IMPORT_CONFIG['policy-updates']` supports generic `bulk_import` and forces `reviewer_status='pending'`. | **YES.** `admin_exam_intelligence.py:list_policy_updates` and `review_policy_update` provide pending/verified/rejected/needs-correction review; verification reports can also `policy_update_create` or `policy_update_edit` through `apply_registry_action`, with `exam_registry_actions` audit rows and `registry_action_service` audit logging. | **YES.** Schema has `claim_status`, `reviewer_status`, `reviewed_at`, `updated_at`, and `publish_status`; list endpoint filters by `reviewer_status`/`source_type`, and policy rows are surfaced in admin review. |

## Gap summary ranked by operator burden

Burden flags used here:

- **Manual-only / no direct bulk** — no direct CSV/paste/batch import for the resolved entity rows.
- **No verify spine** — no candidate → human gate → apply → audit path for the entity's live data.
- **No surfaced freshness** — stale/completeness fields exist, but no operator worklist/dashboard was found for the entity.

### Highest burden

| Entity | Burden flags | Factual basis |
|---|---|---|
| `exam_family` | No verify spine; no surfaced freshness | Has create/edit and bulk, but no reviewer gate and no family freshness worklist. |
| `exam` | No verify spine; no surfaced freshness | Has create/edit and bulk, but no whole-exam reviewer gate or exam-level staleness worklist. |
| `subject` | UI edit gap; no verify spine; no surfaced freshness | Backend edit exists, but CMS UI edit excludes subjects; no review/freshness worklist. |
| `topic` / `microtopic` | UI edit gap; no verify spine; no surfaced freshness | Backend edit exists, but CMS UI edit excludes topics; no taxonomy review/freshness worklist. |
| `vacancy` | No direct CRUD; no direct bulk; no vacancy-row freshness | Vacancy data is scrape/promotion-driven; operator reviews candidates/source fields, not direct vacancy rows. |

### Medium burden

| Entity | Burden flags | Factual basis |
|---|---|---|
| `exam_cycle` | Partial verify only; no dedicated surfaced freshness | Registry action can apply date updates from reports, but direct CMS edits are ungated and there is no cycle date-gap worklist. |
| `pyq` | Mixed verify/freshness by subentity | Questions/options/tags are reviewable; sources/papers are trust-status rows outside `_REVIEWABLE`, and source/paper freshness worklists were not found. |
| `important_date` | Parent-dependent verification; cycle freshness gap | Phase date gaps are surfaced; cycle date gaps are only inline fields. |
| `notification` | No individual-alert verify spine; no create/edit alert UI | Operational generation/run metrics are surfaced, but individual notification records are generated, not human-gated. |

### Lower burden

| Entity | Coverage status | Factual basis |
|---|---|---|
| `exam_phase` | UI + bulk + report-apply path + surfaced phase-date worklist | Best-covered registry row in this audit because missing structured phase dates have an explicit operator worklist. |
| `policy_update` | Bulk + review + report-apply/audit + surfaced status | Rich review and audit path; only generic CMS edit UI is not exposed. |
