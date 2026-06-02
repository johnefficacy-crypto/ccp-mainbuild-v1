import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) => String(e),
}));

// eslint-disable-next-line global-require
const { api } = require("../../../lib/api");
// eslint-disable-next-line global-require
const ExamIntelDocuments = require("./ExamIntelDocuments").default;

const EXAMS = [{ id: "e1", name: "SSC CGL", slug: "ssc-cgl" }];

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ExamIntelDocuments />
    </QueryClientProvider>,
  );
}

async function pickExam() {
  fireEvent.focus(screen.getByTestId("doc-field-exam_id"));
  fireEvent.mouseDown(await screen.findByTestId("doc-field-exam_id-option-e1"));
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, status: 200 }));
});

test("uploads a PDF: upload-url → PUT bytes → complete-upload, then lists the doc", async () => {
  const docs = [];
  api.get.mockImplementation((url) => {
    if (url.includes("/documents?exam_id=")) return Promise.resolve({ items: docs, total: docs.length });
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
  api.post.mockImplementation((url) => {
    if (url.endsWith("/upload-url")) return Promise.resolve({ document_id: "d1", upload_url: "https://storage.test/p?sig", upload_token: "t" });
    if (url.endsWith("/complete-upload")) {
      docs.push({ id: "d1", document_kind: "syllabus", original_filename: "syll.pdf", status: "processing", page_count: null });
      return Promise.resolve({ ok: true, text_extract_enqueued: true });
    }
    return Promise.resolve({ ok: true });
  });

  renderPanel();
  await pickExam();
  fireEvent.change(screen.getByTestId("doc-field-document_kind"), { target: { value: "syllabus" } });
  const file = new File([new Uint8Array([37, 80, 68, 70])], "syll.pdf", { type: "application/pdf" });
  fireEvent.change(screen.getByTestId("doc-file"), { target: { files: [file] } });
  fireEvent.click(screen.getByTestId("doc-upload-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(expect.stringContaining("/upload-url"), expect.anything()));
  // The bytes were PUT to the signed URL.
  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith("https://storage.test/p?sig", expect.objectContaining({ method: "PUT" })));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith(expect.stringContaining("/complete-upload"), { document_id: "d1" }));
  // And the doc shows in the list after reload.
  expect(await screen.findByTestId("doc-row-d1")).toBeTruthy();

  // The upload-url request carried the real file metadata.
  const [, body] = api.post.mock.calls.find(([u]) => u.endsWith("/upload-url"));
  expect(body.exam_id).toBe("e1");
  expect(body.document_kind).toBe("syllabus");
  expect(body.mime_type).toBe("application/pdf");
  expect(body.filename).toBe("syll.pdf");
});

test("rejects a non-PDF file before calling the API", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
  renderPanel();
  await pickExam();
  fireEvent.change(screen.getByTestId("doc-field-document_kind"), { target: { value: "syllabus" } });
  const txt = new File(["hello"], "notes.txt", { type: "text/plain" });
  fireEvent.change(screen.getByTestId("doc-file"), { target: { files: [txt] } });
  fireEvent.click(screen.getByTestId("doc-upload-submit"));

  expect(await screen.findByText(/only pdf/i)).toBeTruthy();
  expect(api.post).not.toHaveBeenCalled();
});

test("link-to-syllabus opens a picker (no window.prompt) and links the selection", async () => {
  const docs = [{ id: "d1", document_kind: "syllabus", original_filename: "syll.pdf", status: "processed", page_count: 1 }];
  api.get.mockImplementation((url) => {
    if (url.includes("/syllabus-documents")) return Promise.resolve({ items: [{ id: "sd1", title: "Official syllabus", document_type: "syllabus_pdf" }], total: 1 });
    if (url.includes("/documents?exam_id=")) return Promise.resolve({ items: docs, total: 1 });
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
  api.post.mockResolvedValue({ ok: true, audit_id: "a1" });
  const promptSpy = jest.spyOn(window, "prompt");

  renderPanel();
  await pickExam();
  await screen.findByTestId("doc-row-d1");
  fireEvent.click(screen.getByTestId("doc-link-syllabus-d1"));

  // A picker appears — not a prompt.
  fireEvent.focus(await screen.findByTestId("doc-link-target-d1"));
  fireEvent.mouseDown(await screen.findByTestId("doc-link-target-d1-option-sd1"));
  // link-to-syllabus requires a reason (>=8 chars) per LinkSyllabusRequest.
  fireEvent.change(screen.getByTestId("doc-link-reason-d1"), {
    target: { value: "Linking official syllabus PDF to CMS row" },
  });
  fireEvent.click(screen.getByTestId("doc-link-confirm-d1"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    expect.stringContaining("/d1/link-to-syllabus"),
    expect.objectContaining({ syllabus_document_id: "sd1", reason: "Linking official syllabus PDF to CMS row" }),
  ));
  expect(promptSpy).not.toHaveBeenCalled();
  promptSpy.mockRestore();
});

test("pages viewer fetches and shows extracted text per page", async () => {
  const docs = [{ id: "d1", document_kind: "syllabus", original_filename: "syll.pdf", status: "processed", page_count: 2 }];
  api.get.mockImplementation((url) => {
    if (url.includes("/documents/d1/pages")) return Promise.resolve({ items: [
      { page_number: 1, text_content: "Quantitative Aptitude", char_count: 21, extraction_status: "extracted" },
    ], total: 1 });
    if (url.includes("/documents?exam_id=")) return Promise.resolve({ items: docs, total: 1 });
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });

  renderPanel();
  await pickExam();
  await screen.findByTestId("doc-row-d1");
  fireEvent.click(screen.getByTestId("doc-pages-d1"));

  const view = await screen.findByTestId("doc-pages-view-d1");
  expect(view.textContent).toMatch(/Quantitative Aptitude/);
});
