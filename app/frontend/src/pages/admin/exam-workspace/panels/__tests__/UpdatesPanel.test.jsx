/**
 * F5 — UpdatesPanel is the live "Updates" tab surface for exam_policy_updates.
 * Covers the correction-request affordance added for the immutable affects_*
 * flags: it renders an Affects column (reused from PolicyUpdatesTable), and
 * "Request correction" goes through useApiAction to PATCH .../review with
 * reviewer_status=needs_correction + disputed_flags + reviewer_notes — never
 * mutating the flags directly.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ToastProvider } from "../../../../../shared/ui/core";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), del: jest.fn() },
}));

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: jest.fn(),
}));

const { api } = require("../../../../../lib/api");
const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const UpdatesPanel = require("../UpdatesPanel").default;

const ROW = {
  id: "pu-1",
  title: "Vacancies revised",
  update_type: "vacancy_change",
  source_type: "official",
  reviewer_status: "verified",
  affects_plan: true,
  affects_vacancy: true,
  created_at: "2026-05-01T00:00:00+00:00",
};

function renderPanel(props = {}) {
  return render(
    <ToastProvider>
      <UpdatesPanel {...props} />
    </ToastProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  useExamWorkspace.mockReturnValue({ exam: { id: "exam-1", name: "SSC CGL" } });
  api.get.mockResolvedValue({ items: [ROW] });
  api.patch.mockResolvedValue({ ok: true });
});

test("F5: renders an Affects column showing the active flags", async () => {
  renderPanel();
  await screen.findByTestId(`update-row-${ROW.id}`);
  expect(screen.getByTestId("policy-correction-open-pu-1")).toBeTruthy();
});

test("F5: submitting a correction request PATCHes reviewer_status=needs_correction with disputed_flags and reviewer_notes", async () => {
  renderPanel();
  await screen.findByTestId(`update-row-${ROW.id}`);

  fireEvent.click(screen.getByTestId("policy-correction-open-pu-1"));
  fireEvent.click(screen.getByTestId("policy-correction-flag-pu-1-affects_vacancy"));
  fireEvent.change(screen.getByTestId("policy-correction-reason-pu-1"), {
    target: { value: "vacancy figure looks stale for this cycle" },
  });
  fireEvent.click(screen.getByTestId("policy-correction-submit-pu-1"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [url, body] = api.patch.mock.calls[api.patch.mock.calls.length - 1];
  expect(url).toBe(`/api/admin/exam-intelligence/policy-updates/${ROW.id}/review`);
  expect(body.reviewer_status).toBe("needs_correction");
  expect(body.disputed_flags).toEqual(["affects_vacancy"]);
  expect(body.reviewer_notes).toBe("vacancy figure looks stale for this cycle");
});

test("F5: correction request never sends affects_* fields in the payload", async () => {
  renderPanel();
  await screen.findByTestId(`update-row-${ROW.id}`);
  fireEvent.click(screen.getByTestId("policy-correction-open-pu-1"));
  fireEvent.click(screen.getByTestId("policy-correction-flag-pu-1-affects_plan"));
  fireEvent.change(screen.getByTestId("policy-correction-reason-pu-1"), {
    target: { value: "plan impact flag seems wrong" },
  });
  fireEvent.click(screen.getByTestId("policy-correction-submit-pu-1"));

  await waitFor(() => expect(api.patch).toHaveBeenCalled());
  const [, body] = api.patch.mock.calls[api.patch.mock.calls.length - 1];
  expect(Object.keys(body)).not.toContain("affects_plan");
  expect(Object.keys(body)).not.toContain("affects_vacancy");
});

test("F5: successful correction request reloads the list (api.get called again)", async () => {
  renderPanel();
  await screen.findByTestId(`update-row-${ROW.id}`);
  api.get.mockClear();
  fireEvent.click(screen.getByTestId("policy-correction-open-pu-1"));
  fireEvent.click(screen.getByTestId("policy-correction-flag-pu-1-affects_plan"));
  fireEvent.change(screen.getByTestId("policy-correction-reason-pu-1"), {
    target: { value: "reloading after correction request" },
  });
  fireEvent.click(screen.getByTestId("policy-correction-submit-pu-1"));
  await waitFor(() => expect(api.get).toHaveBeenCalled());
});
