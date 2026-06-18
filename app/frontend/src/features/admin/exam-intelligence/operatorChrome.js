/**
 * Operator-chrome presentation helpers (Wave 4.6 CL-1).
 *
 * Keep machine identifiers out of operator-facing text: humanize raw
 * snake_case/dotted tokens into safe generic labels, and render timestamps as
 * friendly relative dates (never raw ISO-8601). Presentation only — no data,
 * endpoint, or status-logic change. Mono font stays reserved for IDs/codes.
 */

/** Turn a raw token (snake_case / dotted event key) into a safe human label.
 *  Never returns raw snake_case. Empty/nullish → "". */
export function humanizeToken(token) {
  if (token == null) return "";
  const s = String(token).replace(/[._]+/g, " ").trim();
  if (!s) return "";
  return s.charAt(0).toUpperCase() + s.slice(1);
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
