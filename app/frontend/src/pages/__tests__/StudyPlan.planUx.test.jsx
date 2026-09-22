/**
 * PLAN-UX-01 — the page must not promise more control than it has.
 *
 * Two things were untrue before this. "Apply selected changes" named a
 * per-change selection control that does not exist, and "Nothing changes
 * until you preview and approve it." is false whenever auto_regenerate is on,
 * because regen.py's nightly sweep calls generate_plan directly with no draft
 * and no approval.
 */
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
  default: () => ({ run: jest.fn(async () => ({ ok: true })) }),
}));

import StudyPlan, { planHeaderSub, isAutoRefreshedToday } from "../StudyPlan";

const EXAM_ID = "11111111-1111-4111-8111-111111111111";

function primeGet({ autoRegenerate = true, lastRefresh = null, prefsFail = false } = {}) {
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === "/api/study/plan") {
      return Promise.resolve({
        plan: { id: "p1", theme: "Adaptive weekly plan", last_refresh: lastRefresh },
        tasks: [],
      });
    }
    if (path === "/api/study/plan/preferences") {
      return prefsFail
        ? Promise.reject(new Error("boom"))
        : Promise.resolve({ auto_regenerate: autoRegenerate });
    }
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
      return Promise.resolve({
        exam_id: EXAM_ID, calibrated: true, status: "completed",
        needs_update: false, required_subjects: [], items: [], attempts_used: 0,
      });
    }
    if (path === "/api/study/plan/draft") {
      return Promise.resolve({
        generated: true, exam_name: "SSC CGL", risk_level: "low",
        before_tasks: [], after_tasks: [{ topic_id: "t1", title: "Quant · Number Systems" }],
        changes: { added: [], removed: [], added_count: 1, removed_count: 0, unchanged_count: 0 },
      });
    }
    return Promise.resolve({});
  });
}

afterEach(() => {
  [mockGet, mockPost, mockPut, mockDel].forEach((m) => m.mockReset());
});

// ── the pure helpers ───────────────────────────────────────────────────────

describe("planHeaderSub", () => {
  test("auto_regenerate on says the nightly refresh happens", () => {
    expect(planHeaderSub(true)).toBe(
      "We refresh today's tasks each night. Tasks you've arranged stay put.",
    );
  });

  test("auto_regenerate off keeps the apply promise, which is true there", () => {
    expect(planHeaderSub(false)).toBe("Nothing changes until you preview and apply it.");
  });

  test("unknown preferences make neither claim", () => {
    // A failed or in-flight read must not pick a side — both specific strings
    // are wrong half the time.
    for (const v of [null, undefined]) {
      expect(planHeaderSub(v)).toBe("Preview a plan before you apply it.");
      expect(planHeaderSub(v)).not.toMatch(/each night|Nothing changes/);
    }
  });
});

describe("isAutoRefreshedToday", () => {
  const now = new Date("2026-09-22T09:00:00Z");

  test("true only for a scheduled trigger dated today (UTC)", () => {
    expect(isAutoRefreshedToday({ trigger: "scheduled", at: "2026-09-22T02:05:00Z" }, now)).toBe(true);
  });

  test("false for a user apply, even today", () => {
    expect(isAutoRefreshedToday({ trigger: "manual", at: "2026-09-22T02:05:00Z" }, now)).toBe(false);
  });

  test("false for the sweep yesterday", () => {
    expect(isAutoRefreshedToday({ trigger: "scheduled", at: "2026-09-21T23:59:00Z" }, now)).toBe(false);
  });

  test("false when the field is absent, empty or malformed", () => {
    expect(isAutoRefreshedToday(null, now)).toBe(false);
    expect(isAutoRefreshedToday({}, now)).toBe(false);
    expect(isAutoRefreshedToday({ trigger: "scheduled" }, now)).toBe(false);
    expect(isAutoRefreshedToday({ trigger: "scheduled", at: "not-a-date" }, now)).toBe(false);
  });
});

// ── rendered behaviour ─────────────────────────────────────────────────────

