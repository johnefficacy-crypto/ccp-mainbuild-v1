/**
 * Tests for CoveragePanel — wires the existing exam_topic_coverage routes
 * (derive / list / per-row review) into the operator UI. Sibling of
 * ScoreSnapshotPanel; mirrors its test scaffolding.
 *
 * Coverage:
 * - Derive button POSTs .../coverage/derive with the selected scope, then reloads
 * - Derive scope: exam-wide sends empty body; a phase sends { exam_phase_id }
 * - Per-row Lock PATCHes .../topic-coverage/{id}/review with reviewer_status:locked, then reloads
 * - Locked row shows Unlock (→ draft), not Lock
 * - Bulk-lock loops the per-row PATCH over ONLY draft rows
 * - canManage gate hides Derive; canReview gate hides Lock + bulk-lock
 * - Context loading / error guards block the list read
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// ─── api mock ────────────────────────────────────────────────────────────────
const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPatch = jest.fn();

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: {
    get:   (...a) => mockGet(...a),
    post:  (...a) => mockPost(...a),
    patch: (...a) => mockPatch(...a),
  },
}));

// ─── useApiAction mock ────────────────────────────────────────────────────────
const mockActionRun = jest.fn();
const mockActionHandle = { run: null, busy: false };

jest.mock("../../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => mockActionHandle,
}));

// ─── ExamWorkspaceContext mock ────────────────────────────────────────────────
const EXAM    = { id: "exam-1", name: "UPSC CSE" };
const PHASE_A = { id: "ph-1", exam_id: "exam-1", exam_cycle_id: "cycle-2026", phase_name: "Tier I",  phase_order: 1 };
const PHASE_B = { id: "ph-2", exam_id: "exam-1", exam_cycle_id: "cycle-2026", phase_name: "Tier II", phase_order: 2 };
const CYCLES  = [{ id: "cycle-2026", cycle_name: "2026 Cycle", year: 2026 }];

let mockCtxOverride = null;

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: () => {
    if (mockCtxOverride) return mockCtxOverride;
    return {
      exam:    EXAM,
      phases:  [PHASE_A, PHASE_B],
      cycles:  CYCLES,
      cycle:   { id: "cycle-2026" },
      loading: false,
      error:   "",
    };
  },
}));

import CoveragePanel from "../CoveragePanel";

// Item shape matches GET /topic-coverage's mapped output.
const ROW_DRAFT = {
  id: "cov-1", topic: "Ancient India", topic_id: "t-1", subject: "History",
  priority_score: 42.5, high_yield: false, evidence_count: 12,
  status: "draft", reviewed_at: null,
};
const ROW_DRAFT_2 = { ...ROW_DRAFT, id: "cov-2", topic: "Medieval India" };
const ROW_LOCKED = {
  ...ROW_DRAFT, id: "cov-3", topic: "Modern India", status: "locked",
  reviewed_at: "2026-02-01T00:00:00Z",
};

function makeList(items) {
  return { items, count: items.length };
}

function renderPanel(props = {}, initialSearch = "") {
  return render(
    <MemoryRouter initialEntries={[`/admin/exams/exam-1/manage?tab=pyq&view=coverage${initialSearch}`]}>
      <CoveragePanel canReview={true} canManage={true} {...props} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  mockActionHandle.busy = false;
  mockActionHandle.run = mockActionRun;
  mockCtxOverride = null;
  mockGet.mockResolvedValue(makeList([]));
  mockPatch.mockResolvedValue({});
  mockActionRun.mockResolvedValue({ ok: true, data: {} });
});

// ─── Derive ───────────────────────────────────────────────────────────────────

describe("CoveragePanel — derive", () => {
  it("emits GET /topic-coverage for the exam on mount", async () => {
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(mockGet.mock.calls[0][0]).toContain("/topic-coverage?");
    expect(mockGet.mock.calls[0][0]).toContain("exam_id=exam-1");
  });

  it("Derive (exam-wide) runs the action against the derive endpoint with an empty body, then reloads", async () => {
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    mockGet.mockClear();

    fireEvent.click(screen.getByTestId("derive-btn"));

    await waitFor(() => expect(mockActionRun).toHaveBeenCalled());
    // Invoke the deferred action fn to assert the real endpoint + body.
    await mockActionRun.mock.calls[0][0].action();
    expect(mockPost).toHaveBeenCalledWith(
      "/api/admin/exam-intelligence/exams/exam-1/coverage/derive",
      {},
    );
    // Reload happened after a successful derive.
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
  });

  it("Derive with a phase scope sends { exam_phase_id }", async () => {
    renderPanel({}, "&phase=ph-1");
    await waitFor(() => expect(mockGet).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId("derive-btn"));
    await waitFor(() => expect(mockActionRun).toHaveBeenCalled());
    await mockActionRun.mock.calls[0][0].action();
    expect(mockPost).toHaveBeenCalledWith(
      "/api/admin/exam-intelligence/exams/exam-1/coverage/derive",
      { exam_phase_id: "ph-1" },
    );
  });
});

// ─── Per-row lock ──────────────────────────────────────────────────────────────

describe("CoveragePanel — per-row lock", () => {
  it("Lock on a draft row PATCHes review with reviewer_status:locked, then reloads", async () => {
    mockGet.mockResolvedValue(makeList([ROW_DRAFT]));
    renderPanel();
    await waitFor(() => screen.getByTestId(`coverage-row-${ROW_DRAFT.id}`));
    mockGet.mockClear();

    fireEvent.click(screen.getByTestId(`action-${ROW_DRAFT.id}-lock`));
    await waitFor(() => expect(mockActionRun).toHaveBeenCalled());
    await mockActionRun.mock.calls[0][0].action();
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/admin/exam-intelligence/topic-coverage/cov-1/review",
      { reviewer_status: "locked" },
    );
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
  });

  it("a locked row shows Unlock (→ draft), not Lock", async () => {
    mockGet.mockResolvedValue(makeList([ROW_LOCKED]));
    renderPanel();
    await waitFor(() => screen.getByTestId(`coverage-row-${ROW_LOCKED.id}`));
    expect(screen.getByTestId(`action-${ROW_LOCKED.id}-unlock`)).toBeInTheDocument();
    expect(screen.queryByTestId(`action-${ROW_LOCKED.id}-lock`)).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId(`action-${ROW_LOCKED.id}-unlock`));
    await waitFor(() => expect(mockActionRun).toHaveBeenCalled());
    await mockActionRun.mock.calls[0][0].action();
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/admin/exam-intelligence/topic-coverage/cov-3/review",
      { reviewer_status: "draft" },
    );
  });
});

// ─── Bulk lock ─────────────────────────────────────────────────────────────────

describe("CoveragePanel — bulk lock", () => {
  it("locks ONLY draft rows: two drafts + one locked -> two PATCHes, both to locked", async () => {
    mockGet.mockResolvedValue(makeList([ROW_DRAFT, ROW_DRAFT_2, ROW_LOCKED]));
    renderPanel();
    await waitFor(() => screen.getByTestId(`coverage-row-${ROW_DRAFT.id}`));

    // Button counts only the two drafts.
    const bulk = screen.getByTestId("bulk-lock-btn");
    expect(bulk).toHaveTextContent("Lock all drafts (2)");

    fireEvent.click(bulk);

    await waitFor(() => expect(mockPatch).toHaveBeenCalledTimes(2));
    const patchedIds = mockPatch.mock.calls.map((c) => c[0]);
    expect(patchedIds).toEqual(expect.arrayContaining([
      "/api/admin/exam-intelligence/topic-coverage/cov-1/review",
      "/api/admin/exam-intelligence/topic-coverage/cov-2/review",
    ]));
    // The locked row was never re-PATCHed.
    expect(patchedIds).not.toContain("/api/admin/exam-intelligence/topic-coverage/cov-3/review");
    mockPatch.mock.calls.forEach((c) => expect(c[1]).toEqual({ reviewer_status: "locked" }));
    await waitFor(() => expect(screen.getByTestId("bulk-note")).toHaveTextContent("Locked 2"));
  });

  it("bulk-lock button is disabled when there are no draft rows", async () => {
    mockGet.mockResolvedValue(makeList([ROW_LOCKED]));
    renderPanel();
    await waitFor(() => screen.getByTestId(`coverage-row-${ROW_LOCKED.id}`));
    expect(screen.getByTestId("bulk-lock-btn")).toBeDisabled();
  });
});

// ─── Permission gates ───────────────────────────────────────────────────────────

describe("CoveragePanel — permission gates", () => {
  it("hides Derive when canManage=false", async () => {
    renderPanel({ canManage: false });
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(screen.queryByTestId("derive-btn")).not.toBeInTheDocument();
  });

  it("hides Lock + bulk-lock when canReview=false", async () => {
    mockGet.mockResolvedValue(makeList([ROW_DRAFT]));
    renderPanel({ canReview: false });
    await waitFor(() => screen.getByTestId(`coverage-row-${ROW_DRAFT.id}`));
    expect(screen.queryByTestId(`action-${ROW_DRAFT.id}-lock`)).not.toBeInTheDocument();
    expect(screen.queryByTestId("bulk-lock-btn")).not.toBeInTheDocument();
  });
});

// ─── Context guard ──────────────────────────────────────────────────────────────

describe("CoveragePanel — context guard", () => {
  it("shows loading UI and does NOT read the list while context is loading", () => {
    mockCtxOverride = { exam: EXAM, phases: [], cycles: [], loading: true, error: "" };
    renderPanel();
    expect(screen.getByTestId("context-loading")).toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("shows error UI and does NOT read the list when context errored", () => {
    mockCtxOverride = { exam: EXAM, phases: [], cycles: [], loading: false, error: "Network error" };
    renderPanel();
    expect(screen.getByTestId("context-error")).toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });
});
