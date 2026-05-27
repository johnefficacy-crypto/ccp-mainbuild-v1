---
owner: ops
status: live
last_verified_against_code: 2026-05-27
source_of_truth: process
related_code:
  - .github/pull_request_template.md
  - .github/workflows/click-through-check.yml
  - scripts/check-click-through.js
review_cadence: per-sprint
---

# Click-Through Review Discipline

## Why this exists

Across PR2, PR3, PR4, and PR6 we shipped PRs that claimed end-to-end completion
and merged green — then logs and audits later found route mismatches, swallowed
errors, endpoints pointing at missing tables, and capabilities that no real user
had ever exercised. PR-fix-5 through PR-fix-8 exist almost entirely to clean up
that class of bug.

The gap is not test coverage. Unit tests catch contract violations and E2E
catches happy-path flows. What was missing is **deliberate manual click-through
before merge** — a human actually using the feature with the network tab open
and confirming what the PR claims.

This is process, not code. It is additive discipline on top of automated tests,
not a replacement for them. It is the highest-leverage change in the build
sequence because it prevents the entire class of bug that the fix-PRs chase
after the fact.

## The rule

> No user-facing PR merges without a documented manual click-through by both
> author and reviewer, with the network tab visible, documented in the PR
> description, and the reviewer signing off after replicating the flow.

"User-facing" means the PR diff touches `app/frontend/` or
`app/backend/app/api/`.

## What the author does

1. Run the feature locally (or on staging).
2. Open browser devtools, **Network** tab, and walk the primary flow end to end.
3. Confirm:
   - Zero unexpected `4xx`/`5xx` responses (any that are expected are documented).
   - Console is clean — no errors, no missing-key/prop warnings.
4. Capture a screenshot or short screen recording of the primary flow.
5. Fill in the **Click-through verification** section of the PR template:
   - Check the boxes.
   - Describe the exact **flow walked**.
   - Paste the **network requests observed** (paths + status codes).
   - List **known issues found and filed** — file them as separate issues; do
     not bundle fixes into this PR.

## What the reviewer does

A reviewer's approval of a user-facing PR is contingent on:

1. Reading the click-through description.
2. Running the flow themselves in their local environment (or staging).
3. Confirming their network-tab observations match what the PR claims.

If a reviewer cannot replicate (no local env, no staging access), that is a
separate problem to fix — but they should **not** approve a user-facing PR they
cannot verify. Flag it instead of rubber-stamping.

## CI enforcement

`.github/workflows/click-through-check.yml` runs `scripts/check-click-through.js`
on every PR. The check:

- Computes the PR's changed files.
- If none are under `app/frontend/` or `app/backend/app/api/`, it passes
  (no user surface).
- Otherwise it requires the **Click-through verification** section to exist in
  the PR body with at least one checked box.
- Honors the override labels below.

### Advisory now, blocking later

The check ships **advisory**: a violation prints a warning annotation but does
not fail the build (`CLICK_THROUGH_ENFORCE: warn`). After a two-sprint soak
(**target cutover: 2026-07-08**) we flip it to `block` in the workflow env, and
missing click-through documentation fails the check for user-facing PRs.

To flip it, change `CLICK_THROUGH_ENFORCE` from `warn` to `block` in
`.github/workflows/click-through-check.yml`.

## Labels

Defined in `.github/labels.json` and synced to the repo by
`.github/workflows/labels-sync.yml` (runs on `main` when the definitions change,
or via manual `workflow_dispatch`).

| Label | When to use |
|---|---|
| `click-through-na` | PR has no user-facing surface: pure backend library, docs/README, internal tooling/CLI, or a migration with no API surface. Apply the label **and** leave a comment justifying it. |
| `hotfix-skip-click-through` | Genuine emergency hotfix that cannot wait for a click-through. Apply the label, then open a **mandatory** follow-up click-through audit issue. |

The CI check passes immediately when either label is present.

## Exception process

Some PRs legitimately have no click-through:

- Pure backend libraries (e.g. the PR4a derivation library).
- Docs / READMEs.
- Internal tooling (e.g. the PR2e CLI).
- Migrations with no API surface.

For these, write `N/A — backend-only library / docs / tooling` in the
click-through section and apply the `click-through-na` label with a one-line
justification.

## Emergency hotfixes

Emergency hotfixes are not blocked. Apply `hotfix-skip-click-through`, merge, and
**immediately** file a follow-up click-through audit issue so the flow is walked
after the fire is out. The follow-up is mandatory, not optional.

## Retroactive audit

The prior build (PR1, PR2, PR3, PR4, PR5, PR6, and PR-fix-1 through PR-fix-4)
merged without this discipline. Rather than bundle the cleanup into a single
mega-fix (which is how PR-fix-5 through PR-fix-8 happened), we audit deliberately:

1. One tracking issue per prior PR (label: `click-through-audit`).
2. The owner runs the click-through they should have done originally.
3. Anything found is filed as its own bug.
4. Those bugs go into the **next** sprint — not bundled together.

## Non-goals

- Replacing automated tests with manual review. This is additive.
- Mandating click-through for backend libraries with no user surface.
- Blocking emergency hotfixes (see above).
