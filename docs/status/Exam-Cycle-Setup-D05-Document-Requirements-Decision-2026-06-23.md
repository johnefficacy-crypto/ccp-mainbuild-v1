# Exam Cycle Setup Gate — D05 Document Requirements Decision

- Decision ID: D05
- Status: APPROVED — PRODUCT POLICY LOCKED
- Approver: johnefficacy-crypto (operator)
- Approval date: 2026-06-23
- Parent gate: `docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md`
- Effect: This addendum supersedes only the D05 `UNRESOLVED — OPERATOR DECISION REQUIRED` row in the parent gate. The parent I6 gate remains DRAFT and PR #761 must remain draft until the remaining decisions and exit criteria are closed.
- Runtime effect: None. This is a documentation-only decision record; no migration, API, backend, frontend, or test change is authorized by this file.

## Final D05 resolution

Required exam evidence must be derived from:

```text
management_mode + exam_type + selected operational cycle + canonical phase_kind
```

Do not hardcode a separate requirement list for individual exam slugs.

The management-mode meanings remain:

| Mode | Meaning |
|---|---|
| `core` | Full readiness expected. |
| `light` | Essential operational management. |
| `index_only` | Searchable reference without deep Study OS readiness. |
| `archive` | Retained historical reference with no new activation work. |

`management_mode IS NULL` is not assigned a silent default. An unclassified exam requires operator action and cannot be treated as `core`, `light`, `index_only`, or `archive`.

## Mandatory evidence matrix

| Evidence class | `core` | `light` | `index_only` | `archive` |
|---|---|---|---|---|
| Verified official exam or organization source | Required | Required | Required | Preserve last verified source |
| Current notification or primary cycle document | Required for every selected operational cycle | Required when an operational cycle is exposed | Required only when dates, eligibility, application, or cycle status are displayed | No new requirement |
| Official syllabus | Required for every written phase | Required when Study OS or syllabus details are exposed | Not applicable | Preserve existing evidence |
| Official pattern or scheme | Required for every written phase | Required when pattern details are exposed | Not applicable | Preserve existing evidence |
| Corrigendum | Required when a verified source or operator record establishes that one was issued | Required when it changes displayed facts | Required when it changes indexed facts | Attach only to correct historical records |
| PYQ evidence | Minimum one verified compatible paper per active written phase; evidence from three recent exam years is recommended for trend intelligence | Optional; one recent compatible paper recommended | Not applicable | No new ingestion |
| Official answer key | Required for every objective PYQ used for scoring or correctness | Required for ingested objective PYQs used for scoring or correctness | Not applicable | Preserve existing evidence |
| Phase schedule or calendar | Required when dates are separately published | Required when active-cycle tracking is enabled | Required only when dates are displayed | No new requirement |
| Application instructions | Required when not contained in the primary cycle document | Required when application tracking is enabled | Link-only when application facts are displayed | No new requirement |

“Preserve existing” and “no new ingestion” are retention rules, not activation requirements. Archive exams do not enter a new activation workflow.

## Exam-purpose overlay

Source document names vary by `exam_type`, but normalize into common evidence classes:

| Exam purpose | Mandatory primary-cycle evidence |
|---|---|
| `recruitment` | Notification or detailed advertisement |
| `entrance` | Information bulletin or prospectus |
| `certification` | Candidate handbook or examination regulations |
| `opportunity` | Official call and programme guidelines |
| `other` | Operator-selected authoritative governing document |

An opportunity without a written examination must mark syllabus, PYQ, answer-key, and written-pattern requirements `not_applicable`, not `missing`.

## Phase-specific rules

A canonical `phase_kind` is required. It must not be permanently inferred from a phase slug, phase name, question count, negative marking, or the existing unconstrained `exam_phases.mode` field.

Proposed phase vocabulary for implementation:

```text
objective_written
descriptive_written
mixed_written
interview
physical_test
medical
document_verification
other
```

Evidence requirements:

