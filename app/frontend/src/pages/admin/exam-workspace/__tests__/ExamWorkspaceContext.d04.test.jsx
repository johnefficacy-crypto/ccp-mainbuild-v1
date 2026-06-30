/**
 * ExamWorkspaceContext — D04 fetch-race integration tests.
 *
 * Verifies that legacy readiness is never committed when the management
 * contract is unsupported, regardless of response ordering, and that stale
 * responses from rapid cycle changes are discarded.
 *
 * Also covers:
 *   P0 — stale mgmt must be cleared at the start of every fetchMgmt call so
 *        SmartHeader/action console cannot render the previous cycle's data.
 *   P1 — refetchReadiness must route through fetchMgmt so every readiness
 *        refresh is preceded by a fresh management-contract validation.
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

  test("P0: cycle change — stale mgmt cleared immediately; older request resolving last cannot restore it", async () => {
    // Two overlapping management requests. gen1 (first/older) is held.
    // gen2 (second/newer) resolves first with unsupported version.
    // gen1 then resolves last with supported version — generation guard must discard it.
    let resolveGen1Mgmt;
    const gen1MgmtHeld = new Promise((res) => { resolveGen1Mgmt = res; });
    let mgmtCallCount = 0;

    let capturedRefetch;
    const mgmtValues = [];
    function ProbePlus() {
      const ctx = useExamWorkspace();
      capturedRefetch = ctx.refetchMgmt;
      const val = ctx.mgmt ? "mgmt-ok" : "mgmt-null";
      if (!mgmtValues.length || mgmtValues[mgmtValues.length - 1] !== val) {
        mgmtValues.push(val);
      }
      return (
        <div>
          <span data-testid="mgmt">{val}</span>
          <span data-testid="mgmtVersionError">{String(ctx.mgmtVersionError)}</span>
        </div>
      );
    }

    api.get.mockImplementation((url) => {
      if (url.includes("/context")) return Promise.resolve(CONTEXT_DATA);
      if (url.includes("/management/")) {
        mgmtCallCount++;
        // gen1 (call 1) is held; gen2 (call 2) returns unsupported immediately.
        return mgmtCallCount === 1 ? gen1MgmtHeld : Promise.resolve(UNSUPPORTED_MGMT);
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

    // gen2 fires immediately (triggered by cycle change) and resolves with unsupported.
    act(() => { capturedRefetch(); });
    await waitFor(() => expect(screen.getByTestId("mgmtVersionError").textContent).toBe("true"));
    expect(screen.getByTestId("mgmt").textContent).toBe("mgmt-null");

    // Now resolve gen1 (older, stale) with supported mgmt — must be discarded.
    await act(async () => { resolveGen1Mgmt(SUPPORTED_MGMT); });

    // Generation guard must prevent gen1's result from overwriting gen2's committed state.
    expect(screen.getByTestId("mgmtVersionError").textContent).toBe("true");
    expect(screen.getByTestId("mgmt").textContent).toBe("mgmt-null");
  });

  test("P0: readiness_loading does not stay stuck when a newer mgmt generation invalidates an in-flight readiness request", async () => {
    // gen1 management is supported; gen1 readiness remains in flight.
    // gen2 management starts and returns unsupported (no gen2 readiness launched).
    // gen1 readiness settles stale — its finally block refuses to clear loading.
    // fetchMgmt must reset readiness_loading at the start of each generation
    // so the operator is not left on a permanent loading skeleton.
    let resolveGen1Readiness;
    const gen1ReadinessHeld = new Promise((res) => { resolveGen1Readiness = res; });
    let mgmtCallCount = 0;

    let capturedRefetch;
    function ProbePlus() {
      const ctx = useExamWorkspace();
      capturedRefetch = ctx.refetchMgmt;
      return (
        <div>
          <span data-testid="readiness">{ctx.readiness ? "readiness-ok" : "readiness-null"}</span>
          <span data-testid="readiness_loading">{String(ctx.readiness_loading)}</span>
          <span data-testid="mgmtVersionError">{String(ctx.mgmtVersionError)}</span>
        </div>
      );
    }

    api.get.mockImplementation((url) => {
      if (url.includes("/context")) return Promise.resolve(CONTEXT_DATA);
      if (url.includes("/management/")) {
        mgmtCallCount++;
        return Promise.resolve(mgmtCallCount === 1 ? SUPPORTED_MGMT : UNSUPPORTED_MGMT);
      }
      if (url.includes("/readiness")) return gen1ReadinessHeld;
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

    // gen1 management succeeded and launched gen1 readiness (still in flight).
    // We don't wait for readiness — it is held.

    // gen2 fires (cycle change), returns unsupported — no gen2 readiness.
    await act(async () => { await capturedRefetch(); });
    expect(screen.getByTestId("mgmtVersionError").textContent).toBe("true");

    // Now gen1 readiness settles stale.
    await act(async () => { resolveGen1Readiness(READINESS_DATA); });

    // readiness must stay null and readiness_loading must be false (not stuck).
    expect(screen.getByTestId("readiness").textContent).toBe("readiness-null");
    expect(screen.getByTestId("readiness_loading").textContent).toBe("false");
  });

  test("P1: refetchReadiness routes through fetchMgmt — management contract revalidated", async () => {
    let mgmtCallCount = 0;
    let capturedRefetchReadiness;

    function ProbePlus() {
      const ctx = useExamWorkspace();
      capturedRefetchReadiness = ctx.refetchReadiness;
      return (
        <div>
          <span data-testid="readiness">{ctx.readiness ? "readiness-ok" : "readiness-null"}</span>
        </div>
      );
    }

    api.get.mockImplementation((url) => {
      if (url.includes("/context")) return Promise.resolve(CONTEXT_DATA);
      if (url.includes("/management/")) {
        mgmtCallCount++;
        return Promise.resolve(SUPPORTED_MGMT);
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

    await waitFor(() => expect(screen.getByTestId("readiness").textContent).toBe("readiness-ok"));
    const mgmtAfterInitialLoad = mgmtCallCount;

    // Call refetchReadiness — must trigger a fresh management fetch.
    await act(async () => { await capturedRefetchReadiness(); });

    expect(mgmtCallCount).toBeGreaterThan(mgmtAfterInitialLoad);
    expect(screen.getByTestId("readiness").textContent).toBe("readiness-ok");
  });
});