describe("header copy switches on auto_regenerate", () => {
  test("on → the nightly-refresh line", async () => {
    primeGet({ autoRegenerate: true });
    await act(async () => { render(<StudyPlan />); });
    await waitFor(() =>
      expect(screen.getByText(/We refresh today's tasks each night/)).toBeInTheDocument(),
    );
    expect(screen.queryByText(/Nothing changes until you preview/)).not.toBeInTheDocument();
  });

  test("off → the apply promise", async () => {
    primeGet({ autoRegenerate: false });
    await act(async () => { render(<StudyPlan />); });
    await waitFor(() =>
      expect(
        screen.getByText("Nothing changes until you preview and apply it."),
      ).toBeInTheDocument(),
    );
  });

  test("a failed preferences read falls back to the neutral line", async () => {
    primeGet({ prefsFail: true });
    await act(async () => { render(<StudyPlan />); });
    await waitFor(() =>
      expect(screen.getByText("Preview a plan before you apply it.")).toBeInTheDocument(),
    );
  });
});

describe("auto-refresh notice", () => {
  const todayIso = () => `${new Date().toISOString().slice(0, 10)}T02:05:00Z`;

  test("shows for a sweep-triggered version dated today, with role=status", async () => {
    primeGet({ lastRefresh: { trigger: "scheduled", at: todayIso() } });
    await act(async () => { render(<StudyPlan />); });
    const notice = await screen.findByTestId("auto-refresh-notice");
    expect(notice).toHaveAttribute("role", "status");
    expect(notice).toHaveTextContent("Auto-refreshed today");
    expect(notice).toHaveTextContent("arranged tasks kept");
    expect(screen.getByTestId("auto-refresh-notice-link")).toHaveTextContent("See plan changes");
  });

  test("hidden for a user apply", async () => {
    primeGet({ lastRefresh: { trigger: "manual", at: todayIso() } });
    await act(async () => { render(<StudyPlan />); });
    await waitFor(() => expect(screen.getByTestId("study-plan-page")).toBeInTheDocument());
    expect(screen.queryByTestId("auto-refresh-notice")).not.toBeInTheDocument();
  });

  test("hidden for yesterday's sweep", async () => {
    const y = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    primeGet({ lastRefresh: { trigger: "scheduled", at: `${y}T23:00:00Z` } });
    await act(async () => { render(<StudyPlan />); });
    await waitFor(() => expect(screen.getByTestId("study-plan-page")).toBeInTheDocument());
    expect(screen.queryByTestId("auto-refresh-notice")).not.toBeInTheDocument();
  });

  test("hidden when the backend omits last_refresh entirely", async () => {
    primeGet({ lastRefresh: null });
    await act(async () => { render(<StudyPlan />); });
    await waitFor(() => expect(screen.getByTestId("study-plan-page")).toBeInTheDocument());
    expect(screen.queryByTestId("auto-refresh-notice")).not.toBeInTheDocument();
  });
});

describe("Keep current plan", () => {
  async function openDrawer() {
    await act(async () => { render(<StudyPlan />); });
    const regen = await screen.findByTestId("regenerate-plan-btn");
    await act(async () => { fireEvent.click(regen); });
    return screen.findByTestId("keep-current-plan-btn");
  }

  test("closes the drawer and makes no request", async () => {
    primeGet();
    const keep = await openDrawer();
    expect(keep.tagName).toBe("BUTTON");
    expect(keep).toHaveTextContent("Keep current plan");

    const getsBefore = mockGet.mock.calls.length;
    await act(async () => { fireEvent.click(keep); });

    await waitFor(() =>
      expect(screen.queryByTestId("apply-draft-btn")).not.toBeInTheDocument(),
    );
    // No write, and no extra read either — keeping the current plan is a
    // pure client-side dismissal.
    expect(mockPost).not.toHaveBeenCalled();
    expect(mockPut).not.toHaveBeenCalled();
    expect(mockDel).not.toHaveBeenCalled();
    expect(mockGet.mock.calls.length).toBe(getsBefore);
  });

  test("sits beside the relabelled apply button", async () => {
    primeGet();
    await openDrawer();
    expect(screen.getByTestId("apply-draft-btn")).toHaveTextContent("Apply this plan");
    expect(screen.getByTestId("apply-draft-btn")).not.toHaveTextContent("selected");
  });
});
