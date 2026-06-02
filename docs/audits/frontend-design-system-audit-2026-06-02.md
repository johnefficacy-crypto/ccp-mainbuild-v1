# Frontend & Design System Audit — 2026-06-02

Consolidated from two passes (shallow inventory + deeper critical pass). Dedup'd, re-prioritized. Deeper pass wins on severity.

## Verdict

- Production frontend-ready: **No**.
- Design-system maturity: **Low–Medium**.
- Foundation is sound (route shell, auth, `api.js`, lazy loading, shared primitives, admin shell, CI). It is **feature-built, not system-built**: the right primitives exist (`api.js`, `useApiAction`, `useApiCollection`, `ErrorState`, `ToastProvider`) but screens bypass them.

### Top 5 blockers (ship gate)

1. RouteErrorBoundary does not reset on navigation — one crash poisons the app subtree.
2. Silent mutations — `.catch(() => {})` after `api.post/patch/delete` hides backend rejection.
3. Seed/demo leakage — empty or failed backend renders fake data on trust surfaces.
4. `PartnersScreen` crashes on live backend (`thisWeek.self`/`thisWeek.partner` vs `thisWeek: {}`).
5. No visible API error states + no route/nav contract tests.

---

## Priority order (single source of truth)

1. Route error-boundary reset
2. Kill silent mutations
3. Seed/live data policy
4. Community/resources live-data correctness (incl. PartnersScreen crash)
5. Visible API error states (page-state contract)
6. Route/nav contract tests
7. Query-client staleness defaults
8. Production env build guard
9. Design-token consolidation
10. Component dedupe
11. Accessibility pass
12. Admin console unification
13. Visual regression baseline

> Dropped from blocker tier (still do, lower): token consolidation, dedupe, a11y, admin unification, visual regression. These are quality, not correctness. Doc1 ranked them too high.

---

## P0 — ship blockers

### P0-1 — RouteErrorBoundary reset
Files: `components/RouteErrorBoundary.jsx`, `routes/appRoutes.jsx`
Fix: make location-aware — `useLocation()` wrapper passing `resetKey={location.pathname}`, or key the boundary by pathname.
Accept: crash `/app/community`, navigate `/app/today` → recovers, no full reload.

### P0-2 — Kill silent mutations
Files: every `.catch(() => {})` after `api.post/patch/delete`. Use existing `lib/hooks/useApiAction.js`.
Fix: mandate `useApiAction()` for all user-triggered mutations. Optimistic → POST → rollback on fail → toast.
Accept: grep `.catch(() => {})` in `src` returns zero for mutation paths, or each survivor documented non-critical.

### P0-3 — Seed/live data policy
Files: `lib/hooks/useApiCollection.js`; community/resources/marketplace pages using seeds.
Fix: error state must NOT render seed fixtures. Seeds only when `REACT_APP_ENABLE_DEMO_DATA=true`.
Accept: fresh prod DB (0 rows) → true empty state. Backend failure → error/degraded. Seeds only in demo mode.

### P0-4 — Community/resources live correctness
Files: `features/community/{CommunityScreen,StudyGroupsScreen,PartnersScreen,MentorsScreen,ResourcesScreen}.jsx`. Treat `audit-frontend-community.md` as bug backlog, not docs.
Fix:
- PartnersScreen: null-safe `thisWeek` (handle `{}`).
- Clickable cards → links/buttons (keyboard reachable).
- Open/Save/Report: wire or remove.
- vote/join/invite/rsvp: reconcile or rollback (via P0-2 hook).
- "My groups" / "New" sort: stop silently emptying / pinned-only.
Accept: each `audit-frontend-community.md` item mapped fixed/not-fixed with file:line.

---

## P1 — reliability + contracts

### P1-1 — Page-state contract everywhere
Files: `Marketplace.jsx`, `Pricing.jsx`, `Saved.jsx`, `Blogs.jsx`, `ResourceDetail.jsx`, `features/dashboard/hooks/useDashboardData.js`.
Contract: `idle → loading → data | empty | error | degraded`.
Fix: replace silent `.catch(() => {})` reads + `finally`-only loading clears with `ErrorState` + retry. Dashboard renders degraded when `errors.recruitments`/`errors.apps` set (not empty).
Accept: no API failure renders as empty data; every prod page has all states.

