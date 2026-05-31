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
    expect(screen.getByTestId("workspace-loading")).toBeTruthy();
  });

  test("renders error state with retry button on API failure", async () => {
    api.get.mockRejectedValue(new Error("server error"));
    renderWorkspace();
    await waitFor(() =>
      expect(screen.getByTestId("workspace-error")).toBeTruthy(),
    );
    expect(screen.getByRole("button", { name: /retry/i })).toBeTruthy();
    expect(screen.getByText(/server error/i)).toBeTruthy();
  });

  test("retry button calls refetch", async () => {
    api.get.mockRejectedValueOnce(new Error("fail")).mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => screen.getByTestId("workspace-error"));

    const retry = screen.getByRole("button", { name: /retry/i });
    await act(async () => { fireEvent.click(retry); });

    await waitFor(() =>
      expect(screen.getByTestId("exam-name")).toBeTruthy(),
    );
  });

  test("renders exam name from context", async () => {
    api.get.mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.getByTestId("exam-name").textContent).toBe("SSC CGL");
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
      expect(tab.disabled).toBe(true);
      expect(tab.getAttribute("aria-disabled")).toBe("true");
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
      expect(screen.getByText(label)).toBeTruthy();
    });
  });

  test("renders placeholder content area", async () => {
    api.get.mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => screen.getByTestId("workspace-placeholder"));
    expect(screen.getByTestId("workspace-placeholder").textContent).toBe(
      "Select a section to begin",
    );
  });

  test("changing cycle picker navigates to cycle URL", async () => {
    api.get.mockResolvedValue(CONTEXT_RESPONSE);
    renderWorkspace();
    await waitFor(() => screen.getByTestId("cycle-picker"));

    // Changing cycle navigates, which remounts the provider and triggers a new fetch
    // with the new cycle_id in the URL. We verify navigation happened by checking
    // that api.get was called a second time (initial load + after navigation).
    const callsBefore = api.get.mock.calls.length;

    fireEvent.change(screen.getByTestId("cycle-picker"), {
      target: { value: "cycle-2026" },
    });

    await waitFor(() =>
      expect(api.get.mock.calls.length).toBeGreaterThan(callsBefore),
    );

    const allUrls = api.get.mock.calls.map((c) => c[0]);
    expect(allUrls.some((u) => u.includes("cycle-2026"))).toBe(true);
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
