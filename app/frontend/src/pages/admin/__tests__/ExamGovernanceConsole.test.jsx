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
const useApiCollection = require("../../../lib/hooks/useApiCollection").default;

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
  // Default exam-list collection: live with both exams (overridden per test).
  useApiCollection.mockReturnValue({ items: EXAMS, status: "live", refresh: jest.fn() });
});

// ── Test 1: picker ─────────────────────────────────────────────────────────────

describe("ExamGovernanceConsole — no exam selected", () => {
  test("renders the exam picker from the Registry exam-list read", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");

    await waitFor(() => expect(screen.getByTestId("exam-picker-list")).toBeTruthy());
    expect(screen.getByTestId("exam-picker-item-exam-1")).toBeTruthy();
    expect(screen.getByTestId("exam-picker-item-exam-2")).toBeTruthy();

    // Reused the Registry read — same endpoint, no new fetch path.
    expect(useApiCollection).toHaveBeenCalledWith(
      "/api/admin/exam-intelligence/exams",
      [],
      { params: { limit: "200", active_state: "active" } },
    );
  });

  test("selecting an exam navigates to the console exam route (no local state)", async () => {
    mockApi();
    function LocationProbe() {
      const id = useSelectedExamId();
      return <div data-testid="sel">{id ?? "none"}</div>;
    }
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/console"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/console" element={<ExamGovernanceConsole />} />
          <Route path="/admin/exam-intelligence/console/:exam_id" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByTestId("exam-picker-item-exam-2"));
    fireEvent.click(screen.getByTestId("exam-picker-item-exam-2"));
    await waitFor(() => expect(screen.getByTestId("sel").textContent).toBe("exam-2"));
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
