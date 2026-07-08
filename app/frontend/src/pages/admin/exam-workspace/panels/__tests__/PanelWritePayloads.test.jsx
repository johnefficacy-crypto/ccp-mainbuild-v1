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

// CompetitionPanel now renders CandidateCountsSection, which reads useAuth and
// lists /candidate-counts. Mock auth (super_admin) so the section mounts; the
// candidate list is routed to an empty response below so its rows never
// collide with the competition-metric lifecycle assertions.
jest.mock("../../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { role: "super_admin", permissions: [] } }),
}));

// SetupPanel now imports useApiAction (for cycle create/edit). Mock it so
// tests never need a ToastProvider context — mirrors Organizations.create.test.jsx.
jest.mock("../../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({
    run: jest.fn(async ({ action, onSuccess }) => {
      const result = await action();
      if (onSuccess) onSuccess(result);
      return { ok: true, data: result };
    }),
    busy: false,
  }),
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

// Competition-metrics list response for the current test. Routed by URL so the
// sibling CandidateCountsSection (which lists /candidate-counts) always gets an
// empty list and never renders lifecycle buttons that would shadow the
// competition-metric ones under getByRole.
let compResponse = { items: [] };
function setCompetition(resp) {
  compResponse = resp;
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.patch.mockReset();
  compResponse = { items: [] };
  api.get.mockImplementation((url) =>
    Promise.resolve(String(url).includes("/candidate-counts") ? { items: [] } : compResponse),
  );
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

  test("sends reason≥8, phase_slug, status enum; phase_start/phase_end top-level", async () => {
    render(<SetupPanel />);
    fireEvent.click(screen.getByText("+ Add phase"));
    fireEvent.change(screen.getByPlaceholderText("Phase name"), {
      target: { value: "Prelims" },
    });
    // DateField wraps a native <input type="date">; its IDL value is ISO
    // (YYYY-MM-DD), so fire that (a dd-mm-yyyy string sanitizes to "").
    fireEvent.change(screen.getByLabelText(/phase start/i), {
      target: { value: "2026-05-24" },
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
    // W3: structured dates sent top-level; no freeform phase_window
    expect(body.payload).not.toHaveProperty("phase_window");
    expect(body.payload.phase_start).toBe("2026-05-24");
    expect(body.payload.phase_end).toBeNull();
    expect(body.payload.metadata).toEqual({});
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

  test("hits /exam-competition-metrics with vacancy_total, reason≥8, and NEVER writes applicant_count", async () => {
    render(<CompetitionPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByRole("button", { name: "Add competition metric" }));
    fireEvent.change(screen.getByPlaceholderText("e.g. 1056"), {
      target: { value: "1056" },
    });
    // J3 PR2 (checkpost P0-1): the "Applicants" input is removed — the
    // ambiguous legacy applicant_count is deprecated in place and NO new
    // values may be written (resolutions §1.2 / OD-6).
    expect(screen.queryByPlaceholderText("e.g. 1,100,000")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Save as draft" }));

    await waitFor(() => expect(api.post).toHaveBeenCalled());

    // W2: correct endpoint
    expect(lastPostUrl()).toBe("/api/admin/exam-intelligence-cms/exam-competition-metrics");
    const body = lastPostBody();
    expect(body.reason.length).toBeGreaterThanOrEqual(8);
    // W2: correct column names
    expect(body.payload.vacancy_total).toBe(1056);
    // applicant_count is NEVER written by the panel now.
    expect(body.payload.applicant_count).toBeUndefined();
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

  // The competition review endpoint uses the coverage lifecycle
  // (draft|pending_review|reviewed|locked|rejected); "verified" 422s. The
  // promote action must send a valid status — only "locked" feeds the planner.
  test("Lock action PATCHes a valid coverage status (locked), never 'verified'", async () => {
    // J3 PR1: publication (aspirant visibility) happens at pending_review ->
    // reviewed (migration 216); reviewed -> locked is a status bump on the
    // already-published row, so a "reviewed" row is what exercises "Lock".
    setCompetition({
      items: [{ id: "metric-1", exam_cycle_id: "cyc-1", vacancy_total: 1056, applicant_count: 1100000, reviewer_status: "reviewed" }],
      count: 1,
    });
    api.patch.mockResolvedValue({ ok: true });

    render(<CompetitionPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByRole("button", { name: "Lock" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());

    const [url, body] = api.patch.mock.calls[api.patch.mock.calls.length - 1];
    expect(url).toBe("/api/admin/exam-intelligence/competition-metrics/metric-1/review");
    expect(body.reviewer_status).toBe("locked");
    expect(["draft", "pending_review", "reviewed", "locked", "rejected"]).toContain(body.reviewer_status);
    expect(body.reviewer_status).not.toBe("verified");
  });

  test("Mark reviewed action PATCHes pending_review -> reviewed (publication step)", async () => {
    setCompetition({
      items: [{ id: "metric-2", exam_cycle_id: "cyc-1", vacancy_total: 1056, reviewer_status: "pending_review" }],
      count: 1,
    });
    api.patch.mockResolvedValue({ ok: true });

    render(<CompetitionPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByRole("button", { name: "Mark reviewed" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());

    const [, body] = api.patch.mock.calls[api.patch.mock.calls.length - 1];
    expect(body.reviewer_status).toBe("reviewed");
  });

  test("Reopen action requires notes and sends reviewer_notes", async () => {
    setCompetition({
      items: [{ id: "metric-3", exam_cycle_id: "cyc-1", vacancy_total: 1056, reviewer_status: "locked" }],
      count: 1,
    });
    api.patch.mockResolvedValue({ ok: true });

    render(<CompetitionPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    // No notes yet: clicking Reopen must not PATCH.
    fireEvent.click(await screen.findByRole("button", { name: "Reopen" }));
    expect(api.patch).not.toHaveBeenCalled();

    fireEvent.change(screen.getByPlaceholderText("reopen notes (required)"), {
      target: { value: "cutoff was mistyped" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reopen" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());

    const [, body] = api.patch.mock.calls[api.patch.mock.calls.length - 1];
    expect(body.reviewer_status).toBe("reviewed");
    expect(body.reviewer_notes).toBe("cutoff was mistyped");
  });

  // J3 PR1: metric_kind is derived from exam_phase_id (OD-11) — selecting a
  // phase switches the form to the cutoff_by_category editor and the payload
  // must carry exam_phase_id + cutoff_by_category, never vacancy fields.
  test("J3: selecting a phase sends exam_phase_id + cutoff_by_category, no vacancy fields", async () => {
    useExamWorkspace.mockReturnValue({
      exam: { id: "exam-1" },
      cycle: { id: "cyc-1", cycle_name: "2026" },
      phases: [{ id: "phase-1", phase_name: "Prelims" }],
    });
    render(<CompetitionPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByRole("button", { name: "Add competition metric" }));
    fireEvent.change(screen.getByTestId("competition-phase-select"), { target: { value: "phase-1" } });
    fireEvent.change(screen.getByTestId("cutoff-marks-general"), { target: { value: "75.41" } });
    fireEvent.click(screen.getByRole("button", { name: "Save as draft" }));

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = lastPostBody();
    expect(body.payload.exam_phase_id).toBe("phase-1");
    expect(body.payload.cutoff_by_category).toEqual({ general: { marks: 75.41 } });
    expect(body.payload.vacancy_total).toBeUndefined();
    expect(body.payload.vacancy_by_category).toBeUndefined();
    expect(body.payload.applicant_count).toBeUndefined();
  });

  test("J3: cycle-level (no phase) sends vacancy_by_category, no cutoff fields", async () => {
    render(<CompetitionPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(await screen.findByRole("button", { name: "Add competition metric" }));
    fireEvent.change(screen.getByTestId("vacancy-general"), { target: { value: "442" } });
    fireEvent.click(screen.getByRole("button", { name: "Save as draft" }));

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = lastPostBody();
    expect(body.payload.exam_phase_id).toBeUndefined();
    expect(body.payload.vacancy_by_category).toEqual({ general: 442 });
    expect(body.payload.cutoff_by_category).toBeUndefined();
    expect(body.payload.difficulty_assessment).toBeUndefined();
  });
});
