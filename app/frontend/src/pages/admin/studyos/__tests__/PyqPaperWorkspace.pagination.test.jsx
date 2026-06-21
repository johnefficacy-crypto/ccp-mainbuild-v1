/**
 * Server-side pagination + filter tests for PyqPaperWorkspace.
 *
 * Acceptance criteria (M3 fix):
 *   - No limit=200 in any API call.
 *   - reviewer_status filter is sent as a server param, not applied client-side.
 *   - offset resets to 0 on filter change.
 *   - total count from server response is rendered.
 *   - pagination controls (prev/next) advance and retract the offset.
 *   - After a review status action, questions are refetched from server.
 *
 * Note: this repo's CRA setup has no @testing-library/jest-dom — assertions
 * use plain Jest matchers only (getBy* throws on missing, toBeTruthy, etc.).
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

const PAPER_ID = "paper-pg-1";
const PAPER = {
  id: PAPER_ID,
  year: 2026,
  paper_code: "GS-I",
  exam_id: "exam-1",
  metadata: {},
};

function makeQuestions(n, startAt = 1) {
  return Array.from({ length: n }, (_, i) => ({
    id: `q${startAt + i}`,
    question_number: startAt + i,
    question_text: `Question ${startAt + i}`,
    reviewer_status: "pending",
    source_kind: "auto_extracted",
    source_document_id: null,
    confidence_by_field: null,
    metadata: {},
  }));
}

const PAGE_1_QUESTIONS = makeQuestions(50);
const PAGE_2_QUESTIONS = makeQuestions(10, 51);

const PROGRESS = {
  total_expected: 60,
  present: 60,
  missing: [],
  by_status: { pending: 60 },
};

// ── Render helper ─────────────────────────────────────────────────────────────

function renderWorkspace() {
  return render(
    <MemoryRouter initialEntries={[`/ws/${PAPER_ID}`]}>
      <Routes>
        <Route path="/ws/:pyq_paper_id" element={<PyqPaperWorkspace />} />
        <Route path="/admin/exam-intelligence" element={<div>home</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

// Tracks which offset the caller has "set" so the mock can respond with the
// right page. The real component manages offset in state; here we track the
// last call's offset param to return the correct fixture.
function buildGetMock({ total = 60 } = {}) {
  return (url) => {
    if (url.includes("/progress")) return Promise.resolve(PROGRESS);
    if (url.includes("/pyq-options?")) return Promise.resolve({ items: [] });
    if (url.includes("/pyq-questions?")) {
      const match = url.match(/[?&]offset=(\d+)/);
      const off = match ? parseInt(match[1], 10) : 0;
      const items = off >= 50 ? PAGE_2_QUESTIONS : PAGE_1_QUESTIONS;
      return Promise.resolve({ items, total });
    }
    if (url.includes(`/pyq-papers/${PAPER_ID}`)) return Promise.resolve(PAPER);
    return Promise.resolve({});
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  api.patch.mockResolvedValue({ ok: true });
  api.post.mockResolvedValue({ ok: true, question: { id: "new-q", question_number: 61 } });
});

// ── Tests ─────────────────────────────────────────────────────────────────────

test("initial fetch uses limit=50 and offset=0, never limit=200", async () => {
  api.get.mockImplementation(buildGetMock());
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-pane"));
  const allUrls = api.get.mock.calls.map(([url]) => url);
  const hasLimit50 = allUrls.some((u) => u.includes("limit=50"));
  const hasOffset0 = allUrls.some((u) => u.includes("offset=0"));
  const hasLimit200 = allUrls.some((u) => u.includes("limit=200"));
  expect(hasLimit50).toBe(true);
  expect(hasOffset0).toBe(true);
  expect(hasLimit200).toBe(false);
});

test("server total is shown in the list header", async () => {
  api.get.mockImplementation(buildGetMock({ total: 60 }));
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-total"));
  expect(screen.getByTestId("question-list-total").textContent).toContain("60");
});

test("pagination controls render on initial load", async () => {
  api.get.mockImplementation(buildGetMock());
  renderWorkspace();
  await waitFor(() => screen.getByTestId("pagination-controls"));
  expect(screen.getByTestId("pagination-prev")).toBeTruthy();
  expect(screen.getByTestId("pagination-next")).toBeTruthy();
  expect(screen.getByTestId("pagination-range")).toBeTruthy();
});

test("prev button is disabled on first page (offset=0)", async () => {
  api.get.mockImplementation(buildGetMock());
  renderWorkspace();
  await waitFor(() => screen.getByTestId("pagination-prev"));
  expect(screen.getByTestId("pagination-prev").disabled).toBe(true);
});

test("next button is enabled when total > page_size", async () => {
  api.get.mockImplementation(buildGetMock({ total: 60 }));
  renderWorkspace();
  await waitFor(() => screen.getByTestId("pagination-next"));
  // total=60, offset=0, page_size=50 → offset+50 < 60 → next enabled
  expect(screen.getByTestId("pagination-next").disabled).toBe(false);
});

test("next button advances offset and fetches with offset=50", async () => {
  api.get.mockImplementation(buildGetMock({ total: 60 }));
  renderWorkspace();
  await waitFor(() => screen.getByTestId("pagination-next"));

  await act(async () => {
    fireEvent.click(screen.getByTestId("pagination-next"));
  });

  await waitFor(() => {
    const calls = api.get.mock.calls.map(([url]) => url);
    expect(calls.some((u) => u.includes("offset=50"))).toBe(true);
  });
});

test("prev button after advancing restores offset=0 fetch", async () => {
  api.get.mockImplementation(buildGetMock({ total: 60 }));
  renderWorkspace();
  await waitFor(() => screen.getByTestId("pagination-next"));

  await act(async () => {
    fireEvent.click(screen.getByTestId("pagination-next"));
  });
  await waitFor(() => {
    expect(api.get.mock.calls.some(([u]) => u.includes("offset=50"))).toBe(true);
  });

  await act(async () => {
    fireEvent.click(screen.getByTestId("pagination-prev"));
  });
  await waitFor(() => {
    const calls = api.get.mock.calls.map(([url]) => url);
    // A new call with offset=0 after we went to offset=50
    const backCalls = calls.filter(
      (u) => u.includes("/pyq-questions?") && u.includes("offset=0"),
    );
    expect(backCalls.length).toBeGreaterThanOrEqual(2);
  });
});

test("reviewer_status filter sends server query param", async () => {
  api.get.mockImplementation(buildGetMock());
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-pane"));

  // First combobox is the status filter (value="all" initially)
  const allSelects = screen.getAllByRole("combobox");
  const statusSelect = allSelects.find((el) => el.value === "all");
  expect(statusSelect).toBeTruthy();

  await act(async () => {
    fireEvent.change(statusSelect, { target: { value: "pending" } });
  });

  await waitFor(() => {
    const calls = api.get.mock.calls.map(([url]) => url);
    expect(
      calls.some((u) => u.includes("reviewer_status=pending")),
    ).toBe(true);
  });
});

test("offset resets to 0 when status filter changes from page 2", async () => {
  api.get.mockImplementation(buildGetMock({ total: 60 }));
  renderWorkspace();
  await waitFor(() => screen.getByTestId("pagination-next"));

  // Go to page 2
  await act(async () => {
    fireEvent.click(screen.getByTestId("pagination-next"));
  });
  await waitFor(() => {
    expect(api.get.mock.calls.some(([u]) => u.includes("offset=50"))).toBe(true);
  });

  // Change filter — must reset offset to 0
  const allSelects = screen.getAllByRole("combobox");
  const statusSelect = allSelects.find((el) => el.value === "all");
  await act(async () => {
    fireEvent.change(statusSelect, { target: { value: "pending" } });
  });

  await waitFor(() => {
    const calls = api.get.mock.calls.map(([url]) => url);
    const resetCall = calls.find(
      (u) => u.includes("reviewer_status=pending") && u.includes("offset=0"),
    );
    expect(resetCall).toBeDefined();
  });
});

test("after Reject action, questions list is refetched from server", async () => {
  const singleQ = {
    id: "qpend",
    question_number: 1,
    question_text: "A pending question",
    reviewer_status: "pending",
    source_kind: "manual",
    source_document_id: null,
    confidence_by_field: null,
    metadata: {},
  };
  api.get.mockImplementation((url) => {
    if (url.includes("/progress")) return Promise.resolve(PROGRESS);
    if (url.includes("/pyq-options?")) return Promise.resolve({ items: [] });
    if (url.includes("/pyq-questions?"))
      return Promise.resolve({ items: [singleQ], total: 1 });
    if (url.includes(`/pyq-papers/${PAPER_ID}`)) return Promise.resolve(PAPER);
    return Promise.resolve({});
  });

  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-item-qpend"));
  fireEvent.click(screen.getByTestId("question-list-item-qpend"));
  await waitFor(() => screen.getByTestId("btn-reject"));

  const countBefore = api.get.mock.calls.length;
  await act(async () => {
    fireEvent.click(screen.getByTestId("btn-reject"));
  });

  await waitFor(() =>
    expect(api.patch).toHaveBeenCalledWith(
      expect.stringContaining("/items/pyq_question/qpend/review"),
      expect.objectContaining({ reviewer_status: "rejected" }),
    ),
  );
  // A new GET for questions must follow the PATCH
  await waitFor(() => {
    const questionsCalls = api.get.mock.calls.filter(([u]) =>
      u.includes("/pyq-questions?"),
    );
    expect(questionsCalls.length).toBeGreaterThan(
      api.get.mock.calls.slice(0, countBefore).filter(([u]) =>
        u.includes("/pyq-questions?"),
      ).length,
    );
  });
});

test("pagination range label shows 1–50 on first page of 60", async () => {
  api.get.mockImplementation(buildGetMock({ total: 60 }));
  renderWorkspace();
  await waitFor(() => screen.getByTestId("pagination-range"));
  expect(screen.getByTestId("pagination-range").textContent).toMatch(/1[–-]50/);
});

// ── source_kind server-side filter tests ──────────────────────────────────────

test("source_kind filter sends server query param, not client-side filter", async () => {
  api.get.mockImplementation(buildGetMock());
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-pane"));

  // Second combobox is the source_kind filter (value="all" initially)
  const allSelects = screen.getAllByRole("combobox");
  const sourceSelect = allSelects.find(
    (el) => el.value === "all" && el !== allSelects[0],
  ) || allSelects[1];
  expect(sourceSelect).toBeTruthy();

  await act(async () => {
    fireEvent.change(sourceSelect, { target: { value: "auto_extracted" } });
  });

  await waitFor(() => {
    const calls = api.get.mock.calls.map(([url]) => url);
    expect(calls.some((u) => u.includes("source_kind=auto_extracted"))).toBe(true);
  });
});

test("offset resets to 0 when source_kind filter changes from page 2", async () => {
  api.get.mockImplementation(buildGetMock({ total: 60 }));
  renderWorkspace();
  await waitFor(() => screen.getByTestId("pagination-next"));

  // Go to page 2
  await act(async () => {
    fireEvent.click(screen.getByTestId("pagination-next"));
  });
  await waitFor(() => {
    expect(api.get.mock.calls.some(([u]) => u.includes("offset=50"))).toBe(true);
  });

  // Change source_kind filter — must reset offset to 0
  const allSelects = screen.getAllByRole("combobox");
  const sourceSelect = allSelects.find(
    (el) => el.value === "all" && el !== allSelects[0],
  ) || allSelects[1];
  await act(async () => {
    fireEvent.change(sourceSelect, { target: { value: "manual" } });
  });

  await waitFor(() => {
    const calls = api.get.mock.calls.map(([url]) => url);
    const resetCall = calls.find(
      (u) => u.includes("source_kind=manual") && u.includes("offset=0"),
    );
    expect(resetCall).toBeDefined();
  });
});

test("no limit=200 present in any pyq-questions API call", async () => {
  api.get.mockImplementation(buildGetMock());
  renderWorkspace();
  await waitFor(() => screen.getByTestId("question-list-pane"));
  const questionCalls = api.get.mock.calls
    .map(([url]) => url)
    .filter((u) => u.includes("/pyq-questions?"));
  expect(questionCalls.every((u) => !u.includes("limit=200"))).toBe(true);
});
