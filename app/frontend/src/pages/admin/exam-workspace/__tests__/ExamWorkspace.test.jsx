/**
 * Tests for ExamWorkspace shell (PR1) + readiness provider (PR2).
 *
 * Covers:
 * - shell renders loading state
 * - shell renders error state with retry button
 * - shell renders exam name from context
 * - shell renders cycle picker populated from cycles[]
 * - shell renders 7 disabled tabs
 * - changing cycle picker updates URL
 * - useExamWorkspace() outside provider throws
 * - provider exposes readiness after fetch (PR2)
 * - readiness fetch error does not crash shell (PR2)
 * - refetchReadiness() re-fires the call (PR2)
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
};

const READINESS_RESPONSE = {
  exam_id: "exam-1",
  cycle_id: null,
  generated_at: "2026-01-01T00:00:00Z",
  overall: { status: "empty", score_percent: 0, ready_to_activate: false, blockers: [] },
  sections: [],
};

// ── Mock helper — routes /context calls to CONTEXT_RESPONSE, /readiness to READINESS_RESPONSE ──

function mockBothEndpoints({ contextResponse = CONTEXT_RESPONSE, readinessResponse = READINESS_RESPONSE } = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/readiness")) return Promise.resolve(readinessResponse);
    return Promise.resolve(contextResponse);
  });
}

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

// ── PR1 Tests ─────────────────────────────────────────────────────────────────

describe("ExamWorkspace shell", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders loading state while fetch is in flight", async () => {
    // Context never resolves; readiness resolves (doesn't affect shell loading)
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      return new Promise(() => {});
    });
    renderWorkspace();
    expect(screen.getByTestId("workspace-loading")).toBeTruthy();
  });

  test("renders error state with retry button on API failure", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      return Promise.reject(new Error("server error"));
    });
    renderWorkspace();
    await waitFor(() =>
      expect(screen.getByTestId("workspace-error")).toBeTruthy(),
    );
    expect(screen.getByRole("button", { name: /retry/i })).toBeTruthy();
    expect(screen.getByText(/server error/i)).toBeTruthy();
  });

  test("retry button calls refetch", async () => {
    let callCount = 0;
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      callCount++;
      if (callCount === 1) return Promise.reject(new Error("fail"));
      return Promise.resolve(CONTEXT_RESPONSE);
    });
    renderWorkspace();
    await waitFor(() => screen.getByTestId("workspace-error"));

    const retry = screen.getByRole("button", { name: /retry/i });
    await act(async () => { fireEvent.click(retry); });

    await waitFor(() =>
      expect(screen.getByTestId("exam-name")).toBeTruthy(),
    );
  });

  test("renders exam name from context", async () => {
    mockBothEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.getByTestId("exam-name").textContent).toBe("SSC CGL");
  });

  test("renders cycle picker populated from cycles[]", async () => {
    mockBothEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("cycle-picker"));
    const picker = screen.getByTestId("cycle-picker");
    // "All cycles" option + 2 cycle options
    expect(picker.options).toHaveLength(3);
    expect(picker.options[1].text).toBe("2026");
    expect(picker.options[2].text).toBe("2025");
  });

  test("renders exactly 7 tabs all disabled", async () => {
    mockBothEndpoints();
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
    mockBothEndpoints();
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
    mockBothEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("workspace-placeholder"));
    expect(screen.getByTestId("workspace-placeholder").textContent).toBe(
      "Select a section to begin",
    );
  });

  test("changing cycle picker navigates to cycle URL", async () => {
    mockBothEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("cycle-picker"));

    const callsBefore = api.get.mock.calls.filter((c) => c[0].includes("/context")).length;

    fireEvent.change(screen.getByTestId("cycle-picker"), {
      target: { value: "cycle-2026" },
    });

    await waitFor(() =>
      expect(api.get.mock.calls.filter((c) => c[0].includes("/context")).length).toBeGreaterThan(callsBefore),
    );

    const allUrls = api.get.mock.calls.map((c) => c[0]);
    expect(allUrls.some((u) => u.includes("cycle-2026"))).toBe(true);
  });
});

// ── PR2 Tests: readiness provider ─────────────────────────────────────────────

describe("ExamWorkspace readiness provider (PR2)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("provider exposes readiness after fetch", async () => {
    mockBothEndpoints();
    let captured = null;

    function ReadinessCapture() {
      const { readiness } = useExamWorkspace();
      captured = readiness;
      return null;
    }

    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/workspace/exam-1"]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/workspace/:exam_id"
            element={
              <ExamWorkspaceProvider>
                <ReadinessCapture />
              </ExamWorkspaceProvider>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(captured).not.toBeNull());
    expect(captured.exam_id).toBe("exam-1");
    expect(captured.overall).toBeTruthy();
  });

  test("readiness fetch error does not crash shell", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.reject(new Error("readiness fail"));
      return Promise.resolve(CONTEXT_RESPONSE);
    });
    renderWorkspace();
    // Shell renders normally despite readiness failure
    await waitFor(() => expect(screen.getByTestId("exam-name")).toBeTruthy());
    // workspace-error should NOT appear (that's only for context failure)
    expect(screen.queryByTestId("workspace-error")).toBeNull();
  });

  test("refetchReadiness re-fires the readiness call", async () => {
    mockBothEndpoints();
    let captured = null;

    function ReadinessHarness() {
      const { readiness, refetchReadiness } = useExamWorkspace();
      captured = { readiness, refetchReadiness };
      return null;
    }

    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/workspace/exam-1"]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/workspace/:exam_id"
            element={
              <ExamWorkspaceProvider>
                <ReadinessHarness />
              </ExamWorkspaceProvider>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(captured.readiness).not.toBeNull());
    const callsBefore = api.get.mock.calls.filter((c) => c[0].includes("/readiness")).length;

    await act(async () => { captured.refetchReadiness(); });

    await waitFor(() =>
      expect(api.get.mock.calls.filter((c) => c[0].includes("/readiness")).length).toBeGreaterThan(callsBefore),
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
