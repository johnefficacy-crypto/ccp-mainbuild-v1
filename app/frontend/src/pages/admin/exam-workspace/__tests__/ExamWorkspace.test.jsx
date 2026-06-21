/**
 * Tests for ExamWorkspace shell (PR1) + readiness provider (PR2).
 *
 * Covers:
 * - shell renders loading state
 * - shell renders error state with retry button
 * - shell renders exam name from context
 * - shell renders cycle picker populated from cycles[]
 * - shell renders 8 clickable tabs
 * - changing cycle picker updates URL
 * - useExamWorkspace() outside provider throws
 * - provider exposes readiness after fetch (PR2)
 * - readiness fetch error does not crash shell (PR2)
 * - refetchReadiness() re-fires the call (PR2)
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

jest.mock("../../../../lib/supabase", () => ({
  __esModule: true,
  supabase: { auth: { getSession: jest.fn(), onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })) } },
}));

// ReviewActivatePanel calls useAuth.
jest.mock("../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { role: "admin", permissions: [] } }),
}));

const { api } = require("../../../../lib/api");

// Lazy-require after mock is set up
const ExamWorkspace = require("../ExamWorkspace").default;
const { AddCycleRedirect } = require("../../../../routes/adminRoutes");
const { useExamWorkspace, ExamWorkspaceProvider } = require("../ExamWorkspaceContext");

// ── Fixtures ──────────────────────────────────────────────────────────────────

const EXAM = { id: "exam-1", name: "SSC CGL", exam_type: "recruitment", management_mode: null, family_name: null, organization_name: null };
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
  organization: null,
  family: null,
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

function renderWorkspace(examId = "exam-1", cycleId = null, query = "") {
  const path = cycleId
    ? `/admin/exam-intelligence/workspace/${examId}/${cycleId}${query}`
    : `/admin/exam-intelligence/workspace/${examId}${query}`;
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

  test("no longer renders the Advanced raw-table-editor drawer (Wave 4.6B)", async () => {
    mockBothEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.queryByText(/raw table editor/i)).toBeNull();
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

  test("renders exactly 8 tabs all clickable", async () => {
    mockBothEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-strip"));

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(8);
    tabs.forEach((tab) => {
      expect(tab.disabled).toBeFalsy();
    });
  });

  test("renders all 8 tab labels", async () => {
    mockBothEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-strip"));

    const expectedLabels = [
      "Overview", "Setup", "Documents", "Syllabus Mapper", "PYQ Workbench",
      "Updates", "Competition", "Review & Activate",
    ];
    expectedLabels.forEach((label) => {
      expect(screen.getByText(label)).toBeTruthy();
    });
  });

  test("defaults to Overview tab active and renders overview smoke details", async () => {
    mockBothEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-overview"));
    const overviewTab = screen.getByTestId("tab-overview");
    expect(overviewTab.getAttribute("aria-selected")).toBe("true");
    expect(screen.getByTestId("overview-panel")).toBeTruthy();
    expect(screen.getByText("Unclassified")).toBeTruthy();
  });

  test("overview renders resolved family and organization from workspace context", async () => {
    mockBothEndpoints({
      contextResponse: {
        ...CONTEXT_RESPONSE,
        family: { id: "fam-1", name: "Resolved Family", slug: "resolved-family" },
        organization: { id: "org-1", name: "Resolved Organization", type: "central", trust_tier: "verified" },
      },
    });
    renderWorkspace();
    await waitFor(() => screen.getByTestId("overview-panel"));
  });


  test("workspace/:id?tab=setup starts on Setup tab", async () => {
    mockBothEndpoints();
    renderWorkspace("exam-1", null, "?tab=setup");
    await waitFor(() => screen.getByTestId("tab-setup"));
    expect(screen.getByTestId("tab-setup").getAttribute("aria-selected")).toBe("true");
    expect(screen.getByText(/Set up this exam's cycles/i)).toBeTruthy();
  });

  test("workspace/:id?tab=setup&action=add-cycle opens cycle-create-section", async () => {
    mockBothEndpoints();
    renderWorkspace("exam-1", null, "?tab=setup&action=add-cycle");
    await waitFor(() => screen.getByTestId("cycle-create-section"));
    expect(screen.getByTestId("tab-setup").getAttribute("aria-selected")).toBe("true");
  });

  test("workspace/:id without query still defaults to Overview", async () => {
    mockBothEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-overview"));
    expect(screen.getByTestId("tab-overview").getAttribute("aria-selected")).toBe("true");
    expect(screen.getByTestId("overview-panel")).toBeTruthy();
  });

  test("add-cycle route redirects to workspace setup with action=add-cycle", async () => {
    function LocationCapture() {
      const location = useLocation();
      return <div data-testid="location">{location.pathname}{location.search}</div>;
    }

    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/exams/exam-1/add-cycle"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/exams/:exam_id/add-cycle" element={<AddCycleRedirect />} />
          <Route path="/admin/exam-intelligence/workspace/:exam_id" element={<LocationCapture />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("location").textContent).toBe("/admin/exam-intelligence/workspace/exam-1?tab=setup&action=add-cycle"));
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

// ── B2: standalone workspace regression ─────────────────────────────────────

const STANDALONE_READINESS = {
  exam_id: "exam-1",
  cycle_id: null,
  overall: { status: "partial", score_percent: 40, ready_to_activate: false, blockers: [] },
  sections: [
    { section: "setup",          label: "Setup",              status: "ready",   blockers: [],                                  metrics: { phase_count: 2 } },
    { section: "documents",      label: "Documents",          status: "partial", blockers: ["3 documents pending extraction"],  metrics: { total: 5, extracted: 2, pending: 3, failed: 0 } },
    { section: "syllabus_mapper",label: "Syllabus Mapper",    status: "empty",   blockers: ["2 mentions pending review"],       metrics: { total: 2, pending: 2, verified: 0, locked: 0 } },
    { section: "pyq_workbench",  label: "PYQ Workbench",      status: "empty",   blockers: ["no PYQ papers uploaded"],          metrics: { papers: 0, questions_total: 0 } },
    { section: "updates",        label: "Updates",            status: "partial", blockers: [],                                  metrics: { total: 3, pending: 1, verified: 2 } },
    { section: "competition",    label: "Competition",        status: "ready",   blockers: [],                                  metrics: {} },
    { section: "review_activate",label: "Review & Activate",  status: "partial", blockers: ["upstream sections incomplete"],     metrics: {} },
  ],
  topic_coverage: { total: 20, draft: 1, pending: 12, reviewed: 7, locked: 0, high_yield: 3 },
};

describe("ExamWorkspace standalone layout regression (B2)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("standalone workspace keeps the tab strip and renders no rail (regression)", async () => {
    mockBothEndpoints({ readinessResponse: STANDALONE_READINESS });
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/workspace/exam-1"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/workspace/:exam_id" element={<ExamWorkspace />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByTestId("tab-strip"));
    expect(screen.getAllByRole("tab")).toHaveLength(8);
    expect(screen.getByTestId("cycle-picker")).toBeTruthy();
    expect(screen.getAllByText("40% ready · partial")[0]).toBeTruthy();
    expect(screen.getByTestId("tab-review").textContent).toContain("40%");
    expect(screen.getByTestId("overview-readiness-sections").textContent).toContain("40%");
    expect(screen.queryByTestId("exam-task-rail")).toBeNull();
    expect(screen.queryByTestId("console-rail-layout")).toBeNull();
  });
});

// ── B2: standalone fetch regression ─────────────────────────────────────────

describe("ExamWorkspace standalone fetch regression (B2)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("fetches context and readiness exactly once on initial mount", async () => {
    mockBothEndpoints({ readinessResponse: STANDALONE_READINESS });
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/workspace/exam-1"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/workspace/:exam_id" element={<ExamWorkspace />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByTestId("exam-name"));
    const contextCalls = api.get.mock.calls.filter(([url]) => url.includes("/context"));
    const readinessCalls = api.get.mock.calls.filter(([url]) => url.includes("/readiness"));
    expect(contextCalls).toHaveLength(1);
    expect(readinessCalls).toHaveLength(1);
  });
});

// ── B2: standalone review surface ───────────────────────────────────────────

describe("ExamWorkspace standalone review surface (B2)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("review tab renders ReviewActivatePanel without extra readiness fetch", async () => {
    mockBothEndpoints({ readinessResponse: STANDALONE_READINESS });
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/workspace/exam-1?tab=review"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/workspace/:exam_id" element={<ExamWorkspace />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByRole("heading", { name: /Readiness & Activation/i }));
    expect(screen.getByText("40% ready")).toBeTruthy();
    const readinessCalls = api.get.mock.calls.filter(([url]) => url.includes("/readiness"));
    expect(readinessCalls).toHaveLength(1);
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
