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
 * - activation/deactivation shipped in SP2 (`/writing-prompts/{id}/activate` and
 *   `/deactivate`) under the SEPARATE content_studio.activate authority; the RPC
 *   (migration 226) is the sole eligibility authority, returning a structured
 *   `{eligible, blockers}` verdict at HTTP 200. Neither author nor review may
 *   flip is_active — these mutations are gated on content_studio.activate and
 *   carry the client's `expected_updated_at` (CAS) unchanged + a reason, exactly
 *   like PATCH/review. The UI NEVER computes eligibility: on `{eligible:false,
 *   blockers}` it simply renders the blocker codes the RPC returned.
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

  // Activation lifecycle (is_active) — content_studio.activate authority (EWP-SP2).
  // CAS token (expected_updated_at) is passed through UNCHANGED (no pre-write
  // refetch), mirroring PATCH/review. activate resolves the RPC verdict:
  // {eligible:false, blockers} arrives at HTTP 200 (a valid answer, not an error).
  activateWritingPrompt: (id, { expected_updated_at, reason }) =>
    api.post(`${BASE}/writing-prompts/${id}/activate`, { expected_updated_at, reason }),
  deactivateWritingPrompt: (id, { expected_updated_at, reason }) =>
    api.post(`${BASE}/writing-prompts/${id}/deactivate`, { expected_updated_at, reason }),

  // Exam Assignments (writing_prompt_targets) — J2 propose/review/remove split
  listTargets: (promptId) => api.get(`${BASE}/writing-prompts/${promptId}/targets`),
  proposeTarget: (promptId, body) => api.post(`${BASE}/writing-prompts/${promptId}/targets`, body),
  reviewTarget: (targetId, body) => api.post(`${BASE}/writing-prompt-targets/${targetId}/review`, body),
  removeTarget: (targetId, body) => api.post(`${BASE}/writing-prompt-targets/${targetId}/remove`, body),

  // Quant heuristic authority (GQR-Q7). Read = content_studio reads; review =
  // content_studio.review. There is no create/edit/assign path — migration 243
  // ships only the review RPC (CAS + reason hardened in 245). Every review
  // decision carries an 8–500 char `reason` and is dual-CAS-guarded on BOTH the
  // `expected_status` and the content `expected_updated_at` the client last read
  // (so a reviewer can never verify a revision they did not see); a 409 means the
  // heuristic changed under review — refetch and re-read before deciding.
  listHeuristics: (params) => api.get(`${BASE}/quant-heuristics${qs(params)}`),
  getHeuristic: (id) => api.get(`${BASE}/quant-heuristics/${id}`),
  reviewHeuristic: (id, { status, expected_status, expected_updated_at, reason, reviewer_notes }) =>
    api.post(`${BASE}/quant-heuristics/${id}/review`, {
      status,
      expected_status,
      expected_updated_at,
      reason,
      ...(reviewer_notes ? { reviewer_notes } : {}),
    }),

  // Reasoning strategy authority (GQR-S3). Read = content_studio reads; review =
  // content_studio.review. There is no create/edit/assign path — migration 262
  // ships only the review RPC. Every review decision carries an 8–500 char
  // `reason` and is dual-CAS-guarded on BOTH the `expected_status` and the content
  // `expected_updated_at` the client last read (so a reviewer can never verify a
  // revision they did not see); a 409 means the strategy changed under review —
  // refetch and re-read before deciding. Mirrors the quant-heuristic surface.
  listStrategies: (params) => api.get(`${BASE}/reasoning-strategies${qs(params)}`),
  getStrategy: (id) => api.get(`${BASE}/reasoning-strategies/${id}`),
  reviewStrategy: (id, { status, expected_status, expected_updated_at, reason, reviewer_notes }) =>
    api.post(`${BASE}/reasoning-strategies/${id}/review`, {
      status,
      expected_status,
      expected_updated_at,
      reason,
      ...(reviewer_notes ? { reviewer_notes } : {}),
    }),

  // Current-affairs question candidates (GQR-G4). The reviewer approves/rejects/
  // sends-back a shadow-generated candidate; PROMOTION into the objective bank is a
  // separate, higher-trust (`mock_questions:publish`) action. Both CAS-guard on the
  // status the reviewer last saw (`expected_status`) server-side — a 409 means the
  // candidate changed under review; refetch before deciding.
  listCaCandidates: (params) => api.get(`${BASE}/ca-question-candidates${qs(params)}`),
  getCaCandidate: (id) => api.get(`${BASE}/ca-question-candidates/${id}`),
  reviewCaCandidate: (id, { status, expected_status, reviewer_notes }) =>
    api.post(`${BASE}/ca-question-candidates/${id}/review`, {
      status,
      expected_status,
      ...(reviewer_notes ? { reviewer_notes } : {}),
    }),
  promoteCaCandidate: (id, { expected_status = "approved" } = {}) =>
    api.post(`${BASE}/ca-question-candidates/${id}/promote`, { expected_status }),
};

