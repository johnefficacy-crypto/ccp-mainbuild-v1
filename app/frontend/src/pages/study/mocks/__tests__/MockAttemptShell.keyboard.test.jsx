/**
 * MockAttemptShell — keyboard navigation, option-label normalization, and the
 * sticky footer (PR #942 P0).
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

jest.mock("../useAnswerSync", () => ({
  __esModule: true,
  SYNC: { UNSAVED: "unsaved", SAVING: "saving", SAVED: "saved", RETRYING: "retrying", FAILED: "failed" },
  default: () => ({
    queueSave: jest.fn(),
    flush: jest.fn(() => Promise.resolve()),
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

// Options use NUMERIC option_index (0/1) — the UI must never surface these as
// learner-facing labels; it must show A/B.
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
        { id: "o1a", option_index: 0, option_text: "Alpha" },
        { id: "o1b", option_index: 1, option_text: "Beta" },
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
        { id: "o2a", option_index: 0, option_text: "Gamma" },
        { id: "o2b", option_index: 1, option_text: "Delta" },
      ],
      selected_option_id: null,
      is_marked_for_review: false,
    },
  ],
};

function primeApi() {
  mockGet.mockReset();
  mockGet.mockImplementation((path) =>
    path === `/api/study/mocks/attempts/attempt-123`
      ? Promise.resolve(ATTEMPT)
      : Promise.reject(new Error(`Unexpected GET ${path}`)),
  );
  mockPost.mockReset();
  mockPost.mockResolvedValue({});
}

afterEach(() => jest.clearAllMocks());

test("option labels never show a raw numeric index (0/1 → A/B) and the footer is present", async () => {
  primeApi();
  const { getByTestId } = await act(async () => render(<MockAttemptShell />));

  const optA = getByTestId("attempt-option-0");
  const optB = getByTestId("attempt-option-1");
  expect(optA.textContent).toContain("A.");
  expect(optB.textContent).toContain("B.");
  expect(optA.textContent).not.toMatch(/^\s*0\./);
  expect(optB.textContent).not.toMatch(/1\./);

  // Sticky footer action bar exists.
  expect(getByTestId("attempt-footer")).toBeTruthy();
});

test("ArrowRight / ArrowLeft move between questions", async () => {
  primeApi();
  const { getByTestId, container } = await act(async () => render(<MockAttemptShell />));

  expect(container.textContent).toContain("Q 1 of 2");
  await act(async () => {
    fireEvent.keyDown(window, { key: "ArrowRight" });
  });
  expect(container.textContent).toContain("Q 2 of 2");
  await act(async () => {
    fireEvent.keyDown(window, { key: "ArrowLeft" });
  });
  expect(container.textContent).toContain("Q 1 of 2");
  expect(getByTestId("attempt-footer")).toBeTruthy();
});

test("numeric keys select the option at that position", async () => {
  primeApi();
  const { getByTestId } = await act(async () => render(<MockAttemptShell />));

  expect(getByTestId("attempt-option-1").getAttribute("aria-pressed")).toBe("false");
  await act(async () => {
    fireEvent.keyDown(window, { key: "2" });
  });
  expect(getByTestId("attempt-option-1").getAttribute("aria-pressed")).toBe("true");
});

test("'m' marks the current question for review", async () => {
  primeApi();
  const { getByTestId } = await act(async () => render(<MockAttemptShell />));

  expect(getByTestId("attempt-mark-review").checked).toBe(false);
  await act(async () => {
    fireEvent.keyDown(window, { key: "m" });
  });
  expect(getByTestId("attempt-mark-review").checked).toBe(true);
});
