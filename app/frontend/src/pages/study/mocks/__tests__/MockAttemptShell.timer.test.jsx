/**
 * MockAttemptShell — timer visibility (GQR-R10, checkpost #960 finding 2)
 *
 * The attempt read contract distinguishes timed practice (nullable countdown) from
 * untimed practice: the backend sends `time_remaining_sec: null` for untimed practice.
 * The shell must then render "--" and run NO countdown / auto-submit, while a timed
 * attempt renders and decrements the countdown.
 */
import React from "react";
import { act, render } from "@testing-library/react";

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

const mockGet = jest.fn();
const mockPost = jest.fn();
jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: (...args) => mockGet(...args), post: (...args) => mockPost(...args) },
}));

jest.mock("../../../../shared/config/env", () => ({
  __esModule: true,
  BACKEND_URL: "https://api.example.test/",
}));

jest.mock("../../../../lib/supabase", () => ({
  __esModule: true,
  supabase: { auth: { getSession: () => Promise.resolve({ data: { session: null } }) } },
}));

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  __esModule: true,
  useNavigate: () => mockNavigate,
  useParams: () => ({ attemptId: "attempt-123" }),
}));

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

jest.mock("../AnswerSyncIndicator", () => ({ __esModule: true, default: () => null }));

import MockAttemptShell from "../MockAttemptShell";

function baseAttempt(overrides) {
  return {
    id: "attempt-123",
    status: "in_progress",
    template_name: "Practice",
    current_section_index: 0,
    section_locks_enabled: false,
    template_config: {},
    questions: [
      {
        question_id: "q1",
        question_text: "Q1",
        section_index: 0,
        marks: 1,
        negative_marks: 0,
        options: [{ id: "o1a", option_index: "A", option_text: "A" }],
        selected_option_id: null,
        is_marked_for_review: false,
      },
    ],
    ...overrides,
  };
}

function primeApi(attempt) {
  mockGet.mockReset();
  mockGet.mockImplementation((path) =>
    path === `/api/study/mocks/attempts/${attempt.id}`
      ? Promise.resolve(attempt)
      : Promise.reject(new Error(`Unexpected GET ${path}`))
  );
  mockPost.mockReset();
  mockPost.mockResolvedValue({});
}

afterEach(() => jest.clearAllMocks());

async function renderShell(attempt) {
  let utils;
  await act(async () => {
    utils = render(<MockAttemptShell />);
    await Promise.resolve();
  });
  return utils;
}

test("untimed practice (null countdown) shows -- and never auto-submits", async () => {
  primeApi(baseAttempt({ time_remaining_sec: null }));
  const { getByTestId } = await renderShell();
  expect(getByTestId("attempt-timer").textContent).toBe("--");
  // Advancing time must not tick a countdown or fire an auto-submit.
  act(() => {
    jest.useFakeTimers();
    jest.advanceTimersByTime(5000);
    jest.useRealTimers();
  });
  expect(getByTestId("attempt-timer").textContent).toBe("--");
  const submitCalls = mockPost.mock.calls.filter(([p]) => String(p).includes("/submit"));
  expect(submitCalls).toHaveLength(0);
});

test("timed practice renders the countdown", async () => {
  primeApi(baseAttempt({ time_remaining_sec: 120 }));
  const { getByTestId } = await renderShell();
  expect(getByTestId("attempt-timer").textContent).toBe("2:00");
});
