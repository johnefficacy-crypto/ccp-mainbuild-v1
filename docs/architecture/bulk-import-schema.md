# Bulk import — JSON/CSV schema (UX-EI-4)

_Last updated: 2026-07-08_

Closes the documentation gap tracked as **UX-EI-4** in
`docs/status/career-copilot-checklist.md`: no in-repo doc described the
bulk-import request shape(s), required fields, or pre-requisites. This is
that document. Source of truth is the code below — re-derive from source if
the two ever disagree.

There are **two independent bulk-import surfaces** in the Exam Intelligence
CMS. They are not interchangeable and use different endpoints, different
request envelopes, and different commit semantics.

| Surface | Endpoint(s) | Frontend | Scope |
|---|---|---|---|
| A. Generic CMS bulk-import | `POST /api/admin/exam-intelligence-cms/bulk-import` | `ExamIntelCms.jsx` (`submitBulk`, JSON textarea / file picker) | One call per row-set of a single **CMS taxonomy/registry entity** (exam families, exams, cycles, phases, syllabus documents, PYQ papers, coverage, policy updates, competition metrics, subjects, topics, syllabus mentions, phase sections, PYQ topic tags, PYQ questions, PYQ options) |
| B. PYQ paper question importer | `POST /pyq-papers/{paper_id}/bulk-import/preflight` + `POST /pyq-papers/{paper_id}/bulk-import/commit` | `BulkImportModal.jsx` (`app/frontend/src/pages/admin/exam-workspace/pyq-workbench/bulk-import/`) | Questions (+ options, + v2 stimuli) for **one already-existing `pyq_papers` row**, via a two-step preflight/commit wizard with dedup |

Both require the `exam_intelligence.cms` permission (`PERM_CMS` in
`app/backend/app/api/admin_exam_intel_cms.py`) and the
`admin.study_os.enabled` feature flag (`_flag_enabled`); a disabled flag
returns `404`, not `403`.

---

## A. Generic CMS bulk-import

`POST /api/admin/exam-intelligence-cms/bulk-import`
(`admin_exam_intel_cms.py`, `bulk_import()`, function starts ~line 4223).

### Request body

```json
{
  "reason": "string, 8-500 chars, required",
  "entity": "string, one of the slugs below, required",
  "rows": [ { "...per-row payload, see entity table..." } ]
}
```

- `reason` — free-text audit justification. `min_length=8`, `max_length=500`.
- `entity` — a CMS slug (see table below). Unknown slug → `422` with
  `"Unknown entity '<x>'; known: [...]"`.
- `rows` — non-empty list, each item a JSON object (`min_length=1`, hard
  ceiling `max_length=4000` at the Pydantic level — `_MAX_BULK_CAP`). Each
  entity additionally enforces its own cap (`max_rows`, default 500) — a
  batch bigger than that entity's cap returns `422` with
  `"'<entity>' accepts at most <cap> rows per request; got <n>"`.

There is **no CSV support** on this endpoint — CSV files are parsed
client-side into a JSON row array before the request is sent (see
`app/frontend/src/lib/bulkImportFile.js`, used by `handleBulkFile` in
`ExamIntelCms.jsx`). The wire format is always the JSON envelope above.

### Per-row processing (`_validate_bulk_row` + `bulk_import`)

For every row, in order:

1. Row must be a JSON object, else `"row must be an object"`.
2. Unknown keys are silently dropped (only the entity's `allowed` field set
   is kept) — no error for extra fields, unlike the single-row create
   endpoints (which reject unknown fields with `422`).
3. Every `required` field must be present and not `None`/`""`, else
   `"missing required field '<field>'"`.
4. Every enum field, if present, must be one of its allowed values, else
   `"<field> must be one of [...]"`.
5. `exam_policy_updates` only: if `source_type != "official"`, none of
   `affects_plan` / `affects_deadline` / `affects_eligibility` /
   `affects_documents` / `affects_syllabus` / `affects_vacancy` may be
   truthy, else `"non-official policy update cannot set <field>=true"`.
