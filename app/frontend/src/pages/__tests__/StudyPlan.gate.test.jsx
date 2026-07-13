import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

const mockGet = jest.fn();
const mockPut = jest.fn();
const mockPost = jest.fn();
const mockDel = jest.fn();

jest.mock("../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...args) => mockGet(...args),
    put: (...args) => mockPut(...args),
    post: (...args) => mockPost(...args),
    del: (...args) => mockDel(...args),
  },
}));

jest.mock("../../features/study/components/PlanChangeLogCard", () => () => null);
jest.mock("../../features/study/components/PlanByTopic", () => () => null);
jest.mock("../../features/study/components/ExamCycleTimeline", () => () => null);

jest.mock("../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({ run: jest.fn() }),
}));

import StudyPlan from "../StudyPlan";

const EXAM_ID = "11111111-1111-4111-8111-111111111111";

// Prime every endpoint StudyPlan hits on mount. `selfAssessment` is injected so
// each test controls whether the calibration GET resolves, never resolves, or
// returns a specific gate state.
function primeApi({ selfAssessment } = {}) {
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan") return Promise.resolve({ plan: null, tasks: [] });
    if (path === "/api/study/focus/summary")
      return Promise.resolve({ total_hours_7d: 0, week: [] });
    if (path === "/api/study/weekly-review") return Promise.resolve(null);
    if (path === "/api/study/exams") {
      return Promise.resolve({
        items: [{ id: EXAM_ID, name: "SSC CGL", planner_ready: true }],
      });
    }
    if (path === "/api/study/target-exam") {
      return Promise.resolve({
        selected_exam: { id: EXAM_ID, slug: "ssc-cgl", name: "SSC CGL", is_active: true },
      });
    }
    if (path === "/api/study/tracked-exams") {
      return Promise.resolve({
        items: [
          {
            id: EXAM_ID,
            slug: "ssc-cgl",
            name: "SSC CGL",
            planner_ready: true,
            is_primary: true,
          },
        ],
        primary_exam_id: EXAM_ID,
      });
    }
    if (path === "/api/study/self-assessment") {
      return selfAssessment
        ? selfAssessment()
        : Promise.resolve({
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
        after_tasks: [{ topic_id: "t1", title: "Quant" }],
        changes: { added: [], removed: [], added_count: 1, removed_count: 0, unchanged_count: 0 },
      });
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

test("while calibration is loading, plan action controls are NOT rendered and a checking state shows", async () => {
  // Self-assessment GET never resolves → calibrated stays null (loading).
  primeApi({ selfAssessment: () => new Promise(() => {}) });

  await act(async () => {
    render(<StudyPlan />);
  });

  // The lightweight loading note is shown once the exam id has hydrated.
  await waitFor(() => {
    expect(screen.getByTestId("plan-controls-checking")).toBeTruthy();
  });

  // Generation controls must be absent while the gate is unresolved — a user
  // cannot trigger a plan draft before calibration resolves.
  expect(screen.queryByTestId("regenerate-plan-btn")).toBeNull();
  expect(screen.queryByTestId("suggest-changes-btn")).toBeNull();
  // The blocking interstitial is also not shown yet (only shown on false).
  expect(screen.queryByTestId("preplan-calibration")).toBeNull();
  // The draft endpoint was never called.
  expect(
    mockGet.mock.calls.some(([p]) => p === "/api/study/plan/draft"),
  ).toBe(false);
});

test("when calibrated === false the interstitial shows and controls stay hidden", async () => {
  primeApi({
    selfAssessment: () =>
      Promise.resolve({
        exam_id: EXAM_ID,
        calibrated: false,
        status: "none",
        needs_update: false,
        required_subjects: [
          { subject_id: "s1", subject_name: "Quant" },
        ],
        items: [],
        attempts_used: null,
      }),
  });

  await act(async () => {
    render(<StudyPlan />);
  });

  await waitFor(() => {
    expect(screen.getByTestId("preplan-calibration")).toBeTruthy();
  });
  expect(screen.getByTestId("plan-controls-gated")).toBeTruthy();
  expect(screen.queryByTestId("regenerate-plan-btn")).toBeNull();
  expect(screen.queryByTestId("plan-controls-checking")).toBeNull();
});

test("once calibrated === true the generation controls render", async () => {
  primeApi(); // default self-assessment = calibrated true

  await act(async () => {
    render(<StudyPlan />);
  });

  expect(await screen.findByTestId("regenerate-plan-btn")).toBeTruthy();
  expect(screen.getByTestId("suggest-changes-btn")).toBeTruthy();
  expect(screen.queryByTestId("plan-controls-checking")).toBeNull();
  expect(screen.queryByTestId("plan-controls-gated")).toBeNull();
});

// Integration coverage of the hook's stale cross-exam guard (FIX 2): exam A's
// self-assessment GET is held open, the user switches to exam B (uncalibrated),
// and only THEN does A's GET resolve as calibrated:true. A's stale response must
// not clobber B's gate and unlock plan generation for B.
const EXAM_A = EXAM_ID;
const EXAM_B = "22222222-2222-4222-8222-222222222222";

test("a stale self-assessment response for the previous exam does not unlock the new exam", async () => {
  // Hold exam A's self-assessment so it resolves on our command.
  let resolveA;
  const aGet = new Promise((res) => {
    resolveA = res;
  });
  // Per-exam self-assessment behaviour, keyed off how many times the GET ran:
  // first call (exam A, hydrated on mount) is deferred; later calls (exam B,
  // after the switch) resolve immediately as uncalibrated.
  let saCalls = 0;

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
      // Hydrate the initial selection to exam A.
      return Promise.resolve({
        selected_exam: { id: EXAM_A, slug: "ssc-cgl", name: "SSC CGL", is_active: true },
      });
    }
    if (path === "/api/study/tracked-exams") {
      return Promise.resolve({ items: [], primary_exam_id: EXAM_A });
    }
    if (path === "/api/study/self-assessment") {
      saCalls += 1;
      if (saCalls === 1) {
        // Exam A — deferred, ultimately calibrated:true (the stale unlock).
        return aGet;
      }
      // Exam B — uncalibrated.
      return Promise.resolve({
        exam_id: EXAM_B,
        calibrated: false,
        status: "none",
        needs_update: false,
        required_subjects: [{ subject_id: "b1", subject_name: "Reasoning" }],
        items: [],
        attempts_used: null,
      });
    }
    return Promise.resolve({});
  });
  // chooseExam PUTs the target before flipping selectedExamId.
  mockPut.mockReset();
  mockPut.mockResolvedValue({});

  await act(async () => {
    render(<StudyPlan />);
  });

  // Exam A is hydrated and its gate is still loading (GET held).
  await waitFor(() => {
    expect(screen.getByTestId("plan-controls-checking")).toBeTruthy();
  });

  // Switch to exam B: open the selector drawer, then pick B from the list.
  await act(async () => {
    fireEvent.click(screen.getByTestId("open-exam-selector"));
  });
  const examBBtn = screen.getByTestId(`exam-option-${EXAM_B}`);
  await act(async () => {
    fireEvent.click(examBBtn);
  });

  // B resolved as uncalibrated → interstitial shown, controls hidden.
  await waitFor(() => {
    expect(screen.getByTestId("preplan-calibration")).toBeTruthy();
  });
  expect(screen.queryByTestId("regenerate-plan-btn")).toBeNull();

  // Now A's slow GET finally resolves as calibrated:true — the stale unlock.
  await act(async () => {
    resolveA({
      exam_id: EXAM_A,
      calibrated: true,
      status: "completed",
      needs_update: false,
      required_subjects: [],
      items: [],
      attempts_used: 0,
    });
    await aGet;
  });

  // B's gate must be untouched: still blocked, no generation controls.
  expect(screen.getByTestId("preplan-calibration")).toBeTruthy();
  expect(screen.queryByTestId("regenerate-plan-btn")).toBeNull();
  expect(screen.queryByTestId("plan-controls-checking")).toBeNull();
});

