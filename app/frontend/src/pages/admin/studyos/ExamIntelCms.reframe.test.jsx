import React from "react";
import { render, screen } from "@testing-library/react";
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
