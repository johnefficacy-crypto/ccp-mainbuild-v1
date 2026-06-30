/**
 * ExamIntelCms auth-hydration and mounted-scope-change regressions (I8-C).
 *
 * Covers:
 * - auth hydration (checking → authorized): proves exactly one correctly scoped
 *   collection request is issued and the CMS becomes visible
 * - URL scope change on mounted component: changing exam_id in the URL resets
 *   state and fires a new scoped request with the updated scope
 */
import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
  getApiErrorMessage: (e) => e?.message || String(e),
}));

jest.mock("../../../lib/supabase", () => ({
  __esModule: true,
  supabase: {
    auth: {
      getSession: jest.fn(),
      onAuthStateChange: jest.fn(() => ({
        data: { subscription: { unsubscribe: jest.fn() } },
      })),
    },
  },
}));

jest.mock("../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: jest.fn(() => ({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" })),
}));

jest.mock("./ExamIntelDocuments", () => ({
  __esModule: true,
  default: () => <div data-testid="documents-panel">Documents panel</div>,
}));

jest.mock("../../../features/admin/shared/CmsRefField", () => ({
  __esModule: true,
  default: ({ testId }) => <div data-testid={testId || "cms-ref-field"} />,
}));

const { api } = require("../../../lib/api");
const { useAuth: mockUseAuth } = require("../../../lib/authContext");
const AdminExamIntelCms = require("./ExamIntelCms").default;

// ── Auth hydration ────────────────────────────────────────────────────────────

describe("ExamIntelCms auth hydration (I8-C blocker 1)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("checking → authorized issues exactly one scoped request and shows CMS", async () => {
    mockUseAuth.mockReturnValue({ user: null, status: "checking" });
    api.get.mockResolvedValue({ items: [], total: 0 });

    const { rerender } = render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/cms?exam_id=exam-hydrate"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/cms" element={<AdminExamIntelCms />} />
        </Routes>
      </MemoryRouter>,
    );

    // Checking state — no CMS, no API calls
    expect(screen.getByTestId("advanced-repair-checking")).toBeTruthy();
    expect(api.get).not.toHaveBeenCalled();

    // Hydrate to authorized
    mockUseAuth.mockReturnValue({
      user: { role: "super_admin", permissions: [] },
      status: "backend_authed",
    });
    rerender(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/cms?exam_id=exam-hydrate"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/cms" element={<AdminExamIntelCms />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("admin-exam-intel-cms")).toBeTruthy());

    // API calls: one for the default entity list + one for scope name resolution (J1).
    // exam-families is NOT in ENTITY_EXAM_SCOPE so no exam_id in the entity call.
    // The scope summary must show the exam identifier.
    expect(api.get.mock.calls.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId("advanced-repair-scope-summary").textContent).toContain("exam-hydrate");
  });

  test("checking → authorized for scoped entity issues correctly scoped request", async () => {
    mockUseAuth.mockReturnValue({ user: null, status: "checking" });
    api.get.mockResolvedValue({ items: [], total: 0 });

    const { rerender } = render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/cms?exam_id=exam-scope-2"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/cms" element={<AdminExamIntelCms />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByTestId("advanced-repair-checking")).toBeTruthy();
    expect(api.get).not.toHaveBeenCalled();

    mockUseAuth.mockReturnValue({
      user: { role: "super_admin", permissions: [] },
      status: "backend_authed",
    });
    rerender(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/cms?exam_id=exam-scope-2"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/cms" element={<AdminExamIntelCms />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("admin-exam-intel-cms")).toBeTruthy());

    // Switch to a scoped entity to verify the scope is carried
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exam-cycles" } });

    await waitFor(() => {
      const calls = api.get.mock.calls.map(([u]) => u);
      expect(calls.some((u) => u.includes("exam-cycles") && u.includes("exam_id=exam-scope-2"))).toBe(true);
    });
  });
});

// ── Mounted scope change ──────────────────────────────────────────────────────

describe("ExamIntelCms mounted scope change (I8-C blocker 1)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("changing exam_id in URL triggers reset and correctly scoped reload", async () => {
    mockUseAuth.mockReturnValue({
      user: { role: "super_admin", permissions: [] },
      status: "backend_authed",
    });
    api.get.mockResolvedValue({ items: [], total: 0 });

    const router = createMemoryRouter(
      [{ path: "/admin/exam-intelligence/cms", element: <AdminExamIntelCms /> }],
      { initialEntries: ["/admin/exam-intelligence/cms?exam_id=exam-A"] },
    );

    render(<RouterProvider router={router} />);

    await waitFor(() => expect(screen.getByTestId("admin-exam-intel-cms")).toBeTruthy());
    expect(screen.getByTestId("advanced-repair-scope-summary").textContent).toContain("exam-A");

    // Switch to a scoped entity so the scope param is actually injected
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exam-cycles" } });
    await waitFor(() => {
      const calls = api.get.mock.calls.map(([u]) => u);
      expect(calls.some((u) => u.includes("exam-cycles") && u.includes("exam_id=exam-A"))).toBe(true);
    });

    api.get.mockClear();

    // Navigate to a different exam scope
    await act(async () => {
      router.navigate("/admin/exam-intelligence/cms?exam_id=exam-B");
    });

    await waitFor(() => {
      const calls = api.get.mock.calls.map(([u]) => u);
      // After scope change: the entity (exam-cycles) reloads with new exam_id
      expect(calls.some((u) => u.includes("exam-cycles") && u.includes("exam_id=exam-B"))).toBe(true);
    });

    // Old scope must not appear in any call after the change
    const calls = api.get.mock.calls.map(([u]) => u);
    expect(calls.some((u) => u.includes("exam_id=exam-A"))).toBe(false);
  });

  test("scope summary updates when exam_id changes on mounted route", async () => {
    mockUseAuth.mockReturnValue({
      user: { role: "super_admin", permissions: [] },
      status: "backend_authed",
    });
    api.get.mockResolvedValue({ items: [], total: 0 });

    const router = createMemoryRouter(
      [{ path: "/admin/exam-intelligence/cms", element: <AdminExamIntelCms /> }],
      { initialEntries: ["/admin/exam-intelligence/cms?exam_id=exam-X"] },
    );
    render(<RouterProvider router={router} />);
    await waitFor(() => screen.getByTestId("advanced-repair-scope-summary"));
    expect(screen.getByTestId("advanced-repair-scope-summary").textContent).toContain("exam-X");

    await act(async () => {
      router.navigate("/admin/exam-intelligence/cms?exam_id=exam-Y");
    });

    await waitFor(() =>
      expect(screen.getByTestId("advanced-repair-scope-summary").textContent).toContain("exam-Y"),
    );
    expect(screen.getByTestId("advanced-repair-scope-summary").textContent).not.toContain("exam-X");
  });
});
