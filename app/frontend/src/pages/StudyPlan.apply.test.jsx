import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPut = jest.fn();
const mockDel = jest.fn();
const mockSuccessToast = jest.fn();
const mockErrorToast = jest.fn();

jest.mock("../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...a) => mockGet(...a),
    post: (...a) => mockPost(...a),
    put: (...a) => mockPut(...a),
    del: (...a) => mockDel(...a),
  },
}));

jest.mock("../features/study/components/PlanChangeLogCard", () => () => null);
jest.mock("../features/study/components/PlanByTopic", () => () => null);
jest.mock("../features/study/components/ExamCycleTimeline", () => () => null);

// Faithful re-implementation of useApiAction so we exercise the real
// applyDraft control flow (throw-on-failure → result.ok === false) without
// dragging in the ToastProvider. Records toast calls so the test can assert
// that NO success toast fires on a failed apply.
jest.mock("../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({
    run: async ({ action, optimistic, rollback, onSuccess, successMessage, errorMessage }) => {
      if (optimistic) optimistic();
      try {
        const data = await action();
        if (successMessage) mockSuccessToast(successMessage);
        if (onSuccess) onSuccess(data);
        return { ok: true, data };
      } catch (e) {
        if (rollback) rollback();
        mockErrorToast(errorMessage || e?.message);
        return { ok: false, error: e };
      }
    },
  }),
}));

import StudyPlan from "./StudyPlan";

const EXAM_ID = "11111111-1111-4111-8111-111111111111";

function primeGet() {
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan") return Promise.resolve({ plan: null, tasks: [] });
    if (path === "/api/study/focus/summary") return Promise.resolve({ total_hours_7d: 0, week: [] });
    if (path === "/api/study/weekly-review") return Promise.resolve(null);
    if (path === "/api/study/exams") {
      return Promise.resolve({ items: [{ id: EXAM_ID, name: "SSC CGL", planner_ready: true }] });
    }
    if (path === "/api/study/target-exam") {
      return Promise.resolve({
        selected_exam: { id: EXAM_ID, slug: "ssc-cgl", name: "SSC CGL", is_active: true },
      });
    }
    if (path === "/api/study/tracked-exams") {
      return Promise.resolve({
        items: [
          { id: EXAM_ID, slug: "ssc-cgl", name: "SSC CGL", is_active: true, planner_ready: true, is_primary: true },
        ],
        primary_exam_id: EXAM_ID,
      });
    }
    if (path === "/api/study/self-assessment") {
      // Calibrated so the plan action controls render and applyDraft runs
      // (the calibration gate hides/short-circuits them otherwise).
      return Promise.resolve({
        exam_id: EXAM_ID,
        calibrated: true,
        status: "completed",
        needs_update: false,
        required_subjects: [],
        items: [],
        attempts_used: 0,
      });
    }
    if (path === "/api/study/plan/draft") {
      return Promise.resolve({
        generated: true,
        exam_name: "SSC CGL",
        risk_level: "low",
        before_tasks: [],
        after_tasks: [{ topic_id: "t1", title: "Quant · Number Systems" }],
        changes: { added: [], removed: [], added_count: 1, removed_count: 0, unchanged_count: 0 },
      });
    }
    return Promise.resolve({});
  });
}

async function openDraftAndApply() {
  await act(async () => {
    render(<StudyPlan />);
  });
  const regenBtn = await screen.findByTestId("regenerate-plan-btn");
  await act(async () => {
    fireEvent.click(regenBtn);
  });
  const applyBtn = await screen.findByTestId("apply-draft-btn");
  await act(async () => {
    fireEvent.click(applyBtn);
  });
}

afterEach(() => {
  mockGet.mockReset();
  mockPost.mockReset();
  mockPut.mockReset();
  mockDel.mockReset();
  mockSuccessToast.mockReset();
  mockErrorToast.mockReset();
});

test("keeps drawer open and shows reason, no success toast, on non-2xx apply failure", async () => {
  primeGet();
  // Backend now returns a non-2xx; api.post throws an error carrying the reason.
  mockPost.mockImplementation((path) => {
    if (path === "/api/study/plan/apply") {
      const e = new Error("API 500");
      e.status = 500;
      e.detail = { reason: "plan_persist_failed", generated: false };
      e.data = { detail: e.detail };
      return Promise.reject(e);
    }
    return Promise.resolve({});
  });

  await openDraftAndApply();

  // Drawer stays open (apply button still present) and the reason renders
  // inline via the existing error component.
  await waitFor(() => {
    expect(screen.getByTestId("apply-error")).toBeTruthy();
  });
  expect(screen.getByTestId("apply-error").textContent).toMatch(/plan_persist_failed/);
  expect(screen.getByTestId("apply-draft-btn")).toBeTruthy();
  // No "Plan applied." success toast on a failed apply.
  expect(mockSuccessToast).not.toHaveBeenCalled();
});

test("treats a 2xx body with generated:false as a failure (no success toast)", async () => {
  primeGet();
  mockPost.mockImplementation((path) => {
    if (path === "/api/study/plan/apply") {
      return Promise.resolve({ generated: false, applied: false, reason: "no_locked_coverage" });
    }
    return Promise.resolve({});
  });

  await openDraftAndApply();

  await waitFor(() => {
    expect(screen.getByTestId("apply-error")).toBeTruthy();
  });
  expect(screen.getByTestId("apply-error").textContent).toMatch(/no_locked_coverage/);
  expect(screen.getByTestId("apply-draft-btn")).toBeTruthy();
  expect(mockSuccessToast).not.toHaveBeenCalled();
});

test("closes drawer and toasts success when apply succeeds", async () => {
  primeGet();
  mockPost.mockImplementation((path) => {
    if (path === "/api/study/plan/apply") {
      return Promise.resolve({ generated: true, applied: true, version_number: 1 });
    }
    return Promise.resolve({});
  });

  await openDraftAndApply();

  // Success path: drawer closes (apply button gone) and the success toast fires.
  await waitFor(() => {
    expect(screen.queryByTestId("apply-draft-btn")).toBeNull();
  });
  expect(mockSuccessToast).toHaveBeenCalledWith("Plan applied.");
  expect(screen.queryByTestId("apply-error")).toBeNull();
});
