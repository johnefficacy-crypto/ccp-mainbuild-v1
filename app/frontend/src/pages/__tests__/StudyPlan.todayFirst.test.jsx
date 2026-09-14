/**
 * PLAN-UI-03 — the plan page's subject is today.
 *
 * The page used to open with a cycle console: a planned-vs-actual curve, a
 * progress rail, phase bands, per-subject bars and a metric strip reading
 * "planned 62% · actual 0% · plan v9 · planner_v1". Today's blocks sat below
 * all of it. These tests pin the new order, the collapse, and the rule that
 * decides what the honest-state panel is allowed to say.
 */
import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

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

jest.mock("../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({ run: jest.fn(), busy: false }),
}));

// eslint-disable-next-line import/first
import StudyPlan from "../StudyPlan";

const EXAM_ID = "11111111-1111-4111-8111-111111111111";

const TIMELINE = {
  exam_context: {
    exam_name: "UPSC CSE",
    phase: "mains",
    days_remaining: 47,
    exam_start: "2026-10-31",
  },
  plan_context: { plan_version: 9, planner_version: "planner_v1" },
  cycle_progress: {
    status: "on_track",
    planned_progress_pct: 62,
    actual_progress_pct: 0,
    total_days: 120,
    elapsed_days: 73,
  },
  milestones: [
    { kind: "notification", date: "2026-02-01", label: "Notification" },
    { kind: "today", date: "2026-09-14", label: "Today" },
    { kind: "exam", date: "2026-10-31", label: "Exam day" },
  ],
  phase_bands: [
    { name: "Revision", start: "2026-08-01", end: "2026-10-01" },
    { name: "Final sprint", start: "2026-10-01", end: "2026-10-31" },
  ],
  series: [],
  subjects: [],
  risk_flags: [
    {
      code: "subject_behind",
      label: "Polity is behind",
      severity: "medium",
      reason: "Polity has had no completed blocks for eleven days.",
      suggested_action: "Put two Polity blocks on tomorrow.",
    },
  ],
  regen_triggers: [],
};

function task(id, topic) {
  return {
    id,
    title: `${topic} · Study`,
    topic,
    task_type: "concept",
    status: "planned",
    planned_minutes: 45,
    scheduled_date: "2026-09-14",
  };
}

function wire({ tasks = [task("t1", "Percentage")], review = null, timeline = TIMELINE } = {}) {
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan")
      return Promise.resolve({ plan: { id: "p1", theme: "Adaptive weekly plan", day: 4 }, tasks });
    if (path === "/api/study/plan/timeline") return Promise.resolve(timeline);
    if (path === "/api/study/focus/summary")
      return Promise.resolve({ total_hours_7d: 3, week: [{ label: "Mon", hrs: 1.5 }] });
    if (path === "/api/study/weekly-review") return Promise.resolve(review);
    if (path === "/api/study/exams")
      return Promise.resolve({ items: [{ id: EXAM_ID, name: "UPSC CSE", planner_ready: true }] });
    if (path === "/api/study/target-exam")
      return Promise.resolve({ selected_exam: { id: EXAM_ID, name: "UPSC CSE", is_active: true } });
    if (path === "/api/study/tracked-exams") return Promise.resolve({ items: [] });
    if (path.startsWith("/api/study/calibration")) return Promise.resolve({ calibrated: true, items: [] });
    return Promise.resolve({});
  });
}

async function renderPage(opts) {
  wire(opts);
  const utils = render(<StudyPlan />);
  await waitFor(() => expect(screen.getByTestId("cycle-countdown")).toBeInTheDocument());
  return utils;
}

beforeEach(() => {
  jest.clearAllMocks();
});

// ── 1. the page's subject, written first ────────────────────────────────

test("today's blocks are the first substantive content after the countdown", async () => {
  const { container } = await renderPage();

  const countdown = screen.getByTestId("cycle-countdown");
  const today = screen.getByTestId("today-section");
  expect(
    countdown.compareDocumentPosition(today) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();

  // Nothing from the old cycle console sits between them: no planned-vs-actual
  // chart, no progress rail, no per-subject bars.
  expect(screen.queryByTestId("exam-cycle-timeline")).not.toBeInTheDocument();
  expect(container.textContent).toContain("1 block today");
});

test("the day's total planned time is beside the block count", async () => {
  await renderPage({ tasks: [task("t1", "Percentage"), task("t2", "Ratios")] });
  expect(screen.getByTestId("today-section").textContent).toContain("2 blocks today");
  expect(screen.getByTestId("today-section").textContent).toContain("1h 30m");
});

// ── 2. the countdown, collapsed, expanding in place ─────────────────────

test("the countdown is one line until it is clicked, then the dates open in place", async () => {
  await renderPage();

  const toggle = screen.getByTestId("cycle-countdown-toggle");
  expect(toggle.textContent).toContain("Mains · 47 days");
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByTestId("cycle-countdown-detail")).not.toBeInTheDocument();

  fireEvent.click(toggle);

  expect(toggle).toHaveAttribute("aria-expanded", "true");
  const detail = screen.getByTestId("cycle-countdown-detail");
  expect(detail.textContent).toContain("Exam day");
  // In place: still inside the countdown, no navigation.
  expect(screen.getByTestId("cycle-countdown")).toContainElement(detail);
});

