/**
 * Backend-parity validation for writing-prompt content.
 *
 * ONE shared validator for both the editor and bulk import, so the inline
 * pre-validation the handoff asks for actually mirrors what the merged backend
 * (`app/api/content_studio.py` + migration 215 `_canonicalize_required_words` /
 * `ewp_assert_prompt_content`) will accept — instead of a weaker `/\s/`+
 * `toLowerCase` check that passes inputs the server then 422s.
 *
 * Required-word rule (backend `_canonicalize_required_words`): each entry is
 * NFC-normalised and trimmed, must be EXACTLY ONE deterministic word-token
 * (the §16 word-count tokenizer — letters/digits with internal `'`/`-`, no
 * underscore/punctuation/symbols), and duplicates are rejected case-insensitively
 * on an NFC + lower-case key. We reuse `tokenizeWords` (the parity tokenizer) so
 * `foo!`, `a.b`, `under_score`, `@handle` fail the SAME way here as server-side.
 */
import { tokenizeWords } from "../../../features/study/english-practice/requiredWords";

// NFC + lower-case dedupe key. JS has no str.casefold(); NFC+toLowerCase is the
// closest available and matches the backend for the alphabets in scope.
export function requiredWordKey(word) {
  return String(word == null ? "" : word).normalize("NFC").toLowerCase();
}

/**
 * Validate/canonicalise a list of required words (already split into entries).
 * @param {string[]} entries
 * @returns {{ words?: string[], error?: string }}
 */
export function validateRequiredWords(entries) {
  const seen = new Set();
  const out = [];
  for (const rawEntry of entries) {
    const entry = String(rawEntry == null ? "" : rawEntry).normalize("NFC").trim();
    if (!entry) continue;
    const tokens = tokenizeWords(entry);
    if (tokens.length !== 1 || tokens[0] !== entry) {
      return {
        error: `"${rawEntry}" must be a single word — letters/digits with only internal apostrophe or hyphen (no spaces, punctuation, symbols, or underscore).`,
      };
    }
    const key = requiredWordKey(entry);
    if (seen.has(key)) {
      return { error: `"${rawEntry}" appears more than once (case-insensitive).` };
    }
    seen.add(key);
    out.push(entry);
  }
  return { words: out };
}

/** Split a comma-separated required-words field and validate it. */
export function parseRequiredWordsField(text) {
  return validateRequiredWords(String(text || "").split(","));
}

/**
 * Validate an integer field against the backend Pydantic bounds.
 * @returns {{ value?: number|undefined, error?: string }} value undefined = "not provided"
 */
export function validateInt(raw, label, { min, max } = {}) {
  if (raw === "" || raw === null || raw === undefined) return { value: undefined };
  const n = Number(raw);
  if (!Number.isInteger(n)) return { error: `${label} must be a whole number.` };
  if (min !== undefined && n < min) return { error: `${label} must be ≥ ${min}.` };
  if (max !== undefined && n > max) return { error: `${label} must be ≤ ${max}.` };
  return { value: n };
}

// Rough UUID v-any shape check (mirrors that the backend column is uuid-typed;
// a malformed id is a 422 there, so catch it inline).
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function isUuid(value) {
  return UUID_RE.test(String(value || "").trim());
}
