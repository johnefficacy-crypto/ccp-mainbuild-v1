/**
 * MockAttemptShell — first-visit event regression tests
 *
 * Regression: When attempt loads asynchronously, currentIdx is 0 but
 * questions_ref.current is still empty when the visit effect fires.  The
 * merged effect (depends on [currentIdx, attempt]) fixes this by updating
 * questions_ref before emitting question.visited, ensuring question 1 always
 * gets a visit event on initial load.
 *
 * Tests:
 *   1. question.visited is emitted for question 1 (index 0) when attempt loads
 *   2. question.visited is emitted for question 2 (index 1) when user navigates
 *   3. No duplicate question.visited events for question 1
 */
import React from "react";
import { act, render, fireEvent } from "@testing-library/react";

// ── mock eventBus ────────────────────────────────────────────────────────────
const mockEnqueue = jest.fn();
const mockSetCurrentQuestionId = jest.fn();
const mockInit = jest.fn();
const mockDestroy = jest.fn();

jest.mock("../attemptEventBus", () => ({
  __esModule: true,
  eventBus: {
    init: (...args) => mockInit(...args),
    destroy: (...args) => mockDestroy(...args),
    enqueue: (...args) => mockEnqueue(...args),
    setCurrentQuestionId: (...args) => mockSetCurrentQuestionId(...args),
  },
}));

// ── mock api ─────────────────────────────────────────────────────────────────
const mockGet = jest.fn();
const mockPost = jest.fn();

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
  },
}));

// ── mock supabase ─────────────────────────────────────────────────────────────
jest.mock("../../../lib/supabase", () => ({
  __esModule: true,
  supabase: {
    auth: {
      getSession: () => Promise.resolve({ data: { session: null } }),
    },
  },
}));

// ── mock react-router-dom ────────────────────────────────────────────────────
const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  __esModule: true,
  useNavigate: () => mockNavigate,
  useParams: () => ({ attemptId: "attempt-123" }),
}));

// ── mock useAnswerSync ────────────────────────────────────────────────────────
jest.mock("../useAnswerSync", () => ({
  __esModule: true,
  SYNC: { UNSAVED: "unsaved", SAVING: "saving", SAVED: "saved", RETRYING: "retrying", FAILED: "failed" },
  default: () => ({
    queueSave: jest.fn(),
    flushMany: jest.fn(() => Promise.resolve()),
    retryNow: jest.fn(),
    retryAllFailed: jest.fn(),
    hasUnsynced: false,
    pendingCount: 0,
    failedCount: 0,
    syncStates: {},
  }),
}));

// ── mock AnswerSyncIndicator (simple stub) ────────────────────────────────────
jest.mock("../AnswerSyncIndicator", () => ({
  __esModule: true,
  default: () => null,
}));

import MockAttemptShell from "../MockAttemptShell";

// ── shared attempt fixture ────────────────────────────────────────────────────
const ATTEMPT = {
  id: "attempt-123",
  status: "in_progress",
  template_name: "Test Exam",
  time_remaining_sec: 3600,
  current_section_index: 0,
  section_locks_enabled: false,
  template_config: {},
  questions: [
    {
      question_id: "q1",
      question_text: "Question one",
      section_index: 0,
      marks: 1,
      negative_marks: 0,
      options: [
        { id: "o1a", option_index: "A", option_text: "Option A" },
        { id: "o1b", option_index: "B", option_text: "Option B" },
      ],
      selected_option_id: null,
      is_marked_for_review: false,
    },
    {
      question_id: "q2",
      question_text: "Question two",
      section_index: 0,
      marks: 1,
      negative_marks: 0,
      options: [
        { id: "o2a", option_index: "A", option_text: "Option A" },
        { id: "o2b", option_index: "B", option_text: "Option B" },
      ],
      selected_option_id: null,
      is_marked_for_review: false,
    },
  ],
};

function primeApi(attempt = ATTEMPT) {
  mockGet.mockReset();
  mockGet.mockImplementation((path) => {
    if (path === `/api/study/mocks/attempts/${attempt.id}`) {
      return Promise.resolve(attempt);
    }
    return Promise.reject(new Error(`Unexpected GET ${path}`));
  });
  mockPost.mockReset();
  mockPost.mockResolvedValue({});
}

afterEach(() => {
  jest.clearAllMocks();
});

// ── tests ─────────────────────────────────────────────────────────────────────

test("question.visited is emitted for question 1 (index 0) when attempt loads", async () => {
  primeApi();
  await act(async () => {
    render(<MockAttemptShell />);
  });

  const visitedCalls = mockEnqueue.mock.calls.filter(
    ([type]) => type === "question.visited"
  );
  const visitedQ1 = visitedCalls.filter(
    ([, payload]) => payload?.question_id === "q1"
  );
  expect(visitedQ1.length).toBeGreaterThanOrEqual(1);
});

test("question.visited is emitted for question 2 when navigating to index 1", async () => {
  primeApi();
  const { getByTestId } = await act(async () => render(<MockAttemptShell />));

  // Clear calls from initial load so we can check navigation cleanly
  mockEnqueue.mockClear();

  // Navigate to question 2 via the palette button (index 1)
  await act(async () => {
    fireEvent.click(getByTestId("attempt-nav-1"));
  });

  const visitedCalls = mockEnqueue.mock.calls.filter(
    ([type]) => type === "question.visited"
  );
  const visitedQ2 = visitedCalls.filter(
    ([, payload]) => payload?.question_id === "q2"
  );
  expect(visitedQ2.length).toBeGreaterThanOrEqual(1);
});

test("question.visited for question 1 is not emitted before attempt loads (pre-fix guard)", async () => {
  // Delay the API response so we can check that NO spurious pre-load visit
  // event is emitted with an undefined question_id
  let resolveAttempt;
  mockGet.mockReset();
  mockGet.mockImplementation(() => new Promise((res) => { resolveAttempt = () => res(ATTEMPT); }));
  mockPost.mockReset();

  await act(async () => {
    render(<MockAttemptShell />);
  });

  // At this point the attempt hasn't resolved — check there's no "question.visited"
  // with a valid question_id (the old buggy code would fire with qid=null, which
  // also means no event since the guard `if (qid)` prevents it — but let's confirm
  // there's no spurious visit for q1 before data arrives)
  const preLoadVisits = mockEnqueue.mock.calls.filter(
    ([type, payload]) => type === "question.visited" && payload?.question_id === "q1"
  );
  expect(preLoadVisits.length).toBe(0);

  // Now resolve and confirm q1 gets visited
  await act(async () => {
    resolveAttempt();
  });

  const postLoadVisits = mockEnqueue.mock.calls.filter(
    ([type, payload]) => type === "question.visited" && payload?.question_id === "q1"
  );
  expect(postLoadVisits.length).toBeGreaterThanOrEqual(1);
});

test("no duplicate question.visited events for question 1 on initial load", async () => {
  primeApi();
  await act(async () => {
    render(<MockAttemptShell />);
  });

  const visitedQ1Count = mockEnqueue.mock.calls.filter(
    ([type, payload]) => type === "question.visited" && payload?.question_id === "q1"
  ).length;

  // Exactly one visit event for question 1 on initial load — not zero, not two
  expect(visitedQ1Count).toBe(1);
});

test("setCurrentQuestionId is called with q1 id after attempt loads", async () => {
  primeApi();
  await act(async () => {
    render(<MockAttemptShell />);
  });

  const callsWithQ1 = mockSetCurrentQuestionId.mock.calls.filter(
    ([qid]) => qid === "q1"
  );
  expect(callsWithQ1.length).toBeGreaterThanOrEqual(1);
});
