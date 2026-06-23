# Exam Cycle Setup Gate — D11 Competition Applicability Decision

- Decision ID: D11
- Status: APPROVED — PRODUCT POLICY LOCKED
- Approver: johnefficacy-crypto (operator)
- Approval date: 2026-06-23
- Parent gate: `docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md`
- Effect: This addendum supersedes only the D11 row in the parent gate. The parent I6 gate remains DRAFT and PR #761 must remain draft until the remaining decisions and exit criteria are closed.
- Runtime effect: None. This is a documentation-only decision record; no API, backend, frontend, migration, or test behavior is changed by this file.

## Final D11 resolution

Competition readiness is evaluated for the selected exam cycle and is applicable by management mode.

| Management mode | No reviewed/locked row for selected cycle | Reviewed row | Locked row |
|---|---|---|---|
| `core` | `empty` or `partial`; prevents full selected-cycle readiness | `ready` | `locked` |
| `light` | `not_applicable` | `ready` | `locked` |
| `index_only` | `not_applicable` | `ready` | `locked` |
| `archive` | `not_applicable` | `ready` | `locked` |
| `NULL` / unclassified | Do not infer applicability; require management-mode classification | — | — |

This matches the locked lane meanings:

- `core`: full readiness expected;
- `light`: essential facts and major updates;
- `index_only`: searchable reference without deep Study OS readiness;
- `archive`: retained with minimal active operations.

## Selected-cycle scope

Competition intelligence is cycle-specific.

For selected Cycle A, usable rows are:

```sql
exam_id = :exam_id
AND exam_cycle_id = :cycle_a
AND reviewer_status IN ('reviewed', 'locked')
```

Rows belonging to Cycle B must not contribute to Cycle A readiness or Study OS context.

Do not fall back to another cycle merely because it has a reviewed or locked row.

When no cycle is selected, D11 does not authorize choosing an arbitrary historical, future, or unscoped row. The no-cycle state remains governed by the upstream selected-cycle contract and D12/D16. A consumer called without a canonical cycle must return unavailable/unevaluated competition context rather than mixing all cycles.

## Usable-row and precedence rule

Only these lifecycle states are usable evidence:

```python
reviewer_status in {"reviewed", "locked"}
```

Selection precedence within the selected cycle:

1. `locked` rows before `reviewed` rows;
2. newest `created_at` within the same trust state;
3. stable `id` tie-breaker.

Draft, pending-review, and rejected rows behave as follows:

```text
draft / pending_review
    → visible to operators
    → retained in pending counts
    → do not reach Study OS
    → do not make competition evidence applicable
    → do not block light/index_only/archive activation

rejected
    → ignored for readiness and Study OS
    → may remain visible in audit/review surfaces
```

## Core-mode behavior

For `management_mode = 'core'`:

- at least one selected-cycle `locked` row → `locked`;
- otherwise at least one selected-cycle `reviewed` row → `ready`;
- no usable row but one or more draft/pending-review rows → `partial`;
- no usable row and no actionable draft/pending-review row → `empty`.

The blocker text must be precise:

```text
No reviewed or locked competition intelligence for the selected cycle
```

Do not use only `no metric`, because rows may exist but remain unreviewed.

D11 makes missing usable competition evidence prevent full selected-cycle readiness for `core`. It does not independently replace the current exam-scoped `classify_exam` activation authority; final activation composition remains linked to D12 and D14.

## Optional-mode `not_applicable` contract

For `light`, `index_only`, and `archive`, when the selected cycle has no reviewed or locked row, return a truthful non-applicable section rather than `ready`:

```json
{
  "section": "competition",
  "status": "not_applicable",
  "applicable": false,
  "score_percent": null,
  "weight": 0,
  "blockers": [],
  "counts": {
    "present": 0,
    "required": 0
  },
  "metrics": {
    "reviewed": 0,
    "locked": 0,
    "pending": 2,
    "reason": "optional_for_management_mode"
  }
}
```

