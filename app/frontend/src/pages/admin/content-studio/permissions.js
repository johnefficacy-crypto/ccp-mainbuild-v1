/**
 * Content Studio permission gates (frontend affordance-hiding only — the
 * backend is authoritative). Tokens per the handoff contract:
 *   reads   = content_studio.author OR content_studio.review
 *             OR exam_intelligence.manage OR exam_intelligence.review OR super_admin
 *   author  = content_studio.author
 *   review  = content_studio.review
 *   propose assignment = exam_intelligence.manage
 *   review/remove assignment = exam_intelligence.review
 */
export function studioPerms(user) {
  const superAdmin = user?.role === "super_admin";
  const has = (p) => superAdmin || (user?.permissions || []).includes(p);
  return {
    canRead:
      superAdmin ||
      has("content_studio.author") ||
      has("content_studio.review") ||
      has("exam_intelligence.manage") ||
      has("exam_intelligence.review"),
    canAuthor: has("content_studio.author"),
    canReview: has("content_studio.review"),
    canProposeAssignment: has("exam_intelligence.manage"),
    canReviewAssignment: has("exam_intelligence.review"),
    // Activation is a SEPARATE, higher-trust authority (EWP-SP2). Neither author
    // nor review may flip is_active — only content_studio.activate (or super_admin).
    canActivate: has("content_studio.activate"),
    // Promoting a CA candidate INTO the objective bank is a publish action — a
    // higher gate than review (GQR-G4). Affordance-hiding only; backend authoritative.
    canPublish: has("mock_questions:publish"),
  };
}
