/**
 * The descriptive question screen: write, autosave, self-review, submit.
 *
 * What these pin is the behaviour an aspirant would notice if it broke — a word
 * count that stops matching the limit, an autosave that never fires, a submit
 * button that accepts a half-filled rubric.
 */
import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPatch = jest.fn();

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...a) => mockGet(...a),
    post: (...a) => mockPost(...a),
    patch: (...a) => mockPatch(...a),
    del: jest.fn(),
  },
}));

// eslint-disable-next-line import/first
import QuestionScreen from "../QuestionScreen";
// eslint-disable-next-line import/first
import { AUTOSAVE_INTERVAL_MS } from "../useDescriptiveAttempt";

const QUESTION = {
  id: "q-1",
  text: "Examine the relevance of Gandhian thought today.",
  parent_text: "Answer the following in about 150 words each:",
  marks: 10,
  word_limit: 150,
  timer_target_seconds: 720,
  verified_against_official: true,
  optional_subject: "PSIR",
  year: 2024,
  question_number: 2,
};

function draft(over = {}) {
  return {
    id: "att-1",
    pyq_question_id: "q-1",
    status: "draft",
    answer_text: "",
    word_count: 0,
    time_spent_seconds: 0,
    timer_target_seconds: 720,
    self_scores: null,
    self_total: null,
    notes: null,
    ...over,
  };
}

function wire({ attempt = draft(), history = [] } = {}) {
  mockPost.mockImplementation((url) => {
    if (url.endsWith("/attempts")) return Promise.resolve(attempt);
    return Promise.resolve({ ...attempt, status: "submitted" });
  });
  mockPatch.mockImplementation((_url, body) =>
    Promise.resolve({ ...attempt, ...body, word_count: 3 }),
  );
  mockGet.mockResolvedValue({ items: history });
}

async function renderScreen(props = {}) {
  render(<QuestionScreen question={QUESTION} {...props} />);
  await screen.findByTestId("descriptive-question-screen");
}

beforeEach(() => {
  jest.clearAllMocks();
});

// ── the stem ─────────────────────────────────────────────────────────────

test("a sub-part shows its parent stem", async () => {
  wire();
  await renderScreen();
  // "(b) Examine this" is unanswerable without the question it is part (b) of.
  expect(screen.getByTestId("descriptive-parent-stem")).toHaveTextContent(
    "Answer the following in about 150 words each:",
  );
  expect(screen.getByText(QUESTION.text)).toBeInTheDocument();
});

test("opening the question opens exactly one attempt", async () => {
  wire();
  await renderScreen();
  expect(mockPost).toHaveBeenCalledWith("/api/study/descriptive/attempts", {
    pyq_question_id: "q-1",
  });
  expect(mockPost).toHaveBeenCalledTimes(1);
});

// ── the live word count ──────────────────────────────────────────────────

test("the word count tracks what is typed and never caps it", async () => {
  wire();
  await renderScreen();
  const input = screen.getByTestId("descriptive-answer-input");

  fireEvent.change(input, { target: { value: "one two three" } });

  expect(screen.getByTestId("descriptive-word-count")).toHaveTextContent("3 words of 150");
  expect(input).not.toHaveAttribute("maxLength");
});

test("going over the limit is shown, by how much, and still allowed", async () => {
  wire();
  await renderScreen();
  const long = Array.from({ length: 153 }, (_, i) => `w${i}`).join(" ");

  fireEvent.change(screen.getByTestId("descriptive-answer-input"), {
    target: { value: long },
  });

  const counter = screen.getByTestId("descriptive-word-count");
  expect(counter).toHaveTextContent("153 words of 150");
  // The overage is the number the aspirant needs in order to cut.
  expect(counter).toHaveTextContent("3 over");
  expect(screen.getByTestId("descriptive-answer-input")).toHaveValue(long);
});

// ── autosave ─────────────────────────────────────────────────────────────

test("autosave fires on the interval, carrying the answer and elapsed time", async () => {
  jest.useFakeTimers();
  try {
    wire();
    render(<QuestionScreen question={QUESTION} />);
    await act(async () => {});
    fireEvent.change(screen.getByTestId("descriptive-answer-input"), {
      target: { value: "one two three" },
    });
    expect(mockPatch).not.toHaveBeenCalled();

    await act(async () => {
      jest.advanceTimersByTime(AUTOSAVE_INTERVAL_MS);
    });

    // Ten seconds of clock, and the timer was never started. That is the bug:
    // time_spent_seconds used to ride on the optional countdown UI, so it was
    // 0 unless the aspirant pressed Start on a question that had marks.
    expect(mockPatch).toHaveBeenCalledWith("/api/study/descriptive/attempts/att-1", {
      answer_text: "one two three",
      time_spent_seconds: 10,
      pasted_chars: 0,
    });
  } finally {
    jest.useRealTimers();
  }
});

