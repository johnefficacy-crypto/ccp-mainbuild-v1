// Static breadcrumb trail map for aspirant app routes.
// - Only routes that exist in appRoutes.jsx are listed.
// - Returns null for shallow index routes (D3 denylist).
// - Leaf label comes from the map's `fallbackLabel`; child pages may
//   override it via useBreadcrumbLeaf (BreadcrumbLeafContext.jsx).

const SHALLOW = new Set([
  "/app/today",
  "/app/eligibility",
  "/app/eligibility/exams",
  "/app/eligibility/recruitments",
  "/app/eligibility/tracker",
  "/app/study",
  "/app/study/plan",
  "/app/study/learning",
  "/app/study/progress",
]);

// Each entry: { pattern (RegExp), ancestors, fallbackLabel }
// ancestors: [{ label, to }] — the non-leaf links left-to-right.
// to in ancestors uses the literal path string (not the matched pathname).
const TRAIL_DEFS = [
  {
    pattern: /^\/app\/eligibility\/exams\/[^/]+$/,
    ancestors: [
      { label: "Eligibility", to: "/app/eligibility" },
      { label: "Exams", to: "/app/eligibility/exams" },
    ],
    fallbackLabel: "Exam",
  },
  {
    pattern: /^\/app\/eligibility\/recruitments\/[^/]+$/,
    ancestors: [
      { label: "Eligibility", to: "/app/eligibility" },
      { label: "Recruitments", to: "/app/eligibility/recruitments" },
    ],
    fallbackLabel: "Recruitment",
  },
  {
    pattern: /^\/app\/study\/mocks\/attempts\/[^/]+\/result$/,
    ancestors: [
      { label: "Study", to: "/app/study" },
      { label: "Mocks", to: "/app/study/mocks" },
    ],
    fallbackLabel: "Result",
  },
  {
    pattern: /^\/app\/study\/mocks\/attempts\/[^/]+\/review$/,
    ancestors: [
      { label: "Study", to: "/app/study" },
      { label: "Mocks", to: "/app/study/mocks" },
    ],
    fallbackLabel: "Review",
  },

  {
    pattern: /^\/app\/marketplace\/[^/]+\/learn$/,
    ancestors: [
      { label: "Marketplace", to: "/app/marketplace" },
      // Resolve parent :id segment from the current pathname
      { label: "Detail", to: null, resolveParent: true },
    ],
    fallbackLabel: "Learn",
  },
  {
    pattern: /^\/app\/marketplace\/[^/]+$/,
    ancestors: [{ label: "Marketplace", to: "/app/marketplace" }],
    fallbackLabel: "Detail",
  },
  {
    pattern: /^\/app\/mentors\/[^/]+$/,
    ancestors: [{ label: "Mentors", to: "/app/mentors" }],
    fallbackLabel: "Detail",
  },
  {
    pattern: /^\/app\/notifications\/preferences$/,
    ancestors: [{ label: "Notifications", to: "/app/notifications" }],
    fallbackLabel: "Preferences",
  },
];

/**
 * Resolve the breadcrumb trail for a given pathname.
 * Returns null when no trail should be shown (shallow routes, unmapped paths).
 *
 * @param {string} pathname
 * @param {string|null} leafOverride  from useBreadcrumbLeaf context
 * @returns {{ ancestors: {label:string, to:string}[], leaf: string } | null}
 */
export function getBreadcrumbs(pathname, leafOverride = null) {
  if (SHALLOW.has(pathname)) return null;

  const communityMatch = pathname.match(/^\/app\/community\/([^/]+)(?:\/([^/]+))?(?:\/([^/]+))?$/);
  if (communityMatch) {
    const [, spaceId, channelId, threadId] = communityMatch;
    const ancestors = [{ label: "Community", to: "/app/community" }];
    if (channelId) ancestors.push({ label: "Space", to: `/app/community/${spaceId}` });
    if (threadId) ancestors.push({ label: "Channel", to: `/app/community/${spaceId}/${channelId}` });

    return {
      ancestors,
      leaf: leafOverride || (threadId ? "Thread" : channelId ? "Channel" : "Space"),
    };
  }

  for (const def of TRAIL_DEFS) {
    if (!def.pattern.test(pathname)) continue;

    const ancestors = def.ancestors.map((a) => {
      if (a.resolveParent) {
        // Derive parent segment from pathname (strips the last segment).
        const parentTo = pathname.replace(/\/[^/]+$/, "");
        return { label: a.label, to: parentTo };
      }
      return { label: a.label, to: a.to };
    });

    return {
      ancestors,
      leaf: leafOverride || def.fallbackLabel,
    };
  }

  return null;
}
