# Bundle Budget Policy

This repository enforces a frontend bundle budget in CI to protect route-level lazy splitting and prevent admin/prototype code from leaking into public entry surfaces.

## Thresholds

Current enforced limits:

- **Initial (entry) chunk gzip size must be ≤ 220 KB** (`main.*.js`).
- **The initial chunk must not statically include** any of:
  - `pages/admin/`
  - `pages/prototype/`
  - `pages/study/Mocks.jsx` (the user mocks page must be lazy)
  - `pages/StudyPlan.jsx`
  - `features/community/`
  - `recharts` (the entire chart lib)
  - `react-day-picker`

The check runs from `scripts/check-bundle.js` and is wired into CI after the
production build (`npm run check:bundle-budget`). It works in two independent
ways:

1. **Forbidden-in-initial** — a static import-graph walk from `src/index.js`.
   A `lazy(() => import('...'))` is a dynamic import and is *not* followed, so
   lazy routes stay out of the initial chunk; a plain `import X from '...'`
   *is* followed, so re-introducing forbidden code via a static import fails
   the gate with a message naming the offending file and specifier.
2. **Size budget** — the emitted `main.*.js` is gzipped with `zlib` and
   compared against the cap; a violation reports the actual measured size.

`source-map-explorer` is available as an opt-in byte-level cross-check
(`npm run check:bundle -- --sme` or `CHECK_BUNDLE_SME=1`). It is **not** part
of the gate by default because source-map-explorer 2.5.x trips on CRA's
minified entry sourcemap ("generated column Infinity"); the static graph walk
is the authoritative, deterministic signal.

## Local Run

From repo root:

```bash
cd app/frontend
npm ci
npm run build
npm run check:bundle-budget
```

Or from any environment that already has dependencies installed:

```bash
cd app/frontend && npm run build && npm run check:bundle-budget
```

## Lazy-Splitting Guardrail

`src/routes/*Routes.jsx` files must **not** statically import from `../pages/**`.
Only lazy loading is allowed, for example:

```jsx
const Dashboard = lazy(() => import('../pages/Dashboard'));
```

Static imports from `../pages/**` in route modules fail ESLint via a restricted-import rule.

## Raising the Budget

Any change to thresholds or forbidden-module constraints requires:

1. A PR with a clear justification (why split/caching cannot resolve it).
2. Reviewer approval explicitly acknowledging the budget change.
3. Corresponding updates to:
   - `BUNDLE_BUDGET.md`
   - `scripts/check-bundle.js`
   - any CI wiring if applicable.

Do **not** raise the budget as a first response to CI failures; investigate bundle composition and lazy-loading boundaries first.
