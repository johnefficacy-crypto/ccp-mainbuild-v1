/**
 * PhaseTimeline component — unit tests (C2 / D3).
 *
 * Asserts:
 *  1. Phases with null start_date render with a "Needs date" badge.
 *  2. The cycle label (cycle_name + year) appears on date-missing rows (H3/UX-EI-5).
 *  3. Phases with a start_date do NOT get the badge or cycle label.
 *  4. Empty phases list renders the "No phases defined" empty state.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

// Minimal mock for dateFormat — the formatting path is not the focus here.
jest.mock("../../../../../shared/forms/dateFormat", () => ({
  __esModule: true,
  formatDDMMYYYY: (d) => d,
}));

const PhaseTimeline = require("../PhaseTimeline").default;

const CYCLE_2026 = { id: "cyc-1", cycle_name: "Main", year: 2026 };
const CYCLE_2027 = { id: "cyc-2", cycle_name: "Prelim", year: 2027 };

describe("PhaseTimeline — needs-date badge", () => {
  test("renders 'Needs date' badge for a phase with null phase_start and legacy window", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-1",
            phase_name: "Prelims",
            phase_start: null,
            phase_end: null,
            status: "expected",
            metadata: { phase_window: "TBD" },
          },
        ]}
        cycles={[CYCLE_2026]}
      />
    );
    expect(screen.getByTestId("phase-needs-date-badge-ph-1")).toBeTruthy();
    expect(screen.getByTestId("phase-needs-date-badge-ph-1").textContent).toBe("Needs date");
  });

  test("renders 'Needs date' badge for a phase with needs_phase_date_authoring flag", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-2",
            phase_name: "Mains",
            phase_start: null,
            phase_end: null,
            status: "expected",
            metadata: { needs_phase_date_authoring: true },
          },
        ]}
        cycles={[CYCLE_2026]}
      />
    );
    expect(screen.getByTestId("phase-needs-date-badge-ph-2")).toBeTruthy();
  });

  test("renders 'Needs date' badge for a workbook-imported stub phase", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-import",
            phase_name: "Tier I",
            phase_start: null,
            phase_end: null,
            status: "expected",
            metadata: {
              import_source: "exam_registry_workbook",
              needs_phase_date_authoring: true,
            },
          },
        ]}
        cycles={[CYCLE_2026]}
      />
    );
    expect(screen.getByTestId("phase-needs-date-badge-ph-import")).toBeTruthy();
  });

  test("does NOT render badge when phase_start is set", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-dated",
            phase_name: "Prelims",
            phase_start: "2026-05-24",
            phase_end: null,
            status: "active",
            metadata: {},
          },
        ]}
        cycles={[CYCLE_2026]}
      />
    );
    expect(screen.queryByTestId("phase-needs-date-badge-ph-dated")).toBeNull();
  });
});

describe("PhaseTimeline — cycle label (H3 / UX-EI-5)", () => {
  test("renders cycle label on date-missing phase when cycle matches", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-1",
            phase_name: "Prelims",
            phase_start: null,
            phase_end: null,
            exam_cycle_id: "cyc-1",
            status: "expected",
            metadata: { phase_window: "TBD" },
          },
        ]}
        cycles={[CYCLE_2026]}
      />
    );
    const label = screen.getByTestId("phase-cycle-label-ph-1");
    expect(label).toBeTruthy();
    expect(label.textContent).toBe("Main (2026)");
  });

  test("renders cycle label without year when cycle has no year", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-1",
            phase_name: "Prelims",
            phase_start: null,
            phase_end: null,
            exam_cycle_id: "cyc-no-year",
            status: "expected",
            metadata: { phase_window: "TBD" },
          },
        ]}
        cycles={[{ id: "cyc-no-year", cycle_name: "Special", year: null }]}
      />
    );
    const label = screen.getByTestId("phase-cycle-label-ph-1");
    expect(label.textContent).toBe("Special");
  });

  test("silently omits cycle label when phase has no exam_cycle_id", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-template",
            phase_name: "Generic",
            phase_start: null,
            phase_end: null,
            exam_cycle_id: null,
            status: "expected",
            metadata: { needs_phase_date_authoring: true },
          },
        ]}
        cycles={[CYCLE_2026]}
      />
    );
    // Badge is shown, but no cycle label since no cycle_id
    expect(screen.getByTestId("phase-needs-date-badge-ph-template")).toBeTruthy();
    expect(screen.queryByTestId("phase-cycle-label-ph-template")).toBeNull();
  });

  test("does NOT render cycle label on phases that already have dates", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-dated",
            phase_name: "Prelims",
            phase_start: "2026-05-24",
            phase_end: null,
            exam_cycle_id: "cyc-1",
            status: "active",
            metadata: {},
          },
        ]}
        cycles={[CYCLE_2026]}
      />
    );
    expect(screen.queryByTestId("phase-cycle-label-ph-dated")).toBeNull();
  });

  test("each phase resolves its own cycle label independently", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-a",
            phase_name: "Prelims",
            phase_start: null,
            exam_cycle_id: "cyc-1",
            status: "expected",
            metadata: { phase_window: "TBD" },
          },
          {
            id: "ph-b",
            phase_name: "Mains",
            phase_start: null,
            exam_cycle_id: "cyc-2",
            status: "expected",
            metadata: { phase_window: "TBD" },
          },
        ]}
        cycles={[CYCLE_2026, CYCLE_2027]}
      />
    );
    expect(screen.getByTestId("phase-cycle-label-ph-a").textContent).toBe("Main (2026)");
    expect(screen.getByTestId("phase-cycle-label-ph-b").textContent).toBe("Prelim (2027)");
  });
});

describe("PhaseTimeline — empty state and general rendering", () => {
  test("renders empty state when phases array is empty", () => {
    render(<PhaseTimeline phases={[]} cycles={[CYCLE_2026]} />);
    expect(screen.getByText("No phases defined")).toBeTruthy();
    expect(screen.queryByTestId("phase-timeline")).toBeNull();
  });

  test("renders phase-timeline data-testid when phases exist", () => {
    render(
      <PhaseTimeline
        phases={[
          {
            id: "ph-1",
            phase_name: "Prelims",
            phase_start: "2026-05-24",
            status: "active",
            metadata: {},
          },
        ]}
        cycles={[]}
      />
    );
    expect(screen.getByTestId("phase-timeline")).toBeTruthy();
  });

  test("renders phase row testid for each phase", () => {
    render(
      <PhaseTimeline
        phases={[
          { id: "ph-x", phase_name: "X", phase_start: "2026-01-01", status: "active", metadata: {} },
          { id: "ph-y", phase_name: "Y", phase_start: null, status: "expected", metadata: { phase_window: "TBD" } },
        ]}
        cycles={[]}
      />
    );
    expect(screen.getByTestId("phase-timeline-row-ph-x")).toBeTruthy();
    expect(screen.getByTestId("phase-timeline-row-ph-y")).toBeTruthy();
  });
});
