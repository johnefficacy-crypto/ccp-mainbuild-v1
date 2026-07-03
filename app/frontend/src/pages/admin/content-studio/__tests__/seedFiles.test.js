/**
 * Proves the committed writing-prompt seed files are actually uploadable through
 * the Content Studio Bulk Import UI — by running each row through the SAME parser
 * the UI uses (`normalizeRow`), not a re-implementation. A row-array file that the
 * UI would reject (missing/unknown keys, bad UUID, invalid required words, …)
 * fails here.
 */
import fs from "fs";
import path from "path";

// env.js throws without REACT_APP_BACKEND_URL; normalizeRow needs no transport.
jest.mock("../../../../lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
  getApiErrorMessage: (e) => e?.message || "error",
}));

// eslint-disable-next-line import/first
import { normalizeRow } from "../PromptBulkImport";

const SEED_DIR = path.resolve(__dirname, "../../../../../../supabase/seeds/writing_prompts");
const FILES = [
  ["01_sentence_construction.json", 50],
  ["02_sentence_correction.json", 50],
  ["03_grammar.json", 100],
  ["04_vocabulary.json", 50],
  ["05_paragraph.json", 20],
];

describe("writing-prompt seed files", () => {
  test.each(FILES)("%s is a UI-uploadable row array the parser accepts", (file, count) => {
    const raw = JSON.parse(fs.readFileSync(path.join(SEED_DIR, file), "utf8"));
    expect(Array.isArray(raw)).toBe(true);
    expect(raw.length).toBe(count);

    const seen = new Set();
    raw.forEach((row, i) => {
      const { row: normalized, errors } = normalizeRow(row);
      expect({ file, i, errors }).toEqual({ file, i, errors: [] });
      expect(seen.has(normalized.external_key)).toBe(false);
      seen.add(normalized.external_key);
    });
  });

  test("270 prompts total across the five batches", () => {
    const total = FILES.reduce(
      (n, [file]) => n + JSON.parse(fs.readFileSync(path.join(SEED_DIR, file), "utf8")).length,
      0,
    );
    expect(total).toBe(270);
  });
});