// FIX 1: a transient read failure comes back as calibration_check_failed:true
// (calibrated:false, empty required set). The UI must show a non-blocking retry
// state — NOT the interstitial (which would render with no subjects) and NOT
// the plan controls — and Retry must re-issue the self-assessment GET.
test("calibration_check_failed shows a retry state with no interstitial and no controls", async () => {
  primeApi({
    selfAssessment: () =>
      Promise.resolve({
        exam_id: EXAM_ID,
        calibrated: false,
        calibration_check_failed: true,
        status: "unknown",
        needs_update: false,
        required_subjects: [],
        items: [],
        attempts_used: null,
      }),
  });

  await act(async () => {
    render(<StudyPlan />);
  });

  await waitFor(() => {
    expect(screen.getByTestId("plan-controls-check-failed")).toBeTruthy();
  });

  // Neither the interstitial nor the plan controls nor the gated/checking notes.
  expect(screen.queryByTestId("preplan-calibration")).toBeNull();
  expect(screen.queryByTestId("regenerate-plan-btn")).toBeNull();
  expect(screen.queryByTestId("suggest-changes-btn")).toBeNull();
  expect(screen.queryByTestId("plan-controls-gated")).toBeNull();
  expect(screen.queryByTestId("plan-controls-checking")).toBeNull();

  // Retry re-issues the self-assessment GET.
  const before = mockGet.mock.calls.filter(
    ([p]) => p === "/api/study/self-assessment",
  ).length;
  await act(async () => {
    fireEvent.click(screen.getByTestId("calibration-retry-btn"));
  });
  await waitFor(() => {
    const after = mockGet.mock.calls.filter(
      ([p]) => p === "/api/study/self-assessment",
    ).length;
    expect(after).toBeGreaterThan(before);
  });
});

