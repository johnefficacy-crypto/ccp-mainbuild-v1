/**
 * Prompt Bank API adapter — isolates backend contracts for English Writing Practice prompts.
 *
 * Expected endpoints (may not be implemented yet):
 * - GET /api/admin/exam-intelligence-cms/writing-prompts
 * - POST /api/admin/exam-intelligence-cms/writing-prompts
 * - PATCH /api/admin/exam-intelligence-cms/writing-prompts/:prompt_id
 * - PATCH /api/admin/exam-intelligence-cms/writing-prompts/:prompt_id/review
 * - PATCH /api/admin/exam-intelligence-cms/writing-prompts/:prompt_id/activation
 * - POST /api/admin/exam-intelligence-cms/writing-prompts/bulk
 */
import { api } from "../../../../lib/api";

const BASE_URL = "/api/admin/exam-intelligence-cms/writing-prompts";

export const promptBankApi = {
  /**
   * List prompts with optional filters and readiness summary.
   * Returns { items: [], total_count: 0, limit: 25, offset: 0, has_next: false, summary: {...} }
   */
  async listPrompts(filters = {}) {
    const qs = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v != null && v !== "" && v !== false) qs.set(k, v);
    });
    const queryStr = qs.toString();
    const url = queryStr ? `${BASE_URL}?${queryStr}` : BASE_URL;
    return api.get(url);
  },

  /**
   * Get a single prompt by ID.
   */
  async getPrompt(promptId) {
    return api.get(`${BASE_URL}/${promptId}`);
  },

  /**
   * Create a new prompt. Always starts as reviewer_status='pending', is_active=false.
   */
  async createPrompt(payload) {
    return api.post(BASE_URL, payload);
  },

  /**
   * Update an existing prompt.
   */
  async updatePrompt(promptId, payload) {
    return api.patch(`${BASE_URL}/${promptId}`, payload);
  },

  /**
   * Set prompt review status (verify, reject, needs_correction).
   * Requires exam_intelligence.review permission.
   */
  async reviewPrompt(promptId, payload) {
    // payload: { reviewer_status, reviewer_notes }
    return api.patch(`${BASE_URL}/${promptId}/review`, payload);
  },

  /**
   * Toggle prompt activation (is_active).
   * Can only activate if reviewer_status='verified'.
   */
  async setActivation(promptId, isActive) {
    return api.patch(`${BASE_URL}/${promptId}/activation`, { is_active: isActive });
  },

  /**
   * Bulk import from parsed CSV/JSON.
   * payload: { rows: [...], override_duplicates: boolean }
   * Returns: { created: number, failed: number, errors: [...] }
   */
  async bulkImportPrompts(payload) {
    return api.post(`${BASE_URL}/bulk`, payload);
  },

  /**
   * Clone an existing prompt.
   */
  async clonePrompt(sourcePromptId, updates = {}) {
    return api.post(`${BASE_URL}/${sourcePromptId}/clone`, updates);
  },
};