test("no exam date means no countdown line at all", async () => {
  wire({ timeline: { ...TIMELINE, exam_context: { exam_name: "UPSC CSE" } } });
  render(<StudyPlan />);
  await waitFor(() => expect(screen.getByTestId("today-section")).toBeInTheDocument());
  expect(screen.queryByTestId("cycle-countdown")).not.toBeInTheDocument();
});

// ── 3 & 4. honest state: real values only ───────────────────────────────

test("the honest-state panel shows only the fields that carry a real value", async () => {
  await renderPage({
    review: {
      hours_studied: 6,
      hours_planned: 10,
      tasks_completed: 8,
      tasks_planned: 12,
      mocks_taken: 0,
      mock_trend: [],
      backlog_end: 3,
      revision_coverage: null,
      corrections: [],
    },
  });

  const panel = screen.getByTestId("week-truth");
  expect(within(panel).getByTestId("week-truth-blocks").textContent).toBe(
    "You finished 8 of 12 blocks this week.",
  );
  expect(within(panel).getByTestId("week-truth-backlog").textContent).toContain(
    "3 blocks from earlier days",
  );
  // Absent, not rendered as a zero or as "Not available yet".
  expect(screen.queryByTestId("week-truth-revision")).not.toBeInTheDocument();
  expect(screen.queryByTestId("week-truth-mocks")).not.toBeInTheDocument();
  expect(panel.textContent).not.toContain("Not available yet");
  expect(panel.textContent).not.toContain("No backlog");
});

test("when nothing real is known the panel does not render at all", async () => {
  await renderPage({
    review: { hours_studied: 0, tasks_planned: 0, mocks_taken: 0, mock_trend: [], corrections: [] },
  });
  expect(screen.queryByTestId("week-truth")).not.toBeInTheDocument();
});

test("a missing weekly review is the same as nothing real to say", async () => {
  await renderPage({ review: null });
  expect(screen.queryByTestId("week-truth")).not.toBeInTheDocument();
});

// ── 5. the removed vocabulary ───────────────────────────────────────────

test("none of the operator vocabulary survives on the page", async () => {
  const { container } = await renderPage({
    review: {
      hours_studied: 6,
      hours_planned: 10,
      tasks_completed: 8,
      tasks_planned: 12,
      backlog_end: 2,
      revision_coverage: 0.5,
      mocks_taken: 1,
      mock_trend: [{ id: "m1", percentage: 61 }],
      corrections: ["Polity slipped this week."],
    },
  });
  fireEvent.click(screen.getByTestId("cycle-countdown-toggle"));

  for (const banned of [
    "planner_v1",
    "SOURCE CONTRACT",
    "Source contract",
    "plan v9",
    "telemetry",
    "Telemetry",
    "adherence",
    "Adherence",
    "severity",
    "EXAM INTELLIGENCE",
    "WEAKNESS MAP",
    "planned 62%",
  ]) {
    expect(container.textContent).not.toContain(banned);
  }
});

// ── 6. risk flags as sentences ──────────────────────────────────────────

test("risk flags read as sentences with their action, and carry no severity chip", async () => {
  await renderPage();

  const notes = screen.getByTestId("plan-risk-notes");
  expect(notes.textContent).toContain("Polity has had no completed blocks for eleven days.");
  expect(notes.textContent).toContain("Put two Polity blocks on tomorrow.");
  expect(notes.textContent).not.toContain("medium");
  expect(notes.textContent).not.toContain("Suggested");
});

test("nothing flagged renders nothing, not a reassurance card", async () => {
  await renderPage({ timeline: { ...TIMELINE, risk_flags: [] } });
  expect(screen.queryByTestId("plan-risk-notes")).not.toBeInTheDocument();
});

// ── subject breakdown is behind a click, not gone ───────────────────────

test("this week by subject is one click away rather than always open", async () => {
  await renderPage();
  const toggle = screen.getByTestId("subjects-toggle");
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "true");
});
