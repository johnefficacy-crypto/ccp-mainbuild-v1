# Exam Cycle Setup Gate — D06–D08 Decision Record

- Decision IDs: D06, D07, D08
- Operator: johnefficacy-crypto
- Approval date: 2026-06-23
- Parent gate: `docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md`
- Runtime effect: None. This record is documentation-only and does not authorize backend, frontend, API, migration, or test implementation.

## Status summary

| Decision | Status | Final resolution |
|---|---|---|
| D06 | APPROVED — V1 ONE-SUCCESS EXTRACTION THRESHOLD LOCKED | One latest successful `text_extract` job among documents applicable to the selected cycle makes the extraction step `ready`; remaining unresolved documents are advisory. |
| D07 | APPROVED — HARD/ADVISORY SPLIT LOCKED | Locked topic coverage is the activation hard gate; pending syllabus-mention review is advisory work and does not independently block activation. |
| D08 | APPROVED — ORIGINAL PROPOSAL REJECTED AND AMENDED | Topic coverage is selected-cycle-aware: selected-cycle rows plus exam-wide rows where `exam_cycle_id IS NULL`, with selected-cycle precedence per topic/phase. |

This record supersedes only D06–D08 and the conflicting D08 claim that `exam_topic_coverage` lacks `exam_cycle_id`. The parent I6 gate remains DRAFT because D13 and exit criteria E1/E5/E6 remain open.

---

## D06 — V1 extraction completion threshold

### Final completion rule

For contract version 1:

```text
extraction.status = ready
when successful_extraction_count >= 1
```

A successful extraction counts only when all of the following are true:

1. the document is applicable to the selected exam/cycle/phase under the approved D05 evidence policy;
2. the job has `job_type = "text_extract"`;
3. the job is the deterministic latest job for that document, ordered by `(created_at, id)`;
4. the latest job has `status = "succeeded"`.

The stricter rule—every required document must extract successfully—is explicitly deferred beyond contract version 1.

### D03 status mapping

When no latest successful job exists, derive the extraction step from applicable-document evidence using the locked D03 vocabulary:

| Applicable evidence | `extraction.status` |
|---|---|
| No applicable documents | `missing` |
| Documents exist and no extraction has started | `uploaded` |
| No success and at least one latest job is `queued` or `running` | `extracting` |
| No success and at least one latest job is `needs_review` | `review_pending` |
| No success and every applicable document has a terminal latest job of `failed` | `failed` |
| At least one latest job is `succeeded` | `ready` |

For mixed no-success states, apply the locked state-severity ordering without inventing `needs_action` as a status:

```text
failed only when all applicable latest attempts are terminal failures
otherwise review_pending > extracting > uploaded > missing
```

A failed document alongside an unstarted document does not prove the whole step is terminally failed; it remains non-ready with exact metrics and corrective actions.

### Advisory unresolved documents after readiness

Once one applicable document succeeds:

- `status` remains `ready`;
- unresolved documents must not remain in `blockers`;
- failed, pending, review-required, and unstarted documents remain visible through metrics, advisories, and action-queue items;
- activation authority must not be contradicted by a blocker emitted from the same one-success rule.

Canonical shape:

```json
{
  "step_id": "extraction",
  "status": "ready",
  "metrics": {
    "total": 4,
    "succeeded": 1,
    "extracting": 1,
    "review_pending": 0,
    "failed": 2,
    "not_started": 0
  },
  "blockers": [],
  "advisories": [
    {
      "code": "other_documents_unresolved",
      "count": 3
    }
  ]
}
```

The machine advisory code is stable:

```text
other_documents_unresolved
```

Corrective actions may deep-link to each causal document without changing the step back to non-ready.

### Selected-cycle scope

Canonical `cycle_readiness` must call extraction aggregation with the selected cycle and D05-applicable document set. A success belonging only to Cycle B must never complete Cycle A.

The existing helper accepts `cycle_id`, but `console_detail.build_console_detail()` currently calls `load_doc_extraction_counts(sb, exam_id, strict=True)` without passing it. That current path can count another cycle’s successful document. I9 must pass the resolved selected cycle consistently.

D06 does not redefine document inheritance or applicability. D05 remains authoritative for which exam-wide/cycle/phase evidence is applicable.

### Current implementation gaps

Current `readiness.py` already:

- selects the latest `text_extract` job per document deterministically;
- marks Documents `ready` when `extracted >= 1`;
- supports exact cycle filtering when `cycle_id` is supplied.

However it still adds pending documents to `blockers` even after setting the section to `ready`, and it does not expose the full D03 state vocabulary. Those behaviors conflict with D06.

