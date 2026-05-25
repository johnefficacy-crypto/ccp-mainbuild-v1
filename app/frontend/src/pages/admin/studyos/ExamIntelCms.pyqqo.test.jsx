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
const AdminExamIntelCms = require("./ExamIntelCms").default;

const EXAMS = [{ id: "e1", name: "SSC CGL", slug: "ssc-cgl" }];
const PAPERS = [{ id: "p1", paper_code: "CGL-24", year: 2024 }];

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><AdminExamIntelCms /></QueryClientProvider>);
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.post.mockResolvedValue({ ok: true, audit_id: "a1", question: { id: "q1" }, row: { id: "x" } });
  api.get.mockImplementation((url) => {
    if (url.includes("/pyq-questions")) return Promise.resolve({ items: [], total: 0 });
    if (url.includes("/pyq-options")) return Promise.resolve({ items: [], total: 0 });
    if (url.includes("/pyq-papers")) return Promise.resolve({ items: PAPERS, total: 1 });
    if (url.includes("/exams")) return Promise.resolve({ items: EXAMS, total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
});

test("ENTITY_CONFIG exposes both pyq-questions and pyq-options with their controls", async () => {
  renderPage();
  const sel = screen.getByTestId("cms-entity-select");
  const vals = Array.from(sel.querySelectorAll("option")).map((o) => o.value);
  expect(vals).toEqual(expect.arrayContaining(["pyq-questions", "pyq-options"]));

  fireEvent.change(sel, { target: { value: "pyq-questions" } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));
  const qtype = await screen.findByTestId("cms-field-question_type");
  expect(qtype.tagName).toBe("SELECT");
  expect(Array.from(qtype.querySelectorAll("option")).map((o) => o.value)).toEqual(
    expect.arrayContaining(["mcq", "numerical", "matching"]),
  );

  fireEvent.change(sel, { target: { value: "pyq-options" } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));
  const label = await screen.findByTestId("cms-field-option_label");
  expect(Array.from(label.querySelectorAll("option")).map((o) => o.value)).toEqual(
    expect.arrayContaining(["A", "B", "C", "D", "E"]),
  );
  // both entities support bulk
  expect(screen.getByTestId("cms-toggle-bulk")).toBeTruthy();
});

test("pyq-questions create submits to the pyq-questions endpoint (paper scoped to exam)", async () => {
  renderPage();
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "pyq-questions" } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));

  fireEvent.focus(await screen.findByTestId("cms-field-exam_id"));
  fireEvent.mouseDown(await screen.findByTestId("cms-field-exam_id-option-e1"));
  fireEvent.focus(screen.getByTestId("cms-field-pyq_paper_id"));
  fireEvent.mouseDown(await screen.findByTestId("cms-field-pyq_paper_id-option-p1"));
  fireEvent.change(screen.getByTestId("cms-field-question_text"), { target: { value: "10% of 200?" } });
  fireEvent.change(screen.getByTestId("cms-reason"), { target: { value: "seeding a question" } });
  fireEvent.click(screen.getByTestId("cms-create-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(expect.stringContaining("/pyq-questions"), expect.anything()));
  const [, body] = api.post.mock.calls.find(([u]) => u.endsWith("/pyq-questions"));
  expect(body.payload.pyq_paper_id).toBe("p1");
  expect(body.payload.question_text).toBe("10% of 200?");
  expect("exam_id" in body.payload).toBe(false); // ui-only scope not submitted
});
