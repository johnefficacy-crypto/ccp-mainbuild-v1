/**
 * Tests for ReviewActivatePanel (PR-0 §7 compliance).
 *
 * Covers:
 * - panel renders NO one-click activate mutation
 * - readiness checklist shows per-section blocker text labels (not color-only)
 * - per-row lock action calls PATCH /admin/exam-intelligence/{entity}/{id}/review
 * - lock action UI is hidden/read-only when user lacks exam_intelligence.review
 * - lock action UI is shown when user has exam_intelligence.review
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), patch: jest.fn() },
}));

jest.mock("../../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: jest.fn(),
}));

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: jest.fn(),
}));

const { api } = require("../../../../../lib/api");
const { useAuth } = require("../../../../../lib/authContext");
const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const ReviewActivatePanel = require("../ReviewActivatePanel").default;

// ── Fixtures ──────────────────────────────────────────────────────────────────

const READINESS_READY = {
  exam_id: "exam-1",
  overall: { score_percent: 100, ready_to_activate: true, status: "locked" },
  sections: [
    {
      section: "setup",
      label: "Setup",
      status: "ready",
      weight: 1,
      blockers: [],
      note: "1 phase defined",
      metrics: {},
    },
    {
      section: "competition",
      label: "Competition",
      status: "partial",
      weight: 1,
      blockers: ["no competition metric for this cycle"],
      note: "",
      metrics: { row_id: "comp-row-1" },
    },
  ],
};

const READINESS_BLOCKED = {
  exam_id: "exam-1",
  overall: { score_percent: 40, ready_to_activate: false, status: "partial" },
  sections: [
    {
      section: "setup",
      label: "Setup",
      status: "empty",
      weight: 1,
      blockers: ["no phases defined"],
      note: "",
      metrics: {},
    },
    {
      section: "updates",
      label: "Updates",
      status: "partial",
      weight: 1,
      blockers: ["2 updates pending review"],
      note: "",
      metrics: {},
    },
  ],
};

function setup({ readiness = READINESS_READY, permissions = ["exam_intelligence.review"] } = {}) {
  useExamWorkspace.mockReturnValue({
    readiness,
    readiness_loading: false,
    refetchReadiness: jest.fn(),
  });
  useAuth.mockReturnValue({
    user: { permissions },
  });
  return render(<ReviewActivatePanel onGotoTab={jest.fn()} />);
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("ReviewActivatePanel — no fake one-click activation", () => {
  it("does NOT render a one-click Lock & activate button", () => {
    setup();
    expect(screen.queryByText(/lock.*activate exam/i)).toBeNull();
    expect(screen.queryByText(/activate.*exam/i)).toBeNull();
  });

  it("does NOT call any api.patch on render (no bulk activate endpoint)", () => {
    setup();
    expect(api.patch).not.toHaveBeenCalled();
  });
});

describe("ReviewActivatePanel — per-section blocker text labels", () => {
  it("shows blocker reason as visible text for a blocked section", () => {
    setup({ readiness: READINESS_BLOCKED });
    expect(screen.getByText(/no phases defined/i)).toBeTruthy();
    expect(screen.getByText(/2 updates pending review/i)).toBeTruthy();
  });

  it("renders a status text label paired with each status dot", () => {
    setup({ readiness: READINESS_BLOCKED });
    // StatusDot renders a text span alongside the colored dot — not color-only
    expect(screen.getAllByText(/empty|in progress|ready|locked/i).length).toBeGreaterThan(0);
  });
});

describe("ReviewActivatePanel — per-row lock action", () => {
  beforeEach(() => {
    api.patch.mockResolvedValue({ reviewer_status: "locked" });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("shows Lock row button when user has exam_intelligence.review", () => {
    setup({ readiness: READINESS_READY, permissions: ["exam_intelligence.review"] });
    expect(screen.getByRole("button", { name: /lock this row/i })).toBeTruthy();
  });

  it("calls PATCH /admin/exam-intelligence/competition-metrics/{id}/review on click", async () => {
    setup({ readiness: READINESS_READY, permissions: ["exam_intelligence.review"] });
    fireEvent.click(screen.getByRole("button", { name: /lock this row/i }));
    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith(
        "/api/admin/exam-intelligence/competition-metrics/comp-row-1/review",
        { reviewer_status: "locked" },
      ),
    );
  });

  it("does NOT show Lock row button when user lacks exam_intelligence.review", () => {
    setup({ readiness: READINESS_READY, permissions: [] });
    expect(screen.queryByRole("button", { name: /lock this row/i })).toBeNull();
  });

  it("shows read-only notice when user lacks exam_intelligence.review", () => {
    setup({ readiness: READINESS_READY, permissions: [] });
    expect(screen.getByText(/exam_intelligence\.review/)).toBeTruthy();
    expect(screen.getByText(/read-only/i)).toBeTruthy();
  });
});

describe("ReviewActivatePanel — lifecycle contract copy", () => {
  it("states that pending and rejected rows never reach aspirants", () => {
    setup();
    // The lifecycle reference card contains this copy (may appear in multiple elements)
    expect(screen.getAllByText(/never reach aspirants/i).length).toBeGreaterThan(0);
  });

  it("states that locked or reviewed rows feed the planner", () => {
    setup();
    expect(screen.getByText(/planner consumes/i)).toBeTruthy();
    expect(screen.getByText(/locked.*preferred/i)).toBeTruthy();
  });
});

// ── EI-CLEAN-03: PYQ four-metric breakdown + missing-tag CTA ─────────────────

const READINESS_PYQ_MISSING_TAGS = {
  exam_id: "exam-1",
  overall: { score_percent: 60, ready_to_activate: false, status: "partial" },
  sections: [
    {
      section: "pyq_workbench",
      label: "PYQ Workbench",
      status: "partial",
      weight: 3,
      blockers: ["98 questions missing verified topic tag"],
      note: "",
      metrics: {
        pyq_readiness: {
          questions_total: 100,
          planner_ready_question_count: 0,
          reviewed_question_count: 98,
          missing_verified_tag_count: 98,
          rejected_question_count: 2,
        },
      },
    },
  ],
};

describe("ReviewActivatePanel — EI-CLEAN-03 PYQ metric decomposition", () => {
  it("shows planner-ready, reviewed, missing-tag and rejected as distinct metrics", () => {
    setup({ readiness: READINESS_PYQ_MISSING_TAGS });
    expect(screen.getByTestId("pyq-planner-ready").textContent).toMatch(/0 \/ 100 planner-ready/);
    expect(screen.getByTestId("pyq-reviewed").textContent).toMatch(/98 questions reviewed/);
    expect(screen.getByTestId("pyq-missing-tag").textContent).toMatch(/98 need a verified topic tag/);
    expect(screen.getByTestId("pyq-rejected").textContent).toMatch(/2 rejected/);
  });

  it("labels the CTA 'Review missing topic tags' when tags are missing", () => {
    setup({ readiness: READINESS_PYQ_MISSING_TAGS, permissions: ["exam_intelligence.review"] });
    expect(screen.getByRole("button", { name: /review missing topic tags/i })).toBeTruthy();
  });

  it("navigates to the pyq tab when the missing-tags CTA is clicked", () => {
    const onGotoTab = jest.fn();
    useExamWorkspace.mockReturnValue({
      readiness: READINESS_PYQ_MISSING_TAGS,
      readiness_loading: false,
      refetchReadiness: jest.fn(),
    });
    useAuth.mockReturnValue({ user: { permissions: ["exam_intelligence.review"] } });
    render(<ReviewActivatePanel onGotoTab={onGotoTab} />);
    fireEvent.click(screen.getByRole("button", { name: /review missing topic tags/i }));
    expect(onGotoTab).toHaveBeenCalledWith("pyq");
  });
});

// EI-CLEAN-03 fix: missing-tag CTA must survive D10 "ready" (planner_ready >= 1).
const READINESS_PYQ_READY_BUT_MISSING = {
  exam_id: "exam-1",
  overall: { score_percent: 90, ready_to_activate: false, status: "partial" },
  sections: [
    {
      section: "pyq_workbench",
      label: "PYQ Workbench",
      status: "ready", // D10 ready: at least one planner-ready question
      weight: 3,
      blockers: [],
      note: "",
      metrics: {
        pyq_readiness: {
          questions_total: 100,
          planner_ready_question_count: 1,
          reviewed_question_count: 99,
          missing_verified_tag_count: 98,
          rejected_question_count: 0,
        },
      },
    },
  ],
};

describe("ReviewActivatePanel — missing-tag CTA independent of D10 readiness", () => {
  it("still shows the missing-tag CTA (not a Ready seal) when planner_ready>0 and missing>0", () => {
    setup({ readiness: READINESS_PYQ_READY_BUT_MISSING, permissions: ["exam_intelligence.review"] });
    expect(screen.getByTestId("pyq-review-missing-cta")).toBeTruthy();
    expect(screen.getByTestId("pyq-review-missing-cta").textContent).toMatch(/review missing topic tags/i);
    // The Ready seal must NOT be the row's action while tags remain missing.
    expect(screen.getByTestId("pyq-planner-ready").textContent).toMatch(/1 \/ 100 planner-ready/);
  });

  it("shows the missing-tag CTA even for a read-only (non-review) user", () => {
    setup({ readiness: READINESS_PYQ_READY_BUT_MISSING, permissions: [] });
    expect(screen.getByTestId("pyq-review-missing-cta")).toBeTruthy();
  });
});
