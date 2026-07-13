/**
 * MockAttemptShell — integer/numerical question input + numeric-answer save
 * (PYQ PR-11 / gate G11 runtime).
 */
import React from "react";
import { act, render, fireEvent } from "@testing-library/react";

jest.mock("../attemptEventBus", () => ({
  __esModule: true,
  eventBus: {
    init: jest.fn(),
    destroy: jest.fn(),
    enqueue: jest.fn(),
    setCurrentQuestionId: jest.fn(),
    markSubmitFlush: jest.fn(),
    flushAndWait: jest.fn(() => Promise.resolve(true)),
  },
}));

const mockGet = jest.fn();
const mockPost = jest.fn();
jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: (...a) => mockGet(...a), post: (...a) => mockPost(...a) },
}));
jest.mock("../../../../shared/config/env", () => ({ __esModule: true, BACKEND_URL: "https://api.example.test/" }));
jest.mock("../../../../lib/supabase", () => ({
  __esModule: true,
  supabase: { auth: { getSession: () => Promise.resolve({ data: { session: null } }) } },
}));
jest.mock("react-router-dom", () => ({
  __esModule: true,
  useNavigate: () => jest.fn(),
  useParams: () => ({ attemptId: "attempt-int" }),
  Link: ({ children }) => <a>{children}</a>,
}));

let mockSync;
jest.mock("../useAnswerSync", () => ({
  __esModule: true,
  SYNC: { UNSAVED: "unsaved", SAVING: "saving", SAVED: "saved", RETRYING: "retrying", FAILED: "failed" },
  default: () => mockSync,
}));
jest.mock("../AnswerSyncIndicator", () => ({ __esModule: true, default: () => null }));

import MockAttemptShell from "../MockAttemptShell";

const ATTEMPT = {
  id: "attempt-int",
  status: "in_progress",
  template_name: "Integer Mock",
  time_remaining_sec: 3600,
  current_section_index: 0,
  section_locks_enabled: false,
  template_config: {},
  questions: [
    {
      question_id: "iq1",
      question_text: "What is 6 x 7?",
      question_type: "integer",
      section_index: 0,
      marks: 1,
      negative_marks: 0,
      options: [],
      selected_option_id: null,
      numeric_answer: null,
      is_marked_for_review: false,
    },
  ],
};

function makeSync(overrides = {}) {
  return {
    queueSave: jest.fn(),
    flush: jest.fn(() => Promise.resolve()),
    flushMany: jest.fn(() => Promise.resolve()),
    flushAll: jest.fn(() => Promise.resolve({ failedIds: [], answeredCount: 0 })),
    retryNow: jest.fn(),
    retryAllFailed: jest.fn(),
    hasUnsynced: false,
    pendingCount: 0,
    failedCount: 0,
    syncStates: {},
    ...overrides,
  };
}

beforeEach(() => {
  mockSync = makeSync();
  mockGet.mockReset();
  mockGet.mockImplementation((path) =>
    path === `/api/study/mocks/attempts/attempt-int`
      ? Promise.resolve(ATTEMPT)
      : Promise.reject(new Error(`Unexpected GET ${path}`)),
  );
  mockPost.mockReset();
  mockPost.mockResolvedValue({});
});
afterEach(() => jest.clearAllMocks());

test("integer question renders a numeric input instead of option buttons", async () => {
  const { getByTestId, queryByTestId } = await act(async () => render(<MockAttemptShell />));
  expect(getByTestId("attempt-numeric-input")).toBeTruthy();
  // No option buttons for an integer question.
  expect(queryByTestId("attempt-option-0")).toBeNull();
});

test("typing a numeric answer queues a save carrying numeric_answer (parsed) and no option", async () => {
  const { getByTestId } = await act(async () => render(<MockAttemptShell />));
  await act(async () => {
    fireEvent.change(getByTestId("attempt-numeric-input"), { target: { value: "42" } });
  });
  const calls = mockSync.queueSave.mock.calls;
  expect(calls.length).toBeGreaterThan(0);
  const [qid, payload] = calls[calls.length - 1];
  expect(qid).toBe("iq1");
  expect(payload.numeric_answer).toBe(42);
  expect(payload.selected_option_id).toBeNull();
});

test("clearing the input sends numeric_answer null (unattempted / fail-closed)", async () => {
  const { getByTestId } = await act(async () => render(<MockAttemptShell />));
  const input = getByTestId("attempt-numeric-input");
  await act(async () => fireEvent.change(input, { target: { value: "42" } }));
  await act(async () => fireEvent.change(input, { target: { value: "" } }));
  const [, payload] = mockSync.queueSave.mock.calls[mockSync.queueSave.mock.calls.length - 1];
  expect(payload.numeric_answer).toBeNull();
});
