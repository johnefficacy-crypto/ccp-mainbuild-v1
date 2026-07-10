import React from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// ExamDetailAnchorNav uses IntersectionObserver which jsdom does not provide.
global.IntersectionObserver = class {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
};
import { render, screen } from "@testing-library/react";
import ExamDetail from "./ExamDetail";

jest.mock("../lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(() => Promise.resolve()),
  },
}));

function renderExamDetail(slug = "upsc-cse") {
  const { api } = require("../lib/api");
  // Provide a matched recruitment so the full detail view renders (not the no-cycle branch).
  api.get.mockImplementation((url) => {
    if (url.includes("/api/exams/")) return Promise.resolve({ exam: { id: "e1", name: "UPSC CSE", slug } });
    if (url === "/api/recruitments") return Promise.resolve({ items: [{ id: "r1", exam_id: "e1", apply_window: { close: "2026-12-01" } }] });
    if (url.includes("/api/recruitments/r1")) return Promise.resolve({ id: "r1", name: "UPSC CSE 2026", organization: "UPSC", eligibility_preview: { verdict: "pending", fail_reasons: [] }, posts: [] });
    return Promise.resolve({});
  });

  return render(
    <MemoryRouter initialEntries={[`/app/eligibility/exams/${slug}`]}>
      <Routes>
        <Route path="/app/eligibility/exams/:slug" element={<ExamDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

test("parent link copy is 'All exams', not 'All recruitments'", async () => {
  renderExamDetail();
  const link = await screen.findByText("All exams");
  expect(link).toBeTruthy();
  expect(screen.queryByText("All recruitments")).toBeNull();
});

function renderExamDetailNoCycle(slug = "upsc-cse") {
  const { api } = require("../lib/api");
  // Exam resolves, but no recruitment maps to it — the exam-only render path.
  api.get.mockImplementation((url) => {
    if (url.includes("/api/exams/")) return Promise.resolve({ exam: { id: "e1", name: "UPSC CSE", slug } });
    if (url === "/api/recruitments") return Promise.resolve({ items: [] });
    return Promise.resolve({});
  });

  return render(
    <MemoryRouter initialEntries={[`/app/eligibility/exams/${slug}`]}>
      <Routes>
        <Route path="/app/eligibility/exams/:slug" element={<ExamDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

test("renders PYQ Explorer (exam intelligence) even when no recruitment cycle exists", async () => {
  renderExamDetailNoCycle();
  // Exam-level intelligence stays visible.
  expect(await screen.findByTestId("pyq-explorer")).toBeTruthy();
  // A single no-active-cycle banner replaces the repeated recruitment panels.
  expect(screen.getByTestId("no-cycle-banner")).toBeTruthy();
  // Recruitment-only sections are hidden entirely (not shown as empty panels).
  expect(screen.queryByTestId("eligibility-panel")).toBeNull();
  // Recruitment-only actions are hidden.
  expect(screen.queryByTestId("detail-save-btn")).toBeNull();
  expect(screen.queryByTestId("detail-track-btn")).toBeNull();
  expect(screen.queryByTestId("detail-official-link")).toBeNull();
});
