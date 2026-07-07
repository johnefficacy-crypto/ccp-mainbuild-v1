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
    window.sessionStorage.clear();
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

  // Advance N poll intervals, flushing microtasks after each so the awaited
  // async tick resolves and schedules the next timer (works on legacy timers,
  // which lack advanceTimersByTimeAsync).
  async function advancePolls(n) {
    for (let i = 0; i < n; i += 1) {
      // eslint-disable-next-line no-await-in-loop
      await act(async () => {
        jest.advanceTimersByTime(2500);
      });
    }
  }

  function deferred() {
    let resolve;
    const promise = new Promise((r) => {
      resolve = r;
    });
    return { promise, resolve };
  }

  function pendingUnit() {
    return payload([
      { id: "u1", unit_number: 1, status: "evaluation_pending", unit_constraints: {},
        latest_version: { id: "v1", version_number: 1, answer_text: "She is diligent." } },
    ]);
  }
  function doneUnit() {
    return payload([
      { id: "u1", unit_number: 1, status: "rewrite_required", unit_constraints: {},
        latest_version: { id: "v1", version_number: 1, answer_text: "She is diligent." },
        latest_evaluation: { id: "e1", language_result: { issues: [ISSUE] } } },
    ]);
  }

  test("polls a pending unit until the async evaluation lands, then shows issues", async () => {
    jest.useFakeTimers();
    const fetchSession = jest
      .fn()
      .mockResolvedValueOnce(pendingUnit()) // initial load
      .mockResolvedValue(doneUnit()); // subsequent polls
    useEnglishPracticeSession.mockReturnValue({ fetchSession, submitUnit: jest.fn(), busy: false });

    renderShell();
    await screen.findByTestId("unit-1-pending");
    expect(fetchSession).toHaveBeenCalledTimes(1);

    // Advance one poll interval → re-fetch resolves to the terminal state.
    await advancePolls(1);
    expect(screen.getByTestId("issue-card")).toBeInTheDocument();
    expect(fetchSession.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  test("polling stops and does not keep fetching after the component unmounts", async () => {
    jest.useFakeTimers();
    const fetchSession = jest.fn().mockResolvedValue(pendingUnit());
    useEnglishPracticeSession.mockReturnValue({ fetchSession, submitUnit: jest.fn(), busy: false });

    const { unmount } = renderShell();
    await screen.findByTestId("unit-1-pending");
    const callsBefore = fetchSession.mock.calls.length;
    unmount();
    await advancePolls(5);
    // No further fetches once unmounted (cleanup cleared the timer + token).
    expect(fetchSession.mock.calls.length).toBe(callsBefore);
  });

  test("surfaces a timeout + manual retry once the poll cap is hit", async () => {
    jest.useFakeTimers();
    const fetchSession = jest.fn().mockResolvedValue(pendingUnit()); // never terminal
    useEnglishPracticeSession.mockReturnValue({ fetchSession, submitUnit: jest.fn(), busy: false });

    renderShell();
    await screen.findByTestId("unit-1-pending");
    // Exhaust the cap (24 polls) plus margin.
    await advancePolls(26);
    expect(screen.getByTestId("unit-1-poll-timeout")).toBeInTheDocument();
    const callsAtCap = fetchSession.mock.calls.length;
    // Manual retry re-fetches.
    await act(async () => {
      screen.getByTestId("unit-1-poll-retry").click();
    });
    expect(fetchSession.mock.calls.length).toBeGreaterThan(callsAtCap);
  });

  test("retains the before/after diff through a successful rewrite", async () => {
    const rewrite = payload([
      { id: "u1", unit_number: 1, status: "rewrite_required", unit_constraints: {},
        latest_version: { id: "v1", version_number: 1, answer_text: "She is diligent." } },
    ]);
    const ready = payload([
      { id: "u1", unit_number: 1, status: "ready", unit_constraints: {},
        latest_version: { id: "v2", version_number: 2, answer_text: "She is a diligent scholar." } },
    ]);
    const fetchSession = jest
      .fn()
      .mockResolvedValueOnce(rewrite) // initial
      .mockResolvedValue(ready); // after submit refresh
    const submitUnit = jest.fn().mockResolvedValue({ ok: true, data: { version_number: 2 } });
    useEnglishPracticeSession.mockReturnValue({ fetchSession, submitUnit, busy: false });

    renderShell();
    const input = await screen.findByTestId("rewrite-input");
    fireEvent.change(input, { target: { value: "She is a diligent scholar." } });
    fireEvent.click(screen.getByTestId("rewrite-submit"));

    await waitFor(() => expect(screen.getByTestId("unit-1-rewrite-diff")).toBeInTheDocument());
    expect(screen.getByTestId("unit-1-done")).toBeInTheDocument();
  });

  test("resumes the before/after diff on reload from previous_version", async () => {
    const ready = payload([
      { id: "u1", unit_number: 1, status: "ready", unit_constraints: {},
        previous_version: { id: "v1", version_number: 1, answer_text: "She is diligent." },
        latest_version: { id: "v2", version_number: 2, answer_text: "She is a diligent scholar." } },
    ]);
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(ready),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    // No in-session result exists on a fresh load — the diff comes from the
    // resumed prior version → latest version.
    expect(await screen.findByTestId("unit-1-rewrite-diff")).toBeInTheDocument();
  });

  test("a committed submit locks the unit even if the authoritative refresh fails", async () => {
    const fetchSession = jest
      .fn()
      .mockResolvedValueOnce(
        payload([{ id: "u1", unit_number: 1, status: "not_started", unit_constraints: {} }]),
      )
      .mockRejectedValue(new Error("refresh boom")); // post-submit refresh fails
    const submitUnit = jest.fn().mockResolvedValue({ ok: true, data: { version_number: 1 } });
    useEnglishPracticeSession.mockReturnValue({ fetchSession, submitUnit, busy: false });

    renderShell();
    await screen.findByTestId("sentence-builder");
    fireEvent.change(screen.getByTestId("sentence-input"), { target: { value: "my answer" } });
    fireEvent.click(screen.getByTestId("sentence-submit"));

    // The durable submit optimistically locks the unit into pending: the composer
    // is withdrawn and no duplicate submit is possible, even though refresh failed.
    await waitFor(() => expect(screen.getByTestId("unit-1-pending")).toBeInTheDocument());
    expect(screen.queryByTestId("sentence-builder")).not.toBeInTheDocument();
    expect(submitUnit).toHaveBeenCalledTimes(1);
  });

  test("an out-of-order poll cannot revert a unit submitted meanwhile", async () => {
    jest.useFakeTimers();
    const u1Pending = {
      id: "u1", unit_number: 1, status: "evaluation_pending", unit_constraints: {},
      latest_version: { id: "v1", version_number: 1, answer_text: "a sentence here" },
    };
    const initial = payload([u1Pending, { id: "u2", unit_number: 2, status: "not_started", unit_constraints: {} }]);
    // Stale snapshot the older u1 poll will return LAST — u2 still not_started.
    const stale = payload([u1Pending, { id: "u2", unit_number: 2, status: "not_started", unit_constraints: {} }]);
    // Fresh post-submit refresh — u2 now pending.
    const fresh = payload([
      u1Pending,
      { id: "u2", unit_number: 2, status: "evaluation_pending", unit_constraints: {},
        latest_version: { id: "v2b", version_number: 1, answer_text: "hello world here" } },
    ]);

    const pollD = deferred();
    const refreshD = deferred();
    const fetchSession = jest
      .fn()
      .mockResolvedValueOnce(initial) // 1: initial load
      .mockReturnValueOnce(pollD.promise) // 2: the u1 poll (kept in flight)
      .mockReturnValueOnce(refreshD.promise); // 3: post-submit refresh for u2
    const submitUnit = jest.fn().mockResolvedValue({ ok: true, data: { version_number: 1 } });
    useEnglishPracticeSession.mockReturnValue({ fetchSession, submitUnit, busy: false });

    renderShell();
    await screen.findByTestId("sentence-builder"); // u2 composer

    // Start the u1 poll (call 2) — leaves it in flight.
    await act(async () => {
      jest.advanceTimersByTime(2500);
    });
    // Submit u2 → optimistic pending + post-submit refresh (call 3).
    fireEvent.change(screen.getByTestId("sentence-input"), { target: { value: "hello world here" } });
    fireEvent.click(screen.getByTestId("sentence-submit"));
    // Fresh refresh resolves FIRST (u2 pending)...
    await act(async () => {
      refreshD.resolve(fresh);
    });
    // ...then the older poll resolves LAST with the stale snapshot.
    await act(async () => {
      pollD.resolve(stale);
    });

    // u2 must remain pending — the stale poll is dropped by the sequence guard.
    expect(screen.getByTestId("unit-2-pending")).toBeInTheDocument();
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

  test("fails closed on a missing feedback_released flag (hides issues)", async () => {
    const data = {
      session: { id: "S1", mode: "learning", status: "active" },
      prompt: { prompt_text: "p", required_words: [] },
      units: [
        { id: "u1", unit_number: 1, status: "rewrite_required", unit_constraints: {},
          latest_version: { id: "v1", version_number: 1, answer_text: "She is diligent." },
          latest_evaluation: { id: "e1", language_result: { issues: [ISSUE] } } },
      ],
      // feedback_released intentionally OMITTED — client must fail closed.
    };
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(data),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("rewrite-editor");
    expect(screen.queryByTestId("issue-card")).not.toBeInTheDocument();
  });

  // EWP-SP1: source_text is immutable task context visible across every state.
  const SOURCE_PROMPT = {
    prompt_text: "Correct the sentence.",
    exercise_type: "sentence_correction",
    source_text: "He go to school every day.",
    required_words: [],
  };

  test("renders source context in the compose (not_started) state", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload([{ id: "u1", unit_number: 1, status: "not_started", unit_constraints: {} }],
          { prompt: SOURCE_PROMPT }),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("sentence-builder");
    expect(screen.getByTestId("source-context")).toBeInTheDocument();
    expect(screen.getByTestId("source-context-text")).toHaveTextContent("He go to school every day.");
    expect(screen.getByTestId("source-context")).toHaveAttribute("data-readonly", "true");
  });

  test("keeps source context visible in evaluation-pending state", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload([{ id: "u1", unit_number: 1, status: "evaluation_pending", unit_constraints: {},
          latest_version: { id: "v1", version_number: 1, answer_text: "He go to school every day." } }],
          { prompt: SOURCE_PROMPT }),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("unit-1-pending");
    expect(screen.getByTestId("source-context")).toBeInTheDocument();
  });

  test("keeps source context visible in the rewrite state", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload([{ id: "u1", unit_number: 1, status: "rewrite_required", unit_constraints: {},
          latest_version: { id: "v1", version_number: 1, answer_text: "He go to school every day." } }],
          { prompt: SOURCE_PROMPT }),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("rewrite-input");
    expect(screen.getByTestId("source-context")).toBeInTheDocument();
  });

  test("keeps source context visible in a resumed completed/ready state", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload([{ id: "u1", unit_number: 1, status: "completed", unit_constraints: {},
          latest_version: { id: "v2", version_number: 2, answer_text: "He goes to school every day." } }],
          { prompt: SOURCE_PROMPT }),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("unit-1-done");
    expect(screen.getByTestId("source-context")).toBeInTheDocument();
  });

  test("omits source context when the prompt has no source_text (construction prompt)", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload([{ id: "u1", unit_number: 1, status: "not_started", unit_constraints: {} }],
          { prompt: { prompt_text: "Use diligent.", exercise_type: "sentence_construction", required_words: [] } }),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    renderShell();
    await screen.findByTestId("sentence-builder");
    expect(screen.queryByTestId("source-context")).not.toBeInTheDocument();
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

  test("offers a contextual Error Lab entry that navigates to /app/study/error-lab", async () => {
    useEnglishPracticeSession.mockReturnValue({
      fetchSession: jest.fn().mockResolvedValue(
        payload([{ id: "u1", unit_number: 1, status: "not_started", unit_constraints: {} }]),
      ),
      submitUnit: jest.fn(),
      busy: false,
    });
    render(
      <MemoryRouter initialEntries={["/app/study/practice/english/S1"]}>
        <Routes>
          <Route path="/app/study/practice/english/:sessionId" element={<EnglishPracticeShell />} />
          <Route
            path="/app/study/error-lab"
            element={<div data-testid="error-lab-landing">Error Lab</div>}
          />
        </Routes>
      </MemoryRouter>,
    );
    const link = await screen.findByTestId("error-lab-link");
    expect(link).toHaveAttribute("href", "/app/study/error-lab");
    fireEvent.click(link);
    expect(await screen.findByTestId("error-lab-landing")).toBeInTheDocument();
  });
});
