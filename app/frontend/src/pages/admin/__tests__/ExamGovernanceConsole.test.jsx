/**
 * Tests for Wave 4.6A — Exam Governance Console shell + URL selected-exam.
 *
 * Covers:
 * - /console (no param) renders the exam picker built from the Registry read.
 * - /console/:exam_id renders the embedded workspace scoped to that exam.
 * - URL is the single source of truth: changing :exam_id swaps the exam with
 *   no stale selected-exam retained (useSelectedExamId is read-through).
 * - Role gate matches sibling KG routes (non-admin / unauthenticated blocked).
 * - Console routes are present and wrapped by RouteErrorBoundary; Registry and
 *   sibling exam-intelligence routes still resolve (regression).
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

// useApiCollection imports shared/config/env, which throws when
// REACT_APP_BACKEND_URL is unset (the case in the frontend CI job). Mock it
// the same way the sibling admin tests do so the env module never loads.
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

const EXAMS = [
  { id: "exam-1", name: "SSC CGL", slug: "ssc-cgl" },
  { id: "exam-2", name: "UPSC CSE", slug: "upsc-cse" },
];

function ctxFor(examId) {
  const name = examId === "exam-2" ? "UPSC CSE" : "SSC CGL";
  return {
    exam: { id: examId, name, exam_type: "recruitment" },
    cycle: null,
    cycles: [],
    phases: [],
    organization: null,
    family: null,
  };
}

const READINESS = {
  exam_id: "exam-1",
  cycle_id: null,
  overall: { status: "empty", score_percent: 0, ready_to_activate: false, blockers: [] },
  sections: [],
};

// Routes api.get by URL: exam list, workspace context (per exam id), readiness.
function mockApi() {
  api.get.mockImplementation((url) => {
    if (url.includes("/exam-intelligence/exams")) {
      return Promise.resolve({ items: EXAMS });
    }
    if (url.includes("/readiness")) return Promise.resolve(READINESS);
    if (url.includes("/workspace/") && url.includes("/context")) {
      const m = url.match(/\/workspace\/([^/?]+)\/context/);
      const examId = m ? decodeURIComponent(m[1]) : "exam-1";
      return Promise.resolve(ctxFor(examId));
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

beforeEach(() => {
  jest.clearAllMocks();
  // Default auth: admin (overridden in role-gate tests).
  useAuth.mockReturnValue({
    isChecking: false,
    isAuthed: true,
    hasBackendSession: true,
    user: { role: "admin" },
  });
});

// ── Test 1: picker is now the reusable ExamListShell (searchable + paginated) ──

describe("ExamGovernanceConsole — no exam selected (4.6G list shell)", () => {
  test("renders a searchable + filterable list (not flat buttons) from /exams", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");

    await waitFor(() => expect(screen.getByTestId("exam-list-shell")).toBeTruthy());
    // Real search input + the supported /exams filters, not a flat button list.
    expect(screen.getByTestId("exam-list-search")).toBeTruthy();
    expect(screen.getByTestId("exam-list-filter-type")).toBeTruthy();
    expect(screen.getByTestId("exam-list-filter-active")).toBeTruthy();
    expect(screen.getByTestId("exam-list-filter-lane")).toBeTruthy();
    expect(screen.getByTestId("exam-list-filter-cadence")).toBeTruthy();
    expect(screen.queryByTestId("exam-picker-list")).toBeNull(); // old flat picker gone

    await waitFor(() => expect(screen.getByTestId("exam-list-table")).toBeTruthy());
    expect(screen.getByTestId("exam-list-row-exam-1")).toBeTruthy();
    expect(screen.getByTestId("exam-list-row-exam-2")).toBeTruthy();
  });

  test("row primary opens the console, secondary opens the advanced workspace", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-open-exam-1")).toBeTruthy());

    expect(screen.getByTestId("console-open-exam-1").getAttribute("href")).toBe(
      "/admin/exam-intelligence/console/exam-1",
    );
    expect(screen.getByTestId("console-workspace-exam-1").getAttribute("href")).toBe(
      "/admin/exam-intelligence/workspace/exam-1",
    );
    expect(screen.getByTestId("console-open-exam-1").textContent).toContain("Open console");
    expect(screen.getByTestId("console-workspace-exam-1").textContent).toContain("Advanced workspace");
  });

  test("the list read targets /exams with the supported params (limit/offset/active_state)", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("exam-list-table")).toBeTruthy());

    const examUrl = api.get.mock.calls.map((c) => c[0]).find((u) => u.includes("/exam-intelligence/exams"));
    expect(examUrl).toContain("limit=25");
    expect(examUrl).toContain("offset=0");
    expect(examUrl).toContain("active_state=active");
  });

  test("typing a search term sends q to /exams", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("exam-list-table")).toBeTruthy());

    api.get.mockClear();
    mockApi();
    fireEvent.change(screen.getByTestId("exam-list-search"), { target: { value: "upsc" } });

    await waitFor(() =>
      expect(api.get.mock.calls.some((c) => c[0].includes("q=upsc"))).toBe(true),
    );
  });

  test("renders no workflow chips and no fake work-queue counts", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("exam-list-table")).toBeTruthy());

    // 4.6H concepts must NOT appear in 4.6G.
    ["Needs action", "Blocked", "Missing PYQ", "Missing coverage", "Stale", "Ready to activate"].forEach(
      (label) => expect(screen.queryByText(label)).toBeNull(),
    );
    // The honest count reflects returned rows only (2), never a synthesized total.
    expect(screen.getByTestId("exam-list-count").textContent).toContain("2 exam");
  });

  test("empty state renders no seed/mock data and offers a reset", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/exam-intelligence/exams")) return Promise.resolve({ items: [], total_count: 0 });
      return Promise.resolve({});
    });
    renderConsole("/admin/exam-intelligence/console");

    await waitFor(() => expect(screen.getByTestId("exam-list-empty")).toBeTruthy());
    expect(screen.queryByTestId("exam-list-table")).toBeNull();
    expect(screen.queryByText("SSC CGL")).toBeNull();
    expect(screen.queryByText("UPSC CSE")).toBeNull();
  });

  test("error state renders no seed/mock data", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/exam-intelligence/exams")) return Promise.reject(new Error("boom"));
      return Promise.resolve({});
    });
    renderConsole("/admin/exam-intelligence/console");

    await waitFor(() => expect(screen.getByTestId("exam-list-error")).toBeTruthy());
    expect(screen.queryByTestId("exam-list-table")).toBeNull();
    expect(screen.queryByText("SSC CGL")).toBeNull();
  });
});

// ── Test 2: embedded workspace scoped to exam ──────────────────────────────────

describe("ExamGovernanceConsole — exam selected", () => {
  test("renders top bar + embedded workspace scoped to the URL exam", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");

    await waitFor(() => screen.getByTestId("exam-name"));
    // Top bar reads identity straight from the URL (no readiness %, no fetch).
    expect(screen.getByTestId("console-selected-exam").textContent).toBe("exam-1");
    // Embedded workspace rendered its own header for the same exam.
    expect(screen.getByTestId("exam-name").textContent).toBe("SSC CGL");

    // Workspace fetched context scoped to exam-1.
    const urls = api.get.mock.calls.map((c) => c[0]);
    expect(urls.some((u) => u.includes("/workspace/exam-1/context"))).toBe(true);
  });

  test("does not show a readiness percentage anywhere on the console (D-E)", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => screen.getByTestId("exam-name"));
    // The embedded workspace mounts with variant="console", so no "%" should
    // appear in the top bar, smart header, tab strip, or Overview scorecard.
    expect(screen.getByTestId("console-top-bar").textContent).not.toMatch(/%/);
    expect(document.body.textContent).not.toContain("%");
  });
});

// ── Test 3: URL is the single source of truth ──────────────────────────────────

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

// ── Test 4: role gate matches sibling KG routes ────────────────────────────────

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

// ── Test 5 + 6: route presence + RouteErrorBoundary wrapping ───────────────────

describe("adminRoutes — console routes wrapping + regression", () => {
  // Walk the static <Route> element tree, tracking whether each path-bearing
  // Route sits under a RouteErrorBoundary element route.
  function collect(node, underBoundary, acc) {
    if (node == null || typeof node !== "object") return;
    if (Array.isArray(node)) {
      node.forEach((n) => collect(n, underBoundary, acc));
      return;
    }
    const isRoute = node.type && node.type.name !== "Fragment" && node.props && "element" in node.props && ("path" in node.props || "index" in node.props || node.props.children);
    const elementType = node.props?.element?.type;
    const isErrorBoundaryRoute = elementType === RouteErrorBoundary;
    const nextUnder = underBoundary || isErrorBoundaryRoute;
    if (node.props?.path) {
      acc[node.props.path] = underBoundary; // wrapping state at this route's level
    }
    if (node.props?.children) collect(node.props.children, nextUnder, acc);
    // ignore isRoute lint var
    void isRoute;
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
    expect(keys).toContain("/admin/exam-intelligence"); // Registry stays
    expect(keys).toContain("/admin/exam-intelligence/cms");
    expect(keys).toContain("/admin/exam-intelligence/new");
    expect(keys).toContain("/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace");
    expect(keys).toContain("/admin/exam-intelligence/workspace/:exam_id");
    expect(keys).toContain("/admin/exam-intelligence/workspace/:exam_id/:cycle_id");
  });
});
