/**
 * SetupPanel — cycle create/edit and add-phase cycle picker.
 *
 * Concern 1 (cycle authoring):
 *   - "Create cycles in the Exam CMS" dead-end is gone; + Create cycle button present
 *   - create POSTs to /exam-cycles with reason≥8, exam_id, year, cycle_name
 *   - edit PATCHes to /exam-cycles/{id} with reason≥8
 *   - refetch() called after create / edit
 *
 * Concern 2 (cycle picker — written failing before implementation):
 *   - cycle picker present in add-phase form when cycles exist
 *   - picker defaults to the active cycle
 *   - addPhase targets the PICKED cycle, not always activeCycle||cycles[0]
 *     (pins the latent bug where selecting a non-active cycle was ignored)
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

// Mirror the pattern from Organizations.create.test.jsx: mock the hook so
// tests never need a ToastProvider context.
jest.mock("../../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => {
    const run = jest.fn(async ({ action, onSuccess }) => {
      try {
        const result = await action();
        if (onSuccess) onSuccess(result);
        return { ok: true, data: result };
      } catch (e) {
        return { ok: false, error: e };
      }
    });
    return { run, busy: false };
  },
}));

const { api } = require("../../../../../lib/api");
const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const SetupPanel = require("../SetupPanel").default;

const BASE_EXAM = { id: "exam-1", name: "UPSC CSE", slug: "upsc-cse" };
const REFETCH = jest.fn();

const TWO_CYCLES = [
  { id: "cyc-A", status: "active",   cycle_name: "2026 Cycle", year: 2026 },
  { id: "cyc-B", status: "expected", cycle_name: "2027 Cycle", year: 2027 },
];

beforeEach(() => {
  api.post.mockReset();
  api.patch.mockReset();
  api.get.mockReset();
  api.post.mockResolvedValue({ ok: true });
  api.patch.mockResolvedValue({ ok: true });
  REFETCH.mockReset();
});

// ── Concern 1: cycle create ───────────────────────────────────────────────────

describe("SetupPanel cycle create", () => {
  beforeEach(() => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: [],
      phases: [],
      refetch: REFETCH,
    });
  });

  test("shows + Create cycle button instead of CMS dead-end message", () => {
    render(<SetupPanel />);
    expect(screen.queryByText(/Create cycles in the Exam CMS/)).toBeNull();
    expect(screen.getByTestId("add-cycle-btn")).toBeTruthy();
  });

  test("POSTs to /exam-cycles with reason≥8, exam_id, year, cycle_name", async () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByTestId("add-cycle-btn"));
    fireEvent.change(screen.getByPlaceholderText(/cycle name/i), {
      target: { value: "2026 Cycle" },
    });
    fireEvent.change(screen.getByPlaceholderText(/year/i), {
      target: { value: "2026" },
    });
    fireEvent.change(screen.getByPlaceholderText(/reason.*required/i), {
      target: { value: "Creating 2026 cycle for UPSC" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create cycle/i }));

    await waitFor(() => expect(api.post).toHaveBeenCalled());

    const [url, body] = api.post.mock.calls[0];
    expect(url).toBe("/api/admin/exam-intelligence-cms/exam-cycles");
    expect(typeof body.reason).toBe("string");
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    expect(body.payload.exam_id).toBe("exam-1");
    expect(body.payload.year).toBe(2026);
    expect(body.payload.cycle_name).toBe("2026 Cycle");
  });

  test("calls refetch() after successful cycle create", async () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByTestId("add-cycle-btn"));
    fireEvent.change(screen.getByPlaceholderText(/cycle name/i), {
      target: { value: "2026 Cycle" },
    });
    fireEvent.change(screen.getByPlaceholderText(/year/i), {
      target: { value: "2026" },
    });
    fireEvent.change(screen.getByPlaceholderText(/reason.*required/i), {
      target: { value: "Creating 2026 cycle for UPSC" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create cycle/i }));

    await waitFor(() => expect(REFETCH).toHaveBeenCalled());
  });
});

// ── Concern 1: cycle edit ─────────────────────────────────────────────────────

describe("SetupPanel cycle edit", () => {
  beforeEach(() => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: [{ id: "cyc-1", status: "active", cycle_name: "2026 Cycle", year: 2026 }],
      phases: [],
      refetch: REFETCH,
    });
  });

  test("edit button present per cycle row", () => {
    render(<SetupPanel />);
    expect(screen.getByTestId("edit-cycle-cyc-1")).toBeTruthy();
  });

  test("PATCHes to /exam-cycles/{id} with reason≥8 and updated cycle_name", async () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByTestId("edit-cycle-cyc-1"));

    fireEvent.change(screen.getByTestId("edit-cycle-name-cyc-1"), {
      target: { value: "2026 Revised Cycle" },
    });
    fireEvent.change(screen.getByTestId("edit-cycle-reason-cyc-1"), {
      target: { value: "Correcting cycle name after review" },
    });
    fireEvent.click(screen.getByTestId("save-cycle-cyc-1"));

    await waitFor(() => expect(api.patch).toHaveBeenCalled());

    const [url, body] = api.patch.mock.calls[0];
    expect(url).toBe("/api/admin/exam-intelligence-cms/exam-cycles/cyc-1");
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    expect(body.payload.cycle_name).toBe("2026 Revised Cycle");
  });

  test("calls refetch() after successful cycle edit", async () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByTestId("edit-cycle-cyc-1"));
    fireEvent.change(screen.getByTestId("edit-cycle-name-cyc-1"), {
      target: { value: "2026 Revised Cycle" },
    });
    fireEvent.change(screen.getByTestId("edit-cycle-reason-cyc-1"), {
      target: { value: "Correcting cycle name after review" },
    });
    fireEvent.click(screen.getByTestId("save-cycle-cyc-1"));

    await waitFor(() => expect(REFETCH).toHaveBeenCalled());
  });
});

// ── Concern 2: cycle picker on add-phase (written failing before implementation) ──

describe("SetupPanel.addPhase cycle picker", () => {
  beforeEach(() => {
    useExamWorkspace.mockReturnValue({
      exam: BASE_EXAM,
      cycles: TWO_CYCLES,
      phases: [],
      refetch: REFETCH,
    });
  });

  test("cycle picker is present in add-phase form when cycles exist", () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByText("+ Add phase"));
    expect(screen.getByTestId("cycle-picker")).toBeTruthy();
  });

  test("cycle picker defaults to the active cycle", () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByText("+ Add phase"));
    expect(screen.getByTestId("cycle-picker").value).toBe("cyc-A");
  });

  test("addPhase targets the PICKED cycle, not always the active one (bug pin)", async () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByText("+ Add phase"));

    // Switch to the non-active cycle
    fireEvent.change(screen.getByTestId("cycle-picker"), {
      target: { value: "cyc-B" },
    });
    fireEvent.change(screen.getByPlaceholderText("Phase name"), {
      target: { value: "Mains" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add phase" }));

    await waitFor(() => expect(api.post).toHaveBeenCalled());

    const body = api.post.mock.calls[0][1];
    expect(body.payload.exam_cycle_id).toBe("cyc-B");
  });
});