Current `console_detail.py` already marks Documents `done` when one extraction succeeds, but its count load is exam-wide because it omits `cycle_id`.

### D06 acceptance cases

- no applicable documents → `missing`;
- applicable document with no job → `uploaded`;
- queued/running only → `extracting`;
- needs-review only → `review_pending`;
- all applicable latest jobs failed → `failed`;
- one selected-cycle success plus two selected-cycle failures → `ready`, zero blockers, unresolved advisory count two;
- Cycle B success with Cycle A selected and no Cycle A success → Cycle A is not `ready`;
- older success followed by latest failed job for the same document → that document does not count as succeeded;
- equal timestamps resolve by job ID deterministically.

---

## D07 — Syllabus readiness hard/advisory split

### Hard activation check

Planner-consumable topic coverage requires:

```text
locked_topic_coverage_count >= 1
```

Only this lifecycle satisfies the hard check:

```text
exam_topic_coverage.reviewer_status = "locked"
```

`reviewed`, `pending_review`, `draft`, or other rows do not satisfy planner coverage.

The hard check belongs to topic coverage, not to syllabus-document trust or syllabus-mention review.

### Advisory syllabus-mention check

Pending syllabus mentions are operational review work:

```text
syllabus_topic_mentions.reviewer_status in {
    "pending",
    "needs_correction"
}
```

When pending mentions exist:

- the mention-review check reports `review_pending`;
- an action-queue item is emitted;
- the top-level operational verdict may be `needs_action`;
- activation eligibility is not `blocked` when applicable locked topic coverage exists.

### Canonical representation

Within the I9 `syllabus_mapping` step, keep two independently visible checks:

```json
{
  "step_id": "syllabus_mapping",
  "status": "review_pending",
  "checks": [
    {
      "check_id": "locked_coverage",
      "status": "ready",
      "gate_class": "hard",
      "metrics": {
        "locked_rows": 12,
        "total_rows": 15
      }
    },
    {
      "check_id": "mention_review",
      "status": "review_pending",
      "gate_class": "advisory",
      "metrics": {
        "pending_mentions": 8,
        "verified_mentions": 24
      }
    }
  ]
}
```

The aggregate step may be `review_pending` because advisory work remains, but the hard activation check is passed. The backend top-level classifier remains the authority for `blocked | needs_action | ready`.

### Aggregation rule

```text
if locked_coverage.status != ready:
    syllabus_mapping.status = locked_coverage.status
    activation hard gate fails
elif mention_review.status not in {ready, not_applicable}:
    syllabus_mapping.status = mention_review.status
    activation hard gate passes; advisory work remains
else:
    syllabus_mapping.status = ready
```

Do not transform `review_pending` into `needs_action` at step/check level. Urgency and CTA live in blocker/action metadata.

### Current source alignment

`work_queue.classify_exam()` already:

- adds a hard blocker when `locked_coverage_count == 0`;
- treats pending review as a flag that can produce `needs_action` rather than `blocked`.

`console_detail.py` already separates `syllabus` as advisory and `topic_coverage` as hard.

The legacy `readiness.py::_syllabus_mapper()` does not implement this contract correctly: it counts lock states on `syllabus_topic_mentions` itself and places pending mentions in `blockers`. I9 must use `exam_topic_coverage` for the hard check and mention rows only for advisory review state.

### D07 acceptance cases

- locked coverage present, no pending mentions → step `ready`, hard gate passes;
- locked coverage present, pending mentions → step `review_pending`, hard gate passes, action emitted, top-level may be `needs_action` but not `blocked` from mentions;
- reviewed coverage only → hard coverage check not ready;
- pending coverage plus verified mentions → hard gate fails because coverage is not locked;
- locked syllabus document or mention without locked `exam_topic_coverage` → hard gate fails;
- no locked coverage → classifier/top-level activation remains `blocked`.

---

## D08 — Selected-cycle plus exam-wide topic-coverage scope

### Original proposal rejected

The parent gate incorrectly states that `exam_topic_coverage` lacks `exam_cycle_id` and proposes exam-wide-only scope. The schema already contains:

```sql
exam_cycle_id uuid references public.exam_cycles(id)
```

It also has separate uniqueness rules for cycle-specific and exam-wide coverage rows.

### Canonical selected-cycle predicate

For selected Cycle A:

```sql
exam_id = :exam_id
AND (
    exam_cycle_id = :cycle_a
    OR exam_cycle_id IS NULL
)
```

Rows belonging exclusively to Cycle B are excluded.

Canonical evidence scope:

```text
selected_cycle_plus_exam_wide
```

