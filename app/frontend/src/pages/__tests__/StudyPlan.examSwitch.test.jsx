import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPut = jest.fn();
const mockDel = jest.fn();

jest.mock("../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...a) => mockGet(...a),
    post: (...a) => mockPost(...a),
    put: (...a) => mockPut(...a),
    del: (...a) => mockDel(...a),
  },
}));

jest.mock("../../features/study/components/PlanChangeLogCard", () => () => null);
jest.mock("../../features/study/components/PlanByTopic", () => () => null);
jest.mock("../../features/study/components/ExamCycleTimeline", () => () => null);

jest.mock("../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({
    run: async ({ action }) => {
      try {
        return { ok: true, data: await action() };
      } catch (e) {
        return { ok: false, error: e };
      }
    },
  }),
}));

import StudyPlan from "../StudyPlan";

const EXAM_A = "11111111-1111-4111-8111-111111111111";
const EXAM_B = "22222222-2222-4222-8222-222222222222";

/** D5: the switch widened PUT /target-exam's response with a `plan` block. */
function primeGet() {
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan") return Promise.resolve({ plan: null, tasks: [] });
    if (path === "/api/study/focus/summary")
      return Promise.resolve({ total_hours_7d: 0, week: [] });
    if (path === "/api/study/weekly-review") return Promise.resolve(null);
    if (path === "/api/study/exams") {
      return Promise.resolve({
        items: [
          { id: EXAM_A, name: "SSC CGL", planner_ready: true },
          { id: EXAM_B, name: "IBPS PO", planner_ready: true },
        ],
      });
    }
    if (path === "/api/study/target-exam") {
      return Promise.resolve({
        selected_exam: { id: EXAM_A, slug: "ssc-cgl", name: "SSC CGL", is_active: true },
      });
    }
    if (path === "/api/study/tracked-exams") {
      return Promise.resolve({ items: [], primary_exam_id: EXAM_A });
    }
    if (path === "/api/study/self-assessment") {
      return Promise.resolve({
        exam_id: EXAM_A,
        calibrated: true,
        status: "completed",
        needs_update: false,
        required_subjects: [],
        items: [],
        attempts_used: 0,
      });
    }
    return Promise.resolve({});
  });
}

async function switchToExamB() {
  await act(async () => {
    render(<StudyPlan />);
  });
  await act(async () => {
    fireEvent.click(screen.getByTestId("open-exam-selector"));
  });
  const btn = await screen.findByTestId(`exam-option-${EXAM_B}`);
  await act(async () => {
    fireEvent.click(btn);
  });
}

beforeEach(() => {
  primeGet();
  mockPut.mockReset();
});

test("shows the planner's reason when the switch created no plan", async () => {
  mockPut.mockResolvedValue({
    ok: true,
    selected_exam: { id: EXAM_B, slug: "ibps-po", name: "IBPS PO" },
    plan: { created: false, reason: "calibration_required" },
  });

  await switchToExamB();

  await waitFor(() => {
    expect(screen.getByTestId("exam-switch-notice")).toBeTruthy();
  });
  // Aspirant-facing copy, not the raw planner code.
  expect(screen.getByTestId("exam-switch-notice").textContent).toMatch(
    /quick questions about this exam/i,
  );
  expect(screen.getByTestId("exam-switch-notice").textContent).not.toMatch(
    /calibration_required/,
  );
});

test("shows no notice when a plan was created", async () => {
  mockPut.mockResolvedValue({
    ok: true,
    selected_exam: { id: EXAM_B, slug: "ibps-po", name: "IBPS PO" },
    plan: { created: true, reason: null },
  });

  await switchToExamB();

  await waitFor(() => {
    expect(mockPut).toHaveBeenCalled();
  });
  expect(screen.queryByTestId("exam-switch-notice")).toBeNull();
});

test("an unmapped reason still produces a plain notice, never a raw code", async () => {
  mockPut.mockResolvedValue({
    ok: true,
    selected_exam: { id: EXAM_B, slug: "ibps-po", name: "IBPS PO" },
    plan: { created: false, reason: "task_persist_failed" },
  });

  await switchToExamB();

  await waitFor(() => {
    expect(screen.getByTestId("exam-switch-notice")).toBeTruthy();
  });
  expect(screen.getByTestId("exam-switch-notice").textContent).not.toMatch(
    /task_persist_failed/,
  );
});

test("a response without the plan block does not break the switch", async () => {
  // Back-compat: an older server (or a deploy skew) returns {ok, selected_exam}.
  mockPut.mockResolvedValue({
    ok: true,
    selected_exam: { id: EXAM_B, slug: "ibps-po", name: "IBPS PO" },
  });

  await switchToExamB();

  await waitFor(() => {
    expect(mockPut).toHaveBeenCalled();
  });
  expect(screen.queryByTestId("exam-switch-notice")).toBeNull();
});
