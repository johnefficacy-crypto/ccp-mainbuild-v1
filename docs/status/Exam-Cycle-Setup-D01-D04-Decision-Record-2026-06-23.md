# Exam Cycle Setup Gate — D01–D04 Decision Record

- Decision IDs: D01, D02, D03, D04
- Operator: johnefficacy-crypto
- Approval date: 2026-06-23
- Parent gate: `docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md`
- Runtime effect: None. This record is documentation-only and does not authorize backend, frontend, API, migration, or test implementation.

## Status summary

| Decision | Status | Final resolution |
|---|---|---|
| D01 | APPROVED — COMPATIBILITY MIGRATION LOCKED | Extend the existing composite management-detail endpoint with cycle readiness. Do not create another endpoint. |
| D02 | APPROVED — FIELD NAME LOCKED | Canonical field name is `cycle_readiness`. |
| D03 | APPROVED — ORIGINAL PROPOSAL REJECTED AND AMENDED | Use the already locked section/task-state vocabulary; do not use `complete`, `incomplete`, `needs_action`, or `blocked` as checklist-step states. |
| D04 | APPROVED — FAIL-CLOSED VERSION HANDLING LOCKED | Add top-level integer `contract_version`; unsupported versions must not be interpreted by the frontend. |

This record supersedes only D01–D04 and the conflicting proposed-contract wording tied to those decisions. The parent I6 gate remains DRAFT. PR #761 must remain draft until D06–D08, D13, and all exit criteria are closed.

---

## D01 — Extend the composite management-detail endpoint

### Final resolution

Use the existing endpoint:

```http
GET /api/admin/exam-intelligence/management/exams/{exam_id}?cycle_id={cycle_id}
```

Add the canonical `cycle_readiness` object to this response. Do not create another management or cycle-readiness endpoint for I9.

The existing management-detail read model already combines:

- exam identity and management metadata;
- selected/current cycle;
- all cycles and their phases;
- top-level classifier verdict and flags;
- action queue and activation checks;
- advisory section readiness.

A second canonical endpoint would duplicate selected-cycle resolution, failure semantics, classifier context, and frontend loading state.

### Frontend convergence

The canonical Manage Exam frontend currently performs three independent requests:

```text
/workspace/{exam_id}/context
/workspace/{exam_id}/readiness
/management/exams/{exam_id}
```

D01 locks the target state as one canonical management-detail request for identity, cycle navigation, cycle readiness, verdict, and actions.

### Compatibility migration order

```text
1. Backend adds contract_version, cycle_readiness, cycle_readiness_error,
   and the temporary section_readiness alias to management detail.
2. Frontend supports and then adopts the management-detail response.
3. Existing /workspace/{exam_id}/context and /readiness routes remain
   temporarily for compatibility and existing tests/consumers.
4. Migrate all canonical Manage Exam callers and tests.
5. Remove legacy routes only in a separate cleanup after usage is proven absent.
```

Do not delete or change the REST behavior of the existing dedicated readiness endpoint as part of the initial D01 implementation. D16 continues to govern the endpoint-specific invalid-cycle behavior.

### Source-backed rationale

`management_read_model.get_management_exam_detail()` already accepts `cycle_id`, resolves the backend-selected current cycle when absent, and returns `current_cycle`, `cycles`, `section_readiness`, `activation_verdict`, `activation_checks`, and `action_queue`.

`ExamWorkspaceContext.jsx` currently issues all three requests separately. D01 authorizes convergence; it does not authorize premature route deletion.

---

## D02 — Canonical field and cycle semantics

### Field name

```json
{
  "cycle_readiness": {
    "cycle_id": "cycle-uuid",
    "steps": []
  }
}
```

The canonical field name is exactly:

```text
cycle_readiness
```

Do not add a competing alias such as `activation_readiness`, `setup_progress`, `cycle_progress`, or another endpoint-specific name.

### Selected-cycle semantics