// Legal candidate review transitions (mirror of the backend `_CA_REVIEW_TRANSITIONS`).
// Promotion (approved → promoted) is NOT here — it is the separate publish action.
export const CA_REVIEW_TRANSITIONS = {
  review_ready: ["approved", "rejected"],
  approved: ["rejected", "review_ready"],
  rejected: ["review_ready"],
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

// Human-readable text for the activation blocker codes the RPC (migration 226)
// returns in `{eligible:false, blockers}`. The UI NEVER computes these — it only
// translates the codes the server sent. An unrecognised code falls back to the
// raw code so a newly-added server blocker is surfaced, never silently dropped.
export const ACTIVATION_BLOCKER_LABELS = {
  prompt_not_verified: "Prompt is not verified — only a verified prompt can be activated.",
  already_active: "Prompt is already active.",
  no_active_applicability_target:
    "No active exam applicability target — assign the prompt to an exam/family/phase (or global) and have it reviewed active first.",
  exercise_type_not_runtime_ready:
    "This exercise type is not runtime-ready yet (server-owned readiness allowlist).",
  semantic_evaluator_not_live:
    "The semantic evaluator gate is not live for this source-dependent exercise type.",
  rubric_missing: "A rubric is required for this exercise type but none is attached.",
  paragraph_gate_closed: "The paragraph-writing release gate is closed.",
  invalid_scope: "The prompt's subject/topic scope no longer validates.",
  reason_required: "A reason (8–500 characters) is required.",
};

export function describeActivationBlocker(code) {
  return ACTIVATION_BLOCKER_LABELS[code] || code;
}

// Quant heuristic authority (migration 243). heuristic_type facet + the review
// transition matrix, which DIFFERS from writing prompts: needs_correction routes
// back to pending (never straight to verified), a verified heuristic can only be
// reopened for correction, and rejected can be reopened to pending for rework.
export const HEURISTIC_TYPES = ["shortcut", "standard_method", "trap", "estimation"];

export const HEURISTIC_REVIEW_TRANSITIONS = {
  pending: ["verified", "rejected", "needs_correction"],
  needs_correction: ["pending", "rejected"],
  verified: ["needs_correction"],
  rejected: ["pending"],
};

// Reasoning strategy authority (migration 262, GQR-S3). strategy_type facet + the
// review transition matrix, which MATCHES the quant-heuristic one: needs_correction
// routes back to pending (never straight to verified), a verified strategy can only
// be reopened for correction, and rejected can be reopened to pending for rework.
export const REASONING_STRATEGY_TYPES = [
  "approach", "pattern", "elimination", "diagram_method", "set_method", "trap",
];

export const REASONING_REVIEW_TRANSITIONS = {
  pending: ["verified", "rejected", "needs_correction"],
  needs_correction: ["pending", "rejected"],
  verified: ["needs_correction"],
  rejected: ["pending"],
};
