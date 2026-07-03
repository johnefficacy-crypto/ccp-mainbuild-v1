/**
 * Tests for DocumentsPanel.
 *
 * Covers:
 * - loading state (skeleton)
 * - empty state ("Upload syllabus PDF to enable Syllabus Mapper" + upload form inline)
 * - error state on list fetch failure
 * - populated state (linked-docs table renders)
 * - full upload → complete → poll → link-to-syllabus round trip:
 *     POST upload-url → PUT bytes (fetch) → POST complete-upload
 *     → in-flight row appears → link form → POST link-to-syllabus
 *     → in-flight row removed, syllabus-documents refetched (unblocks mapper)
 * - link-to-pyq-paper path: picker fetches existing papers
 * - upload form rejects non-PDF files
 * - Refresh button re-fetches the list
 *
 * Implementation note: useExamWorkspace is mocked directly so the test has
 * stable exam/cycle values without the async ExamWorkspaceProvider fetch chain
 * (which would race against panel state transitions).
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  // DocumentsPanel now renders EvidenceSection, which uses getApiErrorMessage.
  getApiErrorMessage: (e) => (e && e.message) || "error",
}));

jest.mock("../../ExamWorkspaceContext", () => ({
  useExamWorkspace: jest.fn(),
}));

const { api } = require("../../../../../lib/api");
const { useExamWorkspace: mockUseExamWorkspace } = require("../../ExamWorkspaceContext");
const DocumentsPanel = require("../DocumentsPanel").default;

// ── Fixtures ──────────────────────────────────────────────────────────────────

const SYL_DOC = {
  id: "syl-1", exam_id: "exam-1", title: "SSC CGL Syllabus 2026",
  document_type: "syllabus_pdf", trust_status: "pending",
  created_at: "2026-01-15T10:00:00Z",
};
const PYQ_PAPER = { id: "pyq-1", exam_id: "exam-1", year: 2025, paper_code: "Tier-I", shift: "S1" };

// ── Setup helpers ─────────────────────────────────────────────────────────────

function mockEmptyLists() {
  api.get.mockImplementation((url) => {
    if (url.includes("syllabus-documents")) return Promise.resolve({ items: [] });
    if (url.includes("pyq-papers"))         return Promise.resolve({ items: [] });
    return Promise.resolve({ items: [] });
  });
}

function mockPopulatedLists() {
  api.get.mockImplementation((url) => {
    if (url.includes("syllabus-documents")) return Promise.resolve({ items: [SYL_DOC] });
    if (url.includes("pyq-papers"))         return Promise.resolve({ items: [] });
    return Promise.resolve({ items: [] });
  });
}

function renderPanel(props = {}) {
  return render(<DocumentsPanel {...props} />);
}

beforeEach(() => {
  jest.resetAllMocks();
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, status: 200 }));
  mockUseExamWorkspace.mockReturnValue({
    exam:   { id: "exam-1", name: "SSC CGL", exam_type: "recruitment" },
    cycle:  null,
    cycles: [{ id: "cy-1", exam_id: "exam-1", year: 2026, cycle_name: "2026" }],
    phases: [],
  });
});

// ── 1. Loading state ──────────────────────────────────────────────────────────

test("shows loading skeleton while list fetch is in flight", () => {
  // Never resolves → loading stays true
  api.get.mockImplementation(() => new Promise(() => {}));
  renderPanel();
  expect(screen.getByTestId("docs-loading")).toBeTruthy();
});

// ── 2. Empty state ────────────────────────────────────────────────────────────

test("empty state: shows actionable copy and upload form inline; no 'Exam CMS' redirect text", async () => {
  mockEmptyLists();
  renderPanel();

  await waitFor(() => screen.getByTestId("docs-empty"));
  expect(screen.getByTestId("docs-empty-title").textContent).toBe(
    "Upload syllabus PDF to enable Syllabus Mapper",
  );
  // Upload form must be visible without clicking a toggle button
  expect(screen.getByTestId("doc-upload-form")).toBeTruthy();
  // Must NOT suggest going to a separate Exam CMS page
  expect(screen.queryByText(/Exam CMS/)).toBeNull();
});

// ── 3. Error state ────────────────────────────────────────────────────────────

test("error state: shows error message when list fetch rejects", async () => {
  api.get.mockRejectedValue(new Error("network timeout"));
  renderPanel();

  await waitFor(() => screen.getByTestId("docs-list-error"));
  expect(screen.getByTestId("docs-list-error").textContent).toMatch(/network timeout/i);
});

// ── 4. Populated state ────────────────────────────────────────────────────────

test("populated state: renders linked-docs table with syllabus row", async () => {
  mockPopulatedLists();
  renderPanel();

  await waitFor(() => screen.getByTestId("docs-populated"));
  expect(screen.getByTestId("linked-docs-table")).toBeTruthy();
  expect(screen.getByTestId(`linked-doc-row-${SYL_DOC.id}`)).toBeTruthy();
  expect(screen.getByText("SSC CGL Syllabus 2026")).toBeTruthy();
});

// ── 5. Full upload → complete → poll → link-to-syllabus round trip ─────────────

test("upload → complete-upload → in-flight row → link-to-syllabus → linked list reloads", async () => {
  // POST mocks
  api.post.mockImplementation((url) => {
    if (url.endsWith("/upload-url")) {
      return Promise.resolve({
        document_id: "doc-new",
        upload_url:  "https://storage.test/p?sig=abc",
        upload_token: "tok",
      });
    }
    if (url.endsWith("/complete-upload")) {
      return Promise.resolve({ ok: true, text_extract_enqueued: true });
    }
    if (url.includes("/link-to-syllabus")) {
      return Promise.resolve({ ok: true, audit_id: "aud-1", syllabus_document: SYL_DOC });
    }
    return Promise.resolve({ ok: true });
  });

  // GET mocks: lists start empty, then after link the reload returns the doc
  let syllabusCalls = 0;
  api.get.mockImplementation((url) => {
    if (url.includes("documents/doc-new")) {
      return Promise.resolve({
        document: { id: "doc-new", status: "processing" },
        pages_count: 0,
        extraction: { status: "running" },
      });
    }
    if (url.includes("syllabus-documents")) {
      syllabusCalls++;
      return Promise.resolve({ items: syllabusCalls >= 2 ? [SYL_DOC] : [] });
    }
    if (url.includes("pyq-papers")) return Promise.resolve({ items: [] });
    return Promise.resolve({ items: [] });
  });

  renderPanel();
  await waitFor(() => screen.getByTestId("doc-upload-form"));

  // Fill upload form
  fireEvent.change(screen.getByTestId("doc-kind"), { target: { value: "syllabus" } });
  const file = new File(
    [new Uint8Array([37, 80, 68, 70])],
    "syllabus-2026.pdf",
    { type: "application/pdf" },
  );
  fireEvent.change(screen.getByTestId("doc-file"), { target: { files: [file] } });

  await act(async () => {
    fireEvent.click(screen.getByTestId("doc-upload-submit"));
  });

  // Steps 1+2+3: verify the three sequential API calls
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith(
      expect.stringContaining("/upload-url"),
      expect.objectContaining({ exam_id: "exam-1", document_kind: "syllabus" }),
    ),
  );
  expect(global.fetch).toHaveBeenCalledWith(
    "https://storage.test/p?sig=abc",
    expect.objectContaining({ method: "PUT" }),
  );
  expect(api.post).toHaveBeenCalledWith(
    expect.stringContaining("/complete-upload"),
    expect.objectContaining({ document_id: "doc-new" }),
  );

  // In-flight row appears
  await waitFor(() => screen.getByTestId("inflight-row-doc-new"));

  // Open link form
  await act(async () => {
    fireEvent.click(screen.getByTestId("doc-link-open-doc-new"));
  });
  await waitFor(() => screen.getByTestId("doc-link-form-doc-new"));

  // Reason too short → validation error
  fireEvent.change(screen.getByTestId("doc-link-reason-doc-new"), {
    target: { value: "short" },
  });
  await act(async () => {
    fireEvent.click(screen.getByTestId("doc-link-submit-doc-new"));
  });
  await waitFor(() => screen.getByTestId("doc-link-err-doc-new"));

  // Valid reason → link succeeds
  fireEvent.change(screen.getByTestId("doc-link-reason-doc-new"), {
    target: { value: "Linking official SSC CGL syllabus 2026" },
  });
  await act(async () => {
    fireEvent.click(screen.getByTestId("doc-link-submit-doc-new"));
  });

  // Step 5: link-to-syllabus called without syllabus_document_id (creates new row)
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith(
      expect.stringContaining("doc-new/link-to-syllabus"),
      expect.objectContaining({ reason: "Linking official SSC CGL syllabus 2026" }),
    ),
  );
  // No syllabus_document_id should be in the payload (auto-create)
  const linkCall = api.post.mock.calls.find((c) => c[0].includes("link-to-syllabus"));
  expect(linkCall[1].syllabus_document_id).toBeUndefined();

  // In-flight row removed after link
  await waitFor(() =>
    expect(screen.queryByTestId("inflight-row-doc-new")).toBeNull(),
  );

  // syllabus-documents was refetched after link (unblocks DocumentSelector / Mapper)
  expect(
    api.get.mock.calls.filter((c) => c[0].includes("syllabus-documents")).length,
  ).toBeGreaterThanOrEqual(2);
});

// ── 6. link-to-pyq-paper path ──────────────────────────────────────────────────

test("link-to-pyq-paper: fetches papers list for picker and posts correct payload", async () => {
  api.post.mockImplementation((url) => {
    if (url.endsWith("/upload-url"))     return Promise.resolve({ document_id: "doc-pyq", upload_url: "https://s.test/x", upload_token: "t" });
    if (url.endsWith("/complete-upload")) return Promise.resolve({ ok: true });
    if (url.includes("/link-to-pyq-paper")) return Promise.resolve({ ok: true, audit_id: "a2", pyq_paper: PYQ_PAPER });
    return Promise.resolve({ ok: true });
  });

  // First pyq-papers call is the panel's list load (returns empty → shows upload form).
  // Second call is openLink's picker fetch (returns the paper).
  let pyqCallCount = 0;
  api.get.mockImplementation((url) => {
    if (url.includes("documents/doc-pyq")) return Promise.resolve({ document: { id: "doc-pyq", status: "processing" }, pages_count: 0, extraction: { status: "running" } });
    if (url.includes("syllabus-documents")) return Promise.resolve({ items: [] });
    if (url.includes("pyq-papers")) {
      pyqCallCount++;
      return Promise.resolve({ items: pyqCallCount >= 2 ? [PYQ_PAPER] : [] });
    }
    return Promise.resolve({ items: [] });
  });

  renderPanel();
  await waitFor(() => screen.getByTestId("doc-upload-form"));

  // Upload a pyq_paper
  fireEvent.change(screen.getByTestId("doc-kind"), { target: { value: "pyq_paper" } });
  const file = new File([new Uint8Array([37, 80])], "pyq-2025.pdf", { type: "application/pdf" });
  fireEvent.change(screen.getByTestId("doc-file"), { target: { files: [file] } });
  await act(async () => { fireEvent.click(screen.getByTestId("doc-upload-submit")); });

  await waitFor(() => screen.getByTestId("inflight-row-doc-pyq"));

  // Open link form (triggers pyq-papers fetch internally)
  await act(async () => {
    fireEvent.click(screen.getByTestId("doc-link-open-doc-pyq"));
  });
  await waitFor(() => screen.getByTestId("doc-link-form-doc-pyq"));
  // Picker should be populated after async fetch
  await waitFor(() => screen.getByTestId("doc-link-pyq-select-doc-pyq"));

  fireEvent.change(screen.getByTestId("doc-link-pyq-select-doc-pyq"), {
    target: { value: PYQ_PAPER.id },
  });
  fireEvent.change(screen.getByTestId("doc-link-reason-doc-pyq"), {
    target: { value: "Linking Tier-I 2025 PYQ paper" },
  });
  await act(async () => {
    fireEvent.click(screen.getByTestId("doc-link-submit-doc-pyq"));
  });

  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith(
      expect.stringContaining("doc-pyq/link-to-pyq-paper"),
      expect.objectContaining({
        reason:       "Linking Tier-I 2025 PYQ paper",
        pyq_paper_id: PYQ_PAPER.id,
      }),
    ),
  );
});

// ── 7. Upload form rejects non-PDF ────────────────────────────────────────────

test("upload form rejects non-PDF files with inline error", async () => {
  mockEmptyLists();
  renderPanel();

  await waitFor(() => screen.getByTestId("doc-upload-form"));

  const txtFile = new File(["text"], "doc.txt", { type: "text/plain" });
  fireEvent.change(screen.getByTestId("doc-file"), { target: { files: [txtFile] } });

  // Click submit — handleSubmit is synchronous up to the validation check
  await act(async () => {
    fireEvent.click(screen.getByTestId("doc-upload-submit"));
  });

  // Error div should appear
  await waitFor(() => screen.getByTestId("doc-upload-err"), { timeout: 3000 });
  expect(screen.getByTestId("doc-upload-err").textContent).toMatch(/pdf/i);
  expect(api.post).not.toHaveBeenCalled();
});

// ── 8. Refresh re-fetches the list ────────────────────────────────────────────

test("Refresh button re-fetches the linked docs list", async () => {
  mockPopulatedLists();
  renderPanel();
  await waitFor(() => screen.getByTestId("docs-populated"));

  const before = api.get.mock.calls.filter((c) => c[0].includes("syllabus-documents")).length;
  fireEvent.click(screen.getByTestId("doc-refresh"));
  await waitFor(() =>
    expect(
      api.get.mock.calls.filter((c) => c[0].includes("syllabus-documents")).length,
    ).toBeGreaterThan(before),
  );
});

// ── 9. Processed-but-unlinked doc rehydration (P1-2 regression) ──────────────

test("processed pyq_paper doc not linked to any paper appears in inFlight after load", async () => {
  // Use original_filename (real API shape — the backend response does not have filename).
  const PROCESSED_UNLINKED = {
    id: "doc-unlinked-processed",
    original_filename: "upsc-2024-gs1.pdf",
    document_kind: "pyq_paper",
    status: "processed",
    page_count: 32,
    extraction: {},
  };

  api.get.mockImplementation((url) => {
    if (url.includes("syllabus-documents")) return Promise.resolve({ items: [] });
    if (url.includes("pyq-papers")) return Promise.resolve({ items: [] }); // no linked papers
    if (url.includes("documents?")) return Promise.resolve({ items: [PROCESSED_UNLINKED] });
    return Promise.resolve({ items: [] });
  });

  renderPanel();
  // Panel reaches docs-populated because inFlight becomes non-empty
  await waitFor(() => screen.getByTestId("inflight-row-doc-unlinked-processed"));
  // Filename is normalized from original_filename and rendered visibly
  expect(screen.getByText("upsc-2024-gs1.pdf")).toBeTruthy();
});

test("processed pyq_paper doc already linked to a paper is excluded from inFlight", async () => {
  const LINKED_DOC = {
    id: "doc-already-linked",
    filename: "upsc-2023.pdf",
    document_kind: "pyq_paper",
    status: "processed",
    extraction: {},
  };
  const PAPER_WITH_LINK = {
    id: "paper-linked", source_document_id: "doc-already-linked",
  };

  api.get.mockImplementation((url) => {
    if (url.includes("syllabus-documents")) return Promise.resolve({ items: [] });
    if (url.includes("pyq-papers")) return Promise.resolve({ items: [PAPER_WITH_LINK] });
    if (url.includes("documents?")) return Promise.resolve({ items: [LINKED_DOC] });
    return Promise.resolve({ items: [] });
  });

  renderPanel();
  // No inFlight row for the linked doc; panel shows docs-populated because of the linked paper
  await waitFor(() => screen.getByTestId("docs-populated"));
  expect(screen.queryByTestId("inflight-row-doc-already-linked")).toBeNull();
});

// ── 11. D10: load() is always exam-wide — no cycle filter ────────────────────

test("D10: load() fetches exam-wide without any cycle param even when a cycle is selected", async () => {
  // D10 decision prohibits filtering PYQ corpus by cycle. The workbench must
  // always show all same-exam papers regardless of selected cycle.
  mockUseExamWorkspace.mockReturnValue({
    exam:   { id: "exam-1", name: "SSC CGL", exam_type: "recruitment" },
    cycle:  { id: "cy-1" },
    cycles: [{ id: "cy-1", exam_id: "exam-1", year: 2026, cycle_name: "2026" }],
    phases: [],
  });
  api.get.mockImplementation((url) => {
    if (url.includes("syllabus-documents")) return Promise.resolve({ items: [] });
    if (url.includes("pyq-papers"))         return Promise.resolve({ items: [] });
    return Promise.resolve({ items: [] });
  });
  renderPanel();
  await waitFor(() => screen.getByTestId("docs-empty"));

  const sylCall = api.get.mock.calls.find((c) => c[0].includes("syllabus-documents"));
  expect(sylCall[0]).toContain("exam_id=exam-1");
  // Must NOT send any cycle filter.
  expect(sylCall[0]).not.toMatch(/[?&]exam_cycle_id=/);
  expect(sylCall[0]).not.toMatch(/[?&]cycle_id=/);

  const pyqCall = api.get.mock.calls.find((c) => c[0].includes("pyq-papers?"));
  expect(pyqCall[0]).toContain("exam_id=exam-1");
  expect(pyqCall[0]).not.toMatch(/[?&]exam_cycle_id=/);
  expect(pyqCall[0]).not.toMatch(/[?&]cycle_id=/);
});

// ── 12. Document recovery failure surfaces as list error ──────────────────────

test("document recovery fetch failure is surfaced as list error, not swallowed", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("syllabus-documents")) return Promise.resolve({ items: [] });
    if (url.includes("pyq-papers"))         return Promise.resolve({ items: [] });
    if (url.includes("documents?"))         return Promise.reject(new Error("storage unavailable"));
    return Promise.resolve({ items: [] });
  });
  renderPanel();
  await waitFor(() => screen.getByTestId("docs-list-error"));
  expect(screen.getByTestId("docs-list-error").textContent).toMatch(/storage unavailable/i);
});

// ── 13. D10: document linked to a historical-cycle paper is excluded from inFlight

test("D10: document linked to same-exam paper in another cycle is not shown as pending-link", async () => {
  // Recovery fetches exam-wide assets. linkedDocIds must also be exam-wide.
  // A PDF already linked to a 2025-cycle paper must not re-appear as "Uploaded — pending link"
  // when the operator is currently viewing the 2026 cycle.
  mockUseExamWorkspace.mockReturnValue({
    exam:   { id: "exam-1", name: "SSC CGL", exam_type: "recruitment" },
    cycle:  { id: "cy-2026" },
    cycles: [{ id: "cy-2026", exam_id: "exam-1", year: 2026, cycle_name: "2026" }],
    phases: [],
  });

  const PAPER_2025 = {
    id: "paper-2025", exam_id: "exam-1", exam_cycle_id: "cy-2025",
    year: 2025, source_document_id: "doc-historical",
  };
  const DOC_HISTORICAL = {
    id: "doc-historical", original_filename: "upsc-2025-gs1.pdf",
    document_kind: "pyq_paper", status: "processed", extraction: {},
  };

  api.get.mockImplementation((url) => {
    if (url.includes("syllabus-documents")) return Promise.resolve({ items: [] });
    // pyq-papers returns ALL same-exam papers (exam-wide per D10), including 2025 paper
    if (url.includes("pyq-papers"))         return Promise.resolve({ items: [PAPER_2025] });
    if (url.includes("documents?"))         return Promise.resolve({ items: [DOC_HISTORICAL] });
    return Promise.resolve({ items: [] });
  });

  renderPanel();
  await waitFor(() => screen.getByTestId("docs-populated"));
  // The historical document is already linked — must NOT appear in inFlight
  expect(screen.queryByTestId("inflight-row-doc-historical")).toBeNull();
});

// ── 14. Archived documents are excluded from inFlight recovery ────────────────

test("archived document is excluded from inFlight and does not appear as pending-link", async () => {
  const ARCHIVED_DOC = {
    id: "doc-archived", original_filename: "upsc-2024-archive.pdf",
    document_kind: "pyq_paper", status: "archived", extraction: {},
  };

  api.get.mockImplementation((url) => {
    if (url.includes("syllabus-documents")) return Promise.resolve({ items: [] });
    if (url.includes("pyq-papers"))         return Promise.resolve({ items: [] });
    if (url.includes("documents?"))         return Promise.resolve({ items: [ARCHIVED_DOC] });
    return Promise.resolve({ items: [] });
  });

  renderPanel();
  // No inFlight rows → panel stays in docs-empty (archived doc must not add to inFlight)
  await waitFor(() => screen.getByTestId("docs-empty"));
  expect(screen.queryByTestId("inflight-row-doc-archived")).toBeNull();
});

// ── Cycle/phase selectors render readable labels, never raw UUIDs ─────────────

test("upload form cycle/phase options use readable labels, not raw UUIDs", async () => {
  const CYCLE_UUID = "787b0067-b7c4-4311-a1c0-d488395927b6";
  const NAMELESS_CYCLE_UUID = "881832c8-4b70-4b58-adc1-b9584ede75fe";
  const PHASE_UUID = "6566d50e-7f1c-4410-aa36-8142dfe9a79b";
  const NAMELESS_PHASE_UUID = "1111aaaa-2222-3333-4444-555566667777";

  mockEmptyLists();
  mockUseExamWorkspace.mockReturnValue({
    exam:   { id: "exam-1", name: "UPSC CSE", exam_type: "recruitment" },
    cycle:  null,
    cycles: [
      { id: CYCLE_UUID, exam_id: "exam-1", year: 2026, cycle_name: "Prelims" },
      { id: "cy-2025", exam_id: "exam-1", year: 2025, cycle_name: "2025" },
      { id: NAMELESS_CYCLE_UUID, exam_id: "exam-1" },
    ],
    phases: [
      { id: PHASE_UUID, phase_name: "Prelims (CSAT)" },
      { id: NAMELESS_PHASE_UUID, phase_slug: "mains" },
    ],
  });

  renderPanel();
  const cycleSel = await screen.findByTestId("doc-cycle-select");
  const phaseSel = screen.getByTestId("doc-phase-select");

  // Readable labels present
  expect(cycleSel.textContent).toContain("2026 · Prelims");
  expect(cycleSel.textContent).toContain("2025");           // not "2025 · 2025"
  expect(cycleSel.textContent).not.toContain("2025 · 2025");
  expect(cycleSel.textContent).toContain("…de75fe");        // nameless → short id
  expect(phaseSel.textContent).toContain("Prelims (CSAT)");
  expect(phaseSel.textContent).toContain("mains");          // phase_slug fallback

  // No full UUID ever rendered
  expect(cycleSel.textContent).not.toContain(CYCLE_UUID);
  expect(cycleSel.textContent).not.toContain(NAMELESS_CYCLE_UUID);
  expect(phaseSel.textContent).not.toContain(PHASE_UUID);
  expect(phaseSel.textContent).not.toContain(NAMELESS_PHASE_UUID);
});