`not_applicable` must:

- contribute neither points nor weight;
- add no blocker;
- not count as a completed section;
- be excluded from the activation requirement denominator;
- preserve draft and pending-review counts for operator visibility.

If a reviewed or locked row later exists for an optional mode, the section becomes `ready` or `locked`; optionality does not hide valid evidence.

The competition-specific reason code is locked as:

```text
optional_for_management_mode
```

Legacy readiness may expose this as `metrics.reason`. D15 still owns the canonical machine-readable reason field for the future I9 step object; D11 does not approve D15's global field placement.

## Unclassified management mode

`management_mode IS NULL` must not silently inherit `core`, `light`, or `not_applicable` behavior.

The response must surface a blocking classification-required condition, with operator-facing text equivalent to:

```text
Classify the exam management mode before evaluating competition applicability
```

The exact generic status-token and weighting contract for unclassified exams remains part of D14. D11 only locks that no default mode may be inferred.

## Current implementation gaps

### 1. Readiness has no management-mode input

`compute_exam_workspace_readiness(sb, exam_id, cycle_id=None)` and `_competition()` do not receive `management_mode`.

Required contract:

```python
compute_exam_workspace_readiness(
    sb,
    exam_id,
    cycle_id=None,
    management_mode=None,
)
```

The caller must supply the canonical value from the selected exam row. Do not accept a client-provided management mode as authority.

### 2. Both readiness call paths must pass the mode

`management_read_model.get_management_exam_detail()` already loads the exam row and returns `management_mode`, but currently calls readiness without passing it.

The direct workspace readiness endpoint validates the exam but discards the loaded row and also calls readiness without the mode.

Both paths must pass the same canonical database value so their results cannot diverge.

### 3. Current competition readiness treats any row as presence

`readiness.py::_competition()` currently:

- filters selected cycle when supplied;
- marks any non-rejected active row as `partial`;
- returns `empty` only when no row exists;
- adds `no competition metric for this cycle` only when the table is empty;
- assigns weight `1` for every management mode;
- lacks `applicable` and `not_applicable` support;
- omits `pending_review` and `rejected` from its breakdown.

It must count all lifecycle states for operator visibility while deriving readiness only from selected-cycle reviewed/locked rows.

### 4. Readiness score vocabulary lacks `not_applicable`

The current score map contains only:

```python
empty, partial, ready, locked
```

A non-applicable section must bypass score lookup by returning `score_percent=None` and `weight=0`. Do not map `not_applicable` to a synthetic percentage.

### 5. Backend activation denominator counts all sections

`_review_activate()` currently requires every upstream section to be `ready` or `locked` and sets `required = len(upstream)`.

Required behavior:

```python
applicable_sections = [
    section for section in upstream
    if section["status"] != "not_applicable"
]
```

Then:

- numerator counts only applicable `ready`/`locked` sections;
- denominator is `len(applicable_sections)`;
- non-applicable sections are neither complete nor blocked;
- pending optional competition rows remain visible but do not enter the denominator.

### 6. Frontend activation denominator has the same defect

`ReviewActivatePanel.jsx` currently compares the ready/locked count against all sections.

It must:

- exclude `not_applicable` sections from the denominator;
- display an explicit `Not applicable` status badge;
- avoid treating N/A as either clear or blocked;
- display applicable-clear count separately from optional/N-A count;
- preserve operator pending-row visibility.

### 7. Competition panel copy is mode-blind

`CompetitionPanel.jsx` currently always displays `No competition metric for this cycle` and encourages metric creation as if missing competition evidence blocks every exam.

For optional management modes, show truthful copy such as:

```text
Competition intelligence is optional for this management mode.
Draft and reviewed metrics may still be maintained for operator use.
```

The create/review workflow may remain available. Optional does not mean forbidden.

The trust badge mapping must use the actual competition lifecycle:

```text
draft, pending_review, reviewed, locked, rejected
```

It must not display competition `reviewed` rows through an unrelated `verified` label.

