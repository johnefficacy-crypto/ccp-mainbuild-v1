import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(() => Promise.resolve({ items: [], total: 0 })), post: jest.fn() },
  getApiErrorMessage: (e) => String(e),
}));

// eslint-disable-next-line global-require
const AdminExamIntelCms = require("./ExamIntelCms").default;

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><AdminExamIntelCms /></QueryClientProvider>);
}

function openEntity(value) {
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value } });
  fireEvent.click(screen.getByTestId("cms-toggle-create"));
}

test("new entities appear in the selector", () => {
  renderPage();
  const vals = Array.from(screen.getByTestId("cms-entity-select").querySelectorAll("option")).map((o) => o.value);
  expect(vals).toEqual(expect.arrayContaining(["exam-phase-sections", "exam-competition-metrics"]));
});

test("coverage form renders topic_id AND section_id as ref pickers (not raw inputs)", async () => {
  renderPage();
  openEntity("exam-topic-coverage");
  // ref pickers expose a *-options container on focus; raw inputs do not.
  const topic = await screen.findByTestId("cms-field-topic_id");
  fireEvent.focus(topic);
  expect(screen.getByTestId("cms-field-topic_id-options")).toBeTruthy();
  const section = screen.getByTestId("cms-field-section_id");
  fireEvent.focus(section);
  expect(screen.getByTestId("cms-field-section_id-options")).toBeTruthy();
});

test("section_id picker cascades by exam_phase_id (filter param)", async () => {
  // eslint-disable-next-line global-require
  const { api } = require("../../../lib/api");
  api.get.mockReset();
  api.get.mockImplementation((url) => {
    if (url.includes("/exam-phases")) return Promise.resolve({ items: [{ id: "ph1", phase_name: "T1", phase_slug: "t1" }], total: 1 });
    if (url.includes("/exams")) return Promise.resolve({ items: [{ id: "e1", name: "SSC", slug: "ssc" }], total: 1 });
    return Promise.resolve({ items: [], total: 0 });
  });
  renderPage();
  openEntity("exam-topic-coverage");
  fireEvent.focus(await screen.findByTestId("cms-field-exam_id"));
  fireEvent.mouseDown(await screen.findByTestId("cms-field-exam_id-option-e1"));
  fireEvent.focus(screen.getByTestId("cms-field-exam_phase_id"));
  fireEvent.mouseDown(await screen.findByTestId("cms-field-exam_phase_id-option-ph1"));
  fireEvent.focus(screen.getByTestId("cms-field-section_id"));
  await screen.findByTestId("cms-field-section_id-options");
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/exam-phase-sections?"));
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("exam_phase_id=ph1"));
});

test("bulk cap copy is per-entity: 2000 for pyq-questions, 500 for subjects", async () => {
  renderPage();
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "pyq-questions" } });
  fireEvent.click(screen.getByTestId("cms-toggle-bulk"));
  expect((await screen.findByTestId("cms-bulk-form")).textContent).toMatch(/max 2000/);

  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "subjects" } });
  fireEvent.click(screen.getByTestId("cms-toggle-bulk"));
  expect((await screen.findByTestId("cms-bulk-form")).textContent).toMatch(/max 500/);
});
