/**
 * Tests for CycleActivationChecklist component (I9).
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

const { api } = require("../../../../lib/api");
const CycleActivationChecklist = require("../CycleActivationChecklist").default;

const NINE_STEPS = [
  { step_id: "cycle_details", label: "Cycle details", status: "ready", gate_class: "hard", evidence_scope: "selected_cycle", action_cta: null, note: null },
  { step_id: "phases_schedule", label: "Phases and schedule", status: "ready", gate_class: "hard", evidence_scope: "selected_cycle", action_cta: null, note: null },
  { step_id: "source_documents", label: "Source documents", status: "missing", gate_class: "advisory", evidence_scope: "exam_wide", action_cta: { label: "Open Documents", url: "/admin/exam-intelligence/exams/exam-1?tab=documents" }, note: "No source documents uploaded yet." },
  { step_id: "extraction", label: "Extraction", status: "missing", gate_class: "advisory", evidence_scope: "exam_wide", action_cta: { label: "Open Documents", url: "/admin/exam-intelligence/exams/exam-1?tab=documents" }, note: null },
  { step_id: "syllabus_mapping", label: "Syllabus mapping", status: "ready", gate_class: "hard", evidence_scope: "exam_wide", action_cta: null, note: null },
  { step_id: "pyq_readiness", label: "PYQ readiness", status: "ready", gate_class: "advisory", evidence_scope: "exam_wide", action_cta: null, note: null },
  { step_id: "policy_updates", label: "Policy updates", status: "ready", gate_class: "advisory", evidence_scope: "mixed", action_cta: null, note: null },
  { step_id: "competition_context", label: "Competition context", status: "not_applicable", gate_class: "advisory", evidence_scope: "exam_wide", action_cta: null, note: null, not_applicable_reason: "management_mode_light" },
  { step_id: "review_activate", label: "Review and activate", status: "review_pending", gate_class: "hard", evidence_scope: "selected_cycle", action_cta: { label: "Review & Activate", url: "/admin/exam-intelligence/exams/exam-1?cycle=cy-1&tab=review" }, note: null },
];

function successResponse(steps = NINE_STEPS) {
  return Promise.resolve({
    data: {
      contract_version: 1,
      exam_id: "exam-1",
      cycle_id: "cy-1",
      computed_at: "2026-06-29T00:00:00+00:00",
      cycle_readiness: {
        cycle_id: "cy-1",
        computed_at: "2026-06-29T00:00:00+00:00",
        steps,
      },
    },
  });
}

beforeEach(() => {
  jest.clearAllMocks();
});

// ── 1. Shows loading state initially ────────────────────────────────────────

test("shows loading state initially", () => {
  api.get.mockReturnValue(new Promise(() => {})); // never resolves
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  expect(screen.getByTestId("checklist-loading")).toBeInTheDocument();
});

// ── 2. Shows steps after successful fetch (9 steps) ─────────────────────────

test("shows 9 steps after successful fetch", async () => {
  api.get.mockReturnValue(successResponse());
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  await waitFor(() => {
    expect(screen.getByTestId("cycle-activation-checklist")).toBeInTheDocument();
  });
  const steps = screen.getAllByRole("listitem");
  expect(steps).toHaveLength(9);
});

// ── 3. Shows cycle_not_found error ──────────────────────────────────────────

test("shows cycle_not_found error when backend returns cycle_readiness_error", async () => {
  api.get.mockResolvedValue({
    data: {
      contract_version: 1,
      exam_id: "exam-1",
      cycle_id: "bad-id",
      computed_at: "2026-06-29T00:00:00+00:00",
      cycle_readiness: null,
      cycle_readiness_error: "cycle_not_found",
    },
  });
  render(<CycleActivationChecklist examId="exam-1" cycleId="bad-id" />);
  await waitFor(() => {
    expect(screen.getByTestId("checklist-error-cycle-not-found")).toBeInTheDocument();
  });
});

// ── 4. Shows unavailable error on 5xx ───────────────────────────────────────

test("shows unavailable error on 5xx response", async () => {
  api.get.mockRejectedValue({ response: { status: 503 } });
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  await waitFor(() => {
    expect(screen.getByTestId("checklist-error-unavailable")).toBeInTheDocument();
  });
});

// ── 5. Renders correct icons for status values ───────────────────────────────

test("renders correct icon for ready status", async () => {
  api.get.mockReturnValue(successResponse());
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  await waitFor(() => screen.getByTestId("cycle-activation-checklist"));

  const readyStep = screen.getByTestId("checklist-step-cycle_details");
  expect(readyStep).toHaveAttribute("data-status", "ready");
  expect(readyStep.querySelector(".checklist-step__icon").textContent).toBe("✓");
});

test("renders correct icon for missing status", async () => {
  api.get.mockReturnValue(successResponse());
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  await waitFor(() => screen.getByTestId("cycle-activation-checklist"));

  const missingStep = screen.getByTestId("checklist-step-source_documents");
  expect(missingStep).toHaveAttribute("data-status", "missing");
  expect(missingStep.querySelector(".checklist-step__icon").textContent).toBe("○");
});

test("renders correct icon for not_applicable status", async () => {
  api.get.mockReturnValue(successResponse());
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  await waitFor(() => screen.getByTestId("cycle-activation-checklist"));

  const naStep = screen.getByTestId("checklist-step-competition_context");
  expect(naStep).toHaveAttribute("data-status", "not_applicable");
  expect(naStep.querySelector(".checklist-step__icon").textContent).toBe("—");
});

// ── 6. Only renders CTAs for non-ready/non-applicable steps ─────────────────

test("does not render CTA for ready steps", async () => {
  api.get.mockReturnValue(successResponse());
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  await waitFor(() => screen.getByTestId("cycle-activation-checklist"));

  // cycle_details is ready — no CTA
  expect(screen.queryByTestId("checklist-cta-cycle_details")).not.toBeInTheDocument();
});

test("does not render CTA for not_applicable steps", async () => {
  api.get.mockReturnValue(successResponse());
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  await waitFor(() => screen.getByTestId("cycle-activation-checklist"));

  // competition_context is not_applicable — no CTA
  expect(screen.queryByTestId("checklist-cta-competition_context")).not.toBeInTheDocument();
});

test("renders CTA for review_pending steps", async () => {
  api.get.mockReturnValue(successResponse());
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  await waitFor(() => screen.getByTestId("cycle-activation-checklist"));

  // review_activate is review_pending — has CTA
  expect(screen.getByTestId("checklist-cta-review_activate")).toBeInTheDocument();
});

test("shows progress count", async () => {
  api.get.mockReturnValue(successResponse());
  render(<CycleActivationChecklist examId="exam-1" cycleId="cy-1" />);
  await waitFor(() => screen.getByTestId("checklist-progress"));
  // ready steps: cycle_details, phases_schedule, syllabus_mapping, pyq_readiness, policy_updates = 5
  // not_applicable: competition_context (1)
  // total active = 9 - 1 = 8
  expect(screen.getByTestId("checklist-progress").textContent).toMatch(/5\s*\/\s*8/);
});

test("renders nothing when examId or cycleId is missing", () => {
  render(<CycleActivationChecklist examId={null} cycleId="cy-1" />);
  expect(document.body.textContent).toBe("");
});
