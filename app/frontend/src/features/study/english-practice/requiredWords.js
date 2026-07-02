/**
 * Required-word coverage helpers for the Sentence Builder (EWP-3).
 *
 * The authoritative coverage verdict is a version-set-pinned server check
 * (§4.7a); these helpers drive the *live* compose-time affordance only — the
 * word chips and the `words_used: N/total` counter. Matching is case-insensitive
 * on whole Unicode word tokens, so "Ran" satisfies a required "ran" but "ranged"
 * does not.
 *
 * @param {string} word
 * @returns {string}
 */
export function normalizeToken(word) {
  return String(word == null ? "" : word).trim().toLowerCase();
}

/**
 * Tokenise text into lowercased Unicode word tokens. Internal apostrophes and
 * hyphens are kept as part of a token so compound/possessive required words like
 * `well-known` or `don't` match as whole tokens (edge punctuation is not
 * captured — a leading/trailing dash or a standalone " - " is skipped).
 * @param {string} text
 * @returns {string[]}
 */
export function tokenize(text) {
  const matches = String(text == null ? "" : text)
    .toLowerCase()
    .match(/[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu);
  return matches || [];
}

/**
 * Which of `requiredWords` appear as whole tokens in `text`.
 * @param {string} text
 * @param {string[]} requiredWords
 * @returns {string[]} the required words that are used (original casing preserved)
 */
export function usedRequiredWords(text, requiredWords) {
  const present = new Set(tokenize(text));
  return (requiredWords || []).filter((w) => present.has(normalizeToken(w)));
}
