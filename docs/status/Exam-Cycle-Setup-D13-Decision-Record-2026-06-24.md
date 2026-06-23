# Exam Cycle Setup Gate — D13 Final Decision Record

- Decision ID: D13
- Status: APPROVED — CONTROLLED TEMPORARY ADMIN-READINESS WAIVER
- Operator: johnefficacy-crypto
- Approval date: 2026-06-24
- Parent gate: `docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md`
- Supersedes: `Exam-Cycle-Setup-D13-Manual-Override-Scope-Clarification-2026-06-23.md` only where that document says D13 is unresolved
- Runtime effect: None. This is a contract decision only. PR #761 remains documentation-only and does not implement waiver storage, endpoints, auth, classifier changes, UI, or planner behavior.

## Final resolution

D13 does not permit manual completion and does not permit mutation of canonical evidence-derived status.

It permits a narrowly scoped, temporary, two-person-approved **admin-readiness waiver** for explicitly allowlisted non-planner or degradable checks.

```text
D13 — Controlled temporary admin-readiness waiver

canonical evidence status remains unchanged
manual completion remains prohibited
planner evidence remains unchanged
aspirant-facing evidence remains unchanged
backend may apply an approved waiver only to an explicitly allowlisted
admin readiness check for the selected exam cycle
```

A waiver is an administrative exception, not evidence, review, verification, locking, readiness completion, or planner truth.

## Canonical response semantics

The D03 `status` field always remains evidence-derived:

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

A waiver must never rewrite one of those values to `ready`.

Approved step/check representation:

```json
{
  "step_id": "extraction",
  "status": "failed",
  "resolution": "waiver",
  "admin_gate_effect": "satisfied_by_waiver",
  "waiver": {
    "id": "waiver-uuid",
    "reason_code": "source_format_unprocessable",
    "evidence_refs": [
      {"kind": "document_asset", "row_id": "document-uuid"},
      {"kind": "document_processing_job", "row_id": "job-uuid"}
    ],
    "approved_at": "2026-06-24T00:00:00Z",
    "expires_at": "2026-07-01T00:00:00Z"
  }
}
```

Allowed `resolution` values for v1:

```text
evidence
waiver
not_applicable
```

Allowed `admin_gate_effect` values for v1:

```text
satisfied_by_evidence
satisfied_by_waiver
unsatisfied
not_applicable
```

The field is intentionally named `admin_gate_effect`, not generic `gate_satisfied`, because it must not be interpreted as planner evidence or aspirant-facing truth.

The top-level authoritative status vocabulary remains:

```text
blocked | needs_action | ready
```

When the backend classifier returns `ready` using one or more approved active waivers, it must also return:

```json
{
  "status": "ready",
  "resolution": "waiver",
  "active_waiver_count": 1
}
```

The UI renders this as:

```text
Ready with 1 active waiver
```

It must not render the exam as unconditionally evidence-ready.

## Scope and identity

Every waiver is scoped to exactly:

```text
exam_id
exam_cycle_id
step_id
optional check_id
```

Rules:

- no exam-wide waiver when a selected cycle exists;
- no cross-cycle inheritance;
- no cross-step inheritance;
- a check-level waiver does not waive sibling checks or the parent step unless the backend aggregation contract explicitly says that exact check is sufficient;
- no wildcard or global waiver;
- one active waiver maximum per exact scope.

## Waivable checks in v1

Only the following exact checks may be waived.

### 1. Extraction completion

```text
step_id = extraction
check_id = successful_extraction
```

Allowed only when:

- at least one D05-applicable official/source document exists;
- zero applicable latest `text_extract` jobs succeeded;
- no applicable extraction job is currently queued or running;
- required evidence references include the document and terminal processing job(s);
- locked topic coverage already exists independently when planner activation applies.

Allowed evidence states:

```text
failed
review_pending
stale
```

Not allowed while status is:

```text
missing
uploaded
extracting
ready
not_applicable
```

A waiver never makes extracted text available and never substitutes content for syllabus/PYQ/planner consumers.

### 2. Advisory syllabus-mention review

```text
step_id = syllabus_mapping
check_id = mention_review
```

Allowed evidence states:

```text
missing
review_pending
stale
failed
```

The hard `locked_coverage` check remains non-waivable.

### 3. Advisory PYQ readiness

```text
step_id = pyq_readiness
```

Allowed evidence states:

```text
missing
review_pending
stale
failed
```

A waiver does not create verified PYQ counts and the planner continues to receive the actual verified count, including zero.

### 4. Advisory policy-update review

```text
step_id = policy_updates
check_id = informational_review
```

Allowed only when every unresolved row is informational and all of these are false:

```text
affects_syllabus
affects_eligibility
affects_pattern
affects_deadline
affects_planner
```

Any unresolved update that affects one of those domains is non-waivable.

### 5. Advisory competition context

```text
step_id = competition_context
```

Allowed evidence states:

```text
missing
review_pending
stale
failed
```

