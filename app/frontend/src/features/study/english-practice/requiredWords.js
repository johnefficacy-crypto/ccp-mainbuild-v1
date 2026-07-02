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
 * Word-count tokeniser — parity-critical mirror of the backend.
 *
 * MUST stay byte-for-byte behaviourally identical to
 * `app/backend/app/study_os/writing_practice/deterministic.py`:
 *   _WORD_RE = re.compile(r"[^\W_]+(?:['\-][^\W_]+)*", re.UNICODE)
 *   tokenize_words(text) -> _WORD_RE.findall(NFC(text))
 *   word_count(text)     -> len(tokenize_words(text))
 *
 * A token is a run of Unicode letters/digits (NOT underscore), with internal
 * single straight-apostrophe `'` or hyphen `-` joining letter/digit runs.
 *
 * Two divergence traps that this function deliberately avoids:
 *   1. JS `\w`/`\W` are ASCII-only even with the `u` flag, so we use Unicode
 *      property escapes `\p{L}\p{N}` — NOT `[^\W_]`.
 *   2. The inner separator class is ONLY straight apostrophe `'` and hyphen `-`.
 *      The curly apostrophe `’` (U+2019) is NOT a joiner here (unlike `tokenize`
 *      above, which is for chip matching only). Including it would diverge from
 *      the backend for curly-apostrophe input.
 *
 * WORD_TOKENIZER_VERSION mirrors the backend DETERMINISTIC_EVALUATOR_VERSION;
 * bump both together when the counting rule changes.
 */
export const WORD_TOKENIZER_VERSION = "det-v1";

const _WORD_RE = /[\p{L}\p{N}]+(?:['-][\p{L}\p{N}]+)*/gu;

/**
 * Tokenise `text` into word tokens using the backend-parity rule (see above).
 * Casing is preserved (word counting is case-insensitive by construction).
 * @param {string} text
 * @returns {string[]}
 */
export function tokenizeWords(text) {
  const normalised = String(text == null ? "" : text).normalize("NFC");
  return normalised.match(_WORD_RE) || [];
}

/**
 * Count words the same way the backend does. This is the authoritative
 * client-side count for min/max display parity (§16 gate #3).
 * @param {string} text
 * @returns {number}
 */
export function wordCount(text) {
  return tokenizeWords(text).length;
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
