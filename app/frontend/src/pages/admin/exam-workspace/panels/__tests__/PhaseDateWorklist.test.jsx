/**
 * Tests for inline phase-date authoring in SetupPanel (EI-CLEAN-07).
 *
 * The standalone "Phases needing dates" card was removed (it was a filtered
 * duplicate of the main phase list — the D3 regression). Date authoring now
 * happens inline on the single canonical PhaseTimeline: a phase missing a
 * structured start date shows a "Needs date" badge and an inline date editor
 * (start/end + Set dates) on its own row.
 *
 * The needs-date signal is still keyed off phase_start IS NULL plus an explicit
 * authoring signal (legacy phase_window, workbook import_source, or
 * needs_phase_date_authoring). It must NOT key off phase_window_needs_review
 * (regression guard for the 165 flag hole where TBD rows were neither dated
 * nor flagged).
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
}));

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: jest.fn(),
}));

// SetupPanel routes mutations through useApiAction. Mock it so tests never need
// a ToastProvider context — mirrors Organizations.create.test.jsx.
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

const { api } = require("../../../../../lib/api");
const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const SetupPanel = require("../SetupPanel").default;

const BASE_EXAM = { id: "exam-1", name: "UPSC CSE", slug: "upsc-cse" };
const BASE_CYCLES = [{ id: "cyc-1", status: "active", cycle_name: "2026" }];

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.patch.mockReset();
  api.patch.mockResolvedValue({ ok: true });
});

// ── inline date-editor visibility ────────────────────────────────────────────

describe("inline date-editor visibility", () => {
  test("shows an inline date editor for a phase with a legacy window but no phase_start", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", exam_cycle_id: "cyc-1", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-needs-date-badge-ph-1")).toBeTruthy();
    expect(screen.getByTestId("phase-date-editor-ph-1")).toBeTruthy();
  });

  test("shows legacy string on the row so operator sees source text", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", exam_cycle_id: "cyc-1", phase_start: null,
          metadata: { phase_window: "May–June 2026" } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-date-source-ph-1").textContent).toMatch("May–June 2026");
  });

  test("shows no inline editor when no phase has a date-authoring signal", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: "2026-05-24", metadata: {} },
      ],
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("phase-date-editor-ph-1")).toBeNull();
    expect(screen.queryByTestId("phase-needs-date-badge-ph-1")).toBeNull();
  });

  test("shows workbook-imported stubs without overloading phase_window", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-import", phase_name: "Prelims", exam_cycle_id: "cyc-1", phase_start: null,
          metadata: {
            import_source: "exam_registry_workbook",
            needs_phase_date_authoring: true,
          } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-date-editor-ph-import")).toBeTruthy();
    expect(screen.getByTestId("phase-date-source-ph-import").textContent).toMatch(
      "Imported workbook phase stub"
    );
  });

  test("shows explicit authoring stubs without phase_window or import_source", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-author", phase_name: "Mains", exam_cycle_id: "cyc-1", phase_start: null,
          metadata: { needs_phase_date_authoring: true } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-date-editor-ph-author")).toBeTruthy();
  });

  test("does not show an editor for imported stubs that already have phase_start", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-import-dated", phase_name: "Prelims", phase_start: "2026-05-24",
          metadata: {
            import_source: "exam_registry_workbook",
            needs_phase_date_authoring: true,
          } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("phase-date-editor-ph-import-dated")).toBeNull();
  });

  test("only the phase missing phase_start gets an editor", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: "2026-05-24",
          metadata: { phase_window: "24 May 2026" } },
        { id: "ph-2", phase_name: "Mains", exam_cycle_id: "cyc-1", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("phase-date-editor-ph-1")).toBeNull();
    expect(screen.getByTestId("phase-date-editor-ph-2")).toBeTruthy();
  });
});

// ── keyed off phase_start, not the flag ─────────────────────────────────────

describe("needs-date keys off phase_start IS NULL (regression guard)", () => {
  test("TBD row (not flagged by 165) gets an editor — keyed off phase_start null", () => {
    // This phase has no phase_window_needs_review flag (the 165 hole) but
    // DOES have a legacy window and no phase_start. It must be authorable.
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-tbd", phase_name: "Tier I", exam_cycle_id: "cyc-1", phase_start: null,
          metadata: { phase_window: "TBD" /* no phase_window_needs_review */ } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-date-editor-ph-tbd")).toBeTruthy();
    expect(screen.getByTestId("phase-date-source-ph-tbd").textContent).toMatch("TBD");
  });

  test("row flagged needs_review=true but already has phase_start gets NO editor", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-x", phase_name: "Tier II", phase_start: "2026-06-01",
          metadata: { phase_window: "01 Jun 2026", phase_window_needs_review: true } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("phase-date-editor-ph-x")).toBeNull();
  });
});

