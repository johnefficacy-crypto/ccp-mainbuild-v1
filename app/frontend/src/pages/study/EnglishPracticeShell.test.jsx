import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import EnglishPracticeShell from "./EnglishPracticeShell";
import useEnglishPracticeSession from "../../features/study/english-practice/useEnglishPracticeSession";

// Factory mock so the real hook (which imports lib/api → env) is never loaded.
jest.mock("../../features/study/english-practice/useEnglishPracticeSession", () => ({
  __esModule: true,
  default: jest.fn(),
}));

function renderShell() {
  return render(
    <MemoryRouter initialEntries={["/app/study/practice/english/S1"]}>
      <Routes>
        <Route path="/app/study/practice/english/:sessionId" element={<EnglishPracticeShell />} />
      </Routes>
    </MemoryRouter>,
  );
}

// The enriched GET /sessions/{id} resume shape: { session, prompt, units,
// feedback_released }. Each unit may carry latest_version + latest_evaluation.
function payload(units, { prompt = {}, feedbackReleased = true } = {}) {
  return {
    session: { id: "S1", mode: "learning", status: "active" },
    prompt: { prompt_text: "Use the word diligent.", required_words: ["diligent"], ...prompt },
    units,
    feedback_released: feedbackReleased,
  };
}

const ISSUE = {
  issue_type: "word_choice",
  severity: "should_fix",
  span_start_utf16: 0,
  span_end_utf16: 3,
  quoted_text: "She",
  explanation: "Consider a stronger subject.",
};

describe("EnglishPracticeShell", () => {
  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  test("renders a sentence builder for a not-started unit", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload([{ id: "u1", unit_number: 1, status: "not_started", unit_constraints: {} }]),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByTestId("english-practice-shell")).toBeInTheDocument();
    expect(screen.getByTestId("sentence-builder")).toBeInTheDocument();
    // Required-word chip + counter are present (exercise contract).
    expect(screen.getByTestId("word-chips")).toBeInTheDocument();
    expect(screen.getByTestId("words-used")).toHaveTextContent("0/1");
  });

  test("first submit sends CAS version 1", async () => {
    const submitUnit = jest.fn().mockResolvedValue({ ok: true, data: { version_number: 1, evaluation: {} } });
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload([{ id: "u1", unit_number: 1, status: "not_started", unit_constraints: {} }]),
      ),
      submitUnit,
      busy: false,
    });
    renderShell();
    await screen.findByTestId("sentence-builder");
    fireEvent.change(screen.getByTestId("sentence-input"), { target: { value: "She is a diligent student." } });
    fireEvent.click(screen.getByTestId("sentence-submit"));
    await waitFor(() => expect(submitUnit).toHaveBeenCalledWith("S1", 1, "She is a diligent student.", 1));
  });

  test("resumed rewrite_required seeds the editor and submits the NEXT server version (CAS from state)", async () => {
    const submitUnit = jest.fn().mockResolvedValue({ ok: true, data: { version_number: 2 } });
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload([
          {
            id: "u1",
            unit_number: 1,
            status: "rewrite_required",
            unit_constraints: {},
            latest_version: { id: "v1", version_number: 1, answer_text: "She is diligent." },
            latest_evaluation: { id: "e1", language_result: { issues: [ISSUE] } },
          },
        ]),
      ),
      submitUnit,
      busy: false,
    });
    renderShell();
    // Baseline answer is restored from the server, not empty.
    const input = await screen.findByTestId("rewrite-input");
    expect(input).toHaveValue("She is diligent.");
    // Released issue renders.
    expect(screen.getByTestId("issue-card")).toBeInTheDocument();
    // Change the text and submit — CAS must be version 2 (server latest + 1).
    fireEvent.change(input, { target: { value: "She is a diligent scholar." } });
    fireEvent.click(screen.getByTestId("rewrite-submit"));
    await waitFor(() =>
      expect(submitUnit).toHaveBeenCalledWith("S1", 1, "She is a diligent scholar.", 2),
    );
  });

  test("polls a pending unit until the async evaluation lands, then shows issues", async () => {
    jest.useFakeTimers();
    const pending = payload([
      { id: "u1", unit_number: 1, status: "evaluation_pending", unit_constraints: {},
        latest_version: { id: "v1", version_number: 1, answer_text: "She is diligent." } },
    ]);
    const done = payload([
      { id: "u1", unit_number: 1, status: "rewrite_required", unit_constraints: {},
        latest_version: { id: "v1", version_number: 1, answer_text: "She is diligent." },
        latest_evaluation: { id: "e1", language_result: { issues: [ISSUE] } } },
    ]);
    const fetchSession = jest
      .fn()
      .mockResolvedValueOnce(pending) // initial load
      .mockResolvedValue(done); // subsequent polls
    useEnglishPracticeSession.mockReturnValue({ fetchSession, submitUnit: jest.fn(), busy: false });

    renderShell();
    await screen.findByTestId("unit-1-pending");
    expect(fetchSession).toHaveBeenCalledTimes(1);

    // Advance one poll interval → re-fetch resolves to the terminal state.
    await act(async () => {
      jest.advanceTimersByTime(2500);
    });
    await waitFor(() => expect(screen.getByTestId("issue-card")).toBeInTheDocument());
    expect(fetchSession.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  test("hides issues when feedback is not released (exam gating)", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload(
          [
            { id: "u1", unit_number: 1, status: "rewrite_required", unit_constraints: {},
              latest_version: { id: "v1", version_number: 1, answer_text: "She is diligent." },
              latest_evaluation: { id: "e1" } },
          ],
          { feedbackReleased: false },
        ),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("rewrite-editor");
    expect(screen.queryByTestId("issue-card")).not.toBeInTheDocument();
  });

  test("renders an empty state when the session has no units", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(payload([])),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByTestId("ewp-empty")).toBeInTheDocument();
  });

  test("renders an error state with retry when the session cannot load", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockRejectedValue(new Error("boom")),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    expect(await screen.findByText("Practice session unavailable")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });
});
