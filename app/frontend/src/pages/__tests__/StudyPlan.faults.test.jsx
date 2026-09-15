/**
 * PLAN-BUG-02 — the frontend halves of the six plan-page surface faults.
 *
 * F1 (an object stringified into the Truth Panel), F2 (a null in the heading),
 * F3 (a duplicate control) and F6 (a grid track that could not shrink) are
 * pinned here. F2's server half, F4 and F5 are pinned in
 * `app/backend/tests/study_os/test_plan_surface_faults.py`.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

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
  default: () => ({ busy: false, run: async ({ action }) => ({ ok: true, data: await action() }) }),
}));

jest.mock("../../features/study/hooks/useCalibrationPriors", () => ({
  __esModule: true,
  default: () => ({
    calibrated: true,
    checkFailed: false,
    needsUpdate: false,
    requiredSubjects: [{ id: "s1", name: "Quant" }],
    items: [],
    attemptsUsed: 0,
    loading: false,
    saving: false,
    error: "",
    submit: jest.fn(),
    skip: jest.fn(),
    refetch: jest.fn(),
  }),
}));

// eslint-disable-next-line import/first
import StudyPlan, { mockTrendLabel, planHeading } from "../StudyPlan";

/** The exact shape `weekly_review._mock_trend_history` returns. */
const MOCK_TREND = [
  { id: "m1", name: "Mock 1", percentage: 52.4 },
  { id: "m2", name: "Mock 2", percentage: 61 },
];

function wire({ plan, review, examsFail = false } = {}) {
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan") {
      return Promise.resolve({
        date: "2026-09-14",
        plan: plan === undefined ? { id: "p1", theme: "Adaptive weekly plan", day: 4 } : plan,
        tasks: [],
      });
    }
    if (path === "/api/study/weekly-review") return Promise.resolve(review || null);
    if (path === "/api/study/exams") {
      return examsFail
        ? Promise.reject(new Error("500"))
        : Promise.resolve({ items: [{ id: "e1", name: "SSC CGL", planner_ready: true }] });
    }
    if (path === "/api/study/focus/summary") return Promise.resolve({ total_hours_7d: 0, week: [] });
    if (path === "/api/study/target-exam") return Promise.resolve({ selected_exam: { id: "e1" } });
    if (path === "/api/study/tracked-exams") return Promise.resolve({ items: [] });
    return Promise.resolve({});
  });
}

beforeEach(() => {
  jest.clearAllMocks();
});

// ── F1 — an object must never reach a text slot ──────────────────────────

describe("F1 · Truth Panel mock trend", () => {
  test("renders percentages, never a stringified object", () => {
    expect(mockTrendLabel(MOCK_TREND)).toBe("52.4% · 61%");
    expect(mockTrendLabel(MOCK_TREND)).not.toContain("[object Object]");
  });

  test("says so plainly when nothing in the list carries a score", () => {
    expect(mockTrendLabel([])).toBe("No mocks yet");
    expect(mockTrendLabel(undefined)).toBe("No mocks yet");
    expect(mockTrendLabel([{ id: "m1", name: "Mock 1" }])).toBe("No mocks yet");
    expect(mockTrendLabel([{ percentage: null }])).toBe("No mocks yet");
  });

  test("the panel renders no [object Object] for the shape that produced it", async () => {
    wire({ review: { hours_studied: 6, mock_trend: MOCK_TREND, mocks_taken: 2, corrections: [] } });
    const { container } = render(<StudyPlan />);
    // PLAN-UI-03 moved this from a bare value in a dark metric card to a
    // sentence in "How this week went", so the scores are no longer their own
    // text node. The fault this test exists for is unchanged: the percentages
    // are read from the rows, and nothing stringifies an object.
    await waitFor(() =>
      expect(screen.getByText(/52\.4% · 61%/)).toBeInTheDocument(),
    );
    expect(container.textContent).not.toContain("[object Object]");
  });
});

// ── F2 — the heading must never print a null ─────────────────────────────

describe("F2 · plan heading", () => {
  test("shows the day when the server knows it", () => {
    expect(planHeading({ day: 4, theme: "Adaptive weekly plan" })).toBe(
      "Day 4 · Adaptive weekly plan",
    );
  });

  test("omits the segment entirely when the day is unknown", () => {
    for (const day of [null, undefined, 0, -1, "null", NaN]) {
      const title = planHeading({ day, theme: "Adaptive weekly plan" });
      expect(title).toBe("Adaptive weekly plan");
      expect(title).not.toContain("null");
      expect(title).not.toContain("Day");
    }
  });

  test("the rendered heading never contains null", async () => {
    wire({ plan: { id: "p1", theme: "Adaptive weekly plan", day: null } });
    const { container } = render(<StudyPlan />);
    await waitFor(() => expect(screen.getByText("Adaptive weekly plan")).toBeInTheDocument());
    expect(container.textContent).not.toContain("Day null");
    expect(container.textContent).not.toContain("null");
  });
});

// ── F3 — no control that promises something it does not do ───────────────

describe("F3 · Suggest changes", () => {
  test("the duplicate control is absent from the DOM", async () => {
    wire();
    render(<StudyPlan />);
    await waitFor(() =>
      expect(screen.getByTestId("regenerate-plan-btn")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("suggest-changes-btn")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /suggest changes/i })).not.toBeInTheDocument();
  });

  test("the preview flow it duplicated is still reachable", async () => {
    wire();
    render(<StudyPlan />);
    const regenerate = await screen.findByTestId("regenerate-plan-btn");
    expect(regenerate).toBeEnabled();
  });
});

// ── F4 — an error message that names what the user can do ────────────────

describe("F4 · tracked exams", () => {
  test("renders exams on a successful response", async () => {
    wire();
    render(<StudyPlan />);
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/api/study/exams"));
    expect(screen.queryByText(/aren't loading/i)).not.toBeInTheDocument();
  });

  test("a failure names an action the user can actually take", async () => {
    wire({ examsFail: true });
    render(<StudyPlan />);
    const message = await screen.findByText(/Exams aren't loading/i);
    expect(message.textContent).toMatch(/Reload the page/i);
    // "try again in a moment" was advice that could not work: the route failed
    // as a whole, every time, so a retry changed nothing.
    expect(message.textContent).not.toMatch(/try again in a moment/i);
  });
});
