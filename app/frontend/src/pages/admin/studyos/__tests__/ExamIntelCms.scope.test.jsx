/**
 * J1 acceptance tests for ExamIntelCms.jsx scope indicator, search, status filter,
 * and pagination controls (Section G of Advanced-Repair-Scoping-Gate-2026-06-29.md).
 *
 * Note: this repo's CRA setup has no @testing-library/jest-dom; assertions use
 * plain Jest matchers (queryBy*-null, toBeTruthy, etc.) only.
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// ── mutable search params state ──────────────────────────────────────────────
let mockSearchParamsRaw = {};
let mockSetSearchParams = jest.fn((updater) => {
  if (typeof updater === "function") {
    const next = new URLSearchParams(mockSearchParamsRaw);
    updater(next);
    mockSearchParamsRaw = Object.fromEntries(next.entries());
  } else if (updater instanceof URLSearchParams) {
    mockSearchParamsRaw = Object.fromEntries(updater.entries());
  } else {
    mockSearchParamsRaw = updater || {};
  }
});

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useSearchParams: () => {
    const sp = new URLSearchParams(mockSearchParamsRaw);
    return [sp, mockSetSearchParams];
  },
}));

jest.mock("../../../../lib/supabase", () => ({
  __esModule: true,
  supabase: {
    auth: {
      getSession: jest.fn(),
      onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })),
    },
  },
}));

jest.mock("../../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({ user: { role: "super_admin", permissions: [] }, status: "backend_authed" }),
}));

jest.mock("../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), del: jest.fn() },
  getApiErrorMessage: (e) => e?.message || "error",
}));

jest.mock("../../../../features/admin/shared/CmsRefField", () => ({
  __esModule: true,
  default: ({ testId }) => <input data-testid={testId} defaultValue="" />,
}));

jest.mock("../../../../shared/ui/heavy", () => ({
  DateField: () => null,
}));

jest.mock("../ExamIntelDocuments", () => ({
  __esModule: true,
  default: () => null,
}));

const { api } = require("../../../../lib/api");
const ExamIntelCms = require("../ExamIntelCms").default;

// ── helpers ───────────────────────────────────────────────────────────────────

function makeListResponse(items = [], total = items.length) {
  return { items, total };
}

const EXAM_ID = "exam-uuid-1";
const CYCLE_ID = "cycle-uuid-1";
const EXAM_NAME = "UPSC Civil Services";
const CYCLE_NAME = "2026 Cycle";

function setupDefaultMocks() {
  api.get.mockImplementation((url) => {
    if (url.includes("/exams?")) return Promise.resolve(makeListResponse([{ id: EXAM_ID, name: EXAM_NAME }]));
    if (url.includes("/exam-cycles?")) return Promise.resolve(makeListResponse([{ id: CYCLE_ID, cycle_name: CYCLE_NAME }]));
    if (url.includes("/admin/organizations")) return Promise.resolve({ items: [] });
    return Promise.resolve(makeListResponse([], 0));
  });
}

function renderCms() {
  return render(<ExamIntelCms />);
}

// ── Section G.1: scope indicator tests ───────────────────────────────────────

describe("G.1 Scope indicator", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSetSearchParams.mockClear();
    setupDefaultMocks();
  });

  test("scope indicator is NOT rendered when neither param is present", async () => {
    mockSearchParamsRaw = {};
    renderCms();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByTestId("advanced-repair-scope-summary")).toBeNull();
  });

  test("scope indicator renders exam name when exam_id is present", async () => {
    mockSearchParamsRaw = { exam_id: EXAM_ID };
    renderCms();
    await waitFor(() => {
      const el = screen.queryByTestId("scope-exam-name");
      return el && el.textContent === EXAM_NAME;
    });
    expect(screen.getByTestId("scope-exam-name").textContent).toBe(EXAM_NAME);
  });

  test("scope indicator includes cycle name when cycle_id is also present", async () => {
    mockSearchParamsRaw = { exam_id: EXAM_ID, cycle_id: CYCLE_ID };
    renderCms();
    await waitFor(() => {
      const el = screen.queryByTestId("scope-cycle-name");
      return el && el.textContent === CYCLE_NAME;
    });
    expect(screen.getByTestId("scope-cycle-name").textContent).toBe(CYCLE_NAME);
  });

  test("Clear scope button calls setSearchParams removing exam_id and cycle_id", async () => {
    mockSearchParamsRaw = { exam_id: EXAM_ID, cycle_id: CYCLE_ID };
    renderCms();
    const clearBtn = await screen.findByTestId("scope-clear-btn");
    fireEvent.click(clearBtn);
    expect(mockSetSearchParams).toHaveBeenCalled();
    // The argument passed to setSearchParams must not contain exam_id or cycle_id
    const arg = mockSetSearchParams.mock.calls[mockSetSearchParams.mock.calls.length - 1][0];
    // arg is a URLSearchParams instance — convert to string to verify
    const argString = arg instanceof URLSearchParams ? arg.toString() : String(arg);
    expect(argString).not.toMatch(/exam_id/);
    expect(argString).not.toMatch(/cycle_id/);
  });

  test("non-scopable entity shows 'not scoped by exam' note when exam_id present", async () => {
    mockSearchParamsRaw = { exam_id: EXAM_ID };
    renderCms();
    // Default entity is exam-families which is not in ENTITY_EXAM_SCOPE
    await screen.findByTestId("advanced-repair-scope-summary");
    const note = screen.queryByTestId("scope-not-scoped-note");
    expect(note).toBeTruthy();
  });

  test("scopable entity (exam-cycles) does NOT show 'not scoped by exam' note", async () => {
    mockSearchParamsRaw = { exam_id: EXAM_ID };
    renderCms();
    await screen.findByTestId("cms-entity-select");
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exam-cycles" } });
    await waitFor(() => {
      return screen.queryByTestId("scope-not-scoped-note") === null;
    });
    expect(screen.queryByTestId("scope-not-scoped-note")).toBeNull();
  });
});

// ── Section G.2: Search input tests ──────────────────────────────────────────

describe("G.2 Search input", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSetSearchParams.mockClear();
    setupDefaultMocks();
  });

  test("search input is rendered", async () => {
    mockSearchParamsRaw = {};
    renderCms();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.getByTestId("cms-search-input")).toBeTruthy();
  });

  test("typing in search input sends search param to backend after debounce", async () => {
    jest.useFakeTimers();
    mockSearchParamsRaw = { exam_id: EXAM_ID };
    renderCms();
    await screen.findByTestId("cms-search-input");
    api.get.mockClear();
    const input = screen.getByTestId("cms-search-input");
    fireEvent.change(input, { target: { value: "civil" } });
    act(() => jest.advanceTimersByTime(350));
    await waitFor(() => {
      const calls = api.get.mock.calls;
      return calls.some(([url]) => url.includes("search=civil"));
    });
    expect(api.get.mock.calls.some(([url]) => url.includes("search=civil"))).toBe(true);
    jest.useRealTimers();
  });

  test("search input clears when entity changes", async () => {
    mockSearchParamsRaw = {};
    renderCms();
    const input = await screen.findByTestId("cms-search-input");
    fireEvent.change(input, { target: { value: "hello" } });
    expect(input.value).toBe("hello");
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exams" } });
    await waitFor(() => expect(screen.getByTestId("cms-search-input").value).toBe(""));
  });

  test("search request includes exam_id alongside search param", async () => {
    jest.useFakeTimers();
    mockSearchParamsRaw = { exam_id: EXAM_ID };
    renderCms();
    // Switch to a scoped entity
    await screen.findByTestId("cms-entity-select");
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exam-cycles" } });
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    api.get.mockClear();
    const input = screen.getByTestId("cms-search-input");
    fireEvent.change(input, { target: { value: "upsc" } });
    act(() => jest.advanceTimersByTime(350));
    await waitFor(() => {
      return api.get.mock.calls.some(([url]) => url.includes("search=upsc") && url.includes("exam_id="));
    });
    expect(api.get.mock.calls.some(([url]) => url.includes("search=upsc") && url.includes("exam_id="))).toBe(true);
    jest.useRealTimers();
  });
});

// ── Section G.3: Status filter tests ─────────────────────────────────────────

describe("G.3 Status filter", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSetSearchParams.mockClear();
    setupDefaultMocks();
  });

  const REVIEWER_STATUS_ENTITIES = [
    "syllabus-topic-mentions",
    "exam-topic-coverage",
    "policy-updates",
  ];
  const TRUST_STATUS_ENTITIES = [
    "syllabus-documents",
    "pyq-papers",
    "pyq-sources",
  ];

  test.each(REVIEWER_STATUS_ENTITIES)("reviewer_status filter is rendered for %s", async (entity) => {
    mockSearchParamsRaw = {};
    renderCms();
    fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: entity } });
    await waitFor(() => expect(screen.queryByTestId("cms-status-filter")).toBeTruthy());
  });

  test.each(TRUST_STATUS_ENTITIES)("trust_status filter is rendered for %s", async (entity) => {
    mockSearchParamsRaw = {};
    renderCms();
    fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: entity } });
    await waitFor(() => expect(screen.queryByTestId("cms-status-filter")).toBeTruthy());
  });

  test("no status filter for entity without reviewer/trust status (exam-families)", async () => {
    mockSearchParamsRaw = {};
    renderCms();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    // Default entity is exam-families
    expect(screen.queryByTestId("cms-status-filter")).toBeNull();
  });

  test("selecting a reviewer_status value sends correct param to backend", async () => {
    mockSearchParamsRaw = {};
    renderCms();
    fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: "exam-topic-coverage" } });
    const filter = await screen.findByTestId("cms-status-filter");
    api.get.mockClear();
    fireEvent.change(filter, { target: { value: "approved" } });
    await waitFor(() => {
      return api.get.mock.calls.some(([url]) => url.includes("reviewer_status=approved"));
    });
    expect(api.get.mock.calls.some(([url]) => url.includes("reviewer_status=approved"))).toBe(true);
  });

  test("selecting a trust_status value sends correct param for pyq-papers", async () => {
    mockSearchParamsRaw = {};
    renderCms();
    fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: "pyq-papers" } });
    const filter = await screen.findByTestId("cms-status-filter");
    api.get.mockClear();
    fireEvent.change(filter, { target: { value: "trusted" } });
    await waitFor(() => {
      return api.get.mock.calls.some(([url]) => url.includes("trust_status=trusted"));
    });
    expect(api.get.mock.calls.some(([url]) => url.includes("trust_status=trusted"))).toBe(true);
  });

  test("selecting all statuses sends no status filter param", async () => {
    mockSearchParamsRaw = {};
    renderCms();
    fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: "exam-topic-coverage" } });
    const filter = await screen.findByTestId("cms-status-filter");
    fireEvent.change(filter, { target: { value: "approved" } });
    api.get.mockClear();
    fireEvent.change(filter, { target: { value: "" } });
    await waitFor(() => {
      return api.get.mock.calls.some(([url]) => !url.includes("reviewer_status=") && url.includes("exam-topic-coverage"));
    });
    expect(api.get.mock.calls.some(([url]) => !url.includes("reviewer_status=") && url.includes("exam-topic-coverage"))).toBe(true);
  });

  test("filter clears when entity changes", async () => {
    mockSearchParamsRaw = {};
    renderCms();
    fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: "exam-topic-coverage" } });
    const filter = await screen.findByTestId("cms-status-filter");
    fireEvent.change(filter, { target: { value: "approved" } });
    expect(filter.value).toBe("approved");
    // Change to another entity with status filter
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "policy-updates" } });
    await waitFor(() => {
      const f = screen.queryByTestId("cms-status-filter");
      return f && f.value === "";
    });
    expect(screen.getByTestId("cms-status-filter").value).toBe("");
  });
});

// ── Section G.4: Pagination tests ────────────────────────────────────────────

describe("G.4 Pagination", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSetSearchParams.mockClear();
    mockSearchParamsRaw = {};
  });

  function setupPaginatedMock(total) {
    api.get.mockImplementation((url) => {
      if (url.includes("/exams?")) return Promise.resolve(makeListResponse([{ id: EXAM_ID, name: EXAM_NAME }]));
      if (url.includes("/exam-cycles?")) return Promise.resolve(makeListResponse([{ id: CYCLE_ID, cycle_name: CYCLE_NAME }]));
      if (url.includes("/admin/organizations")) return Promise.resolve({ items: [] });
      // Parse offset from URL
      const params = new URLSearchParams(url.split("?")[1] || "");
      const limit = parseInt(params.get("limit") || "50", 10);
      const offset = parseInt(params.get("offset") || "0", 10);
      const fakeItems = Array.from({ length: Math.min(limit, Math.max(0, total - offset)) }, (_, i) => ({
        id: `row-${offset + i}`,
        name: `Row ${offset + i}`,
      }));
      return Promise.resolve(makeListResponse(fakeItems, total));
    });
  }

  test("Previous button is disabled on page 1", async () => {
    setupPaginatedMock(10);
    renderCms();
    await waitFor(() => screen.queryByTestId("cms-pagination-footer"));
    const prev = screen.getByTestId("cms-page-prev-btn");
    expect(prev.disabled).toBe(true);
  });

  test("Next button disabled when total fits in one page", async () => {
    setupPaginatedMock(20);
    renderCms();
    await waitFor(() => screen.queryByTestId("cms-pagination-footer"));
    const next = screen.getByTestId("cms-page-next-btn");
    expect(next.disabled).toBe(true);
  });

  test("Next button enabled when total exceeds page size", async () => {
    setupPaginatedMock(120);
    renderCms();
    await waitFor(() => screen.queryByTestId("cms-pagination-footer"));
    const next = screen.getByTestId("cms-page-next-btn");
    expect(next.disabled).toBe(false);
  });

  test("clicking Next advances page and sends correct offset", async () => {
    setupPaginatedMock(120);
    renderCms();
    await waitFor(() => screen.queryByTestId("cms-pagination-footer"));
    api.get.mockClear();
    fireEvent.click(screen.getByTestId("cms-page-next-btn"));
    await waitFor(() => {
      return api.get.mock.calls.some(([url]) => url.includes("offset=50"));
    });
    expect(api.get.mock.calls.some(([url]) => url.includes("offset=50"))).toBe(true);
  });

  test("clicking Previous goes back to previous page", async () => {
    setupPaginatedMock(120);
    renderCms();
    await waitFor(() => screen.queryByTestId("cms-pagination-footer"));
    fireEvent.click(screen.getByTestId("cms-page-next-btn"));
    await waitFor(() => api.get.mock.calls.some(([url]) => url.includes("offset=50")));
    api.get.mockClear();
    fireEvent.click(screen.getByTestId("cms-page-prev-btn"));
    await waitFor(() => {
      return api.get.mock.calls.some(([url]) => url.includes("offset=0"));
    });
    expect(api.get.mock.calls.some(([url]) => url.includes("offset=0"))).toBe(true);
  });

  test("page indicator shows Page N of M", async () => {
    setupPaginatedMock(120);
    renderCms();
    await waitFor(() => screen.queryByTestId("cms-page-indicator"));
    const indicator = screen.getByTestId("cms-page-indicator");
    expect(indicator.textContent).toMatch(/Page 1 of 3/);
  });

  test("page resets to 1 when entity changes", async () => {
    setupPaginatedMock(120);
    renderCms();
    await waitFor(() => screen.queryByTestId("cms-pagination-footer"));
    fireEvent.click(screen.getByTestId("cms-page-next-btn"));
    await waitFor(() => api.get.mock.calls.some(([url]) => url.includes("offset=50")));
    api.get.mockClear();
    fireEvent.change(screen.getByTestId("cms-entity-select"), { target: { value: "exams" } });
    await waitFor(() => {
      return api.get.mock.calls.some(([url]) => url.includes("offset=0") && url.includes("/exams?"));
    });
    expect(api.get.mock.calls.some(([url]) => url.includes("offset=0") && url.includes("/exams?"))).toBe(true);
  });

  test("pagination includes exam_id and cycle_id scope params", async () => {
    mockSearchParamsRaw = { exam_id: EXAM_ID, cycle_id: CYCLE_ID };
    setupPaginatedMock(120);
    renderCms();
    fireEvent.change(await screen.findByTestId("cms-entity-select"), { target: { value: "exam-phases" } });
    await waitFor(() => screen.queryByTestId("cms-pagination-footer"));
    api.get.mockClear();
    fireEvent.click(screen.getByTestId("cms-page-next-btn"));
    await waitFor(() => {
      return api.get.mock.calls.some(([url]) =>
        url.includes("offset=50") && url.includes("exam_id=") && url.includes("exam_cycle_id=")
      );
    });
    expect(api.get.mock.calls.some(([url]) =>
      url.includes("offset=50") && url.includes("exam_id=") && url.includes("exam_cycle_id=")
    )).toBe(true);
  });

  test("Next button disabled on last page", async () => {
    setupPaginatedMock(100); // exactly 2 pages
    renderCms();
    await waitFor(() => screen.queryByTestId("cms-pagination-footer"));
    fireEvent.click(screen.getByTestId("cms-page-next-btn"));
    await waitFor(() => api.get.mock.calls.some(([url]) => url.includes("offset=50")));
    await waitFor(() => {
      const next = screen.getByTestId("cms-page-next-btn");
      return next.disabled === true;
    });
    expect(screen.getByTestId("cms-page-next-btn").disabled).toBe(true);
  });
});

// ── Section G.5: Invariant / regression ──────────────────────────────────────

describe("G.5 Invariants", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSearchParamsRaw = {};
    api.get.mockResolvedValue(makeListResponse([], 0));
  });

  test("AdminSafetyBanner is always visible", async () => {
    renderCms();
    expect(screen.getByTestId("advanced-repair-safety-banner")).toBeTruthy();
  });

  test("New row and Reload controls still render for non-documents entities", async () => {
    renderCms();
    expect(await screen.findByTestId("cms-toggle-create")).toBeTruthy();
  });

  test("CMS renders for authorized user", async () => {
    renderCms();
    expect(await screen.findByTestId("admin-exam-intel-cms")).toBeTruthy();
  });
});