test("the clock runs without the timer ever being started", async () => {
  jest.useFakeTimers();
  try {
    wire();
    render(<QuestionScreen question={QUESTION} />);
    await act(async () => {});
    // No click on descriptive-timer-toggle anywhere in this test. Two autosave
    // windows, so the second proves the clock keeps accumulating across saves
    // rather than restarting from whatever the server echoed back.
    await act(async () => {
      jest.advanceTimersByTime(AUTOSAVE_INTERVAL_MS);
    });
    await act(async () => {
      jest.advanceTimersByTime(AUTOSAVE_INTERVAL_MS);
    });

    const seconds = mockPatch.mock.calls.map(([, body]) => body.time_spent_seconds);
    expect(seconds).toEqual([10, 20]);
  } finally {
    jest.useRealTimers();
  }
});

test("the clock pauses while the tab is hidden", async () => {
  jest.useFakeTimers();
  const original = Object.getOwnPropertyDescriptor(Document.prototype, "hidden");
  let hidden = false;
  Object.defineProperty(document, "hidden", {
    configurable: true,
    get: () => hidden,
  });
  try {
    wire();
    render(<QuestionScreen question={QUESTION} />);
    await act(async () => {});

    await act(async () => {
      jest.advanceTimersByTime(5_000);
    });
    hidden = true;
    // A question left open in a background tab overnight must not record nine
    // hours of "writing".
    await act(async () => {
      jest.advanceTimersByTime(600_000);
    });
    hidden = false;
    await act(async () => {
      jest.advanceTimersByTime(5_000);
    });

    // 5s visible + 10 minutes hidden + 5s visible = 10s recorded.
    const seconds = mockPatch.mock.calls
      .map(([, body]) => body.time_spent_seconds)
      .filter((v) => typeof v === "number");
    expect(Math.max(...seconds)).toBe(10);
  } finally {
    jest.useRealTimers();
    if (original) Object.defineProperty(Document.prototype, "hidden", original);
    else delete document.hidden;
  }
});

test("pasted characters are counted and sent, never blocked", async () => {
  wire();
  await renderScreen();
  const input = screen.getByTestId("descriptive-answer-input");

  fireEvent.paste(input, {
    clipboardData: { getData: () => "a pasted sentence" },
  });
  fireEvent.change(input, { target: { value: "a pasted sentence" } });
  fireEvent.blur(input);

  await waitFor(() =>
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/study/descriptive/attempts/att-1",
      expect.objectContaining({ pasted_chars: "a pasted sentence".length }),
    ),
  );
  // Recorded, not prevented: the text is still there.
  expect(input).toHaveValue("a pasted sentence");
});

test("successive pastes accumulate", async () => {
  wire();
  await renderScreen();
  const input = screen.getByTestId("descriptive-answer-input");

  fireEvent.paste(input, { clipboardData: { getData: () => "abc" } });
  fireEvent.paste(input, { clipboardData: { getData: () => "de" } });
  fireEvent.blur(input);

  await waitFor(() =>
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/study/descriptive/attempts/att-1",
      expect.objectContaining({ pasted_chars: 5 }),
    ),
  );
});

test("autosave fires on blur without waiting for the interval", async () => {
  wire();
  await renderScreen();
  const input = screen.getByTestId("descriptive-answer-input");
  fireEvent.change(input, { target: { value: "one two three" } });
  fireEvent.blur(input);

  await waitFor(() => expect(mockPatch).toHaveBeenCalledTimes(1));
});

test("a failed save says so and keeps the text", async () => {
  wire();
  mockPatch.mockRejectedValue(new Error("offline"));
  await renderScreen();
  const input = screen.getByTestId("descriptive-answer-input");
  fireEvent.change(input, { target: { value: "one two three" } });
  fireEvent.blur(input);

  await waitFor(() =>
    expect(screen.getByTestId("descriptive-save-state")).toHaveTextContent(
      /Couldn't save/i,
    ),
  );
  expect(input).toHaveValue("one two three");
});

test("nothing is saved when nothing changed", async () => {
  wire();
  await renderScreen();
  fireEvent.blur(screen.getByTestId("descriptive-answer-input"));
  await waitFor(() => expect(mockPatch).not.toHaveBeenCalled());
});

// ── the timer ────────────────────────────────────────────────────────────

test("the timer is offered when the question carries marks", async () => {
  wire();
  await renderScreen();
  expect(screen.getByTestId("descriptive-timer")).toHaveTextContent("0:00");
  expect(screen.getByTestId("descriptive-timer")).toHaveTextContent("12:00");
  expect(screen.getByText(/nothing stops when it runs out/i)).toBeInTheDocument();
});

test("no marks means no timer target rather than an invented one", async () => {
  wire();
  render(
    <QuestionScreen
      question={{ ...QUESTION, marks: null, timer_target_seconds: null, word_limit: null }}
    />,
  );
  await screen.findByTestId("descriptive-question-screen");

  expect(screen.queryByTestId("descriptive-timer")).not.toBeInTheDocument();
  expect(screen.getByText(/No word limit given/i)).toBeInTheDocument();
});

// ── provenance ───────────────────────────────────────────────────────────

test("an unverified question says so", async () => {
  wire();
  render(<QuestionScreen question={{ ...QUESTION, verified_against_official: false }} />);
  await screen.findByTestId("descriptive-question-screen");

  expect(screen.getByTestId("descriptive-provenance")).toHaveTextContent(
    /Not checked against the official paper/i,
  );
});

