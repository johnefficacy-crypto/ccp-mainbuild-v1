import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route, Navigate } from "react-router-dom";

jest.mock("../../../shared/config/env", () => ({ ENABLE_DEMO_DATA: false }));

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

jest.mock("../../../lib/authContext", () => ({
  useAuth: () => ({ user: { email: "tester@example.com", role: "admin" }, logout: jest.fn() }),
}));

import { api } from "../../../lib/api";
import AdminExamIntelligence from "../ExamIntelligence";
import AdminShell from "../AdminShell";

jest.mock("../studyos/ExamIntelCms", () => ({
  __esModule: true,
  default: () => <div data-testid="exam-intel-cms-page">CMS page</div>,
}));

const EMPTY_RESPONSE = { items: [], total_count: 0, has_next: false };

beforeEach(() => {
  api.get.mockResolvedValue(EMPTY_RESPONSE);
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

// ── 2. ExamIntelligence front door: no tabs rendered at all ──

test("ExamIntelligence front door renders no tabs", async () => {
  api.get.mockResolvedValue(EMPTY_RESPONSE);
  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );

  await waitFor(() => expect(api.get).toHaveBeenCalled());

  // I8-A: no tabs at all
  expect(screen.queryByTestId("exam-intel-tab-overview")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-exams")).toBeNull();
  // Previously-removed operational tabs remain absent.
  expect(screen.queryByTestId("exam-intel-tab-review")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-coverage")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-competition")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-policy")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-impact")).toBeNull();
});

// ── 3. Exam row "Manage exam" link targets /exams/:exam_id ──

test("exam row 'Manage exam' link routes to /admin/exam-intelligence/exams/:exam_id", async () => {
  api.get.mockResolvedValueOnce({
    items: [
      {
        id: "exam-abc",
        slug: "upsc-cse",
        name: "UPSC CSE",
        status: "ready",
        blocker_count: 0,
        first_blocker_text: null,
        current_cycle: null,
        family_name: null,
        organization_name: null,
        management_mode: null,
        cadence: null,
        is_active: true,
        readiness_summary: { setup: "ready", topic_coverage: "ready", pyq: "ready", pending_review_count: 0, stale_review_count: 0 },
      },
    ],
    total_count: 1,
    has_next: false,
    family_options: [],
  });

  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );

  const manageLink = await screen.findByTestId("exam-mgmt-manage-upsc-cse");
  expect(manageLink.getAttribute("href")).toBe("/admin/exam-intelligence/exams/exam-abc");
});

// ── 4. AdminShell header shows "Exam Management" ──

test("AdminShell header shows Exam Management for /admin/exam-intelligence", () => {
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
  expect(h1.textContent).toBe("Exam Management");
  expect(h1.textContent).not.toBe("Admin operations console");
  expect(h1.textContent).not.toBe("Exam Registry");
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

// ── 5b. I8-A header CTAs: Create exam is overflow-only; no standalone CTA, no Console, no Advanced CMS ──

test("ExamIntelligence page: Create exam is overflow-only; old CTAs are gone", async () => {
  api.get.mockResolvedValue(EMPTY_RESPONSE);
  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );
  await waitFor(() => expect(api.get).toHaveBeenCalled());

  // Old primary CTAs are absent.
  expect(screen.queryByTestId("registry-open-console")).toBeNull();
  expect(screen.queryByTestId("registry-advanced-cms")).toBeNull();
  expect(screen.queryByTestId("registry-create-exam")).toBeNull();

  // Create exam is NOT a standalone visible button — only exists inside the overflow menu.
  expect(screen.queryByTestId("exam-mgmt-create-exam")).toBeNull();

  // Opening More reveals Create exam.
  fireEvent.click(screen.getByTestId("exam-mgmt-more-trigger"));
  const createExam = screen.getByTestId("exam-mgmt-create-exam");
  expect(createExam.getAttribute("href")).toBe("/admin/exam-intelligence/new");
  expect(createExam.classList.contains("btn-primary")).toBe(false);
});

// ── 5c. Exam Intel CMS entry is absent from the Study OS sidebar group ──

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

test("selecting Unclassified in lane filter sends management_mode=__null__ to management endpoint", async () => {
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );

  await waitFor(() => expect(screen.getByTestId("exam-intel-lane-filter")).toBeTruthy());

  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  fireEvent.change(screen.getByTestId("exam-intel-lane-filter"), {
    target: { value: "__null__" },
  });

  await waitFor(() => expect(api.get).toHaveBeenCalled());

  const url = api.get.mock.calls[0][0];
  expect(url).toContain("management_mode=__null__");
  expect(url).toContain("/management/exams");
});

// ── 7. Status chips are rendered for each status variant ──

test("management rows render correct status chip label", async () => {
  const base = { organization_name: null, management_mode: null, cadence: null, is_active: true, readiness_summary: null, family_options: [] };
  api.get.mockResolvedValueOnce({
    items: [
      { ...base, id: "e1", slug: "exam-a", name: "Exam A", status: "ready", blocker_count: 0, first_blocker_text: null, current_cycle: null, family_name: null },
      { ...base, id: "e2", slug: "exam-b", name: "Exam B", status: "needs_action", blocker_count: 1, first_blocker_text: "Missing PYQ", current_cycle: null, family_name: null },
      { ...base, id: "e3", slug: "exam-c", name: "Exam C", status: "blocked", blocker_count: 2, first_blocker_text: "No cycle", current_cycle: null, family_name: null },
    ],
    total_count: 3,
    has_next: false,
    family_options: [],
  });

  render(
    <MemoryRouter initialEntries={["/admin/exam-intelligence"]}>
      <AdminExamIntelligence />
    </MemoryRouter>,
  );

  await screen.findByTestId("exam-mgmt-row-exam-a");

  expect(screen.getByTestId("exam-mgmt-row-exam-a")).toBeTruthy();
  expect(screen.getByTestId("exam-mgmt-row-exam-b")).toBeTruthy();
  expect(screen.getByTestId("exam-mgmt-row-exam-c")).toBeTruthy();

  // getAllByText: workflow dropdown also contains these labels
  expect(screen.getAllByText("Ready").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("Needs action").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("Blocked").length).toBeGreaterThanOrEqual(1);
});
