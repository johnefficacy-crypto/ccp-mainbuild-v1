# Operator validation workflow

Operator validation is recorded once, not copied across a global checklist, a track checklist, a runbook, and an audit.

## Sources of truth

- `registry.json` is the only mutable source for operator-gate status, next action, review date, blockers, and evidence links.
- `INDEX.md` is generated from the registry. Never edit it manually.
- Existing architecture/status documents describe implementation scope and dependencies; they are references, not operator-status mirrors.
- Runbooks are reusable procedures. A revalidation reuses the same runbook instead of creating another checklist.
- Evidence records are immutable execution results. Add a new evidence file for a materially new run; do not rewrite an earlier result.

The large `docs/status/career-copilot-checklist.md` remains useful for implementation and product-decision history, but migrated operator gates must not duplicate live-validation status there.

## Gate lifecycle

Use one of these registry statuses:

`planned` → `code_present` → `validation_pending` / `operator_pending` → `in_progress` → `passed`

Alternative outcomes are `partial_pass`, `failed`, `blocked`, `cancelled`, or `superseded`.

`partial_pass`, `passed`, and `failed` require at least one evidence record. Every non-terminal gate requires a future `review_by` date; CI fails after that date until the gate is reviewed.

## Implementation PR

1. Add or update one gate in `registry.json`.
2. Link the existing implementation contract/status document. Do not copy its checklist.
3. Link one reusable runbook when the gate is ready for operator work.
4. Set `status`, `updated_at`, `review_by`, `next_action`, blockers, and dependencies.
5. Run:

```bash
node scripts/operator-validation.js --write
node --test scripts/__tests__/operator-validation.test.js
node scripts/operator-validation.js --check
```

## Operator execution

1. Execute the linked runbook against the named environment and deployment SHA.
2. Create one evidence record under `docs/operator-validation/evidence/` using `EVIDENCE_TEMPLATE.md`.
3. Redact tokens, cookies, API keys, authorization headers, and unnecessary personal data.
4. Append the evidence entry to the existing gate in `registry.json`.
5. Update the gate status, next action, dates, and blockers.
6. Regenerate `INDEX.md`.

A repeated run appends evidence to the same gate. Create a new gate only when the acceptance contract or independently promotable boundary changes.

## Staleness and synchronization controls

The GitHub workflow validates:

- unique track and gate IDs;
- allowed statuses and required fields;
- referenced implementation, runbook, and evidence paths;
- evidence presence for partial/pass/fail outcomes;
- dependency references;
- overdue `review_by` dates;
- exact regeneration of `INDEX.md`;
- registry updates when a registered source, runbook, or evidence file changes.

The generated index is intentionally small: one row per operator gate, not one row per implementation step.
