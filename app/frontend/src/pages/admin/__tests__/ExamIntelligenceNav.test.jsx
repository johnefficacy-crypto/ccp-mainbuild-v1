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
  api.get.mockResolvedValueOnce({ items: [], count: 0 }); // families (fires first on mount)
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

// ── 5b. Registry CTAs (B3d-1): Open console is the sole primary header action ──

test("ExamIntelligence page makes Open console the sole Registry header primary action", async () => {
  api.get.mockResolvedValue({ items: [], count: 0 });
  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );
  await waitFor(() => expect(api.get).toHaveBeenCalled());

  // The old primary "Create / Import CMS" CTA is gone.
  expect(screen.queryByTestId("exam-intel-cms-link")).toBeNull();
  expect(screen.queryByText("Create / Import CMS")).toBeNull();

  const console_ = screen.getByTestId("registry-open-console");
  const create = screen.getByTestId("registry-create-exam");
  const advanced = screen.getByTestId("registry-advanced-cms");

  expect(console_.getAttribute("href")).toBe("/admin/exam-intelligence/console");
  expect(create.getAttribute("href")).toBe("/admin/exam-intelligence/new");
  expect(advanced.getAttribute("href")).toBe("/admin/exam-intelligence/cms");

  expect(console_.classList.contains("btn-primary")).toBe(true);
  expect(console_.classList.contains("btn-ghost")).toBe(false);
  expect(create.classList.contains("btn-ghost")).toBe(true);
  expect(create.classList.contains("btn-primary")).toBe(false);
  expect(advanced.classList.contains("btn-ghost")).toBe(true);
  expect(advanced.classList.contains("btn-primary")).toBe(false);

  const primaryActions = [console_, create, advanced].filter((el) =>
    el.classList.contains("btn-primary"),
  );
  expect(primaryActions.length).toBe(1);
  expect(primaryActions[0]).toBe(console_);

  expect(console_.compareDocumentPosition(create) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(create.compareDocumentPosition(advanced) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
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

// ── 6. __null__ sentinel wire ──────────────────────────────────────────────

test("selecting Unclassified in lane filter sends management_mode=__null__ to API", async () => {
  api.get.mockResolvedValue({ items: [], count: 0 });

  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );

  // Switch to exams tab
  const examsTab = await screen.findByTestId("exam-intel-tab-exams");
  fireEvent.click(examsTab);

  await waitFor(() => expect(screen.getByTestId("exam-intel-lane-filter")).toBeTruthy());

  api.get.mockClear();
  api.get.mockResolvedValue({ items: [], count: 0 });

  fireEvent.change(screen.getByTestId("exam-intel-lane-filter"), {
    target: { value: "__null__" },
  });

  await waitFor(() => expect(api.get).toHaveBeenCalled());

  const url = api.get.mock.calls[0][0];
  expect(url).toContain("management_mode=__null__");
});

// ── 7. family filter wire ──────────────────────────────────────────────────

test("selecting a family adds exam_family_id to exam-list request", async () => {
  // families returns one entry
  api.get.mockImplementation((url) => {
    if (url.includes("exam-families")) {
      return Promise.resolve({ items: [{ id: "fam-1", name: "UPSC Family" }], count: 1 });
    }
    return Promise.resolve({ items: [], count: 0 });
  });

  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );

  const examsTab = await screen.findByTestId("exam-intel-tab-exams");
  fireEvent.click(examsTab);

  // Wait for family filter to appear
  await waitFor(() => expect(screen.getByTestId("exam-intel-family-filter")).toBeTruthy());

  api.get.mockClear();
  api.get.mockImplementation((url) => {
    if (url.includes("exam-families")) {
      return Promise.resolve({ items: [{ id: "fam-1", name: "UPSC Family" }], count: 1 });
    }
    return Promise.resolve({ items: [], count: 0 });
  });

  fireEvent.change(screen.getByTestId("exam-intel-family-filter"), {
    target: { value: "fam-1" },
  });

  await waitFor(() =>
    api.get.mock.calls.some((c) => c[0].includes("exam_family_id")),
  );

  const examUrl = api.get.mock.calls.find((c) => c[0].includes("exam_family_id"))?.[0];
  expect(examUrl).toContain("exam_family_id=fam-1");
});
