/**
 * ExamIntelCms access-control and scope tests (I8-C).
 *
 * Covers:
 * - Auth checking state (loading indicator, no CMS UI)
 * - Denied access — zero API calls, denied message shown
 * - exam_intelligence.cms grants scoped access (exam_id param)
 * - super_admin required for global (no exam_id) access
 * - AdminSafetyBanner visible on authorized render
 * - Old caution copy ("Exam Governance Console", "Create-exam wizard") absent
 * - Scoped list requests include correct exam_id / exam_cycle_id params
 * - Unsupported entities do not receive invented scope params
 * - Scope summary renders when exam_id or cycle_id is present
 * - Entity switch preserves scope (scope summary stays visible)
 * - Create form prefills exam_id and exam_cycle_id for applicable entities
 */
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

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

// Stub heavy sub-components so they don't fire real API calls
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

// Lazy-require after mocks are set
const AdminExamIntelCms = require("./ExamIntelCms").default;

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderCms(search = "") {
  const path = `/admin/exam-intelligence/cms${search}`;
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/exam-intelligence/cms" element={<AdminExamIntelCms />} />
      </Routes>
    </MemoryRouter>,
  );
}

function mockDefaultApiResponse() {
  api.get.mockResolvedValue({ items: [], total: 0 });
}

// ── Auth checking state ───────────────────────────────────────────────────────

describe("ExamIntelCms auth checking state", () => {
  beforeEach(() => jest.clearAllMocks());

  test("shows checking indicator while auth status is 'checking'", () => {
    mockUseAuth.mockReturnValue({ user: null, status: "checking" });
    renderCms();
    expect(screen.getByTestId("advanced-repair-checking")).toBeTruthy();
    // CMS controls must not be visible
    expect(screen.queryByTestId("admin-exam-intel-cms")).toBeNull();
    // No API calls during auth check
    expect(api.get).not.toHaveBeenCalled();
  });
});

// ── Access denied ─────────────────────────────────────────────────────────────

describe("ExamIntelCms access denied", () => {
  beforeEach(() => jest.clearAllMocks());

  test("denied for plain admin visiting global CMS (no exam_id)", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "admin", permissions: [] }, status: "backend_authed" });
    renderCms();
    expect(screen.getByTestId("advanced-repair-denied")).toBeTruthy();
    expect(screen.queryByTestId("admin-exam-intel-cms")).toBeNull();
    expect(api.get).not.toHaveBeenCalled();
  });

  test("denied for admin with cms permission visiting global CMS (super_admin only)", async () => {
    mockUseAuth.mockReturnValue({
      user: { role: "admin", permissions: ["exam_intelligence.cms"] },
      status: "backend_authed",
    });
    // No exam_id in URL → requires super_admin
    renderCms();
    expect(screen.getByTestId("advanced-repair-denied")).toBeTruthy();
    expect(api.get).not.toHaveBeenCalled();
  });

  test("denied for unauthenticated user visiting scoped CMS", async () => {
    mockUseAuth.mockReturnValue({ user: null, status: "backend_authed" });
    renderCms("?exam_id=exam-1");
    expect(screen.getByTestId("advanced-repair-denied")).toBeTruthy();
    expect(api.get).not.toHaveBeenCalled();
  });
});

// ── Authorized access ─────────────────────────────────────────────────────────

describe("ExamIntelCms authorized access", () => {
  beforeEach(() => jest.clearAllMocks());

  test("super_admin can access global CMS (no exam_id)", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    mockDefaultApiResponse();
    renderCms();
    await waitFor(() => expect(screen.getByTestId("admin-exam-intel-cms")).toBeTruthy());
  });

  test("admin with exam_intelligence.cms can access scoped CMS", async () => {
    mockUseAuth.mockReturnValue({
      user: { role: "admin", permissions: ["exam_intelligence.cms"] },
      status: "backend_authed",
    });
    mockDefaultApiResponse();
    renderCms("?exam_id=exam-1");
    await waitFor(() => expect(screen.getByTestId("admin-exam-intel-cms")).toBeTruthy());
  });

  test("super_admin can access scoped CMS", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    mockDefaultApiResponse();
    renderCms("?exam_id=exam-1");
    await waitFor(() => expect(screen.getByTestId("admin-exam-intel-cms")).toBeTruthy());
  });
});

// ── AdminSafetyBanner ─────────────────────────────────────────────────────────

describe("ExamIntelCms AdminSafetyBanner (I8-C)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("AdminSafetyBanner is visible on authorized render", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    mockDefaultApiResponse();
    renderCms();
    await waitFor(() => expect(screen.getByTestId("advanced-repair-safety-banner")).toBeTruthy());
  });

  test("old caution copy ('Exam Governance Console') is absent", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    mockDefaultApiResponse();
    renderCms();
    await waitFor(() => screen.getByTestId("advanced-repair-safety-banner"));
    expect(screen.queryByText(/Exam Governance Console/)).toBeNull();
  });

  test("old caution copy ('Create-exam wizard') is absent", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    mockDefaultApiResponse();
    renderCms();
    await waitFor(() => screen.getByTestId("advanced-repair-safety-banner"));
    expect(screen.queryByText(/Create-exam wizard/)).toBeNull();
  });

  test("old cms-caution-banner testId is absent", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    mockDefaultApiResponse();
    renderCms();
    await waitFor(() => screen.getByTestId("advanced-repair-safety-banner"));
    expect(screen.queryByTestId("cms-caution-banner")).toBeNull();
  });
});

