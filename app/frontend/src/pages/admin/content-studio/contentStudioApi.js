/**
 * Content Studio API adapter — the only place that knows the
 * `/api/admin/content-studio` endpoint shapes (docs/status/ewp-prompt-bank-frontend-handoff.md).
 *
 * Contract highlights the UI must respect:
 * - every write carries a `reason` (8–500 chars) — missing/short reason is a 422
 * - PATCH and review are CAS-guarded: send back the `updated_at` (and for review,
 *   the `reviewer_status`) the browser actually read; stale token → 409
 * - bulk import is atomic all-or-nothing; success returns
 *   `{ok, result:{created,updated,unchanged}}` — there are no per-row results
 * - there is NO activate endpoint (activation is migration-gated) — do not add one
 */
import { api } from "../../../lib/api";

const BASE = "/api/admin/content-studio";

function qs(params) {
  const cleaned = {};
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined) cleaned[k] = v;
  });
  const s = new URLSearchParams(cleaned).toString();
  return s ? `?${s}` : "";
}

export const contentStudioApi = {
  // Reads — author OR review OR exam_intelligence.manage/review OR super_admin
  listPrompts: (params) => api.get(`${BASE}/writing-prompts${qs(params)}`),
  getPrompt: (id) => api.get(`${BASE}/writing-prompts/${id}`),

  // Selector option feeds (EWP-SP4) — readable, dependent pickers replace raw UUIDs.
  listSubjects: () => api.get(`${BASE}/taxonomy/subjects`),
  listTopics: (params) => api.get(`${BASE}/taxonomy/topics${qs(params)}`),
  listExamFamilies: () => api.get(`${BASE}/exam-scope/families`),
  listExams: (params) => api.get(`${BASE}/exam-scope/exams${qs(params)}`),
  listExamPhases: (params) => api.get(`${BASE}/exam-scope/phases${qs(params)}`),
  listRubrics: () => api.get(`${BASE}/rubrics`),
  listSourceDocuments: () => api.get(`${BASE}/source-documents`),
  // Author read-back of the latest reviewer correction note (needs_correction).
  getCorrectionNote: (id) => api.get(`${BASE}/writing-prompts/${id}/correction-note`),

  // Authoring — content_studio.author
  createPrompt: ({ reason, payload }) =>
    api.post(`${BASE}/writing-prompts`, { reason, payload }),
  updatePrompt: (id, { reason, expected_updated_at, payload }) =>
    api.patch(`${BASE}/writing-prompts/${id}`, { reason, expected_updated_at, payload }),
  bulkImportPrompts: ({ reason, subject_id, rows }) =>
    api.post(`${BASE}/writing-prompts/bulk`, { reason, subject_id, rows }),

  // Review lifecycle — content_studio.review
  reviewPrompt: (id, { status, expected_status, expected_updated_at, reason, reviewer_notes }) =>
    api.post(`${BASE}/writing-prompts/${id}/review`, {
      status,
      expected_status,
      expected_updated_at,
      reason,
      ...(reviewer_notes ? { reviewer_notes } : {}),
    }),

  // Exam Assignments (writing_prompt_targets) — J2 propose/review/remove split
  listTargets: (promptId) => api.get(`${BASE}/writing-prompts/${promptId}/targets`),
  proposeTarget: (promptId, body) => api.post(`${BASE}/writing-prompts/${promptId}/targets`, body),
  reviewTarget: (targetId, body) => api.post(`${BASE}/writing-prompt-targets/${targetId}/review`, body),
  removeTarget: (targetId, body) => api.post(`${BASE}/writing-prompt-targets/${targetId}/remove`, body),
};

export const EXERCISE_TYPES = [
  "sentence_construction",
  "sentence_correction",
  "vocabulary_in_context",
  "sentence_rewrite",
  "sentence_reconstruction",
  "paragraph_writing",
  "summary_writing",
  "precis_practice",
  "essay_practice",
  "letter_practice",
];

export const REVIEWER_STATUSES = ["pending", "verified", "rejected", "needs_correction"];

// Legal review transitions (mirror of the backend map; `rejected` is terminal).
export const REVIEW_TRANSITIONS = {
  pending: ["verified", "rejected", "needs_correction"],
  needs_correction: ["verified", "rejected", "pending"],
  verified: ["rejected", "needs_correction"],
  rejected: [],
};

export function isValidReason(reason) {
  const r = (reason || "").trim();
  return r.length >= 8 && r.length <= 500;
}
