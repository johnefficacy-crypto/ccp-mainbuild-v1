/**
 * PR7 — is_correct persistence regression guard.
 *
 * Root-cause audit result:
 *   (a) onChange: confirmed to fire — toggleCorrect is bound as onChange handler.
 *   (b) Payload: confirmed correct — { payload: { is_correct: !opt.is_correct } }.
 *   (c) Allowlist: _OPTION_FIELDS includes is_correct — confirmed in admin_exam_intel_cms.py:663.
 *
 * None of (a)/(b)/(c) apply in the current code. These tests document that the
 * toggle correctly sends the PATCH and the UI reflects the persisted value after reload.
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: {
    get: jest.fn(),
    patch: jest.fn(),
    post: jest.fn(),
  },
  getApiErrorMessage: (e) => String(e?.message || e),
}));

// eslint-disable-next-line global-require
const { api } = require("../../../../lib/api");
// eslint-disable-next-line global-require
const PyqPaperWorkspace = require("../PyqPaperWorkspace").default;

const EXAMS = [{ id: "e1", name: "SSC CGL", slug: "ssc-cgl" }];
const PAPERS = [{ id: "paper-1", exam_id: "e1", paper_code: "CGL-2024", year: 2024 }];
const QUESTIONS = [
  {
    id: "q-1",
    pyq_paper_id: "paper-1",
    question_text: "What is 2+2?",
    question_type: "mcq",
    reviewer_status: "pending",
  },
];
const OPTIONS_ALL_FALSE = [
  { id: "opt-a", question_id: "q-1", option_label: "A", option_text: "3", is_correct: false, reviewer_status: "pending" },
  { id: "opt-b", question_id: "q-1", option_label: "B", option_text: "4", is_correct: false, reviewer_status: "pending" },
];
const OPTIONS_B_CORRECT = [
  { id: "opt-a", question_id: "q-1", option_label: "A", option_text: "3", is_correct: false, reviewer_status: "pending" },
  { id: "opt-b", question_id: "q-1", option_label: "B", option_text: "4", is_correct: true, reviewer_status: "pending" },
];

function renderWorkspace() {
  return render(<PyqPaperWorkspace />);
}

beforeEach(() => {
  api.get.mockReset();
  api.patch.mockReset();
  api.post.mockReset();
});

/** Set up mocks so the workspace can fully navigate to options. */
function setupMocks({ optionsAfterPatch = OPTIONS_B_CORRECT } = {}) {
  let optionsCallCount = 0;
  api.get.mockImplementation((url) => {
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS });
    if (url.includes("/pyq-papers")) return Promise.resolve({ items: PAPERS });
    if (url.includes("/pyq-questions")) return Promise.resolve({ items: QUESTIONS });
    if (url.includes("/pyq-options")) {
      // First call returns all-false; subsequent (after PATCH) returns updated values.
      optionsCallCount += 1;
      return Promise.resolve({ items: optionsCallCount === 1 ? OPTIONS_ALL_FALSE : optionsAfterPatch });
    }
    return Promise.resolve({ items: [] });
  });
  api.patch.mockResolvedValue({ ok: true, row: { id: "opt-b", is_correct: true } });
}

async function navigateToOptions() {
  // Select exam
  const examSel = await screen.findByTestId("workspace-exam-select");
  await act(async () => {
    fireEvent.change(examSel, { target: { value: "e1" } });
  });

  // Select paper
  const paperSel = await screen.findByTestId("workspace-paper-select");
  await act(async () => {
    fireEvent.change(paperSel, { target: { value: "paper-1" } });
  });

  // Click a question button — questions render in the question-list section
  const qButton = await screen.findByText(/What is 2\+2/);
  await act(async () => {
    fireEvent.click(qButton);
  });

  // Wait for options editor to appear
  await screen.findByTestId("options-editor");
}

test("is_correct checkbox sends PATCH with correct payload", async () => {
  setupMocks();
  renderWorkspace();
  await navigateToOptions();

  const checkboxB = await screen.findByTestId("option-correct-B");
  expect(checkboxB.checked).toBe(false);

  await act(async () => {
    fireEvent.click(checkboxB);
  });

  expect(api.patch).toHaveBeenCalledWith(
    expect.stringContaining("/pyq-options/opt-b"),
    expect.objectContaining({
      reason: expect.any(String),
      payload: { is_correct: true },
    }),
  );
});

test("is_correct checkbox shows updated value after PATCH and options reload", async () => {
  setupMocks();
  renderWorkspace();
  await navigateToOptions();

  const checkboxB = await screen.findByTestId("option-correct-B");
  expect(checkboxB.checked).toBe(false);

  await act(async () => {
    fireEvent.click(checkboxB);
  });

  // After PATCH + options reload, checkbox B should be checked.
  await waitFor(() => {
    const cb = screen.getByTestId("option-correct-B");
    expect(cb.checked).toBe(true);
  });
});

test("is_correct checkbox of other option stays unchanged after sibling toggle", async () => {
  setupMocks();
  renderWorkspace();
  await navigateToOptions();

  await act(async () => {
    fireEvent.click(screen.getByTestId("option-correct-B"));
  });

  await waitFor(() => {
    expect(screen.getByTestId("option-correct-A").checked).toBe(false);
    expect(screen.getByTestId("option-correct-B").checked).toBe(true);
  });
});
