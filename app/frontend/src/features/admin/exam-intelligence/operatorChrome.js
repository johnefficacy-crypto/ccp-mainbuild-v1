/**
 * operatorChrome.js
 *
 * Operator-safe display helpers for Exam Intelligence admin surfaces.
 * These utilities ensure raw UUIDs and internal tokens never leak into
 * the operator UI where they have no actionable meaning.
 *
 * Rule: If a value looks like a UUID (8-4-4-4-12 hex groups), humanize it.
 * Otherwise return the original value so meaningful slugs / codes pass through.
 */

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * humanizeToken(token)
 *
 * Returns a short operator-readable label for any identifier.
 *
 * - UUID → "#" + first 8 hex chars (e.g. "#a4cad004")
 * - Any other string → returned as-is (slugs, codes, etc. are already human)
 * - null/undefined → "—"
 */
export function humanizeToken(token) {
  if (token == null) return "—";
  const s = String(token);
  if (UUID_RE.test(s)) {
    return `#${s.slice(0, 8)}`;
  }
  return s;
}

/**
 * isRawUUID(value)
 *
 * Returns true if the value is a raw UUID string.
 * Useful as a guard before deciding whether to display a value directly.
 */
export function isRawUUID(value) {
  if (value == null) return false;
  return UUID_RE.test(String(value));
}

/**
 * safePhaseLabel(phase)
 *
 * Returns the best human-readable label for a phase object,
 * never falling back to a raw UUID.
 */
export function safePhaseLabel(phase) {
  if (!phase) return "this phase";
  return phase.phase_name || phase.name || "this phase";
}
