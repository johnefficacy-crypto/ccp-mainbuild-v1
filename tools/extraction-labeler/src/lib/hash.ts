/**
 * Question text normalization per corpus contract:
 *   lowercase → remove leading Q./N. numbering → collapse whitespace →
 *   strip punctuation except internal "?" and "."
 */
export function normalizeQuestionText(text: string): string {
  let t = text;
  // Remove leading numbering: "Q.", "N.", "Q1.", "1." etc.
  t = t.replace(/^\s*(?:[QqNn]\d*\.?\s*|\d+\.\s*)/u, '');
  t = t.toLowerCase();
  t = t.replace(/\s+/g, ' ').trim();
  // Strip all punctuation except ? and . (Unicode-aware)
  t = t.replace(/[^\p{L}\p{N}\s?.]/gu, '');
  t = t.replace(/\s+/g, ' ').trim();
  return t;
}

export async function sha256Hex(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const buf = await globalThis.crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export async function hashQuestionText(text: string): Promise<string> {
  return sha256Hex(normalizeQuestionText(text));
}