6. Every FK field, if present, must resolve (`_safe_select` against the
   target table by `id`) — checked once per unique value per call via an
   in-call cache, so 500 rows referencing 10 exam_ids costs 10 lookups —
   else `"<field>=<value> does not resolve in <table>"`.
7. `forced` fields are set/overwritten unconditionally after validation
   (e.g. `trust_status` / `reviewer_status` always forced to `pending` or
   `pending_review` on entities that feed a review queue — bulk-import
   can never create pre-verified content).
8. Entity-specific `row_validator`, currently only on `pyq-papers`
   (EI-CLEAN-09 scope check, see below).
9. Insert (or `upsert(on_conflict=<upsert_on>)` for entities that declare
   one) into the target table. A DB-level exception is caught and reported
   as `"db: <first 200 chars of exception>"`.
10. If the entity declares an `inline` child spec (currently only
    `pyq-questions` → `options`), and the row payload carries an
    `options` array, each child is inserted against the freshly created
    parent id. If **any** child insert fails, the parent row is rolled
    back (`delete().eq("id", row["id"])`) and the whole row is reported as
    `"options insert failed"` with a `child_errors` array — there is no
    partial question-with-some-options state.

Each row is inserted **individually** (not one bulk INSERT) so one bad row
does not block the rows before or after it in the batch.

### Response

```json
{
  "ok": true,
  "audit_id": "uuid-or-null",
  "entity": "pyq-papers",
  "total": 3,
  "ok_count": 2,
  "error_count": 1,
  "results": [
    { "index": 0, "ok": true, "row": { "...inserted row..." } },
    { "index": 1, "ok": true, "row": { "...inserted row..." }, "children_created": 4 },
    { "index": 2, "ok": false, "error": "missing required field 'year'" }
  ]
}
```

`ok` is `true` only when `error_count == 0`. One `admin_audit_logs` row is
written per **call** (not per row), action `<entity>.bulk_create` (see
`audit` in the config table below), recording `reason`/`total`/`ok`/`errors`
— individual row payloads are not separately audited beyond what
`admin_audit_logs.new_value` captures.

### Supported entities, required fields, caps

Source: `_IMPORT_CONFIG` dict in `admin_exam_intel_cms.py` (~line 4010).
"Allowed fields" is the full write-allowlist for that entity (superset of
required); anything else in the row is dropped silently, not rejected.