### P1-2 — Route/nav contract tests
Files: `routes/{appRoutes,adminRoutes,publicRoutes}.jsx`, `pages/DashShell.jsx`, `pages/admin/AdminShell.jsx`, new inventory test.
Tests: all DashShell links resolve; all AdminShell links resolve; all notification CTA paths resolve; prototype routes blocked unless `REACT_APP_ENABLE_PROTOTYPE=true`.
Accept: every visible nav target maps to a mounted route; no dangling links.

### P1-3 — Query-client staleness
File: `shared/api/queryClient.js`.
Fix: keep relaxed defaults for dashboards only. Per-domain freshness — notifications: refetch focus/reconnect; admin queues: short stale; payments/subs: refetch on focus + after mutation; scraper: poll/explicit refresh.
Accept: each critical hook declares freshness explicitly.

### P1-4 — Production env build guard
File: `shared/config/env.js`.
Fix: prod build FAILS if `REACT_APP_BACKEND_URL` empty; FAILS if `REACT_APP_ENABLE_PROTOTYPE=true` in prod.
Accept: bad prod build fails at build, not in user session.

---

## P2 — design system + a11y + polish

### P2-1 — Design-token consolidation
Files: `tailwind.config.js`, `index.css`, `admin-console.css`, `shared/ui/studyos/primitives.jsx`, `features/community/ui/index.jsx`.
Three+ active systems (Tailwind tokens, global CSS classes, Study OS primitives, Community "Field", admin console). Define: core tokens (color/type/radius/spacing/shadow/z/motion/focus-ring) → core primitives → domain skins consuming core.
Accept: no new raw hex outside token files; status colors from token map; buttons/pills/cards use canonical primitives. Add lint/script banning raw hex in `src/pages` + `src/features`.

### P2-2 — Component dedupe
Files: `shared/ui/*`, `features/community/ui/index.jsx`, `pages/admin/mocks/components/StatusBadge.jsx`, page-local repeats.
Canonicalize: Button, Card, Pill, Badge, EmptyState, ErrorState, Drawer, Modal, Table, Tabs.
Accept: component registry doc; high-repeat moved to `shared/ui`; feature primitives clearly scoped.

### P2-3 — Accessibility pass
Files: route-level pages, `DashShell.jsx`, `AdminShell.jsx`, community/resources, modal/drawer.
Fix: no clickable non-interactive elements; icon-only buttons labeled; drawer focus trap + Esc + restore focus + scroll lock; skip-to-main link (`#main-content`); table headers; status not color-only; mobile drawer keyboard-usable; route-level skeletons for dense screens.
Accept: keyboard-only user navigates app/admin/community.

### P2-4 — Admin console unification
Files: `pages/admin/AdminShell.jsx`, `admin-console.css`, `pages/admin/*`, `features/admin/*`.
Fix: normalize `oc-*`/`btn`/inline → canonical section/nav primitives; admin tables use `AdminTable`/`RowActions`/`StatusBadge`. Don't break dense layouts.

### P2-5 — Visual regression baseline
Files: `e2e`, new Playwright visual smoke.
Screens: Landing, Login, Today, Eligibility, Study Home, Marketplace, Community, Pricing, Admin Overview, Admin Operations, Admin Exam Intelligence.
Accept: screenshots in CI/local; layout shifts caught pre-merge.

> Ties into your PR8 (Playwright E2E regression). Fold P2-5 into that track, not a separate PR.

### P2-6 — Type safety (longer arc)
No TS on main frontend; zod/RHF present. Short: zod schemas at API boundaries. Mid: generated OpenAPI client. Long: TS for `lib`, `shared`, then routes.

---

## Notes / decisions

- `ProtectedRoute.jsx` is correctly documented UX-only; backend enforces. Add permission-aware disabled states for admin buttons/routes — UX only, not P0.
- Toast infra exists but underused — fold into P0-2 (every POST/PATCH/DELETE surfaces failure toast).
- Governance is the real lever: every new route uses shared page-state primitives; every mutation uses `useApiAction`; every seed-fallback collection uses `useApiCollection`. Add to AGENTS.md.
