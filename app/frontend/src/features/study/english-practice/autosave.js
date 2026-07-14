/**
 * Draft autosave for the Sentence Builder (EWP-3 client safeguard).
 *
 * Drafts are persisted to `sessionStorage` keyed by `sessionId + unitNumber` so
 * an accidental reload never loses in-progress work (release gate §16.1 —
 * "no lost-answer incidents"). Storage is best-effort: private-mode / quota /
 * disabled-storage failures degrade to no-op rather than breaking compose.
 */
const PREFIX = "ewp:draft:";

/**
 * @param {string} sessionId
 * @param {number|string} unitNumber
 * @returns {string}
 */
export function draftKey(sessionId, unitNumber) {
  return `${PREFIX}${sessionId}:${unitNumber}`;
}

/**
 * @param {string} sessionId
 * @param {number|string} unitNumber
 * @param {string} text
 */
export function saveDraft(sessionId, unitNumber, text) {
  try {
    window.sessionStorage.setItem(draftKey(sessionId, unitNumber), text);
  } catch (e) {
    /* storage unavailable — best-effort */
  }
}

/**
 * @param {string} sessionId
 * @param {number|string} unitNumber
 * @returns {string|null}
 */
export function loadDraft(sessionId, unitNumber) {
  try {
    return window.sessionStorage.getItem(draftKey(sessionId, unitNumber));
  } catch (e) {
    return null;
  }
}

/**
 * @param {string} sessionId
 * @param {number|string} unitNumber
 */
export function clearDraft(sessionId, unitNumber) {
  try {
    window.sessionStorage.removeItem(draftKey(sessionId, unitNumber));
  } catch (e) {
    /* storage unavailable — best-effort */
  }
}

/* -------------------------------------------------------------------------- *
 * Paragraph outline scratchpad (EWP-6 scaffolding).
 *
 * The Paragraph Builder plans a paragraph as an ordered list of outline points
 * before the body is written. That structure is the `outline_json` shape from
 * the EWP-6 design. Like the draft, it is persisted to `sessionStorage` (keyed
 * separately) so a reload never loses the plan. It is a CLIENT scratchpad only
 * — it is NOT submitted to the backend in this scaffold (a persisted
 * `outline_json` column is a future backend slice, gated with the rest of
 * EWP-6). Storage is best-effort and degrades to no-op.
 * -------------------------------------------------------------------------- */
const OUTLINE_PREFIX = "ewp:outline:";

/**
 * @param {string} sessionId
 * @param {number|string} unitNumber
 * @returns {string}
 */
export function outlineKey(sessionId, unitNumber) {
  return `${OUTLINE_PREFIX}${sessionId}:${unitNumber}`;
}

/**
 * @param {string} sessionId
 * @param {number|string} unitNumber
 * @param {Array} outline - Array of outline points ({ id, text }).
 */
export function saveOutline(sessionId, unitNumber, outline) {
  try {
    window.sessionStorage.setItem(outlineKey(sessionId, unitNumber), JSON.stringify(outline));
  } catch (e) {
    /* storage unavailable / not serialisable — best-effort */
  }
}

/**
 * @param {string} sessionId
 * @param {number|string} unitNumber
 * @returns {Array|null} Parsed outline points, or null when absent/corrupt.
 */
export function loadOutline(sessionId, unitNumber) {
  try {
    const raw = window.sessionStorage.getItem(outlineKey(sessionId, unitNumber));
    if (raw == null) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : null;
  } catch (e) {
    return null;
  }
}

/**
 * @param {string} sessionId
 * @param {number|string} unitNumber
 */
export function clearOutline(sessionId, unitNumber) {
  try {
    window.sessionStorage.removeItem(outlineKey(sessionId, unitNumber));
  } catch (e) {
    /* storage unavailable — best-effort */
  }
}
