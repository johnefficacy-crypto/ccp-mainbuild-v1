import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import CurrentAffairsAttemptShell from "./CurrentAffairsAttemptShell";
import useCurrentAffairsAttempt from "../../features/study/current-affairs/useCurrentAffairsAttempt";

// Factory mock so the real hook (which imports lib/api → env) is never loaded.
jest.mock("../../features/study/current-affairs/useCurrentAffairsAttempt", () => ({
  __esModule: true,
  default: jest.fn(),
}));

function renderShell() {
  return render(
    <MemoryRouter initialEntries={["/app/study/current-affairs/attempts/A1"]}>
      <Routes>
        <Route
          path="/app/study/current-affairs/attempts/:attemptId"
          element={<CurrentAffairsAttemptShell />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

function question(overrides = {}) {
  return {
    question_id: "q1",
    question_text: "Who issued the June circular?",
    question_type: "mcq",
    options: [
      { id: "o1", option_text: "RBI", option_index: 0 },
      { id: "o2", option_text: "SEBI", option_index: 1 },
    ],
    selected_option_id: null,
    is_marked_for_review: false,
    is_visited: false,
    client_seq: 0,
    time_spent_sec: 0,
    ...overrides,
  };
}

function inProgress(questions = [question()]) {
  return {
    attempt_id: "A1",
    status: "in_progress",
    cadence: "weekly",
    bundle_id: "b1",
    total_questions: questions.length,
    questions,
  };
}

function submitted(questions) {
  return {
    attempt_id: "A1",
    status: "submitted",
    cadence: "weekly",
    bundle_id: "b1",
    total_questions: questions.length,
    total_correct: questions.filter((q) => q.is_correct).length,
    submitted_at: "2026-07-13T00:00:00Z",
    questions,
  };
}

describe("CurrentAffairsAttemptShell", () => {
  afterEach(() => jest.clearAllMocks());

  test("renders frozen questions and hides the answer while in progress", async () => {
    useCurrentAffairsAttempt.mockReturnValue({
      fetchAttempt: jest.fn().mockResolvedValue(inProgress()),
      saveAnswer: jest.fn(),
      submitAttempt: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByTestId("current-affairs-attempt-shell")).toBeInTheDocument();
    expect(screen.getByTestId("ca-question-1")).toBeInTheDocument();
    // No answer/explanation/provenance revealed pre-submit.
    expect(screen.queryByTestId("ca-explanation-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("ca-result-summary")).not.toBeInTheDocument();
  });

  test("selecting an option persists a monotonic client_seq above the stored value", async () => {
    const saveAnswer = jest.fn().mockResolvedValue({ ok: true });
    useCurrentAffairsAttempt.mockReturnValue({
      // Resume: stored client_seq=3, so the next save must be >3.
      fetchAttempt: jest.fn().mockResolvedValue(
        inProgress([question({ client_seq: 3 })]),
      ),
      saveAnswer,
      submitAttempt: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("current-affairs-attempt-shell");
    fireEvent.click(screen.getByTestId("ca-option-1-1")); // pick SEBI
    await waitFor(() => expect(saveAnswer).toHaveBeenCalled());
    expect(saveAnswer).toHaveBeenCalledWith("A1", expect.objectContaining({
      questionId: "q1",
      selectedOptionId: "o2",
      clientSeq: 4,
    }));
  });

  test("submit reveals the answer, explanation and §10 provenance envelope", async () => {
    const fetchAttempt = jest
      .fn()
      .mockResolvedValueOnce(inProgress([question({ selected_option_id: "o2" })]))
      .mockResolvedValueOnce(
        submitted([
          question({
            selected_option_id: "o2",
            correct_option_id: "o1",
            is_correct: false,
            explanation: "The RBI issued it.",
            event_date: "2026-07-09",
            source_published_at: "2026-07-08T00:00:00Z",
            source_url: "https://pib.gov.in/x",
            superseded: true,
            supersession_note: "A newer circular may supersede this.",
          }),
        ]),
      );
    useCurrentAffairsAttempt.mockReturnValue({
      fetchAttempt,
      saveAnswer: jest.fn().mockResolvedValue({ ok: true }),
      submitAttempt: jest.fn().mockResolvedValue({ ok: true, data: { outcome: "submitted" } }),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("current-affairs-attempt-shell");
    fireEvent.click(screen.getByTestId("ca-submit"));

    expect(await screen.findByTestId("ca-result-summary")).toBeInTheDocument();
    expect(screen.getByTestId("ca-explanation-1")).toHaveTextContent("The RBI issued it.");
    expect(screen.getByRole("link", { name: /view source/i })).toHaveAttribute(
      "href",
      "https://pib.gov.in/x",
    );
    expect(screen.getByTestId("ca-superseded-q1")).toHaveTextContent(/supersede/i);
    // Submit control withdrawn post-submit.
    expect(screen.queryByTestId("ca-submit")).not.toBeInTheDocument();
  });

  test("surfaces a load error with retry", async () => {
    useCurrentAffairsAttempt.mockReturnValue({
      fetchAttempt: jest.fn().mockRejectedValue(new Error("boom")),
      saveAnswer: jest.fn(),
      submitAttempt: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByText(/current-affairs attempt unavailable/i)).toBeInTheDocument();
  });
});
