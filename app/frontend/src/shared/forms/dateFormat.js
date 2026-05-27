// Date-only string helpers. Everything is treated as a literal
// `YYYY-MM-DD` <-> `dd-mm-yyyy` string transform — no `Date` parsing, so
// there is never a timezone shift. Storage stays ISO date-only.

export function formatDDMMYYYY(iso) {
  if (!iso) return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso));
  if (!m) return "";
  return `${m[3]}-${m[2]}-${m[1]}`;
}

export function parseDDMMYYYY(text) {
  if (!text) return null;
  const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(String(text).trim());
  if (!m) return null;
  const dd = Number(m[1]);
  const mm = Number(m[2]);
  const yyyy = Number(m[3]);
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return null;
  // Reject impossible calendar dates (e.g. 31-02). Date Y/M/D getters are
  // timezone-independent, so this validity check never shifts a day.
  const d = new Date(yyyy, mm - 1, dd);
  if (d.getFullYear() !== yyyy || d.getMonth() !== mm - 1 || d.getDate() !== dd) return null;
  return `${m[3]}-${m[2]}-${m[1]}`;
}

// ISO date-only string -> local Date (midnight) for the picker, built from
// components so the displayed day matches the stored day in any timezone.
export function isoToLocalDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
  if (!m) return undefined;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

export function localDateToIso(d) {
  if (!d) return null;
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const da = String(d.getDate()).padStart(2, "0");
  return `${y}-${mo}-${da}`;
}
