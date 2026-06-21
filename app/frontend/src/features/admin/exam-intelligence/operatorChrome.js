/**
 * Operator-chrome presentation helpers (Wave 4.6 CL-1).
 *
 * Keep machine identifiers out of operator-facing text: humanize raw
 * snake_case/dotted tokens into safe generic labels, and render timestamps as
 * friendly relative dates (never raw ISO-8601). Presentation only — no data,
 * endpoint, or status-logic change. Mono font stays reserved for IDs/codes.
 */

const UUID_TOKEN_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Turn a raw token (snake_case / dotted event key, or UUID) into a safe human
 *  label. UUID-shaped strings are truncated to first 8 chars + "…" so they are
 *  recognisable to operators without exposing the full identifier. Never returns
 *  raw snake_case or a full UUID. Empty/nullish → "". */
export function humanizeToken(token) {
  if (token == null) return "";
  const s = String(token).trim();
  if (!s) return "";
  // Truncate UUID-shaped values — never render a full UUID verbatim.
  if (UUID_TOKEN_RE.test(s)) return s.slice(0, 8) + "…";
  const readable = s.replace(/[._]+/g, " ").trim();
  if (!readable) return "";
  return readable.charAt(0).toUpperCase() + readable.slice(1);
}

/** Friendly relative date from an ISO timestamp; older dates fall back to a
 *  short calendar date (no time, no ISO leak). Invalid/empty → "—". */
export function relativeDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const sec = Math.round((Date.now() - d.getTime()) / 1000);
  if (sec < 0) return "just now";
  if (sec < 60) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 7) return `${day}d ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

/** Operator-safe actor label. Emails and human names pass through; a UUID-shaped
 *  actor id becomes "Administrator"; empty/"system" becomes "System". Never
 *  renders a raw UUID. */
export function formatOperatorActor(value) {
  const v = value == null ? "" : String(value).trim();
  if (!v || v.toLowerCase() === "system") return "System";
  if (UUID_TOKEN_RE.test(v)) return "Administrator";
  return v;
}

// Internal audit note markers that must never reach operators verbatim.
const INTERNAL_NOTE_LABELS = {
  admin_exam_intel_cms: "",
};

/** Audit-note label. Known internal markers are suppressed (or mapped to a
 *  friendly label); empty → "". Arbitrary human-authored notes pass through
 *  unchanged — notes are NOT blindly humanized. */
export function formatAuditNote(value) {
  if (value == null) return "";
  const v = String(value);
  if (Object.prototype.hasOwnProperty.call(INTERNAL_NOTE_LABELS, v.trim())) {
    return INTERNAL_NOTE_LABELS[v.trim()];
  }
  return v;
}
