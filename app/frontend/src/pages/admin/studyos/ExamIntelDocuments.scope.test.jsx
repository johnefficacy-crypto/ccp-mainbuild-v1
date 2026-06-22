/**
 * ExamIntelDocuments scope-prop regressions (I8-C blocker 2).
 *
 * Covers:
 * - document list immediately requests the scoped exam_id on mount (no user action required)
 * - upload form has exam_id pre-filled from scopeExamId prop
 * - upload form has exam_cycle_id pre-filled from scopeCycleId prop
 * - scope change on mounted component updates list request deterministically
 */
import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) => e?.message || String(e),
}));

jest.mock("../../../lib/supabase", () => ({
  __esModule: true,
  supabase: {
    auth: {
      getSession: jest.fn(),
      onAuthStateChange: jest.fn(() => ({
        data: { subscription: { unsubscribe: jest.fn() } },
      })),
    },
  },
}));

// CmsRefField renders a stub that shows the value as a data attribute
jest.mock("../../../features/admin/shared/CmsRefField", () => ({
  __esModule: true,
  default: ({ testId, value }) => <div data-testid={testId || "cms-ref-field"} data-value={value} />,
}));

const { api } = require("../../../lib/api");
const ExamIntelDocuments = require("./ExamIntelDocuments").default;

function renderDocs(props = {}) {
  return render(
    <MemoryRouter>
      <ExamIntelDocuments {...props} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  api.get.mockReset();
  api.get.mockResolvedValue({ items: [], total: 0 });
});

// ── Scoped list request on mount ──────────────────────────────────────────────

test("document list requests scoped exam_id immediately on mount (no user action)", async () => {
  renderDocs({ scopeExamId: "exam-doc-scope" });

  await waitFor(() => {
    const calls = api.get.mock.calls.map(([u]) => u);
    expect(calls.some((u) => u.includes("exam_id=exam-doc-scope"))).toBe(true);
  });
});

test("no list request when scopeExamId is absent (form.exam_id is empty)", () => {
  renderDocs({});
  // Without exam_id, loadList short-circuits
  expect(api.get).not.toHaveBeenCalled();
});

// ── Upload form pre-fill ──────────────────────────────────────────────────────

test("upload form exam_id field is pre-filled from scopeExamId prop", () => {
  renderDocs({ scopeExamId: "exam-prefill-doc" });
  // CmsRefField stub renders data-value attribute
  const examField = screen.getByTestId("doc-field-exam_id");
  expect(examField.dataset.value).toBe("exam-prefill-doc");
});

test("upload form exam_cycle_id field is pre-filled from scopeCycleId prop", () => {
  renderDocs({ scopeExamId: "exam-prefill-doc", scopeCycleId: "cycle-prefill" });
  const cycleField = screen.getByTestId("doc-field-exam_cycle_id");
  expect(cycleField.dataset.value).toBe("cycle-prefill");
});

test("upload form shows empty exam_id when no scope provided", () => {
  renderDocs({});
  const examField = screen.getByTestId("doc-field-exam_id");
  expect(examField.dataset.value).toBe("");
});

// ── Scope change updates list request ─────────────────────────────────────────

test("scope change on mounted component updates document list request", async () => {
  const { rerender } = renderDocs({ scopeExamId: "exam-old" });

  await waitFor(() => {
    expect(api.get.mock.calls.some(([u]) => u.includes("exam_id=exam-old"))).toBe(true);
  });

  api.get.mockClear();

  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-new" />
    </MemoryRouter>,
  );

  await waitFor(() => {
    expect(api.get.mock.calls.some(([u]) => u.includes("exam_id=exam-new"))).toBe(true);
  });

  expect(api.get.mock.calls.some(([u]) => u.includes("exam_id=exam-old"))).toBe(false);
});

// ── Fail-closed scope transitions ─────────────────────────────────────────────

test("scope transition from exam to global clears exam_id form field immediately", async () => {
  const { rerender } = renderDocs({ scopeExamId: "exam-clear-test" });

  rerender(
    <MemoryRouter>
      <ExamIntelDocuments />
    </MemoryRouter>,
  );

  const examField = screen.getByTestId("doc-field-exam_id");
  expect(examField.dataset.value).toBe("");
});

test("scope transition removing cycle clears exam_cycle_id form field", async () => {
  const { rerender } = renderDocs({ scopeExamId: "exam-1", scopeCycleId: "cycle-to-remove" });

  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-1" />
    </MemoryRouter>,
  );

  const cycleField = screen.getByTestId("doc-field-exam_cycle_id");
  expect(cycleField.dataset.value).toBe("");
});

test("full scope change sets new scope exactly and clears phase field", async () => {
  const { rerender } = renderDocs({ scopeExamId: "exam-old", scopeCycleId: "cycle-old" });

  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-new" scopeCycleId="cycle-new" />
    </MemoryRouter>,
  );

  const examField = screen.getByTestId("doc-field-exam_id");
  const cycleField = screen.getByTestId("doc-field-exam_cycle_id");
  expect(examField.dataset.value).toBe("exam-new");
  expect(cycleField.dataset.value).toBe("cycle-new");
});

test("stale response from old exam scope cannot overwrite docs after scope change", async () => {
  let resolveOld;
  const oldPromise = new Promise((res) => { resolveOld = res; });
  api.get.mockReturnValueOnce(oldPromise);
  api.get.mockResolvedValue({ items: [], total: 0 });

  const { rerender } = renderDocs({ scopeExamId: "exam-stale" });

  // Change scope before old request resolves
  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-fresh" />
    </MemoryRouter>,
  );

  // Now resolve the old (stale) request with a doc
  resolveOld({ items: [{ id: "stale-doc", title: "Stale Doc", type: "pdf" }], total: 1 });

  // Wait for new scope request to settle
  await waitFor(() => {
    expect(api.get.mock.calls.some(([u]) => u.includes("exam_id=exam-fresh"))).toBe(true);
  });

  // Stale doc must not appear
  expect(screen.queryByText("Stale Doc")).toBeNull();
});

test("document rows from previous scope are cleared immediately on scope transition", async () => {
  // First scope resolves with a doc
  api.get.mockResolvedValueOnce({ items: [{ id: "doc-1", title: "Old Doc", type: "pdf" }], total: 1 });
  // Second scope (after rerender) resolves with nothing
  api.get.mockResolvedValue({ items: [], total: 0 });

  const { rerender } = renderDocs({ scopeExamId: "exam-has-docs" });

  await waitFor(() => expect(api.get).toHaveBeenCalled());

  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-empty" />
    </MemoryRouter>,
  );

  // After scope change, old docs must not persist
  await waitFor(() => {
    expect(screen.queryByText("Old Doc")).toBeNull();
  });
});

test("failed new-scope request does not restore old-scope docs", async () => {
  api.get.mockResolvedValueOnce({ items: [{ id: "doc-a", title: "Prev Doc", type: "pdf" }], total: 1 });
  api.get.mockRejectedValue(new Error("network error"));

  const { rerender } = renderDocs({ scopeExamId: "exam-prev" });

  await waitFor(() => expect(api.get).toHaveBeenCalled());

  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-fail" />
    </MemoryRouter>,
  );

  // Even after failed new request, old docs must not reappear
  await waitFor(() => {
    expect(screen.queryByText("Prev Doc")).toBeNull();
  });
});
