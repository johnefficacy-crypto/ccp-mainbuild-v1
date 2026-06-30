/**
 * Tests for ScoreSnapshotPanel — PR B: Score Snapshot Workbench UI.
 *
 * Coverage:
 * - Renders scope selector with exam-wide default
 * - Renders phases from context in scope selector
 * - Sends exam_phase_id query param when phase selected
 * - Compute button triggers POST with correct scope
 * - Modal stays open on API failure (preserves notes + shows error)
 * - Modal closes on success
 * - Evidence drawer shows scope, corpus, score_components
 * - Two-phase regression: Phase A list does NOT include Phase B rows
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// ─── api mock ────────────────────────────────────────────────────────────────
const mockGet  = jest.fn();
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
// The component calls useApiAction() twice (compute + review).
// We expose a single mockActionRun that both instances share.
const mockActionRun = jest.fn();

jest.mock("../../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({ run: mockActionRun, busy: false }),
}));

// ─── ExamWorkspaceContext mock ────────────────────────────────────────────────
const EXAM  = { id: "exam-1", name: "UPSC CSE" };
const PHASE_A = { id: "ph-1", exam_id: "exam-1", exam_cycle_id: "cycle-2026", phase_name: "Tier I",  phase_order: 1 };
const PHASE_B = { id: "ph-2", exam_id: "exam-1", exam_cycle_id: "cycle-2026", phase_name: "Tier II", phase_order: 2 };

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: () => ({
    exam:   EXAM,
    phases: [PHASE_A, PHASE_B],
    cycle:  { id: "cycle-2026" },
  }),
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

import ScoreSnapshotPanel from "../ScoreSnapshotPanel";

const SNAP_DRAFT = {
  id: "snap-1",
  exam_id: "exam-1",
  exam_phase_id: null,
  topic_id: "t-1",
  topic_name: "Polity",
  status: "draft",
  computed_at: "2026-01-01T00:00:00Z",
  input_summary: { paper_count: 3, question_count: 120, primary_tag_count: 5 },
  score_components: { frequency: 0.72, recency: 0.55 },
  model_version: "v2",
  model_fingerprint: "abc123",
};

const SNAP_LOCKED_PHASE_A = {
  ...SNAP_DRAFT,
  id: "snap-2",
  exam_phase_id: "ph-1",
  status: "locked",
  topic_name: "Economy",
};

function makeListResponse(snaps) {
  return { snapshots: snaps, total: snaps.length, exam_id: "exam-1" };
}

function renderPanel(initialSearch = "") {
  return render(
    <MemoryRouter initialEntries={[`/admin/exams/exam-1/manage?tab=pyq&view=snapshots${initialSearch}`]}>
      <ScoreSnapshotPanel />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGet.mockResolvedValue(makeListResponse([]));
  mockActionRun.mockResolvedValue({ ok: true, data: {} });
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ScoreSnapshotPanel — scope selector", () => {
  it("renders exam-wide scope button", async () => {
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(screen.getByTestId("scope-exam")).toBeInTheDocument();
  });

  it("renders phases from context as scope buttons", async () => {
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(screen.getByTestId("scope-ph-1")).toBeInTheDocument();
    expect(screen.getByTestId("scope-ph-2")).toBeInTheDocument();
    expect(screen.getByText("Tier I")).toBeInTheDocument();
    expect(screen.getByText("Tier II")).toBeInTheDocument();
  });

  it("marks phase button as active when ?phase= param set in URL", async () => {
    renderPanel("&phase=ph-1");
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(screen.getByTestId("scope-ph-1").className).toMatch(/active/);
  });
});

describe("ScoreSnapshotPanel — API scope isolation", () => {
  it("fetches exam-wide (no exam_phase_id) when scope = exam-wide", async () => {
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    const url = mockGet.mock.calls[0][0];
    expect(url).not.toContain("exam_phase_id");
  });

  it("includes exam_phase_id when a phase is selected via URL", async () => {
    renderPanel("&phase=ph-1");
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    const url = mockGet.mock.calls[0][0];
    expect(url).toContain("exam_phase_id=ph-1");
  });

  it("two-phase regression: Phase A list does not contain Phase B rows", async () => {
    // First render: Phase A scope
    mockGet.mockResolvedValue(makeListResponse([SNAP_LOCKED_PHASE_A]));
    renderPanel("&phase=ph-1");
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    // Only snap-2 (ph-1) should appear
    expect(screen.getAllByTestId(/snapshot-row/)).toHaveLength(1);
    // No exam-wide row
    expect(screen.queryByText("Polity")).not.toBeInTheDocument();
    expect(screen.getByText("Economy")).toBeInTheDocument();
  });
});

describe("ScoreSnapshotPanel — compute button", () => {
  it("triggers compute POST with no exam_phase_id for exam-wide", async () => {
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("compute-btn"));
    expect(mockActionRun).toHaveBeenCalledTimes(1);
    const call = mockActionRun.mock.calls[0][0];
    expect(call.action).toBeDefined();
    // Call action to inspect URL
    mockPost.mockResolvedValue({});
    await call.action();
    const url = mockPost.mock.calls[0][0];
    expect(url).not.toContain("exam_phase_id");
  });

  it("includes exam_phase_id in compute POST when phase selected", async () => {
    renderPanel("&phase=ph-2");
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("compute-btn"));
    const call = mockActionRun.mock.calls[0][0];
    mockPost.mockResolvedValue({});
    await call.action();
    const url = mockPost.mock.calls[0][0];
    expect(url).toContain("exam_phase_id=ph-2");
  });
});

describe("ScoreSnapshotPanel — reviewer notes modal", () => {
  beforeEach(() => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_LOCKED_PHASE_A]));
    mockActionRun.mockResolvedValue({ ok: false, error: { message: "Conflict: already in use" } });
  });

  it("stays open and shows error when revert fails", async () => {
    renderPanel("&phase=ph-1");
    await waitFor(() => screen.getAllByTestId(/snapshot-row/));

    // Click the revert button for the locked snapshot (locked → reviewed)
    fireEvent.click(screen.getByTestId(`action-${SNAP_LOCKED_PHASE_A.id}-reviewed`));
    expect(screen.getByTestId("reviewer-notes-input")).toBeInTheDocument();

    // Fill in notes and submit
    fireEvent.change(screen.getByTestId("reviewer-notes-input"), { target: { value: "wrong evidence" } });
    fireEvent.click(screen.getByTestId("reviewer-notes-submit"));

    await waitFor(() => expect(mockActionRun).toHaveBeenCalled());

    // Modal should still be open with error shown
    await waitFor(() => expect(screen.getByTestId("notes-modal-error")).toBeInTheDocument());
    expect(screen.getByTestId("reviewer-notes-input")).toBeInTheDocument();
    expect(screen.getByTestId("notes-modal-error")).toHaveTextContent("Conflict");
  });

  it("closes modal on successful revert", async () => {
    // First call returns locked; after success, reloads with reviewed
    mockActionRun.mockResolvedValue({ ok: true, data: {} });
    mockGet
      .mockResolvedValueOnce(makeListResponse([SNAP_LOCKED_PHASE_A]))
      .mockResolvedValue(makeListResponse([{ ...SNAP_LOCKED_PHASE_A, status: "reviewed" }]));

    renderPanel("&phase=ph-1");
    await waitFor(() => screen.getAllByTestId(/snapshot-row/));

    fireEvent.click(screen.getByTestId(`action-${SNAP_LOCKED_PHASE_A.id}-reviewed`));
    fireEvent.change(screen.getByTestId("reviewer-notes-input"), { target: { value: "valid reason" } });
    fireEvent.click(screen.getByTestId("reviewer-notes-submit"));

    await waitFor(() => expect(mockActionRun).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByTestId("reviewer-notes-input")).not.toBeInTheDocument());
  });
});

describe("ScoreSnapshotPanel — evidence drawer", () => {
  beforeEach(() => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_DRAFT]));
  });

  it("shows evidence drawer on row click with scope, corpus, score_components", async () => {
    renderPanel();
    await waitFor(() => screen.getAllByTestId(/snapshot-row/));

    fireEvent.click(screen.getByTestId(`snapshot-row-${SNAP_DRAFT.id}`));

    const drawer = await screen.findByTestId(`evidence-drawer-${SNAP_DRAFT.id}`);
    expect(drawer).toBeInTheDocument();

    // Scope
    expect(drawer).toHaveTextContent("Exam-wide");
    // Corpus
    expect(drawer).toHaveTextContent("3 papers");
    expect(drawer).toHaveTextContent("120 questions");
    expect(drawer).toHaveTextContent("5 primary tags");
    // Score components
    expect(drawer).toHaveTextContent("frequency");
    expect(drawer).toHaveTextContent("recency");
  });
});
