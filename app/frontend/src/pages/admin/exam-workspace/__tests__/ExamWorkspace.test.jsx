/**
 * Tests for ExamWorkspace shell (I8-B).
 *
 * Covers:
 * - shell renders loading state
 * - shell renders error state with retry button
 * - shell renders exam name from context
 * - shell renders cycle picker populated from cycles[]
 * - shell renders 7 clickable tabs (no Overview after I8-B)
 * - URL is the single source of tab state (tab click updates ?tab=)
 * - cycle change preserves ?tab= and drops document/paper/row
 * - management endpoint called with cycle_id when ?cycle= is set
 * - initial cycle normalization adds ?cycle= from backend current_cycle
 * - useExamWorkspace() outside provider throws
 * - provider exposes readiness after fetch (PR2)
 * - readiness fetch error does not crash shell (PR2)
 * - refetchReadiness() re-fires the call (PR2)
 * - action console embedded at /exams/:exam_id (I8-B)
 * - add-cycle compat redirect preserved (I8-B)
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

// Closure variable — must start with "mock" so Jest's hoisting rule permits it
// inside jest.mock() factories. Tests mutate this directly; beforeEach resets it.
let mockAuthUser = { role: "admin", permissions: [] };

// ReviewActivatePanel and SmartHeader call useAuth.
jest.mock("../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: mockAuthUser }),
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

const MANAGEMENT_RESPONSE = {
  id: "exam-1", slug: "ssc-cgl", name: "SSC CGL",
  management_mode: null, cadence: null, is_active: true,
  family_name: null, organization_name: null,
  family_id: null, organization_id: null,
  status: "ready", flags: [], blocker_count: 0, first_blocker_text: null,
  readiness_summary: { setup: "ready", topic_coverage: "missing", pyq: "missing", pending_review_count: 0, stale_review_count: 0 },
  current_cycle: null,
  cycles: [],
  section_readiness: null,
  activation_verdict: { status: "ready", headline: "Ready for aspirants", reasons: [] },
  mock_readiness: { status: "ready", detail: null },
  action_queue: [],
  activation_checks: [],
  stages: [],
  evidence_refs: [],
  generated_at: "2026-01-01T00:00:00Z",
};

// ── Mock helper ───────────────────────────────────────────────────────────────

function mockAllEndpoints({ contextResponse = CONTEXT_RESPONSE, readinessResponse = READINESS_RESPONSE, managementResponse = MANAGEMENT_RESPONSE } = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/readiness")) return Promise.resolve(readinessResponse);
    if (url.includes("/management/exams/")) return Promise.resolve(managementResponse);
    return Promise.resolve(contextResponse);
  });
}

// ── Render helper ─────────────────────────────────────────────────────────────

function renderWorkspace(examId = "exam-1", cycleId = null, extraSearch = "") {
  const searchParts = [];
  if (cycleId) searchParts.push(`cycle=${cycleId}`);
  if (extraSearch) searchParts.push(extraSearch.replace(/^\?/, ""));
  const qs = searchParts.length ? `?${searchParts.join("&")}` : "";
  const path = `/admin/exam-intelligence/exams/${examId}${qs}`;
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/exam-intelligence/exams/:exam_id" element={<ExamWorkspace />} />
      </Routes>
    </MemoryRouter>,
  );
}

// Helper: render with a location capture component
function renderWorkspaceWithLocation(path) {
  function LocationCapture() {
    const loc = useLocation();
    return <div data-testid="location">{loc.pathname}{loc.search}</div>;
  }
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/admin/exam-intelligence/exams/:exam_id"
          element={<><ExamWorkspace /><LocationCapture /></>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

// ── Shell Tests ───────────────────────────────────────────────────────────────

describe("ExamWorkspace shell", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders loading state while fetch is in flight", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      if (url.includes("/management/exams/")) return Promise.resolve(MANAGEMENT_RESPONSE);
      return new Promise(() => {});
    });
    renderWorkspace();
    expect(screen.getByTestId("workspace-loading")).toBeTruthy();
  });

  test("renders error state with retry button on API failure", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      if (url.includes("/management/exams/")) return Promise.resolve(MANAGEMENT_RESPONSE);
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
      if (url.includes("/management/exams/")) return Promise.resolve(MANAGEMENT_RESPONSE);
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
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.getByTestId("exam-name").textContent).toBe("SSC CGL");
  });

  test("no longer renders the Advanced raw-table-editor drawer (Wave 4.6B)", async () => {
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.queryByText(/raw table editor/i)).toBeNull();
  });

  test("renders cycle picker populated from cycles[]", async () => {
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("cycle-picker"));
    const picker = screen.getByTestId("cycle-picker");
    // "All cycles" option + 2 cycle options
    expect(picker.options).toHaveLength(3);
    expect(picker.options[1].text).toBe("2026");
    expect(picker.options[2].text).toBe("2025");
  });

  test("renders exactly 7 tabs all clickable (no Overview after I8-B)", async () => {
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-strip"));

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(7);
    tabs.forEach((tab) => {
      expect(tab.disabled).toBeFalsy();
    });
  });

  test("renders all 7 tab labels (no Overview)", async () => {
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-strip"));

    const expectedLabels = [
      "Setup", "Documents", "Syllabus Mapper", "PYQ Workbench",
      "Updates", "Competition", "Review & Activate",
    ];
    expectedLabels.forEach((label) => {
      expect(screen.getByText(label)).toBeTruthy();
    });
    // Overview tab is gone (I8-B)
    expect(screen.queryByTestId("tab-overview")).toBeNull();
  });

  test("defaults to Setup tab active (Overview removed in I8-B)", async () => {
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-setup"));
    const setupTab = screen.getByTestId("tab-setup");
    expect(setupTab.getAttribute("aria-selected")).toBe("true");
  });

  test("exams/:id?tab=setup starts on Setup tab", async () => {
    mockAllEndpoints();
    renderWorkspace("exam-1", null, "?tab=setup");
    await waitFor(() => screen.getByTestId("tab-setup"));
    expect(screen.getByTestId("tab-setup").getAttribute("aria-selected")).toBe("true");
    expect(screen.getByText(/Set up this exam's cycles/i)).toBeTruthy();
  });

  test("exams/:id?tab=setup&action=add-cycle opens cycle-create-section", async () => {
    mockAllEndpoints();
    renderWorkspace("exam-1", null, "?tab=setup&action=add-cycle");
    await waitFor(() => screen.getByTestId("cycle-create-section"));
    expect(screen.getByTestId("tab-setup").getAttribute("aria-selected")).toBe("true");
  });

  test("exams/:id without query still defaults to Setup", async () => {
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("tab-setup"));
    expect(screen.getByTestId("tab-setup").getAttribute("aria-selected")).toBe("true");
  });

  test("add-cycle route redirects to exams/:id?tab=setup&action=add-cycle", async () => {
    function LocationCapture() {
      const location = useLocation();
      return <div data-testid="location">{location.pathname}{location.search}</div>;
    }

    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/exams/exam-1/add-cycle"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/exams/:exam_id/add-cycle" element={<AddCycleRedirect />} />
          <Route path="/admin/exam-intelligence/exams/:exam_id" element={<LocationCapture />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("location").textContent).toBe("/admin/exam-intelligence/exams/exam-1?tab=setup&action=add-cycle"));
  });

  test("changing cycle picker navigates to ?cycle= query param", async () => {
    mockAllEndpoints();
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

// ── URL is the single source of tab state ────────────────────────────────────

describe("ExamWorkspace URL-driven tab state", () => {
  beforeEach(() => jest.clearAllMocks());

  test("?tab=documents starts on Documents tab (not setup)", async () => {
    mockAllEndpoints();
    renderWorkspace("exam-1", null, "?tab=documents");
    await waitFor(() => screen.getByTestId("tab-documents"));
    expect(screen.getByTestId("tab-documents").getAttribute("aria-selected")).toBe("true");
    expect(screen.getByTestId("tab-setup").getAttribute("aria-selected")).toBe("false");
  });

  test("tab click updates ?tab= search param", async () => {
    mockAllEndpoints();
    renderWorkspaceWithLocation("/admin/exam-intelligence/exams/exam-1");
    await waitFor(() => screen.getByTestId("tab-strip"));
    fireEvent.click(screen.getByTestId("tab-documents"));
    await waitFor(() =>
      expect(screen.getByTestId("location").textContent).toContain("tab=documents"),
    );
    expect(screen.getByTestId("tab-documents").getAttribute("aria-selected")).toBe("true");
  });

  test("cycle change preserves ?tab= param and drops document/paper/row", async () => {
    mockAllEndpoints();
    // Start on documents tab
    renderWorkspaceWithLocation("/admin/exam-intelligence/exams/exam-1?tab=documents&document=doc-1");
    await waitFor(() => screen.getByTestId("tab-documents"));
    expect(screen.getByTestId("tab-documents").getAttribute("aria-selected")).toBe("true");

    fireEvent.change(screen.getByTestId("cycle-picker"), { target: { value: "cycle-2026" } });

    // Tab should still be documents
    await waitFor(() =>
      expect(screen.getByTestId("location").textContent).toContain("tab=documents"),
    );
    // document param should be dropped
    expect(screen.getByTestId("location").textContent).not.toContain("document=doc-1");
    // cycle should be set
    expect(screen.getByTestId("location").textContent).toContain("cycle=cycle-2026");
  });

  test("management endpoint includes cycle_id when ?cycle= is set", async () => {
    mockAllEndpoints();
    renderWorkspace("exam-1", "cycle-2026");
    await waitFor(() => screen.getByTestId("exam-name"));
    const mgmtCalls = api.get.mock.calls.filter(
      ([u]) => u.includes("/management/exams/exam-1") && u.includes("cycle_id=cycle-2026"),
    );
    expect(mgmtCalls.length).toBeGreaterThan(0);
  });

  test("initial cycle normalization adds ?cycle= from backend current_cycle", async () => {
    const mgmtWithCycle = {
      ...MANAGEMENT_RESPONSE,
      current_cycle: { id: "cycle-2026", name: "2026", year: 2026, status: "active", phases: [] },
    };
    mockAllEndpoints({ managementResponse: mgmtWithCycle });
    renderWorkspaceWithLocation("/admin/exam-intelligence/exams/exam-1");
    await waitFor(() =>
      expect(screen.getByTestId("location").textContent).toContain("cycle=cycle-2026"),
    );
  });

  test("no cycle normalization when ?cycle= already in URL", async () => {
    const mgmtWithCycle = {
      ...MANAGEMENT_RESPONSE,
      current_cycle: { id: "cycle-2026", name: "2026", year: 2026, status: "active", phases: [] },
    };
    mockAllEndpoints({ managementResponse: mgmtWithCycle });
    renderWorkspaceWithLocation("/admin/exam-intelligence/exams/exam-1?cycle=cycle-2025");
    await waitFor(() => screen.getByTestId("exam-name"));
    // Should keep cycle-2025, not replace with cycle-2026
    expect(screen.getByTestId("location").textContent).toContain("cycle=cycle-2025");
    expect(screen.getByTestId("location").textContent).not.toContain("cycle=cycle-2026");
  });
});

// ── I8-B: embedded action console ────────────────────────────────────────────

describe("ExamWorkspace embedded action console (I8-B)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("renders verdict from management data (no separate console fetch)", async () => {
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("activation-verdict"));
    expect(screen.getByTestId("activation-verdict").textContent).toContain("Ready");
    expect(screen.getByTestId("verdict-headline").textContent).toBe("Ready for aspirants");
    // Ensure NO separate /console/exams/ request was made
    const consoleCalls = api.get.mock.calls.filter(([u]) => u.includes("/console/exams/"));
    expect(consoleCalls.length).toBe(0);
  });

  test("management endpoint called for exam_id", async () => {
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("activation-verdict"));
    const mgmtCalls = api.get.mock.calls.filter(([u]) => u.includes("/management/exams/exam-1"));
    expect(mgmtCalls.length).toBeGreaterThan(0);
  });

  test("embedded mode: no action-console-back or action-console-workspace nav shown", async () => {
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("activation-verdict"));
    expect(screen.queryByTestId("action-console-back")).toBeNull();
    expect(screen.queryByTestId("action-console-workspace")).toBeNull();
    expect(screen.queryByTestId("action-console-name")).toBeNull();
  });

  test("action queue renders when management returns actions with real CTA routes", async () => {
    const mgmtWithActions = {
      ...MANAGEMENT_RESPONSE,
      activation_verdict: { status: "blocked", headline: "Not ready", reasons: [] },
      action_queue: [
        { id: "setup", severity: "blocker", area: "setup", title: "Fix setup",
          why: "No phases defined", cta_label: "Go to Setup",
          cta_route: "/admin/exam-intelligence/exams/exam-1?tab=setup",
          entity_kind: null, entity_id: null, evidence_refs: [], status: "open" },
      ],
      activation_checks: [],
      stages: [],
    };
    mockAllEndpoints({ managementResponse: mgmtWithActions });
    renderWorkspace();
    await waitFor(() => screen.getByTestId("action-queue"));
    expect(screen.getByTestId("action-setup")).toBeTruthy();
    expect(screen.getByTestId("action-cta-setup").getAttribute("href"))
      .toBe("/admin/exam-intelligence/exams/exam-1?tab=setup");
  });
});

// ── PR2 Tests: readiness provider ─────────────────────────────────────────────

describe("ExamWorkspace readiness provider (PR2)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("provider exposes readiness after fetch", async () => {
    mockAllEndpoints();
    let captured = null;

    function ReadinessCapture() {
      const { readiness } = useExamWorkspace();
      captured = readiness;
      return null;
    }

    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/exams/exam-1"]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/exams/:exam_id"
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
      if (url.includes("/management/exams/")) return Promise.resolve(MANAGEMENT_RESPONSE);
      return Promise.resolve(CONTEXT_RESPONSE);
    });
    renderWorkspace();
    // Shell renders normally despite readiness failure
    await waitFor(() => expect(screen.getByTestId("exam-name")).toBeTruthy());
    // workspace-error should NOT appear (that's only for context failure)
    expect(screen.queryByTestId("workspace-error")).toBeNull();
  });

  test("refetchReadiness re-fires the readiness call", async () => {
    mockAllEndpoints();
    let captured = null;

    function ReadinessHarness() {
      const { readiness, refetchReadiness } = useExamWorkspace();
      captured = { readiness, refetchReadiness };
      return null;
    }

    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/exams/exam-1"]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/exams/:exam_id"
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

  test("standalone workspace at /exams/ keeps the tab strip and renders no rail (regression)", async () => {
    mockAllEndpoints({ readinessResponse: STANDALONE_READINESS });
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/exams/exam-1"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/exams/:exam_id" element={<ExamWorkspace />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByTestId("tab-strip"));
    expect(screen.getAllByRole("tab")).toHaveLength(7);
    expect(screen.getByTestId("cycle-picker")).toBeTruthy();
    // verdict headline comes from management response (not workspace readiness)
    expect(screen.getByTestId("smart-header-verdict")).toBeTruthy();
    // tab strip review tab still shows the advisory readiness percentage
    expect(screen.getByTestId("tab-review").textContent).toContain("40%");
    expect(screen.queryByTestId("exam-task-rail")).toBeNull();
    expect(screen.queryByTestId("console-rail-layout")).toBeNull();
  });
});

// ── B2: standalone fetch regression ─────────────────────────────────────────

describe("ExamWorkspace standalone fetch regression (B2)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("fetches context, readiness, and management once on initial mount (no current_cycle = no extra fetch)", async () => {
    // MANAGEMENT_RESPONSE has current_cycle: null → no cycle normalization → 1 fetch each
    mockAllEndpoints({ readinessResponse: STANDALONE_READINESS });
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/exams/exam-1"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/exams/:exam_id" element={<ExamWorkspace />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByTestId("exam-name"));
    const contextCalls = api.get.mock.calls.filter(([url]) => url.includes("/context"));
    const readinessCalls = api.get.mock.calls.filter(([url]) => url.includes("/readiness"));
    const mgmtCalls = api.get.mock.calls.filter(([url]) => url.includes("/management/exams/"));
    expect(contextCalls).toHaveLength(1);
    expect(readinessCalls).toHaveLength(1);
    expect(mgmtCalls).toHaveLength(1);
    // No separate console fetch in embedded mode
    expect(api.get.mock.calls.filter(([url]) => url.includes("/console/exams/"))).toHaveLength(0);
  });
});

// ── B2: standalone review surface ───────────────────────────────────────────

describe("ExamWorkspace standalone review surface (B2)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("review tab renders ReviewActivatePanel without extra readiness fetch", async () => {
    mockAllEndpoints({ readinessResponse: STANDALONE_READINESS });
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/exams/exam-1?tab=review"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/exams/:exam_id" element={<ExamWorkspace />} />
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


// ── Management data loading/error race prevention ─────────────────────────────

describe("ExamWorkspace management-data race prevention", () => {
  test("shows loading state while management data is pending", async () => {
    let resolveMgmt;
    const mgmtPromise = new Promise((resolve) => { resolveMgmt = resolve; });
    api.get.mockImplementation((url) => {
      if (url.includes("/management/exams/")) return mgmtPromise;
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      return Promise.resolve(CONTEXT_RESPONSE);
    });

    renderWorkspace();
    // Shell must render (context loaded) but console must show loading, not fetch /console/exams/
    await waitFor(() => expect(screen.queryByTestId("workspace-loading")).not.toBeInTheDocument());
    expect(screen.getByTestId("action-console-loading")).toBeInTheDocument();
    expect(api.get).not.toHaveBeenCalledWith(expect.stringContaining("/console/exams/"));
    resolveMgmt(MANAGEMENT_RESPONSE);
    await waitFor(() => expect(screen.getByTestId("exam-action-console")).toBeInTheDocument());
  });

  test("shows error + Retry when management request fails, zero console calls", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/management/exams/")) return Promise.reject(new Error("500"));
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      return Promise.resolve(CONTEXT_RESPONSE);
    });

    renderWorkspace();
    await waitFor(() => expect(screen.getByTestId("action-console-error")).toBeInTheDocument());
    expect(screen.getByTestId("action-console-retry")).toBeInTheDocument();
    expect(api.get).not.toHaveBeenCalledWith(expect.stringContaining("/console/exams/"));
  });

  test("Retry restores management data", async () => {
    let callCount = 0;
    api.get.mockImplementation((url) => {
      if (url.includes("/management/exams/")) {
        callCount++;
        return callCount === 1 ? Promise.reject(new Error("500")) : Promise.resolve(MANAGEMENT_RESPONSE);
      }
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      return Promise.resolve(CONTEXT_RESPONSE);
    });

    renderWorkspace();
    await waitFor(() => expect(screen.getByTestId("action-console-error")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("action-console-retry"));
    await waitFor(() => expect(screen.getByTestId("exam-action-console")).toBeInTheDocument());
  });
});

// ── I8-B: deep-link row passing to panels ────────────────────────────────────

describe("ExamWorkspace deep-link panel receiving (I8-B)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("?tab=updates&row=upd-1 shows not-found banner when update absent from list", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      if (url.includes("/management/exams/")) return Promise.resolve(MANAGEMENT_RESPONSE);
      if (url.includes("/policy-updates")) return Promise.resolve({ items: [] });
      return Promise.resolve(CONTEXT_RESPONSE);
    });
    renderWorkspace("exam-1", null, "?tab=updates&row=upd-1");
    await waitFor(() =>
      expect(screen.getByTestId("update-deep-link-not-found")).toBeInTheDocument(),
    );
  });

  test("?tab=updates&row=upd-1 hides not-found banner when update exists", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      if (url.includes("/management/exams/")) return Promise.resolve(MANAGEMENT_RESPONSE);
      if (url.includes("/policy-updates")) return Promise.resolve({
        items: [
          { id: "upd-1", title: "Test policy update", reviewer_status: "pending",
            source_type: "official", affects_plan: false, change_summary: null },
        ],
      });
      return Promise.resolve(CONTEXT_RESPONSE);
    });
    renderWorkspace("exam-1", null, "?tab=updates&row=upd-1");
    await waitFor(() => screen.getByTestId("tab-updates"));
    // Wait for load to settle — no not-found banner
    await waitFor(() =>
      expect(screen.queryByTestId("update-deep-link-not-found")).toBeNull(),
    );
  });

  test("?tab=documents&document=da-1 fetches asset from document_assets ID space and shows highlighted card", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      if (url.includes("/management/exams/")) return Promise.resolve(MANAGEMENT_RESPONSE);
      if (url.includes("/documents/da-1")) return Promise.resolve({
        document: { id: "da-1", filename: "syllabus-2026.pdf" },
        extraction: { status: "succeeded" },
        pages_count: 42,
      });
      if (url.includes("/syllabus-documents")) return Promise.resolve({ items: [] });
      if (url.includes("/pyq-papers")) return Promise.resolve({ items: [] });
      return Promise.resolve(CONTEXT_RESPONSE);
    });
    renderWorkspace("exam-1", null, "?tab=documents&document=da-1");
    await waitFor(() =>
      expect(screen.getByTestId("doc-deep-link-asset")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("doc-deep-link-not-found")).toBeNull();
  });

  test("?tab=documents&document=da-missing shows not-found when asset fetch fails", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve(READINESS_RESPONSE);
      if (url.includes("/management/exams/")) return Promise.resolve(MANAGEMENT_RESPONSE);
      if (url.includes("/documents/da-missing")) return Promise.reject(new Error("Not found"));
      if (url.includes("/syllabus-documents")) return Promise.resolve({ items: [] });
      if (url.includes("/pyq-papers")) return Promise.resolve({ items: [] });
      return Promise.resolve(CONTEXT_RESPONSE);
    });
    renderWorkspace("exam-1", null, "?tab=documents&document=da-missing");
    await waitFor(() =>
      expect(screen.getByTestId("doc-deep-link-not-found")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("doc-deep-link-asset")).toBeNull();
  });
});

// ── I8-C: More → Advanced Repair overflow menu ───────────────────────────────

describe("ExamWorkspace More menu (I8-C)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset to non-cms user before each test (mutates the closure variable)
    mockAuthUser = { role: "admin", permissions: [] };
  });

  test("operator with exam_intelligence.cms sees More trigger", async () => {
    mockAuthUser = { role: "admin", permissions: ["exam_intelligence.cms"] };
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.getByTestId("workspace-more-trigger")).toBeTruthy();
  });

  test("super_admin sees More trigger", async () => {
    mockAuthUser = { role: "super_admin", permissions: [] };
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.getByTestId("workspace-more-trigger")).toBeTruthy();
  });

  test("operator without cms permission does not see More trigger", async () => {
    // beforeEach sets { role: "admin", permissions: [] } — no cms permission
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.queryByTestId("workspace-more-trigger")).toBeNull();
  });

  test("More trigger has aria-haspopup menu (not a primary CTA)", async () => {
    mockAuthUser = { role: "super_admin", permissions: [] };
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("workspace-more-trigger"));
    const trigger = screen.getByTestId("workspace-more-trigger");
    expect(trigger.getAttribute("aria-haspopup")).toBe("menu");
    expect(trigger.className).not.toContain("primary");
  });

  test("clicking More trigger opens the menu with Advanced Repair item", async () => {
    mockAuthUser = { role: "super_admin", permissions: [] };
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("workspace-more-trigger"));
    fireEvent.click(screen.getByTestId("workspace-more-trigger"));
    expect(screen.getByTestId("workspace-more-menu")).toBeTruthy();
    expect(screen.getByTestId("workspace-advanced-repair-link")).toBeTruthy();
  });

  test("Advanced Repair link includes exam_id", async () => {
    mockAuthUser = { role: "super_admin", permissions: [] };
    mockAllEndpoints();
    renderWorkspace("exam-42");
    await waitFor(() => screen.getByTestId("workspace-more-trigger"));
    fireEvent.click(screen.getByTestId("workspace-more-trigger"));
    const link = screen.getByTestId("workspace-advanced-repair-link");
    expect(link.getAttribute("href")).toContain("exam_id=exam-42");
  });

  test("Advanced Repair link includes cycle_id when cycle is selected", async () => {
    mockAuthUser = { role: "super_admin", permissions: [] };
    mockAllEndpoints();
    renderWorkspace("exam-1", "cycle-2026");
    await waitFor(() => screen.getByTestId("workspace-more-trigger"));
    fireEvent.click(screen.getByTestId("workspace-more-trigger"));
    const link = screen.getByTestId("workspace-advanced-repair-link");
    expect(link.getAttribute("href")).toContain("cycle_id=cycle-2026");
  });

  test("Advanced Repair link omits cycle_id when no cycle is selected", async () => {
    mockAuthUser = { role: "super_admin", permissions: [] };
    mockAllEndpoints();
    renderWorkspace("exam-1", null);
    await waitFor(() => screen.getByTestId("workspace-more-trigger"));
    fireEvent.click(screen.getByTestId("workspace-more-trigger"));
    const link = screen.getByTestId("workspace-advanced-repair-link");
    expect(link.getAttribute("href")).not.toContain("cycle_id");
  });

  test("Escape key closes the More menu", async () => {
    mockAuthUser = { role: "super_admin", permissions: [] };
    mockAllEndpoints();
    renderWorkspace();
    await waitFor(() => screen.getByTestId("workspace-more-trigger"));
    fireEvent.click(screen.getByTestId("workspace-more-trigger"));
    expect(screen.getByTestId("workspace-more-menu")).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByTestId("workspace-more-menu")).toBeNull());
  });
});