A waiver does not fabricate competition metrics and cannot change planner intensity or aspirant claims.

## Non-waivable conditions

The following are always non-waivable in v1:

```text
cycle_details
phases_schedule
source_documents absence when D05 marks the evidence required
syllabus_mapping.locked_coverage
review_activate
management_mode IS NULL
invalid or foreign selected cycle
cycle_not_found
unsupported, absent, or malformed contract_version
backend, database, network, or critical-read failure
not_applicable classification
actively queued/running extraction
any evidence required directly by Study OS/planner
```

Specifically:

- no waiver may satisfy missing required phases;
- no waiver may satisfy zero applicable locked `exam_topic_coverage` rows;
- no waiver may make unreviewed/unlocked topic coverage planner-consumable;
- no waiver may convert a backend failure into a readiness state;
- no waiver may override D15 applicability or its reason code.

## Permission model

Dedicated permissions are required:

```text
exam_intelligence.readiness_waiver.request
exam_intelligence.readiness_waiver.approve
exam_intelligence.readiness_waiver.revoke
```

Rules:

- requester and approver must be different permanent users;
- requester cannot approve their own request;
- approval requires the explicit approval permission;
- revocation requires the explicit revoke permission;
- no role-only approval;
- no implicit `super_admin` bypass;
- anonymous users are prohibited;
- the existing `require_permission()` helper must not be reused unchanged because it bypasses checks for `super_admin`;
- implementation requires a new `require_explicit_permission()` dependency that checks the exact permission for every role, including `super_admin`.

If two distinct authorised actors are unavailable, the waiver remains pending and has no gate effect.

## Exception-code allowlist

Allowed reason codes:

```text
source_format_unprocessable
external_dependency_outage
historical_evidence_unavailable
processing_defect_with_verified_alternative
duplicate_or_superseded_artifact
official_source_temporarily_unavailable
```

No unrestricted `other` code.

Step restrictions:

| Reason code | Permitted scope |
|---|---|
| `source_format_unprocessable` | extraction only |
| `external_dependency_outage` | extraction or advisory review checks; expiry at most 7 days |
| `historical_evidence_unavailable` | syllabus mention review, PYQ, or competition; selected cycle must be closed/completed |
| `processing_defect_with_verified_alternative` | extraction only; alternative evidence reference required |
| `duplicate_or_superseded_artifact` | extraction or informational policy review; superseding row reference required |
| `official_source_temporarily_unavailable` | advisory review checks only; never source-document absence; expiry at most 7 days |

Operational inconvenience, staffing shortage, backlog size, target date pressure, or desire to improve readiness score are not valid exceptions.

## Mandatory request contract

Every request must include:

```json
{
  "exam_id": "exam-uuid",
  "exam_cycle_id": "cycle-uuid",
  "step_id": "extraction",
  "check_id": "successful_extraction",
  "reason_code": "source_format_unprocessable",
  "reason": "Official scanned notification remains unprocessable after terminal OCR retries.",
  "evidence_refs": [
    {"kind": "document_asset", "row_id": "document-uuid"},
    {"kind": "document_processing_job", "row_id": "job-uuid"}
  ],
  "requested_expires_at": "2026-07-01T00:00:00Z"
}
```

Requirements:

- reason length 20–1000 characters;
- at least one evidence reference, plus all step-specific references;
- every evidence row must belong to the same exam/cycle scope;
- the server records a deterministic evidence fingerprint at request time;
- requested expiry is mandatory;
- default expiry is 7 days;
- maximum expiry is 30 days;
- renewal requires a new request and a new approval; expired/revoked records cannot be reactivated.

## Lifecycle

Approved lifecycle:

```text
pending
approved
active
needs_revalidation
superseded_by_evidence
expired
revoked
rejected
```

Rules:

- creation produces `pending` and no gate effect;
- approval moves to `active` only after all server validations pass;
- evidence fingerprint change moves an active waiver to `needs_revalidation` immediately and removes its gate effect;
- canonical evidence becoming satisfied moves the waiver to `superseded_by_evidence` and removes it from active counts;
- expiry removes gate effect without a worker dependency: every read treats `expires_at <= now()` as expired;
- revocation removes gate effect immediately;
- rejected, revoked, expired, superseded, or revalidation-required waivers cannot be reactivated.

## Revocation and revalidation

Revocation requires:

```text
waiver_id
reason
actor with explicit revoke permission
```

The backend must recompute readiness and activation immediately after revocation.

Revalidation requires a new request referencing the prior waiver. It must not update the prior approval in place.

## Atomic audit requirement

Waiver mutation and audit recording must be atomic.

The existing best-effort CMS `_audit()` pattern is not sufficient because it catches audit failure and permits the main write to continue.

Implementation must use a database RPC/transaction that atomically writes:

```text
waiver row or lifecycle transition
immutable audit event
request/approval/revocation actor identity
previous and new lifecycle state
evidence fingerprint
reason and evidence refs
```

If the audit event cannot be written, the waiver mutation fails.

