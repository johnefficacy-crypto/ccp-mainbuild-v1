/**
 * SetupPanel — D1 identity collapse regression tests.
 *
 * Verifies that the "Exam details" card (name, slug, type, family) previously
 * at lines ~909–924 has been removed because those fields are already shown in
 * SmartHeader. Also verifies that the rest of SetupPanel (cycles, phases, etc.)
 * continues to render.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
}));

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: jest.fn(),
}));

jest.mock("../../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => {
    const run = jest.fn(async ({ action, onSuccess }) => {
      try {
        const result = await action();
        if (onSuccess) onSuccess(result);
        return { ok: true, data: result };
      } catch (e) {
        return { ok: false, error: e };
      }
    });
    return { run, busy: false };
  },
}));

const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const SetupPanel = require("../SetupPanel").default;

const BASE_EXAM = {
  id: "exam-1",
  name: "UPSC CSE",
  slug: "upsc-cse",
  exam_type: "recruitment",
  family: "civil-services",
  family_name: "Civil Services",
};

const ACTIVE_CYCLE = { id: "cyc-1", status: "active", cycle_name: "2026 Cycle", year: 2026 };

function setup(overrides = {}) {
  useExamWorkspace.mockReturnValue({
    exam: BASE_EXAM,
    cycles: [ACTIVE_CYCLE],
    phases: [],
    refetch: jest.fn(),
    ...overrides,
  });
  return render(<SetupPanel />);
}

describe("SetupPanel — D1 identity collapse", () => {
  afterEach(() => jest.clearAllMocks());

  test("D1: does not render an 'Exam details' heading (removed card)", () => {
    setup();
    expect(screen.queryByText("Exam details")).toBeNull();
  });

  test("D1: does not render exam name in the exam-details region (shown in SmartHeader)", () => {
    setup();
    // The exam name should not appear in a field-val inside the old exam-details card.
    // We check that there is no element with text "UPSC CSE" inside a field-val div.
    // Since the rest of SetupPanel does not render exam.name as field-val,
    // the only occurrence would have been the removed card.
    const fieldVals = document.querySelectorAll(".field-val");
    const nameInFieldVal = Array.from(fieldVals).some(
      (el) => el.textContent === "UPSC CSE",
    );
    expect(nameInFieldVal).toBe(false);
  });

  test("D1: does not render exam slug in a field-val (shown in SmartHeader)", () => {
    setup();
    const fieldVals = document.querySelectorAll(".field-val");
    const slugInFieldVal = Array.from(fieldVals).some(
      (el) => el.textContent === "upsc-cse",
    );
    expect(slugInFieldVal).toBe(false);
  });

  test("D1: does not render exam type in a field-val (shown in SmartHeader)", () => {
    setup();
    const fieldVals = document.querySelectorAll(".field-val");
    const typeInFieldVal = Array.from(fieldVals).some(
      (el) => el.textContent === "recruitment",
    );
    expect(typeInFieldVal).toBe(false);
  });

  test("D1: does not render exam family in a field-val (shown in SmartHeader)", () => {
    setup();
    const fieldVals = document.querySelectorAll(".field-val");
    const familyInFieldVal = Array.from(fieldVals).some(
      (el) => el.textContent === "Civil Services" || el.textContent === "civil-services",
    );
    expect(familyInFieldVal).toBe(false);
  });

  test("SetupPanel still renders cycle information (rest of panel preserved)", () => {
    setup();
    // The cycle section heading or the cycle name should still be present
    expect(screen.getByText("2026 Cycle")).toBeTruthy();
  });

  test("SetupPanel still renders + Create cycle button (rest of panel preserved)", () => {
    setup({ cycles: [] });
    expect(screen.getByText(/create cycle/i)).toBeTruthy();
  });
});
