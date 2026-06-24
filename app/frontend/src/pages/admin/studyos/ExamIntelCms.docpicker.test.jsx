import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useSearchParams: () => [new URLSearchParams(), jest.fn()],
}))

jest.mock("../../../lib/supabase", () => ({
  __esModule: true,
  supabase: { auth: { getSession: jest.fn(), onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })) } },
}))
jest.mock("../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" }),
}))

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) => String(e),
}));

// eslint-disable-next-line global-require
const { api } = require("../../../lib/api");
// eslint-disable-next-line global-require
const AdminExamIntelCms = require("./ExamIntelCms").default;

const EXAMS = [{ id: "e1", name: "SSC CGL", slug: "ssc-cgl" }];
const DOCS = [{ id: "doc1", storage_path: "admin/e1/syll.pdf", original_filename: "syll.pdf",
               document_kind: "syllabus", created_at: "2026-05-25" }];

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><AdminExamIntelCms /></QueryClientProvider>);
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.get.mockImplementation((url) => {
    if (url.includes("/documents")) return Promise.resolve({ items: DOCS, total: 1 });
    if (url.includes("/syllabus-documents")) return Promise.resolve({ items: [], total: 0 });
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
});

test("storage_path is a document picker (not a text input) and writes the path", async () => {
  renderPage();
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "syllabus-documents" } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  // pick the exam so the picker can scope its list
  fireEvent.focus(await screen.findByTestId("cms-field-exam_id"));
  fireEvent.mouseDown(await screen.findByTestId("cms-field-exam_id-option-e1"));

  // storage_path renders the picker search box, not a bare text input
  const sp = screen.getByTestId("cms-field-storage_path");
  fireEvent.focus(sp);
  // option id is the storage_path value (valueField), label shows filename
  const opt = await screen.findByTestId("cms-field-storage_path-option-admin/e1/syll.pdf");
  expect(opt.textContent).toMatch(/syll\.pdf/);
  fireEvent.mouseDown(opt);
  // selected chip shows the chosen value
  expect(screen.getByTestId("cms-field-storage_path-selected")).toBeTruthy();

  // documents picker was scoped to the chosen exam
  await waitFor(() => expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/documents?")));
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("exam_id=e1"));
});