| `entity` slug | table | required | enum fields (allowed values) | forced on insert | FK checks | upsert key | max rows |
|---|---|---|---|---|---|---|---|
| `exam-families` | `exam_families` | `slug`, `name` | — | — | — | — | 500 |
| `exams` | `exams` | `slug`, `name` | `exam_type`: recruitment/entrance/certification/opportunity/other | — | `exam_family_id` → `exam_families` | — | 500 — ⚠️ **not usable via bulk import today** (see note below) |
| `exam-cycles` | `exam_cycles` | `exam_id`, `year`, `cycle_name` | `status`: expected/open/active/closed/completed/cancelled | — | `exam_id` → `exams` | — | 500 |
| `exam-phases` | `exam_phases` | `exam_id`, `phase_name`, `phase_slug` | `status`: expected/active/completed/cancelled; `phase_kind`: classified kinds + `other` | — | `exam_id` → `exams` | — | 500 |
| `syllabus-documents` | `syllabus_documents` | `exam_id`, `document_type`, `title` | `document_type`: notification/syllabus_pdf/official_page/pattern_notice/corrigendum/other | `trust_status="pending"` | `exam_id` → `exams` | — | 500 |
| `pyq-papers` | `pyq_papers` | `exam_id`, `year` | `source_type`: official/memory_based/coaching/community/aggregator/unknown | `trust_status="pending"` | `exam_id` → `exams` | — | 500; **plus** `row_validator` = EI-CLEAN-09 scope check (below) |
| `exam-topic-coverage` | `exam_topic_coverage` | `exam_id`, `topic_id` | — | `reviewer_status="pending_review"` | `exam_id` → `exams` | — | 500 |
| `policy-updates` | `exam_policy_updates` | `exam_id`, `update_type`, `title` | `update_type`: notification_change/cycle_change/date_change/syllabus_change/pattern_change/vacancy_change/eligibility_change/reservation_change/document_rule_change/other | `reviewer_status="pending"` | `exam_id` → `exams` | — | 500; **plus** non-official `affects_*` check (above) |
| `exam-competition-metrics` | `exam_competition_metrics` | `exam_id` | `source_basis`: manual/official/reviewed_analysis/derived/model_generated | `reviewer_status="draft"` | `exam_id` → `exams` | — | 500 |
| `subjects` | `subjects` | `slug`, `name` | — | — | — | `slug` (idempotent re-import) | 500 |
| `topics` | `topics` | `subject_id`, `slug`, `name` | `level`: topic/microtopic/concept | — | `subject_id` → `subjects`, `parent_topic_id` → `topics` | `subject_id,parent_topic_id,slug` | 500 |
| `syllabus-topic-mentions` | `syllabus_topic_mentions` | `syllabus_document_id`, `exam_id`, `topic_id` | `mention_type`: explicit/implied/parent_topic_only/derived | `reviewer_status="pending"` | `syllabus_document_id` → `syllabus_documents`, `exam_id` → `exams`, `topic_id` → `topics` | — | 500 |
| `exam-phase-sections` | `exam_phase_sections` | `exam_phase_id`, `subject_id`, `section_label` | — | — | `exam_phase_id` → `exam_phases`, `subject_id` → `subjects` | `exam_phase_id,subject_id,section_label` | 500 |
| `pyq-question-topic-tags` | `pyq_question_topic_tags` | `question_id`, `topic_id` | `tag_role`: primary/secondary/prerequisite/trap/calculation_layer/conceptual_layer; `tagging_source`: manual/admin/ai/rule/imported | `reviewer_status="pending"` | `question_id` → `pyq_questions`, `topic_id` → `topics` | — | **2000** (20-year PYQ archives produce tens of thousands of tags) |
| `pyq-questions` | `pyq_questions` | `pyq_paper_id`, `question_text` | `question_type`: mcq/numerical/descriptive/caselet/matching/other | `reviewer_status="pending"` | `pyq_paper_id` → `pyq_papers` | — | **2000**; each row may carry an inline `options` array → child-inserted into `pyq_options` (see step 10 above) |
| `pyq-options` | `pyq_options` | `question_id` | — | — | `question_id` → `pyq_questions` | — | **4000** (~4 options/question over a 20-year archive) |

Full per-entity `allowed` field sets (everything else in a row is silently
dropped, not rejected):

- **exam-families** (`_FAMILY_FIELDS`): `slug`, `name`, `description`, `is_active`, `metadata`
- **exams** (`_EXAM_FIELDS`): `exam_family_id`, `name`, `exam_type`, `default_difficulty_level`, `description`, `is_active`, `metadata`, `conducting_organization_id`, `management_mode`, `cadence`
  - ⚠️ **`exams` bulk import is currently non-functional.** `_IMPORT_CONFIG["exams"]` marks `slug` **required**, but `slug` is **not** in `_EXAM_FIELDS` (allowed) because it is server-derived from `name` (+ conducting org) via `_exam_slug()` on the single-create path (`POST /exams`). `_validate_bulk_row()` strips every key not in `allowed` **before** the required-field check and the bulk path performs no per-row slug derivation, so `slug` is always missing → every `exams` row fails with `missing required field 'slug'`. Until the bulk path grows a per-row slug-derivation hook (mirroring the pyq-papers `row_validator` pattern), create exams via the single `POST /exams` endpoint or the Guided Exam Wizard, not bulk import. (Unlike `exam-families`/`subjects`/`topics`, whose allowed sets DO include a user-supplied `slug`, so their bulk import works.)
