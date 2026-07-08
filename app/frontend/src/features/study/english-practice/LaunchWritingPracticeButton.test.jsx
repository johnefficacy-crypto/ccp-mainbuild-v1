import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import LaunchWritingPracticeButton from "./LaunchWritingPracticeButton";

// Mock the router: capture navigate() calls without a real Router.
const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

// Mock the data-layer hook so the component's launchWriting call is observable.
const mockLaunchWriting = jest.fn();
jest.mock("./useEnglishPracticeSession", () => ({
  __esModule: true,
  default: () => ({ launchWriting: mockLaunchWriting }),
}));

function apiError(status, detail) {
  const err = new Error(typeof detail === "string" ? detail : "error");
  err.status = status;
  err.detail = detail;
  return err;
}

const TASK = { id: "task-123", action_label: "Start sentence practice" };

beforeEach(() => {
  mockNavigate.mockReset();
  mockLaunchWriting.mockReset();
});

test("renders the launch button on a writing task with its label", () => {
  render(<LaunchWritingPracticeButton task={TASK} />);
  const btn = screen.getByTestId("launch-writing-btn");
  expect(btn).toHaveTextContent("Start sentence practice");
});

test("success: calls launchWriting and navigates to the returned practice_route", async () => {
  mockLaunchWriting.mockResolvedValue({
    session_id: "sess-9",
    practice_route: "/app/study/practice/english/sess-9",
  });
  render(<LaunchWritingPracticeButton task={TASK} />);

  fireEvent.click(screen.getByTestId("launch-writing-btn"));

  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith(
    "/app/study/practice/english/sess-9",
  ));
  expect(mockLaunchWriting).toHaveBeenCalledWith("task-123");
});

test("409 no_eligible_prompt: shows the calm 'no practice yet' state, no navigation", async () => {
  mockLaunchWriting.mockRejectedValue(apiError(409, "no_eligible_prompt"));
  render(<LaunchWritingPracticeButton task={TASK} />);

  fireEvent.click(screen.getByTestId("launch-writing-btn"));

  await screen.findByTestId("launch-writing-no-prompt");
  expect(screen.queryByTestId("launch-writing-error")).not.toBeInTheDocument();
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("404: shows a clear not-available message, no navigation", async () => {
  mockLaunchWriting.mockRejectedValue(apiError(404, "study task not found"));
  render(<LaunchWritingPracticeButton task={TASK} />);

  fireEvent.click(screen.getByTestId("launch-writing-btn"));

  await screen.findByTestId("launch-writing-not-found");
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("network/other error: shows explicit error + retry, no navigation", async () => {
  mockLaunchWriting.mockRejectedValue(apiError(0, "Network error"));
  render(<LaunchWritingPracticeButton task={TASK} />);

  fireEvent.click(screen.getByTestId("launch-writing-btn"));

  await screen.findByTestId("launch-writing-error");
  expect(screen.getByTestId("launch-writing-retry")).toBeInTheDocument();
  expect(mockNavigate).not.toHaveBeenCalled();

  // Retry re-invokes the launch and can succeed.
  mockLaunchWriting.mockResolvedValue({
    session_id: "sess-1",
    practice_route: "/app/study/practice/english/sess-1",
  });
  fireEvent.click(screen.getByTestId("launch-writing-retry"));
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith(
    "/app/study/practice/english/sess-1",
  ));
});

test("loading: the control is disabled while launching", async () => {
  let resolveLaunch;
  mockLaunchWriting.mockReturnValue(
    new Promise((resolve) => {
      resolveLaunch = resolve;
    }),
  );
  render(<LaunchWritingPracticeButton task={TASK} />);

  const btn = screen.getByTestId("launch-writing-btn");
  fireEvent.click(btn);

  await waitFor(() => expect(btn).toBeDisabled());
  expect(btn).toHaveAttribute("aria-busy", "true");
  expect(btn).toHaveTextContent("Starting…");

  resolveLaunch({
    session_id: "sess-2",
    practice_route: "/app/study/practice/english/sess-2",
  });
  await waitFor(() => expect(mockNavigate).toHaveBeenCalled());
});