// ── Scope summary ─────────────────────────────────────────────────────────────

describe("ExamIntelCms scope summary (I8-C)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("scope summary visible when exam_id present", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    mockDefaultApiResponse();
    renderCms("?exam_id=exam-abc");
    await waitFor(() => screen.getByTestId("advanced-repair-scope-summary"));
    expect(screen.getByTestId("advanced-repair-scope-summary").textContent).toContain("exam-abc");
  });

  test("scope summary includes cycle_id when both params present", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    mockDefaultApiResponse();
    renderCms("?exam_id=exam-abc&cycle_id=cycle-2026");
    await waitFor(() => screen.getByTestId("advanced-repair-scope-summary"));
    const summary = screen.getByTestId("advanced-repair-scope-summary");
    expect(summary.textContent).toContain("exam-abc");
    expect(summary.textContent).toContain("cycle-2026");
  });

  test("scope summary absent when no exam_id or cycle_id", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    mockDefaultApiResponse();
    renderCms();
    await waitFor(() => screen.getByTestId("admin-exam-intel-cms"));
    expect(screen.queryByTestId("advanced-repair-scope-summary")).toBeNull();
  });
});

// ── Scoped list requests ──────────────────────────────────────────────────────

describe("ExamIntelCms scoped list requests (I8-C)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("exam-cycles list request includes exam_id param when scoped", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    api.get.mockResolvedValue({ items: [], total: 0 });
    renderCms("?exam_id=exam-scope-1");

    // Default entity is exam-families (no exam_id filter). Switch to exam-cycles.
    await waitFor(() => screen.getByTestId("cms-entity-select"));
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exam-cycles" } });

    await waitFor(() => {
      const calls = api.get.mock.calls.map(([u]) => u);
      return calls.some((u) => u.includes("exam-cycles") && u.includes("exam_id=exam-scope-1"));
    });

    const calls = api.get.mock.calls.map(([u]) => u);
    expect(calls.some((u) => u.includes("exam-cycles") && u.includes("exam_id=exam-scope-1"))).toBe(true);
  });

  test("exam-phases list request includes exam_cycle_id when cycle_id scoped", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    api.get.mockResolvedValue({ items: [], total: 0 });
    renderCms("?exam_id=exam-1&cycle_id=cycle-2026");

    await waitFor(() => screen.getByTestId("cms-entity-select"));
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exam-phases" } });

    await waitFor(() => {
      const calls = api.get.mock.calls.map(([u]) => u);
      return calls.some((u) => u.includes("exam-phases") && u.includes("exam_cycle_id=cycle-2026"));
    });

    const calls = api.get.mock.calls.map(([u]) => u);
    expect(calls.some((u) => u.includes("exam-phases") && u.includes("exam_cycle_id=cycle-2026"))).toBe(true);
  });

  test("exams entity does not receive invented exam_id scope param", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    api.get.mockResolvedValue({ items: [], total: 0 });
    renderCms("?exam_id=exam-1");

    // Default is exam-families; switch to "exams" (not in ENTITY_EXAM_SCOPE)
    await waitFor(() => screen.getByTestId("cms-entity-select"));
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exams" } });

    await waitFor(() => {
      const calls = api.get.mock.calls.map(([u]) => u);
      return calls.some((u) => u.includes("/exams?"));
    });

    const calls = api.get.mock.calls.map(([u]) => u);
    const examsCalls = calls.filter((u) => u.includes("/exam-intelligence-cms/exams?"));
    expect(examsCalls.length).toBeGreaterThan(0);
    // "exams" entity should NOT have exam_id filter injected
    expect(examsCalls.every((u) => !u.includes("exam_id="))).toBe(true);
  });

  test("scope persists across entity switch", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    api.get.mockResolvedValue({ items: [], total: 0 });
    renderCms("?exam_id=exam-scope-persist");

    await waitFor(() => screen.getByTestId("cms-entity-select"));

    // Switch to exam-cycles (scoped entity)
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exam-cycles" } });

    await waitFor(() => {
      const calls = api.get.mock.calls.map(([u]) => u);
      return calls.some((u) => u.includes("exam-cycles") && u.includes("exam_id=exam-scope-persist"));
    });

    // Scope summary still visible
    expect(screen.getByTestId("advanced-repair-scope-summary")).toBeTruthy();
  });
});

// ── Create form prefill ───────────────────────────────────────────────────────

describe("ExamIntelCms create form scope prefill (I8-C)", () => {
  beforeEach(() => jest.clearAllMocks());

  test("create form opens for exam-cycles without crashing (prefill does not throw)", async () => {
    mockUseAuth.mockReturnValue({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" });
    api.get.mockResolvedValue({ items: [], total: 0 });
    renderCms("?exam_id=exam-prefill-1");

    await waitFor(() => screen.getByTestId("cms-entity-select"));
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exam-cycles" } });

    // Open create form — verifies the entity switch + prefill logic doesn't throw
    const toggleBtn = await waitFor(() => screen.getByTestId("cms-toggle-create"));
    fireEvent.click(toggleBtn);

    await waitFor(() => expect(screen.getByTestId("cms-create-form")).toBeTruthy());
  });
});
