/**
 * Tests for CandidateCountsSection (J3 PR2 follow-up — applied-vs-appeared
 * operator UI). Covers the checkpost findings:
 * - permission tier: manage sees create/edit; review sees lifecycle; cms does
 *   NOT get the normal-surface create button; super_admin bypass
 * - evidence gate: reviewed disabled without evidence, enabled with it
 * - transition matrix aligned to migration 219 (reviewed -> locked only; no
 *   reviewed -> rejected)
 * - edit/PATCH payload shape
 * - integer validation rejects 12.9 and 1e3 (no truncation)
 * - useApiAction usage (success toast surfaces)
 * - a11y label associations present
 * - no client-side denominator heuristic
 * - cycle required (no submit of exam_cycle_id: null) + server-side cycle scope
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ToastProvider } from "../../../../../shared/ui/core";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
}));

jest.mock("../../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: jest.fn(),
}));

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: jest.fn(),
}));

const { api } = require("../../../../../lib/api");
const { useAuth } = require("../../../../../lib/authContext");
const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const CandidateCountsSection = require("../CandidateCountsSection").default;

const WORKSPACE = {
  exam: { id: "exam-1", name: "UPSC CSE" },
  cycle: { id: "cyc-1", cycle_name: "2024" },
  phases: [{ id: "phase-1", phase_name: "Prelims" }],
};

function renderCC() {
  return render(
    <ToastProvider>
      <CandidateCountsSection />
    </ToastProvider>,
  );
}

function lastPost() {
  const calls = api.post.mock.calls;
  return calls[calls.length - 1];
}
function lastPatch() {
  const calls = api.patch.mock.calls;
  return calls[calls.length - 1];
}

// Route api.get by URL: list vs per-row evidence.
function mockGet({ items = [], evidence = [] } = {}) {
  api.get.mockImplementation((url) => {
    if (String(url).includes("/evidence")) return Promise.resolve({ items: evidence });
    return Promise.resolve({ items });
  });
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.patch.mockReset();
  mockGet({ items: [] });
  api.post.mockResolvedValue({ ok: true });
  api.patch.mockResolvedValue({ ok: true });
  useExamWorkspace.mockReturnValue(WORKSPACE);
  useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
});

describe("create payloads", () => {
  test("applied → cycle-scoped official-total payload, reason≥8, no phase", async () => {
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId("candidate-count-add"));
    fireEvent.change(screen.getByTestId("candidate-count-value"), { target: { value: "1,200,000" } });
    fireEvent.click(screen.getByTestId("candidate-count-save"));

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [url, body] = lastPost();
    expect(url).toBe("/api/admin/exam-intelligence-cms/exam-candidate-counts");
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    expect(body.payload.count_type).toBe("applied");
    expect(body.payload.scope_kind).toBe("cycle");
    expect(body.payload.reservation_category_id).toBeNull();
    expect(body.payload.count_value).toBe(1200000);
    expect(body.payload.exam_cycle_id).toBe("cyc-1");
    expect(body.payload).not.toHaveProperty("exam_phase_id");
    expect(JSON.stringify(body)).not.toMatch(/reviewer_status|reviewed|locked/);
  });

  test("appeared → phase-scoped payload carries exam_phase_id", async () => {
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId("candidate-count-add"));
    fireEvent.change(screen.getByTestId("candidate-count-type"), { target: { value: "appeared" } });
    fireEvent.change(screen.getByTestId("candidate-count-scope"), { target: { value: "phase" } });
    fireEvent.change(screen.getByTestId("candidate-count-phase"), { target: { value: "phase-1" } });
    fireEvent.change(screen.getByTestId("candidate-count-value"), { target: { value: "500000" } });
    fireEvent.click(screen.getByTestId("candidate-count-save"));

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [, body] = lastPost();
    expect(body.payload.count_type).toBe("appeared");
    expect(body.payload.scope_kind).toBe("phase");
    expect(body.payload.exam_phase_id).toBe("phase-1");
    expect(body.payload.count_value).toBe(500000);
  });

  test("useApiAction surfaces a success toast after create", async () => {
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("candidate-count-add"));
    fireEvent.change(screen.getByTestId("candidate-count-value"), { target: { value: "1000" } });
    fireEvent.click(screen.getByTestId("candidate-count-save"));
    expect(await screen.findByText("Candidate count saved as draft.")).toBeInTheDocument();
  });
});

describe("integer validation (no truncation)", () => {
  test("rejects a decimal (12.9) — form error, disabled save, no POST", async () => {
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("candidate-count-add"));
    fireEvent.change(screen.getByTestId("candidate-count-value"), { target: { value: "12.9" } });
    expect(screen.getByTestId("candidate-count-form-error")).toBeInTheDocument();
    expect(screen.getByTestId("candidate-count-save")).toBeDisabled();
    fireEvent.click(screen.getByTestId("candidate-count-save"));
    expect(api.post).not.toHaveBeenCalled();
  });

  test("rejects exponent syntax (1e3) rather than parsing it to 1", async () => {
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("candidate-count-add"));
    fireEvent.change(screen.getByTestId("candidate-count-value"), { target: { value: "1e3" } });
    expect(screen.getByTestId("candidate-count-form-error")).toBeInTheDocument();
    expect(screen.getByTestId("candidate-count-save")).toBeDisabled();
    fireEvent.click(screen.getByTestId("candidate-count-save"));
    expect(api.post).not.toHaveBeenCalled();
  });
});

describe("invalid-scope prevention", () => {
  test("applied count type disables the scope selector (cannot be phase)", async () => {
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("candidate-count-add"));
    expect(screen.getByTestId("candidate-count-scope")).toBeDisabled();
    expect(screen.queryByTestId("candidate-count-phase")).toBeNull();
  });

  test("appeared phase scope without a phase blocks save (no POST)", async () => {
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("candidate-count-add"));
    fireEvent.change(screen.getByTestId("candidate-count-type"), { target: { value: "appeared" } });
    fireEvent.change(screen.getByTestId("candidate-count-scope"), { target: { value: "phase" } });
    fireEvent.change(screen.getByTestId("candidate-count-value"), { target: { value: "500000" } });
    expect(screen.getByTestId("candidate-count-form-error")).toBeInTheDocument();
    expect(screen.getByTestId("candidate-count-save")).toBeDisabled();
    fireEvent.click(screen.getByTestId("candidate-count-save"));
    expect(api.post).not.toHaveBeenCalled();
  });
});

describe("review lifecycle + transition matrix (migration 219)", () => {
  test("Submit for review PATCHes draft → pending_review", async () => {
    mockGet({
      items: [{
        id: "cc1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
        reservation_category_id: null, count_value: 1200000, source_basis: "official",
        reviewer_status: "draft", is_current_published: false,
      }],
    });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByTestId("candidate-count-action-cc1-pending_review"));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const [url, body] = lastPatch();
    expect(url).toBe("/api/admin/exam-intelligence/candidate-counts/cc1/review");
    expect(body.reviewer_status).toBe("pending_review");
  });

  test("a reviewed row exposes ONLY Lock — reviewed → rejected is NOT offered", async () => {
    mockGet({
      items: [{
        id: "cc3", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
        reservation_category_id: null, count_value: 1200000, source_basis: "official",
        reviewer_status: "reviewed", is_current_published: true,
      }],
    });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(await screen.findByTestId("candidate-count-action-cc3-locked")).toBeInTheDocument();
    // Forbidden by the 219 RPC matrix — must not be rendered.
    expect(screen.queryByTestId("candidate-count-action-cc3-rejected")).toBeNull();
  });

  test("Reopen a locked row requires notes and sends reviewer_notes", async () => {
    mockGet({
      items: [{
        id: "cc2", exam_cycle_id: "cyc-1", count_type: "appeared", scope_kind: "cycle",
        reservation_category_id: null, count_value: 500000, source_basis: "official",
        reviewer_status: "locked", is_current_published: true,
      }],
    });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByTestId("candidate-count-action-cc2-reviewed"));
    expect(api.patch).not.toHaveBeenCalled();

    const notesInputs = screen.getAllByPlaceholderText("notes (required)");
    fireEvent.change(notesInputs[0], { target: { value: "count was mistyped" } });
    fireEvent.click(screen.getByTestId("candidate-count-action-cc2-reviewed"));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const [, body] = lastPatch();
    expect(body.reviewer_status).toBe("reviewed");
    expect(body.reviewer_notes).toBe("count was mistyped");
  });
});

describe("evidence promotion gate (P0-2)", () => {
  const pendingRow = {
    id: "cc1", exam_cycle_id: "cyc-1", count_type: "appeared", scope_kind: "phase",
    exam_phase_id: "phase-1", reservation_category_id: null, count_value: 500000,
    source_basis: "official", reviewer_status: "pending_review", is_current_published: false,
  };

  test("Mark reviewed is disabled with a blocker when no evidence exists", async () => {
    mockGet({ items: [pendingRow], evidence: [] });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    const btn = await screen.findByTestId("candidate-count-action-cc1-reviewed");
    expect(btn).toBeDisabled();
    expect(screen.getByTestId("candidate-count-evidence-blocker-cc1")).toBeInTheDocument();
  });

  test("Mark reviewed enabled once qualifying evidence exists → PATCHes", async () => {
    mockGet({
      items: [pendingRow],
      evidence: [{ id: "ev1", evidence_kind: "official_result", evidence_role: "primary", claim_value: {} }],
    });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    const btn = await screen.findByTestId("candidate-count-action-cc1-reviewed");
    await waitFor(() => expect(btn).not.toBeDisabled());
    fireEvent.click(btn);
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const [url, body] = lastPatch();
    expect(url).toBe("/api/admin/exam-intelligence/candidate-counts/cc1/review");
    expect(body.reviewer_status).toBe("reviewed");
  });

  test("attach evidence posts the claim snapshot auto-filled from the parent row", async () => {
    mockGet({ items: [pendingRow], evidence: [] });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(await screen.findByTestId("candidate-count-evidence-toggle-cc1"));
    fireEvent.change(await screen.findByTestId("candidate-count-evidence-url-cc1"), {
      target: { value: "https://official.example/result.pdf" },
    });
    fireEvent.click(screen.getByTestId("candidate-count-evidence-attach-cc1"));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [url, body] = lastPost();
    expect(url).toBe("/api/admin/exam-intelligence/candidate-counts/cc1/evidence");
    expect(body.claim_value).toEqual({
      count_type: "appeared", scope_kind: "phase", exam_phase_id: "phase-1",
      reservation_category_code: null, count_value: 500000,
    });
    expect(body.evidence_url).toBe("https://official.example/result.pdf");
  });
});

describe("edit / PATCH (P0-3)", () => {
  test("draft row edit PATCHes count_value + source_basis to the CMS route", async () => {
    mockGet({
      items: [{
        id: "cc1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
        reservation_category_id: null, count_value: 1000, source_basis: "official",
        reviewer_status: "draft", is_current_published: false,
      }],
    });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(await screen.findByTestId("candidate-count-edit-cc1"));
    fireEvent.change(screen.getByTestId("candidate-count-edit-value-cc1"), { target: { value: "1050" } });
    fireEvent.change(screen.getByTestId("candidate-count-edit-basis-cc1"), { target: { value: "reviewed_analysis" } });
    fireEvent.click(screen.getByTestId("candidate-count-edit-save-cc1"));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const [url, body] = lastPatch();
    expect(url).toBe("/api/admin/exam-intelligence-cms/exam-candidate-counts/cc1");
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    expect(body.payload.count_value).toBe(1050);
    expect(body.payload.source_basis).toBe("reviewed_analysis");
    expect(body.payload).not.toHaveProperty("scope_kind");
  });
});

describe("permission gating (manage / review / cms)", () => {
  test("manage sees create and edit", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.manage"] } });
    mockGet({
      items: [{
        id: "cc1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
        reservation_category_id: null, count_value: 1000, source_basis: "official",
        reviewer_status: "draft", is_current_published: false,
      }],
    });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.getByTestId("candidate-count-add")).toBeInTheDocument();
    expect(await screen.findByTestId("candidate-count-edit-cc1")).toBeInTheDocument();
    // manage is not a reviewer → no lifecycle action.
    expect(screen.queryByTestId("candidate-count-action-cc1-pending_review")).toBeNull();
  });

  test("cms permission alone does NOT surface the normal create button", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.cms"] } });
    mockGet({ items: [] });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByTestId("candidate-count-add")).toBeNull();
  });

  test("review-only shows lifecycle actions but not create/edit", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    mockGet({
      items: [{
        id: "cc1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
        reservation_category_id: null, count_value: 1000, source_basis: "official",
        reviewer_status: "draft", is_current_published: false,
      }],
    });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByTestId("candidate-count-add")).toBeNull();
    expect(screen.queryByTestId("candidate-count-edit-cc1")).toBeNull();
    expect(await screen.findByTestId("candidate-count-action-cc1-pending_review")).toBeInTheDocument();
  });

  test("no manage/review permission hides create and lifecycle actions", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: [] } });
    mockGet({
      items: [{
        id: "cc1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
        reservation_category_id: null, count_value: 1000, source_basis: "official",
        reviewer_status: "draft", is_current_published: false,
      }],
    });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByTestId("candidate-count-add")).toBeNull();
    expect(screen.queryByTestId("candidate-count-action-cc1-pending_review")).toBeNull();
  });
});

describe("cycle scoping + no denominator heuristic + a11y", () => {
  test("no selected cycle → no read, create hidden, never submits null cycle", async () => {
    useExamWorkspace.mockReturnValue({ ...WORKSPACE, cycle: null });
    renderCC();
    await waitFor(() => expect(screen.getByTestId("candidate-count-no-cycle")).toBeInTheDocument());
    expect(api.get).not.toHaveBeenCalled();
    expect(screen.queryByTestId("candidate-count-add")).toBeNull();
  });

  test("list read is scoped by exam_cycle_id server-side", async () => {
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    const listCall = api.get.mock.calls.find((c) => !String(c[0]).includes("/evidence"));
    expect(listCall[0]).toMatch(/exam_cycle_id=cyc-1/);
    expect(listCall[0]).toMatch(/exam_id=exam-1/);
  });

  test("no client-side ratio-denominator heuristic is rendered", async () => {
    mockGet({
      items: [
        { id: "a1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle", reservation_category_id: null, count_value: 1200000, source_basis: "official", reviewer_status: "locked", is_current_published: true },
        { id: "p1", exam_cycle_id: "cyc-1", count_type: "appeared", scope_kind: "cycle", reservation_category_id: null, count_value: 800000, source_basis: "official", reviewer_status: "reviewed", is_current_published: true },
      ],
    });
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByTestId("candidate-count-denominator")).toBeNull();
    expect(screen.queryByText(/denominator in use/i)).toBeNull();
  });

  test("create form controls have associated labels (a11y)", async () => {
    renderCC();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("candidate-count-add"));
    expect(screen.getByLabelText("Count type")).toBeInTheDocument();
    expect(screen.getByLabelText("Scope")).toBeInTheDocument();
    expect(screen.getByLabelText("Count value (official total)")).toBeInTheDocument();
    expect(screen.getByLabelText("Source basis")).toBeInTheDocument();
  });
});
