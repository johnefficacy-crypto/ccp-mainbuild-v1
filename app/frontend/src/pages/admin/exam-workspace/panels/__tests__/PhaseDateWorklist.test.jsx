/**
 * D3 / C2 regression tests — "Phases needing dates" standalone section removed.
 *
 * After the D3 fix the standalone "Phases needing dates" card is gone from
 * SetupPanel. Missing-date phases are now flagged inline inside PhaseTimeline
 * via a "Needs date" badge and cycle label.
 *
 * These tests assert:
 *  1. The phase-date-worklist card is NO LONGER rendered by SetupPanel.
 *  2. SetupPanel still renders the main PhaseTimeline (the phases section).
 *  3. Phases with missing dates appear with "Needs date" badges in the timeline.
 *  4. The cycle label from H3 (UX-EI-5) is shown in the timeline for cycle-bound
 *     missing-date phases.
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
  default: () => ({
    run: jest.fn(async ({ action, onSuccess }) => {
      const result = await action();
      if (onSuccess) onSuccess(result);
      return { ok: true, data: result };
    }),
    busy: false,
  }),
}));

jest.mock("../../../../../shared/forms/dateFormat", () => ({
  __esModule: true,
  formatDDMMYYYY: (d) => d,
}));

const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const SetupPanel = require("../SetupPanel").default;

const BASE_EXAM = { id: "exam-1", name: "UPSC CSE", slug: "upsc-cse" };
const BASE_CYCLES = [{ id: "cyc-1", status: "active", cycle_name: "2026", year: 2026 }];

beforeEach(() => {
  jest.clearAllMocks();
  const { api } = require("../../../../../lib/api");
  api.patch.mockResolvedValue({ ok: true });
});

// ── D3: standalone worklist card is gone ─────────────────────────────────────

describe("D3 regression: 'Phases needing dates' standalone section removed", () => {
  test("phase-date-worklist card is NOT rendered when phases have missing dates", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        {
          id: "ph-1",
          phase_name: "Prelims",
          phase_start: null,
          metadata: { phase_window: "TBD" },
        },
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("phase-date-worklist")).toBeNull();
  });

  test("'Phases needing dates' heading is NOT rendered", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        {
          id: "ph-1",
          phase_name: "Prelims",
          phase_start: null,
          metadata: { needs_phase_date_authoring: true },
        },
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    expect(screen.queryByText("Phases needing dates")).toBeNull();
  });

  test("phase-date-worklist card is NOT rendered even with no missing-date phases", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        {
          id: "ph-1",
          phase_name: "Prelims",
          phase_start: "2026-05-24",
          metadata: {},
        },
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("phase-date-worklist")).toBeNull();
  });
});

// ── PhaseTimeline still rendered ──────────────────────────────────────────────

describe("SetupPanel still renders PhaseTimeline", () => {
  test("phase-timeline is rendered when phases exist", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        {
          id: "ph-1",
          phase_name: "Prelims",
          phase_start: "2026-05-24",
          status: "active",
          metadata: {},
        },
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-timeline")).toBeTruthy();
  });

  test("PhaseTimeline shows 'Needs date' badge for missing-date phase", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        {
          id: "ph-missing",
          phase_name: "Prelims",
          phase_start: null,
          exam_cycle_id: "cyc-1",
          status: "expected",
          metadata: { phase_window: "TBD" },
        },
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-needs-date-badge-ph-missing")).toBeTruthy();
    expect(screen.getByTestId("phase-needs-date-badge-ph-missing").textContent).toBe("Needs date");
  });

  test("PhaseTimeline shows cycle label for missing-date phase bound to a cycle (H3/UX-EI-5)", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        {
          id: "ph-missing",
          phase_name: "Prelims",
          phase_start: null,
          exam_cycle_id: "cyc-1",
          status: "expected",
          metadata: { phase_window: "TBD" },
        },
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    const label = screen.getByTestId("phase-cycle-label-ph-missing");
    expect(label).toBeTruthy();
    expect(label.textContent).toBe("2026 (2026)");
  });

  test("PhaseTimeline does NOT show badge for phase that already has dates", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        {
          id: "ph-dated",
          phase_name: "Prelims",
          phase_start: "2026-05-24",
          status: "active",
          metadata: {},
        },
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("phase-needs-date-badge-ph-dated")).toBeNull();
  });
});
