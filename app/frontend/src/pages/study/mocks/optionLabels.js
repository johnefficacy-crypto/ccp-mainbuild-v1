// Single source of truth for the learner-facing label of an answer option.
//
// Backend option rows are inconsistent: a projected PYQ carries a printed
// `source_label` (e.g. "(a)"), authored rows carry an `option_index` that may
// be a letter ("A") OR a raw 0-/1-based number, and some payloads only carry an
// `option_label`. A learner must NEVER see a bare `0`, `1`, `2`, `3` — those are
// storage indices, not labels. This helper resolves one stable display label.
//
// Precedence:
//   1. `source_label` (official printed label) — used as-is (trimmed).
//   2. `option_index` when it is an A/B/C… letter — upper-cased.
//   3. `option_label` when present and not purely numeric.
//   4. positional fallback by visible order → A, B, C, D, E, F…

function positionalLabel(index) {
  const i = Number.isInteger(index) && index >= 0 ? index : 0;
  return String.fromCharCode(65 + (i % 26));
}

export function resolveOptionLabel(option, index = 0) {
  if (!option) return positionalLabel(index);

  const src = option.source_label;
  if (src != null && String(src).trim() !== "") return String(src).trim();

  const oi = option.option_index;
  if (typeof oi === "string" && /^[A-Za-z]$/.test(oi.trim())) return oi.trim().toUpperCase();

  const ol = option.option_label;
  if (ol != null && String(ol).trim() !== "" && !/^\d+$/.test(String(ol).trim())) {
    return String(ol).trim();
  }

  return positionalLabel(index);
}
