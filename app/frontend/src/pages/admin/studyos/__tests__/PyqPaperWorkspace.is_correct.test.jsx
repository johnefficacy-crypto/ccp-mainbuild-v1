/**
 * PR7 — is_correct persistence fix and regression guard.
 *
 * Root-cause: in the OptionsEditor, onChange for is_correct only called
 * updateOption() (local state update) but never called saveOption(), so the
 * PATCH to the backend was never sent when the user toggled the checkbox.
 *
 * Fix applied in PyqPaperWorkspace.jsx: onChange now calls
 *   saveOption({ ...opt, is_correct: e.target.checked }, idx)
 * so the PATCH fires immediately on toggle, not only when the text field blurs.
 */
import React from "react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: {
    get: jest.fn(),
    patch: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
  getApiErrorMessage: (e) => String(e?.message || e),
}));

jest.mock("../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { role: "super_admin", permissions: [] } }),
}));

// eslint-disable-next-line global-require
const { api } = require("../../../../lib/api");
// eslint-disable-next-line global-require
const PyqPaperWorkspace = require("../PyqPaperWorkspace").default;

const PAPER_ID = "paper-1";
const PAPERS = [{ id: PAPER_ID, exam_id: "e1", paper_code: "CGL-2024", year: 2024 }];
const QUESTIONS = [
  {
    id: "q-1",
    pyq_paper_id: PAPER_ID,
    question_number: 1,
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
  return render(
    <MemoryRouter initialEntries={[`/${PAPER_ID}`]}>
      <Routes>
        <Route path="/:pyq_paper_id" element={<PyqPaperWorkspace />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  api.get.mockReset();
  api.patch.mockReset();
  api.post.mockReset();
});

function setupMocks({ optionsAfterPatch = OPTIONS_B_CORRECT } = {}) {
  let optionsCalls = 0;
  api.get.mockImplementation((url) => {
    if (url.includes("/pyq-papers/") && url.includes("/progress")) {
      return Promise.resolve({ total: 1, verified: 0 });
    }
    if (url.includes("/pyq-papers")) return Promise.resolve({ items: PAPERS });
    if (url.includes("/pyq-questions")) return Promise.resolve({ items: QUESTIONS });
    if (url.includes("/pyq-options")) {
      optionsCalls += 1;
      return Promise.resolve({ items: optionsCalls === 1 ? OPTIONS_ALL_FALSE : optionsAfterPatch });
    }
    return Promise.resolve({ items: [] });
  });
  api.patch.mockResolvedValue({ ok: true, row: { id: "opt-b", is_correct: true } });
}

async function selectQuestion() {
  const qItem = await screen.findByTestId("question-list-item-q-1");
  await act(async () => {
    fireEvent.click(qItem);
  });
  // Wait for options editor to show the checkbox
  await screen.findByTestId("option-correct-A");
}

test("is_correct toggle sends PATCH immediately (not only on text blur)", async () => {
  setupMocks();
  renderWorkspace();
  await selectQuestion();

  const checkboxB = screen.getByTestId("option-correct-B");
  expect(checkboxB.checked).toBe(false);

  await act(async () => {
    fireEvent.click(checkboxB);
  });

  expect(api.patch).toHaveBeenCalledWith(
    expect.stringContaining("/pyq-options/opt-b"),
    expect.objectContaining({
      payload: expect.objectContaining({ is_correct: true }),
    }),
  );
});

test("is_correct checkbox reflects persisted value (true stays true after state update)", async () => {
  setupMocks();
  renderWorkspace();
  await selectQuestion();

  await act(async () => {
    fireEvent.click(screen.getByTestId("option-correct-B"));
  });

  // Checkbox B should be checked immediately (optimistic local state update via updateOption).
  await waitFor(() => {
    expect(screen.getByTestId("option-correct-B").checked).toBe(true);
  });
  // Sibling A must remain unchecked.
  expect(screen.getByTestId("option-correct-A").checked).toBe(false);
});

test("is_correct PATCH payload includes both option_text and is_correct", async () => {
  setupMocks();
  renderWorkspace();
  await selectQuestion();

  await act(async () => {
    fireEvent.click(screen.getByTestId("option-correct-B"));
  });

  expect(api.patch).toHaveBeenCalledWith(
    expect.stringContaining("/pyq-options/opt-b"),
    expect.objectContaining({
      payload: expect.objectContaining({
        is_correct: true,
        option_text: "4",
      }),
    }),
  );
});