Audit events are append-only. No endpoint may delete or rewrite request, approval, rejection, expiry, supersession, revalidation, or revocation history.

## Backend authority and classifier integration

The frontend must never calculate waiver effect.

Future implementation must:

1. load active, unexpired, fingerprint-valid waivers for the selected exam/cycle;
2. validate each against the allowlist and current evidence state;
3. pass validated waiver context into the single backend readiness/classifier path;
4. preserve evidence-derived step/check `status`;
5. derive `resolution` and `admin_gate_effect` server-side;
6. derive the top-level `blocked | needs_action | ready` verdict from the same backend classifier used by list/detail surfaces;
7. expose active waiver count and typed waiver evidence;
8. fail closed if a non-ready or waiver-derived verdict cannot be explained.

No separate frontend classifier and no parallel console-only activation rule are permitted.

Catalogue/list and management-detail views must remain consistent with the selected-cycle waiver effect. A waiver cannot make one endpoint report `ready` while another reports `blocked` for the same selected cycle and contract version.

## Planner and aspirant effect

Locked final effect:

```text
planner_effect = none
aspirant_effect = none
```

Specifically:

- Study OS continues reading only canonical locked topic coverage and verified evidence;
- no waiver table or field may be joined into planner coverage, verified PYQ counts, task priority, `why_this_task`, competition intensity, policy context, exam eligibility, or user-facing source trust;
- no unverified row becomes visible to aspirants;
- no missing content is fabricated;
- no waiver changes mastery, mock selection, study-plan generation, plan adaptation, or notification truth;
- waiver state is admin-only.

## Admin UI effect

The only permitted UI entry point is contextual to an allowlisted unsatisfied check under Manage Exam → Review & Activate.

Allowed labels:

```text
Request temporary waiver
Review waiver request
Revoke waiver
```

Prohibited labels:

```text
Mark complete
Force complete
Complete anyway
Override status
Waive exam
```

The UI must display simultaneously:

```text
canonical evidence status
waiver lifecycle
reason code and reason
evidence references
requester and approver
expiry
planner effect: none
```

No top-level sidebar destination is created. Waiver history may appear in an embedded drawer or existing audit surface.

## Storage contract for future implementation

Future implementation may add one append-audited waiver table, but not in PR #761.

Minimum conceptual fields:

```text
id
exam_id
exam_cycle_id
step_id
check_id
reason_code
reason
evidence_refs
evidence_fingerprint
lifecycle_status
requested_by
requested_at
approved_by
approved_at
expires_at
revoked_by
revoked_at
supersedes_waiver_id
created_at
updated_at
```

Database constraints must enforce:

- requester differs from approver;
- expiry follows approval/request time;
- exact-scope active uniqueness;
- valid lifecycle transitions;
- approved/active rows have approver and approved_at;
- revoked rows have revoker and revoked_at;
- evidence refs and fingerprint are non-empty;
- step/check and reason code combinations come from the server allowlist.

## Acceptance cases

1. Extraction is failed, applicable official document exists, no active jobs, approved unexpired waiver exists → `status=failed`, `resolution=waiver`, `admin_gate_effect=satisfied_by_waiver`; no extracted text or planner evidence appears.
2. Same case with pending waiver → unsatisfied; no gate effect.
3. Same user requests and approves → approval rejected.
4. `super_admin` lacks explicit approval permission → approval rejected.
5. Missing required source document → waiver request rejected.
6. Extraction job queued/running → waiver request rejected.
7. Zero locked topic coverage → waiver request rejected; topic coverage remains hard blocked.
8. Missing required phases → waiver request rejected.
9. Informational pending policy update with no impact flags → may be waived.
10. Pending policy update with `affects_syllabus=true` → waiver rejected.
11. Evidence fingerprint changes → waiver becomes `needs_revalidation`; gate effect removed.
12. Evidence becomes ready → waiver becomes `superseded_by_evidence`; evidence resolution wins.
13. Expired waiver → no gate effect even if expiry worker has not run.
14. Revoked waiver → readiness recomputed immediately.
15. Audit insert failure → waiver mutation fails atomically.
16. Planner query receives identical canonical evidence before and after waiver.
17. Frontend attempts to infer waiver effect → prohibited; tests require backend fields.
18. Same exam/cycle returns consistent verdict and active-waiver metadata across catalogue/detail/readiness surfaces.

## Deferred beyond v1

- permanent waivers;
- wildcard exam/family waivers;
- waivers for locked topic coverage, cycle details, phases, source-document absence, or planner inputs;
- one-person emergency approval;
- unrestricted exception codes;
- waiver effect on Study OS, aspirant UI, eligibility, notifications, scoring, analytics, or planner;
- automatic waiver creation;
- AI-generated waiver reasons or approval decisions.

## Final decision boundary

D13 is approved only as the contract above.

It does not authorize implementation in PR #761. The runtime implementation must be a separate gated PR with migration, explicit-permission auth, transactional RPC/audit, backend classifier integration, UI, tests, and checklist updates.
