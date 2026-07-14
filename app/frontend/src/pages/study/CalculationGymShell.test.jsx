import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import CalculationGymShell from "./CalculationGymShell";
import useCalculationGym from "../../features/study/calculation-gym/useCalculationGym";

jest.mock("../../features/study/calculation-gym/useCalculationGym", () => ({
  __esModule: true,
  default: jest.fn(),
}));

function renderShell() {
  return render(
    <MemoryRouter initialEntries={["/app/study/calculation-gym/sessions/s1"]}>
      <Routes>
        <Route
          path="/app/study/calculation-gym/sessions/:sessionId"
          element={<CalculationGymShell />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

const inProgress = {
  session_id: "s1",
  status: "in_progress",
  skill: "tables",
  question_count: 2,
  duration_sec: 180,
  expires_at: new Date(Date.now() + 180000).toISOString(),
  items: [
    { item_index: 0, prompt: "12 × 5" },
    { item_index: 1, prompt: "9 × 11" },
  ],
};

describe("CalculationGymShell", () => {
  afterEach(() => jest.clearAllMocks());

  test("runs the rapid-fire flow and submits learner answers", async () => {
    const submitSession = jest.fn().mockResolvedValue({ ok: true, data: {} });
    const fetchSession = jest
      .fn()
      .mockResolvedValueOnce(inProgress)
      .mockResolvedValueOnce({
        ...inProgress,
        status: "submitted",
        score_correct: 1,
        score_total: 2,
        items: [
          { item_index: 0, prompt: "12 × 5", user_answer: "60", expected_answer: "60", is_correct: true },
          { item_index: 1, prompt: "9 × 11", user_answer: "98", expected_answer: "99", is_correct: false },
        ],
      });
    useCalculationGym.mockReturnValue({ fetchSession, submitSession, busy: false });

    renderShell();
    expect(await screen.findByText("12 × 5")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/your answer/i), { target: { value: "60" } });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("9 × 11")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/your answer/i), { target: { value: "98" } });
    fireEvent.click(screen.getByRole("button", { name: /submit session/i }));

    await waitFor(() => expect(submitSession).toHaveBeenCalledTimes(1));
    expect(submitSession.mock.calls[0][1]).toEqual(expect.arrayContaining([
      expect.objectContaining({ item_index: 0, user_answer: "60" }),
      expect.objectContaining({ item_index: 1, user_answer: "98" }),
    ]));
    expect(await screen.findByTestId("calc-gym-result")).toHaveTextContent("Correct answer: 99");
  });

  test("withdraws answer controls for an expired session", async () => {
    useCalculationGym.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue({ ...inProgress, status: "expired" }),
      submitSession: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByText(/time is up/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/your answer/i)).not.toBeInTheDocument();
  });

  test("renders a retryable load error", async () => {
    useCalculationGym.mockReturnValue({
      fetchSession: jest.fn().mockRejectedValue(new Error("boom")),
      submitSession: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByText("boom")).toBeInTheDocument();
  });
});
