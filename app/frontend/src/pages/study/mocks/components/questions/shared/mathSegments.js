/**
 * Math-delimiter detection for question/explanation text (REG-CORPUS-02).
 *
 * Pure and dependency-free so it can sit in the eager chunk: `hasMath` decides
 * whether the KaTeX chunk is fetched at all, and `splitMath` feeds the renderer.
 *
 * The corpus uses `$` as MONEY ("₹80/$", "$40 in the US", "US$450 bn"), so the
 * rules are deliberately strict and anything ambiguous stays literal text:
 *
 *   - `\$` is always a literal dollar (left in the text for markdown to unescape).
 *   - `$$…$$` is display math (non-empty, explicit on both sides).
 *   - An inline opener `$` must NOT be preceded by a letter, digit or `\`, and
 *     must be followed by a char that is neither whitespace nor closing
 *     punctuation (`.,;:!?)]}`), so "₹80/$." and "per $;" never open math.
 *   - An inline closer `$` must be preceded by non-whitespace and NOT followed by
 *     a letter or digit (so "$40 … US$50" never closes).
 *   - The inline body may not span a blank line, may not contain `₹`, and may
 *     not read as prose (three consecutive plain words outside `\text{…}`), so a
 *     money sentence that happens to hit a valid opener/closer pair still stays
 *     literal. A rejected opener is treated as a plain `$` and scanning resumes.
 */

const WORDY = /\\[a-zA-Z]+\s*\{[^{}]*\}/g; // \text{…}, \mathrm{…}, … stripped before the prose check
const PROSE = /[A-Za-z]{2,}\s+[A-Za-z]{2,}\s+[A-Za-z]{2,}/;
const OPENER_BLOCKED_NEXT = /[\s.,;:!?)\]}]/;

function isEscaped(text, i) {
  let n = 0;
  for (let j = i - 1; j >= 0 && text[j] === "\\"; j -= 1) n += 1;
  return n % 2 === 1;
}

function isAlnum(ch) {
  return !!ch && /[\p{L}\p{N}]/u.test(ch);
}

function acceptableInline(body) {
  if (!body || body.includes("\n\n") || body.includes("₹")) return false;
  if (PROSE.test(body.replace(WORDY, " "))) return false;
  return true;
}

function findDisplayClose(text, from) {
  for (let j = from; j < text.length - 1; j += 1) {
    if (text[j] === "$" && text[j + 1] === "$" && !isEscaped(text, j)) return j;
  }
  return -1;
}

function findInlineClose(text, from) {
  for (let j = from; j < text.length; j += 1) {
    if (text[j] !== "$" || isEscaped(text, j)) continue;
    if (text[j + 1] === "$") return -1; // a `$$` inside inline math: not ours
    const prev = text[j - 1];
    const next = text[j + 1];
    if (prev && /\s/.test(prev)) continue;
    if (isAlnum(next)) continue;
    return j;
  }
  return -1;
}

/**
 * Split text into `{ type: "text", value }` and
 * `{ type: "math", value, display }` segments. Concatenating the source of the
 * segments (math re-wrapped in its delimiters) reproduces the input.
 */
export function splitMath(input) {
  const text = typeof input === "string" ? input : "";
  const out = [];
  let buf = "";
  let i = 0;
  const flush = () => {
    if (buf) out.push({ type: "text", value: buf });
    buf = "";
  };

  while (i < text.length) {
    const ch = text[i];
    if (ch !== "$" || isEscaped(text, i)) {
      buf += ch;
      i += 1;
      continue;
    }

    if (text[i + 1] === "$") {
      const close = findDisplayClose(text, i + 2);
      const body = close === -1 ? "" : text.slice(i + 2, close);
      if (body.trim()) {
        flush();
        out.push({ type: "math", value: body.trim(), display: true });
        i = close + 2;
        continue;
      }
      buf += "$$";
      i += 2;
      continue;
    }

    const prev = text[i - 1];
    const next = text[i + 1];
    const canOpen = !(prev && (isAlnum(prev) || prev === "\\")) && next !== undefined && !OPENER_BLOCKED_NEXT.test(next);
    if (canOpen) {
      const close = findInlineClose(text, i + 1);
      const body = close === -1 ? "" : text.slice(i + 1, close);
      if (close !== -1 && acceptableInline(body)) {
        flush();
        out.push({ type: "math", value: body, display: false });
        i = close + 1;
        continue;
      }
    }
    buf += ch;
    i += 1;
  }
  flush();
  return out;
}

export function hasMath(text) {
  return splitMath(text).some((s) => s.type === "math");
}
