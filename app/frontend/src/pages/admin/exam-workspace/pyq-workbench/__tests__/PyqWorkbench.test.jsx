/**
 * Tests for PR4: PYQ Workbench tab.
 *
 * Covers:
 * - PyqWorkbenchPanel fetches papers on mount with correct exam_id
 * - PyqWorkbenchPanel passes cycle_id query param when workspace has cycle
 * - empty papers list shows empty-state message
 * - selecting a paper renders PyqPaperWorkspace with paperId prop
 * - PyqPaperWorkspace with paperId prop ignores useParams
 * - PyqPaperWorkspace embedded=true drops h-screen wrapper
 * - old route still renders the workspace (useParams fallback)
 * - old route shows banner with correct workspace link
 * F2: after bulk import success, onSuccess(paperId) auto-selects the imported paper
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

jest.mock("../../../../../lib/api", () => {
  function _fieldList(error, key) {
    const detail = error?.detail ?? error?.data?.detail ?? error?.data?.message ?? error?.message;
    const v =
      error?.[key] ??
      (detail && typeof detail === "object" ? detail[key] : undefined) ??
      error?.data?.[key];
    return Array.isArray(v) ? v : [];
  }
  return {
    __esModule: true,
    api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
    getApiBlockingFields: (e) => _fieldList(e, "blocking_fields"),
    getApiBlockingIssues:  (e) => _fieldList(e, "blocking_issues"),
    getApiErrorMessage:    (e) => e?.message || "Unknown error",
  };
});

// Mock BulkImportModal so we can simulate onSuccess without driving the full flow
jest.mock("../bulk-import/BulkImportModal", () => {
  const React = require("react");
  return {
    __esModule: true,
    default: function MockBulkImportModal({ onSuccess, onClose }) {
      return (
        <div data-testid="mock-bulk-import-modal">
          <button
            data-testid="mock-import-success-p1"
            onClick={() => { onSuccess("p1"); onClose(); }}
          >
            Simulate success p1
          </button>
          <button
            data-testid="mock-import-success-p2"
            onClick={() => { onSuccess("p2"); onClose(); }}
          >
            Simulate success p2
          </button>
          <button data-testid="mock-close-modal" onClick={onClose}>Close</button>
        </div>
      );
    },
  };
});

jest.mock("../../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: jest.fn(),
}));

// useApiAction is used by usePyqWorkbench for mutations. The real hook uses
// useToast() which requires a ToastProvider; this lightweight mock replicates
// the run() contract (calls action, invokes onSuccess on success, returns
// {ok,data} or {ok:false,error}) without needing the toast context.
jest.mock("../../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({
    run: async ({ action, onSuccess }) => {
      try {
        const result = await action();
        if (onSuccess) onSuccess(result);
        return { ok: true, data: result };
      } catch (e) {
        return { ok: false, error: e };
      }
    },
    busy: false,
  }),
}));

const { api } = require("../../../../../lib/api");
const { useAuth } = require("../../../../../lib/authContext");
const ExamWorkspaceContext = require("../../ExamWorkspaceContext");

// ── Fixtures ──────────────────────────────────────────────────────────────────

const EXAM_ID = "exam-1";
const CYCLE_ID = "cycle-1";

const PAPERS = [
  { id: "p1", exam_id: EXAM_ID, exam_cycle_id: CYCLE_ID, year: 2024, paper_code: "GS-I", shift: "I" },
  { id: "p2", exam_id: EXAM_ID, exam_cycle_id: CYCLE_ID, year: 2023, paper_code: "GS-I", shift: "II" },
];

const PAPER_P1 = { id: "p1", exam_id: EXAM_ID, exam_cycle_id: CYCLE_ID, year: 2024, paper_code: "GS-I", shift: "I" };

function mockContextApi({ withCycle = false } = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/readiness")) {
      return Promise.resolve({
        exam_id: EXAM_ID, overall: { status: "partial" },
        sections: [
          { section: "pyq_workbench", status: "partial", score_percent: 40 },
          { section: "syllabus_mapper", status: "partial", score_percent: 50 },
        ],
      });
    }
    if (url.includes("/context")) {
      return Promise.resolve({
        exam: { id: EXAM_ID, name: "SSC CGL", exam_type: "recruitment" },
        cycle: withCycle ? { id: CYCLE_ID } : null,
        cycles: withCycle ? [{ id: CYCLE_ID, cycle_name: "2024" }] : [],
        phases: [],
      });
    }
    if (url.includes("/pyq-papers/p1") && !url.includes("pyq-papers?")) {
      return Promise.resolve(PAPER_P1);
    }
    if (url.includes("/pyq-papers?")) {
      return Promise.resolve({ items: PAPERS });
    }
    if (url.includes("/pyq-questions?")) {
      return Promise.resolve({ items: [] });
    }
    if (url.includes("/progress")) {
      return Promise.resolve({ total_expected: 0, present: 0, missing: [], by_status: {} });
    }
    return Promise.resolve({});
  });
}

// ── Wrappers ──────────────────────────────────────────────────────────────────

function WorkspaceWrapper({ examId = EXAM_ID, cycleId = null, children }) {
  const path = cycleId
    ? `/admin/exam-intelligence/workspace/${examId}/${cycleId}`
    : `/admin/exam-intelligence/workspace/${examId}`;
  const routePath = cycleId
    ? "/admin/exam-intelligence/workspace/:exam_id/:cycle_id"
    : "/admin/exam-intelligence/workspace/:exam_id";
  return (
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path={routePath}
          element={
            <ExamWorkspaceContext.ExamWorkspaceProvider>
              {children}
            </ExamWorkspaceContext.ExamWorkspaceProvider>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

const PyqWorkbenchPanel = require("../PyqWorkbenchPanel").default;
const PyqPaperWorkspace = require("../../../studyos/PyqPaperWorkspace").default;

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PyqWorkbenchPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockContextApi();
    useAuth.mockReturnValue({ user: { role: "admin", permissions: [] } });
  });

  test("fetches papers on mount with correct exam_id", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining(`exam_id=${EXAM_ID}`)),
    );
  });

  test("D10: never passes exam_cycle_id to pyq-papers, even when a cycle is selected", async () => {
    // D10 decision: PYQ corpus is always exam-wide. cycle is provenance
    // metadata, not a default scope filter; passing exam_cycle_id would hide
    // historical and parallel-cycle papers from the workbench.
    jest.clearAllMocks();
    mockContextApi({ withCycle: true });
    render(<WorkspaceWrapper cycleId={CYCLE_ID}><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining(`exam_id=${EXAM_ID}`),
      ),
    );
    const pyqCalls = api.get.mock.calls.filter((c) => c[0].includes("pyq-papers?"));
    expect(pyqCalls.length).toBeGreaterThan(0);
    pyqCalls.forEach(([url]) => {
      expect(url).not.toContain("exam_cycle_id");
    });
  });

  test("shows empty-state when no papers returned", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
      if (url.includes("/context")) return Promise.resolve({
        exam: { id: EXAM_ID, name: "Test" }, cycle: null, cycles: [], phases: [],
      });
      if (url.includes("/pyq-papers?")) return Promise.resolve({ items: [] });
      return Promise.resolve({});
    });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => {
      const el = screen.getByTestId("pyq-empty-state");
      if (!el.textContent.includes("No PYQ papers")) throw new Error("not ready");
    });
  });

  // F3: paper picker must be a table, not a <select>
  test("F3: no <select> element renders in the paper picker area", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.queryByTestId("pyq-paper-select")).toBeNull();
    expect(document.querySelector("select")).toBeNull();
  });

  test("F3: table renders one row per paper", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.getByTestId("pyq-paper-row-p1")).toBeTruthy();
    expect(screen.getByTestId("pyq-paper-row-p2")).toBeTruthy();
  });

  test("F3: clicking a table row updates selection and passes paper to PyqPaperWorkspace", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("pyq-paper-row-p1"));
    // After row click, the workspace loads questions for the selected paper
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-papers/p1"),
      ),
    );
  });

  test("selecting a paper via table row renders PyqPaperWorkspace", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("pyq-paper-row-p1"));
    // After selection, the workspace loads questions (embedded PyqPaperWorkspace)
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-papers/p1"),
      ),
    );
  });

  // F2: bulk import auto-navigate
  test("F2: bulk import open shows modal", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("bulk-import-btn"));
    expect(screen.getByTestId("mock-bulk-import-modal")).toBeTruthy();
  });

  test("F2: onSuccess from BulkImportModal auto-selects the imported paper", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());

    // Open bulk import modal
    fireEvent.click(screen.getByTestId("bulk-import-btn"));
    expect(screen.getByTestId("mock-bulk-import-modal")).toBeTruthy();

    // No paper selected yet
    expect(screen.getByTestId("pyq-no-paper-selected")).toBeTruthy();

    // Simulate successful import of p1
    fireEvent.click(screen.getByTestId("mock-import-success-p1"));

    // Modal should close
    expect(screen.queryByTestId("mock-bulk-import-modal")).toBeNull();

    // p1 should now be selected and PyqPaperWorkspace should begin loading
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-papers/p1"),
      ),
    );
  });

  test("F2: onSuccess selects the correct paper (p2) when p2 was imported", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());

    fireEvent.click(screen.getByTestId("bulk-import-btn"));
    fireEvent.click(screen.getByTestId("mock-import-success-p2"));

    // p2 should now be selected
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-papers/p2"),
      ),
    );
  });

  test("F2: closing modal without success leaves selection unchanged", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());

    // Confirm no paper selected initially
    expect(screen.getByTestId("pyq-no-paper-selected")).toBeTruthy();

    // Open modal and close without importing
    fireEvent.click(screen.getByTestId("bulk-import-btn"));
    fireEvent.click(screen.getByTestId("mock-close-modal"));

    // Selection unchanged — still no paper selected
    expect(screen.queryByTestId("pyq-no-paper-selected")).toBeTruthy();
  });

  // D10 acceptance tests: exam-wide PYQ scope
  test("D10: paper from another cycle remains visible when a different cycle is selected", async () => {
    // A 2025-cycle paper must appear in the 2026 workbench view.
    // The corpus is exam-wide; cycle is provenance, not a scope filter.
    const PAPER_2025 = {
      id: "p-2025", exam_id: EXAM_ID, exam_cycle_id: "cy-2025",
      year: 2025, paper_code: "GS-I", shift: "I",
    };
    const PAPER_2026 = {
      id: "p-2026", exam_id: EXAM_ID, exam_cycle_id: CYCLE_ID,
      year: 2026, paper_code: "GS-I", shift: "I",
    };
    jest.clearAllMocks();
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
      if (url.includes("/context")) return Promise.resolve({
        exam: { id: EXAM_ID, name: "SSC CGL", exam_type: "recruitment" },
        cycle: { id: CYCLE_ID }, cycles: [{ id: CYCLE_ID, cycle_name: "2026" }], phases: [],
      });
      if (url.includes("/pyq-papers?")) return Promise.resolve({ items: [PAPER_2025, PAPER_2026] });
      return Promise.resolve({});
    });
    useAuth.mockReturnValue({ user: { role: "admin", permissions: [] } });
    render(<WorkspaceWrapper cycleId={CYCLE_ID}><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    // Both papers — 2025 and 2026 — must be visible.
    expect(screen.getByTestId("pyq-paper-row-p-2025")).toBeTruthy();
    expect(screen.getByTestId("pyq-paper-row-p-2026")).toBeTruthy();
  });

  test("D10: unscoped paper (no exam_cycle_id) remains visible when a cycle is selected", async () => {
    const UNSCOPED = {
      id: "p-unscoped", exam_id: EXAM_ID, exam_cycle_id: null,
      year: 2023, paper_code: "GS-II", shift: "I",
    };
    jest.clearAllMocks();
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
      if (url.includes("/context")) return Promise.resolve({
        exam: { id: EXAM_ID, name: "SSC CGL", exam_type: "recruitment" },
        cycle: { id: CYCLE_ID }, cycles: [{ id: CYCLE_ID, cycle_name: "2026" }], phases: [],
      });
      if (url.includes("/pyq-papers?")) return Promise.resolve({ items: [UNSCOPED] });
      return Promise.resolve({});
    });
    useAuth.mockReturnValue({ user: { role: "admin", permissions: [] } });
    render(<WorkspaceWrapper cycleId={CYCLE_ID}><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.getByTestId("pyq-paper-row-p-unscoped")).toBeTruthy();
  });
});

describe("PyqPaperWorkspace — paperId prop / embedded", () => {
  const PAPER_ID = "p1";

  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({ user: { role: "admin", permissions: [] } });
    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("?")) {
        return Promise.resolve(PAPER_P1);
      }
      if (url.includes("/pyq-questions?")) return Promise.resolve({ items: [] });
      if (url.includes("/progress")) return Promise.resolve({ total_expected: 0, present: 0, missing: [], by_status: {} });
      return Promise.resolve({});
    });
  });

  test("paperId prop uses single-fetch endpoint, ignores useParams", async () => {
    render(
      <MemoryRouter initialEntries={["/some/unrelated/path"]}>
        <Routes>
          <Route path="/some/unrelated/path" element={<PyqPaperWorkspace paperId={PAPER_ID} embedded />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining(`/pyq-papers/${PAPER_ID}`),
      ),
    );
    // Must NOT call the old limit=1 list endpoint
    expect(api.get).not.toHaveBeenCalledWith(expect.stringContaining("pyq-papers?limit=1"));
  });

  test("embedded=true sets data-embedded=true on wrapper", async () => {
    render(
      <MemoryRouter initialEntries={["/x"]}>
        <Routes>
          <Route path="/x" element={<PyqPaperWorkspace paperId={PAPER_ID} embedded />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("pyq-workspace-root")).toBeTruthy());
    expect(screen.getByTestId("pyq-workspace-root").dataset.embedded).toBe("true");
  });

  test("embedded=false (default) sets data-embedded=false on wrapper", async () => {
    render(
      <MemoryRouter initialEntries={[`/admin/exam-intelligence/pyq-papers/${PAPER_ID}/workspace`]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace"
            element={<PyqPaperWorkspace />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("pyq-workspace-root")).toBeTruthy());
    expect(screen.getByTestId("pyq-workspace-root").dataset.embedded).toBe("false");
  });

  test("old route renders workspace via useParams fallback", async () => {
    render(
      <MemoryRouter initialEntries={[`/admin/exam-intelligence/pyq-papers/${PAPER_ID}/workspace`]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace"
            element={<PyqPaperWorkspace />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining(`/pyq-papers/${PAPER_ID}`),
      ),
    );
  });

  test("old route shows banner with correct workspace link", async () => {
    render(
      <MemoryRouter initialEntries={[`/admin/exam-intelligence/pyq-papers/${PAPER_ID}/workspace`]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace"
            element={<PyqPaperWorkspace />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("workspace-banner")).toBeTruthy());
    const link = screen.getByTestId("workspace-banner-link");
    // PAPER_P1 has exam_id=exam-1, exam_cycle_id=cycle-1
    expect(link.getAttribute("href")).toContain(`/workspace/${EXAM_ID}/${CYCLE_ID}`);
  });
});

// ── Review lifecycle (comment #4777966548, item 5) ────────────────────────────

const REVIEW_PAPERS = [
  {
    id: "p-pending", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
    source_url: "https://upsc.gov.in/2024.pdf", source_type: "official",
  },
  { id: "p-verified", exam_id: EXAM_ID, year: 2023, trust_status: "verified" },
  { id: "p-rejected", exam_id: EXAM_ID, year: 2022, trust_status: "rejected" },
];

function mockApiForReview() {
  api.get.mockImplementation((url) => {
    if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
    if (url.includes("/context")) return Promise.resolve({
      exam: { id: EXAM_ID, name: "Test" }, cycle: null, cycles: [], phases: [],
    });
    if (url.includes("/pyq-papers?")) return Promise.resolve({ items: REVIEW_PAPERS });
    return Promise.resolve({});
  });
}

describe("PyqWorkbenchPanel — paper lifecycle review", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiForReview();
  });

  test("review buttons hidden when user lacks exam_intelligence.review", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.cms"] } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.queryByTestId("verify-paper-btn-p-pending")).toBeNull();
    expect(screen.queryByTestId("reject-paper-btn-p-pending")).toBeNull();
    expect(screen.queryByTestId("requeue-paper-btn-p-rejected")).toBeNull();
  });

  test("review buttons visible when user has exam_intelligence.review", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    // pending → Verify + Reject
    expect(screen.getByTestId("verify-paper-btn-p-pending")).toBeTruthy();
    expect(screen.getByTestId("reject-paper-btn-p-pending")).toBeTruthy();
    // verified → Reject only (no Verify)
    expect(screen.queryByTestId("verify-paper-btn-p-verified")).toBeNull();
    expect(screen.getByTestId("reject-paper-btn-p-verified")).toBeTruthy();
    // rejected → Re-queue only (no Verify, no Reject)
    expect(screen.queryByTestId("verify-paper-btn-p-rejected")).toBeNull();
    expect(screen.queryByTestId("reject-paper-btn-p-rejected")).toBeNull();
    expect(screen.getByTestId("requeue-paper-btn-p-rejected")).toBeTruthy();
  });

  test("super_admin sees review buttons even without review permission in permissions array", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.getByTestId("verify-paper-btn-p-pending")).toBeTruthy();
    expect(screen.getByTestId("requeue-paper-btn-p-rejected")).toBeTruthy();
  });

  test("clicking Verify opens PaperReviewModal with Verify submit label", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("verify-paper-btn-p-pending")).toBeTruthy());
    fireEvent.click(screen.getByTestId("verify-paper-btn-p-pending"));
    expect(screen.getByTestId("paper-review-modal")).toBeTruthy();
    expect(screen.getByTestId("paper-review-submit")).toHaveTextContent("Verify");
  });

  test("clicking Reject opens PaperReviewModal with Reject submit label", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("reject-paper-btn-p-pending")).toBeTruthy());
    fireEvent.click(screen.getByTestId("reject-paper-btn-p-pending"));
    expect(screen.getByTestId("paper-review-modal")).toBeTruthy();
    expect(screen.getByTestId("paper-review-submit")).toHaveTextContent("Reject");
  });

  test("successful review calls api.post with correct payload and refreshes paper list", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    api.post.mockResolvedValue({ ok: true, audit_id: "a1", row: { id: "p-pending", trust_status: "verified" } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("verify-paper-btn-p-pending")).toBeTruthy());

    fireEvent.click(screen.getByTestId("verify-paper-btn-p-pending"));
    fireEvent.change(screen.getByTestId("paper-review-reason"), {
      target: { value: "confirmed via official UPSC source PDF" },
    });
    fireEvent.click(screen.getByTestId("paper-review-submit"));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-papers/p-pending/review"),
        { status: "verified", reason: "confirmed via official UPSC source PDF" },
      ),
    );
    // Papers refetched after success
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/pyq-papers?")),
    );
    // Modal closes on success
    await waitFor(() => expect(screen.queryByTestId("paper-review-modal")).toBeNull());
  });

  test("API error shows error message in modal without closing it", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    api.post.mockRejectedValue(new Error("provenance_incomplete"));
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("verify-paper-btn-p-pending")).toBeTruthy());

    fireEvent.click(screen.getByTestId("verify-paper-btn-p-pending"));
    fireEvent.change(screen.getByTestId("paper-review-reason"), {
      target: { value: "confirmed via official UPSC source PDF" },
    });
    fireEvent.click(screen.getByTestId("paper-review-submit"));

    await waitFor(() => expect(screen.getByTestId("paper-review-error")).toBeTruthy());
    expect(screen.getByTestId("paper-review-error")).toHaveTextContent("provenance_incomplete");
    // Modal stays open so operator can correct and retry
    expect(screen.getByTestId("paper-review-modal")).toBeTruthy();
  });

  test("client-side guard: reason shorter than 8 chars blocks submit without calling api", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("verify-paper-btn-p-pending")).toBeTruthy());

    fireEvent.click(screen.getByTestId("verify-paper-btn-p-pending"));
    fireEvent.change(screen.getByTestId("paper-review-reason"), { target: { value: "short" } });
    fireEvent.click(screen.getByTestId("paper-review-submit"));

    expect(screen.getByTestId("paper-review-error")).toHaveTextContent("8 characters");
    expect(api.post).not.toHaveBeenCalled();
  });

  test("Cancel button closes modal without calling api.post", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("verify-paper-btn-p-pending")).toBeTruthy());

    fireEvent.click(screen.getByTestId("verify-paper-btn-p-pending"));
    expect(screen.getByTestId("paper-review-modal")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByTestId("paper-review-modal")).toBeNull();
    expect(api.post).not.toHaveBeenCalled();
  });

  test("Re-queue opens modal with 'Re-queue' label and amber style (not Reject/rose)", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("requeue-paper-btn-p-rejected")).toBeTruthy());

    fireEvent.click(screen.getByTestId("requeue-paper-btn-p-rejected"));
    expect(screen.getByTestId("paper-review-modal")).toBeTruthy();
    // Submit button must say "Re-queue", not "Reject"
    const submitBtn = screen.getByTestId("paper-review-submit");
    expect(submitBtn).toHaveTextContent("Re-queue");
    expect(submitBtn.className).toMatch(/amber/);
    expect(submitBtn.className).not.toMatch(/rose/);
  });
});

// ── Provenance gate + PaperProvenanceModal (migration 191) ───────────────────

const { isPaperProvenanceComplete } = require("../PyqWorkbenchPanel");

const INCOMPLETE_PAPERS_NO_TYPE = [
  {
    id: "p-no-type", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
    source_url: "https://upsc.gov.in/2024.pdf", source_type: null,
    source_document_id: null, pyq_source_id: null,
  },
];

const INCOMPLETE_PAPERS_UNKNOWN_TYPE = [
  {
    id: "p-unknown", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
    source_url: "https://upsc.gov.in/2024.pdf", source_type: "unknown",
    source_document_id: null, pyq_source_id: null,
  },
];

const INCOMPLETE_PAPERS_NO_ANCHOR = [
  {
    id: "p-no-anchor", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
    source_url: null, source_type: "official",
    source_document_id: null, pyq_source_id: null,
  },
];

const COMPLETE_PAPERS_URL = [
  {
    id: "p-with-url", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
    source_url: "https://upsc.gov.in/2024.pdf", source_type: "official",
    source_document_id: null, pyq_source_id: null,
  },
];

const COMPLETE_PAPERS_DOC = [
  {
    id: "p-with-doc", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
    source_url: null, source_type: "official",
    source_document_id: "doc-uuid-1", pyq_source_id: null,
  },
];

const MODAL_DOCS = [
  { id: "doc-uuid-1", original_filename: "upsc-2024-gs1.pdf", page_count: 32, status: "processed" },
  { id: "doc-uuid-2", original_filename: "upsc-2024-csat.pdf", page_count: 28, status: "processed" },
];

const MODAL_SOURCES = [
  { id: "src-1", title: "UPSC Official 2024", exam_id: EXAM_ID },
];

function mockApiForProvenance(papers, opts = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
    if (url.includes("/context")) return Promise.resolve({
      exam: { id: EXAM_ID, name: "Test" }, cycle: null, cycles: [], phases: [],
    });
    if (url.includes("/pyq-papers?")) return Promise.resolve({ items: papers });
    if (url.includes("/documents?") && url.includes("document_kind=pyq_paper")) {
      return Promise.resolve({ items: opts.docs || MODAL_DOCS });
    }
    if (url.includes("/pyq-sources?")) return Promise.resolve({ items: opts.sources || MODAL_SOURCES });
    return Promise.resolve({});
  });
}

describe("isPaperProvenanceComplete — unit", () => {
  // Test 1
  test("returns false when source_type is null", () => {
    expect(isPaperProvenanceComplete({ source_type: null, source_url: "https://example.com" })).toBe(false);
  });

  // Test 2
  test("returns false when source_type is 'unknown'", () => {
    expect(isPaperProvenanceComplete({ source_type: "unknown", source_url: "https://example.com" })).toBe(false);
  });

  // Test 3
  test("returns false when both source_url and source_document_id are absent", () => {
    expect(isPaperProvenanceComplete({ source_type: "official", source_url: null, source_document_id: null })).toBe(false);
  });

  // Test 4
  test("returns true when source_type is valid and source_url is set", () => {
    expect(isPaperProvenanceComplete({ source_type: "official", source_url: "https://example.com" })).toBe(true);
  });

  // Test 5
  test("returns true when source_type is valid and source_document_id is set", () => {
    expect(isPaperProvenanceComplete({ source_type: "official", source_url: null, source_document_id: "some-uuid" })).toBe(true);
  });
});

describe("PyqWorkbenchPanel — provenance gate + PaperProvenanceModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
  });

  // Test 6
  test("pending paper without source_type shows 'Confirm provenance' instead of 'Verify'", async () => {
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.queryByTestId("verify-paper-btn-p-no-type")).toBeNull();
    expect(screen.getByTestId("confirm-provenance-btn-p-no-type")).toBeTruthy();
  });

  // Test 7
  test("pending paper with source_type='unknown' shows 'Confirm provenance' not 'Verify'", async () => {
    mockApiForProvenance(INCOMPLETE_PAPERS_UNKNOWN_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.queryByTestId("verify-paper-btn-p-unknown")).toBeNull();
    expect(screen.getByTestId("confirm-provenance-btn-p-unknown")).toBeTruthy();
  });

  // Test 8
  test("pending paper with no source anchor shows 'Confirm provenance'", async () => {
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_ANCHOR);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.queryByTestId("verify-paper-btn-p-no-anchor")).toBeNull();
    expect(screen.getByTestId("confirm-provenance-btn-p-no-anchor")).toBeTruthy();
  });

  // Test 9
  test("pending paper with valid source_type and source_url shows 'Verify' button", async () => {
    mockApiForProvenance(COMPLETE_PAPERS_URL);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.getByTestId("verify-paper-btn-p-with-url")).toBeTruthy();
    expect(screen.queryByTestId("confirm-provenance-btn-p-with-url")).toBeNull();
  });

  // Test 10
  test("pending paper with valid source_type and source_document_id shows 'Verify' button", async () => {
    mockApiForProvenance(COMPLETE_PAPERS_DOC);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.getByTestId("verify-paper-btn-p-with-doc")).toBeTruthy();
    expect(screen.queryByTestId("confirm-provenance-btn-p-with-doc")).toBeNull();
  });

  // Test 11
  test("clicking 'Confirm provenance' opens PaperProvenanceModal", async () => {
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-no-type")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-no-type"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());
  });

  // Test 12
  test("PaperProvenanceModal title contains paper year, code, shift", async () => {
    const papers = [{
      id: "p-title", exam_id: EXAM_ID, year: 2024, paper_code: "GS-I", shift: "Morning",
      trust_status: "pending", source_url: null, source_type: null,
      source_document_id: null, pyq_source_id: null,
    }];
    mockApiForProvenance(papers);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-title")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-title"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());
    const title = screen.getByTestId("paper-provenance-modal").querySelector("h2");
    expect(title.textContent).toContain("2024");
    expect(title.textContent).toContain("GS-I");
    expect(title.textContent).toContain("Morning");
  });

  // Test 13
  test("PaperProvenanceModal has source_type dropdown", async () => {
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-no-type")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-no-type"));
    await waitFor(() => expect(screen.getByTestId("provenance-source-type")).toBeTruthy());
  });

  // Test 14
  test("PaperProvenanceModal has source_url input", async () => {
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-no-type")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-no-type"));
    await waitFor(() => expect(screen.getByTestId("provenance-source-url")).toBeTruthy());
  });

  // Test 15
  test("PaperProvenanceModal document selector lists filenames not raw UUIDs", async () => {
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE, { docs: MODAL_DOCS });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-no-type")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-no-type"));
    // Wait until the async fetchPyqDocuments resolves and populates the options
    await waitFor(() => {
      const select = screen.getByTestId("provenance-document-id");
      const texts = Array.from(select.options).map((o) => o.text);
      if (!texts.some((t) => t.includes("upsc-2024-gs1.pdf"))) throw new Error("options not yet loaded");
    });
    const select = screen.getByTestId("provenance-document-id");
    const optionTexts = Array.from(select.options).map((o) => o.text);
    expect(optionTexts.some((t) => t.includes("upsc-2024-gs1.pdf"))).toBe(true);
    expect(optionTexts.some((t) => t === "doc-uuid-1")).toBe(false);
  });

  // Test 16 — diff-based payload: only changed fields are sent.
  // Paper starts with source_type=null, source_url=null; user sets both.
  // Both must appear in the payload because both are genuine changes.
  test("saving provenance calls POST /set-provenance with changed fields in payload", async () => {
    const PAPER_NO_TYPE_NO_URL = [{
      id: "p-no-type-url", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
      source_type: null, source_url: null,
      source_document_id: null, pyq_source_id: null,
    }];
    api.post.mockResolvedValue({ ok: true, audit_id: "a1", demoted_from_verified: false });
    mockApiForProvenance(PAPER_NO_TYPE_NO_URL);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-no-type-url")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-no-type-url"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());

    fireEvent.change(screen.getByTestId("provenance-source-type"), { target: { value: "official" } });
    fireEvent.change(screen.getByTestId("provenance-source-url"), {
      target: { value: "https://upsc.gov.in/2024.pdf" },
    });
    fireEvent.change(screen.getByTestId("provenance-reason"), {
      target: { value: "attaching verified source URL from official site" },
    });
    fireEvent.click(screen.getByTestId("provenance-submit"));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/set-provenance"),
        expect.objectContaining({
          payload: expect.objectContaining({
            source_type: "official",
            source_url: "https://upsc.gov.in/2024.pdf",
          }),
        }),
      ),
    );
  });

  // Test 17
  test("PaperProvenanceModal shows blocking_fields error when API returns structured error", async () => {
    const err = new Error("provenance_incomplete: source_type, source_url");
    err.blocking_fields = ["source_type", "source_url"];
    api.post.mockRejectedValue(err);
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-no-type")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-no-type"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());

    fireEvent.change(screen.getByTestId("provenance-source-type"), { target: { value: "official" } });
    fireEvent.change(screen.getByTestId("provenance-reason"), {
      target: { value: "attempting to save incomplete provenance" },
    });
    fireEvent.click(screen.getByTestId("provenance-submit"));

    await waitFor(() => expect(screen.getByTestId("provenance-error")).toBeTruthy());
    const errText = screen.getByTestId("provenance-error").textContent;
    expect(errText).toContain("source_type");
    expect(errText).toContain("source_url");
  });

  // Test 18
  test("successful save closes PaperProvenanceModal", async () => {
    api.post.mockResolvedValue({ ok: true, audit_id: "a1", demoted_from_verified: false });
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-no-type")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-no-type"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());

    fireEvent.change(screen.getByTestId("provenance-source-type"), { target: { value: "official" } });
    fireEvent.change(screen.getByTestId("provenance-source-url"), {
      target: { value: "https://upsc.gov.in/2024.pdf" },
    });
    fireEvent.change(screen.getByTestId("provenance-reason"), {
      target: { value: "adding official source url for pyq paper" },
    });
    fireEvent.click(screen.getByTestId("provenance-submit"));

    await waitFor(() => expect(screen.queryByTestId("paper-provenance-modal")).toBeNull());
  });

  test("Cancel closes PaperProvenanceModal without calling api.post", async () => {
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-no-type")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-no-type"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByTestId("paper-provenance-modal")).toBeNull();
    expect(api.post).not.toHaveBeenCalled();
  });

  test("'Set Provenance' button is shown when paper has no source_document_id", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.getByTestId("attach-doc-btn-p-no-type")).toBeTruthy();
    expect(screen.queryByTestId("view-pdf-btn-p-no-type")).toBeNull();
  });

  test("'Edit Provenance' + PDF button shown when paper has source_document_id", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForProvenance(COMPLETE_PAPERS_DOC);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.getByTestId("view-pdf-btn-p-with-doc")).toBeTruthy();
    expect(screen.getByTestId("replace-doc-btn-p-with-doc")).toBeTruthy();
    expect(screen.queryByTestId("attach-doc-btn-p-with-doc")).toBeNull();
  });

  test("'Set Provenance' button click opens PaperProvenanceModal", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("attach-doc-btn-p-no-type")).toBeTruthy());
    fireEvent.click(screen.getByTestId("attach-doc-btn-p-no-type"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());
  });

  test("'Edit Provenance' button click opens PaperProvenanceModal", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForProvenance(COMPLETE_PAPERS_DOC);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("replace-doc-btn-p-with-doc")).toBeTruthy());
    fireEvent.click(screen.getByTestId("replace-doc-btn-p-with-doc"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());
  });

  // P1-3 regressions: diff-based payload
  test("no-op save on verified paper shows 'No changes to save.' without calling api.post", async () => {
    const VERIFIED_COMPLETE = [{
      id: "p-ver-noop", exam_id: EXAM_ID, year: 2023, trust_status: "verified",
      source_type: "official", source_url: "https://upsc.gov.in/2023.pdf",
      source_document_id: null, pyq_source_id: null,
    }];
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForProvenance(VERIFIED_COMPLETE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("attach-doc-btn-p-ver-noop")).toBeTruthy());
    fireEvent.click(screen.getByTestId("attach-doc-btn-p-ver-noop"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());

    fireEvent.change(screen.getByTestId("provenance-reason"), {
      target: { value: "no actual changes being made here" },
    });
    fireEvent.click(screen.getByTestId("provenance-submit"));

    await waitFor(() => expect(screen.getByTestId("provenance-error")).toBeTruthy());
    expect(screen.getByTestId("provenance-error").textContent).toContain("No changes to save");
    expect(api.post).not.toHaveBeenCalled();
  });

  test("clearing source_type sends source_type: null in payload", async () => {
    // Paper has source_type="official" but no anchor → confirm-provenance-btn shows.
    // User opens modal (source_type initialises to "official"), clears it,
    // and submits — payload must include source_type: null.
    const PAPER_WITH_TYPE_INCOMPLETE = [{
      id: "p-clear-type", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
      source_type: "official",   // pre-populated; user will clear it
      source_url: null,          // no anchor → incomplete provenance
      source_document_id: null, pyq_source_id: null,
    }];
    api.post.mockResolvedValue({ ok: true, audit_id: "a-clear", demoted_from_verified: false });
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForProvenance(PAPER_WITH_TYPE_INCOMPLETE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("confirm-provenance-btn-p-clear-type")).toBeTruthy());
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-clear-type"));
    await waitFor(() => expect(screen.getByTestId("paper-provenance-modal")).toBeTruthy());

    // source_type is pre-filled with "official"; clear it to ""
    fireEvent.change(screen.getByTestId("provenance-source-type"), { target: { value: "" } });
    fireEvent.change(screen.getByTestId("provenance-reason"), {
      target: { value: "clearing source type explicitly" },
    });
    fireEvent.click(screen.getByTestId("provenance-submit"));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/set-provenance"),
        expect.objectContaining({
          payload: expect.objectContaining({ source_type: null }),
        }),
      ),
    );
  });
});

// ── Fix 3 — review-only user permission gate ───────────────────────────────────

describe("PyqWorkbenchPanel — review-only user provenance gate", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("review-only user sees 'CMS provenance confirmation required' span, not the button", async () => {
    useAuth.mockReturnValue({
      user: { role: "admin", permissions: ["exam_intelligence.review"] },
    });
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.queryByTestId("confirm-provenance-btn-p-no-type")).toBeNull();
    expect(screen.getByTestId("provenance-needed-p-no-type")).toBeTruthy();
    expect(screen.getByTestId("provenance-needed-p-no-type").textContent).toContain(
      "CMS provenance confirmation required",
    );
  });

  test("super_admin still sees 'Confirm provenance' button", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForProvenance(INCOMPLETE_PAPERS_NO_TYPE);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.getByTestId("confirm-provenance-btn-p-no-type")).toBeTruthy();
    expect(screen.queryByTestId("provenance-needed-p-no-type")).toBeNull();
  });
});

// ── Fix 1 — question-derived document inference ────────────────────────────────

const PAPER_NO_DOC = {
  id: "p-infer", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
  source_url: null, source_type: null, source_document_id: null, pyq_source_id: null,
};

function mockApiWithQuestions(papers, questions, opts = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
    if (url.includes("/context")) return Promise.resolve({
      exam: { id: EXAM_ID, name: "Test" }, cycle: null, cycles: [], phases: [],
    });
    if (url.includes("/pyq-papers?")) return Promise.resolve({ items: papers });
    if (url.includes("/documents?") && url.includes("document_kind=pyq_paper")) {
      return Promise.resolve({ items: opts.docs || MODAL_DOCS });
    }
    if (url.includes("/pyq-sources?")) return Promise.resolve({ items: opts.sources || [] });
    if (url.includes("/pyq-questions?")) return Promise.resolve({ items: questions });
    return Promise.resolve({});
  });
}

describe("PyqWorkbenchPanel — question-derived document inference (P1-1)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
  });

  test("fetchPaperQuestions is called with pyq_paper_id param, not paper_id", async () => {
    mockApiWithQuestions([PAPER_NO_DOC], []);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => screen.getByTestId("confirm-provenance-btn-p-infer"));
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-infer"));
    await waitFor(() => screen.getByTestId("paper-provenance-modal"));

    const questionsCall = api.get.mock.calls.find((c) => c[0].includes("pyq-questions"));
    expect(questionsCall).toBeTruthy();
    expect(questionsCall[0]).toContain("pyq_paper_id=");
    expect(questionsCall[0]).not.toMatch(/[?&]paper_id=/);
  });

  test("modal preselects the document most questions reference", async () => {
    const QUESTIONS = [
      { id: "q1", source_document_id: "doc-uuid-1" },
      { id: "q2", source_document_id: "doc-uuid-1" },
      { id: "q3", source_document_id: "doc-uuid-1" },
      { id: "q4", source_document_id: "doc-uuid-2" },
    ];
    mockApiWithQuestions([PAPER_NO_DOC], QUESTIONS);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => screen.getByTestId("confirm-provenance-btn-p-infer"));
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-infer"));
    await waitFor(() => screen.getByTestId("paper-provenance-modal"));

    // Wait for async data to load and preselect effect to fire
    await waitFor(() => {
      const sel = screen.getByTestId("provenance-document-id");
      if (sel.value !== "doc-uuid-1") throw new Error("not yet preselected");
    });
    expect(screen.getByTestId("provenance-document-id").value).toBe("doc-uuid-1");
  });

  test("modal does not preselect when two docs are tied", async () => {
    const QUESTIONS = [
      { id: "q1", source_document_id: "doc-uuid-1" },
      { id: "q2", source_document_id: "doc-uuid-2" },
    ];
    mockApiWithQuestions([PAPER_NO_DOC], QUESTIONS);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => screen.getByTestId("confirm-provenance-btn-p-infer"));
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-infer"));
    await waitFor(() => screen.getByTestId("paper-provenance-modal"));
    // Give async ops time to settle
    await waitFor(() => {
      const sel = screen.getByTestId("provenance-document-id");
      const opts = Array.from(sel.options).map((o) => o.text);
      return opts.some((t) => t.includes("upsc-2024-gs1.pdf"));
    });
    expect(screen.getByTestId("provenance-document-id").value).toBe("");
  });

  test("document dropdown shows question count next to each doc", async () => {
    const QUESTIONS = [
      { id: "q1", source_document_id: "doc-uuid-1" },
      { id: "q2", source_document_id: "doc-uuid-1" },
      { id: "q3", source_document_id: "doc-uuid-2" },
    ];
    mockApiWithQuestions([PAPER_NO_DOC], QUESTIONS);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => screen.getByTestId("confirm-provenance-btn-p-infer"));
    fireEvent.click(screen.getByTestId("confirm-provenance-btn-p-infer"));
    await waitFor(() => screen.getByTestId("paper-provenance-modal"));

    // Wait for counts to appear in options
    await waitFor(() => {
      const opts = Array.from(screen.getByTestId("provenance-document-id").options).map((o) => o.text);
      return opts.some((t) => t.includes("2 questions"));
    });

    const optionTexts = Array.from(
      screen.getByTestId("provenance-document-id").options,
    ).map((o) => o.text);
    expect(optionTexts.some((t) => t.includes("2 questions"))).toBe(true);
    expect(optionTexts.some((t) => t.includes("1 question"))).toBe(true);
  });

  test("modal does not preselect when paper already has source_document_id", async () => {
    const PAPER_WITH_DOC = {
      ...PAPER_NO_DOC, id: "p-has-doc", source_document_id: "doc-uuid-2",
    };
    const QUESTIONS = [
      { id: "q1", source_document_id: "doc-uuid-1" },
      { id: "q2", source_document_id: "doc-uuid-1" },
    ];
    mockApiWithQuestions([PAPER_WITH_DOC], QUESTIONS, { docs: MODAL_DOCS });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    // Paper has source_document_id so it shows canEdit buttons
    await waitFor(() => screen.getByTestId("replace-doc-btn-p-has-doc"));
    fireEvent.click(screen.getByTestId("replace-doc-btn-p-has-doc"));
    await waitFor(() => screen.getByTestId("paper-provenance-modal"));

    // Let async ops settle
    await waitFor(() => {
      const opts = Array.from(screen.getByTestId("provenance-document-id").options).map((o) => o.text);
      return opts.some((t) => t.includes("upsc-2024-gs1.pdf"));
    });
    // Existing source_document_id (doc-uuid-2) must be preserved, not overwritten by inference
    expect(screen.getByTestId("provenance-document-id").value).toBe("doc-uuid-2");
  });
});

// ── Contextual PYQ onboarding (J2 — Section D) ───────────────────────────────

const ONBOARD_DOCS = [
  { id: "doc-uuid-1", original_filename: "upsc-2024-gs1.pdf", page_count: 32, status: "processed" },
  {
    id: "doc-uuid-long",
    original_filename:
      "extremely-long-commission-archive-filename-that-clips-the-option-2024-gs-paper-i.pdf",
    page_count: 40, status: "processed",
  },
];

const ONBOARD_SOURCES = [
  { id: "src-1", title: "UPSC Official 2024", exam_id: EXAM_ID },
];

function mockApiForOnboarding(papers, opts = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
    if (url.includes("/context")) return Promise.resolve({
      exam: { id: EXAM_ID, name: "SSC CGL" }, cycle: null, cycles: [], phases: [],
    });
    if (url.includes("/pyq-papers?")) return Promise.resolve({ items: papers });
    if (url.includes("/documents?") && url.includes("document_kind=pyq_paper")) {
      return Promise.resolve({ items: opts.docs || ONBOARD_DOCS });
    }
    if (url.includes("/pyq-sources?")) return Promise.resolve({ items: opts.sources || ONBOARD_SOURCES });
    return Promise.resolve({});
  });
}

describe("PyqWorkbenchPanel — contextual onboarding (J2)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
  });

  // D: empty-state copy
  test("empty state renders 'Add the first PYQ paper' and does NOT mention CMS; copy is exam-wide", async () => {
    mockApiForOnboarding([]);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    // findBy retries until the empty-state CTA settles. Read the copy off the
    // CTA's own container (the empty-state div) to avoid a second async gap.
    const cta = await screen.findByTestId("add-first-pyq-paper-btn");
    expect(cta.textContent).toContain("Add the first PYQ paper");
    const empty = cta.closest('[data-testid="pyq-empty-state"]');
    expect(empty).toBeTruthy();
    expect(empty.textContent).toContain("No PYQ papers for this exam");
    expect(empty.textContent).not.toContain("CMS");
  });

  // The onboarding modal is opened from the stable header "Add PYQ paper"
  // action (the empty-state CTA opens the identical modal).
  async function openAddModal() {
    const btn = await screen.findByTestId("add-pyq-paper-btn");
    fireEvent.click(btn);
    await screen.findByTestId("add-pyq-paper-modal");
  }

  // D: header action beside Bulk import
  test("panel header renders an 'Add PYQ paper' action beside Bulk import", async () => {
    mockApiForOnboarding(PAPERS);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.getByTestId("add-pyq-paper-btn")).toBeTruthy();
    expect(screen.getByTestId("add-pyq-paper-btn").textContent).toContain("Add PYQ paper");
    expect(screen.getByTestId("bulk-import-btn")).toBeTruthy();
  });

  // D: modal reuses picker + pyq_source selector, no raw-UUID input (OD-4)
  test("the onboarding modal reuses the document picker + pyq_source selector with no raw-UUID input", async () => {
    mockApiForOnboarding(PAPERS);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();

    // Reused document picker (a <select>, populated from exam-scoped documents)
    await waitFor(() => {
      const sel = screen.getByTestId("add-pyq-evidence-document-id");
      const texts = Array.from(sel.options).map((o) => o.text);
      if (!texts.some((t) => t.includes("upsc-2024-gs1.pdf"))) throw new Error("docs not loaded");
    });
    const docSelect = screen.getByTestId("add-pyq-evidence-document-id");
    expect(docSelect.tagName).toBe("SELECT");
    // No raw-UUID text input for the document anywhere in the modal
    const modal = screen.getByTestId("add-pyq-paper-modal");
    const textInputs = Array.from(modal.querySelectorAll("input"));
    textInputs.forEach((inp) => {
      expect(inp.getAttribute("data-testid")).not.toMatch(/document/i);
    });
    // Reused pyq_source selector
    expect(screen.getByTestId("add-pyq-existing-source-id")).toBeTruthy();
    expect(screen.getByTestId("add-pyq-source-pyq-source-id")).toBeTruthy();
  });

  // D: filename clip fix — long filenames carry a full-text title tooltip
  test("long document filenames are truncated in the label but kept in the title tooltip", async () => {
    mockApiForOnboarding(PAPERS);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();
    await waitFor(() => {
      const sel = screen.getByTestId("add-pyq-evidence-document-id");
      if (sel.options.length < 3) throw new Error("docs not loaded");
    });
    const sel = screen.getByTestId("add-pyq-evidence-document-id");
    const longOpt = Array.from(sel.options).find((o) => o.value === "doc-uuid-long");
    expect(longOpt).toBeTruthy();
    // visible label is truncated (contains the ellipsis), title holds the full name
    expect(longOpt.text).toContain("…");
    expect(longOpt.title).toContain(
      "extremely-long-commission-archive-filename-that-clips-the-option-2024-gs-paper-i.pdf",
    );
  });

  // D: advisory, not blocker (OD-3)
  test("paper with valid provenance but no pyq_source_id shows 'No reusable source record' advisory, not a blocker", async () => {
    const ADVISORY_PAPER = [{
      id: "p-advisory", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
      source_type: "official", source_url: "https://upsc.gov.in/2024.pdf",
      source_document_id: null, pyq_source_id: null,
    }];
    mockApiForOnboarding(ADVISORY_PAPER);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    const advisory = screen.getByTestId("no-source-record-advisory-p-advisory");
    expect(advisory.textContent).toContain("No reusable source record");
    // It must NOT be a provenance blocker — Verify (complete provenance) is shown.
    expect(screen.getByTestId("verify-paper-btn-p-advisory")).toBeTruthy();
    expect(screen.queryByTestId("confirm-provenance-btn-p-advisory")).toBeNull();
  });

  test("paper WITH a pyq_source_id shows no advisory badge", async () => {
    const LINKED_PAPER = [{
      id: "p-linked", exam_id: EXAM_ID, year: 2024, trust_status: "pending",
      source_type: "official", source_url: "https://upsc.gov.in/2024.pdf",
      source_document_id: null, pyq_source_id: "src-1",
    }];
    mockApiForOnboarding(LINKED_PAPER);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    expect(screen.queryByTestId("no-source-record-advisory-p-linked")).toBeNull();
  });

  // D: submitting calls POST /pyq-onboarding and selects the returned paper
  test("submitting calls POST /pyq-onboarding and selects the returned paper", async () => {
    mockApiForOnboarding(PAPERS);
    api.post.mockResolvedValue({
      ok: true, audit_id: "aud-1",
      source: { id: "src-new", created: true, trust_status: "pending" },
      paper: { id: "p-new", trust_status: "pending", pyq_source_id: "src-new" },
      document_link: { document_id: "doc-uuid-1", linked: true },
    });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();

    fireEvent.change(screen.getByTestId("add-pyq-year"), { target: { value: "2024" } });
    fireEvent.change(screen.getByTestId("add-pyq-source-source-type"), { target: { value: "official" } });
    fireEvent.change(screen.getByTestId("add-pyq-source-source-url"), {
      target: { value: "https://upsc.gov.in/2024.pdf" },
    });
    fireEvent.change(screen.getByTestId("add-pyq-reason"), {
      target: { value: "added official 2024 paper from commission archive" },
    });
    fireEvent.click(screen.getByTestId("add-pyq-submit"));

    // POST to the LOCKED endpoint with contract-shaped body
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-onboarding"),
        expect.objectContaining({
          reason: "added official 2024 paper from commission archive",
          exam_id: EXAM_ID,
          paper: expect.objectContaining({ year: 2024 }),
        }),
      ),
    );
    // Body uses canonical source.source_id, never source_registry_id
    const body = api.post.mock.calls.find((c) => c[0].includes("/pyq-onboarding"))[1];
    expect(body.source).not.toBeNull();
    expect("source_id" in body.source).toBe(true);
    expect("source_registry_id" in body.source).toBe(false);
    expect(body.paper.metadata).toHaveProperty("expected_question_count");

    // Modal closes and the returned paper is selected → workspace loads it
    await waitFor(() => expect(screen.queryByTestId("add-pyq-paper-modal")).toBeNull());
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/pyq-papers/p-new")),
    );
  });

  test("onboarding without a source but with valid paper provenance omits the source block (OD-1)", async () => {
    mockApiForOnboarding(PAPERS);
    api.post.mockResolvedValue({ ok: true, audit_id: "a", paper: { id: "p-nosrc" } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();

    fireEvent.change(screen.getByTestId("add-pyq-year"), { target: { value: "2024" } });
    // Pick an evidence document instead of a source → paper provenance complete
    await waitFor(() => {
      const sel = screen.getByTestId("add-pyq-evidence-document-id");
      if (sel.options.length < 2) throw new Error("docs not loaded");
    });
    fireEvent.change(screen.getByTestId("add-pyq-evidence-document-id"), {
      target: { value: "doc-uuid-1" },
    });
    fireEvent.change(screen.getByTestId("add-pyq-reason"), {
      target: { value: "added paper linked to uploaded pdf only" },
    });
    fireEvent.click(screen.getByTestId("add-pyq-submit"));

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = api.post.mock.calls.find((c) => c[0].includes("/pyq-onboarding"))[1];
    expect(body.source).toBeNull();
    expect(body.document_id).toBe("doc-uuid-1");
  });

  test("client guard: missing year blocks submit without calling api.post", async () => {
    mockApiForOnboarding(PAPERS);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();

    fireEvent.change(screen.getByTestId("add-pyq-reason"), {
      target: { value: "trying without a year value here" },
    });
    fireEvent.click(screen.getByTestId("add-pyq-submit"));
    expect(screen.getByTestId("add-pyq-error").textContent).toContain("Year");
    expect(api.post).not.toHaveBeenCalled();
  });

  test("backend blocking_fields surface in operator-readable form", async () => {
    mockApiForOnboarding(PAPERS);
    const err = new Error("onboarding blocked");
    err.blocking_fields = ["document_id"];
    api.post.mockRejectedValue(err);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();

    fireEvent.change(screen.getByTestId("add-pyq-year"), { target: { value: "2024" } });
    fireEvent.change(screen.getByTestId("add-pyq-reason"), {
      target: { value: "valid reason that is long enough" },
    });
    fireEvent.click(screen.getByTestId("add-pyq-submit"));

    await waitFor(() => expect(screen.getByTestId("add-pyq-error")).toBeTruthy());
    expect(screen.getByTestId("add-pyq-error").textContent).toContain("document_id");
    // Modal stays open so the operator can correct
    expect(screen.getByTestId("add-pyq-paper-modal")).toBeTruthy();
  });
});

// ── Follow-up 1 — inline PDF upload in AddPyqPaperModal (OD-5) ────────────────

describe("PyqWorkbenchPanel — inline PDF upload (OD-5 follow-up)", () => {
  let originalFetch;

  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  async function openAddModal() {
    const btn = await screen.findByTestId("add-pyq-paper-btn");
    fireEvent.click(btn);
    await screen.findByTestId("add-pyq-paper-modal");
  }

  function pdfFile(name = "new-2024.pdf") {
    return new File([new Uint8Array([1, 2, 3])], name, { type: "application/pdf" });
  }

  test("inline upload option appears in the evidence step", async () => {
    mockApiForOnboarding(PAPERS);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();
    expect(screen.getByTestId("add-pyq-evidence-mode-select")).toBeTruthy();
    expect(screen.getByTestId("add-pyq-evidence-mode-upload")).toBeTruthy();
    // Default mode is "select existing" — the picker is visible, no upload input.
    expect(screen.getByTestId("add-pyq-evidence-document-id")).toBeTruthy();
    expect(screen.queryByTestId("add-pyq-upload-file")).toBeNull();
  });

  test("upload sequence sets document_id and submits onboarding with the new id", async () => {
    mockApiForOnboarding(PAPERS);

    // Binary PUT to storage — must bypass the api wrapper (raw fetch).
    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 });

    // upload-url → complete-upload via api.post; onboarding via api.post too.
    api.post.mockImplementation((url) => {
      if (url.includes("/documents/upload-url")) {
        return Promise.resolve({ upload_url: "https://storage.example/put", document_id: "doc-new-1" });
      }
      if (url.includes("/documents/complete-upload")) {
        return Promise.resolve({ ok: true });
      }
      if (url.includes("/pyq-onboarding")) {
        return Promise.resolve({ ok: true, audit_id: "a", paper: { id: "p-new", pyq_source_id: null } });
      }
      return Promise.resolve({});
    });

    // Poll: document GET returns a terminal (processed) status immediately.
    const baseGet = api.get.getMockImplementation();
    api.get.mockImplementation((url) => {
      if (url.match(/\/documents\/doc-new-1(\?|$)/)) {
        return Promise.resolve({ document: { status: "processed" }, extraction: { status: "succeeded" } });
      }
      return baseGet(url);
    });

    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();

    fireEvent.change(screen.getByTestId("add-pyq-year"), { target: { value: "2024" } });
    fireEvent.change(screen.getByTestId("add-pyq-reason"), {
      target: { value: "uploaded official 2024 paper inline" },
    });

    // Switch to upload mode and run the inline upload.
    fireEvent.click(screen.getByTestId("add-pyq-evidence-mode-upload"));
    fireEvent.change(screen.getByTestId("add-pyq-upload-file"), {
      target: { files: [pdfFile()] },
    });
    fireEvent.click(screen.getByTestId("add-pyq-upload-submit"));

    // upload-url minted, raw PUT performed, complete-upload called.
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/documents/upload-url"),
        expect.objectContaining({ document_kind: "pyq_paper", exam_id: EXAM_ID }),
      ),
    );
    expect(global.fetch).toHaveBeenCalledWith(
      "https://storage.example/put",
      expect.objectContaining({ method: "PUT" }),
    );
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/documents/complete-upload"),
        { document_id: "doc-new-1" },
      ),
    );

    // The new document is linked and surfaced.
    await waitFor(() => expect(screen.getByTestId("add-pyq-upload-linked")).toBeTruthy());

    // Submitting onboarding carries the freshly-uploaded document_id.
    fireEvent.click(screen.getByTestId("add-pyq-submit"));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-onboarding"),
        expect.objectContaining({ document_id: "doc-new-1" }),
      ),
    );
  });

  test("binary PUT failure surfaces an upload error and does not set document_id", async () => {
    mockApiForOnboarding(PAPERS);
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    api.post.mockImplementation((url) => {
      if (url.includes("/documents/upload-url")) {
        return Promise.resolve({ upload_url: "https://storage.example/put", document_id: "doc-fail" });
      }
      return Promise.resolve({});
    });

    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();
    fireEvent.click(screen.getByTestId("add-pyq-evidence-mode-upload"));
    fireEvent.change(screen.getByTestId("add-pyq-upload-file"), {
      target: { files: [pdfFile()] },
    });
    fireEvent.click(screen.getByTestId("add-pyq-upload-submit"));

    await waitFor(() => expect(screen.getByTestId("add-pyq-upload-error")).toBeTruthy());
    expect(screen.getByTestId("add-pyq-upload-error").textContent).toMatch(/Storage upload failed/);
    // complete-upload never called; no linked confirmation.
    expect(api.post).not.toHaveBeenCalledWith(
      expect.stringContaining("/documents/complete-upload"),
      expect.anything(),
    );
    expect(screen.queryByTestId("add-pyq-upload-linked")).toBeNull();
  });

  test("terminal extraction failure surfaces an error and does NOT link the document", async () => {
    mockApiForOnboarding(PAPERS);
    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 });
    api.post.mockImplementation((url) => {
      if (url.includes("/documents/upload-url")) {
        return Promise.resolve({ upload_url: "https://storage.example/put", document_id: "doc-extract-fail" });
      }
      if (url.includes("/documents/complete-upload")) {
        return Promise.resolve({ ok: true });
      }
      if (url.includes("/pyq-onboarding")) {
        return Promise.resolve({ ok: true, audit_id: "a", paper: { id: "p-x", pyq_source_id: null } });
      }
      return Promise.resolve({});
    });
    // Poll returns a TERMINAL FAILED extraction → result.ok === false.
    const baseGet = api.get.getMockImplementation();
    api.get.mockImplementation((url) => {
      if (url.match(/\/documents\/doc-extract-fail(\?|$)/)) {
        return Promise.resolve({ document: { status: "failed" }, extraction: { status: "failed" } });
      }
      return baseGet(url);
    });

    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();
    fireEvent.change(screen.getByTestId("add-pyq-year"), { target: { value: "2024" } });
    fireEvent.change(screen.getByTestId("add-pyq-reason"), {
      target: { value: "attempted upload of a paper that fails extraction" },
    });
    fireEvent.click(screen.getByTestId("add-pyq-evidence-mode-upload"));
    fireEvent.change(screen.getByTestId("add-pyq-upload-file"), { target: { files: [pdfFile()] } });
    fireEvent.click(screen.getByTestId("add-pyq-upload-submit"));

    // complete-upload IS reached (unlike the PUT-failure path) then extraction fails.
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/documents/complete-upload"),
        { document_id: "doc-extract-fail" },
      ),
    );
    await waitFor(() => expect(screen.getByTestId("add-pyq-upload-error")).toBeTruthy());
    expect(screen.getByTestId("add-pyq-upload-error").textContent).toMatch(/Extraction failed/);
    // The failed asset must NOT be linked / shown as success.
    expect(screen.queryByTestId("add-pyq-upload-linked")).toBeNull();

    // Submitting onboarding must NOT carry the failed document_id.
    fireEvent.click(screen.getByTestId("add-pyq-submit"));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(expect.stringContaining("/pyq-onboarding"), expect.anything()),
    );
    const onboardingCall = api.post.mock.calls.find((c) => String(c[0]).includes("/pyq-onboarding"));
    expect(onboardingCall?.[1]?.document_id || null).toBeNull();
  });

  // ── Cycle/phase label fix — browser gate remediation ─────────────────────────

  test("modal shows 'No cycle selected (exam-wide paper)' and exam-wide phase default when no cycle context is active", async () => {
    // mockApiForOnboarding returns cycle: null by default
    mockApiForOnboarding(PAPERS);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();
    expect(screen.getByTestId("add-pyq-cycle-label").textContent).toContain("No cycle selected (exam-wide paper)");
    // EI-CLEAN-02: no cycle → no cycle-scoped phases → phase defaults to exam-wide.
    expect(screen.getByTestId("add-pyq-phase-label").textContent).toContain("Exam-wide / no phase");
  });

  test("modal shows readable cycle name and year when a cycle is selected", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
      if (url.includes("/context")) return Promise.resolve({
        exam: { id: EXAM_ID, name: "SSC CGL" },
        cycle: { id: CYCLE_ID, cycle_name: "AILET 2026", year: 2026 },
        cycles: [{ id: CYCLE_ID, cycle_name: "AILET 2026", year: 2026 }],
        phases: [],
      });
      if (url.includes("/pyq-papers?")) return Promise.resolve({ items: PAPERS });
      if (url.includes("/documents?") && url.includes("document_kind=pyq_paper")) return Promise.resolve({ items: ONBOARD_DOCS });
      if (url.includes("/pyq-sources?")) return Promise.resolve({ items: ONBOARD_SOURCES });
      return Promise.resolve({});
    });
    render(<WorkspaceWrapper cycleId={CYCLE_ID}><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();
    const label = screen.getByTestId("add-pyq-cycle-label").textContent;
    expect(label).toContain("AILET 2026");
    expect(label).toContain("2026");
    expect(label).not.toContain("No cycle selected");
  });

  test("submitted body carries cycleId; phase is always null; years matching means no mismatch warning", async () => {
    // Real context shape: cycle has year; paper year matches cycle year — normal happy path
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
      if (url.includes("/context")) return Promise.resolve({
        exam: { id: EXAM_ID, name: "SSC CGL" },
        cycle: { id: CYCLE_ID, cycle_name: "AILET 2026", year: 2025 },
        cycles: [{ id: CYCLE_ID, cycle_name: "AILET 2026", year: 2025 }],
        phases: [],
      });
      if (url.includes("/pyq-papers?")) return Promise.resolve({ items: PAPERS });
      if (url.includes("/documents?") && url.includes("document_kind=pyq_paper")) return Promise.resolve({ items: ONBOARD_DOCS });
      if (url.includes("/pyq-sources?")) return Promise.resolve({ items: ONBOARD_SOURCES });
      return Promise.resolve({});
    });
    api.post.mockImplementation((url) => {
      if (url.includes("/pyq-onboarding")) return Promise.resolve({ ok: true, paper: { id: "p-new" } });
      return Promise.resolve({});
    });
    render(<WorkspaceWrapper cycleId={CYCLE_ID}><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();
    expect(screen.getByTestId("add-pyq-cycle-label").textContent).toContain("AILET 2026");
    // EI-CLEAN-02: this context seeds no phases, so the default remains exam-wide.
    expect(screen.getByTestId("add-pyq-phase-label").textContent).toContain("Exam-wide / no phase");
    fireEvent.change(screen.getByTestId("add-pyq-year"), { target: { value: "2025" } });
    // years match — no warning
    expect(screen.queryByTestId("add-pyq-year-mismatch-warning")).toBeNull();
    fireEvent.change(screen.getByTestId("add-pyq-reason"), { target: { value: "browser gate verification" } });
    fireEvent.click(screen.getByTestId("add-pyq-submit"));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(expect.stringContaining("/pyq-onboarding"), expect.anything()),
    );
    const body = api.post.mock.calls.find((c) => String(c[0]).includes("/pyq-onboarding"))?.[1];
    expect(body?.exam_cycle_id).toBe(CYCLE_ID);
    // EI-CLEAN-02: no phase selected (none seeded) → exam-wide → exam_phase_id null.
    expect(body?.exam_phase_id ?? null).toBeNull();
  });

  test("year mismatch warning shown when paper year differs from cycle year; submit not blocked", async () => {
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
      if (url.includes("/context")) return Promise.resolve({
        exam: { id: EXAM_ID, name: "SSC CGL" },
        cycle: { id: CYCLE_ID, cycle_name: "AILET 2026", year: 2026 },
        cycles: [{ id: CYCLE_ID, cycle_name: "AILET 2026", year: 2026 }],
        phases: [],
      });
      if (url.includes("/pyq-papers?")) return Promise.resolve({ items: PAPERS });
      if (url.includes("/documents?") && url.includes("document_kind=pyq_paper")) return Promise.resolve({ items: ONBOARD_DOCS });
      if (url.includes("/pyq-sources?")) return Promise.resolve({ items: ONBOARD_SOURCES });
      return Promise.resolve({});
    });
    render(<WorkspaceWrapper cycleId={CYCLE_ID}><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();
    // Enter a paper year that differs from cycle year (2026)
    fireEvent.change(screen.getByTestId("add-pyq-year"), { target: { value: "2025" } });
    // Mismatch warning must appear
    const warning = screen.getByTestId("add-pyq-year-mismatch-warning");
    expect(warning.textContent).toContain("2025");
    expect(warning.textContent).toContain("2026");
    // Submit must NOT be disabled (warning only, not a hard block)
    expect(screen.getByTestId("add-pyq-submit")).not.toBeDisabled();
  });

  test("submit and upload are both blocked when cycleId is set but cycleLabel cannot be resolved", async () => {
    // Simulates a stale/bad context: cycleId present but cycle row missing cycle_name
    api.get.mockImplementation((url) => {
      if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
      if (url.includes("/context")) return Promise.resolve({
        exam: { id: EXAM_ID, name: "SSC CGL" },
        cycle: { id: CYCLE_ID },  // no cycle_name — mismatch condition
        cycles: [],
        phases: [],
      });
      if (url.includes("/pyq-papers?")) return Promise.resolve({ items: PAPERS });
      if (url.includes("/documents?") && url.includes("document_kind=pyq_paper")) return Promise.resolve({ items: ONBOARD_DOCS });
      if (url.includes("/pyq-sources?")) return Promise.resolve({ items: ONBOARD_SOURCES });
      return Promise.resolve({});
    });
    api.post.mockImplementation((url) => {
      if (url.includes("/pyq-onboarding")) return Promise.resolve({ ok: true, paper: { id: "p-new" } });
      return Promise.resolve({});
    });
    render(<WorkspaceWrapper cycleId={CYCLE_ID}><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await openAddModal();
    // Error banner must be visible; cycle-label span absent
    expect(screen.getByTestId("add-pyq-cycle-label-error")).toBeTruthy();
    expect(screen.queryByTestId("add-pyq-cycle-label")).toBeNull();
    // Submit button must be disabled
    const submitBtn = screen.getByTestId("add-pyq-submit");
    expect(submitBtn).toBeDisabled();
    fireEvent.click(submitBtn);
    expect(api.post).not.toHaveBeenCalled();
    // Upload button must also be disabled (cycle guard applies to the upload path too)
    fireEvent.click(screen.getByTestId("add-pyq-evidence-mode-upload"));
    const uploadBtn = screen.getByTestId("add-pyq-upload-submit");
    expect(uploadBtn).toBeDisabled();
  });
});

// ── Follow-up 2 — PYQ source trust lifecycle UI (OD-2 / Finding 7) ───────────

const SRC_PENDING = {
  id: "src-trust-1", exam_id: EXAM_ID, title: "UPSC Official Archive",
  source_type: "official", source_url: "https://upsc.gov.in/archive",
  trust_status: "pending",
};

const PAPER_WITH_SOURCE = {
  id: "p-src", exam_id: EXAM_ID, year: 2024, paper_code: "GS-I", trust_status: "pending",
  source_type: "official", source_url: "https://upsc.gov.in/2024.pdf",
  source_document_id: null, pyq_source_id: "src-trust-1",
};

function mockApiForSourceTrust(papers, sources, opts = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/readiness")) return Promise.resolve({ sections: [] });
    if (url.includes("/context")) return Promise.resolve({
      exam: { id: EXAM_ID, name: "SSC CGL" }, cycle: null, cycles: [], phases: [],
    });
    if (url.includes("/pyq-papers/p-src") && !url.includes("pyq-papers?")) {
      return Promise.resolve(papers.find((p) => p.id === "p-src") || {});
    }
    if (url.includes("/pyq-papers?")) return Promise.resolve({ items: papers });
    if (url.includes("/pyq-sources?")) return Promise.resolve({ items: sources });
    if (url.includes("/pyq-questions?")) return Promise.resolve({ items: [] });
    if (url.includes("/progress")) return Promise.resolve({ total_expected: 0, present: 0, missing: [], by_status: {} });
    if (url.includes("/documents?")) return Promise.resolve({ items: opts.docs || [] });
    return Promise.resolve({});
  });
}

describe("PyqWorkbenchPanel — source trust summary (OD-2 / Finding 7)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("selecting a paper with a source renders the trust summary + chip", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForSourceTrust([PAPER_WITH_SOURCE], [SRC_PENDING]);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("pyq-paper-row-p-src"));

    await waitFor(() => expect(screen.getByTestId("source-trust-summary")).toBeTruthy());
    expect(screen.getByTestId("source-trust-summary").textContent).toContain("UPSC Official Archive");
    expect(screen.getByTestId("source-trust-type").textContent).toContain("official");
    expect(screen.getByTestId("source-trust-chip").textContent).toContain("Pending");
  });

  test("paper without a source shows no trust summary (advisory case unaffected)", async () => {
    const PAPER_NO_SOURCE = { ...PAPER_WITH_SOURCE, id: "p-src", pyq_source_id: null };
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForSourceTrust([PAPER_NO_SOURCE], [SRC_PENDING]);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("pyq-paper-row-p-src"));
    // Give the (non-)fetch a tick; no summary should ever appear.
    await waitFor(() => expect(screen.getByTestId("pyq-paper-row-p-src")).toBeTruthy());
    expect(screen.queryByTestId("source-trust-summary")).toBeNull();
  });

  test("Verify/Reject/Re-queue actions are gated by canReview", async () => {
    // review-only false: a CMS-only editor sees the summary but no actions.
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.cms"] } });
    mockApiForSourceTrust([PAPER_WITH_SOURCE], [SRC_PENDING]);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("pyq-paper-row-p-src"));
    await waitFor(() => expect(screen.getByTestId("source-trust-summary")).toBeTruthy());
    expect(screen.queryByTestId("source-trust-actions")).toBeNull();
    expect(screen.queryByTestId("verify-source-btn")).toBeNull();
  });

  test("pending source shows Verify + Reject; reviewer can act", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    mockApiForSourceTrust([PAPER_WITH_SOURCE], [SRC_PENDING]);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("pyq-paper-row-p-src"));
    await waitFor(() => expect(screen.getByTestId("source-trust-actions")).toBeTruthy());
    expect(screen.getByTestId("verify-source-btn")).toBeTruthy();
    expect(screen.getByTestId("reject-source-btn")).toBeTruthy();
    expect(screen.queryByTestId("requeue-source-btn")).toBeNull();
  });

  test("rejected source shows only Re-queue (legal transitions)", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    const REJECTED = { ...SRC_PENDING, trust_status: "rejected" };
    mockApiForSourceTrust([PAPER_WITH_SOURCE], [REJECTED]);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("pyq-paper-row-p-src"));
    await waitFor(() => expect(screen.getByTestId("source-trust-actions")).toBeTruthy());
    expect(screen.getByTestId("requeue-source-btn")).toBeTruthy();
    expect(screen.queryByTestId("verify-source-btn")).toBeNull();
    expect(screen.queryByTestId("reject-source-btn")).toBeNull();
  });

  test("reviewPyqSource posts status+reason to the review endpoint and refetches", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForSourceTrust([PAPER_WITH_SOURCE], [SRC_PENDING]);
    api.post.mockResolvedValue({ ok: true, audit_id: "aud-src", row: { id: "src-trust-1", trust_status: "verified" } });
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("pyq-paper-row-p-src"));
    await waitFor(() => expect(screen.getByTestId("verify-source-btn")).toBeTruthy());

    fireEvent.click(screen.getByTestId("verify-source-btn"));
    await waitFor(() => expect(screen.getByTestId("source-review-modal")).toBeTruthy());
    fireEvent.change(screen.getByTestId("source-review-reason"), {
      target: { value: "confirmed source is the official commission archive" },
    });
    fireEvent.click(screen.getByTestId("source-review-submit"));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-sources/src-trust-1/review"),
        { status: "verified", reason: "confirmed source is the official commission archive" },
      ),
    );
    // Refetch happens (onSuccess → fetchPapers) and the modal closes.
    await waitFor(() => expect(screen.queryByTestId("source-review-modal")).toBeNull());
    const pyqPaperCalls = api.get.mock.calls.filter((c) => c[0].includes("/pyq-papers?"));
    expect(pyqPaperCalls.length).toBeGreaterThan(1);
  });

  test("client guard: reason under 8 chars blocks the source review POST", async () => {
    useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
    mockApiForSourceTrust([PAPER_WITH_SOURCE], [SRC_PENDING]);
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-table")).toBeTruthy());
    fireEvent.click(screen.getByTestId("pyq-paper-row-p-src"));
    await waitFor(() => expect(screen.getByTestId("reject-source-btn")).toBeTruthy());

    fireEvent.click(screen.getByTestId("reject-source-btn"));
    await waitFor(() => expect(screen.getByTestId("source-review-modal")).toBeTruthy());
    fireEvent.change(screen.getByTestId("source-review-reason"), { target: { value: "short" } });
    fireEvent.click(screen.getByTestId("source-review-submit"));

    expect(screen.getByTestId("source-review-error").textContent).toContain("8 characters");
    expect(api.post).not.toHaveBeenCalledWith(
      expect.stringContaining("/review"),
      expect.objectContaining({ status: "rejected" }),
    );
  });
});
