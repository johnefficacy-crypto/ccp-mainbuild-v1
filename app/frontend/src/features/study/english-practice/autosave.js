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
