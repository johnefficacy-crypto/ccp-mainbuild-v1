# Bundle Budget Policy

This repository enforces a frontend bundle budget in CI to protect route-level lazy splitting and prevent admin/prototype code from leaking into public entry surfaces.

## Thresholds

Current enforced limits:

- **Main chunk gzip size must be ≤ 200 KB**.
- **Any bundle that is reachable from `/` or `/login` must not include**:
  - `pages/admin/**`
  - `pages/prototype/**`
  - `src/prototype/**`

The check runs from `app/frontend/scripts/check-bundle-budget.mjs` and is wired into CI after production build.

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
   - `app/frontend/scripts/check-bundle-budget.mjs`
   - any CI wiring if applicable.

Do **not** raise the budget as a first response to CI failures; investigate bundle composition and lazy-loading boundaries first.
