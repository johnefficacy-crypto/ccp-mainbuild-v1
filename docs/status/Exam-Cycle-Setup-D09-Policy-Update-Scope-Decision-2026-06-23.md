# Exam Cycle Setup Gate — D09 Policy Update Scope Decision

- Decision ID: D09
- Status: APPROVED — PRODUCT POLICY LOCKED
- Approver: johnefficacy-crypto (operator)
- Approval date: 2026-06-23
- Parent gate: `docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md`
- Effect: This addendum supersedes only the D09 row in the parent gate. The parent I6 gate remains DRAFT and PR #761 must remain draft until the remaining decisions and exit criteria are closed.
- Runtime effect: None. This is a documentation-only decision record; no API, backend, frontend, migration, cache, or test behavior is changed by this file.

## Final D09 resolution

For an exam-scoped consumer, applicable policy updates are selected by exam and cycle scope:

```sql
exam_id = :exam_id
AND (
  exam_cycle_id = :selected_cycle_id
  OR exam_cycle_id IS NULL
)
```

Semantics:

- `exam_cycle_id = selected_cycle_id` applies only to the selected cycle.
- `exam_cycle_id IS NULL` is exam-wide and applies to every cycle of that exam.
- Rows linked to a different cycle are excluded.
- When an exam is selected but no cycle is selected, return only exam-wide rows.
- Never treat “no selected cycle” as permission to mix every historical and future cycle-specific row.

This scope rule is applied before reviewer-status, source-type, claim-status, publication, or planner-impact filtering. D09 defines applicability scope; it does not collapse the independent trust/review lifecycle.

## Schema decision

No migration is required for the D09 scope itself.

The current schema already provides:

- nullable `exam_policy_updates.exam_cycle_id`;
- foreign keys to `exams` and `exam_cycles`;
- index `idx_exam_policy_updates_exam` on `(exam_id, exam_cycle_id, published_at desc)`.

A selected `cycle_id` must be validated as belonging to the supplied `exam_id` before scoped reads or writes execute.

## Shared backend rule

Implement one reusable helper in a neutral exam-intelligence module, for example:

```python
def apply_policy_cycle_scope(query, cycle_id: str | None):
    if cycle_id:
        return query.or_(
            f"exam_cycle_id.eq.{cycle_id},exam_cycle_id.is.null"
        )
    return query.is_("exam_cycle_id", "null")
```

Recommended module:

```text
app/backend/app/exam_intelligence/policy_scope.py
```

The helper must be reused by readiness, exam-scoped admin reads, Study OS policy context, and any future selected-cycle policy consumer. Do not duplicate subtly different predicates.

## Global admin review exception

The existing admin endpoint permits a global review list with no `exam_id`. That is not an exam-scoped consumer.

Contract:

- `exam_id + cycle_id` → selected-cycle rows plus exam-wide rows.
- `exam_id` without `cycle_id` → exam-wide rows only.
- `cycle_id` without `exam_id` → reject with HTTP 422 because ownership cannot be validated.
- no `exam_id` and no `cycle_id` → the explicit global repair/review list may retain all rows across exams and cycles; every row must expose its derived scope.

This exception prevents the selected-exam rule from unintentionally removing cycle-specific rows from the global review queue.

## Derived response scope

Every exam-scoped admin/readiness item must expose:

```json
{
  "scope": "cycle",
  "exam_cycle_id": "<cycle-id>"
}
```

or:

```json
{
  "scope": "exam_wide",
  "exam_cycle_id": null
}
```

`scope` is derived from `exam_cycle_id`; it is not independently writable.

## Current implementation gaps

### 1. Readiness scope is incorrect

`readiness.py::_updates()` currently applies exact cycle equality when a cycle is selected, which excludes exam-wide rows. When no cycle is selected, it currently reads all cycle-specific history for the exam. Both paths violate D09.

Required behavior:

```text
selected cycle → selected-cycle OR NULL
no selected cycle → NULL only
```

### 2. Admin review endpoint is not cycle-aware

`GET /api/admin/exam-intelligence/policy-updates` accepts `exam_id`, status, and source type, but no `cycle_id`. An exam-scoped call therefore returns all cycles.

Add `cycle_id: str | None = Query(None)`, validate cycle ownership, apply the shared rule for exam-scoped requests, and return derived scope.

### 3. Workspace ignores selected cycle

`UpdatesPanel.jsx` currently reads only `exam` from `useExamWorkspace()`, requests only `exam_id`, and does not label scope.

New updates created through this panel omit `exam_cycle_id`, making them exam-wide implicitly. The operator must choose scope explicitly:

```text
Apply to:
- Selected cycle
- Every cycle of this exam
```

Selected-cycle payload:

```json
{
  "exam_id": "<exam-id>",
  "exam_cycle_id": "<selected-cycle-id>"
}
```

Exam-wide payload:

```json
{
  "exam_id": "<exam-id>",
  "exam_cycle_id": null
}
```

If no cycle is selected, the selected-cycle option is disabled and the UI must not silently invent a cycle.

