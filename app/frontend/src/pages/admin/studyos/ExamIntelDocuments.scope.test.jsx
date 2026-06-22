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
  api.post.mockReset();
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
  // First scope resolves with a real doc row
  api.get.mockResolvedValueOnce({
    items: [{ id: "doc-1", document_kind: "syllabus", original_filename: "old.pdf", status: "pending" }],
    total: 1,
  });
  // Second scope resolves empty
  api.get.mockResolvedValue({ items: [], total: 0 });

  const { rerender } = renderDocs({ scopeExamId: "exam-has-docs" });

  // Wait for the old doc row to actually appear in the DOM
  await waitFor(() => screen.getByTestId("doc-row-doc-1"));

  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-empty" />
    </MemoryRouter>,
  );

  // After scope change, the old doc row must disappear
  await waitFor(() => {
    expect(screen.queryByTestId("doc-row-doc-1")).toBeNull();
  });
});

test("failed new-scope request does not restore old-scope docs", async () => {
  api.get.mockResolvedValueOnce({
    items: [{ id: "doc-a", document_kind: "pyq_paper", original_filename: "prev.pdf", status: "processed" }],
    total: 1,
  });
  api.get.mockRejectedValue(new Error("network error"));

  const { rerender } = renderDocs({ scopeExamId: "exam-prev" });

  // Wait for the old doc row to actually appear
  await waitFor(() => screen.getByTestId("doc-row-doc-a"));

  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-fail" />
    </MemoryRouter>,
  );

  // Even after failed new request, old doc row must not reappear
  await waitFor(() => {
    expect(screen.queryByTestId("doc-row-doc-a")).toBeNull();
  });
});

// ── Multi-step workflow protection (scopeGenRef) ──────────────────────────────

test("selected file is cleared when exam scope changes", async () => {
  const { rerender } = renderDocs({ scopeExamId: "exam-a" });

  // Simulate selecting a PDF file
  const pdf = new File(["dummy"], "report.pdf", { type: "application/pdf" });
  fireEvent.change(screen.getByTestId("doc-file"), { target: { files: [pdf] } });

  // Set document_kind to pass the first validation checks
  fireEvent.change(screen.getByTestId("doc-field-document_kind"), { target: { value: "syllabus" } });

  // Change scope — this should clear the selected file
  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-b" />
    </MemoryRouter>,
  );

  // Submit — if file was cleared, we get "Choose a PDF file." before any API call
  fireEvent.submit(screen.getByTestId("doc-upload-form"));

  await waitFor(() => {
    expect(screen.getByRole("status").textContent).toContain("Choose a PDF file");
  });
  expect(api.post).not.toHaveBeenCalled();
});

test("upload completion from old scope cannot set success status in new scope", async () => {
  api.get.mockResolvedValue({ items: [], total: 0 });

  let resolveUploadUrl;
  api.post.mockReturnValueOnce(new Promise((res) => { resolveUploadUrl = res; }));

  const { rerender } = renderDocs({ scopeExamId: "exam-upload-a" });

  // Set document_kind and file, then submit
  fireEvent.change(screen.getByTestId("doc-field-document_kind"), { target: { value: "syllabus" } });
  const pdf = new File(["dummy"], "test.pdf", { type: "application/pdf" });
  fireEvent.change(screen.getByTestId("doc-file"), { target: { files: [pdf] } });

  // Kick off the upload (upload-url request starts)
  fireEvent.submit(screen.getByTestId("doc-upload-form"));

  // Change scope before upload-url resolves
  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-upload-b" />
    </MemoryRouter>,
  );

  // Resolve the stale upload-url with a signed response
  resolveUploadUrl({ upload_url: "https://storage.example.com/put", document_id: "doc-stale" });

  // Wait for any async effects to flush
  await waitFor(() => {
    expect(api.get.mock.calls.some(([u]) => u.includes("exam_id=exam-upload-b"))).toBe(true);
  });

  // No success status from old scope should appear
  expect(screen.queryByText(/Extraction queued/)).toBeNull();
});

test("pages response from old scope cannot display after scope changes", async () => {
  const sharedDoc = { id: "shared-doc", document_kind: "syllabus", original_filename: "shared.pdf", status: "processed" };

  // Mocks must be in call-order: exam-a list → deferred pages → exam-b list
  let resolvePagesOld;
  api.get
    .mockResolvedValueOnce({ items: [sharedDoc], total: 1 })
    .mockReturnValueOnce(new Promise((res) => { resolvePagesOld = res; }))
    .mockResolvedValueOnce({ items: [sharedDoc], total: 1 });

  const { rerender } = renderDocs({ scopeExamId: "exam-pages-a" });

  // Wait for exam-a doc row
  await waitFor(() => screen.getByTestId("doc-row-shared-doc"));

  // Click Pages (consumes the deferred mock)
  fireEvent.click(screen.getByTestId("doc-pages-shared-doc"));

  // Change scope before pages resolve
  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-pages-b" />
    </MemoryRouter>,
  );

  // Wait for exam-b doc list to load
  await waitFor(() => screen.getByTestId("doc-row-shared-doc"));

  // Resolve old pages with distinctive stale content
  resolvePagesOld({ items: [{ page_number: 1, extraction_status: "done", text_content: "Stale page content exam-a" }] });

  await new Promise((r) => setTimeout(r, 0));

  // Stale page content from exam-a must not appear
  expect(screen.queryByText("Stale page content exam-a")).toBeNull();
});

test("link confirmation from old scope cannot set success status after scope changes", async () => {
  const doc = { id: "link-doc", document_kind: "syllabus", original_filename: "link.pdf", status: "processed" };
  api.get.mockResolvedValueOnce({ items: [doc], total: 1 });
  api.get.mockResolvedValue({ items: [], total: 0 });

  let resolveLink;
  api.post.mockReturnValueOnce(new Promise((res) => { resolveLink = res; }));

  const { rerender } = renderDocs({ scopeExamId: "exam-link-a" });

  // Wait for doc row to appear and open the link picker
  await waitFor(() => screen.getByTestId("doc-row-link-doc"));
  fireEvent.click(screen.getByTestId("doc-link-syllabus-link-doc"));

  // Change scope before link resolves
  rerender(
    <MemoryRouter>
      <ExamIntelDocuments scopeExamId="exam-link-b" />
    </MemoryRouter>,
  );

  // Resolve the stale link request
  resolveLink({ ok: true });

  // Wait for async to flush
  await waitFor(() => {
    expect(api.get.mock.calls.some(([u]) => u.includes("exam_id=exam-link-b"))).toBe(true);
  });

  // No success status from the old-scope link should appear
  expect(screen.queryByText(/Linked document/)).toBeNull();
});