### 8. Study OS currently falls back across cycles

`competition_context()` queries all reviewed/locked rows for the exam. `_pick_best()` merely ranks a matching cycle first, then falls back to another cycle when no matching row exists.

Required behavior:

- require the canonical selected/active-plan cycle;
- apply exact `exam_cycle_id` filtering before selection;
- return `available=False` when that cycle has no reviewed/locked row;
- do not substitute another cycle;
- preserve locked-over-reviewed and deterministic newest-row precedence within the selected cycle.

A legacy plan without a canonical cycle must not consume an arbitrary competition row.

## Legacy readiness versus I9 boundaries

D11 authorizes `not_applicable` for the competition section in the existing readiness contract.

It does not approve:

- the full D03 global status vocabulary;
- a section-level `blocked` state;
- D14's full management-mode/cadence applicability matrix;
- D15's final field location for machine-readable N/A reasons;
- D12's final activation-composition predicate.

Those decisions must remain independently auditable.

## Acceptance tests

### Selected-cycle trust

- Cycle A reviewed row → Cycle A `ready` and Study OS available.
- Cycle A locked row → Cycle A `locked`; locked wins over reviewed.
- Cycle A has no usable row; Cycle B has locked row → Cycle A does not use Cycle B.
- Cycle A draft/pending-review rows only → Study OS unavailable.
- Rejected row only → ignored.
- Multiple selected-cycle rows → deterministic locked/reviewed/newest/id precedence.
- No selected cycle → no cross-cycle fallback.

### Management mode

- `core` + no rows → `empty`, applicable, precise blocker.
- `core` + pending rows only → `partial`, applicable, precise blocker.
- `light` + no usable rows → `not_applicable`, weight `0`, no blocker.
- `index_only` + pending rows only → `not_applicable`, pending count retained.
- `archive` + rejected row only → `not_applicable`.
- optional mode + reviewed row → `ready`.
- optional mode + locked row → `locked`.
- null mode → no inferred default; classification-required condition.

### Denominator and score

- N/A competition adds no score or weight.
- N/A competition is absent from backend activation denominator.
- N/A competition is absent from frontend applicable-section denominator.
- N/A competition is not counted as complete.
- All other applicable sections ready plus competition N/A → review/activation rollup may be ready, subject to D12/D14 authority.
- Pending optional competition rows remain visible in metrics and operator panel.

### Caller parity

- Management detail and direct workspace readiness return identical competition status for the same exam/cycle.
- Neither caller trusts a client-supplied mode.
- Changing the persisted exam management mode changes the recomputed section deterministically.

## Expected implementation files

```text
app/backend/app/exam_intelligence/readiness.py
app/backend/app/exam_intelligence/management_read_model.py
app/backend/app/api/admin_exam_intelligence.py
app/backend/app/study_os/competition_context.py
app/backend/app/study_os/mission_control.py
app/backend/app/study_os/planner.py
app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx
app/frontend/src/pages/admin/exam-workspace/panels/CompetitionPanel.jsx
app/backend/tests/exam_intelligence/test_readiness.py
app/backend/tests/exam_intelligence/test_management_read_model.py
app/backend/tests/study_os/test_competition_update_context.py
app/frontend/src/pages/admin/exam-workspace/panels/__tests__/ReviewActivatePanel.test.jsx
app/frontend/src/pages/admin/exam-workspace/panels/__tests__/CompetitionPanel.test.jsx
docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md
docs/status/career-copilot-checklist.md
```

## D11 decision boundary

D11 settles:

- competition applicability by management mode;
- exact selected-cycle scope;
- reviewed/locked trust boundary;
- locked-over-reviewed precedence;
- truthful `not_applicable` behavior for optional modes;
- exclusion from score, blocker list, completion numerator, and requirement denominator;
- prohibition on cross-cycle Study OS fallback.

D11 does not settle D03, D12, D14, or D15 beyond the explicit competition-specific rules above.
