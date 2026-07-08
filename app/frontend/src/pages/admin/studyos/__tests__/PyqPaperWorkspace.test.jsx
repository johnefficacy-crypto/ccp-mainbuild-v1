/**
 * Tests for PyqPaperWorkspace — three-pane PYQ reviewer workspace.
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), delete: jest.fn() },
}));

jest.mock("../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { role: "super_admin", permissions: [] } }),
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
    pyq_paper_id: PAPER_ID,
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
    pyq_paper_id: PAPER_ID,
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
    pyq_paper_id: PAPER_ID,
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
  await waitFor(() =>
    expect(screen.getByTestId("editor-question-text").value).toContain("capital of India"),
  );
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
  // Wait for the question list to populate (data loaded)
  await waitFor(() => screen.getByTestId("question-list-item-q1"));
  // Progress bar renders status words — at least one "verified" and "pending" label exists
  const bodyText = document.body.textContent;
  expect(bodyText).toMatch(/verified/i);
  expect(bodyText).toMatch(/pending/i);
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

// ── Deep-link receiving tests (I8-B round-3 + round-4) ───────────────────────

const PAPER_B_ID = "paper-uuid-2";
const PAPER_B = { ...PAPER, id: PAPER_B_ID, paper_code: "GS-II" };

describe("PyqPaperWorkspace deep-link (I8-B)", () => {
  const Q_PAGE2 = {
    id: "q-page2",
    question_number: 99,
    question_text: "Page-2 question text",
    reviewer_status: "pending",
    source_kind: "auto_extracted",
    source_document_id: "doc-2",
    source_page: 7,
    confidence_by_field: {},
    content_hash: "xyz999",
    metadata: {},
    pyq_paper_id: PAPER_ID,  // same paper — valid fetch
  };

  const Q_WRONG_PAPER = {
    id: "q-wrong-paper",
    question_number: 1,
    question_text: "Question from another paper",
    reviewer_status: "pending",
    source_kind: "auto_extracted",
    source_document_id: null,
    source_page: null,
    confidence_by_field: {},
    content_hash: "cross-paper",
    metadata: {},
    pyq_paper_id: "some-other-paper-id",  // different paper — should reject
  };

  function renderEmbedded(extraProps = {}, paperId = PAPER_ID) {
    return render(
      <MemoryRouter initialEntries={["/"]}>
        <PyqPaperWorkspace paperId={paperId} embedded {...extraProps} />
      </MemoryRouter>,
    );
  }

  function setupDeepLinkMocks() {
    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`)) return Promise.resolve(PAPER);
      if (url.includes(`/pyq-papers/${PAPER_B_ID}`)) return Promise.resolve(PAPER_B);
      if (url.includes(`pyq_paper_id=${PAPER_B_ID}`)) return Promise.resolve({ items: [], total: 0 });
      if (url.includes("pyq_paper_id=") && url.includes("reviewer_status=rejected"))
        return Promise.resolve({ items: [], total: 0 });
      if (url.includes("/pyq-questions?")) return Promise.resolve({ items: QUESTIONS, total: 3 });
      if (url.includes(`/progress`)) return Promise.resolve(PROGRESS);
      if (url.includes("/pyq-options?")) return Promise.resolve({ items: OPTIONS });
      if (url.includes("/pyq-questions/q-page2")) return Promise.resolve(Q_PAGE2);
      if (url.includes("/pyq-questions/q-wrong-paper")) return Promise.resolve(Q_WRONG_PAPER);
      if (url.includes("/pyq-questions/invalid-row")) return Promise.reject(new Error("Not found"));
      if (url.includes("/pyq-questions/q1")) return Promise.resolve({ ...QUESTIONS[0], pyq_paper_id: PAPER_ID });
      if (url.includes("/pyq-questions/q2")) return Promise.resolve({ ...QUESTIONS[1], pyq_paper_id: PAPER_ID });
      return Promise.resolve({});
    });
  }

  beforeEach(() => {
    jest.clearAllMocks();
    setupDeepLinkMocks();
  });

  test("question beyond page 1: fetches by ID and auto-selects", async () => {
    renderEmbedded({ rowId: "q-page2" });
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/pyq-questions/q-page2")),
    );
    await waitFor(() =>
      expect(screen.getByTestId("editor-question-text").value).toContain("Page-2 question"),
    );
  });

  test("status prop initializes statusFilter and is sent to API", async () => {
    renderEmbedded({ status: "pending" });
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("reviewer_status=pending")),
    );
  });

  test("rowId change without remount re-applies deep link to new question", async () => {
    const { rerender } = renderEmbedded({ rowId: "q1" });
    await waitFor(() =>
      expect(screen.getByTestId("editor-question-text").value).toContain("capital of India"),
    );

    rerender(
      <MemoryRouter initialEntries={["/"]}>
        <PyqPaperWorkspace paperId={PAPER_ID} embedded rowId="q2" />
      </MemoryRouter>,
    );
    await waitFor(() => {
      const ta = screen.getByTestId("editor-question-text");
      expect(ta.value).toContain("first PM of India");
    });
  });

  test("invalid rowId shows not-found banner and does not select anything", async () => {
    renderEmbedded({ rowId: "invalid-row" });
    await waitFor(() => screen.getByTestId("pyq-deep-link-not-found"));
    expect(screen.queryByTestId("editor-question-text")).toBeNull();
  });

  // ── Round-4 additions ─────────────────────────────────────────────────────

  test("paper change without remount clears stale question selection", async () => {
    const { rerender } = renderEmbedded({ rowId: "q1" });
    await waitFor(() =>
      expect(screen.getByTestId("editor-question-text").value).toContain("capital of India"),
    );

    // Switch to a different paper (paper B returns no questions)
    rerender(
      <MemoryRouter initialEntries={["/"]}>
        <PyqPaperWorkspace paperId={PAPER_B_ID} embedded />
      </MemoryRouter>,
    );
    // Stale question editor must be gone
    await waitFor(() => expect(screen.queryByTestId("editor-question-text")).toBeNull());
  });

  test("status prop change without remount resets selection and sends new filter", async () => {
    const { rerender } = renderEmbedded({ rowId: "q1", status: null });
    await waitFor(() => screen.getByTestId("editor-question-text"));

    // Change status prop to "rejected" (mock returns empty list for rejected filter)
    rerender(
      <MemoryRouter initialEntries={["/"]}>
        <PyqPaperWorkspace paperId={PAPER_ID} embedded status="rejected" />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.queryByTestId("editor-question-text")).toBeNull());
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("reviewer_status=rejected")),
    );
  });

  test("cross-paper fetchQuestionById result shows not-found banner", async () => {
    // q-wrong-paper is returned by the API but belongs to a different paper
    renderEmbedded({ rowId: "q-wrong-paper" });
    await waitFor(() => screen.getByTestId("pyq-deep-link-not-found"));
    expect(screen.queryByTestId("editor-question-text")).toBeNull();
  });

  // ── Round-5: request-race safety ──────────────────────────────────────────

  test("stale paper-A question response does not overwrite paper-B state after rapid switch", async () => {
    let resolveStaleQuestions;
    const staleQuestionsP = new Promise((res) => { resolveStaleQuestions = res; });

    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER);
      if (url.includes(`/pyq-papers/${PAPER_B_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER_B);
      if (url.includes("/pyq-questions?") && url.includes(`pyq_paper_id=${PAPER_ID}`))
        return staleQuestionsP;
      if (url.includes("/pyq-questions?") && url.includes(`pyq_paper_id=${PAPER_B_ID}`))
        return Promise.resolve({ items: [], total: 0 });
      if (url.includes("/progress")) return Promise.resolve(PROGRESS);
      if (url.includes("/pyq-options?")) return Promise.resolve({ items: OPTIONS });
      return Promise.resolve({});
    });

    const { rerender } = render(
      <MemoryRouter><PyqPaperWorkspace paperId={PAPER_ID} embedded /></MemoryRouter>,
    );
    // Switch to paper B before paper A's questions resolve
    rerender(
      <MemoryRouter><PyqPaperWorkspace paperId={PAPER_B_ID} embedded /></MemoryRouter>,
    );
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining(`pyq_paper_id=${PAPER_B_ID}`)),
    );
    // Resolve the stale paper A response — it must be discarded by the gen guard
    await act(async () => { resolveStaleQuestions({ items: QUESTIONS, total: 3 }); });
    expect(screen.queryByTestId("question-list-item-q1")).toBeNull();
    expect(screen.queryByTestId("question-list-item-q2")).toBeNull();
  });

  test("stale status-filter question response does not overwrite new filter state after rapid switch", async () => {
    let resolveStaleVerified;
    const staleVerifiedP = new Promise((res) => { resolveStaleVerified = res; });

    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER);
      if (url.includes("/pyq-questions?") && url.includes("reviewer_status=verified"))
        return staleVerifiedP;
      if (url.includes("/pyq-questions?") && url.includes("reviewer_status=pending"))
        return Promise.resolve({ items: [], total: 0 });
      if (url.includes("/pyq-questions?"))
        return Promise.resolve({ items: QUESTIONS, total: 3 });
      if (url.includes("/progress")) return Promise.resolve(PROGRESS);
      if (url.includes("/pyq-options?")) return Promise.resolve({ items: OPTIONS });
      return Promise.resolve({});
    });

    const { rerender } = render(
      <MemoryRouter><PyqPaperWorkspace paperId={PAPER_ID} embedded status="verified" /></MemoryRouter>,
    );
    // Switch to pending before verified response resolves
    rerender(
      <MemoryRouter><PyqPaperWorkspace paperId={PAPER_ID} embedded status="pending" /></MemoryRouter>,
    );
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("reviewer_status=pending")),
    );
    // Resolve the stale verified response — it must be discarded by the gen guard
    await act(async () => { resolveStaleVerified({ items: QUESTIONS, total: 3 }); });
    expect(screen.queryByTestId("question-list-item-q1")).toBeNull();
    expect(screen.queryByTestId("question-list-item-q2")).toBeNull();
  });

  // ── Round-6: same-generation query races + option race ───────────────────

  test("stale paper-A page-2 question response does not overwrite paper-B page-1 state", async () => {
    let resolveStalePage2;
    const stalePage2P = new Promise((res) => { resolveStalePage2 = res; });

    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER);
      if (url.includes(`/pyq-papers/${PAPER_B_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER_B);
      // Paper A page 1 (offset=0)
      if (url.includes(`pyq_paper_id=${PAPER_ID}`) && !url.includes("offset=50"))
        return Promise.resolve({ items: QUESTIONS, total: 53 });
      // Paper A page 2 (offset=50) — stale
      if (url.includes(`pyq_paper_id=${PAPER_ID}`) && url.includes("offset=50"))
        return stalePage2P;
      // Paper B — always empty
      if (url.includes(`pyq_paper_id=${PAPER_B_ID}`))
        return Promise.resolve({ items: [], total: 0 });
      if (url.includes("/progress")) return Promise.resolve(PROGRESS);
      if (url.includes("/pyq-options?")) return Promise.resolve({ items: OPTIONS });
      return Promise.resolve({});
    });

    const { rerender } = renderEmbedded({});
    await waitFor(() => screen.getByTestId("question-list-item-q1"));

    // Navigate to page 2 of paper A — stale promise starts
    fireEvent.click(screen.getByTestId("pagination-next"));
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("offset=50")),
    );

    // Switch to paper B before page-2 resolves
    rerender(
      <MemoryRouter initialEntries={["/"]}>
        <PyqPaperWorkspace paperId={PAPER_B_ID} embedded />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining(`pyq_paper_id=${PAPER_B_ID}`)),
    );

    // Resolve the stale page-2 response — must be discarded
    await act(async () => { resolveStalePage2({ items: QUESTIONS, total: 53 }); });
    expect(screen.queryByTestId("question-list-item-q1")).toBeNull();
    expect(screen.queryByTestId("question-list-item-q2")).toBeNull();
  });

  test("stale local-filter question response does not overwrite new filter state", async () => {
    let resolveStalePending;
    const stalePendingP = new Promise((res) => { resolveStalePending = res; });

    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER);
      // initial "all" filter — immediate
      if (url.includes("/pyq-questions?") && !url.includes("reviewer_status="))
        return Promise.resolve({ items: QUESTIONS, total: 3 });
      // "pending" filter — stale
      if (url.includes("/pyq-questions?") && url.includes("reviewer_status=pending"))
        return stalePendingP;
      // "verified" filter — immediate empty (new state)
      if (url.includes("/pyq-questions?") && url.includes("reviewer_status=verified"))
        return Promise.resolve({ items: [], total: 0 });
      if (url.includes("/progress")) return Promise.resolve(PROGRESS);
      if (url.includes("/pyq-options?")) return Promise.resolve({ items: OPTIONS });
      return Promise.resolve({});
    });

    renderEmbedded({});
    await waitFor(() => screen.getByTestId("question-list-item-q1"));

    // Change local filter to "pending" — stale request starts
    const statusSelect = screen.getAllByRole("combobox")[0];
    fireEvent.change(statusSelect, { target: { value: "pending" } });
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("reviewer_status=pending")),
    );

    // Change to "verified" before pending resolves
    fireEvent.change(statusSelect, { target: { value: "verified" } });
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("reviewer_status=verified")),
    );

    // Resolve the stale pending response — must be discarded
    await act(async () => { resolveStalePending({ items: QUESTIONS, total: 3 }); });
    expect(screen.queryByTestId("question-list-item-q1")).toBeNull();
    expect(screen.queryByTestId("question-list-item-q2")).toBeNull();
  });

  test("stale loadOptions response does not overwrite options for a new question selection", async () => {
    const Q2_OPTIONS = [
      { id: "o3", question_id: "q2", option_label: "A", option_text: "Nehru", is_correct: true },
    ];
    let resolveStaleQ1Options;
    const staleQ1OptionsP = new Promise((res) => { resolveStaleQ1Options = res; });

    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER);
      if (url.includes("/pyq-questions?")) return Promise.resolve({ items: QUESTIONS, total: 3 });
      if (url.includes("/progress")) return Promise.resolve(PROGRESS);
      if (url.includes("/pyq-options?") && url.includes("question_id=q1")) return staleQ1OptionsP;
      if (url.includes("/pyq-options?") && url.includes("question_id=q2"))
        return Promise.resolve({ items: Q2_OPTIONS });
      return Promise.resolve({});
    });

    renderEmbedded({});
    await waitFor(() => screen.getByTestId("question-list-item-q1"));

    // Select q1 — starts stale options load
    fireEvent.click(screen.getByTestId("question-list-item-q1"));
    // Immediately select q2 — starts immediate options load
    fireEvent.click(screen.getByTestId("question-list-item-q2"));

    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("question_id=q2")),
    );

    // Resolve stale q1 options — must be discarded
    await act(async () => { resolveStaleQ1Options({ items: OPTIONS }); });

    // "Delhi" and "Mumbai" (q1 options) must not appear in q2's editor
    expect(screen.queryByDisplayValue("Delhi")).toBeNull();
    expect(screen.queryByDisplayValue("Mumbai")).toBeNull();
  });

  // ── Round-7: manual-refresh token races + optionsGenRef invalidation ──────

  test("stale save-refresh does not overwrite review-refresh question list after Verify", async () => {
    // handleVerify: saveDraft (calls onSaved without await) → doReview (calls onStatusChange
    // without await). Both handleSaved and handleStatusChange call loadQuestions concurrently.
    // The save-refresh (stale) must be discarded; the review-refresh (new) must win.
    let resolveSaveRefresh;
    const saveRefreshP = new Promise((res) => { resolveSaveRefresh = res; });
    let questionsGetCount = 0;

    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER);
      if (url.includes("/pyq-questions?")) {
        questionsGetCount += 1;
        if (questionsGetCount === 1) return Promise.resolve({ items: QUESTIONS, total: 3 }); // initial
        if (questionsGetCount === 2) return saveRefreshP;  // save-refresh (stale)
        // review-refresh: q1 now verified, q2/q3 absent
        return Promise.resolve({
          items: [{ ...QUESTIONS[0], reviewer_status: "verified" }],
          total: 1,
        });
      }
      if (url.includes("/progress")) return Promise.resolve(PROGRESS);
      if (url.includes("/pyq-options?")) return Promise.resolve({ items: OPTIONS });
      return Promise.resolve({});
    });
    api.patch.mockResolvedValue({ ok: true });

    renderEmbedded({});
    await waitFor(() => screen.getByTestId("question-list-item-q1"));

    // Select q1 then click Verify — triggers both save-refresh and review-refresh
    fireEvent.click(screen.getByTestId("question-list-item-q1"));
    await waitFor(() => screen.getByTestId("btn-verify"));
    fireEvent.click(screen.getByTestId("btn-verify"));

    // Wait until the review-refresh wins and q2/q3 are gone
    await waitFor(() => expect(screen.queryByTestId("question-list-item-q2")).toBeNull());

    // Resolve the stale save-refresh — q2 and q3 must not reappear
    await act(async () => { resolveSaveRefresh({ items: QUESTIONS, total: 3 }); });
    expect(screen.queryByTestId("question-list-item-q2")).toBeNull();
    expect(screen.queryByTestId("question-list-item-q3")).toBeNull();
  });

  test("stale loadOptions from paper A does not populate options after switching to paper B", async () => {
    const QB1_OPTIONS = [
      { id: "o-b1", question_id: "q-b1", option_label: "A", option_text: "Wellington", is_correct: false },
    ];
    const Q_B1 = {
      id: "q-b1",
      question_number: 1,
      question_text: "First question of paper B",
      reviewer_status: "pending",
      source_kind: "manual",
      source_document_id: null,
      source_page: null,
      confidence_by_field: {},
      content_hash: "qb1hash",
      metadata: {},
      pyq_paper_id: PAPER_B_ID,
    };
    let resolveStaleQ1Options;
    const staleQ1OptionsP = new Promise((res) => { resolveStaleQ1Options = res; });

    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER);
      if (url.includes(`/pyq-papers/${PAPER_B_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER_B);
      if (url.includes(`pyq_paper_id=${PAPER_ID}`))
        return Promise.resolve({ items: QUESTIONS, total: 3 });
      if (url.includes(`pyq_paper_id=${PAPER_B_ID}`))
        return Promise.resolve({ items: [Q_B1], total: 1 });
      if (url.includes("/progress")) return Promise.resolve(PROGRESS);
      if (url.includes("/pyq-options?") && url.includes("question_id=q1")) return staleQ1OptionsP;
      if (url.includes("/pyq-options?") && url.includes("question_id=q-b1"))
        return Promise.resolve({ items: QB1_OPTIONS });
      return Promise.resolve({});
    });

    const { rerender } = renderEmbedded({});
    await waitFor(() => screen.getByTestId("question-list-item-q1"));

    // Select q1 on paper A — stale options start loading
    fireEvent.click(screen.getByTestId("question-list-item-q1"));
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("question_id=q1")),
    );

    // Switch to paper B before q1 options resolve — paper reset increments optionsGenRef
    rerender(
      <MemoryRouter initialEntries={["/"]}>
        <PyqPaperWorkspace paperId={PAPER_B_ID} embedded />
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByTestId("question-list-item-q-b1"));

    // Select q-b1 on paper B — immediate options (Wellington)
    fireEvent.click(screen.getByTestId("question-list-item-q-b1"));
    // Wait until Wellington is actually rendered before resolving the stale promise
    await waitFor(() => screen.getByDisplayValue("Wellington"));

    // Resolve stale q1 options — must be discarded; Wellington must remain visible
    await act(async () => { resolveStaleQ1Options({ items: OPTIONS }); });
    expect(screen.queryByDisplayValue("Delhi")).toBeNull();
    expect(screen.queryByDisplayValue("Mumbai")).toBeNull();
    expect(screen.getByDisplayValue("Wellington")).toBeTruthy();
  });

  // ── Round-8: progressGenRef per-call guard ────────────────────────────────

  test("stale save-triggered progress does not overwrite review-triggered progress after Verify", async () => {
    // Verify: saveDraft → handleSaved calls loadProgress (stale, deferred)
    //         doReview  → handleStatusChange calls loadProgress (new, immediate)
    // The stale save-progress must be discarded; the review-progress must win.
    const PROGRESS_REVIEWED = {
      ...PROGRESS,
      by_status: { pending: 0, verified: 2, rejected: 1 },
    };
    let resolveSaveProgress;
    const saveProgressP = new Promise((res) => { resolveSaveProgress = res; });
    let progressCallCount = 0;

    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER);
      if (url.includes("/pyq-questions?"))
        return Promise.resolve({ items: QUESTIONS, total: 3 });
      if (url.includes("/progress")) {
        progressCallCount += 1;
        if (progressCallCount === 1) return Promise.resolve(PROGRESS);     // initial
        if (progressCallCount === 2) return saveProgressP;                 // save-refresh (stale)
        return Promise.resolve(PROGRESS_REVIEWED);                         // review-refresh (new)
      }
      if (url.includes("/pyq-options?")) return Promise.resolve({ items: OPTIONS });
      return Promise.resolve({});
    });
    api.patch.mockResolvedValue({ ok: true });

    renderEmbedded({});
    await waitFor(() => screen.getByTestId("question-list-item-q1"));

    // Select q1 and click Verify — triggers save-refresh (stale) then review-refresh (new)
    fireEvent.click(screen.getByTestId("question-list-item-q1"));
    await waitFor(() => screen.getByTestId("btn-verify"));
    fireEvent.click(screen.getByTestId("btn-verify"));

    // Wait until the review-refresh progress is rendered (2 verified)
    await waitFor(() => expect(document.body.textContent).toContain("2 verified"));

    // Resolve the stale save-progress — the UI must not revert to 1 verified
    await act(async () => { resolveSaveProgress(PROGRESS); });
    expect(document.body.textContent).toContain("2 verified");
  });

  test("stale progress from old paper does not overwrite new paper progress after switch", async () => {
    const PROGRESS_B = {
      paper_id: PAPER_B_ID,
      total_expected: 10,
      present: 2,
      missing: [],
      by_status: { pending: 2, verified: 0, rejected: 0 },
    };
    let resolveStalePaperAProgress;
    const stalePaperAProgressP = new Promise((res) => { resolveStalePaperAProgress = res; });

    api.get.mockImplementation((url) => {
      if (url.includes(`/pyq-papers/${PAPER_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER);
      if (url.includes(`/pyq-papers/${PAPER_B_ID}`) && !url.includes("questions") && !url.includes("progress"))
        return Promise.resolve(PAPER_B);
      if (url.includes(`pyq_paper_id=${PAPER_ID}`)) return Promise.resolve({ items: QUESTIONS, total: 3 });
      if (url.includes(`pyq_paper_id=${PAPER_B_ID}`)) return Promise.resolve({ items: [], total: 0 });
      if (url.includes(`${PAPER_ID}/progress`)) return stalePaperAProgressP;
      if (url.includes(`${PAPER_B_ID}/progress`)) return Promise.resolve(PROGRESS_B);
      if (url.includes("/pyq-options?")) return Promise.resolve({ items: [] });
      return Promise.resolve({});
    });

    const { rerender } = renderEmbedded({});
    // Confirm paper A's progress request has fired (it will remain pending)
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining(`${PAPER_ID}/progress`)),
    );

    // Switch to paper B before paper A's progress resolves
    rerender(
      <MemoryRouter initialEntries={["/"]}>
        <PyqPaperWorkspace paperId={PAPER_B_ID} embedded />
      </MemoryRouter>,
    );
    // Wait for paper B's progress to render (10 total expected)
    await waitFor(() => expect(document.body.textContent).toContain("/ 10 expected"));

    // Resolve the stale paper A progress — must be discarded; paper B counts must remain
    await act(async () => { resolveStalePaperAProgress(PROGRESS); });
    expect(document.body.textContent).toContain("/ 10 expected");
  });
});

// ── PR-3: section assignment + passage/stimulus grouping (migration 223) ──────

describe("PyqPaperWorkspace PR-3 sections + stimuli", () => {
  const PAPER_PR3 = { ...PAPER, exam_phase_id: "phase-1", exam_id: "exam-1" };
  const SECTIONS = [
    { id: "sec-1", exam_phase_id: "phase-1", section_label: "General Awareness" },
    { id: "sec-2", exam_phase_id: "phase-1", section_label: "Quantitative Aptitude" },
  ];
  const STIMULI = [
    {
      id: "stim-1",
      pyq_paper_id: PAPER_ID,
      section_id: "sec-1",
      stimulus_type: "passage",
      content_text: "Read the following passage about the rivers of India.",
      reviewer_status: "pending",
      display_order: 1,
    },
  ];
  const LINKS = [
    { id: "link-1", question_id: "q1", stimulus_id: "stim-1", reviewer_status: "pending", display_order: 1 },
  ];

  function baseGet(url, overrides = {}) {
    if (url.includes("/progress")) return Promise.resolve(PROGRESS);
    if (url.includes("/signed-pdf")) return Promise.resolve({ signed_url: "https://example.com/doc.pdf" });
    if (url.includes("/exam-phase-sections")) return overrides.sections || Promise.resolve({ items: SECTIONS, total: 2 });
    if (url.includes("/pyq-question-stimuli")) return Promise.resolve({ items: LINKS, total: LINKS.length });
    if (url.includes("/pyq-stimuli")) return overrides.stimuli || Promise.resolve({ items: STIMULI, total: STIMULI.length });
    if (url.includes("/pyq-options?")) return Promise.resolve({ items: OPTIONS });
    if (url.includes("/pyq-questions?")) return Promise.resolve({ items: QUESTIONS, total: 3 });
    if (url.includes("/pyq-papers/")) return Promise.resolve(PAPER_PR3);
    if (url.includes("/dup-check")) return Promise.resolve({ matches: [] });
    return Promise.resolve({});
  }

  function setupPr3Mocks(overrides = {}) {
    api.get.mockImplementation((url) => baseGet(url, overrides));
    api.post.mockResolvedValue({ ok: true, row: { id: "new-stim" } });
    api.patch.mockResolvedValue({ ok: true, row: {} });
    api.delete.mockResolvedValue({ ok: true });
  }

  function renderPr3() {
    return render(
      <MemoryRouter initialEntries={["/"]}>
        <PyqPaperWorkspace paperId={PAPER_ID} embedded />
      </MemoryRouter>,
    );
  }

  beforeEach(() => {
    jest.clearAllMocks();
    setupPr3Mocks();
  });

  test("section dropdown loads the paper's phase sections and renders them in the editor", async () => {
    renderPr3();
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/exam-phase-sections?exam_phase_id=phase-1")),
    );
    fireEvent.click(screen.getByTestId("question-list-item-q1"));
    await waitFor(() => screen.getByTestId("editor-question-section"));
    const select = screen.getByTestId("editor-question-section");
    expect(select.textContent).toContain("General Awareness");
    expect(select.textContent).toContain("Quantitative Aptitude");
  });

  test("assigning a section saves via PATCH /pyq-questions with section_id", async () => {
    renderPr3();
    await waitFor(() => screen.getByTestId("question-list-item-q1"));
    fireEvent.click(screen.getByTestId("question-list-item-q1"));
    await waitFor(() => screen.getByTestId("editor-question-section"));
    fireEvent.change(screen.getByTestId("editor-question-section"), { target: { value: "sec-1" } });
    fireEvent.click(screen.getByTestId("btn-save-draft"));
    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-questions/q1"),
        expect.objectContaining({ payload: expect.objectContaining({ section_id: "sec-1" }) }),
      ),
    );
  });

  test("stimuli panel lists stimuli for the paper after expanding", async () => {
    renderPr3();
    await waitFor(() => screen.getByTestId("pyq-stimuli-panel-toggle"));
    fireEvent.click(screen.getByTestId("pyq-stimuli-panel-toggle"));
    await waitFor(() => screen.getByTestId("stimulus-row-stim-1"));
    expect(screen.getByTestId("stimulus-row-stim-1").textContent).toContain("rivers of India");
    // section label resolves from section_id
    expect(screen.getByTestId("stimulus-section-stim-1").textContent).toContain("General Awareness");
  });

  test("stimulus verify button calls the review router PATCH /items/pyq_stimulus/{id}/review", async () => {
    renderPr3();
    await waitFor(() => screen.getByTestId("pyq-stimuli-panel-toggle"));
    fireEvent.click(screen.getByTestId("pyq-stimuli-panel-toggle"));
    await waitFor(() => screen.getByTestId("stimulus-verify-stim-1"));
    fireEvent.click(screen.getByTestId("stimulus-verify-stim-1"));
    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith(
        expect.stringContaining("/items/pyq_stimulus/stim-1/review"),
        expect.objectContaining({ reviewer_status: "verified" }),
      ),
    );
  });

  test("creating a stimulus posts to /pyq-stimuli with the paper id", async () => {
    renderPr3();
    await waitFor(() => screen.getByTestId("pyq-stimuli-panel-toggle"));
    fireEvent.click(screen.getByTestId("pyq-stimuli-panel-toggle"));
    await waitFor(() => screen.getByTestId("stimulus-create-open"));
    fireEvent.click(screen.getByTestId("stimulus-create-open"));
    fireEvent.change(screen.getByTestId("stimulus-create-content"), { target: { value: "New passage text" } });
    fireEvent.click(screen.getByTestId("stimulus-create-submit"));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/pyq-stimuli"),
        expect.objectContaining({
          payload: expect.objectContaining({ pyq_paper_id: PAPER_ID, stimulus_type: "passage", content_text: "New passage text" }),
        }),
      ),
    );
  });

  test("create-stimulus type dropdown offers only PR-3 text types (no PR-11 media types)", async () => {
    renderPr3();
    await waitFor(() => screen.getByTestId("pyq-stimuli-panel-toggle"));
    fireEvent.click(screen.getByTestId("pyq-stimuli-panel-toggle"));
    await waitFor(() => screen.getByTestId("stimulus-create-open"));
    fireEvent.click(screen.getByTestId("stimulus-create-open"));
    const select = screen.getByTestId("stimulus-create-type");
    const values = Array.from(select.querySelectorAll("option")).map((o) => o.value);
    expect(values).toEqual(["passage", "caselet", "table"]);
    expect(values).not.toContain("image");
    expect(values).not.toContain("chart");
    expect(values).not.toContain("diagram");
  });

  test("linked-stimuli list renders for the selected question", async () => {
    renderPr3();
    await waitFor(() => screen.getByTestId("question-list-item-q1"));
    fireEvent.click(screen.getByTestId("question-list-item-q1"));
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/pyq-question-stimuli?question_id=q1")),
    );
    await waitFor(() => screen.getByTestId("question-link-link-1"));
  });

  test("per-link verify calls PATCH /items/pyq_question_stimulus/{id}/review", async () => {
    renderPr3();
    await waitFor(() => screen.getByTestId("question-list-item-q1"));
    fireEvent.click(screen.getByTestId("question-list-item-q1"));
    await waitFor(() => screen.getByTestId("link-verify-link-1"));
    fireEvent.click(screen.getByTestId("link-verify-link-1"));
    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith(
        expect.stringContaining("/items/pyq_question_stimulus/link-1/review"),
        expect.objectContaining({ reviewer_status: "verified" }),
      ),
    );
  });

  test("stimuli panel shows empty state when there are none", async () => {
    setupPr3Mocks({ stimuli: Promise.resolve({ items: [], total: 0 }) });
    renderPr3();
    await waitFor(() => screen.getByTestId("pyq-stimuli-panel-toggle"));
    fireEvent.click(screen.getByTestId("pyq-stimuli-panel-toggle"));
    await waitFor(() => screen.getByTestId("pyq-stimuli-empty"));
  });

  test("stimuli panel shows loading state while the fetch is pending", async () => {
    setupPr3Mocks({ stimuli: new Promise(() => {}) }); // never resolves
    renderPr3();
    await waitFor(() => screen.getByTestId("pyq-stimuli-panel-toggle"));
    fireEvent.click(screen.getByTestId("pyq-stimuli-panel-toggle"));
    await waitFor(() => screen.getByTestId("pyq-stimuli-loading"));
  });

  test("stimuli panel shows error state when the fetch fails", async () => {
    setupPr3Mocks({ stimuli: Promise.reject(new Error("boom")) });
    renderPr3();
    await waitFor(() => screen.getByTestId("pyq-stimuli-panel-toggle"));
    fireEvent.click(screen.getByTestId("pyq-stimuli-panel-toggle"));
    await waitFor(() => screen.getByTestId("pyq-stimuli-error"));
  });
});
