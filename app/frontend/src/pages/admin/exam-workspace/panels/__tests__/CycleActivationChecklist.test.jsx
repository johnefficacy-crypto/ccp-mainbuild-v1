/**
 * CycleActivationChecklist — unit tests
 *
 * Tests: loading state, error state, cycle_not_found error, steps render, CTA links.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

const { api } = require("../../../../../lib/api");
const CycleActivationChecklist = require("../CycleActivationChecklist").default;

const MOCK_READINESS = {
  cycle_id: "cy1",
  computed_at: "2026-06-29T00:00:00+00:00",
  overall: "ready",
  steps: [
    {
      step: 1,
      key: "cycle_details",
      label: "Cycle details",
      status: "ready",
      gate_class: "hard",
      evidence_scope: "selected_cycle",
      not_applicable_reason: null,
      action_cta: null,
      note: null,
    },
    {
      step: 2,
      key: "phases_schedule",
      label: "Phases schedule",
      status: "missing",
      gate_class: "hard",
      evidence_scope: "selected_cycle",
      not_applicable_reason: null,
      action_cta: { label: "Add phase", url: "/admin/exam-intelligence/exams/e1?tab=setup" },
      note: null,
    },
  ],
};

beforeEach(() => {
  api.get.mockReset();
});

test("shows loading state initially", () => {
  api.get.mockReturnValue(new Promise(() => {})); // never resolves
  render(<CycleActivationChecklist examId="e1" cycleId="cy1" />);
  expect(screen.getByTestId("cycle-checklist-loading")).toBeInTheDocument();
});

test("shows error state on fetch failure", async () => {
  api.get.mockRejectedValue(new Error("Network error"));
  render(<CycleActivationChecklist examId="e1" cycleId="cy1" />);
  await waitFor(() => {
    expect(screen.getByTestId("cycle-checklist-error")).toBeInTheDocument();
  });
  expect(screen.getByText(/Network error/)).toBeInTheDocument();
});

test("shows cycle_not_found message when error is set", async () => {
  api.get.mockResolvedValue({
    cycle_readiness: null,
    cycle_readiness_error: "cycle_not_found",
  });
  render(<CycleActivationChecklist examId="e1" cycleId="ghost" />);
  await waitFor(() => {
    expect(screen.getByTestId("cycle-checklist-cycle-not-found")).toBeInTheDocument();
  });
});

test("renders all steps when checklist loaded", async () => {
  api.get.mockResolvedValue({
    cycle_readiness: MOCK_READINESS,
    cycle_readiness_error: null,
  });
  render(<CycleActivationChecklist examId="e1" cycleId="cy1" />);
  await waitFor(() => {
    expect(screen.getByTestId("cycle-checklist")).toBeInTheDocument();
  });
  expect(screen.getByTestId("checklist-step-1")).toBeInTheDocument();
  expect(screen.getByTestId("checklist-step-2")).toBeInTheDocument();
  expect(screen.getByTestId("checklist-step-1-status")).toHaveTextContent("ready");
  expect(screen.getByTestId("checklist-step-2-status")).toHaveTextContent("missing");
});

test("shows deep-link CTA button for steps with action_cta", async () => {
  api.get.mockResolvedValue({
    cycle_readiness: MOCK_READINESS,
    cycle_readiness_error: null,
  });
  render(<CycleActivationChecklist examId="e1" cycleId="cy1" />);
  await waitFor(() => {
    expect(screen.getByTestId("checklist-step-2-cta")).toBeInTheDocument();
  });
  const link = screen.getByTestId("checklist-step-2-cta");
  expect(link).toHaveAttribute("href", "/admin/exam-intelligence/exams/e1?tab=setup");
});

test("shows overall verdict badge", async () => {
  api.get.mockResolvedValue({
    cycle_readiness: MOCK_READINESS,
    cycle_readiness_error: null,
  });
  render(<CycleActivationChecklist examId="e1" cycleId="cy1" />);
  await waitFor(() => {
    expect(screen.getByTestId("cycle-checklist-overall")).toBeInTheDocument();
  });
  expect(screen.getByTestId("cycle-checklist-overall")).toHaveTextContent("Ready to activate");
});

test("fetches with cycle_id in query when cycleId provided", async () => {
  api.get.mockResolvedValue({ cycle_readiness: MOCK_READINESS, cycle_readiness_error: null });
  render(<CycleActivationChecklist examId="e1" cycleId="cy1" />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get).toHaveBeenCalledWith(
    expect.stringContaining("cycle_id=cy1")
  );
});
