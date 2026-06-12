/**
 * Convert a string to a URL-safe kebab-case slug.
 * Matches the backend's app.common.strings.slugify behaviour:
 *   - lowercase
 *   - non-alphanumeric runs → single hyphen
 *   - leading/trailing hyphens stripped
 *
 * @param {string} s
 * @returns {string}
 */
export function slugify(s) {
  return String(s || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/**
 * Build a cycle-bound phase slug.
 * Always suffixes the base slug with the year (preferred) or cycle_name (fallback)
 * so that a cycle-bound phase is never bare.
 *
 * @param {string} baseSlug  e.g. "prelims"
 * @param {string|number} year  e.g. 2025
 * @param {string} cycleName  fallback if year is blank
 * @returns {string}  e.g. "prelims-2025"
 */
export function cycleBoundSlug(baseSlug, year, cycleName) {
  const suffix = String(year || "").trim() || String(cycleName || "").trim();
  return slugify(baseSlug + "-" + suffix);
}
