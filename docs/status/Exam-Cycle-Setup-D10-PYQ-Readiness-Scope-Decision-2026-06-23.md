# Exam Cycle Setup Gate — D10 PYQ Readiness Scope Decision

- Decision ID: D10
- Status: APPROVED — PRODUCT POLICY LOCKED
- Approver: johnefficacy-crypto (operator)
- Approval date: 2026-06-23
- Parent gate: `docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md`
- Effect: This addendum supersedes only the D10 row in the parent gate. The parent I6 gate remains DRAFT and PR #761 must remain draft until the remaining decisions and exit criteria are closed.
- Runtime effect: None. This is a documentation-only decision record; no API, backend, frontend, migration, or test behavior is changed by this file.

## Final D10 resolution

PYQ readiness is exam-wide historical evidence readiness, not selected-cycle equality.

Canonical corpus predicate:

```python
pyq_papers.exam_id == selected_exam_id
```

The following predicate is prohibited as the default readiness scope:

```python
pyq_papers.exam_id == selected_exam_id
and pyq_papers.exam_cycle_id == selected_cycle_id
```

`pyq_papers.exam_cycle_id` records the paper's origin/provenance. It does not determine whether that historical paper may contribute to the currently selected cycle's general PYQ corpus.

The behavior is exam-wide both when a cycle is selected and when no cycle is selected.

## Verified schema facts

The existing schema already supports provenance without a new migration:

- `pyq_papers.exam_id` is required;
- `pyq_papers.exam_cycle_id` is nullable;
- `pyq_papers.exam_phase_id` is nullable;
- admin PYQ CRUD accepts `exam_cycle_id` and `exam_phase_id`;
- the admin paper list can optionally filter by `exam_cycle_id`.

No D10 migration is required. The defect is in default filtering and trust/readiness aggregation.

## Separation of concepts

| Concept | Meaning |
|---|---|
| Paper provenance | `pyq_papers.exam_cycle_id`, `exam_phase_id`, `year`, and paper metadata describe where the paper came from. |
| Evidence applicability | The default historical corpus is all papers belonging to the selected exam. |
| Selected cycle | Provides management context for dates, syllabus, competition, policy updates, and future compatibility evaluation. |
| PYQ readiness | Verified historical question evidence is available for the exam. |

Simple cycle equality must not be used as a compatibility rule.

Future narrowing may use an explicit, approved compatibility model based on one or more of:

- phase equivalence;
- pattern or scheme version;
- syllabus regime;
- recency window;
- manually reviewed supersession or incompatibility;
- question type or scoring compatibility.

Until such a model exists, cycle provenance remains descriptive and filterable but does not remove papers from the default readiness corpus.

## Trust rule

Exam-wide scope does not mean every paper or question counts.

The canonical verified PYQ evidence count remains the work-queue three-gate definition. Count a distinct question only when:

1. its parent `pyq_papers.trust_status = 'verified'`;
2. `pyq_questions.reviewer_status = 'verified'`;
3. at least one linked `pyq_question_topic_tags` row has `reviewer_status = 'verified'`.

A verified paper with no verified questions does not satisfy readiness. A verified question without a verified topic tag does not satisfy readiness. A question under an unverified paper does not satisfy readiness.

`pyq_questions.reviewer_status` does not currently include `locked`; readiness code must not treat a non-schema `locked` question state as valid evidence.

## Current implementation gaps

### 1. Workspace readiness incorrectly filters by selected cycle

`readiness.py::_pyq_workbench()` currently applies:

```python
if cycle_id:
    papers_q = papers_q.eq("exam_cycle_id", cycle_id)
```

This hides historical and unscoped papers whenever a cycle is selected.

Required change:

- query papers by `exam_id` only;
- retain `cycle_id` only as response context;
- calculate provenance breakdown independently from readiness scope.

### 2. Workspace readiness does not implement the canonical trust gates

The current readiness implementation:

- counts questions with reviewer status `verified` or the non-schema value `locked`;
- does not require parent-paper `trust_status='verified'`;
- counts all topic tags rather than requiring at least one verified topic tag per question;
- can mark a section ready from a percentage of question statuses rather than the canonical distinct verified-question count.

D10 implementation must reuse or extract the same three-gate aggregation logic as `work_queue.aggregate`. Do not maintain two independently drifting definitions.

Recommended shared module:

```text
app/backend/app/exam_intelligence/pyq_readiness.py
```

It should support both:

- set-based catalogue aggregation for many exams;
- detailed single-exam evidence and provenance metrics for Manage Exam.

### 3. Frontend workbench repeats selected-cycle filtering

`usePyqWorkbench(examId, cycleId)` currently sends `exam_cycle_id` whenever a workspace cycle is selected.

Required default behavior:

- request by `exam_id` only;
- optionally expose cycle as an explicit provenance filter controlled by the operator;
- provenance filters must not redefine readiness scope.

### 4. Empty and not-found copy is incorrect

Replace:

```text
No PYQ papers for this exam/cycle.
```

with:

