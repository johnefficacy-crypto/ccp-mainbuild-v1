# Exam Cycle Setup Gate — D12–D16 Decision Record

- Decision IDs: D12, D13, D14, D15, D16
- Operator: johnefficacy-crypto
- Recorded date: 2026-06-23
- Parent gate: `docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md`
- Runtime effect: None. This record is documentation-only and does not authorize API, backend, frontend, migration, or test implementation.

## Status summary

| Decision | Status | Effect on parent register |
|---|---|---|
| D12 | APPROVED — MODE-AWARE SCOPE LOCKED | Supersedes the D12 unresolved row. |
| D13 | UNRESOLVED — OPERATOR DECISION REQUIRED | Remains unresolved; interim fail-closed prohibitions are locked. |
| D14 | APPROVED — MANAGEMENT-MODE BASELINE LOCKED | Supersedes the D14 unresolved row; cadence modifiers remain deferred. |
| D15 | APPROVED — TYPED REASON CODE REQUIRED | Supersedes the D15 unresolved row. |
| D16 | APPROVED — ENDPOINT-SCOPE CLARIFIED | Supersedes the D16 unresolved row. |

The parent I6 gate remains DRAFT. PR #761 must remain draft until the remaining decisions and all exit criteria are closed.

---

## D12 — Review & Activate minimum prerequisites

### Final resolution

Review & Activate has a mode-aware planner-activation minimum:

```text
planner_activation_minimum =
    selected cycle details complete
    AND required phases complete
    AND at least one applicable locked topic-coverage row exists
```

Locked topic coverage means exactly:

```text
exam_topic_coverage.reviewer_status = "locked"
```

It does not mean that a syllabus document, syllabus topic mention, extraction job, or other evidence row is locked.

### Mode application

| Management mode | D12 planner-activation minimum |
|---|---|
| `core` | Required. |
| `light` | Required only when the exam/cycle is exposed to Study OS or planner activation. |
| `index_only` | Not applicable; indexed reference retention must not require planner coverage. |
| `archive` | Not applicable; active planner activation is disabled. |
| `NULL` | Cannot evaluate; management-mode classification is required. |

### Scope boundary

D12 is a minimum gate, not the full activation contract. Other mode-applicable checklist steps may still block activation.

The existing catalogue classifier already hard-blocks when exam-wide phase count is zero or exam-wide locked coverage count is zero. D12 does not silently replace that classifier. It defines the minimum selected-cycle planner-activation contract for I9.

`exam_topic_coverage` already contains `exam_cycle_id`, `exam_phase_id`, and the lifecycle value `locked`. However, D08 still owns the rule for whether selected-cycle coverage may inherit an exam-wide row and how phase/cycle precedence works. Therefore:

```text
applicable locked coverage =
    a locked row accepted by the final D08 scope/inheritance contract
```

D12 must not be implemented by assuming either exact-cycle-only or unconditional exam-wide inheritance before D08 is resolved.

### Required-phase meaning

“Required phases complete” means all phases required by the approved D05 evidence policy and D14 management-mode applicability are present and satisfy their required cycle/phase facts. It is not satisfied merely by any arbitrary phase row when the approved policy requires more.

### No circular predicate

`review_activate` must not define itself by requiring every `cycle_readiness.steps[]` entry, including itself, to be complete. Implementations must evaluate its prerequisite inputs directly.

### Acceptance cases

- `core` + complete selected cycle + required phases + applicable locked coverage → D12 minimum passes.
- `core` + reviewed but not locked coverage → D12 minimum fails.
- `light` with planner activation disabled → D12 is not applicable.
- `light` with planner activation enabled and no applicable locked coverage → D12 minimum fails.
- `index_only` or `archive` → planner activation minimum is not applicable.
- Locked syllabus mention/document without locked `exam_topic_coverage` → D12 minimum fails.

---

## D13 — Manual completion override

### Status

```text
D13: UNRESOLVED — OPERATOR DECISION REQUIRED
```

No manual evidence-step completion may be implemented until the operator defines:

```text
permission
permitted step types
permitted exceptional cases
required reason
required evidence reference
expiry/revalidation behaviour
audit event shape
whether override affects planner output or UI only
```

### Interim fail-closed contract

Until D13 is approved:

