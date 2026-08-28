/**
 * Tests for ScoreSnapshotPanel — PR B: Score Snapshot Workbench UI.
 *
 * Coverage:
 * - Renders scope selector with exam-wide default
 * - Renders phases from context in scope selector
 * - Sends exam_phase_id query param when phase selected
 * - Compute button triggers POST with correct scope (body, not query string)
 * - Modal stays open on API failure (preserves notes + shows error)
 * - Modal closes on success
 * - Evidence drawer shows scope, corpus, score_components
 * - Two-phase regression: Phase A list does NOT include Phase B rows
 * - Invalid phase param shows error banner (only after context is ready)
 * - Context loading state: shows loading UI, defers phase validation
 * - Context error state: shows error UI, blocks all mutations
 * - canReview=false: hides Compute button and action buttons
 * - canReview=true: shows Compute button and action buttons
 * - Duplicate phase names: uses human cycle label from cycles[]
 * - Modal dismissal guard: Escape does not close while busy
 * - Pagination: shows prev/next when total > PAGE_SIZE
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
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
// Supports controllable busy state. setBusy() updates the shared action
// handle and lets tests simulate an in-flight mutation.
const mockActionRun = jest.fn();

// A mutable handle exposed as a module-level const so jest.mock() can see it.
// Must be prefixed with "mock" to satisfy jest.mock() out-of-scope variable rule.
const mockActionHandle = { run: null, busy: false };

function setBusy(val) {
  mockActionHandle.busy = val;
}

jest.mock("../../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  // Return the same mutable handle every call so tests can control .busy.
  default: () => mockActionHandle,
}));

// ─── ExamWorkspaceContext mock ────────────────────────────────────────────────
const EXAM    = { id: "exam-1", name: "UPSC CSE" };
const PHASE_A = { id: "ph-1", exam_id: "exam-1", exam_cycle_id: "cycle-2026", phase_name: "Tier I",  phase_order: 1 };
const PHASE_B = { id: "ph-2", exam_id: "exam-1", exam_cycle_id: "cycle-2026", phase_name: "Tier II", phase_order: 2 };
const CYCLES  = [{ id: "cycle-2026", cycle_name: "2026 Cycle", year: 2026 }];

// Mutable context state for tests that need to override loading/error.
// Must be prefixed with "mock" to be accessible inside jest.mock() factories.
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

// ─── Helpers ──────────────────────────────────────────────────────────────────

import ScoreSnapshotPanel from "../ScoreSnapshotPanel";

// Fixtures use the real backend field names from score_snapshots.py:
//   input_summary:    fingerprint, paper_count, question_count, topic_primary_count, corpus_total_primary
//   score_components: frequency_component, coverage_component, evidence_quality
const SNAP_DRAFT = {
  id: "snap-1",
  exam_id: "exam-1",
  exam_phase_id: null,
  topic_id: "t-1",
  topic_name: "Polity",
  topic_path: "Indian Constitution",
  status: "draft",
  computed_at: "2026-01-01T00:00:00Z",
  input_summary: {
    fingerprint: "abc123fingerprint",
    paper_count: 3,
    question_count: 120,
    topic_primary_count: 5,
    corpus_total_primary: 200,
  },
  score_components: {
    frequency_component: 0.72,
    coverage_component: 0.55,
    evidence_quality: 0.40,
  },
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

function makeListResponse(snaps, total) {
  return { snapshots: snaps, total: total ?? snaps.length, exam_id: "exam-1" };
}

function renderPanel(initialSearch = "", props = {}) {
  return render(
    <MemoryRouter initialEntries={[`/admin/exams/exam-1/manage?tab=pyq&view=snapshots${initialSearch}`]}>
      <ScoreSnapshotPanel canReview={true} {...props} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  mockActionHandle.busy = false;
  mockActionHandle.run = mockActionRun;
  mockCtxOverride = null;
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

  it("shows invalid-scope-error banner for unknown phase param (after context ready)", async () => {
    renderPanel("&phase=unknown-phase-id");
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(screen.getByTestId("invalid-scope-error")).toBeInTheDocument();
  });
});

describe("ScoreSnapshotPanel — context loading/error guard", () => {
  it("shows loading UI and does NOT emit GET while context is loading", async () => {
    mockCtxOverride = { exam: EXAM, phases: [], cycles: [], loading: true, error: "" };
    renderPanel();
    expect(screen.getByTestId("context-loading")).toBeInTheDocument();
    // No list call — panel must wait for context.
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("does NOT show invalid-scope-error while context is loading", () => {
    mockCtxOverride = { exam: EXAM, phases: [], cycles: [], loading: true, error: "" };
    renderPanel("&phase=ph-1");
    expect(screen.queryByTestId("invalid-scope-error")).not.toBeInTheDocument();
  });

  it("shows context error UI and does NOT emit GET when context errored", async () => {
    mockCtxOverride = { exam: EXAM, phases: [], cycles: [], loading: false, error: "Network error" };
    renderPanel();
    expect(screen.getByTestId("context-error")).toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe("ScoreSnapshotPanel — canReview permission gate", () => {
  it("hides Compute button when canReview=false", async () => {
    renderPanel("", { canReview: false });
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(screen.queryByTestId("compute-btn")).not.toBeInTheDocument();
  });

  it("shows Compute button when canReview=true", async () => {
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(screen.getByTestId("compute-btn")).toBeInTheDocument();
  });

  it("hides action buttons when canReview=false", async () => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_DRAFT]));
    renderPanel("", { canReview: false });
    await waitFor(() => screen.getAllByTestId(/snapshot-row/));
    expect(screen.queryByTestId(`action-${SNAP_DRAFT.id}-reviewed`)).not.toBeInTheDocument();
    expect(screen.queryByTestId(`action-${SNAP_DRAFT.id}-rejected`)).not.toBeInTheDocument();
  });
});

describe("ScoreSnapshotPanel — duplicate phase names", () => {
  it("uses human cycle label from cycles[] when two phases share the same phase_name", async () => {
    mockCtxOverride = {
      exam: EXAM,
      phases: [
        { id: "ph-1", exam_id: "exam-1", exam_cycle_id: "cycle-2025", phase_name: "Tier I", phase_order: 1 },
        { id: "ph-2", exam_id: "exam-1", exam_cycle_id: "cycle-2026", phase_name: "Tier I", phase_order: 2 },
      ],
      cycles: [
        { id: "cycle-2025", cycle_name: "2025 Cycle", year: 2025 },
        { id: "cycle-2026", cycle_name: "2026 Cycle", year: 2026 },
      ],
      loading: false,
      error: "",
    };
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    // Both buttons should show human cycle label, not raw UUID
    expect(screen.getByText("Tier I · 2025 Cycle")).toBeInTheDocument();
    expect(screen.getByText("Tier I · 2026 Cycle")).toBeInTheDocument();
    expect(screen.queryByText(/cycle-2025/)).not.toBeInTheDocument();
    expect(screen.queryByText(/cycle-2026/)).not.toBeInTheDocument();
  });

  it("with distinct names, labels are plain (no cycle suffix)", async () => {
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(screen.getByText("Tier I")).toBeInTheDocument();
    expect(screen.getByText("Tier II")).toBeInTheDocument();
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
    // Wait for row to appear, not just for mockGet to be called
    await waitFor(() => expect(screen.getAllByTestId(/snapshot-row/)).toHaveLength(1));
    // No exam-wide row
    expect(screen.queryByText("Polity")).not.toBeInTheDocument();
    expect(screen.getByText("Economy")).toBeInTheDocument();
  });

  it("sends limit and offset query params", async () => {
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    const url = mockGet.mock.calls[0][0];
    expect(url).toContain("limit=50");
    expect(url).toContain("offset=0");
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
    // Call action to inspect POST body — exam_phase_id must NOT be in the URL
    mockPost.mockResolvedValue({});
    await call.action();
    const url = mockPost.mock.calls[0][0];
    expect(url).not.toContain("exam_phase_id");
    // Body must not contain exam_phase_id for exam-wide scope
    const body = mockPost.mock.calls[0][1];
    expect(body).not.toHaveProperty("exam_phase_id");
  });

  it("includes exam_phase_id in compute POST body (not URL) when phase selected", async () => {
    renderPanel("&phase=ph-2");
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("compute-btn"));
    const call = mockActionRun.mock.calls[0][0];
    mockPost.mockResolvedValue({});
    await call.action();
    const url = mockPost.mock.calls[0][0];
    // exam_phase_id must NOT be in the URL
    expect(url).not.toContain("exam_phase_id");
    // exam_phase_id must be in the request body
    const body = mockPost.mock.calls[0][1];
    expect(body).toHaveProperty("exam_phase_id", "ph-2");
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

describe("ScoreSnapshotPanel — modal dismissal guard", () => {
  beforeEach(() => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_LOCKED_PHASE_A]));
  });

  it("does not close modal on Escape while mutation is in flight", async () => {
    // Simulate a pending (never-resolving) mutation while busy=true
    let resolveMutation;
    mockActionRun.mockImplementation(() => {
      return new Promise((res) => { resolveMutation = res; });
    });

    renderPanel("&phase=ph-1");
    await waitFor(() => screen.getAllByTestId(/snapshot-row/));

    fireEvent.click(screen.getByTestId(`action-${SNAP_LOCKED_PHASE_A.id}-reviewed`));
    expect(screen.getByTestId("reviewer-notes-input")).toBeInTheDocument();

    // Set busy BEFORE submit so the modal sees busy=true when Escape fires.
    setBusy(true);

    fireEvent.change(screen.getByTestId("reviewer-notes-input"), { target: { value: "reason" } });
    fireEvent.click(screen.getByTestId("reviewer-notes-submit"));

    // Escape on the modal — should NOT close while busy.
    fireEvent.keyDown(document.body, { key: "Escape" });

    // Modal must still be open — notes input still present.
    expect(screen.getByTestId("reviewer-notes-input")).toBeInTheDocument();

    // Resolve the mutation so the test can finish cleanly
    setBusy(false);
    resolveMutation({ ok: false, error: { message: "server error" } });
    await waitFor(() => expect(screen.getByTestId("notes-modal-error")).toBeInTheDocument());
  });
});

describe("ScoreSnapshotPanel — evidence drawer", () => {
  beforeEach(() => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_DRAFT]));
  });

  it("shows evidence drawer via expand button with scope, corpus, score_components", async () => {
    renderPanel();
    await waitFor(() => screen.getAllByTestId(/snapshot-row/));

    // Expansion is via the disclosure button, not a row click
    fireEvent.click(screen.getByTestId(`expand-btn-${SNAP_DRAFT.id}`));

    const drawer = await screen.findByTestId(`evidence-drawer-${SNAP_DRAFT.id}`);
    expect(drawer).toBeInTheDocument();

    // Scope — exam-wide because snap.exam_phase_id is null
    expect(drawer).toHaveTextContent("Exam-wide");
    // Corpus — real field names from score_snapshots.py
    expect(drawer).toHaveTextContent("3 papers");
    expect(drawer).toHaveTextContent("120 questions");
    expect(drawer).toHaveTextContent("5");   // topic_primary_count
    // Score components — real field names
    expect(drawer).toHaveTextContent("frequency_component");
    expect(drawer).toHaveTextContent("coverage_component");
    expect(drawer).toHaveTextContent("evidence_quality");
  });

  it("shows phase scope label in evidence drawer for a phase-scoped snapshot", async () => {
    const phaseSnap = { ...SNAP_DRAFT, id: "snap-ph", exam_phase_id: "ph-1" };
    mockGet.mockResolvedValue(makeListResponse([phaseSnap]));
    renderPanel("&phase=ph-1");
    await waitFor(() => screen.getAllByTestId(/snapshot-row/));
    fireEvent.click(screen.getByTestId(`expand-btn-snap-ph`));
    const drawer = await screen.findByTestId(`evidence-drawer-snap-ph`);
    // The scope label should resolve to the phase name, not a UUID
    expect(drawer).toHaveTextContent("Tier I");
  });
});

describe("ScoreSnapshotPanel — pagination", () => {
  it("shows pagination controls when total > PAGE_SIZE", async () => {
    mockGet.mockResolvedValue(makeListResponse(
      Array.from({ length: 50 }, (_, i) => ({ ...SNAP_DRAFT, id: `snap-${i}` })),
      120,
    ));
    renderPanel();
    // Wait for actual rows to appear (state update complete)
    await waitFor(() => expect(screen.getAllByTestId(/snapshot-row/)).toHaveLength(50));
    expect(screen.getByTestId("page-next-btn")).toBeInTheDocument();
    expect(screen.getByTestId("page-prev-btn")).toBeInTheDocument();
  });

  it("does not show pagination when total <= PAGE_SIZE", async () => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_DRAFT], 1));
    renderPanel();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(screen.queryByTestId("page-next-btn")).not.toBeInTheDocument();
  });
});

// ─── Part D: subject-group sectioning + 0-evidence flag ─────────────────────────

// GS Paper I leaf (real evidence), CSAT Paper II leaf (real evidence), and a
// CSAT rollup/header node with zero evidence — the shape that produced the
// flat, undifferentiated list before this fix.
const SNAP_GS = {
  ...SNAP_DRAFT, id: "snap-gs", topic_name: "Polity", subject_group: "gs",
  subject_name: "Polity & Governance", evidence_count: 12, status: "draft",
};
const SNAP_CSAT = {
  ...SNAP_DRAFT, id: "snap-csat", topic_name: "Reading Comprehension",
  subject_group: "reasoning", subject_name: "CSAT (Aptitude)", evidence_count: 8,
  status: "draft",
};
const SNAP_CSAT_ROLLUP = {
  ...SNAP_DRAFT, id: "snap-rollup", topic_name: "General mental ability",
  subject_group: "reasoning", subject_name: "CSAT (Aptitude)", evidence_count: 0,
  status: "draft",
};

describe("ScoreSnapshotPanel — subject-group sectioning", () => {
  it("sections GS Paper I and CSAT Paper II under separate, labelled headers", async () => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_GS, SNAP_CSAT], 2));
    renderPanel();
    await waitFor(() => screen.getByTestId(`snapshot-row-${SNAP_GS.id}`));

    const gsHead = screen.getByTestId("group-header-gs");
    const csatHead = screen.getByTestId("group-header-reasoning");
    expect(gsHead).toHaveTextContent("GS Paper I");
    expect(csatHead).toHaveTextContent("CSAT Paper II");
    // GS section renders before CSAT (GS-first ordering).
    expect(gsHead.compareDocumentPosition(csatHead) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // Both leaves still render as normal rows.
    expect(screen.getByTestId(`snapshot-row-${SNAP_GS.id}`)).toBeInTheDocument();
    expect(screen.getByTestId(`snapshot-row-${SNAP_CSAT.id}`)).toBeInTheDocument();
  });

  it("puts subject-less rows in an explicit Unclassified section, never merged into a paper", async () => {
    const orphan = { ...SNAP_DRAFT, id: "snap-orphan", subject_group: null, evidence_count: 3 };
    mockGet.mockResolvedValue(makeListResponse([SNAP_GS, orphan], 2));
    renderPanel();
    await waitFor(() => screen.getByTestId(`snapshot-row-${orphan.id}`));
    expect(screen.getByTestId("group-header-__none__")).toHaveTextContent("Unclassified");
  });
});

describe("ScoreSnapshotPanel — 0-evidence rollup flag", () => {
  it("flags a 0-evidence node visibly and does not silently drop it", async () => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_CSAT_ROLLUP], 1));
    renderPanel();
    await waitFor(() => screen.getByTestId(`snapshot-row-${SNAP_CSAT_ROLLUP.id}`));
    // Still visible…
    expect(screen.getByText("General mental ability")).toBeInTheDocument();
    // …and explicitly flagged.
    expect(screen.getByTestId(`zero-evidence-flag-${SNAP_CSAT_ROLLUP.id}`)).toBeInTheDocument();
  });

  it("disables Approve on a 0-evidence draft but keeps Reject enabled (consciously rejectable, not approvable)", async () => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_CSAT_ROLLUP], 1));
    renderPanel();
    await waitFor(() => screen.getByTestId(`snapshot-row-${SNAP_CSAT_ROLLUP.id}`));
    expect(screen.getByTestId(`action-${SNAP_CSAT_ROLLUP.id}-reviewed`)).toBeDisabled();
    expect(screen.getByTestId(`action-${SNAP_CSAT_ROLLUP.id}-rejected`)).not.toBeDisabled();
  });

  it("blocks Lock on a 0-evidence reviewed node", async () => {
    const reviewedRollup = { ...SNAP_CSAT_ROLLUP, id: "snap-rev-rollup", status: "reviewed" };
    mockGet.mockResolvedValue(makeListResponse([reviewedRollup], 1));
    renderPanel();
    await waitFor(() => screen.getByTestId(`snapshot-row-${reviewedRollup.id}`));
    expect(screen.getByTestId(`action-${reviewedRollup.id}-locked`)).toBeDisabled();
    // Reject and Revert-draft stay available.
    expect(screen.getByTestId(`action-${reviewedRollup.id}-rejected`)).not.toBeDisabled();
    expect(screen.getByTestId(`action-${reviewedRollup.id}-draft`)).not.toBeDisabled();
  });

  it("does not flag or block a real evidence-backed leaf", async () => {
    mockGet.mockResolvedValue(makeListResponse([SNAP_GS], 1));
    renderPanel();
    await waitFor(() => screen.getByTestId(`snapshot-row-${SNAP_GS.id}`));
    expect(screen.queryByTestId(`zero-evidence-flag-${SNAP_GS.id}`)).not.toBeInTheDocument();
    expect(screen.getByTestId(`action-${SNAP_GS.id}-reviewed`)).not.toBeDisabled();
  });
});
