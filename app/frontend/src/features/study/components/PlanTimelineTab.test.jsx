import React from "react";
import { render, screen, act, waitFor, fireEvent } from "@testing-library/react";

const mockGet = jest.fn();
const mockNavigate = jest.fn();

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: (...args) => mockGet(...args) },
}));

jest.mock("react-router-dom", () => {
  const actual = jest.requireActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

import PlanTimelineTab from "./PlanTimelineTab";

afterEach(() => {
  mockGet.mockReset();
  mockNavigate.mockReset();
});

test("shows empty state when no events in window", async () => {
  mockGet.mockResolvedValue({ events: [] });
  await act(async () => {
    render(<PlanTimelineTab />);
  });
  await waitFor(() => {
    expect(screen.getByText(/No plan changes yet/i)).toBeTruthy();
  });
});

// TODO(PR-fix-4): promote the click-through to a full E2E (plan → click event →
// land on attempt result) once browser E2E infra exists. This unit test covers
// the navigation contract in the meantime.
test("renders a mock-attempt event and navigates to the attempt result on click", async () => {
  mockGet.mockResolvedValue({
    events: [
      {
        id: "e1",
        at: "2026-05-20T10:00:00+00:00",
        kind: "priority_shift",
        reason_code: "mastery_shift",
        reason_human: "Mastery updated from a mock attempt",
        trigger: { type: "mock_attempt", attempt_id: "attempt-7" },
        mastery_delta_db: { topic_id: "t9", before: 40, after: 52, delta: 12 },
      },
    ],
  });
  await act(async () => {
    render(<PlanTimelineTab />);
  });
  const title = await screen.findByText("Priority shift");
  // Mastery delta renders inline (MasteryDeltaIndicator shows the magnitude).
  expect(screen.getByText("12%")).toBeTruthy();
  fireEvent.click(title);
  expect(mockNavigate).toHaveBeenCalledWith("/app/study/mocks/attempts/attempt-7/result");
});

test("suppresses the delta indicator when mastery_delta_db is null", async () => {
  mockGet.mockResolvedValue({
    events: [
      {
        id: "e2",
        at: "2026-05-20T10:00:00+00:00",
        kind: "phase_change",
        reason_code: "deadline_changed",
        reason_human: "Exam deadline changed",
        trigger: { type: "scheduled" },
        mastery_delta_db: null,
      },
    ],
  });
  await act(async () => {
    render(<PlanTimelineTab />);
  });
  await screen.findByText("Phase change");
  expect(screen.queryByLabelText(/improved|declined/i)).toBeNull();
  // A scheduled (non-mock) event title is not a clickable button.
  expect(screen.queryByRole("button", { name: "Phase change" })).toBeNull();
});
