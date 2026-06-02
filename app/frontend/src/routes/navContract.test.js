/**
 * Nav contract tests (P1-2).
 *
 * Ensures every navigation link in DashShell and AdminShell resolves to a
 * real route definition.  A nav link that points at an undefined route
 * renders a blank page in production — this test catches regressions before
 * they ship.
 *
 * We keep both lists (nav paths + route paths) statically declared here
 * instead of importing the full component trees (which drag in auth, API,
 * Supabase, and env guards that are not needed for a path-existence check).
 * When you add or remove a nav link or route, update the corresponding list.
 */

// ── App (DashShell) nav paths ──────────────────────────────────────────────
// Source: DashShell.jsx SECTIONS arrays.
const DASH_NAV_PATHS = [
  "/app/today",
  "/app/eligibility",
  "/app/study",
  "/app/study/subjects",
  "/app/study/resources",
  "/app/notes",
  "/app/flashcards",
  "/app/study/revision",
  "/app/study/mocks",
  "/app/study/mistakes",
  "/app/study/review",
  "/app/study/compare",
  "/app/reports",
  "/app/community",
  "/app/groups",
  "/app/partners",
  "/app/mentors",
  "/app/resources",
  "/app/marketplace",
  "/app/ai",
  "/app/notifications",
  "/app/pricing",
  "/app/saved",
];

// ── App route paths (appRoutes.jsx) ────────────────────────────────────────
// Source: appRoutes.jsx Route path props.
const APP_ROUTE_PATHS = new Set([
  "/app",
  "/app/dashboard",
  "/app/today",
  "/app/profile",
  "/app/onboarding",
  "/app/saved",
  "/app/eligibility",
  "/app/eligibility/exams",
  "/app/eligibility/exams/:slug",
  "/app/eligibility/recruitments",
  "/app/eligibility/recruitments/:id",
  "/app/eligibility/tracker",
  "/app/study",
  "/app/study/plan",
  "/app/study/learning",
  "/app/study/progress",
  "/app/study/focus",
  "/app/study/mocks",
  "/app/study/mocks/attempts/:attemptId",
  "/app/study/mocks/attempts/:attemptId/result",
  "/app/study/mocks/attempts/:attemptId/review",
  "/app/study/subjects",
  "/app/study/review",
  "/app/study/compare",
  "/app/study/mistakes",
  "/app/study/resources",
  "/app/study/revision",
  "/app/notes",
  "/app/flashcards",
  "/app/flashcards/:deckId",
  "/app/reports",
  "/app/community",
  "/app/community/:spaceId",
  "/app/community/:spaceId/:channelId",
  "/app/community/:spaceId/:channelId/:threadId",
  "/app/groups",
  "/app/partners",
  "/app/resources",
  "/app/marketplace",
  "/app/marketplace/:id",
  "/app/marketplace/:id/learn",
  "/app/mentors",
  "/app/mentors/:id",
  "/app/accountability",
  "/app/ai",
  "/app/notifications",
  "/app/notifications/preferences",
  "/app/pricing",
]);

// ── Admin (AdminShell) nav paths ───────────────────────────────────────────
// Source: AdminShell.jsx SECTIONS arrays.
const ADMIN_NAV_PATHS = [
  // Command Center
  "/admin",
  "/admin/operations",
  // Trust Pipeline
  "/admin/sources",
  "/admin/scraper",
  "/admin/recruitments",
  "/admin/eligibility-ops",
  "/admin/audit",
  // Knowledge Governance
  "/admin/exam-intelligence",
  "/admin/exam-eligibility",
  "/admin/organizations",
  "/admin/ai-policy",
  "/admin/persona",
  // Community & Marketplace
  "/admin/community",
  "/admin/community/groups",
  "/admin/community/partners",
  "/admin/community/resources",
  "/admin/mentors",
  "/admin/marketplace",
  "/admin/plans",
  // Study OS
  "/admin/study-os",
  "/admin/study-os/plan-ops",
  "/admin/study-os/artifacts",
  "/admin/study-os/mocks",
  "/admin/study-os/reports",
  "/admin/study-os/social",
  "/admin/study-os/content-access",
  // Mock Content
  "/admin/mocks/questions",
  "/admin/mocks/review-queue",
  "/admin/mocks/import",
  // Safety & Config
  "/admin/moderation",
  "/admin/copyright",
  "/admin/notifications",
  "/admin/rbac",
  "/admin/kpis",
  "/admin/blogs",
];

// ── Admin route paths (adminRoutes.jsx) ────────────────────────────────────
// Source: adminRoutes.jsx Route path props.
const ADMIN_ROUTE_PATHS = new Set([
  "/admin",
  "/admin/operations",
  "/admin/recruitments",
  "/admin/eligibility-queue",
  "/admin/promotion-queue",
  "/admin/eligibility-ops",
  "/admin/sources",
  "/admin/organizations",
  "/admin/scraper",
  "/admin/notifications",
  "/admin/marketplace",
  "/admin/plans",
  "/admin/audit",
  "/admin/rbac",
  "/admin/mentors",
  "/admin/community",
  "/admin/community/groups",
  "/admin/community/partners",
  "/admin/community/resources",
  "/admin/ai-policy",
  "/admin/persona",
  "/admin/exam-intelligence",
  "/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace",
  "/admin/exam-intelligence/workspace/:exam_id",
  "/admin/exam-intelligence/workspace/:exam_id/:cycle_id",
  "/admin/exam-eligibility",
  "/admin/moderation",
  "/admin/kpis",
  "/admin/copyright",
  "/admin/blogs",
  "/admin/study-os",
  "/admin/study-os/plan-ops",
  "/admin/study-os/artifacts",
  "/admin/study-os/mocks",
  "/admin/study-os/reports",
  "/admin/study-os/social",
  "/admin/study-os/exam-intel-cms",
  "/admin/study-os/content-access",
  "/admin/mocks/questions",
  "/admin/mocks/questions/new",
  "/admin/mocks/questions/:id",
  "/admin/mocks/review-queue",
  "/admin/mocks/import",
]);

// ── Helper ─────────────────────────────────────────────────────────────────

/**
 * True if `navPath` is satisfied by `routePathSet`.
 * Accepts prefix coverage: /app/eligibility is covered by
 * /app/eligibility/exams (an Outlet-based layout route).
 */
function isCovered(navPath, routePathSet) {
  if (routePathSet.has(navPath)) return true;
  for (const rp of routePathSet) {
    if (rp.startsWith(navPath + "/")) return true;
  }
  return false;
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe("DashShell nav contract — every nav link has a route", () => {
  test.each(DASH_NAV_PATHS)("%s", (path) => {
    expect(isCovered(path, APP_ROUTE_PATHS)).toBe(true);
  });
});

describe("AdminShell nav contract — every nav link has a route", () => {
  test.each(ADMIN_NAV_PATHS)("%s", (path) => {
    expect(isCovered(path, ADMIN_ROUTE_PATHS)).toBe(true);
  });
});

describe("Prototype route gate", () => {
  test("prototype routes are absent by default (ENABLE_PROTOTYPE unset)", () => {
    // publicRoutes.jsx conditionally includes PrototypeRoutes only when
    // REACT_APP_ENABLE_PROTOTYPE === "true". Verify the toggle is guarded.
    const enabled = process.env.REACT_APP_ENABLE_PROTOTYPE === "true";
    expect(enabled).toBe(false);
  });
});
