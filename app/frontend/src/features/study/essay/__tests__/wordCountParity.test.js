/**
 * The shared word rule, pinned on the JS side.
 *
 * `wordCount` is used by three surfaces now — the Essay Spine's slot readout,
 * the descriptive answer editor's live counter, and (as
 * `descriptive.word_count`) the server that stores the number. This file and
 * `app/backend/tests/study_os/test_descriptive_practice.py` read the SAME
 * fixture list, so neither implementation can drift without the other's test
 * going red.
 *
 * Why it matters here specifically: the descriptive editor shows a live count
 * against a word limit while you type, and the server recomputes it on save. A
 * live counter that disagrees with the stored one is worse than no counter —
 * the aspirant would watch it cross 150 and then be told it hadn't.
 */
import fs from "fs";
import path from "path";

import { wordCount } from "../spineSlots";

const FIXTURES = path.resolve(
  __dirname,
  "../../../../../../backend/tests/fixtures/word_count_cases.json",
);

const { cases } = JSON.parse(fs.readFileSync(FIXTURES, "utf8"));

test("the fixture file is actually loaded and non-trivial", () => {
  // A silently-empty fixture list would make every parity assertion below pass
  // vacuously, which is the one way this test could lie.
  expect(Array.isArray(cases)).toBe(true);
  expect(cases.length).toBeGreaterThan(10);
});

test.each(cases.map((c) => [c.name, c.text, c.expected]))(
  "wordCount: %s",
  (_name, text, expected) => {
    expect(wordCount(text)).toBe(expected);
  },
);

test("nullish input counts as zero, matching the Python `str(text or '')`", () => {
  expect(wordCount(null)).toBe(0);
  expect(wordCount(undefined)).toBe(0);
});