| Phase kind | Required evidence |
|---|---|
| `objective_written` | Syllabus, pattern, compatible question-paper evidence, and official answer key when the PYQ is used for scoring or correctness |
| `descriptive_written` | Syllabus, pattern, and compatible question-paper evidence; answer key is `not_applicable` |
| `mixed_written` | Syllabus, pattern, compatible question-paper evidence, and answer key for objective components used for scoring |
| `interview`, `physical_test`, `medical`, `document_verification` | Official phase rules or standards; syllabus, PYQ, and answer key are `not_applicable` unless explicitly overridden |
| `other` or `NULL` | Requires operator classification before a blocking policy is applied |

## Independent evidence predicates

Document presence, source authority, human trust review, supersession, and extraction are separate predicates.

An evidence requirement is satisfied only when all predicates enabled by its policy pass:

1. It is associated with the correct exam and required exam/cycle/phase scope.
2. Its evidence role satisfies the normalized requirement class.
3. Its source is official or explicitly operator-approved.
4. Human trust review is verified when required.
5. It is not rejected, archived as unusable, or superseded by a newer governing record.
6. Its latest `document_processing_jobs` row for `job_type='text_extract'` is `succeeded` when downstream text use is required.

Trust verification must not be inferred from extraction success. Extraction success must not be inferred from trust verification.

## Current-source facts and implementation gaps

The current implementation does not satisfy this decision:

- `readiness.py` marks Documents ready when at least one admin exam-intelligence document has successful extraction. It does not evaluate a required evidence set.
- `work_queue.classify_exam` is management-mode-blind and applies phase and locked-coverage blockers to every exam.
- Admin uploads create `document_assets` rows and store exam, cycle, and phase identifiers in `metadata`; those rows do not have a human trust lifecycle or a relational supersession model.
- Current upload kinds are `syllabus`, `pyq_paper`, `notification`, `corrigendum`, and `answer_key`.
- `exam_phases` has no canonical phase-kind column.
- A single source PDF may satisfy multiple evidence roles, such as primary cycle document, application instructions, pattern, schedule, and eligibility rules.

## Required implementation model

The implementation must use a normalized evidence policy rather than a slug-specific matrix.

### 1. Canonical phase classification

Add a forward migration for a constrained `exam_phases.phase_kind` field. Existing rows may remain `NULL` until explicitly classified or safely backfilled. For operational `core` and `light` exams, an active unclassified phase produces operator action.

### 2. Policy table

Use an evidence-level policy table because some requirements are sources, links, cycle fields, or phase fields rather than uploaded documents:

```text
exam_evidence_requirements
- id
- management_mode
- exam_type nullable
- phase_kind nullable
- evidence_kind
- satisfied_by: document_asset | source_registry | cycle_fields | phase_fields | external_link
- requirement_level: required | recommended | not_applicable
- gate_effect: block | warn | none
- scope: exam | cycle | phase
- minimum_count
- minimum_distinct_years nullable
- lookback_years nullable
- requires_verified_source
- requires_human_review
- requires_extraction
- condition_code
- condition_params jsonb
- priority
- is_active
- created_at
- updated_at
```

Do not implement arbitrary executable expressions in `applies_when`. Use validated `condition_code` values and structured parameters. Candidate condition codes include:

```text
always
cycle_is_operational
cycle_dates_published
study_os_enabled
pattern_details_exposed
corrigendum_known
objective_pyq_used_for_scoring
application_tracking_enabled
```

Absence of a corrigendum row does not prove no corrigendum was issued. Conditional requirements must be activated by canonical source evidence or explicit operator state.

### 3. Relational document evidence registration

`document_assets` remains the storage and extraction shell. Add an exam-domain registration layer with relational scope and human review:

```text
exam_document_evidence
- id
- document_asset_id
- exam_id
- exam_cycle_id nullable
- exam_phase_id nullable
- source_registry_id nullable
- trust_status: pending | verified | rejected | superseded
- superseded_by_id nullable
- reviewed_by
- reviewed_at
- created_at
- updated_at
```

Readiness must use relational IDs rather than treating JSON metadata as the long-term canonical policy join.

### 4. Multiple evidence roles per source

A document may satisfy multiple requirement classes:

```text
exam_document_evidence_roles
- document_evidence_id
- evidence_kind
- exam_cycle_id nullable
- exam_phase_id nullable
```

Preserve display subtypes such as `information_bulletin`, `prospectus`, `candidate_handbook`, or `detailed_advertisement`, while normalizing them to `primary_cycle_document` for policy evaluation. Keep `exam_pattern` as a separate evidence role.

