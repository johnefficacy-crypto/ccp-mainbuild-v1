/**
 * Minimal RFC 4180 CSV parser — handles quoted fields, embedded commas,
 * escaped quotes ("") and CRLF/LF line endings. `split(",")` corrupts quoted
 * prompt text, which is why this exists.
 *
 * Fails LOUD on malformed input instead of silently dropping data:
 *   - an unterminated quote throws,
 *   - a blank or duplicate header throws,
 *   - a row whose column count differs from the header throws.
 * Only UNQUOTED cells are trimmed (a deliberately padded quoted value keeps its
 * spaces); a leading UTF-8 BOM is stripped so the first header is not corrupted.
 *
 * Returns an array of row objects keyed by the header row.
 */
export function parseCsv(input) {
  // Strip a leading UTF-8 BOM.
  const text = input && input.charCodeAt(0) === 0xfeff ? input.slice(1) : (input || "");

  const rows = [];
  let field = "";
  let fieldQuoted = false; // did this field contain a quoted segment?
  let row = [];
  let inQuotes = false;
  const pushField = () => { row.push({ value: field, quoted: fieldQuoted }); field = ""; fieldQuoted = false; };
  const pushRow = () => { rows.push(row); row = []; };

  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 1; } else { inQuotes = false; }
      } else if (c === "\r" && text[i + 1] === "\n") {
        // Normalise CRLF → LF inside a quoted field (drop the stray CR).
        field += "\n"; i += 1;
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
      fieldQuoted = true;
    } else if (c === ",") {
      pushField();
    } else if (c === "\n") {
      pushField(); pushRow();
    } else if (c === "\r") {
      if (text[i + 1] !== "\n") { pushField(); pushRow(); }
    } else {
      field += c;
    }
  }
  if (inQuotes) throw new Error("Malformed CSV: unterminated quoted field.");
  if (field !== "" || row.length > 0) { pushField(); pushRow(); }

  // A row is empty only if every cell is unquoted-and-blank.
  const nonEmpty = rows.filter((r) => r.some((cell) => cell.quoted || cell.value.trim() !== ""));
  if (nonEmpty.length < 2) return [];

  const headers = nonEmpty[0].map((h) => h.value.trim());
  const seen = new Set();
  headers.forEach((h) => {
    if (!h) throw new Error("Malformed CSV: a header column is blank.");
    if (seen.has(h)) throw new Error(`Malformed CSV: duplicate header column "${h}".`);
    seen.add(h);
  });

  return nonEmpty.slice(1).map((cells, idx) => {
    if (cells.length !== headers.length) {
      throw new Error(
        `Malformed CSV: row ${idx + 2} has ${cells.length} columns, expected ${headers.length}.`,
      );
    }
    const obj = {};
    headers.forEach((h, i) => {
      const cell = cells[i];
      obj[h] = cell.quoted ? cell.value : cell.value.trim();
    });
    return obj;
  });
}
