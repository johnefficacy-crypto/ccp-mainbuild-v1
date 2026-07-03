import { tokenizeWords, wordCount, WORD_TOKENIZER_VERSION } from "./requiredWords";

/**
 * Word-count parity suite (EWP §16 gate #3).
 *
 * Every vector below is asserted by the backend deterministic engine in
 * `app/backend/tests/study_os/test_writing_deterministic.py` against
 * `deterministic.word_count`, OR exercises the exact rule those tests pin
 * (Unicode letters/digits, internal straight `'`/`-` joiners, no underscore).
 * The frontend `wordCount` MUST return the identical integer for each.
 */
describe("wordCount backend parity", () => {
  // [input, expectedCount, note]
  const VECTORS = [
    ["", 0, "empty string"],
    ["   ", 0, "whitespace only"],
    ["\t\n  \n", 0, "mixed whitespace only"],
    ["hello,world", 2, "punctuation separates (client split would give 1)"],
    ["it's fine", 2, "straight apostrophe joins, space separates"],
    ["don't stop", 2, "backend: don't stop == 2"],
    ["well-known", 1, "hyphen joins into one token"],
    ["state-of-the-art", 1, "backend: state-of-the-art == 1"],
    ["  Hello,   world!  ", 2, "backend: '  Hello,   world!  ' == 2"],
    ["Hello world.", 2, "backend: to_dict server_word_count == 2"],
    ["one two three", 3, "backend below_min vector"],
    ["one two three four five six", 6, "backend above_max vector"],
    ["Despite the rain, we left early.", 6, "backend clean-pass == 6"],
    ["The scheme is useful.", 4, "trailing period does not add a word"],
    ["_", 0, "lone underscore is NOT a word (backend excludes _)"],
    ["foo_bar", 2, "underscore separates (\\p{L}\\p{N}, not \\w)"],
    ["café touché", 2, "Unicode letters counted"],
    ["naïve", 1, "Unicode letter within a single token"],
    ["Über-cool", 1, "Unicode letters + hyphen join to one"],
    ["Москва Питер", 2, "Cyrillic letters counted"],
    ["東京 大阪", 2, "CJK letters counted"],
    ["abc123 42", 2, "digits are word chars"],
    ["-leading trailing-", 2, "edge hyphens are not internal joiners"],
    ["a'", 1, "trailing apostrophe not an internal joiner -> just 'a'"],
    ["can’t stop", 3, "curly apostrophe is NOT a joiner: cant't -> can, t, stop"],
  ];

  test.each(VECTORS)("wordCount(%j) === %i  (%s)", (input, expected) => {
    expect(wordCount(input)).toBe(expected);
  });

  test("wordCount handles null/undefined as 0 (defensive)", () => {
    expect(wordCount(null)).toBe(0);
    expect(wordCount(undefined)).toBe(0);
  });

  test("tokenizeWords returns the token list underlying the count", () => {
    expect(tokenizeWords("hello,world")).toEqual(["hello", "world"]);
    expect(tokenizeWords("well-known it's fine")).toEqual(["well-known", "it's", "fine"]);
    expect(tokenizeWords("")).toEqual([]);
    expect(tokenizeWords(null)).toEqual([]);
  });

  test("curly apostrophe diverges from the chip tokeniser but matches the backend", () => {
    // requiredWords.tokenize() keeps ’ as a joiner (chip matching); the
    // parity tokeniser must NOT, so it stays aligned with the backend.
    expect(wordCount("can’t")).toBe(2);
    expect(wordCount("can't")).toBe(1);
  });

  test("tokenizer version is pinned to the backend rule", () => {
    expect(WORD_TOKENIZER_VERSION).toBe("det-v1");
  });
});