### 4. CMS writes do not validate cycle ownership

`admin_exam_intel_cms.py::create_policy_update()` currently accepts `exam_cycle_id` through the allowlist but does not verify that the cycle belongs to `exam_id`.

Create and update paths must reject an exam/cycle mismatch with HTTP 422 before writing.

### 5. Study OS policy context is exam-wide across all cycles

`policy_update_context(supabase, exam_id)` currently reads every policy row for the exam. Its contract must become:

```python
policy_update_context(supabase, exam_id, cycle_id)
```

Only applicable rows may enter either the official-update channel or the discovery channel. Only applicable trusted rows may contribute `affects_*` flags.

D09 does not redefine the existing trust gates. Plan-affecting rows remain subject to the independent official-source and reviewer-verification rules. Supersession handling remains a lifecycle concern and must not be inferred from cycle scope.

### 6. Planner does not pass or persist cycle provenance

`planner.py::_compute_plan()` already calls `resolve_exam_target_window()`, whose result contains `cycle_id`, but it currently calls `policy_update_context(supabase, exam_id)` without that cycle.

The planner must:

1. pass `resolver_result["cycle_id"]` to `policy_update_context`;
2. include that cycle in the generation context;
3. persist it to `study_plans.exam_cycle_id` on plan creation and regeneration;
4. propagate it to generated `study_tasks.exam_cycle_id` where applicable.

The schema already contains `study_plans.exam_cycle_id` and `study_tasks.exam_cycle_id`; no D09 migration is needed for these columns.

### 7. Mission Control cache is not cycle-aware

Mission Control currently caches policy context as:

```python
("policy_update_context", exam_id)
```

It must cache as:

```python
("policy_update_context", exam_id, cycle_id)
```

The active-plan loader must select and return `exam_id` and `exam_cycle_id`. Mission Control must use the active plan’s persisted cycle when the plan belongs to the same exam.

Legacy plans with `exam_cycle_id IS NULL` receive exam-wide updates only. They must not fall back to mixing all cycle-specific rows. A plan regeneration may populate the canonical cycle through the planner resolver.

## Frontend contract

`UpdatesPanel.jsx` must:

- read both `exam` and `cycle` from workspace context;
- request `exam_id` and selected `cycle_id`;
- show a scope badge for every row: `Current cycle` or `Exam-wide`;
- require explicit scope on create;
- include `exam_cycle_id` in the create payload;
- reset/reload when selected cycle changes;
- preserve deep-link behavior and show a truthful not-found message when a row belongs to another cycle.

## Acceptance tests

Core scope matrix:

| Selected cycle | Row cycle | Included |
|---|---|---:|
| Cycle A | Cycle A | Yes |
| Cycle A | `NULL` | Yes |
| Cycle A | Cycle B | No |
| No cycle | `NULL` | Yes |
| No cycle | Cycle A | No |

Also test:

- selected cycle ownership is validated against the exam;
- `cycle_id` without `exam_id` is rejected for exam-scoped admin reads;
- global admin review without exam scope still returns all reviewable rows and labels each scope;
- exam-wide verified official updates contribute to Study OS impact flags;
- selected-cycle verified official updates contribute;
- other-cycle verified official updates do not contribute;
- non-official or unverified rows do not gain plan authority because of scope;
- Cycle A and Cycle B use distinct cache entries;
- a legacy active plan with no cycle receives only exam-wide updates;
- planner persistence writes the resolver cycle to the plan and generated tasks;
- workspace creation sends explicit cycle or `null` scope;
- workspace rows display `Current cycle` or `Exam-wide`.

## Expected implementation files

```text
app/backend/app/exam_intelligence/policy_scope.py
app/backend/app/exam_intelligence/readiness.py
app/backend/app/api/admin_exam_intelligence.py
app/backend/app/api/admin_exam_intel_cms.py
app/backend/app/study_os/update_context.py
app/backend/app/study_os/planner.py
app/backend/app/study_os/mission_control.py
app/frontend/src/pages/admin/exam-workspace/panels/UpdatesPanel.jsx
app/backend/tests/exam_intelligence/test_readiness.py
app/backend/tests/exam_intelligence/test_admin_api.py
app/backend/tests/study_os/test_competition_update_context.py
app/backend/tests/study_os/test_mission_control.py
app/backend/tests/study_os/test_planner.py
app/frontend/src/pages/admin/exam-workspace/panels/__tests__/PanelWritePayloads.test.jsx
app/frontend/src/pages/admin/exam-workspace/panels/__tests__/UpdatesPanel.test.jsx
docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md
docs/status/career-copilot-checklist.md
```

## D09 decision boundary

D09 settles which policy-update rows are applicable to a selected exam/cycle context. It does not authorize runtime implementation and does not settle:

- policy-review state aggregation for the nine-step checklist;
- superseded-row lifecycle behavior beyond preserving it as an independent trust axis;
- D12 selected-cycle activation authority;
- D14 management-mode or cadence applicability.
