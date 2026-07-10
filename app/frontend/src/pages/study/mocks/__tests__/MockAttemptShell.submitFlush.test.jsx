/**
 * MockAttemptShell — pre-submit telemetry flush regression (PR #803 review P0).
 *
 * Regression: doSubmit() previously POSTed /submit (which synchronously runs
 * compute_and_persist() server-side) without awaiting an event flush, so the
 * final buffered question.visited/answered events could be persisted to /events
 * AFTER analytics was already computed — and /events does not recompute. The fix
 * awaits eventBus.flushAndWait() BEFORE the submit POST.
 */
/* eslint-disable import/first */ // SUT import must follow jest.mock() setup
import React from "react";
import { act, render, fireEvent } from "@testing-library/react";

const mockFlushAndWait = jest.fn(() => Promise.resolve(true));

jest.mock("../attemptEventBus", () => ({
  __esModule: true,
  eventBus: {
    init: jest.fn(),
    destroy: jest.fn(),
    enqueue: jest.fn(),
    setCurrentQuestionId: jest.fn(),
    markSubmitFlush: jest.fn(),
    flushAndWait: (...args) => mockFlushAndWait(...args),
  },
}));

const mockGet = jest.fn();
const mockPost = jest.fn();
jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: (...args) => mockGet(...args), post: (...args) => mockPost(...args) },
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
    flush: jest.fn(() => Promise.resolve()),
    flushMany: jest.fn(() => Promise.resolve()),
    flushAll: jest.fn(() => Promise.resolve({ failedIds: [], answeredCount: 0 })),
    retryNow: jest.fn(),
    retryAllFailed: jest.fn(),
    hasUnsynced: false,
    pendingCount: 0,
    failedCount: 0,
    syncStates: {},
  }),
}));

jest.mock("../AnswerSyncIndicator", () => ({ __esModule: true, default: () => null }));

jest.mock("../../../../shared/config/env", () => ({
  __esModule: true,
  BACKEND_URL: "https://api.example.test/",
}));

import MockAttemptShell from "../MockAttemptShell";

const ATTEMPT = {
  id: "attempt-123",
  status: "in_progress",
  template_name: "Test Exam",
  time_remaining_sec: 3600,
  current_section_index: 0,
  section_locks_enabled: false,
  template_config: {},
  questions: [
    { question_id: "q1", question_text: "Q1", section_index: 0, marks: 1, negative_marks: 0,
      options: [{ id: "o1a", option_index: "A", option_text: "A" }], selected_option_id: null, is_marked_for_review: false },
  ],
};

beforeEach(() => {
  mockGet.mockReset();
  mockGet.mockImplementation((path) =>
    path === `/api/study/mocks/attempts/${ATTEMPT.id}` ? Promise.resolve(ATTEMPT) : Promise.reject(new Error(`GET ${path}`)));
  mockPost.mockReset();
  mockPost.mockResolvedValue({});
  mockFlushAndWait.mockReset();
  mockFlushAndWait.mockResolvedValue(true);
});

afterEach(() => jest.clearAllMocks());

test("doSubmit awaits eventBus.flushAndWait() BEFORE POSTing /submit", async () => {
  const { getByTestId } = await act(async () => render(<MockAttemptShell />));

  await act(async () => { fireEvent.click(getByTestId("attempt-submit")); });        // open confirm dialog
  await act(async () => { fireEvent.click(getByTestId("attempt-confirm-submit")); }); // doSubmit()

  expect(mockFlushAndWait).toHaveBeenCalledTimes(1);
  const submitIdx = mockPost.mock.calls.findIndex(([p]) => p.endsWith("/submit"));
  expect(submitIdx).toBeGreaterThanOrEqual(0);
  // Ordering via jest's global monotonic invocation counter: the flush must be
  // invoked before the submit POST.
  const flushOrder = mockFlushAndWait.mock.invocationCallOrder[0];
  const submitOrder = mockPost.mock.invocationCallOrder[submitIdx];
  expect(flushOrder).toBeLessThan(submitOrder);
});

test("submit still proceeds if the pre-submit flush rejects (telemetry never blocks submit)", async () => {
  mockFlushAndWait.mockRejectedValueOnce(new Error("flush boom"));

  const { getByTestId } = await act(async () => render(<MockAttemptShell />));
  await act(async () => { fireEvent.click(getByTestId("attempt-submit")); });
  await act(async () => { fireEvent.click(getByTestId("attempt-confirm-submit")); });

  const submitCalls = mockPost.mock.calls.filter(([p]) => p.endsWith("/submit"));
  expect(submitCalls).toHaveLength(1); // submit proceeded despite flush failure
});