- no “Mark complete” control;
- no manual-completion field;
- no implicit super-admin bypass;
- no completion inferred from notes, comments, metadata, or reason text;
- no override endpoint;
- no speculative audit schema;
- no planner-impact override;
- no UI-only completion override.

Evidence-derived steps must remain recomputable from canonical evidence. The unresolved state may not be bypassed by implementation convenience.

D13 remains the only `UNRESOLVED — OPERATOR DECISION REQUIRED` item in the D05/D13 E1 class.

---

## D14 — Management-mode baseline

### Final resolution

Adopt the management-mode baseline below. Cadence-specific modifiers are deferred.

| Mode | Baseline |
|---|---|
| `core` | Full cycle, phases, documents, extraction, syllabus coverage, PYQ, updates, competition, and activation workflow. |
| `light` | Essential cycle/phase facts, authoritative documents, and major updates; deeper syllabus, PYQ, competition, and planner activation are conditional. |
| `index_only` | Searchable identity, cycle facts, and source provenance; deep Study OS and planner-activation steps are not applicable. |
| `archive` | Preservation/reference checks only; no active readiness-production or planner-activation obligation. |
| `NULL` | No baseline may be inferred; classification is required. |

### Applicability is explicit

Every checklist step must expose one of:

```text
required
conditional
not_applicable
```

This applicability value is independent from status and weight. An implementation must not encode applicability only by setting `weight = 0`.

Recommended response shape:

```json
{
  "step_id": "competition_context",
  "applicability": "conditional",
  "status": "not_applicable"
}
```

### V1 step applicability matrix

| Step | `core` | `light` | `index_only` | `archive` |
|---|---|---|---|---|
| `cycle_details` | required | required | required | conditional |
| `phases_schedule` | required | required | conditional | conditional |
| `source_documents` | required | required | required | conditional |
| `extraction` | required | conditional | conditional | not_applicable |
| `syllabus_mapping` | required | conditional | not_applicable | not_applicable |
| `pyq_readiness` | required | conditional | not_applicable | not_applicable |
| `policy_updates` | required | required | conditional | conditional |
| `competition_context` | required | conditional | conditional | conditional |
| `review_activate` | required | conditional | not_applicable | not_applicable |

Matrix interpretation:

- A `conditional` step is evaluated only when its approved condition is true.
- D05 controls evidence/document conditions.
- D10 controls exam-wide PYQ corpus semantics.
- D11 controls conditional competition applicability and selected-cycle trust.
- D12 controls planner-activation minimums.
- D15 controls typed reasons when a conditional or optional step resolves to `not_applicable`.

### Cadence deferral

The values:

```text
annual
recurring
irregular
one_off
unknown
```

must not change the D14 baseline in the first implementation. No cadence-specific required/N-A rule may be inferred from recurrence, one-off status, unknown status, low ROI, or data absence.

Cadence modifiers require a separate approved contract after the management-mode baseline is stable.

### Archive clarification

Archive retention rules preserve existing source/evidence references but create no new activation or ingestion obligation. A conditional archive step may report preserved facts; it must not become an active production requirement.

---

## D15 — Typed `not_applicable` reason

### Final resolution

Every `not_applicable` state must include a stable machine-readable reason code.

```text
status == "not_applicable"
    → not_applicable_reason is required

status != "not_applicable"
    → not_applicable_reason is null
```

Canonical shape:

```json
{
  "status": "not_applicable",
  "not_applicable_reason": "optional_for_management_mode"
}
```

An optional display field may carry human-readable copy:

```json
{
  "not_applicable_reason": "archive_reference_only",
  "not_applicable_message": "Active competition maintenance is not required for archived exams."
}
```

The machine contract must never use an unrestricted sentence in place of the code.

### Initial reason-code vocabulary

```text
optional_for_management_mode
planner_activation_disabled
archive_reference_only
unsupported_exam_type
no_selected_cycle
```

This list is an initial typed vocabulary, not permission for arbitrary strings. New codes must be reviewed, documented, and added additively.

D11’s competition reason is:

```text
optional_for_management_mode
```

D15 supersedes D11’s temporary allowance to place that code only under `metrics.reason`: the canonical I9 step/check contract must expose `not_applicable_reason` directly on the object whose status is `not_applicable`.

