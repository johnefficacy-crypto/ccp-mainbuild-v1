import { errorTypeLabel, ERROR_TYPE_LABELS } from "./errorTypeLabels";

test("maps every classifier code to a learner-friendly label", () => {
  expect(errorTypeLabel("silly_mistake")).toBe("Careless mistake");
  expect(errorTypeLabel("knowledge_gap")).toBe("Knowledge gap");
  expect(errorTypeLabel("concept_gap")).toBe("Concept gap");
  expect(errorTypeLabel("time_pressure_unattempted")).toBe("Time pressure / not attempted");
  expect(errorTypeLabel("option_trap")).toBe("Distractor trap");
  expect(errorTypeLabel("calc_error")).toBe("Calculation error");
  expect(errorTypeLabel("marked_unanswered")).toBe("Marked but unanswered");
  expect(errorTypeLabel("correct")).toBe("Correct");
});

test("never leaks a raw machine code for unknown or missing values", () => {
  expect(errorTypeLabel(null)).toBe("Not analyzed");
  expect(errorTypeLabel(undefined)).toBe("Not analyzed");
  expect(errorTypeLabel("")).toBe("Not analyzed");
  expect(errorTypeLabel("some_new_backend_code")).toBe("Not analyzed");
});

test("label table has no snake_case values (nothing raw slips through)", () => {
  for (const label of Object.values(ERROR_TYPE_LABELS)) {
    expect(label).not.toMatch(/_[a-z]/);
  }
});
