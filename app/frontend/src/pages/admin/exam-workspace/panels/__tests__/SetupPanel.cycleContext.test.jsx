/**
 * SetupPanel — UX-EI-5 (D3): cycle context on inline date-editor rows (single canonical PhaseTimeline).
 *
 * For multi-cycle exams, each undated phase row now shows the cycle it
 * belongs to (cycle name + year) so operators don't have to mentally join
 * the phase name to its cycle.
 *
 * Regression guard:
 * - Single-cycle exam: cycle label appears.
 * - Multi-cycle exam: each phase shows its own cycle, not the active one.
 * - Phase with no matching cycle_id: gracefully absent (no crash, no label).
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

const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const SetupPanel = require("../SetupPanel").default;

const BASE_EXAM = { id: "exam-1", name: "UPSC CSE", slug: "upsc-cse" };

const CYCLE_2026 = { id: "cyc-2026", cycle_name: "2026 Cycle", year: 2026, status: "active" };
const CYCLE_2027 = { id: "cyc-2027", cycle_name: "2027 Cycle", year: 2027, status: "expected" };

// Phase stubs that trigger the inline date editor
function makePhase(id, name, cycleId, extraMeta = {}) {
  return {
    id,
    phase_name: name,
    phase_start: null,
    exam_cycle_id: cycleId,
    metadata: { phase_window: "TBD", ...extraMeta },
  };
}

describe("SetupPanel — UX-EI-5: cycle context on inline date-editor rows", () => {
  test("shows cycle name and year for a phase in a single cycle", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: [CYCLE_2026],
      phases: [makePhase("ph-1", "Prelims", "cyc-2026")],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);

    const cycleLabel = screen.getByTestId("phase-cycle-label-ph-1");
    expect(cycleLabel.textContent).toMatch(/2026 Cycle/);
    expect(cycleLabel.textContent).toMatch(/2026/);
  });

  test("multi-cycle: each phase shows its own cycle, not always the active one", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: [CYCLE_2026, CYCLE_2027],
      phases: [
        makePhase("ph-prelims-26", "Prelims 2026", "cyc-2026"),
        makePhase("ph-prelims-27", "Prelims 2027", "cyc-2027"),
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);

    expect(screen.getByTestId("phase-cycle-label-ph-prelims-26").textContent).toMatch(/2026 Cycle/);
    expect(screen.getByTestId("phase-cycle-label-ph-prelims-27").textContent).toMatch(/2027 Cycle/);
  });

  test("cycle label includes the year in parentheses", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: [CYCLE_2026],
      phases: [makePhase("ph-1", "Prelims", "cyc-2026")],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-cycle-label-ph-1").textContent).toMatch(/\(2026\)/);
  });

  test("phase with no matching cycle_id renders no cycle label (no crash)", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: [CYCLE_2026],
      phases: [
        // exam_cycle_id references a non-existent cycle
        { ...makePhase("ph-orphan", "Orphan Phase", "cyc-nonexistent") },
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);

    // Editor row still renders
    expect(screen.getByTestId("phase-date-editor-ph-orphan")).toBeTruthy();
    // But no cycle label since cycle can't be resolved
    expect(screen.queryByTestId("phase-cycle-label-ph-orphan")).toBeNull();
  });

  test("phase with no cycle_id renders no cycle label (graceful)", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: [CYCLE_2026],
      phases: [
        {
          id: "ph-nocycle",
          phase_name: "No Cycle Phase",
          phase_start: null,
          // no exam_cycle_id
          metadata: { phase_window: "TBD" },
        },
      ],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-date-editor-ph-nocycle")).toBeTruthy();
    expect(screen.queryByTestId("phase-cycle-label-ph-nocycle")).toBeNull();
  });

  test("phase name still appears alongside the cycle label", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: [CYCLE_2026],
      phases: [makePhase("ph-1", "Prelims", "cyc-2026")],
      refetch: jest.fn(),
    });
    render(<SetupPanel />);
    expect(screen.getAllByText("Prelims")[0]).toBeTruthy();
    expect(screen.getByTestId("phase-cycle-label-ph-1")).toBeTruthy();
  });
});
