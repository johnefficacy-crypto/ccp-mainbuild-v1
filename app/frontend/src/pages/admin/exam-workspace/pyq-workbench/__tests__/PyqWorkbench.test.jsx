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
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
}));

const { api } = require("../../../../../lib/api");
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
  beforeEach(() => { jest.clearAllMocks(); mockContextApi(); });

  test("fetches papers on mount with correct exam_id", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining(`exam_id=${EXAM_ID}`)),
    );
  });

  test("passes exam_cycle_id when workspace has a cycle", async () => {
    jest.clearAllMocks();
    mockContextApi({ withCycle: true });
    render(<WorkspaceWrapper cycleId={CYCLE_ID}><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining(`exam_cycle_id=${CYCLE_ID}`),
      ),
    );
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

  test("paper select appears after load", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-select")).toBeTruthy());
  });

  test("selecting a paper renders PyqPaperWorkspace", async () => {
    render(<WorkspaceWrapper><PyqWorkbenchPanel /></WorkspaceWrapper>);
    await waitFor(() => expect(screen.getByTestId("pyq-paper-select")).toBeTruthy());
    fireEvent.change(screen.getByTestId("pyq-paper-select"), { target: { value: "p1" } });
    // After selection, the workspace loads questions (embedded PyqPaperWorkspace)
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-papers/p1"),
      ),
    );
  });
});

describe("PyqPaperWorkspace — paperId prop / embedded", () => {
  const PAPER_ID = "p1";

  beforeEach(() => {
    jest.clearAllMocks();
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
