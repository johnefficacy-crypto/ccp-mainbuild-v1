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

  test("selecting an option persists a monotonic client_seq above the stored value and resumes time", async () => {
    const saveAnswer = jest.fn().mockResolvedValue({ ok: true, data: { status: "recorded" } });
    useCurrentAffairsAttempt.mockReturnValue({
      // Resume: stored client_seq=3 (next save >3) and stored time=30s (never reset to 0).
      fetchAttempt: jest.fn().mockResolvedValue(
        inProgress([question({ client_seq: 3, time_spent_sec: 30 })]),
      ),
      saveAnswer,
      submitAttempt: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("current-affairs-attempt-shell");
    fireEvent.click(screen.getByTestId("ca-option-1-1")); // pick SEBI
    await waitFor(() => expect(saveAnswer).toHaveBeenCalled());
    const [, payload] = saveAnswer.mock.calls[0];
    expect(payload).toMatchObject({ questionId: "q1", selectedOptionId: "o2", clientSeq: 4 });
    // Cumulative time carries the resumed base forward (never resets to zero).
    expect(payload.timeSpentSec).toBeGreaterThanOrEqual(30);
  });

  test("a stale/idempotent save reconciles against the authoritative stored answer", async () => {
    // The server no-ops an equal/lower sequence and reports already_recorded WITHOUT
    // storing our selection — the shell must refetch, not leave a false optimistic pick.
    const fetchAttempt = jest
      .fn()
      .mockResolvedValueOnce(inProgress([question({ client_seq: 0 })]))
      // Authoritative state after the race: another device already recorded "o1".
      .mockResolvedValueOnce(inProgress([question({ selected_option_id: "o1", client_seq: 5 })]));
    const saveAnswer = jest
      .fn()
      .mockResolvedValue({ ok: true, data: { status: "already_recorded", idempotent: true } });
    useCurrentAffairsAttempt.mockReturnValue({
      fetchAttempt,
      saveAnswer,
      submitAttempt: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("current-affairs-attempt-shell");
    fireEvent.click(screen.getByTestId("ca-option-1-1")); // optimistically pick SEBI (o2)
    // Reconcile refetch fires; the authoritative RBI (o1) wins over the optimistic pick.
    await waitFor(() => expect(fetchAttempt).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(screen.getByTestId("ca-option-1-0").querySelector("input").checked).toBe(true),
    );
    expect(screen.getByTestId("ca-option-1-1").querySelector("input").checked).toBe(false);
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