- Explicit `cycle_id` supplied: `cycle_readiness` represents that requested cycle when valid.
- No `cycle_id` supplied: `cycle_readiness` represents the deterministic current cycle selected by the backend.
- No available cycle: `cycle_readiness` is `null` or contains no cycle only according to the approved D15/D16 no-cycle/error contract; the frontend must not independently choose another initial cycle.
- The backend cycle selector remains the sole authority for the initial/current cycle.

### Temporary compatibility alias

During migration, management detail returns:

```json
{
  "cycle_readiness": { "...": "canonical object" },
  "section_readiness": { "...": "temporary identical alias" }
}
```

Both fields must be produced from the same computed object in one request path. They must be structurally and semantically identical for the migration period and must never be independently computed.

`section_readiness` is deprecated immediately when this alias ships. It is removed only after the canonical frontend and tests consume `cycle_readiness`.

This alias is separate from the legacy `/workspace/{exam_id}/readiness` route, which remains temporarily available under D01.

---

## D03 — Locked checklist-step status vocabulary

### Rejected proposal

Do not use this proposed enum:

```text
complete
incomplete
needs_action
not_applicable
blocked
```

It mixes completion, evidence lifecycle, workflow urgency, activation authority, and applicability.

### Canonical step/check status enum

Every `cycle_readiness.steps[].status` and `checks[].status` must use exactly:

```text
missing
uploaded
extracting
review_pending
ready
stale
failed
not_applicable
```

No additional step-state token may be introduced without a breaking contract-version decision.

### Concept separation

| Concept | Canonical representation |
|---|---|
| Evidence/task state | Locked eight-value step/check enum above |
| Corrective urgency | Action queue item, blocker metadata, severity, or CTA; not step status |
| Activation authority | Top-level `blocked | needs_action | ready` verdict from `work_queue.classify_exam` |
| Applicability | Explicit `required | conditional | not_applicable` plus D15 typed reason when N/A |

### Mapping from rejected proposal

| Rejected value | Correct representation |
|---|---|
| `complete` | `ready` |
| `incomplete` | Actual evidence state: `missing`, `uploaded`, `extracting`, `review_pending`, `stale`, or `failed` |
| `needs_action` | Action queue/blocker metadata while status remains the actual evidence state |
| `blocked` | Top-level activation verdict or prerequisite/blocker metadata; never a step/check status |
| `not_applicable` | `not_applicable` with required typed `not_applicable_reason` |

### Dependency handling

A prerequisite failure must not synthesize a `blocked` step status.

- The failed prerequisite reports its real evidence state.
- A downstream cycle-specific step that cannot be evaluated without a selected cycle may report `not_applicable` with `not_applicable_reason = "no_selected_cycle"` when that code applies.
- Otherwise, the downstream step reports its own evidence state and carries prerequisite/blocker metadata separately.
- The backend top-level verdict remains responsible for activation blocking.

### Aggregation requirement

The parent gate’s aggregation rules written in terms of `complete`, `incomplete`, `needs_action`, and `blocked` are superseded. Implementation must aggregate check evidence into the locked state vocabulary and emit corrective actions separately.

A step cannot be reported `ready` if a required contributing check is `missing`, `uploaded`, `extracting`, `review_pending`, `stale`, or `failed`.

`not_applicable` follows D14/D15 applicability and typed-reason rules; it is not a synonym for successful evidence completion.

### Classifier authority

The top-level management verdict remains:

```text
blocked | needs_action | ready
```

It continues to come from `work_queue.classify_exam`. `cycle_readiness` does not create a second frontend or backend activation classifier, and readiness score percentages do not authorize activation.

---

## D04 — Top-level contract version and fail-closed frontend behavior

### Canonical placement

```json
{
  "contract_version": 1,
  "cycle_readiness": {
    "cycle_id": "cycle-uuid",
    "steps": []
  },
  "cycle_readiness_error": null
}
```

`contract_version` is a required top-level integer on the composite management-detail response.

The parent proposal that placed `contract_version` inside `cycle_readiness` is superseded. Do not duplicate the version in both locations in version 1.

### Version rules

```text
contract_version = 1
```

