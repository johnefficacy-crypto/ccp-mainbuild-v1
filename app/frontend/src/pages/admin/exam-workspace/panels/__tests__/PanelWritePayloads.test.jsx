/**
 * Write-payload contract tests for the Exam Intelligence workspace panels.
 *
 * Covers PR fixes W1–W4 against the CMS WriteEnvelope contract
 * (admin_exam_intel_cms.py):
 * - W1: every create sends a required reason (≥8 chars).
 * - W3 SetupPanel phase create: sends phase_slug + status (valid enum),
 *   no phase_window/state at the top level (WriteEnvelope, _PHASE_FIELDS).
 * - W4 UpdatesPanel policy create: sends update_type, no reviewer_status
 *   (_POLICY_FIELDS / _POLICY_UPDATE_TYPES).
 * - W2 CompetitionPanel metric create: hits /exam-competition-metrics with
 *   vacancy_total / applicant_count, valid ranges, no reviewer_status
 *   (_COMPETITION_FIELDS).
 * - Trust: no create payload requests verified/locked.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
}));

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: jest.fn(),
}));

const { api } = require("../../../../../lib/api");
const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const SetupPanel = require("../SetupPanel").default;
const UpdatesPanel = require("../UpdatesPanel").default;
const CompetitionPanel = require("../CompetitionPanel").default;

const VALID_PHASE_STATUSES = ["expected", "active", "completed", "cancelled"];
const VALID_UPDATE_TYPES = [
  "notification_change", "cycle_change", "date_change", "syllabus_change",
  "pattern_change", "vacancy_change", "eligibility_change",
  "reservation_change", "document_rule_change", "other",
];

function lastPostBody() {
  const calls = api.post.mock.calls;
  return calls[calls.length - 1][1];
}

function lastPostUrl() {
  const calls = api.post.mock.calls;
  return calls[calls.length - 1][0];
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.patch.mockReset();
  api.get.mockResolvedValue({ items: [] });
  api.post.mockResolvedValue({ ok: true });
});

// ── W3 + W1: SetupPanel phase create ────────────────────────────────────────

describe("SetupPanel.addPhase", () => {
  beforeEach(() => {
    useExamWorkspace.mockReturnValue({
      exam: { id: "exam-1", name: "UPSC CSE", slug: "upsc-cse" },
      cycles: [{ id: "cyc-1", status: "active", cycle_name: "2026" }],
      phases: [],
    });
  });

  test("sends reason≥8, phase_slug, status enum; no phase_window/state top-level", async () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByText("+ Add phase"));
    fireEvent.change(screen.getByPlaceholderText("Phase name"), {
      target: { value: "Prelims" },
    });
    fireEvent.change(screen.getByPlaceholderText("Window (e.g. 24 May 2026)"), {
      target: { value: "24 May 2026" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add phase" }));

    await waitFor(() => expect(api.post).toHaveBeenCalled());

    expect(lastPostUrl()).toBe("/api/admin/exam-intelligence-cms/exam-phases");
    const body = lastPostBody();
    // W1: reason required, ≥8 chars
    expect(typeof body.reason).toBe("string");
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    // W3: phase_slug sent, derived from name
    expect(body.payload.phase_slug).toBe("prelims");
    expect(body.payload.phase_name).toBe("Prelims");
    // W3: status enum, not state
    expect(VALID_PHASE_STATUSES).toContain(body.payload.status);
    expect(body.payload).not.toHaveProperty("state");
    // W3: phase_window not top-level — lives in metadata jsonb
    expect(body.payload).not.toHaveProperty("phase_window");
    expect(body.payload.metadata).toEqual({ phase_window: "24 May 2026" });
  });

  test("trust: phase create never requests verified/locked", async () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByText("+ Add phase"));
    fireEvent.change(screen.getByPlaceholderText("Phase name"), {
      target: { value: "Mains" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add phase" }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());

    const body = lastPostBody();
    expect(body.payload).not.toHaveProperty("reviewer_status");
    expect(JSON.stringify(body)).not.toMatch(/verified|locked/);
  });
});

// ── W4 + W1: UpdatesPanel policy create ─────────────────────────────────────

describe("UpdatesPanel.addUpdate", () => {
  beforeEach(() => {
    useExamWorkspace.mockReturnValue({ exam: { id: "exam-1" } });
  });

  test("sends reason≥8 + update_type (valid), drops reviewer_status", async () => {
    render(<UpdatesPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByRole("button", { name: "+ Add update" }));
    fireEvent.change(screen.getByPlaceholderText("Update title"), {
      target: { value: "New notification released" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add as draft" }));

    await waitFor(() => expect(api.post).toHaveBeenCalled());

    expect(lastPostUrl()).toBe("/api/admin/exam-intelligence-cms/policy-updates");
    const body = lastPostBody();
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    expect(VALID_UPDATE_TYPES).toContain(body.payload.update_type);
    expect(body.payload.title).toBe("New notification released");
    // W4: reviewer_status is not an allowed input
    expect(body.payload).not.toHaveProperty("reviewer_status");
  });

  test("trust: update create never requests verified/locked", async () => {
    render(<UpdatesPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(await screen.findByRole("button", { name: "+ Add update" }));
    fireEvent.change(screen.getByPlaceholderText("Update title"), {
      target: { value: "Cutoff revised upward" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add as draft" }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());

    expect(JSON.stringify(lastPostBody())).not.toMatch(/verified|locked/);
  });
});

// ── W2 + W1: CompetitionPanel metric create ─────────────────────────────────

describe("CompetitionPanel.saveMetric", () => {
  beforeEach(() => {
    useExamWorkspace.mockReturnValue({
      exam: { id: "exam-1" },
      cycle: { id: "cyc-1", cycle_name: "2026" },
    });
  });

  test("hits /exam-competition-metrics with vacancy_total/applicant_count, reason≥8, valid ranges", async () => {
    render(<CompetitionPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByRole("button", { name: "Add competition metric" }));
    fireEvent.change(screen.getByPlaceholderText("e.g. 1056"), {
      target: { value: "1056" },
    });
    fireEvent.change(screen.getByPlaceholderText("e.g. 1,100,000"), {
      target: { value: "1,100,000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save as draft" }));

    await waitFor(() => expect(api.post).toHaveBeenCalled());

    // W2: correct endpoint
    expect(lastPostUrl()).toBe("/api/admin/exam-intelligence-cms/exam-competition-metrics");
    const body = lastPostBody();
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    // W2: correct column names
    expect(body.payload.vacancy_total).toBe(1056);
    expect(body.payload.applicant_count).toBe(1100000);
    expect(body.payload).not.toHaveProperty("vacancies");
    expect(body.payload).not.toHaveProperty("total_applicants");
    // W2: reviewer_status dropped (server forces 'draft')
    expect(body.payload).not.toHaveProperty("reviewer_status");
    // Range validity for any numeric field that IS sent
    if (body.payload.selection_ratio !== undefined) {
      expect(body.payload.selection_ratio).toBeGreaterThanOrEqual(0);
      expect(body.payload.selection_ratio).toBeLessThanOrEqual(1);
    }
    if (body.payload.confidence_score !== undefined) {
      expect(body.payload.confidence_score).toBeGreaterThanOrEqual(0);
      expect(body.payload.confidence_score).toBeLessThanOrEqual(1);
    }
    if (body.payload.competition_pressure_score !== undefined) {
      expect(body.payload.competition_pressure_score).toBeGreaterThanOrEqual(0);
      expect(body.payload.competition_pressure_score).toBeLessThanOrEqual(100);
    }
  });

  test("trust: metric create never requests verified/locked, not old topic-coverage endpoint", async () => {
    render(<CompetitionPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(await screen.findByRole("button", { name: "Add competition metric" }));
    fireEvent.change(screen.getByPlaceholderText("e.g. 1056"), {
      target: { value: "500" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save as draft" }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());

    expect(lastPostUrl()).not.toMatch(/exam-topic-coverage/);
    expect(JSON.stringify(lastPostBody())).not.toMatch(/verified|locked/);
  });
});
