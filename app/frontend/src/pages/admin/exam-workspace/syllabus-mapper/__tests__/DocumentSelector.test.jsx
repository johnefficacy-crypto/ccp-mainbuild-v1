/**
 * Tests for DocumentSelector (dead-mapper fix).
 *
 * The previous implementation called
 *   GET /api/admin/exam-intelligence/workspace/{examId}/documents
 * which does not exist in the backend.  The fixed implementation calls
 *   GET /api/admin/exam-intelligence-cms/syllabus-documents?exam_id={examId}&limit=100
 * which is confirmed in PR-0 §6 and populated by link-to-syllabus.
 */
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

const { api } = require("../../../../../lib/api");
const DocumentSelector = require("../DocumentSelector").default;

const SYL_DOCS = [
  { id: "doc-1", title: "SSC CGL Syllabus 2026",    document_type: "syllabus_pdf", source_document_id: "asset-1" },
  { id: "doc-2", title: "SSC CGL Notification 2025", document_type: "notification"  },
];

beforeEach(() => {
  api.get.mockReset();
});

test("calls the CMS syllabus-documents endpoint (not the nonexistent workspace route)", async () => {
  api.get.mockResolvedValue({ items: SYL_DOCS });

  render(<DocumentSelector examId="exam-1" value={null} onChange={() => {}} />);

  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));

  const calledUrl = api.get.mock.calls[0][0];
  // Must call the CMS endpoint
  expect(calledUrl).toContain("/exam-intelligence-cms/syllabus-documents");
  expect(calledUrl).toContain("exam_id=exam-1");
  // Must NOT call the nonexistent workspace sub-route
  expect(calledUrl).not.toContain("/workspace/");
});

test("renders fetched documents as options using title field", async () => {
  api.get.mockResolvedValue({ items: SYL_DOCS });

  render(<DocumentSelector examId="exam-1" value={null} onChange={() => {}} />);

  await waitFor(() =>
    expect(screen.getByRole("option", { name: "SSC CGL Syllabus 2026" })).toBeTruthy(),
  );
  expect(screen.getByRole("option", { name: "SSC CGL Notification 2025" })).toBeTruthy();
});

test("shows 'No documents' when list is empty", async () => {
  api.get.mockResolvedValue({ items: [] });

  render(<DocumentSelector examId="exam-1" value={null} onChange={() => {}} />);

  await waitFor(() =>
    expect(screen.getByRole("combobox").textContent).toContain("No documents"),
  );
  expect(screen.getByRole("combobox").disabled).toBe(true);
});

test("fires onChange with selected doc id", async () => {
  api.get.mockResolvedValue({ items: SYL_DOCS });
  const onChange = jest.fn();

  render(<DocumentSelector examId="exam-1" value={null} onChange={onChange} />);
  await waitFor(() =>
    expect(screen.getByRole("option", { name: "SSC CGL Syllabus 2026" })).toBeTruthy(),
  );

  fireEvent.change(screen.getByTestId("syllabus-doc-select"), {
    target: { value: "doc-1" },
  });
  // Passes the id AND the selected row so callers can reach source_document_id.
  expect(onChange).toHaveBeenCalledWith("doc-1", SYL_DOCS[0]);
});

test("does not fetch when examId is falsy", () => {
  api.get.mockResolvedValue({ items: [] });
  render(<DocumentSelector examId={null} value={null} onChange={() => {}} />);
  expect(api.get).not.toHaveBeenCalled();
});