- Increment only for breaking structural or semantic changes.
- Additive optional fields do not require an increment.
- The version applies to the composite management-detail response contract, including cycle readiness, errors, verdict/action fields consumed by canonical Manage Exam, and their semantics.
- Backend returns the field on every successful management-detail response after rollout, including no-cycle and typed invalid-cycle responses.
- Tests pin the supported version and critical semantic invariants.

### Fail-closed frontend handling

```js
const SUPPORTED_CONTRACT_VERSIONS = new Set([1]);

if (!SUPPORTED_CONTRACT_VERSIONS.has(data.contract_version)) {
  // Preserve safe identity/navigation only.
  // Do not interpret readiness, blockers, verdict actions, or activation state.
}
```

For an absent, invalid, or unsupported contract version, the frontend must:

- render only safe identity and cycle-navigation information whose structure is independently validated;
- not infer checklist statuses;
- not calculate activation authority;
- not render potentially incorrect blocker or activation CTAs;
- not fall back to interpreting the response as version 1;
- show an inline compatibility error;
- retain retry/reload capability;
- log diagnostics without exposing sensitive identifiers unnecessarily.

A warning while continuing to interpret unknown semantics is prohibited.

### Compatibility alias and version

`cycle_readiness` and deprecated `section_readiness` are interpreted only when the top-level version is supported. Both aliases must serialize the same canonical object.

The legacy direct readiness endpoint may remain unversioned during the compatibility period because it is not the canonical post-D01 Manage Exam contract. Its eventual removal is a separate cleanup.

---

## Required acceptance tests

### D01/D02

- Management detail returns canonical `cycle_readiness` for explicit valid cycle.
- Without cycle query, returned cycle matches backend deterministic current-cycle selection.
- No frontend code independently selects a different initial cycle.
- `section_readiness` and `cycle_readiness` are deeply equal and originate from one computation during migration.
- Canonical Manage Exam can render from management detail without context/readiness requests.
- Legacy context/readiness routes remain functional until separate cleanup.

### D03

- Every step/check status belongs to the locked eight-value enum.
- No step/check emits `complete`, `incomplete`, `needs_action`, or `blocked`.
- Failed extraction remains `failed`, with action metadata rather than `needs_action` status.
- Pending review remains `review_pending`.
- Top-level verdict still matches `work_queue.classify_exam`.
- Frontend does not reconstruct activation authority from step statuses.

### D04

- Successful management-detail responses include integer `contract_version: 1`.
- Version is top-level and not duplicated inside cycle readiness.
- Supported version renders canonical readiness/verdict/actions.
- Missing, malformed, or unsupported version renders identity/navigation only and suppresses readiness and activation interpretation.
- Unsupported version produces inline compatibility error and diagnostics.
- Typed D16 invalid-cycle HTTP 200 response still includes `contract_version`.

---

## Expected implementation files

```text
app/backend/app/exam_intelligence/management_read_model.py
app/backend/app/exam_intelligence/readiness.py
app/backend/app/exam_intelligence/work_queue.py
app/backend/app/api/admin_exam_intelligence.py
app/frontend/src/pages/admin/exam-workspace/ExamWorkspaceContext.jsx
app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx
app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx
app/backend/tests/exam_intelligence/test_management_read_model.py
app/backend/tests/exam_intelligence/test_readiness.py
app/frontend/src/pages/admin/exam-workspace/__tests__/ExamWorkspaceContext.test.jsx
app/frontend/src/pages/admin/exam-workspace/__tests__/ExamWorkspace.test.jsx
docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md
docs/status/career-copilot-checklist.md
```

## Decision boundary

D01–D04 settle:

- one canonical composite management-detail endpoint;
- `cycle_readiness` field naming and backend-selected cycle semantics;
- temporary identical `section_readiness` alias;
- locked section/task-state vocabulary;
- separation of step state, action urgency, applicability, and activation verdict;
- top-level contract versioning and fail-closed frontend handling.

They do not settle:

- D06 extraction aggregation over required evidence;
- D07 syllabus aggregation details under the corrected vocabulary;
- D08 topic-coverage inheritance/scope;
- D13 manual completion overrides;
- runtime implementation or legacy-route removal timing.