test("a verified question shows no provenance warning", async () => {
  wire();
  await renderScreen();
  expect(screen.queryByTestId("descriptive-provenance")).not.toBeInTheDocument();
});

// ── the rubric ───────────────────────────────────────────────────────────

test("the rubric appears only after finishing, and gates submit until complete", async () => {
  wire();
  await renderScreen();
  expect(screen.queryByTestId("descriptive-rubric")).not.toBeInTheDocument();

  fireEvent.click(screen.getByTestId("descriptive-finish"));
  await screen.findByTestId("descriptive-rubric");

  const submit = screen.getByTestId("descriptive-submit");
  expect(submit).toBeDisabled();

  // Five of six is still incomplete: a total out of 12 measuring five criteria
  // looks like a score and is not one.
  ["structure", "relevance", "coverage", "examples", "conclusion"].forEach((k) => {
    fireEvent.click(screen.getByTestId(`rubric-${k}-2`));
  });
  expect(submit).toBeDisabled();

  fireEvent.click(screen.getByTestId("rubric-within_limit-1"));
  expect(submit).toBeEnabled();
  expect(screen.getByTestId("descriptive-rubric-total")).toHaveTextContent("11 / 12");
});

test("submitting sends every criterion and the notes", async () => {
  wire();
  await renderScreen();
  fireEvent.change(screen.getByTestId("descriptive-answer-input"), {
    target: { value: "one two three" },
  });
  fireEvent.click(screen.getByTestId("descriptive-finish"));
  await screen.findByTestId("descriptive-rubric");

  ["structure", "relevance", "coverage", "examples", "conclusion", "within_limit"].forEach(
    (k) => fireEvent.click(screen.getByTestId(`rubric-${k}-1`)),
  );
  fireEvent.change(screen.getByTestId("descriptive-notes"), {
    target: { value: "Ran out of time." },
  });
  fireEvent.click(screen.getByTestId("descriptive-submit"));

  await waitFor(() =>
    expect(mockPost).toHaveBeenCalledWith(
      "/api/study/descriptive/attempts/att-1/submit",
      {
        self_scores: {
          structure: 1,
          relevance: 1,
          coverage: 1,
          examples: 1,
          conclusion: 1,
          within_limit: 1,
        },
        notes: "Ran out of time.",
        // Submit carries the finals: the last autosave can be ten seconds old,
        // and this is the moment the elapsed time has to be right.
        time_spent_seconds: expect.any(Number),
        pasted_chars: 0,
      },
    ),
  );
});

test("submitting flushes the answer first", async () => {
  wire();
  await renderScreen();
  fireEvent.change(screen.getByTestId("descriptive-answer-input"), {
    target: { value: "a last unsaved paragraph" },
  });
  fireEvent.click(screen.getByTestId("descriptive-finish"));
  await screen.findByTestId("descriptive-rubric");

  // The server recomputes word_count from the STORED text, so an unflushed
  // last paragraph would be missing from the record.
  await waitFor(() =>
    expect(mockPatch).toHaveBeenCalledWith(
      "/api/study/descriptive/attempts/att-1",
      expect.objectContaining({ answer_text: "a last unsaved paragraph" }),
    ),
  );
});

// ── after submit ─────────────────────────────────────────────────────────

test("a submitted attempt is read-only and shows what was saved", async () => {
  wire({
    attempt: draft({
      status: "submitted",
      answer_text: "Written under time.",
      word_count: 3,
      self_total: 9,
      notes: "Conclusion was rushed.",
      time_spent_seconds: 725,
    }),
  });
  await renderScreen();

  expect(screen.getByTestId("descriptive-answer-input")).toHaveAttribute("readonly");
  expect(screen.queryByTestId("descriptive-finish")).not.toBeInTheDocument();
  const saved = screen.getByTestId("descriptive-submitted");
  expect(saved).toHaveTextContent("you scored it 9/12");
  expect(saved).toHaveTextContent("12:05");
});

test("earlier attempts at the same question are listed, and the current one is not", async () => {
  wire({
    history: [
      draft({ id: "att-1", status: "draft" }),
      draft({
        id: "att-0",
        status: "submitted",
        submitted_at: "2026-08-01T10:00:00+00:00",
        word_count: 140,
        self_total: 7,
        notes: "Too much theory.",
      }),
    ],
  });
  await renderScreen();

  const history = await screen.findByTestId("descriptive-history");
  expect(history).toHaveTextContent("140 words");
  expect(history).toHaveTextContent("7/12");
  expect(history).toHaveTextContent("2026-08-01");
  expect(history).not.toHaveTextContent("att-1");
});

test("a map question is refused with a reason rather than an empty editor", async () => {
  const err = new Error("map");
  err.status = 422;
  mockPost.mockRejectedValue(err);
  mockGet.mockResolvedValue({ items: [] });

  render(<QuestionScreen question={QUESTION} />);

  expect(await screen.findByTestId("descriptive-error")).toHaveTextContent(
    /needs a map sheet/i,
  );
});
