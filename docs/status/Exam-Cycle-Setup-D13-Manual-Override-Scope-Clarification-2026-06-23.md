# Exam Cycle Setup Gate — D13 Manual Override Scope Clarification

- Decision ID: D13
- Status: UNRESOLVED — OPERATOR DECISION REQUIRED
- Operator clarification date: 2026-06-23
- Parent gate: `docs/status/Exam-Cycle-Setup-Gate-2026-06-22.md`
- Related record: `docs/status/Exam-Cycle-Setup-D12-D16-Decision-Record-2026-06-23.md`
- Runtime effect: None. This clarification is documentation-only and authorizes no API, database, backend, frontend, planner, score, blocker, or activation change.

## Scope

D13 governs only a manual override of evidence-derived checklist completion.

```text
D13 — Manual override of evidence-derived checklist completion
Status: UNRESOLVED — OPERATOR DECISION REQUIRED
```

Canonical interim contract:

```text
effective_status = status_derived_from_canonical_evidence
manual_override = prohibited
```

A D13 override would report a checklist step as complete/ready while the canonical evidence still reports an unsatisfied state such as:

```text
missing
uploaded
extracting
review_pending
stale
failed
```

D13 does not govern normal evidence lifecycle operations.

## Evidence review and locking are not D13 overrides

Existing actions that review, verify, reject, or lock underlying evidence mutate the canonical evidence lifecycle. After that mutation, readiness is recomputed from the changed evidence.

Examples:

```text
exam_topic_coverage.reviewer_status → locked
exam_competition_metrics.reviewer_status → reviewed | locked
exam_policy_updates.reviewer_status → verified | rejected
```

These are normal evidence-governance actions, not manual readiness overrides.

`ReviewActivatePanel.jsx` currently exposes row-lock actions through the review endpoints. Those actions change the source row status and then refetch readiness. They do not set a checklist step complete independently.

A D13 override would instead leave the evidence unchanged and replace or suppress the evidence-derived readiness result. That behavior is prohibited while D13 is unresolved.

## Interim fail-closed contract

Until D13 receives a complete operator decision:

- no `Mark complete`, `Force complete`, `Waive`, `Override`, or equivalent readiness control;
- no `override_status`, `manually_completed`, `manual_completion`, `waived_at`, `waived_by`, or equivalent field;
- no readiness-override API, RPC, service, database table, metadata key, or event type;
- no implicit override permission for `super_admin`, repository owner, or any existing review role;
- no completion inferred from reviewer notes, comments, metadata, reason text, or audit annotations;
- no frontend-only completion state or local persisted override;
- no planner-output mutation based on a manual assertion;
- no blocker or advisory suppression based on a manual assertion;
- no readiness score, completion numerator, denominator, activation verdict, or CTA adjustment based on a manual assertion;
- no override implemented indirectly through generic admin-repair endpoints;
- no speculative audit schema for an unapproved override contract.

The backend remains the sole source of readiness and activation truth. The frontend renders the backend contract and must not calculate, replace, or persist readiness authority.

## Required future operator contract

A future approval must define D13 as one complete contract. Partial implementation is prohibited.

```text
permission
overridable_step_ids
allowed_evidence_states
exception_codes
mandatory_reason
mandatory_evidence_refs
expiry_or_revalidation
audit_event_schema
revocation_process
admin_UI_effect
activation_effect
planner_effect
```

The approval must also define:

- whether an override is allowed for hard-gate steps, advisory steps, or both;
- whether an override can coexist with `failed`, `stale`, or actively processing evidence;
- whether the override expires automatically when canonical evidence changes;
- whether revocation immediately restores the evidence-derived result;
- how concurrent evidence updates and override changes are ordered;
- whether override state is returned separately from canonical status;
- how downstream analytics distinguish evidence-backed readiness from waived readiness.

## Safest future model — recommendation only

The safest default, if D13 is eventually approved, is a separately visible waiver rather than mutation of canonical evidence-derived status.

Illustrative, non-approved shape:

```json
{
  "derived_status": "failed",
  "waiver": {
    "active": true,
    "exception_code": "operator_approved_exception",
    "reason": "...",
    "evidence_refs": ["..."],
    "expires_at": "..."
  },
  "effective_status": "ready_with_waiver"
}
```

This example is not a locked contract. In particular, `ready_with_waiver`, field names, storage, permissions, and planner/activation effects remain unapproved.

No implementation may use this illustrative shape until D13 is explicitly resolved.

## Repository verification

Inspected:

```text
docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md
app/frontend/src/pages/admin/exam-workspace/panels/ReviewActivatePanel.jsx
docs/status/Exam-Cycle-Setup-D12-D16-Decision-Record-2026-06-23.md
repository searches for override_status, manually_completed, waived_at,
manual readiness override, force complete, and mark complete
```

Current findings:

- existing Review & Activate actions lock or review underlying rows;
- no manual readiness-completion control was found;
- no override field, table, or endpoint was found;
- current readiness remains evidence-derived;
- D13 remains the only unresolved decision in the D01–D16 register.

## Decision boundary

This clarification locks only the scope and interim prohibition while D13 remains unresolved.

It does not approve:

- any override permission;
- any overridable step;
- any exception code;
- any database schema;
- any API;
- any UI control;
- any effective-status token;
- any blocker, score, activation, or planner effect.