### Validation requirements

- backend schema/model rejects or prevents N/A without a code;
- non-N/A objects serialize the field as `null`;
- frontend renders known codes through a label map and may fall back to a safe generic message for a newer unknown code;
- analytics and tests assert codes, not display messages.

---

## D16 — Invalid cycle versus backend failure

### Final resolution

The sibling `cycle_readiness_error` contract applies to the composite management-detail endpoint only.

Future composite endpoint shape:

```json
{
  "id": "exam-id",
  "current_cycle": null,
  "cycle_readiness": null,
  "cycle_readiness_error": {
    "code": "cycle_not_found",
    "requested_cycle_id": "invalid-cycle-id"
  }
}
```

### Composite management-detail HTTP behavior

```text
Exam exists + requested cycle absent
    → HTTP 200
    → cycle_readiness = null
    → cycle_readiness_error.code = "cycle_not_found"

Exam exists + requested cycle belongs to another exam
    → HTTP 200
    → same cycle_not_found code
    → do not reveal cross-exam ownership

Exam does not exist
    → HTTP 404

Critical database/network failure resolving exam or cycle catalogue
    → HTTP 5xx
```

The error object must be absent or `null` when cycle readiness is successfully computed.

### Advisory-readiness failure is distinct

The current management-detail endpoint intentionally treats `section_readiness` as advisory and fail-soft: a computation failure returns HTTP 200 with `section_readiness: null`.

D16 does not convert every advisory readiness failure into HTTP 5xx. It locks only these distinctions:

- critical exam/cycle resolution read failure → 5xx;
- invalid requested cycle → typed `cycle_not_found` under HTTP 200 on the composite endpoint;
- advisory readiness computation failure → HTTP 200 with null advisory field and no false `cycle_not_found` label.

A readiness computation exception must never be mapped to `cycle_not_found`.

### Dedicated readiness endpoint remains REST-strict

The dedicated resource retains its current semantics:

```text
/workspace/{exam_id}/readiness?cycle_id=unknown
    → HTTP 404

/workspace/{exam_id}/readiness?cycle_id=<cycle from another exam>
    → HTTP 422
```

D16 does not change the existing `/workspace/{exam_id}/context` or dedicated readiness validation behavior.

### Implementation requirements

The composite management-detail implementation must separate:

1. exam lookup;
2. cycle catalogue lookup;
3. requested-cycle validation;
4. advisory section-readiness computation;
5. future cycle-readiness computation.

Only step 3 produces `cycle_not_found`. Failures in steps 1–2 remain critical; failures in steps 4–5 use their own fail-soft/unavailable contract and must not masquerade as invalid selection.

### Acceptance cases

- existing exam + unknown cycle → 200, typed error object, no cycle readiness;
- existing exam + foreign cycle → same 200/code, no ownership leak;
- unknown exam → 404;
- cycle catalogue DB failure → 5xx;
- advisory section-readiness failure → 200, `section_readiness: null`, no cycle-not-found code;
- dedicated readiness unknown cycle → 404;
- dedicated readiness foreign cycle → 422.

---

## Expected implementation files

```text
app/backend/app/exam_intelligence/readiness.py
app/backend/app/exam_intelligence/management_read_model.py
app/backend/app/exam_intelligence/work_queue.py
app/backend/app/api/admin_exam_intelligence.py
app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx
app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx
app/backend/tests/exam_intelligence/test_readiness.py
app/backend/tests/exam_intelligence/test_management_read_model.py
app/backend/tests/exam_intelligence/test_work_queue.py
app/frontend/src/pages/admin/exam-workspace/panels/__tests__/ReviewActivatePanel.test.jsx
docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md
docs/status/career-copilot-checklist.md
```

No migration is required merely to record D12–D16. Runtime implementation may require schema work only where separately approved contracts demand it; D13 explicitly prohibits speculative override schema.

## Decision boundary

This record settles D12, D14, D15, and D16 as stated. D13 remains unresolved.

It does not settle:

- D01–D04 backend contract naming/version details;
- D06 extraction aggregation thresholds;
- D07 syllabus aggregation;
- D08 topic-coverage inheritance and exact scope;
- D13 override permissions and audit model;
- cadence-specific behavior.