```text
No PYQ papers for this exam.
```

A deep-linked paper belonging to the same exam but another cycle must remain discoverable. A paper belonging to another exam is not found in this workspace.

### 5. Provenance must be visible

The paper table should expose at least:

- paper year;
- source cycle name/year when available;
- phase provenance when available;
- unscoped provenance when `exam_cycle_id IS NULL`;
- paper trust status.

The frontend may map cycle IDs from workspace/management data, or the backend may return resolved cycle and phase labels. Raw UUIDs must not be displayed.

### 6. Admin write integrity remains required

Although admin CRUD accepts provenance IDs, create and update paths must validate:

- `exam_cycle_id` belongs to `exam_id`;
- `exam_phase_id` belongs to `exam_id`;
- when both are supplied, the phase belongs to the supplied cycle or is an explicitly permitted exam-level template.

This is a write-integrity requirement and does not change the exam-wide readiness scope.

## Read-model shape

The detailed PYQ section may expose selected-cycle context and provenance breakdown without using it as a filter:

```json
{
  "pyq_readiness": {
    "state": "ready",
    "scope": "exam_wide",
    "selected_cycle_id": "<cycle-2026-id>",
    "papers_total": 4,
    "selected_cycle_papers": 0,
    "other_cycle_papers": 3,
    "unscoped_papers": 1,
    "verified_question_count": 142
  }
}
```

Use `other_cycle_papers` unless chronology is actually established. A paper attached to a different cycle is not automatically historical; it could belong to a future or parallel cycle. `historical_cycle_papers` may be added only when comparison against validated cycle/year ordering proves that classification.

The section state must use the locked vocabulary. General exam-wide PYQ readiness is:

```text
ready          when verified_question_count >= 1
review_pending when papers/questions/tags exist but trusted review work remains
missing        when no usable corpus exists
failed         only for an actual required read/processing failure
```

Detailed precedence and failure behavior must remain backend-derived.

## D05 compatibility boundary

D10 settles the default corpus scope and canonical general PYQ evidence count.

It does not erase D05's stricter `core` policy requiring compatible PYQ evidence for each active written phase. Until phase-equivalence and compatibility rules are approved:

- the exam-wide verified count may satisfy general PYQ corpus readiness and the catalogue `missing_pyq` signal;
- it must not be treated as proof that every active written phase has a compatible paper;
- D05 per-phase activation evaluation remains blocked on the future compatibility contract.

This distinction prevents a verified paper from an unrelated phase or obsolete pattern from silently satisfying a phase-specific hard requirement.

## Acceptance tests

Required scope cases:

- selected 2026 cycle plus verified 2025 paper for the same exam → included;
- selected 2026 cycle plus unscoped paper for the same exam → included;
- selected 2026 cycle plus paper attached to another cycle of the same exam → included in the exam-wide corpus and labelled by provenance;
- paper belonging to another exam → excluded;
- selecting or clearing a workspace cycle does not change the exam-wide corpus total;
- an explicit provenance filter may change the visible table but not the backend readiness count.

Required trust cases:

- verified paper + verified question + verified topic tag → counts once;
- unverified paper + verified question + verified tag → does not count;
- verified paper + pending/rejected question + verified tag → does not count;
- verified paper + verified question + no verified tag → does not count;
- multiple verified tags on one question → question counts once;
- verified empty paper → does not satisfy readiness.

Required parity cases:

- `work_queue.verified_pyq_count` and detailed readiness use the same canonical distinct-question definition;
- management list cannot report verified PYQ evidence while detailed readiness reports no corpus because of selected-cycle filtering;
- provenance metrics do not affect the canonical verified count;
- frontend empty state says `No PYQ papers for this exam.`;
- paper rows show human-readable cycle/phase provenance without raw UUIDs.

## Expected implementation files

```text
app/backend/app/exam_intelligence/pyq_readiness.py
app/backend/app/exam_intelligence/readiness.py
app/backend/app/exam_intelligence/work_queue.py
app/backend/app/api/admin_exam_intel_cms.py
app/frontend/src/pages/admin/exam-workspace/pyq-workbench/usePyqWorkbench.js
app/frontend/src/pages/admin/exam-workspace/pyq-workbench/PyqWorkbenchPanel.jsx
app/backend/tests/exam_intelligence/test_readiness.py
app/backend/tests/exam_intelligence/test_work_queue.py
app/backend/tests/admin/test_admin_study_os.py
app/frontend/src/pages/admin/exam-workspace/pyq-workbench/__tests__/PyqWorkbench.test.jsx
docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md
docs/status/career-copilot-checklist.md
```

## D10 decision boundary

D10 settles:

- exam-wide PYQ corpus scope;
- cycle ID as provenance rather than default applicability;
- canonical three-gate verified-question counting;
- selected-cycle-independent general PYQ readiness.

D10 does not settle:

- phase-equivalence or pattern-compatibility rules;
- recency windows;
- D05 per-phase hard-gate completion;
- management-mode applicability under D14;
- manual supersession workflows.