// ── save / patch flow ────────────────────────────────────────────────────────

describe("inline date save flow", () => {
  test("Set dates button is disabled when no start date entered", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", exam_cycle_id: "cyc-1", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-date-save-ph-1").disabled).toBe(true);
  });

  test("PATCHes with phase_start/phase_end when date entered and saved", async () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", exam_cycle_id: "cyc-1", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);

    // Enter a date into the phase start DateField for ph-1.
    const startInputs = screen.getAllByLabelText(/phase start/i);
    fireEvent.change(startInputs[startInputs.length - 1], {
      target: { value: "24-05-2026" },
    });

    fireEvent.click(screen.getByTestId("phase-date-save-ph-1"));

    await waitFor(() => expect(api.patch).toHaveBeenCalled());

    const [url, body] = api.patch.mock.calls[0];
    expect(url).toBe("/api/admin/exam-intelligence-cms/exam-phases/ph-1");
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    expect(body.payload.phase_start).toBe("2026-05-24");
    expect(body.payload.phase_end).toBeNull();
  });

  test("editor drops from the row after a successful PATCH", async () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", exam_cycle_id: "cyc-1", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);

    const startInputs = screen.getAllByLabelText(/phase start/i);
    fireEvent.change(startInputs[startInputs.length - 1], {
      target: { value: "24-05-2026" },
    });

    fireEvent.click(screen.getByTestId("phase-date-save-ph-1"));

    await waitFor(() =>
      expect(screen.queryByTestId("phase-date-editor-ph-1")).toBeNull()
    );
    // And the "Needs date" badge clears for that row too.
    expect(screen.queryByTestId("phase-needs-date-badge-ph-1")).toBeNull();
  });
});

// ── template phases stay out of the canonical timeline (checkpost Finding 1) ──

describe("template phases are not rendered or date-edited in the main timeline", () => {
  test("an unbound template phase appears only under Template phases, never in the timeline", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        // Cycle-bound operational phase — belongs in the canonical timeline.
        { id: "cyc-ph-1", phase_name: "Prelims 2026", exam_cycle_id: "cyc-1",
          phase_start: null, metadata: { phase_window: "TBD" } },
        // Unbound template (exam_cycle_id == null) with a date-authoring signal —
        // must NOT leak into the timeline or become date-editable there.
        { id: "tpl-1", phase_name: "Generic Prelims", phase_slug: "generic-prelims",
          phase_start: null, metadata: { needs_phase_date_authoring: true } },
      ],
    });
    render(<SetupPanel />);

    // Cycle-bound phase is in the timeline with an inline editor.
    expect(screen.getByTestId("phase-timeline-row-cyc-ph-1")).toBeTruthy();
    expect(screen.getByTestId("phase-date-editor-cyc-ph-1")).toBeTruthy();

    // Template phase is absent from the timeline and has no date editor/badge.
    expect(screen.queryByTestId("phase-timeline-row-tpl-1")).toBeNull();
    expect(screen.queryByTestId("phase-date-editor-tpl-1")).toBeNull();
    expect(screen.queryByTestId("phase-needs-date-badge-tpl-1")).toBeNull();

    // It appears only inside the collapsed Template phases section.
    const templateCard = screen.getByTestId("promote-template-card");
    expect(templateCard).toContainElement(screen.getByTestId("template-phase-tpl-1"));
  });
});
