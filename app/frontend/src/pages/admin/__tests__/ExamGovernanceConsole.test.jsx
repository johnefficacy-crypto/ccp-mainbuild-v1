/**
 * Tests for the Exam Governance Console.
 *
 * Wave 4.6H-FE: the no-exam view now renders the ConsoleWorkQueue against the
 * truthful work-queue endpoints (/console/exams + /console/summary), NOT
 * ExamListShell against /exams. The selected-exam view still mounts the
 * embedded <ExamWorkspace variant="console" />. Role gate + route wrapping +
 * Registry regression are unchanged.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
  auth: {},
}));

jest.mock("../../../lib/supabase", () => ({
  __esModule: true,
  supabase: {
    auth: {
      getSession: jest.fn(),
      onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })),
    },
  },
}));

jest.mock("../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: jest.fn(),
}));

// Defensive: keep the env-loading hook inert in the frontend CI job.
jest.mock("../../../lib/hooks/useApiCollection", () => ({
  __esModule: true,
  default: jest.fn(),
}));

const { api } = require("../../../lib/api");
const { useAuth } = require("../../../lib/authContext");

const ExamGovernanceConsole = require("../ExamGovernanceConsole").default;
const useSelectedExamId = require("../../../lib/hooks/useSelectedExamId").default;
const { ProtectedRoute } = require("../../../lib/ProtectedRoute");
const { ADMIN_ROLES } = require("../../../lib/rbac");
const { adminRouteElements } = require("../../../routes/adminRoutes");
const RouteErrorBoundary = require("../../../components/RouteErrorBoundary").default;

// ── Fixtures ──────────────────────────────────────────────────────────────────

const ROWS = [
  {
    id: "exam-1", slug: "ssc-cgl", name: "SSC CGL", exam_type: "recruitment",
    management_mode: "core", cadence: "annual", exam_family_id: null,
    organization_name: "Staff Selection Commission",
    status: "blocked", flags: ["missing_coverage", "pending_review"],
    blocker_count: 2, first_blocker_text: "No locked topic coverage — planner cannot use this exam",
    locked_coverage_count: 0, verified_pyq_count: 0, total_pyq_count: 42,
  },
  {
    id: "exam-2", slug: "upsc-cse", name: "UPSC CSE", exam_type: "entrance",
    management_mode: "light", cadence: "annual", exam_family_id: null,
    organization_name: null,
    status: "ready", flags: [], blocker_count: 0, first_blocker_text: null,
    locked_coverage_count: 5, verified_pyq_count: 3, total_pyq_count: 9,
  },
];

const SUMMARY = {
  blocked: 1, needs_action: 0, ready: 1, pending_review: 1, stale_review_queue: 0,
  total_count: 2, generated_at: "2026-06-17T00:00:00Z",
};

function ctxFor(examId) {
  const name = examId === "exam-2" ? "UPSC CSE" : "SSC CGL";
  return { exam: { id: examId, name, exam_type: "recruitment" },
           cycle: null, cycles: [], phases: [], organization: null, family: null };
}

const READINESS = {
  exam_id: "exam-1", cycle_id: null,
  overall: { status: "empty", score_percent: 0, ready_to_activate: false, blockers: [] },
  sections: [],
};

function mockApi(overrides = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/console/summary")) {
      return overrides.summary ? overrides.summary(url) : Promise.resolve(SUMMARY);
    }
    if (url.includes("/console/exams")) {
      return overrides.list ? overrides.list(url)
        : Promise.resolve({ items: ROWS, count: 2, total_count: 2, has_next: true, limit: 25, offset: 0 });
    }
    if (url.includes("exam-families")) return Promise.resolve({ items: [] });
    if (url.includes("/readiness")) return Promise.resolve(READINESS);
    if (url.includes("/workspace/") && url.includes("/context")) {
      const m = url.match(/\/workspace\/([^/?]+)\/context/);
      return Promise.resolve(ctxFor(m ? decodeURIComponent(m[1]) : "exam-1"));
    }
    return Promise.resolve({});
  });
}

function renderConsole(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/exam-intelligence/console" element={<ExamGovernanceConsole />} />
        <Route path="/admin/exam-intelligence/console/:exam_id" element={<ExamGovernanceConsole />} />
      </Routes>
    </MemoryRouter>,
  );
}

const listCalls = () => api.get.mock.calls.map((c) => c[0]).filter((u) => u.includes("/console/exams"));
const summaryCalls = () => api.get.mock.calls.map((c) => c[0]).filter((u) => u.includes("/console/summary"));

beforeEach(() => {
  jest.clearAllMocks();
  useAuth.mockReturnValue({ isChecking: false, isAuthed: true, hasBackendSession: true, user: { role: "admin" } });
});

// ── Console work-queue (4.6H-FE) ───────────────────────────────────────────

describe("ExamGovernanceConsole — work queue (no exam selected)", () => {
  test("renders the work queue and calls /console/exams (not /exams)", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    expect(listCalls().length).toBeGreaterThan(0);
    // It must NOT use the generic /exams contract in console mode.
    expect(api.get.mock.calls.every((c) => !c[0].includes("/exam-intelligence/exams"))).toBe(true);
    expect(screen.queryByTestId("exam-list-shell")).toBeNull();
  });

  test("default list params: limit/offset/active_state/sort, no workflow", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    const url = listCalls()[0];
    expect(url).toContain("limit=25");
    expect(url).toContain("offset=0");
    expect(url).toContain("active_state=active");
    expect(url).toContain("sort=blockers_first");
    expect(url).not.toContain("workflow=");
  });

  test("summary gets the same base filters incl. q, never workflow/sort/limit/offset", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());

    api.get.mockClear();
    mockApi();
    fireEvent.change(screen.getByTestId("console-search"), { target: { value: "ssc" } });
    await waitFor(() => expect(summaryCalls().some((u) => u.includes("q=ssc"))).toBe(true));

    const sUrl = summaryCalls().find((u) => u.includes("q=ssc"));
    expect(sUrl).not.toMatch(/workflow=|sort=|limit=|offset=/);
    expect(listCalls().some((u) => u.includes("q=ssc"))).toBe(true);
  });

  test("workflow goes only to the list; summary is not refetched on workflow change", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());

    api.get.mockClear();
    mockApi();
    fireEvent.click(screen.getByTestId("console-chip-blocked"));
    await waitFor(() => expect(listCalls().some((u) => u.includes("workflow=blocked"))).toBe(true));

    expect(screen.getByTestId("console-chip-blocked").getAttribute("aria-pressed")).toBe("true");
    expect(summaryCalls().length).toBe(0); // base filters unchanged → no summary refetch
    expect(summaryCalls().every((u) => !u.includes("workflow="))).toBe(true);
  });

  test("sort goes only to the list and is server-driven", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());

    api.get.mockClear();
    mockApi();
    fireEvent.change(screen.getByTestId("console-sort"), { target: { value: "name" } });
    await waitFor(() => expect(listCalls().some((u) => u.includes("sort=name"))).toBe(true));
    expect(summaryCalls().length).toBe(0);
  });

  test("selecting a workflow after paging resets offset to 0", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-next")).toBeTruthy());
    fireEvent.click(screen.getByTestId("console-next"));
    await waitFor(() => expect(listCalls().some((u) => u.includes("offset=25"))).toBe(true));

    api.get.mockClear();
    mockApi();
    fireEvent.click(screen.getByTestId("console-chip-ready"));
    await waitFor(() => expect(listCalls().some((u) => u.includes("workflow=ready"))).toBe(true));
    expect(listCalls().every((u) => u.includes("offset=0"))).toBe(true);
  });

  test("summary strip shows base-scoped counts as accessible buttons", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-summary-strip")).toBeTruthy());
    expect(screen.getByTestId("console-chip-all").textContent).toContain("2");
    expect(screen.getByTestId("console-chip-blocked").textContent).toContain("1");
    expect(screen.getByTestId("console-chip-ready").textContent).toContain("1");
    expect(screen.getByTestId("console-chip-pending_review").textContent).toContain("1");
    expect(screen.getByTestId("console-chip-stale_review_queue").textContent).toContain("0");
  });

  test("Missing PYQ + Missing coverage render with NO fabricated count, no thin_mock_bank", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    const mpyq = screen.getByTestId("console-chip-missing_pyq");
    const mcov = screen.getByTestId("console-chip-missing_coverage");
    expect(mpyq.textContent).toMatch(/Missing PYQ/);
    expect(mpyq.textContent).not.toMatch(/\d/); // no number, never "0"
    expect(mcov.textContent).not.toMatch(/\d/);
    expect(screen.queryByTestId("console-chip-thin_mock_bank")).toBeNull();
    expect(screen.queryByText(/thin mock/i)).toBeNull();
  });

  test("row renders org, status, blocker text/count, locked coverage, verified/total pyq, human flags", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-row-exam-1")).toBeTruthy());

    expect(screen.getByTestId("console-org-exam-1").textContent).toBe("Staff Selection Commission");
    expect(screen.getByTestId("console-org-exam-2").textContent).toBe("—"); // null → em dash
    expect(screen.getByTestId("console-status-exam-1").textContent).toContain("Blocked");
    expect(screen.getByTestId("console-blocker-exam-1").textContent).toContain("No locked topic coverage");
    expect(screen.getByTestId("console-blocker-exam-1").textContent).toContain("more"); // blocker_count 2
    expect(screen.getByTestId("console-blocker-exam-2").textContent).toContain("No hard blocker");
    expect(screen.getByTestId("console-coverage-exam-2").textContent).toContain("5");
    expect(screen.getByTestId("console-pyq-exam-2").textContent).toContain("3");
    expect(screen.getByTestId("console-pyq-exam-2").textContent).toContain("9");
    // human-readable flags, not raw tokens
    expect(screen.getByTestId("console-flag-exam-1-missing_coverage").textContent).toBe("Missing locked coverage");
    expect(screen.getByTestId("console-flag-exam-1-pending_review").textContent).toBe("Pending review");
  });

  test("row actions: primary → /console/:id, secondary → /workspace/:id", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-open-exam-1")).toBeTruthy());
    expect(screen.getByTestId("console-open-exam-1").getAttribute("href")).toBe("/admin/exam-intelligence/console/exam-1");
    expect(screen.getByTestId("console-workspace-exam-1").getAttribute("href")).toBe("/admin/exam-intelligence/workspace/exam-1");
  });

  test("no readiness/confidence percentage and no raw readiness_level/pyq_coverage_status", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    expect(document.body.textContent).not.toMatch(/%/);
    expect(document.body.textContent).not.toMatch(/readiness_level|pyq_coverage_status|confidence/i);
  });

  test("list error renders no seed data; list retry refetches the list", async () => {
    mockApi({ list: () => Promise.reject(new Error("boom")) });
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-error")).toBeTruthy());
    expect(screen.queryByTestId("console-table")).toBeNull();
    expect(screen.queryByText("SSC CGL")).toBeNull();
  });

  test("summary error does NOT replace valid list data with zeros", async () => {
    mockApi({ summary: () => Promise.reject(new Error("summary down")) });
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    // list still usable
    expect(screen.getByTestId("console-row-exam-1")).toBeTruthy();
    // honest summary failure, no fabricated zero counts on chips
    expect(screen.getByTestId("console-summary-error")).toBeTruthy();
    expect(screen.getByTestId("console-chip-blocked").textContent).not.toMatch(/\d/);
  });

  test("empty state accounts for workflow and offers clears", async () => {
    mockApi({ list: () => Promise.resolve({ items: [], total_count: 0, has_next: false }) });
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-empty")).toBeTruthy());
    expect(screen.getByTestId("console-empty").textContent).toMatch(/search, filters or workflow/i);
  });
});

// ── Selected-exam view still mounts the embedded workspace ──────────────────

describe("ExamGovernanceConsole — exam selected", () => {
  test("renders top bar + embedded workspace scoped to the URL exam", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.getByTestId("console-selected-exam").textContent).toBe("exam-1");
    expect(screen.getByTestId("exam-name").textContent).toBe("SSC CGL");
    expect(api.get.mock.calls.map((c) => c[0]).some((u) => u.includes("/workspace/exam-1/context"))).toBe(true);
    // It did not call the work-queue endpoints in selected-exam mode.
    expect(listCalls().length).toBe(0);
  });

  test("no readiness percentage anywhere on the selected-exam console (D-E)", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.getByTestId("console-top-bar").textContent).not.toMatch(/%/);
    expect(document.body.textContent).not.toContain("%");
  });
});

// ── URL is the single source of truth ───────────────────────────────────────

describe("URL selected-exam is the single source of truth", () => {
  test("a different :exam_id renders the other exam", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-2");
    await waitFor(() => screen.getByTestId("exam-name"));
    expect(screen.getByTestId("console-selected-exam").textContent).toBe("exam-2");
    expect(screen.getByTestId("exam-name").textContent).toBe("UPSC CSE");
  });

  test("changing the param swaps the exam with no stale value retained", async () => {
    function Probe() {
      const id = useSelectedExamId();
      const navigate = useNavigate();
      return (
        <div>
          <div data-testid="sel">{id ?? "none"}</div>
          <button onClick={() => navigate("/admin/exam-intelligence/console/exam-2")}>go</button>
        </div>
      );
    }
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/console/exam-1"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/console" element={<Probe />} />
          <Route path="/admin/exam-intelligence/console/:exam_id" element={<Probe />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("sel").textContent).toBe("exam-1");
    fireEvent.click(screen.getByText("go"));
    await waitFor(() => expect(screen.getByTestId("sel").textContent).toBe("exam-2"));
  });

  test("useSelectedExamId returns null when no exam is in the URL", () => {
    function Probe() {
      const id = useSelectedExamId();
      return <div data-testid="sel">{id ?? "none"}</div>;
    }
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/console"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/console" element={<Probe />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("sel").textContent).toBe("none");
  });
});

// ── Role gate matches sibling KG routes ──────────────────────────────────────

describe("Console role gate (matches sibling KG routes)", () => {
  function renderGated(path = "/admin/exam-intelligence/console") {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/console"
            element={
              <ProtectedRoute role={ADMIN_ROLES} requireBackend>
                <div data-testid="gated-ok">console</div>
              </ProtectedRoute>
            }
          />
          <Route path="/app" element={<div data-testid="redirect-app">app</div>} />
          <Route path="/login" element={<div data-testid="redirect-login">login</div>} />
        </Routes>
      </MemoryRouter>,
    );
  }

  test("admin sees the console", () => {
    useAuth.mockReturnValue({ isChecking: false, isAuthed: true, hasBackendSession: true, user: { role: "admin" } });
    renderGated();
    expect(screen.getByTestId("gated-ok")).toBeTruthy();
  });

  test("non-admin is redirected to /app", () => {
    useAuth.mockReturnValue({ isChecking: false, isAuthed: true, hasBackendSession: true, user: { role: "user" } });
    renderGated();
    expect(screen.queryByTestId("gated-ok")).toBeNull();
    expect(screen.getByTestId("redirect-app")).toBeTruthy();
  });

  test("unauthenticated is redirected to /login", () => {
    useAuth.mockReturnValue({ isChecking: false, isAuthed: false, hasBackendSession: false, user: null });
    renderGated();
    expect(screen.queryByTestId("gated-ok")).toBeNull();
    expect(screen.getByTestId("redirect-login")).toBeTruthy();
  });
});

// ── Route presence + RouteErrorBoundary wrapping + Registry regression ───────

describe("adminRoutes — console routes wrapping + regression", () => {
  function collect(node, underBoundary, acc) {
    if (node == null || typeof node !== "object") return;
    if (Array.isArray(node)) { node.forEach((n) => collect(n, underBoundary, acc)); return; }
    const elementType = node.props?.element?.type;
    const isErrorBoundaryRoute = elementType === RouteErrorBoundary;
    const nextUnder = underBoundary || isErrorBoundaryRoute;
    if (node.props?.path) acc[node.props.path] = underBoundary;
    if (node.props?.children) collect(node.props.children, nextUnder, acc);
  }

  const paths = {};
  collect(adminRouteElements, false, paths);

  test("both console routes exist", () => {
    expect(Object.keys(paths)).toContain("/admin/exam-intelligence/console");
    expect(Object.keys(paths)).toContain("/admin/exam-intelligence/console/:exam_id");
  });

  test("console routes are wrapped by RouteErrorBoundary", () => {
    expect(paths["/admin/exam-intelligence/console"]).toBe(true);
    expect(paths["/admin/exam-intelligence/console/:exam_id"]).toBe(true);
  });

  test("regression: Registry and sibling exam-intelligence routes still resolve", () => {
    const keys = Object.keys(paths);
    expect(keys).toContain("/admin/exam-intelligence");
    expect(keys).toContain("/admin/exam-intelligence/cms");
    expect(keys).toContain("/admin/exam-intelligence/new");
    expect(keys).toContain("/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace");
    expect(keys).toContain("/admin/exam-intelligence/workspace/:exam_id");
    expect(keys).toContain("/admin/exam-intelligence/workspace/:exam_id/:cycle_id");
  });
});
