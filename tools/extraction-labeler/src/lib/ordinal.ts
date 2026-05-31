/**
 * Utilities for detecting and stripping leading ordinal numbers from question text.
 */

/**
 * Detects a leading ordinal number (e.g. "1.", "2)", "3:", "4 ") at the start of text.
 * Returns the number if found, null otherwise.
 */
export function detectLeadingOrdinal(text: string): number | null {
  const match = /^\s*(\d+)[.):\s]/.exec(text);
  if (!match) return null;
  return parseInt(match[1], 10);
}

/**
 * Removes a leading ordinal (e.g. "1.", "2)", "3:") and any following whitespace
 * from the start of text.
 */
export function stripLeadingOrdinal(text: string): string {
  return text.replace(/^\s*\d+[.):\s]\s*/, '');
}

/**
 * Collapses runs of spaces/tabs to a single space on each line, trims each
 * line's leading/trailing whitespace, and preserves intentional newlines
 * (e.g. between numbered statement items I./II./1./2.).
 */
export function cleanWhitespace(text: string): string {
  return text
    .split('\n')
    .map((line) => line.replace(/[ \t]+/g, ' ').trim())
    .join('\n')
    .trim();
}