- **exam-cycles** (`_CYCLE_FIELDS`): `exam_id`, `year`, `cycle_name`, `status`, `notification_date`, `application_start`, `application_end`, `exam_start`, `exam_end`, `source_url`, `metadata`
- **exam-phases** (`_PHASE_FIELDS`): `exam_id`, `exam_cycle_id`, `phase_name`, `phase_slug`, `phase_order`, `mode`, `duration_mins`, `total_questions`, `total_marks`, `negative_marking`, `status`, `metadata`, `phase_start`, `phase_end`, `phase_kind`
- **syllabus-documents** (`_DOC_FIELDS`): `exam_id`, `exam_cycle_id`, `source_id`, `document_type`, `title`, `source_url`, `storage_path`, `content_hash`, `published_at`, `fetched_at`, `metadata`
- **pyq-papers** (`_PAPER_FIELDS`): `pyq_source_id`, `exam_id`, `exam_cycle_id`, `exam_phase_id`, `year`, `paper_date`, `shift`, `paper_code`, `source_url`, `source_type`, `source_document_id`, `content_hash`, `metadata`
- **exam-topic-coverage** (`_COVERAGE_FIELDS`): `exam_id`, `exam_cycle_id`, `exam_phase_id`, `section_id`, `topic_id`, `coverage_depth`, `expected_difficulty`, `exam_priority_score`, `is_high_yield`, `confidence_score`, `source_basis`, `reviewer_status`, `review_notes`, `metadata`
- **policy-updates** (`_POLICY_FIELDS`): `exam_id`, `exam_cycle_id`, `source_id`, `update_type`, `title`, `summary`, `source_url`, `source_type`, `claim_status`, `affects_plan`, `affects_deadline`, `affects_eligibility`, `affects_documents`, `affects_syllabus`, `affects_vacancy`, `change_summary`, `evidence`, `published_at`, `effective_from`
- **exam-competition-metrics** (`_COMPETITION_FIELDS`): `exam_id`, `exam_cycle_id`, `exam_phase_id`, `vacancy_total`, `vacancy_by_category`, `cutoff_by_category`, `difficulty_assessment`, `breakdown_complete`, `competition_pressure_score`, `source_basis`, `confidence_score`, `reviewer_notes`, `metadata` (legacy `applicant_count`/`cutoff_trend`/`difficulty_trend`/`selection_ratio`/`evidence_count` are deliberately excluded — server/lifecycle-controlled)
- **subjects** (`_SUBJECT_FIELDS`): `slug`, `name`, `subject_group`, `default_difficulty_level`, `description`, `is_active`, `metadata`
- **topics** (`_TOPIC_FIELDS`): `subject_id`, `parent_topic_id`, `slug`, `name`, `level`, `default_difficulty_level`, `description`, `is_active`, `metadata`
- **syllabus-topic-mentions** (`_MENTION_FIELDS`): `syllabus_document_id`, `exam_id`, `exam_cycle_id`, `exam_phase_id`, `topic_id`, `raw_text`, `normalized_text`, `mention_type`, `confidence_score`, `extraction_method`, `metadata`
- **exam-phase-sections** (`_SECTION_FIELDS`): `exam_phase_id`, `subject_id`, `section_label`, `question_count`, `marks`, `duration_mins`, `negative_marking`, `difficulty_level`, `weightage_percent`, `sort_order`, `metadata`
- **pyq-question-topic-tags** (`_PYQ_TAG_FIELDS`): `question_id`, `topic_id`, `tag_weight`, `tag_role`, `tagging_source`, `confidence_score`, `metadata`
- **pyq-questions** (`_QUESTION_FIELDS`): `pyq_paper_id`, `question_number`, `question_text`, `normalized_question_hash`, `question_type`, `explanation_text`, `observed_difficulty`, `expected_solve_time_sec`, `language`, `metadata`, `source_kind`, `source_document_id`, `source_page`, `source_regions`, `extractor_version`, `extraction_run_id`, `idempotency_key`, `content_hash`, `confidence_by_field`, `section_id`, `source_question_ref`, `display_order`; inline child `options` uses `_OPTION_FIELDS`
- **pyq-options** (`_OPTION_FIELDS | {"question_id"}`): `question_id`, `option_label`, `option_text`, `normalized_option_hash`, `normalized_value`, `is_correct`, `metadata`, `display_order`, `source_label`

### Pre-requisites — must the parent (cycle/phase/exam) already exist?

