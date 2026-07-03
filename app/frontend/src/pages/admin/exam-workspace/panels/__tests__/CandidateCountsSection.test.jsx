/**
 * Tests for CandidateCountsSection (J3 PR 3 — applied-vs-appeared editor UI).
 *
 * Covers:
 * - valid create payload per scope/count_type (applied→cycle, appeared→phase)
 * - invalid-scope prevention (applied cannot be phase-scoped; appeared phase
 *   scope requires a phase) — client mirror of _validate_candidate_count_scope
 * - review action fires PATCH /candidate-counts/{id}/review with a valid status
 * - canManage / canReview gating hides/shows create + lifecycle actions
 * - derived-ratio denominator label from the current published official total
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

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

function lastPost() {
  const calls = api.post.mock.calls;
  return calls[calls.length - 1];
}
function lastPatch() {
  const calls = api.patch.mock.calls;
  return calls[calls.length - 1];
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.patch.mockReset();
  api.get.mockResolvedValue({ items: [] });
  api.post.mockResolvedValue({ ok: true });
  api.patch.mockResolvedValue({ ok: true });
  useExamWorkspace.mockReturnValue(WORKSPACE);
  useAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] } });
});

describe("create payloads", () => {
  test("applied → cycle-scoped official-total payload, reason≥8, no phase", async () => {
    render(<CandidateCountsSection />);
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
    // Trust: never client-requests a published status.
    expect(JSON.stringify(body)).not.toMatch(/reviewer_status|reviewed|locked/);
  });

  test("appeared → phase-scoped payload carries exam_phase_id", async () => {
    render(<CandidateCountsSection />);
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
});

describe("invalid-scope prevention", () => {
  test("applied count type disables the scope selector (cannot be phase)", async () => {
    render(<CandidateCountsSection />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("candidate-count-add"));
    // Applied is selected by default → scope is forced to cycle and disabled.
    expect(screen.getByTestId("candidate-count-scope")).toBeDisabled();
    // No phase option is offered for applied.
    expect(screen.queryByTestId("candidate-count-phase")).toBeNull();
  });

  test("appeared phase scope without a phase blocks save (no POST)", async () => {
    render(<CandidateCountsSection />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("candidate-count-add"));
    fireEvent.change(screen.getByTestId("candidate-count-type"), { target: { value: "appeared" } });
    fireEvent.change(screen.getByTestId("candidate-count-scope"), { target: { value: "phase" } });
    fireEvent.change(screen.getByTestId("candidate-count-value"), { target: { value: "500000" } });
    // Phase left unselected → form error + disabled save + no POST.
    expect(screen.getByTestId("candidate-count-form-error")).toBeInTheDocument();
    expect(screen.getByTestId("candidate-count-save")).toBeDisabled();
    fireEvent.click(screen.getByTestId("candidate-count-save"));
    expect(api.post).not.toHaveBeenCalled();
  });
});

describe("review lifecycle", () => {
  test("Submit for review PATCHes draft → pending_review", async () => {
    api.get.mockResolvedValue({
      items: [{
        id: "cc1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
        reservation_category_id: null, count_value: 1200000, source_basis: "official",
        reviewer_status: "draft", is_current_published: false,
      }],
    });
    render(<CandidateCountsSection />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByTestId("candidate-count-action-cc1-pending_review"));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const [url, body] = lastPatch();
    expect(url).toBe("/api/admin/exam-intelligence/candidate-counts/cc1/review");
    expect(body.reviewer_status).toBe("pending_review");
    expect(["draft", "pending_review", "reviewed", "locked", "rejected"]).toContain(body.reviewer_status);
  });

  test("Reopen a locked row requires notes and sends reviewer_notes", async () => {
    api.get.mockResolvedValue({
      items: [{
        id: "cc2", exam_cycle_id: "cyc-1", count_type: "appeared", scope_kind: "cycle",
        reservation_category_id: null, count_value: 500000, source_basis: "official",
        reviewer_status: "locked", is_current_published: true,
      }],
    });
    render(<CandidateCountsSection />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    // No notes yet → clicking Reopen must not PATCH.
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

describe("permission gating", () => {
  test("no manage/review permission hides create and lifecycle actions", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: [] } });
    api.get.mockResolvedValue({
      items: [{
        id: "cc1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
        reservation_category_id: null, count_value: 1200000, source_basis: "official",
        reviewer_status: "draft", is_current_published: false,
      }],
    });
    render(<CandidateCountsSection />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByTestId("candidate-count-add")).toBeNull();
    // Draft lifecycle action hidden without review permission.
    expect(screen.queryByTestId("candidate-count-action-cc1-pending_review")).toBeNull();
  });

  test("review-only permission shows lifecycle actions but not the create button", async () => {
    useAuth.mockReturnValue({ user: { role: "admin", permissions: ["exam_intelligence.review"] } });
    api.get.mockResolvedValue({
      items: [{
        id: "cc1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
        reservation_category_id: null, count_value: 1200000, source_basis: "official",
        reviewer_status: "draft", is_current_published: false,
      }],
    });
    render(<CandidateCountsSection />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByTestId("candidate-count-add")).toBeNull();
    expect(await screen.findByTestId("candidate-count-action-cc1-pending_review")).toBeInTheDocument();
  });
});

describe("derived denominator label", () => {
  test("shows the current published official total and its count_type basis", async () => {
    api.get.mockResolvedValue({
      items: [
        {
          id: "applied1", exam_cycle_id: "cyc-1", count_type: "applied", scope_kind: "cycle",
          reservation_category_id: null, count_value: 1200000, source_basis: "official",
          reviewer_status: "locked", is_current_published: true,
        },
        {
          id: "appeared1", exam_cycle_id: "cyc-1", count_type: "appeared", scope_kind: "cycle",
          reservation_category_id: null, count_value: 800000, source_basis: "official",
          reviewer_status: "reviewed", is_current_published: true,
        },
      ],
    });
    render(<CandidateCountsSection />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    const note = await screen.findByTestId("candidate-count-denominator");
    // appeared preferred over applied (candidate_counts.py preference order).
    expect(note).toHaveTextContent("800,000");
    expect(note).toHaveTextContent("appeared");
  });
});
