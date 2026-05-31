/**
 * Tests for ExamWorkspace shell (PR1).
 *
 * Covers:
 * - shell renders loading state
 * - shell renders error state with retry button
 * - shell renders exam name from context
 * - shell renders cycle picker populated from cycles[]
 * - shell renders 7 disabled tabs
 * - changing cycle picker updates URL
 * - useExamWorkspace() outside provider throws
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

const { api } = require("../../../../lib/api");

// Lazy-require after mock is set up
const ExamWorkspace = require("../ExamWorkspace").default;
const { useExamWorkspace, ExamWorkspaceProvider } = require("../ExamWorkspaceContext");

// ── Fixtures ──────────────────────────────────────────────────────────────────

const EXAM = { id: "exam-1", name: "SSC CGL", exam_type: "recruitment" };
const CYCLES = [
  { id: "cycle-2026", exam_id: "exam-1", year: 2026, cycle_name: "2026" },
  { id: "cycle-2025", exam_id: "exam-1", year: 2025, cycle_name: "2025" },
];
const PHASES = [
  { id: "ph-1", exam_id: "exam-1", exam_cycle_id: "cycle-2026", phase_name: "Tier I", phase_order: 1 },
];

const CONTEXT_RESPONSE = {
  exam: EXAM,
  cycle: null,
  cycles: CYCLES,
  phases: PHASES,
  readiness: null,
};

// ── Render helper ─────────────────────────────────────────────────────────────

function renderWorkspace(examId = "exam-1", cycleId = null) {
  const path = cycleId
    ? `/admin/exam-intelligence/workspace/${examId}/${cycleId}`
    : `/admin/exam-intelligence/workspace/${examId}`;
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/exam-intelligence/workspace/:exam_id" element={<ExamWorkspace />} />
        <Route path="/admin/exam-intelligence/workspace/:exam_id/:cycle_id" element={<ExamWorkspace />} />
      </Routes>
    </MemoryRouter>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ExamWorkspace shell", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders loading state while fetch is in flight", async () => {
    // Never resolves
    api.get.mockReturnValue(new Promise(() => {}));
    renderWorkspace();
    expect(screen.getByTestId("workspace-loading")).toBeInTheDocument();
  });

  test("renders error state with retry button on API failure", async () => {
    api.get.mockRejectedValue(new Error("server error"));
    renderWorkspace();
    await waitFor(() =>
      expect(screen.getByTestId("workspace-error")).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    expect(screen.getByText(/server error/i)).toBeInTheDocument();
  });

  test("retry button calls refetch", async () => {
    api.get.mockRejectedValueOnce(new Error("fail")).mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => screen.getByTestId("workspace-error"));

    const retry = screen.getByRole("button", { name: /retry/i });
    await act(async () => { fireEvent.click(retry); });

    await waitFor(() =>
      expect(screen.getByTestId("exam-name")).toBeInTheDocument(),
    );
  });

  test("renders exam name from context", async () => {
    api.get.mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => expect(screen.getByTestId("exam-name")).toBeInTheDocument());
    expect(screen.getByTestId("exam-name")).toHaveTextContent("SSC CGL");
  });

  test("renders cycle picker populated from cycles[]", async () => {
    api.get.mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => screen.getByTestId("cycle-picker"));
    const picker = screen.getByTestId("cycle-picker");
    // "All cycles" option + 2 cycle options
    expect(picker.options).toHaveLength(3);
    expect(picker.options[1].text).toBe("2026");
    expect(picker.options[2].text).toBe("2025");
  });

  test("renders exactly 7 tabs all disabled", async () => {
    api.get.mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-strip"));

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(7);
    tabs.forEach((tab) => {
      expect(tab).toBeDisabled();
      expect(tab).toHaveAttribute("aria-disabled", "true");
    });
  });

  test("renders all 7 tab labels", async () => {
    api.get.mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-strip"));

    const expectedLabels = [
      "Setup", "Documents", "Syllabus Mapper", "PYQ Workbench",
      "Updates", "Competition", "Review & Activate",
    ];
    expectedLabels.forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  test("renders placeholder content area", async () => {
    api.get.mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => screen.getByTestId("workspace-placeholder"));
    expect(screen.getByTestId("workspace-placeholder")).toHaveTextContent(
      "Select a section to begin",
    );
  });

  test("changing cycle picker navigates to cycle URL", async () => {
    api.get.mockResolvedValue(CONTEXT_RESPONSE);
    const { container } = renderWorkspace();
    await waitFor(() => screen.getByTestId("cycle-picker"));

    fireEvent.change(screen.getByTestId("cycle-picker"), {
      target: { value: "cycle-2026" },
    });

    // After navigation, a new fetch fires with the new path including cycle_id
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining("cycle-2026"),
      ),
    );
  });
});

// ── useExamWorkspace outside provider ────────────────────────────────────────

describe("useExamWorkspace", () => {
  test("throws when called outside ExamWorkspaceProvider", () => {
    function BadComponent() {
      useExamWorkspace();
      return null;
    }
    // Suppress React error boundary noise in test output
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => {
      render(
        <MemoryRouter>
          <BadComponent />
        </MemoryRouter>,
      );
    }).toThrow("useExamWorkspace must be used inside ExamWorkspaceProvider");
    spy.mockRestore();
  });
});