Do not label this simply `exam_wide` or `selected_cycle`; both would hide part of the effective evidence set.

### Override precedence

For the same canonical topic/phase key:

```text
1. selected-cycle row
2. otherwise exam-wide row where exam_cycle_id IS NULL
3. never another cycle’s row
```

The v1 precedence key is:

```text
(exam_phase_id, topic_id)
```

`exam_id` is fixed by the query. Existing uniqueness indexes are defined on this key with cycle scope. If future phase-template equivalence is introduced, mapping different phase IDs requires a separate explicit contract; do not infer it from names or slugs.

Selected-cycle rows override exam-wide rows regardless of reviewer lifecycle. A selected-cycle draft/pending/rejected row must not silently fall back to an older exam-wide locked row for the same key, because that would conceal an explicit cycle-specific override. Its actual lifecycle remains visible and governs that key.

### Metrics contract

Expose raw-source counts and effective post-precedence counts separately:

```json
{
  "scope": "selected_cycle_plus_exam_wide",
  "selected_cycle_id": "cycle-uuid",
  "metrics": {
    "cycle_specific_rows": 7,
    "exam_wide_rows": 5,
    "effective_rows": 10,
    "locked_rows": 8
  }
}
```

- `cycle_specific_rows`: raw rows where `exam_cycle_id = selected_cycle_id`;
- `exam_wide_rows`: raw rows where `exam_cycle_id IS NULL`;
- `effective_rows`: rows remaining after selected-cycle precedence;
- `locked_rows`: effective rows whose reviewer status is `locked`.

Hard-gate evaluation uses effective `locked_rows`, not the raw union count.

### No selected cycle

A selected-cycle readiness request without a resolved cycle must not aggregate rows from every historical/future cycle.

- canonical cycle readiness uses D15 `not_applicable_reason = "no_selected_cycle"` where the step cannot be evaluated;
- an explicitly exam-wide administrative view may query only `exam_cycle_id IS NULL` rows;
- no consumer may interpret “no cycle filter” as “all cycles are applicable.”

### Current implementation gap

`readiness.py::_topic_coverage_snapshot()` already applies the combined selected-cycle/null predicate when `cycle_id` is supplied. This supports the D08 amendment.

It does not yet:

- select `exam_cycle_id`, `exam_phase_id`, or `topic_id` in the snapshot query;
- distinguish cycle-specific versus exam-wide counts;
- apply per-topic/phase override precedence;
- expose `scope = "selected_cycle_plus_exam_wide"`;
- prevent all-cycle aggregation when no cycle is supplied.

These are required I9 implementation changes.

### D08 acceptance cases

- Cycle A row only → included;
- exam-wide row only → inherited into Cycle A;
- same topic/phase has Cycle A and exam-wide rows → Cycle A row wins once;
- same topic/phase has Cycle B and exam-wide rows while Cycle A selected → Cycle B excluded; exam-wide row inherited;
- same key has Cycle A draft and exam-wide locked → Cycle A draft wins; hard gate does not count the hidden exam-wide locked row;
- no selected cycle → no all-cycle union;
- metrics distinguish raw cycle-specific, raw exam-wide, effective, and effective locked rows.

---

## Expected implementation files

```text
app/backend/app/exam_intelligence/readiness.py
app/backend/app/exam_intelligence/console_detail.py
app/backend/app/exam_intelligence/work_queue.py
app/backend/app/exam_intelligence/management_read_model.py
app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx
app/backend/tests/exam_intelligence/test_readiness.py
app/backend/tests/exam_intelligence/test_console_detail.py
app/backend/tests/exam_intelligence/test_work_queue.py
app/backend/tests/exam_intelligence/test_management_read_model.py
app/frontend/src/pages/admin/exam-workspace/panels/__tests__/ReviewActivatePanel.test.jsx
docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md
docs/status/career-copilot-checklist.md
```

No migration is required for D08 because `exam_topic_coverage.exam_cycle_id` and the relevant uniqueness indexes already exist. D06–D08 authorize no runtime work within PR #761.

## Decision boundary

D06–D08 settle:

- v1 one-success extraction completion;
- unresolved-document advisories after extraction readiness;
- selected-cycle document-count discipline;
- locked topic coverage as hard activation evidence;
- syllabus mention review as advisory work;
- selected-cycle plus exam-wide topic-coverage inheritance;
- selected-cycle precedence per topic/phase.

They do not settle:

- D13 manual completion overrides;
- a future all-required-documents extraction threshold;
- cadence-specific modifiers;
- cross-phase equivalence between different `exam_phase_id` values;
- runtime implementation or PR readiness.
