/**
 * UTF-16 span verification for language-issue highlights (architecture §4.5b).
 *
 * The backend emits issue spans as UTF-16 code-unit offsets and a `quoted_text`
 * for verification. JavaScript strings are already UTF-16, so `String.prototype
 * .slice(start, end)` operates on the same code units — but a span can be stale
 * (computed against a different version of the answer). Before rendering a
 * highlight the frontend MUST confirm the slice equals `quoted_text`; a mismatch
 * means the span no longer aligns and must not be rendered as a highlight.
 */

/**
 * @param {string} sourceText   full answer text
 * @param {number} spanStart    inclusive UTF-16 offset
 * @param {number} spanEnd      exclusive UTF-16 offset
 * @param {string} quotedText   expected substring
 * @returns {{ valid: boolean, before: string, highlighted: string, after: string }}
 */
export function verifyAndSliceSpan(sourceText, spanStart, spanEnd, quotedText) {
  const text = typeof sourceText === "string" ? sourceText : "";
  const start = Number.isInteger(spanStart) ? spanStart : -1;
  const end = Number.isInteger(spanEnd) ? spanEnd : -1;

  // Bounds + ordering must hold before we trust the offsets.
  if (start < 0 || end < start || end > text.length) {
    return { valid: false, before: text, highlighted: "", after: "" };
  }
  const highlighted = text.slice(start, end);
  return {
    valid: highlighted === quotedText,
    before: text.slice(0, start),
    highlighted,
    after: text.slice(end),
  };
}

export default verifyAndSliceSpan;
