import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route, Navigate } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

jest.mock("../../../lib/authContext", () => ({
  useAuth: () => ({ user: { email: "tester@example.com", role: "admin" }, logout: jest.fn() }),
}));

jest.mock("../../../features/admin/exam-intelligence/ExamIntelligenceOverviewCards", () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock("../../../features/admin/exam-intelligence/ExamListTable", () => ({
  __esModule: true,
  default: ({ items }) => {
    const { createElement } = require("react");
    const rows = Array.isArray(items) ? items : [];
    return createElement(
      "div",
      { "data-testid": "exam-list-table" },
      rows.map((e) =>
        createElement(
          "a",
          {
            key: e.id,
            href: `/admin/exam-intelligence/workspace/${e.id}`,
            "data-testid": `exam-intel-workspace-${e.slug}`,
          },
          e.name,
        ),
      ),
    );
  },
}));

import { api } from "../../../lib/api";
import AdminExamIntelligence from "../ExamIntelligence";
import AdminShell from "../AdminShell";

jest.mock("../studyos/ExamIntelCms", () => ({
  __esModule: true,
  default: () => <div data-testid="exam-intel-cms-page">CMS page</div>,
}));

beforeEach(() => {
  api.get.mockResolvedValue({ items: [], count: 0 });
  try { window.localStorage.setItem("cc-admin-nav-open", "1"); } catch { /* ignore */ }
});

afterEach(() => {
  api.get.mockReset();
});

// ── 1. redirect: /admin/study-os/exam-intel-cms → /admin/exam-intelligence/cms ──

test("study-os/exam-intel-cms redirects to /admin/exam-intelligence/cms", () => {
  render(
    <MemoryRouter initialEntries={["/admin/study-os/exam-intel-cms"]}>
      <Routes>
        <Route
          path="/admin/study-os/exam-intel-cms"
          element={<Navigate to="/admin/exam-intelligence/cms" replace />}
        />
        <Route
          path="/admin/exam-intelligence/cms"
          element={<div data-testid="exam-intel-cms-landing">cms landing</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByTestId("exam-intel-cms-landing")).toBeTruthy();
});

// ── 2. ExamIntelligence page does NOT render the 5 removed operational tabs ──

test("ExamIntelligence landing does not render removed operational tabs", async () => {
  api.get.mockResolvedValue({ items: [], count: 0 });
  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );

  await waitFor(() => expect(api.get).toHaveBeenCalled());

  expect(screen.queryByTestId("exam-intel-tab-review")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-coverage")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-competition")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-policy")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-impact")).toBeNull();

  expect(screen.getByTestId("exam-intel-tab-overview")).toBeTruthy();
  expect(screen.getByTestId("exam-intel-tab-exams")).toBeTruthy();
});

// ── 3. Exam row "Open workspace" link targets /workspace/:exam_id ──

test("exam row Open workspace link routes to /admin/exam-intelligence/workspace/:exam_id", async () => {
  api.get.mockResolvedValueOnce({ items: [], count: 0 }); // overview
  api.get.mockResolvedValueOnce({
    items: [{ id: "exam-abc", slug: "upsc-cse", name: "UPSC CSE", exam_type: "civil_services" }],
    count: 1,
  }); // exams

  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );

  const examsTab = await screen.findByTestId("exam-intel-tab-exams");
  fireEvent.click(examsTab);

  await waitFor(() =>
    expect(screen.getByTestId("exam-intel-workspace-upsc-cse")).toBeTruthy(),
  );

  const link = screen.getByTestId("exam-intel-workspace-upsc-cse");
  expect(link.getAttribute("href")).toBe("/admin/exam-intelligence/workspace/exam-abc");
});

// ── 4. AdminShell header reflects current page title ──

test("AdminShell header shows dynamic page title for exam-intelligence", () => {
  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <Routes>
        <Route element={<AdminShell />}>
          <Route path="/admin/exam-intelligence" element={<div>exam intel page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );

  const h1 = screen.getByRole("heading", { level: 1 });
  expect(h1.textContent).toBe("Exam Registry");
  expect(h1.textContent).not.toBe("Admin operations console");
});

// ── 5a. /admin/exam-intelligence/cms route renders ExamIntelCms ──

test("cms route renders ExamIntelCms", async () => {
  const { Suspense } = require("react");
  const AdminExamIntelCms = require("../studyos/ExamIntelCms").default;
  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence/cms"]}>
      <Routes>
        <Route
          path="/admin/exam-intelligence/cms"
          element={
            <Suspense fallback={null}>
              <AdminExamIntelCms />
            </Suspense>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() =>
    expect(screen.getByTestId("exam-intel-cms-page")).toBeTruthy(),
  );
});

// ── 5b. ExamIntelligence page shows Create / Import CMS link ──

test("ExamIntelligence page has Create / Import CMS link to /admin/exam-intelligence/cms", async () => {
  api.get.mockResolvedValue({ items: [], count: 0 });
  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  const link = screen.getByTestId("exam-intel-cms-link");
  expect(link).toBeTruthy();
  expect(link.getAttribute("href")).toBe("/admin/exam-intelligence/cms");
});

// ── 5. Exam Intel CMS entry is absent from the Study OS sidebar group ──

test("Exam Intel CMS link is removed from the Study OS sidebar section", () => {
  render(
    <MemoryRouter initialEntries={["/admin"]}>
      <Routes>
        <Route element={<AdminShell />}>
          <Route path="/admin" element={<div>overview</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );

  expect(screen.queryByTestId("admin-nav-studyos-exam-intel-cms")).toBeNull();
});
