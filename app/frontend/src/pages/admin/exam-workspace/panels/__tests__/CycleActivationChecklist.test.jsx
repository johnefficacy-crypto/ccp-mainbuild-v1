/**
 * CycleActivationChecklist — unit tests
 *
 * Component reads from ExamWorkspaceContext (mgmt/mgmtLoading/mgmtError).
 * No direct api.get calls — context is mocked.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

// Mock context — tests inject values via mockContextValue
let mockContextValue = {};
jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: () => mockContextValue,
}));

const CycleActivationChecklist = require("../CycleActivationChecklist").default;

const MOCK_READINESS = {
  cycle_id: "cy1",
  computed_at: "2026-06-29T00:00:00+00:00",
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

const MGMT_WITH_READINESS = {
  contract_version: 1,
  cycle_readiness: MOCK_READINESS,
  cycle_readiness_error: null,
};

beforeEach(() => {
  mockContextValue = { mgmt: null, mgmtLoading: false, mgmtError: "" };
});

test("shows loading state when mgmtLoading", () => {
  mockContextValue = { mgmt: null, mgmtLoading: true, mgmtError: "" };
  render(<CycleActivationChecklist />);
  expect(screen.getByTestId("cycle-checklist-loading")).toBeInTheDocument();
});

test("shows error state when mgmtError", () => {
  mockContextValue = { mgmt: null, mgmtLoading: false, mgmtError: "Network error" };
  render(<CycleActivationChecklist />);
  expect(screen.getByTestId("cycle-checklist-error")).toBeInTheDocument();
  expect(screen.getByText(/Network error/)).toBeInTheDocument();
});

test("renders nothing when mgmt is null", () => {
  mockContextValue = { mgmt: null, mgmtLoading: false, mgmtError: "" };
  const { container } = render(<CycleActivationChecklist />);
  expect(container.firstChild).toBeNull();
});

test("shows version-error when contract_version is unsupported", () => {
  mockContextValue = {
    mgmt: { contract_version: 99, cycle_readiness: null, cycle_readiness_error: null },
    mgmtLoading: false,
    mgmtError: "",
  };
  render(<CycleActivationChecklist />);
  expect(screen.getByTestId("cycle-checklist-version-error")).toBeInTheDocument();
});

test("shows version-error when contract_version is absent", () => {
  mockContextValue = {
    mgmt: { cycle_readiness: null, cycle_readiness_error: null },
    mgmtLoading: false,
    mgmtError: "",
  };
  render(<CycleActivationChecklist />);
  expect(screen.getByTestId("cycle-checklist-version-error")).toBeInTheDocument();
});

test("shows cycle_not_found message when error code is set", () => {
  mockContextValue = {
    mgmt: {
      contract_version: 1,
      cycle_readiness: null,
      cycle_readiness_error: { code: "cycle_not_found", requested_cycle_id: "ghost" },
    },
    mgmtLoading: false,
    mgmtError: "",
  };
  render(<CycleActivationChecklist />);
  expect(screen.getByTestId("cycle-checklist-cycle-not-found")).toBeInTheDocument();
});

test("shows unavailable state when mgmt has no cycle_readiness and no error (A7)", () => {
  mockContextValue = {
    mgmt: { contract_version: 1, cycle_readiness: null, cycle_readiness_error: null },
    mgmtLoading: false,
    mgmtError: "",
  };
  render(<CycleActivationChecklist />);
  expect(screen.getByTestId("cycle-checklist-unavailable")).toBeInTheDocument();
});

test("renders all steps when checklist is available", () => {
  mockContextValue = { mgmt: MGMT_WITH_READINESS, mgmtLoading: false, mgmtError: "" };
  render(<CycleActivationChecklist />);
  expect(screen.getByTestId("cycle-checklist")).toBeInTheDocument();
  expect(screen.getByTestId("checklist-step-1")).toBeInTheDocument();
  expect(screen.getByTestId("checklist-step-2")).toBeInTheDocument();
  expect(screen.getByTestId("checklist-step-1-status")).toHaveTextContent("ready");
  expect(screen.getByTestId("checklist-step-2-status")).toHaveTextContent("missing");
});

test("shows CTA link for steps with action_cta", () => {
  mockContextValue = { mgmt: MGMT_WITH_READINESS, mgmtLoading: false, mgmtError: "" };
  render(<CycleActivationChecklist />);
  const link = screen.getByTestId("checklist-step-2-cta");
  expect(link).toHaveAttribute("href", "/admin/exam-intelligence/exams/e1?tab=setup");
});

test("does not render an overall activation verdict badge (D03)", () => {
  mockContextValue = { mgmt: MGMT_WITH_READINESS, mgmtLoading: false, mgmtError: "" };
  render(<CycleActivationChecklist />);
  expect(screen.queryByTestId("cycle-checklist-overall")).not.toBeInTheDocument();
});