**Yes for every FK.** This endpoint never creates parent rows implicitly.
Every `fks` entry above must resolve to an existing row by `id`
*before* the child row import — there is no "create cycle/phase if
missing" behaviour anywhere in this path. If you are seeding a new exam
from scratch, entities must be bulk-imported **in dependency order**:
`exam-families` → `exams` → `exam-cycles` / `subjects` → `exam-phases` →
`topics` / `exam-phase-sections` → `syllabus-documents` / `pyq-papers` →
`pyq-questions` (+ inline `options`) → `pyq-question-topic-tags`.

`pyq-papers` additionally runs the **EI-CLEAN-09** scope validator
(`_pyq_paper_scope_error`) after the plain FK checks pass. It fails with
one of these exact error tokens (HTTP `422`, returned as the row's
`"error"` string):

- `exam_not_found` — supplied `exam_id` does not exist (redundant with the
  generic FK check but the token differs).
- `exam_cycle_not_found` — supplied `exam_cycle_id` does not exist.
- `exam_cycle_exam_mismatch` — the cycle belongs to a different exam.
- `exam_phase_not_found` — supplied `exam_phase_id` does not exist.
- `exam_phase_exam_mismatch` — the phase belongs to a different exam.
- `exam_phase_cycle_mismatch` — the phase is bound to a different cycle
  than the paper's `exam_cycle_id` (null-safe: an exam-level, cycle-less
  phase is a valid target for a cycle-less paper).

---

## B. PYQ paper question importer (preflight + commit)

Module: `app/backend/app/exam_intelligence/pyq_bulk_import.py`. Routes:
`admin_exam_intel_cms.py` lines ~1643-1724. Frontend wizard:
`BulkImportModal.jsx` + `useBulkImport.js` under
`app/frontend/src/pages/admin/exam-workspace/pyq-workbench/bulk-import/`.

