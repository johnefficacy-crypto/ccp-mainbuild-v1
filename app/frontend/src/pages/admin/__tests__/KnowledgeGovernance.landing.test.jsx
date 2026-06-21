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

// ── 4.6F: exam-truth lane chips point operators at the console ──────────────

test("exam-truth lane's first chip is 'Exam Governance Console' routing to /console", async () => {
  wrap();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  const console = screen.getByText("Exam Governance Console");
  expect(console.closest("a").getAttribute("href")).toBe("/admin/exam-intelligence/console");
});

test("exam-truth lane chips include Exam Registry and Create exam", async () => {
  wrap();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.getByText("Exam Registry").closest("a").getAttribute("href")).toBe(
    "/admin/exam-intelligence",
  );
  expect(screen.getByText("Create exam").closest("a").getAttribute("href")).toBe(
    "/admin/exam-intelligence/new",
  );
});

test("'CMS / PYQ' is no longer a primary exam-truth chip", async () => {
  wrap();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.queryByText("CMS / PYQ")).toBeNull();
});
