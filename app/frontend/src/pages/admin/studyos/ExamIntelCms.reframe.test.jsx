import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const EXAM_ROW = {
  id: "exam-row-1",
  slug: "sample-exam",
  name: "Sample Exam",
  exam_type: "recruitment",
  management_mode: null,
  is_active: true,
  created_at: "2026-06-19T00:00:00Z",
};

const CYCLE_ROW = {
  id: "cycle-row-1",
  exam_id: "exam-row-1",
  year: 2026,
  cycle_name: "Sample Cycle",
  status: "expected",
};

const examsUrl = "/api/admin/exam-intelligence-cms/exams?limit=50";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiErrorMessage: (e) => String(e),
}));

// eslint-disable-next-line global-require
const { api } = require("../../../lib/api");
// eslint-disable-next-line global-require
const AdminExamIntelCms = require("./ExamIntelCms").default;

beforeEach(() => {
  api.get.mockReset();
  api.get.mockImplementation((url) => {
    if (url === examsUrl) {
      return Promise.resolve({ items: [EXAM_ROW], total: 1 });
    }
    if (url === "/api/admin/exam-intelligence-cms/exam-cycles?limit=50") {
      return Promise.resolve({ items: [CYCLE_ROW], total: 1 });
    }
    return Promise.resolve({ items: [], total: 0 });
  });
});

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><AdminExamIntelCms /></QueryClientProvider>);
}

function selectEntity(v) {
  fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: v } });
}

// ── Wave 4.6E: Raw CMS reframed to "Advanced Import / Repair" ────────────────

test("heading is 'Advanced Import / Repair' (reframed, not 'Raw CMS / Bulk Import')", () => {
  renderPage();
  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Advanced Import / Repair");
  expect(screen.queryByText("Raw CMS / Bulk Import")).toBeNull();
});

test("shows the power-user caution banner steering to Console + Create-exam wizard", () => {
  renderPage();
  const banner = screen.getByTestId("cms-caution-banner");
  expect(banner).toBeTruthy();
  expect(banner.textContent).toMatch(/Exam Governance Console/);
  expect(banner.textContent).toMatch(/Create-exam wizard/);
  expect(banner.textContent).toMatch(/slug/); // idempotency / upsert-key warning
});

test("CMS functionality is intact — the entity selector + tool still render (regression)", () => {
  renderPage();
  expect(screen.getByTestId("admin-exam-intel-cms")).toBeTruthy();
  const vals = Array.from(screen.getByTestId("cms-entity-select").querySelectorAll("option")).map((o) => o.value);
  expect(vals).toEqual(expect.arrayContaining(["exam-topic-coverage", "pyq-questions"]));
});

test("no percentage in the reframed header copy", () => {
  renderPage();
  expect(screen.getByTestId("cms-caution-banner").textContent).not.toContain("%");
  expect(screen.getByRole("heading", { level: 1 }).textContent).not.toContain("%");
});

test("default entity does not render the removed New guided exam CTA", () => {
  renderPage();

  expect(screen.queryByTestId("cms-new-guided-exam")).toBeNull();
  expect(screen.queryByRole("link", { name: /New guided exam/i })).toBeNull();
});

test("exams entity does not render the removed New guided exam CTA", async () => {
  renderPage();
  selectEntity("exams");

  await screen.findByText("Sample Exam");

  expect(screen.queryByTestId("cms-new-guided-exam")).toBeNull();
  expect(screen.queryByRole("link", { name: /New guided exam/i })).toBeNull();
});

test("entity churn never restores the removed New guided exam CTA", async () => {
  renderPage();

  selectEntity("exams");
  await screen.findByText("Sample Exam");
  expect(screen.queryByTestId("cms-new-guided-exam")).toBeNull();
  expect(screen.queryByRole("link", { name: /New guided exam/i })).toBeNull();

  selectEntity("exam-cycles");
  await screen.findByText("Sample Cycle");
  expect(api.get).toHaveBeenCalledWith("/api/admin/exam-intelligence-cms/exam-cycles?limit=50");
  expect(screen.queryByTestId("cms-new-guided-exam")).toBeNull();
  expect(screen.queryByRole("link", { name: /New guided exam/i })).toBeNull();

  const examsCallsBeforeReturn = api.get.mock.calls.filter(([url]) => url === examsUrl).length;

  selectEntity("exams");
  await screen.findByText("Sample Exam");
  expect(api.get.mock.calls.filter(([url]) => url === examsUrl)).toHaveLength(examsCallsBeforeReturn + 1);
  expect(screen.queryByTestId("cms-new-guided-exam")).toBeNull();
  expect(screen.queryByRole("link", { name: /New guided exam/i })).toBeNull();
});

test("exams entity keeps the Reload control", async () => {
  renderPage();
  selectEntity("exams");
  await screen.findByText("Sample Exam");

  expect(screen.getByRole("button", { name: /reload/i })).toBeTruthy();
});

test("exams New row still opens the correct create form", async () => {
  renderPage();
  selectEntity("exams");
  await screen.findByText("Sample Exam");

  fireEvent.click(screen.getByRole("button", { name: /New row/i }));

  expect(screen.getByTestId("cms-create-form")).toBeTruthy();
  expect(screen.getByRole("heading", { name: "New Exams row" })).toBeTruthy();
});

test("exams Bulk import still opens the correct bulk form", async () => {
  renderPage();
  selectEntity("exams");
  await screen.findByText("Sample Exam");

  fireEvent.click(screen.getByRole("button", { name: /Bulk import/i }));

  expect(screen.getByTestId("cms-bulk-form")).toBeTruthy();
  expect(screen.getByRole("heading", { name: /Bulk import Exams/i })).toBeTruthy();
});
