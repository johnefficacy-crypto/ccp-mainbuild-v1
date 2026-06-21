import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

import { api } from "../../../lib/api";
import AdminKnowledgeGovernance from "../KnowledgeGovernance";

beforeEach(() => {
  api.get.mockResolvedValue({ recent_audit: [], kg: null });
});

afterEach(() => {
  api.get.mockReset();
});

function wrap() {
  return render(
    <MemoryRouter>
      <AdminKnowledgeGovernance />
    </MemoryRouter>,
  );
}

// ── I7 / §4.4: exam-truth lane removed from KG landing ──────────────────────

test("exam-truth lane card is not rendered", async () => {
  wrap();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.queryByText("Exam truth & planner readiness")).toBeNull();
});

test("landing copy describes three lanes, not four", async () => {
  wrap();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.getByText(/three lanes/i)).toBeInTheDocument();
  expect(screen.queryByText(/four lanes/i)).toBeNull();
});

test("exactly three lane cards are rendered", async () => {
  wrap();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.getByText("User eligibility truth")).toBeInTheDocument();
  expect(screen.getByText("Official-source trust & change propagation")).toBeInTheDocument();
  expect(screen.getByText("AI + personalization guardrails")).toBeInTheDocument();
  expect(screen.queryByText("Exam truth & planner readiness")).toBeNull();
});

test("exam-governance links are not present on the KG landing page", async () => {
  wrap();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.queryByText("Exam Governance Console")).toBeNull();
  expect(screen.queryByText("Exam Registry")).toBeNull();
  expect(screen.queryByText("Create exam")).toBeNull();
});
