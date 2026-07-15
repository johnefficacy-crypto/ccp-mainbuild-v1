# Operator validation workflow

Operator validation is recorded once, not copied across a global checklist, track checklist, runbook, and audit.

## Sources of truth

- `registry.json` is the only mutable source for operator-gate status, next action, exact UTC review timestamp, blockers, defects, and evidence links.
- `INDEX.md` is generated from the registry. Never edit it manually.
- Architecture/status documents describe implementation scope and product decisions; they are references, not operator-status mirrors after a gate is migrated.
- Runbooks are reusable procedures. Revalidation reuses the same runbook instead of creating another checklist.
- Evidence records are immutable execution results. Add a new evidence file for a materially new run; do not rewrite an earlier result.

The large `docs/status/career-copilot-checklist.md` remains implementation and product-decision history. Migrated operator gates must not duplicate mutable live-validation status there. `AGENTS.md` and `CLAUDE.md` enforce this split for future agent work.

## Gate lifecycle

Use one of these registry statuses:

`planned` → `code_present` → `validation_pending` / `operator_pending` → `in_progress` → `passed`

Alternative outcomes are `partial_pass`, `failed`, `blocked`, `cancelled`, or `superseded`.

`partial_pass`, `passed`, and `failed` require evidence. Every non-terminal gate requires `review_by` as an exact RFC3339 UTC timestamp: `YYYY-MM-DDTHH:mm:ssZ`. CI fails as soon as that instant passes.

## Defect accounting

Every gate has two arrays:

- `defects_found`: cumulative defects discovered by code review or operator evidence.
- `defects_fixed`: the subset with a verified code/data/documentation remediation.

Each item has a stable kebab-case `id` and concise `summary`. A fixed ID must already exist in `defects_found`. Moving a defect into `defects_fixed` does not prove live closure: keep the gate `validation_pending` until the remediation is deployed and revalidated.

## Implementation PR

1. Add or update one gate in `registry.json`.
2. Link existing contracts/status documents; do not copy their checklists.
3. Link one reusable runbook when operator work is actionable.
4. Set status, `updated_at`, exact UTC `review_by`, next action, defects, blockers, and dependencies.
5. Regenerate and verify:

```bash
node scripts/operator-validation.js --write
node --test scripts/__tests__/operator-validation.test.js
node scripts/operator-validation.js --check
```

## Operator execution

1. Execute the linked runbook against the named environment and deployment SHA.
2. Create one immutable evidence record under `docs/operator-validation/evidence/` using `EVIDENCE_TEMPLATE.md`.
3. Redact tokens, cookies, API keys, authorization headers, and unnecessary personal data.
4. Append the evidence entry to the existing gate.
5. Reconcile defects found/fixed, status, next action, exact review timestamp, and blockers.
6. Regenerate `INDEX.md`.

A repeated run appends evidence to the same gate. Create a new gate only when the acceptance contract or independently promotable boundary changes.

## Staleness and synchronization controls

The workflow validates:

- unique track, gate, and defect IDs;
- allowed statuses and required fields;
- fixed defects reference known found defects;
- referenced implementation, runbook, and evidence paths;
- evidence presence for partial/pass/fail outcomes;
- dependency references;
- exact UTC `review_by` timestamps and overdue instants;
- exact regeneration of `INDEX.md`;
- registry updates when a registered source, runbook, or evidence file changes.

The generated index stays compact: one row per gate, with defects found/fixed summarized in dedicated columns.
