# Follow-up: Study leaf route nesting (D5 — deferred)

## What was deferred

Routes under `/app/study` that are currently declared as siblings of the `StudyShell` outlet:

```
/app/study/focus
/app/study/mocks
/app/study/mocks/attempts/:attemptId
/app/study/subjects
/app/study/review
/app/study/compare
/app/study/resources
/app/study/revision
/app/study/mistakes
```

These are **not** nested under `<StudyShell>` in `appRoutes.jsx`, so they do not inherit the Study sub-nav tabs. Breadcrumbs provide context for the mock result/review routes (the two deep enough to need it), but the flat routes themselves have no Study shell header.

## Why it was deferred

Nesting these routes would require:
1. Moving each route declaration inside the `<StudyShell>` Route block in `appRoutes.jsx`.
2. Verifying each page does not rely on assuming no shell wrapper (layout side-effects, header conflicts).
3. Updating any tests that rely on the current flat route structure.

This is non-trivial churn with risk of regressions in the Study surface. The breadcrumb trail for mocks result/review already provides the orientation signal described in the spec. Deferring avoids test churn and layout risk in this PR.

## What a future PR should do

1. Move the leaf routes into the `StudyShell` Route block.
2. Confirm each page looks correct with the Study section header + sub-nav above it.
3. Remove the flat sibling declarations.
4. Update `appRoutes.test.js` / `navContract.test.js` to reflect the new nesting.
