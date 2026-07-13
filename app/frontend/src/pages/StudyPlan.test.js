import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

const mockGet = jest.fn();
const mockPut = jest.fn();
const mockPost = jest.fn();
const mockDel = jest.fn();

jest.mock("../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...args) => mockGet(...args),
    put: (...args) => mockPut(...args),
    post: (...args) => mockPost(...args),
    del: (...args) => mockDel(...args),
  },
}));

// Heavy children pull in their own data; stub them so this test stays focused
// on the hydration behavior of the exam picker.
jest.mock("../features/study/components/PlanChangeLogCard", () => () => null);
jest.mock("../features/study/components/PlanByTopic", () => () => null);
jest.mock("../features/study/components/ExamCycleTimeline", () => () => null);

jest.mock("../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({ run: jest.fn() }),
}));

import StudyPlan from "./StudyPlan";

const EXAM_ID = "11111111-1111-4111-8111-111111111111";

function setupApi({ selectedExam, trackedItems } = {}) {
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan") return Promise.resolve({ plan: null, tasks: [] });
    if (path === "/api/study/focus/summary") return Promise.resolve({ total_hours_7d: 0, week: [] });
    if (path === "/api/study/weekly-review") return Promise.resolve(null);
    if (path === "/api/study/exams") {
      return Promise.resolve({
        items: [
          { id: EXAM_ID, name: "SSC CGL", planner_ready: true },
          { id: "22222222-2222-4222-8222-222222222222", name: "UPSC CSE", planner_ready: false },
        ],
      });
    }
    if (path === "/api/study/target-exam") return Promise.resolve({ selected_exam: selectedExam });
    if (path === "/api/study/tracked-exams") {
      return Promise.resolve({ items: trackedItems || [], primary_exam_id: selectedExam?.id || null });
    }
    return Promise.resolve({});
  });
}

afterEach(() => {
  mockGet.mockReset();
  mockPut.mockReset();
  mockPost.mockReset();
  mockDel.mockReset();
});

test("hydrates selectedExamId from GET /api/study/target-exam on mount", async () => {
  setupApi({
    selectedExam: { id: EXAM_ID, slug: "ssc-cgl", name: "SSC CGL", is_active: true },
  });

  await act(async () => {
    render(<StudyPlan />);
  });

  // Once hydration resolves, the "Choose your exam" empty-state copy must
  // disappear and the current selection must stay visible as a chip even with
  // the selector drawer closed and no tracked-exams strip present.
  await waitFor(() => {
    expect(screen.queryByText(/Choose the exam you are preparing for\./i)).toBeNull();
  });
  const chip = screen.getByTestId("selected-exam-chip");
  expect(chip.textContent).toMatch(/SSC CGL/);
  expect(chip.textContent).toMatch(/Primary/);
  // With a selection present, the control invites a change rather than a first
  // choice.
  expect(screen.getByTestId("open-exam-selector").textContent).toMatch(/Change or add exam/i);
  // Confirm the hydration call actually fired.
  expect(mockGet).toHaveBeenCalledWith("/api/study/target-exam");
});

test("selector drawer lists planner-ready exams first and hides not-ready under Other exams", async () => {
  setupApi({ selectedExam: null });

  await act(async () => {
    render(<StudyPlan />);
  });

  await waitFor(() => {
    expect(screen.getByTestId("open-exam-selector")).toBeTruthy();
  });
  // The full exam list is not rendered inline — it only appears in the drawer.
  expect(screen.queryByTestId("exam-selector")).toBeNull();

  fireEvent.click(screen.getByTestId("open-exam-selector"));

  // Planner-ready exam is visible immediately; the not-ready exam is collapsed.
  expect(screen.getByTestId(`exam-option-${EXAM_ID}`)).toBeTruthy();
  expect(
    screen.queryByTestId("exam-option-22222222-2222-4222-8222-222222222222"),
  ).toBeNull();

  // Expanding "Other exams" reveals the not-ready exam.
  fireEvent.click(screen.getByTestId("toggle-other-exams"));
  expect(
    screen.getByTestId("exam-option-22222222-2222-4222-8222-222222222222"),
  ).toBeTruthy();
});

test("not-ready exams in the selector are informational and cannot be chosen", async () => {
  setupApi({ selectedExam: null });

  await act(async () => {
    render(<StudyPlan />);
  });

  await waitFor(() => {
    expect(screen.getByTestId("open-exam-selector")).toBeTruthy();
  });
  fireEvent.click(screen.getByTestId("open-exam-selector"));
  fireEvent.click(screen.getByTestId("toggle-other-exams"));

  const notReady = screen.getByTestId(
    "exam-option-22222222-2222-4222-8222-222222222222",
  );
  // The row is not a control (no button role) and clicking it does nothing.
  expect(notReady.tagName).not.toBe("BUTTON");
  fireEvent.click(notReady);

  // No target mutation, and the drawer stays open.
  expect(mockPut).not.toHaveBeenCalled();
  expect(screen.getByTestId("exam-selector")).toBeTruthy();
});

test("searching the selector reveals a matching not-ready exam without expanding", async () => {
  setupApi({ selectedExam: null });

  await act(async () => {
    render(<StudyPlan />);
  });

  await waitFor(() => {
    expect(screen.getByTestId("open-exam-selector")).toBeTruthy();
  });
  fireEvent.click(screen.getByTestId("open-exam-selector"));

  fireEvent.change(screen.getByTestId("exam-search-input"), {
    target: { value: "upsc" },
  });

  // The ready exam is filtered out; the matching not-ready exam auto-reveals.
  expect(screen.queryByTestId(`exam-option-${EXAM_ID}`)).toBeNull();
  expect(
    screen.getByTestId("exam-option-22222222-2222-4222-8222-222222222222"),
  ).toBeTruthy();
});

test("keeps empty state when no target exam is stored", async () => {
  setupApi({ selectedExam: null });

  await act(async () => {
    render(<StudyPlan />);
  });

  await waitFor(() => {
    expect(screen.getByText(/Choose the exam you are preparing for\./i)).toBeTruthy();
  });
});

test("renders the tracked-exams strip with the primary flagged", async () => {
  setupApi({
    selectedExam: { id: EXAM_ID, slug: "ssc-cgl", name: "SSC CGL", is_active: true },
    trackedItems: [
      { id: EXAM_ID, slug: "ssc-cgl", name: "SSC CGL", is_active: true, planner_ready: true, is_primary: true },
      { id: "22222222-2222-4222-8222-222222222222", slug: "upsc-cse", name: "UPSC CSE", is_active: true, planner_ready: false, is_primary: false },
    ],
  });

  await act(async () => {
    render(<StudyPlan />);
  });

  await waitFor(() => {
    expect(screen.getByTestId("tracked-exams-strip")).toBeTruthy();
  });
  expect(mockGet).toHaveBeenCalledWith("/api/study/tracked-exams");
  const primary = screen.getByTestId("tracked-exam-ssc-cgl");
  expect(primary.getAttribute("data-primary")).toBe("true");
  expect(primary.textContent).toMatch(/Primary/);
  const secondary = screen.getByTestId("tracked-exam-upsc-cse");
  expect(secondary.getAttribute("data-primary")).toBe("false");
});

test("strip is hidden when no tracked exams come back", async () => {
  setupApi({ selectedExam: null, trackedItems: [] });

  await act(async () => {
    render(<StudyPlan />);
  });

  await waitFor(() => {
    expect(mockGet).toHaveBeenCalledWith("/api/study/tracked-exams");
  });
  expect(screen.queryByTestId("tracked-exams-strip")).toBeNull();
});