// FIX (4th review): the self-assessment GET REJECTS (network error, or a
// failure in the backend's post-evaluate prefill reads). The hook's catch path
// has no authoritative gate state, so it must set checkFailed:true. The page
// must then render the retry state — NOT the blocking interstitial (which would
// render with an empty required set) and NOT the plan controls — and Retry must
// re-issue the self-assessment GET. This is the thrown-error sibling of the
// calibration_check_failed:true 200-response case above; both lead to retry.
test("a rejected self-assessment GET shows the retry state, no interstitial, no controls", async () => {
  primeApi({
    selfAssessment: () => Promise.reject(new Error("network down")),
  });

  await act(async () => {
    render(<StudyPlan />);
  });

  await waitFor(() => {
    expect(screen.getByTestId("plan-controls-check-failed")).toBeTruthy();
  });

  // Never the interstitial (it would render with no authoritative subjects),
  // never the plan controls, never the gated/checking notes.
  expect(screen.queryByTestId("preplan-calibration")).toBeNull();
  expect(screen.queryByTestId("regenerate-plan-btn")).toBeNull();
  expect(screen.queryByTestId("suggest-changes-btn")).toBeNull();
  expect(screen.queryByTestId("plan-controls-gated")).toBeNull();
  expect(screen.queryByTestId("plan-controls-checking")).toBeNull();
  // The draft endpoint was never reachable (handlers stay gated on calibrated).
  expect(
    mockGet.mock.calls.some(([p]) => p === "/api/study/plan/draft"),
  ).toBe(false);

  // Retry re-issues the self-assessment GET.
  const before = mockGet.mock.calls.filter(
    ([p]) => p === "/api/study/self-assessment",
  ).length;
  await act(async () => {
    fireEvent.click(screen.getByTestId("calibration-retry-btn"));
  });
  await waitFor(() => {
    const after = mockGet.mock.calls.filter(
      ([p]) => p === "/api/study/self-assessment",
    ).length;
    expect(after).toBeGreaterThan(before);
  });
});

// FIX 2: when the required set is empty the user is auto-calibrated
// (calibrated:true, required_subjects:[]). The "Update your starting point"
// edit affordance must NOT render — opening it would show an empty interstitial
// that hangs.
test("calibrated with an empty required set hides the update-starting-point affordance", async () => {
  primeApi({
    selfAssessment: () =>
      Promise.resolve({
        exam_id: EXAM_ID,
        calibrated: true,
        status: "completed",
        // needs_update would normally surface the banner, but with no editable
        // subjects there is nothing to update so it must stay hidden too.
        needs_update: true,
        required_subjects: [],
        items: [],
        attempts_used: 0,
      }),
  });

  await act(async () => {
    render(<StudyPlan />);
  });

  // Plan controls render (user is calibrated)…
  expect(await screen.findByTestId("regenerate-plan-btn")).toBeTruthy();
  // …but no edit affordance / update banner since there are no editable subjects.
  expect(screen.queryByTestId("calibration-edit-link")).toBeNull();
  expect(screen.queryByTestId("calibration-update-banner")).toBeNull();
  expect(screen.queryByTestId("calibration-update-btn")).toBeNull();
});
