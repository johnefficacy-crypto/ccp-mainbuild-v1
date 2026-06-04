/**
 * Tests for the "Phases needing dates" worklist in SetupPanel.
 *
 * The worklist is keyed off phase_start IS NULL plus an explicit authoring
 * signal: legacy phase_window, workbook import_source, or
 * needs_phase_date_authoring. It must NOT key off phase_window_needs_review
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

// SetupPanel now imports useApiAction (for cycle create/edit). Mock it so
// tests never need a ToastProvider context — mirrors Organizations.create.test.jsx.
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

// ── worklist visibility ──────────────────────────────────────────────────────

describe("worklist visibility", () => {
  test("shows worklist card when phases have a legacy window but no phase_start", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-date-worklist")).toBeTruthy();
    expect(screen.getByTestId("worklist-row-ph-1")).toBeTruthy();
  });

  test("shows legacy string in worklist row so operator sees source text", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: null,
          metadata: { phase_window: "May–June 2026" } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("worklist-legacy-ph-1").textContent).toMatch("May–June 2026");
  });

  test("hides worklist card when no phases have a date-authoring signal", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: "2026-05-24", metadata: {} },
      ],
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("phase-date-worklist")).toBeNull();
  });

  test("shows workbook-imported stubs without overloading phase_window", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-import", phase_name: "Prelims", phase_start: null,
          metadata: {
            import_source: "exam_registry_workbook",
            needs_phase_date_authoring: true,
          } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("phase-date-worklist")).toBeTruthy();
    expect(screen.getByTestId("worklist-row-ph-import")).toBeTruthy();
    expect(screen.getByTestId("worklist-legacy-ph-import").textContent).toMatch(
      "Imported workbook phase stub"
    );
  });

  test("shows explicit authoring stubs without phase_window or import_source", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-author", phase_name: "Mains", phase_start: null,
          metadata: { needs_phase_date_authoring: true } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("worklist-row-ph-author")).toBeTruthy();
  });

  test("does not include imported stubs that already have phase_start", () => {
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
    expect(screen.queryByTestId("phase-date-worklist")).toBeNull();
  });

  test("does not include phases that already have phase_start in worklist", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: "2026-05-24",
          metadata: { phase_window: "24 May 2026" } },
        { id: "ph-2", phase_name: "Mains", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("worklist-row-ph-1")).toBeNull();
    expect(screen.getByTestId("worklist-row-ph-2")).toBeTruthy();
  });
});

// ── keyed off phase_start, not the flag ─────────────────────────────────────

describe("worklist keys off phase_start IS NULL (regression guard)", () => {
  test("TBD row (not flagged by 165) appears in worklist — keyed off phase_start null", () => {
    // This phase has no phase_window_needs_review flag (the 165 hole) but
    // DOES have a legacy window and no phase_start. It must appear.
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-tbd", phase_name: "Tier I", phase_start: null,
          metadata: { phase_window: "TBD" /* no phase_window_needs_review */ } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("worklist-row-ph-tbd")).toBeTruthy();
    expect(screen.getByTestId("worklist-legacy-ph-tbd").textContent).toMatch("TBD");
  });

  test("row flagged needs_review=true but already has phase_start is NOT in worklist", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-x", phase_name: "Tier II", phase_start: "2026-06-01",
          metadata: { phase_window: "01 Jun 2026", phase_window_needs_review: true } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.queryByTestId("worklist-row-ph-x")).toBeNull();
  });
});

// ── save / patch flow ────────────────────────────────────────────────────────

describe("worklist save flow", () => {
  test("Set dates button is disabled when no start date entered", () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);
    expect(screen.getByTestId("worklist-save-ph-1").disabled).toBe(true);
  });

  test("PATCHes with phase_start/phase_end when date entered and saved", async () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);

    // Enter a date into the phase start DateField for ph-1.
    const startInputs = screen.getAllByLabelText(/phase start/i);
    fireEvent.change(startInputs[startInputs.length - 1], {
      target: { value: "24-05-2026" },
    });

    fireEvent.click(screen.getByTestId("worklist-save-ph-1"));

    await waitFor(() => expect(api.patch).toHaveBeenCalled());

    const [url, body] = api.patch.mock.calls[0];
    expect(url).toBe("/api/admin/exam-intelligence-cms/exam-phases/ph-1");
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    expect(body.payload.phase_start).toBe("2026-05-24");
    expect(body.payload.phase_end).toBeNull();
  });

  test("row drops from worklist after successful PATCH", async () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);

    const startInputs = screen.getAllByLabelText(/phase start/i);
    fireEvent.change(startInputs[startInputs.length - 1], {
      target: { value: "24-05-2026" },
    });

    fireEvent.click(screen.getByTestId("worklist-save-ph-1"));

    await waitFor(() =>
      expect(screen.queryByTestId("worklist-row-ph-1")).toBeNull()
    );
  });

  test("shows all-dated empty state when all worklist rows have been saved", async () => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: BASE_CYCLES,
      phases: [
        { id: "ph-1", phase_name: "Prelims", phase_start: null,
          metadata: { phase_window: "TBD" } },
      ],
    });
    render(<SetupPanel />);

    const startInputs = screen.getAllByLabelText(/phase start/i);
    fireEvent.change(startInputs[startInputs.length - 1], {
      target: { value: "24-05-2026" },
    });
    fireEvent.click(screen.getByTestId("worklist-save-ph-1"));

    await waitFor(() =>
      expect(screen.getByTestId("worklist-all-dated")).toBeTruthy()
    );
  });
});
