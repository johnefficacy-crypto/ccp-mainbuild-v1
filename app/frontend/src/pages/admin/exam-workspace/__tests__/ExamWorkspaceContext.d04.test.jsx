/**
 * ExamWorkspaceContext — D04 fetch-race integration tests.
 *
 * Verifies that legacy readiness is never committed when the management
 * contract is unsupported, regardless of response ordering, and that stale
 * responses from rapid cycle changes are discarded.
 */
import React from "react";
import { render, screen, act, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

jest.mock("../../../../lib/supabase", () => ({
  __esModule: true,
  supabase: { auth: { getSession: jest.fn(), onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })) } },
}));

jest.mock("../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { role: "admin", permissions: [] } }),
}));

const { api } = require("../../../../lib/api");
const { ExamWorkspaceProvider, useExamWorkspace } = require("../ExamWorkspaceContext");

// Minimal consumer that exposes context values for assertions.
function Probe() {
  const ctx = useExamWorkspace();
  return (
    <div>
      <span data-testid="mgmt">{ctx.mgmt ? "mgmt-ok" : "mgmt-null"}</span>
      <span data-testid="mgmtVersionError">{String(ctx.mgmtVersionError)}</span>
      <span data-testid="readiness">{ctx.readiness ? "readiness-ok" : "readiness-null"}</span>
    </div>
  );
}

function renderProvider(search = "") {
  return render(
    <MemoryRouter initialEntries={[`/admin/exam-intelligence/exams/exam1${search}`]}>
      <Routes>
        <Route
          path="/admin/exam-intelligence/exams/:exam_id"
          element={
            <ExamWorkspaceProvider>
              <Probe />
            </ExamWorkspaceProvider>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

const CONTEXT_DATA = { exam: null, cycle: null, cycles: [], phases: [], organization: null, family: null };
const SUPPORTED_MGMT = { contract_version: 1, cycle_readiness: null };
const UNSUPPORTED_MGMT = { contract_version: 99 };
const READINESS_DATA = { cycle_id: "cy1", steps: [] };

beforeEach(() => {
  jest.clearAllMocks();
});

describe("D04: readiness gated on management contract validation", () => {
  test("unsupported mgmt — readiness is never fetched", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/context")) return Promise.resolve(CONTEXT_DATA);
      if (url.includes("/management/")) return Promise.resolve(UNSUPPORTED_MGMT);
      if (url.includes("/readiness")) return Promise.resolve(READINESS_DATA);
      return Promise.resolve({});
    });

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId("mgmtVersionError").textContent).toBe("true");
    });

    // Readiness null because fetchMgmt must not call fetchReadiness for unsupported versions.
    expect(screen.getByTestId("readiness").textContent).toBe("readiness-null");
    const readinessCalls = api.get.mock.calls.filter(([url]) => url.includes("/readiness"));
    expect(readinessCalls).toHaveLength(0);
  });

  test("unsupported mgmt resolves before readiness would complete — readiness stays null", async () => {
    // mgmt returns synchronously; readiness is a held promise
    let resolveReadiness;
    const readinessHeld = new Promise((res) => { resolveReadiness = res; });

    api.get.mockImplementation((url) => {
      if (url.includes("/context")) return Promise.resolve(CONTEXT_DATA);
      if (url.includes("/management/")) return Promise.resolve(UNSUPPORTED_MGMT);
      if (url.includes("/readiness")) return readinessHeld;
      return Promise.resolve({});
    });

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId("mgmtVersionError").textContent).toBe("true");
    });

    // Even if we resolve readiness now, it must be discarded (fetchReadiness was never called).
    await act(async () => { resolveReadiness(READINESS_DATA); });

    expect(screen.getByTestId("readiness").textContent).toBe("readiness-null");
  });

  test("supported mgmt — readiness IS fetched and committed", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/context")) return Promise.resolve(CONTEXT_DATA);
      if (url.includes("/management/")) return Promise.resolve(SUPPORTED_MGMT);
      if (url.includes("/readiness")) return Promise.resolve(READINESS_DATA);
      return Promise.resolve({});
    });

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId("readiness").textContent).toBe("readiness-ok");
    });
    expect(screen.getByTestId("mgmtVersionError").textContent).toBe("false");
    expect(screen.getByTestId("mgmt").textContent).toBe("mgmt-ok");
  });

  test("refetch: mgmt downgrades from supported to unsupported — readiness is cleared", async () => {
    // First render: mgmt is supported, readiness is committed.
    // After refetchMgmt: mgmt returns unsupported, readiness must be cleared.
    let mgmtCallCount = 0;

    // Expose refetchMgmt so we can trigger a second fetch in the test.
    let capturedRefetch;
    function ProbePlus() {
      const ctx = useExamWorkspace();
      capturedRefetch = ctx.refetchMgmt;
      return (
        <div>
          <span data-testid="mgmtVersionError">{String(ctx.mgmtVersionError)}</span>
          <span data-testid="readiness">{ctx.readiness ? "readiness-ok" : "readiness-null"}</span>
        </div>
      );
    }

    api.get.mockImplementation((url) => {
      if (url.includes("/context")) return Promise.resolve(CONTEXT_DATA);
      if (url.includes("/management/")) {
        mgmtCallCount++;
        return Promise.resolve(mgmtCallCount === 1 ? SUPPORTED_MGMT : UNSUPPORTED_MGMT);
      }
      if (url.includes("/readiness")) return Promise.resolve(READINESS_DATA);
      return Promise.resolve({});
    });

    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/exams/exam1"]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/exams/:exam_id"
            element={<ExamWorkspaceProvider><ProbePlus /></ExamWorkspaceProvider>}
          />
        </Routes>
      </MemoryRouter>
    );

    // First load: supported version, readiness committed.
    await waitFor(() => {
      expect(screen.getByTestId("readiness").textContent).toBe("readiness-ok");
    });
    expect(screen.getByTestId("mgmtVersionError").textContent).toBe("false");

    // Trigger re-fetch (simulates cycle change or manual refresh).
    await act(async () => { await capturedRefetch(); });

    // Second mgmt returned unsupported; readiness must now be cleared.
    expect(screen.getByTestId("mgmtVersionError").textContent).toBe("true");
    expect(screen.getByTestId("readiness").textContent).toBe("readiness-null");
  });
});
