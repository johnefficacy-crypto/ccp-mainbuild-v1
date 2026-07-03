/**
 * Minimal RFC 4180 CSV parser — handles quoted fields, embedded commas,
 * escaped quotes ("") and CRLF/LF line endings. `split(",")` corrupts quoted
 * prompt text, which is why this exists.
 *
 * Returns an array of row objects keyed by the header row.
 */
export function parseCsv(text) {
  const rows = [];
  let field = "";
  let row = [];
  let inQuotes = false;
  const pushField = () => { row.push(field); field = ""; };
  const pushRow = () => { rows.push(row); row = []; };

  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 1; } else { inQuotes = false; }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ",") {
      pushField();
    } else if (c === "\n") {
      pushField(); pushRow();
    } else if (c === "\r") {
      // swallow; \n (if any) closes the row
      if (text[i + 1] !== "\n") { pushField(); pushRow(); }
    } else {
      field += c;
    }
  }
  if (field !== "" || row.length > 0) { pushField(); pushRow(); }

  const nonEmpty = rows.filter((r) => r.some((cell) => cell.trim() !== ""));
  if (nonEmpty.length < 2) return [];
  const headers = nonEmpty[0].map((h) => h.trim());
  return nonEmpty.slice(1).map((cells) => {
    const obj = {};
    headers.forEach((h, idx) => { obj[h] = (cells[idx] ?? "").trim(); });
    return obj;
  });
}
