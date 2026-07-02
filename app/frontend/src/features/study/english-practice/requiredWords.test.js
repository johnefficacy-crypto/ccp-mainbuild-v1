import { normalizeToken, tokenize, usedRequiredWords } from "./requiredWords";

describe("requiredWords tokenisation", () => {
  test("tokenize splits on non-word chars and lowercases", () => {
    expect(tokenize("The quick, brown fox!")).toEqual(["the", "quick", "brown", "fox"]);
  });

  test("tokenize handles empty/null", () => {
    expect(tokenize("")).toEqual([]);
    expect(tokenize(null)).toEqual([]);
  });

  test("normalizeToken trims and lowercases", () => {
    expect(normalizeToken("  Diligent ")).toBe("diligent");
    expect(normalizeToken(null)).toBe("");
  });

  test("matches required words case-insensitively as whole tokens", () => {
    expect(usedRequiredWords("She Ran home.", ["ran", "swiftly"])).toEqual(["ran"]);
  });

  test("does not match a required word as a substring of a larger token", () => {
    // "ran" must not be satisfied by "ranged".
    expect(usedRequiredWords("They ranged widely.", ["ran"])).toEqual([]);
  });

  test("returns each used required word once, preserving original casing", () => {
    expect(usedRequiredWords("Diligent, diligent work.", ["Diligent"])).toEqual(["Diligent"]);
  });

  test("matches hyphenated required words as whole tokens", () => {
    expect(usedRequiredWords("A well-known fact.", ["well-known"])).toEqual(["well-known"]);
    // The compound must not be satisfied by only one half.
    expect(usedRequiredWords("A known fact.", ["well-known"])).toEqual([]);
  });

  test("matches apostrophe words", () => {
    expect(usedRequiredWords("I don't know.", ["don't"])).toEqual(["don't"]);
    expect(tokenize("don't well-known")).toEqual(["don't", "well-known"]);
  });
});
