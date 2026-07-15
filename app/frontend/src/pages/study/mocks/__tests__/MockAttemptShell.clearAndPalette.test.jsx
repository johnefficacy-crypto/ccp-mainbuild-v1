/**
 * MockAttemptShell — clear-response control (audit 2026-07-14 defect #4) and
 * question-navigator scroll discoverability (defect #3).
 */
import React from "react";
import { act, render, fireEvent } from "@testing-library/react";

const mockEnqueue = jest.fn();
jest.mock("../attemptEventBus", () => ({
  __esModule: true,
  eventBus: {
    init: jest.fn(),
    destroy: jest.fn(),
    enqueue: (...a) => mockEnqueue(...a),
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

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  __esModule: true,
  useNavigate: () => mockNavigate,
  useParams: () => ({ attemptId: "attempt-123" }),
  Link: ({ children }) => <a>{children}</a>,
}));

let mockSync;
jest.mock("../useAnswerSync", () => ({
  __esModule: true,
  SYNC: { UNSAVED: "unsaved", SAVING: "saving", SAVED: "saved", RETRYING: "retrying", FAILED: "failed" },
  default: () => mockSync,
}));

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

jest.mock("../AnswerSyncIndicator", () => ({ __esModule: true, default: () => null }));

import MockAttemptShell from "../MockAttemptShell";

function makeAttempt(questionCount) {
  return {
    id: "attempt-123",
    status: "in_progress",
    template_name: "Test Exam",
    time_remaining_sec: 3600,
    current_section_index: 0,
    section_locks_enabled: false,
    template_config: {},
    questions: Array.from({ length: questionCount }, (_, i) => ({
      question_id: `q${i + 1}`,
      question_text: `Question ${i + 1}`,
      section_index: 0,
      marks: 1,
      negative_marks: 0,
      options: [
        { id: `q${i + 1}a`, option_index: 0, option_text: "Alpha" },
        { id: `q${i + 1}b`, option_index: 1, option_text: "Beta" },
      ],
      selected_option_id: null,
      is_marked_for_review: false,
    })),
  };
}

function primeApi(attempt) {
  mockGet.mockReset();
  mockGet.mockImplementation((path) =>
    path === `/api/study/mocks/attempts/attempt-123`
      ? Promise.resolve(attempt)
      : Promise.reject(new Error(`Unexpected GET ${path}`)),
  );
  mockPost.mockReset();
  mockPost.mockResolvedValue({});
}

beforeEach(() => {
  mockSync = makeSync();
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
});
afterEach(() => jest.clearAllMocks());

test("no Clear response control until a question is answered", async () => {
  primeApi(makeAttempt(2));
  const { queryByTestId } = await act(async () => render(<MockAttemptShell />));
  expect(queryByTestId("attempt-clear-response")).toBeNull();
});

test("Clear response returns an answered question to unattempted and persists a null answer", async () => {
  primeApi(makeAttempt(2));
  const { getByTestId, queryByTestId } = await act(async () => render(<MockAttemptShell />));

  // Answer Q1.
  await act(async () => {
    fireEvent.click(getByTestId("attempt-option-0"));
  });
  expect(getByTestId("attempt-option-0").getAttribute("aria-pressed")).toBe("true");

  // Clear response appears; clicking it deselects and queues a null save.
  const clearBtn = getByTestId("attempt-clear-response");
  await act(async () => {
    fireEvent.click(clearBtn);
  });
  expect(getByTestId("attempt-option-0").getAttribute("aria-pressed")).toBe("false");
  // The control disappears again (nothing left to clear).
  expect(queryByTestId("attempt-clear-response")).toBeNull();

  const clearSave = mockSync.queueSave.mock.calls.find(
    ([, payload]) => payload.question_id === "q1" && payload.selected_option_id === null,
  );
  expect(clearSave).toBeTruthy();
  expect(mockEnqueue).toHaveBeenCalledWith("question.cleared", expect.objectContaining({ question_id: "q1" }));
});

test("navigator renders every question in a dedicated scroll area and scrolls the active item into view", async () => {
  primeApi(makeAttempt(90));
  const { getByTestId } = await act(async () => render(<MockAttemptShell />));

  // Explicit scroll area wraps the full 90-button grid (defect #3).
  const scroll = getByTestId("attempt-palette-scroll");
  expect(scroll).toBeTruthy();
  expect(getByTestId("attempt-nav-0")).toBeTruthy();
  expect(getByTestId("attempt-nav-89")).toBeTruthy();
  expect(scroll.contains(getByTestId("attempt-nav-89"))).toBe(true);

  // Advancing scrolls the newly-active palette button into view.
  window.HTMLElement.prototype.scrollIntoView.mockClear();
  await act(async () => {
    fireEvent.keyDown(window, { key: "ArrowRight" });
  });
  expect(window.HTMLElement.prototype.scrollIntoView).toHaveBeenCalled();
});