This importer is scoped to **one existing `pyq_papers` row** (`{paper_id}`
in the URL — `404` if it doesn't resolve) and imports **questions, their
options, and (v2 only) shared stimuli** into that paper. It does **not**
create the paper itself — use surface A (`pyq-papers` entity) or the
single-row `POST /pyq-papers` endpoint first.

It is a two-call, token-mediated flow: **preflight never writes**; **commit**
consumes a one-shot `import_token` from preflight and performs the actual
inserts. This lets an operator review every row's fate before anything
lands in the DB.

### Step 1 — preflight

`POST /pyq-papers/{paper_id}/bulk-import/preflight`

- Body is **raw CSV or JSON bytes**, not a JSON envelope — the endpoint
  reads `request.body()` directly and dispatches on the `Content-Type`
  header (`text/csv` vs anything containing `json`). An empty body is
  `422`.
- Parses, validates every row, runs the dedup ladder, and returns a
  **preview** with an `import_token` — no DB writes happen here.
- Parse/structural failures (bad CSV headers, malformed v2 envelope, bad
  `stimuli` array) raise `ValueError` → `422` with `"parse failed: <msg>"`
  or a v2-envelope-specific message (see Format detection below).

Response:

```json
{
  "import_token": "32-hex-char one-shot token",
  "paper_id": "uuid",
  "total": 12,
  "format_version": 1,
  "summary": { "ok": 9, "error": 1, "duplicate": 1, "fuzzy": 1 },
  "rows": [
    {
      "row": 1,
      "status": "ok | error | duplicate | fuzzy",
      "messages": ["human-readable reason(s), only for error/duplicate/fuzzy"],
      "question_number": 3,
      "question_text": "truncated to 120 chars + …",
      "question_type": "mcq",
      "correct_option": "A",
      "observed_difficulty": "medium"
    }
  ]
}
```

(v2-format rows additionally carry `source_question_ref`,
`correct_option_label`, `section_ref`, `stimulus_refs` instead of
`correct_option`.)

The `import_token` is stored server-side in `pyq_import_tokens`
(migration `163_pyq_import_tokens.sql`) with a **1-hour TTL**
(`_DEFAULT_TTL_SEC = 3600`), scoped to `(token, paper_id)`. It is a bearer
capability — any actor holding the token string for the right `paper_id`
can commit it, not only the operator who ran preflight (documented,
intentional design choice, not a gap).

### Step 2 — commit

`POST /pyq-papers/{paper_id}/bulk-import/commit`

```json
{
  "import_token": "token from preflight, required",
  "override_errors": false,
  "reason": "string, defaults to \"bulk import commit\""
}
```

- `import_token` — required, must match the token from preflight **and**
  the same `paper_id` in the URL, unconsumed, unexpired. Otherwise `404`
  with `"import_token '<t>' not found for paper_id '<p>' (wrong paper,
  unknown token, or already consumed)"` (unknown/wrong-paper/already-
  consumed) or `"... has expired"` (expired). Claiming is atomic (a single
  `UPDATE ... WHERE consumed_at IS NULL`), so two concurrent commits on the
  same token can never both proceed.
- `override_errors` (default `false`) — when `false`, rows preflighted as
  `error` or `duplicate` are skipped (not committed); `fuzzy` rows are
  **always** committed unless they also carry an error. When `true`, error
  rows still cannot be committed if they have no parsed data (validation
  failures never produce usable row data no matter what) — the UI copy for
  this is literally *"Rows with missing required fields cannot be imported
  even with override."*
- `reason` — required by the frontend (`CommitConfirmation.jsx` disables
  the Commit button until non-empty) but only defaulted, not enforced
  non-empty, at the Pydantic level.
- A batch-level `ValueError` (e.g. a v2 stimulus `ref` already exists in
  this paper with **different** content than the retry is submitting) aborts
  the whole commit before any row writes, mapped to `422`.

Response:

```json
{
  "paper_id": "uuid",
  "committed": 9,
  "skipped": 2,
  "failed": 1,
  "per_row": [
    { "row": 1, "result": "committed", "question_number": 3, "question_id": "uuid" },
    { "row": 2, "result": "skipped", "reason": "duplicate", "question_number": 4 },
    { "row": 3, "result": "failed", "reason": "options insert failed: ...", "question_number": 5 }
  ]
}
```

`per_row[].reason` for `skipped` is one of: `validation_error`,
`duplicate`, `error`, `already_exists` (idempotent re-commit).

Commit is **idempotent**: a row whose `question_number` (v1) or
`source_question_ref`/`question_number` (v2) — or, uniformly for both
formats, `normalized_question_hash` — already exists in the paper is
silently skipped rather than duplicated, so retrying the same commit call
(e.g. after a timeout) is safe.

### Format detection and schema (`parse_bytes`)

Both CSV and JSON accept two contract versions. Version is auto-detected —
there is no explicit `format=` query param.

#### v1 (legacy) — fixed 4-option MCQ

**CSV** required columns (case-insensitive header match):
`question_number, question_text, option_a, option_b, option_c, option_d,
correct_option, question_type` (`observed_difficulty` optional). Missing
any → `422` `"CSV missing required columns: [...]"`.

**JSON**: a bare array of row objects with the same fields.

Per-row validation (`_validate_row`), errors accumulate (all reported, not
fail-fast):

| Field | Type | Required | Constraint |
|---|---|---|---|
| `question_number` | int | yes | must parse as int; must not repeat within the same upload |
| `question_text` | string | yes | non-empty after strip |
| `option_a`..`option_d` | string | yes (all 4) | non-empty after strip — **exactly 4 options, always A-D** |
| `correct_option` | string | yes | one of `A`/`B`/`C`/`D` |
| `question_type` | string | yes | one of `mcq`, `numerical`, `descriptive`, `caselet`, `matching`, `other` |
| `observed_difficulty` | string | no | one of `easy`, `medium`, `hard`, matched after `strip().lower()`; `null`/absent/blank all mean NULL and are accepted. Any other value is a row error — these three are the only values migration 239's projection to `mock_question_bank` recognises, and it rewrites anything else to `medium` without warning. |

#### v2 — variable option count, sections, shared stimuli

**JSON**: an object envelope:

```json
{
  "format_version": 2,
  "stimuli": [
    {
      "ref": "passage-04",
      "stimulus_type": "passage",
      "content_text": "...",
      "section_ref": "reasoning",
      "display_order": 1
    }
  ],
  "questions": [
    {
      "source_question_ref": "Q17",
      "display_order": 17,
      "section_ref": "reasoning",
      "stimulus_refs": ["passage-04"],
      "question_text": "...",
      "question_type": "mcq",
      "options": [
        { "label": "1", "source_label": "(1)", "text": "...", "display_order": 1 },
        { "label": "2", "source_label": "(2)", "text": "...", "display_order": 2 }
      ],
      "correct_option_label": "1",
      "observed_difficulty": "medium"
    }
  ]
}
```

- `format_version` must be the literal integer `2` (booleans explicitly
  rejected even though `bool` is an `int` subclass in Python) — otherwise
  `422` `'JSON v2 object must declare "format_version": 2; got <x>'`.
- `questions` must be a list, else `"JSON v2 object must include a
  'questions' list"`.
- `stimuli` is optional; if present, must be a list, else `"JSON v2
  'stimuli' must be a list"`.

**CSV v2** is detected by the presence of an `options_json` column
(instead of `option_a`..`option_d`): each row carries `options_json` (a
JSON-encoded array of `{"label", "source_label", "text",
"display_order"}` objects), plus `correct_option_label` and optionally
`source_question_ref`, `display_order`, `section_ref`. There is no
top-level `stimuli` array in the CSV path — stimulus_refs in CSV v2 are
lenient (JSON array or comma-separated string) but nothing in the CSV
payload can declare new stimuli metadata; use JSON v2 to import shared
stimuli.

Per-row fields (`_validate_row_v2`):

| Field | Type | Required | Constraint |
|---|---|---|---|
| `source_question_ref` | string | no | dedup key within the upload when present; also checked against existing DB rows in the paper |
| `question_number` | int | no | must parse as int if present; must not repeat within the upload |
| `display_order` | int | no | ≥1; must not repeat within the upload (preflight-time UX check only — the DB unique index is the real backstop) |
| `question_text` | string | yes | non-empty after strip |
| `question_type` | string | yes | **only `mcq` is currently importable** — any other value (`numerical`, `descriptive`, `caselet`, `matching`, `other`) is rejected with `"question_type '<x>' is not yet supported by the v2 importer; only 'mcq' is currently supported"` |
| `observed_difficulty` | string | no | one of `easy`, `medium`, `hard`, matched after `strip().lower()`; `null`/absent/blank all mean NULL and are accepted (same rule as v1) |
| `section_ref` | string | no | resolved case-insensitively against `exam_phase_sections.section_label` scoped to the paper's `exam_phase_id`; no match → error; 2+ matches (same label, different subject) → `"...is ambiguous..."` error |
| `stimulus_refs` | array of string | no | each ref must appear in the batch's own top-level `stimuli` array; duplicate refs within one question are rejected |
| `options` | array of object | yes | **2 or more** entries (not fixed at 4); each needs a non-empty, unique-within-question `label` and non-empty `text`; `display_order` optional (defaults to 1-based array position); `source_label` optional |
| `correct_option_label` | string | required only when `question_type == "mcq"` | must resolve to exactly one supplied option's `label` |

Top-level `stimuli[]` entries (`_validate_stimuli_batch`) — a structural
problem here fails the **whole batch**, not just one row, since a stimulus
is shared infrastructure:

| Field | Type | Required | Constraint |
|---|---|---|---|
| `ref` | string | yes | non-empty; unique within the `stimuli` array |
| `stimulus_type` | string | yes | importer currently only accepts `passage`, `caselet`, `table` (media types `chart`/`image`/`diagram`/`other` are DB-legal but not yet supported by *this importer* — use the single-row CMS stimulus endpoint for those, see `docs/architecture/pyq-media.md`) |
| `section_ref` | string | no | same resolution rule as per-question `section_ref` |
| `display_order` | int | no | ≥1; unique within the batch |
| `content_text` | string | no | — |
| `language` | string | no | — |

A `pyq_stimuli` row is created **once per `ref`** during commit (shared
across every question in the same commit call that references it) and
linked via `pyq_question_stimuli`; a retry that references an
already-durably-created ref (from an earlier, separate commit call) reuses
the existing row rather than creating a duplicate, **unless** the content
differs, in which case commit aborts (see above).

### Dedup ladder (both formats, preflight-time)

Applied in this order per row, first match wins:

1. **Same-upload duplicate** — exact normalized-text hash match against an
   earlier row in the *same* upload → `duplicate`, `"exact text match with
   row <n> earlier in this same upload"`.
2. **Exact DB duplicate** — normalized-text hash match against an existing
   row already in this paper → `duplicate`,
   `"exact text match with existing question_number <n> (id=<uuid>)"`.
3. **Identity duplicate** — v1: `question_number` already exists in the
   paper. v2: `source_question_ref` (if set) or else `question_number` (if
   set) already exists → `duplicate`.
4. **Fuzzy near-miss** — only checked when neither of the above fired:
   Levenshtein ratio ≥ 0.85 against an existing question's normalized text
   → `fuzzy`, `"near-duplicate (ratio=<r>) with existing question_number
   <n> (id=<uuid>)"`. `fuzzy` rows commit by default (not skipped like
   `duplicate`/`error`) unless `override_errors` semantics otherwise apply.

### Pre-requisites — must cycle/phase/section exist first?

- The **paper** (`pyq_papers` row) must already exist — this importer only
  ever inserts questions/options/stimuli into an existing paper; it never
  creates or modifies the paper row.
- **`exam_phase_sections`** must be pre-created if you want to use
  `section_ref` — the importer resolves against existing sections scoped
  to the paper's `exam_phase_id` and never creates one on the fly. Omitting
  `section_ref` is fine (question lands with no section).
- **Cycle/phase themselves** are not touched by this importer at all — they
  must already be set on the target `pyq_papers` row (via surface A or the
  single-row paper endpoints) before you bulk-import its questions.

---

## Minimal valid example payloads

### A. Generic bulk-import — create two exam cycles under an existing exam

> Note: `exams` itself is **not** bulk-importable today (server-derived `slug`; see
> the exams field-set note above). Create exams via `POST /exams` or the Guided
> Exam Wizard, then bulk-import their cycles/phases/etc. as shown here.

```json
POST /api/admin/exam-intelligence-cms/bulk-import
{
  "reason": "Seed SSC CGL 2025 and 2026 cycles",
  "entity": "exam-cycles",
  "rows": [
    { "exam_id": "8f2b...", "year": 2025, "cycle_name": "SSC CGL 2025" },
    { "exam_id": "8f2b...", "year": 2026, "cycle_name": "SSC CGL 2026" }
  ]
}
```

### B. PYQ paper importer — v1 CSV (preflight body)

```
question_number,question_text,option_a,option_b,option_c,option_d,correct_option,question_type,observed_difficulty
1,"What is 2+2?","3","4","5","6","B","mcq","easy"
```

Sent as `Content-Type: text/csv` raw bytes to
`POST /pyq-papers/{paper_id}/bulk-import/preflight`, then the returned
`import_token` is posted to `.../commit` with a `reason`.

### B. PYQ paper importer — v2 JSON (preflight body)

```json
{
  "format_version": 2,
  "stimuli": [],
  "questions": [
    {
      "source_question_ref": "Q1",
      "question_text": "What is 2+2?",
      "question_type": "mcq",
      "options": [
        { "label": "1", "text": "3" },
        { "label": "2", "text": "4" },
        { "label": "3", "text": "5" }
      ],
      "correct_option_label": "2"
    }
  ]
}
```

Sent as `Content-Type: application/json` to the same preflight endpoint.

---

## Related docs

- `docs/architecture/pyq-media.md` — media stimulus types (`image`/`chart`/
  `diagram`); explicitly **not** importable via the bulk paths above (single-
  row CMS stimulus endpoint only).
- `docs/architecture/pyq-intelligence-v2.md` — broader PYQ data-model
  architecture; does not itself describe the bulk-import wire schema.
- `docs/status/career-copilot-checklist.md` — UX-EI-4 row, now pointing here.