### 5. Narrow overrides

Per-exam exceptions are permitted only when the general matrix cannot express a legitimate case:

```text
exam_evidence_requirement_overrides
- id
- base_requirement_id nullable
- exam_id
- exam_cycle_id nullable
- exam_phase_id nullable
- evidence_kind
- requirement_level nullable
- gate_effect nullable
- minimum_count nullable
- minimum_distinct_years nullable
- requires_verified_source nullable
- requires_human_review nullable
- requires_extraction nullable
- condition_code nullable
- condition_params nullable
- reason
- created_by
- created_at
- expires_at nullable
```

Precedence is deterministic:

```text
phase override
> cycle override
> exam override
> exact management_mode + exam_type + phase_kind
> management_mode + exam_type
> management_mode + phase_kind
> management_mode default
```

### 6. Operational-cycle semantics

Operational-cycle policy applies to `expected`, `open`, and `active` cycles. `closed`, `completed`, and `cancelled` cycles use preservation/history rules unless explicitly reopened by policy.

### 7. Classifier integration

No second activation classifier is authorized.

A backend policy service may resolve and evaluate requirements, but `work_queue.classify_exam` must remain the single top-level verdict authority. The work-queue path must preserve its set-based, fail-closed behavior and must not add an unbounded query per exam.

`index_only` and `archive` exams must not be blocked for missing syllabus, topic coverage, or PYQ evidence. `management_mode IS NULL` remains blocking until classified. This classifier change overlaps D14 and cannot ship until D14 is resolved.

## Read-model shape

Use the locked section-state vocabulary rather than a new `blocked` section state:

```json
{
  "documents": {
    "state": "missing",
    "requires_action": true,
    "blocked_by": [],
    "blocking_requirement_count": 1,
    "requirements": [
      {
        "requirement_kind": "answer_key",
        "requirement_level": "required",
        "gate_effect": "block",
        "scope": "phase",
        "target_phase_id": "<phase-id>",
        "state": "missing",
        "present": false,
        "source_verified": false,
        "human_verified": false,
        "extraction_state": "not_applicable",
        "satisfied": false,
        "blocker_code": "required_answer_key_missing",
        "blocker": "Official answer key missing for the selected objective phase PYQ"
      }
    ]
  }
}
```

A requirement is satisfied only when its enabled policy predicates pass. A section is satisfied only when all blocking requirements are satisfied and `blocked_by` is empty.

## D05 decision boundary

D05 now settles the product policy for deriving evidence requirements. It does not authorize implementation until the remaining linked contracts are resolved, including:

- D06 extraction aggregation over the D05-required evidence set.
- D08/D10 evidence-scope and inheritance rules.
- D12 selected-cycle prerequisites versus the exam-scoped activation authority.
- D14 management-mode, `NULL`-mode, cadence, and classifier behavior.
- Final migration numbering from the live `schema_migrations` state.

## Expected implementation files

At minimum, implementation is expected to affect:

```text
app/backend/app/exam_intelligence/document_policy.py
app/backend/app/exam_intelligence/readiness.py
app/backend/app/exam_intelligence/work_queue.py
app/backend/app/exam_intelligence/management_read_model.py
app/backend/app/exam_intelligence/console_detail.py
app/backend/app/api/admin_exam_intel_documents.py
app/backend/app/api/admin_exam_intel_cms.py
app/frontend/src/pages/admin/studyos/ExamIntelDocuments.jsx
app/frontend/src/pages/admin/exam-workspace/panels/DocumentsPanel.jsx
app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx
app/backend/tests/exam_intelligence/test_document_policy.py
app/backend/tests/exam_intelligence/test_work_queue.py
app/backend/tests/exam_intelligence/test_management_read_model.py
app/frontend/src/pages/admin/studyos/ExamIntelDocuments.test.jsx
app/frontend/src/pages/admin/exam-workspace/panels/__tests__/DocumentsPanel.test.jsx
docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md
docs/status/career-copilot-checklist.md
app/supabase/migrations/<MAX(schema_migrations)+1>_exam_evidence_requirements.sql
```

Applied migrations remain immutable. The migration number must be determined from the live `schema_migrations` state and must be contiguous.
