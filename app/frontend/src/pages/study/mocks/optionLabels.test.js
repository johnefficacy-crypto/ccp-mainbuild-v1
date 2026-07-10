import { resolveOptionLabel, formatOptionLabel } from "./optionLabels";

test("keeps an official printed source_label as-is", () => {
  expect(resolveOptionLabel({ source_label: "(a)" }, 0)).toBe("(a)");
  expect(resolveOptionLabel({ source_label: "(iv)" }, 3)).toBe("(iv)");
});

test("uppercases an A/B/C-style option_index", () => {
  expect(resolveOptionLabel({ option_index: "a" }, 5)).toBe("A");
  expect(resolveOptionLabel({ option_index: "C" }, 0)).toBe("C");
});

test("numeric option_index never leaks — falls back to the positional letter", () => {
  expect(resolveOptionLabel({ option_index: 0 }, 0)).toBe("A");
  expect(resolveOptionLabel({ option_index: 1 }, 1)).toBe("B");
  expect(resolveOptionLabel({ option_index: 3 }, 3)).toBe("D");
});

test("uses a non-numeric option_label when present", () => {
  expect(resolveOptionLabel({ option_label: "P" }, 0)).toBe("P");
  // purely numeric option_label is ignored (never shown as a digit)
  expect(resolveOptionLabel({ option_label: "2" }, 1)).toBe("B");
});

test("falls back to visible order when nothing usable is present", () => {
  expect(resolveOptionLabel({}, 0)).toBe("A");
  expect(resolveOptionLabel(null, 2)).toBe("C");
  expect(resolveOptionLabel({ id: "11111111-1111-4111-8111-111111111111" }, 4)).toBe("E");
});

test("never renders a raw UUID or a digit", () => {
  const label = resolveOptionLabel({ id: "deadbeef-0000-4000-8000-000000000000", option_index: 2 }, 2);
  expect(label).toBe("C");
  expect(label).not.toMatch(/\d/);
  expect(label).not.toContain("deadbeef");
});

test("formatOptionLabel appends a dot to bare labels but not to printed labels", () => {
  // bare alphanumeric → append "."
  expect(formatOptionLabel({ option_index: "A" }, 0)).toBe("A.");
  expect(formatOptionLabel({ option_index: 0 }, 1)).toBe("B.");
  // already-punctuated printed label stays verbatim (no "(a).")
  expect(formatOptionLabel({ source_label: "(a)" }, 0)).toBe("(a)");
  expect(formatOptionLabel({ source_label: "(iv)" }, 3)).toBe("(iv)");
});
