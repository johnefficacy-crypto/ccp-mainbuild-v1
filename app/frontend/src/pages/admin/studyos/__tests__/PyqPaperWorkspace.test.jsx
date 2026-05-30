/**
 * Tests for PyqPaperWorkspace — three-pane PYQ reviewer workspace.
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
}));

const { api } = require("../../../../lib/api");
const PyqPaperWorkspace = require("../PyqPaperWorkspace").default;

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PAPER_ID = "paper-uuid-1";
const PAPER = {
  id: PAPER_ID,
  year: 2026,
  paper_code: "GS-I",
  shift: "I",
  metadata: { expected_question_count: 5 },
};
const QUESTIONS = [
  {
    id: "q1",
    question_number: 1,
    question_text: "What is the capital of India?",
    reviewer_status: "pending",
    source_kind: "auto_extracted",
    source_document_id: "doc-1",
    source_page: 3,
    confidence_by_field: { question_text: 0.92 },
    content_hash: "abc123",
    metadata: {},
  },
  {
    id: "q2",
    question_number: 2,
    question_text: "Who was the first PM of India?",
    reviewer_status: "verified",
    source_kind: "manual",
    source_document_id: null,
    source_page: null,
    confidence_by_field: null,
    content_hash: "def456",
    metadata: {},
  },
  {
    id: "q3",
    question_number: 3,
    question_text: "Name the highest peak in India.",
    reviewer_status: "rejected",
    source_kind: "auto_extracted",
    source_document_id: "doc-1",
    source_page: 5,
    confidence_by_field: { question_text: 0.55 },
    content_hash: "ghi789",
    metadata: {},
  },
];

const OPTIONS = [
  { id: "o1", question_id: "q1", option_label: "A", option_text: "Delhi", is_correct: true },
  { id: "o2", question_id: "q1", option_label: "B", option_text: "Mumbai", is_correct: false },
];

const PROGRESS = {
  paper_id: PAPER_ID,
  total_expected: 5,
  present: 3,
  missing: [4, 5],
  by_status: { pending: 1, verified: 1, rejected: 1 },
};

// ── Render helper ─────────────────────────────────────────────────────────────

function renderWorkspace() {
  return render(
    <MemoryRouter initialEntries={[`/admin/exam-intelligence/pyq-papers/${PAPER_ID}/workspace`]}>
      <Routes>
        <Route
          path="/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace"
          element={<PyqPaperWorkspace />}
        />
        <Route path="/admin/exam-intelligence" element={<div>Exam intel home</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function setupMocks() {
  api.get.mockImplementation((url) => {
    if (url.includes("/pyq-papers?")) return Promise.resolve({ items: [PAPER] });
    if (url.includes("/pyq-questions?")) return Promise.resolve({ items: QUESTIONS });
    if (url.includes("/progress")) return Promise.resolve(PROGRESS);
    if (url.includes("/pyq-options?")) return Promise.resolve({ items: OPTIONS });
    if (url.includes("/dup-check")) return Promise.resolve({ matches: [] });
    if (url.includes("/signed-pdf")) return Promise.resolve({ signed_url: "https://example.com/doc.pdf" });
    return Promise.resolve({});
  });
  api.post.mockResolvedValue({ ok: true, question: { id: "new-q", question_number: 4 } });
  api.patch.mockResolvedValue({ ok: true, row: {} });
}

beforeEach(() => {
  jest.clearAllMocks();
  setupMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

test("workspace loads with paper ID and fetches questions", async () => {
  renderWorkspace();
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/pyq-questions?")));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/progress")));
});

test("left pane lists questions sorted by question_number", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-q1"));
  const q1 = screen.getByTestId("question-list-item-q1");
  const q2 = screen.getByTestId("question-list-item-q2");
  // q1 appears before q2 in DOM (sorted by question_number ascending)
  expect(q1.compareDocumentPosition(q2) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

test("selecting a question populates center pane", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-q1"));
  fireEvent.click(screen.getByTestId("question-list-item-q1"));
  await waitFor(() => screen.getByTestId("editor-question-text"));
  const textarea = screen.getByTestId("editor-question-text");
  expect(textarea.value).toContain("capital of India");
});

test("question_text is visible and editable in center pane", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-q1"));
  fireEvent.click(screen.getByTestId("question-list-item-q1"));
  await waitFor(() => screen.getByTestId("editor-question-text"));
  const textarea = screen.getByTestId("editor-question-text");
  fireEvent.change(textarea, { target: { value: "Updated question text" } });
  expect(textarea.value).toBe("Updated question text");
});

test("Verify button calls correct API", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-q1"));
  fireEvent.click(screen.getByTestId("question-list-item-q1"));
  await waitFor(() => screen.getByTestId("btn-verify"));
  fireEvent.click(screen.getByTestId("btn-verify"));
  await waitFor(() =>
    expect(api.patch).toHaveBeenCalledWith(
      expect.stringContaining("/pyq-questions/q1"),
      expect.objectContaining({ reason: expect.any(String) }),
    ),
  );
});

test("Reject button exists and is clickable", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-q1"));
  fireEvent.click(screen.getByTestId("question-list-item-q1"));
  await waitFor(() => screen.getByTestId("btn-reject"));
  fireEvent.click(screen.getByTestId("btn-reject"));
  await waitFor(() =>
    expect(api.patch).toHaveBeenCalledWith(
      expect.stringContaining("/items/pyq_question/q1/review"),
      expect.objectContaining({ reviewer_status: "rejected" }),
    ),
  );
});

test("Needs correction button calls status change API", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-q1"));
  fireEvent.click(screen.getByTestId("question-list-item-q1"));
  await waitFor(() => screen.getByTestId("btn-needs-correction"));
  fireEvent.click(screen.getByTestId("btn-needs-correction"));
  await waitFor(() =>
    expect(api.patch).toHaveBeenCalledWith(
      expect.stringContaining("/items/pyq_question/q1/review"),
      expect.objectContaining({ reviewer_status: "needs_correction" }),
    ),
  );
});

test("missing indicator shows missing question numbers", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByText(/Missing:/));
  expect(screen.getByText(/Missing:/)).toBeTruthy();
  expect(screen.getByText(/4, 5/)).toBeTruthy();
});

test("Add missing opens modal pre-populated with next missing number", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByText("Add missing"));
  fireEvent.click(screen.getByText("Add missing"));
  await waitFor(() => screen.getByText("Add missing question"));
  const numInput = screen.getAllByRole("spinbutton")[0];
  expect(numInput.value).toBe("4");
});

test("progress bar reflects current state", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByText(/1.*verified/i));
  expect(screen.getByText(/1.*pending/i)).toBeTruthy();
});

test("source_kind manual rows show no PDF document_id → no signed URL fetched", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-q2"));
  fireEvent.click(screen.getByTestId("question-list-item-q2"));
  // Q2 has no source_document_id — signed-pdf should not be called
  await waitFor(() => expect(api.get).not.toHaveBeenCalledWith(
    expect.stringContaining("/signed-pdf"),
  ));
  await waitFor(() => screen.getByText(/Manual entry|no source preview/i));
});

test("auto_extracted question triggers PDF signed URL fetch", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-q1"));
  fireEvent.click(screen.getByTestId("question-list-item-q1"));
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/signed-pdf?document_id=doc-1")),
  );
});

test("Save draft button calls PATCH without changing status", async () => {
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-q1"));
  fireEvent.click(screen.getByTestId("question-list-item-q1"));
  await waitFor(() => screen.getByTestId("btn-save-draft"));
  fireEvent.click(screen.getByTestId("btn-save-draft"));
  await waitFor(() =>
    expect(api.patch).toHaveBeenCalledWith(
      expect.stringContaining("/pyq-questions/q1"),
      expect.objectContaining({ reason: expect.any(String), payload: expect.any(Object) }),
    ),
  );
  // Should NOT call the review endpoint
  expect(api.patch).not.toHaveBeenCalledWith(
    expect.stringContaining("/review"),
    expect.anything(),
  );
});
