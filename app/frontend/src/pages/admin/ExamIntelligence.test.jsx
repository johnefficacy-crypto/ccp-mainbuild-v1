import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Prevent env.js from throwing when REACT_APP_BACKEND_URL is unset in CI.
jest.mock("../../shared/config/env", () => ({ ENABLE_DEMO_DATA: false }));

jest.mock("../../lib/api", () => ({
  api: { get: jest.fn() },
}));

import { api } from "../../lib/api";
import AdminExamIntelligence from "./ExamIntelligence";

const EMPTY_RESPONSE = {
  items: [],
  total_count: 0,
  has_next: false,
  family_options: [],
};

function makeExamsResponse(overrides = {}) {
  return {
    items: [
      {
        id: "e1",
        slug: "ssc-cgl",
        name: "SSC CGL",
        status: "ready",
        blocker_count: 0,
        first_blocker_text: null,
        current_cycle: { id: "cy1", name: "2024", year: 2024, status: "active", phases: [] },
        family_name: "Staff Selection",
        organization_name: "SSC",
        management_mode: "core",
        cadence: "annual",
        is_active: true,
        readiness_summary: {
          setup: "ready", topic_coverage: "ready", pyq: "ready",
          pending_review_count: 0, stale_review_count: 0,
        },
      },
    ],
    total_count: 1,
    has_next: false,
    family_options: [{ id: "fam1", name: "Staff Selection" }],
    ...overrides,
  };
}

function wrap(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

beforeEach(() => {
  jest.clearAllMocks();
  api.get.mockResolvedValue(EMPTY_RESPONSE);
});

// ── API endpoint ───────────────────────────────────────────────────────────

test("fetches from the management endpoint", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("/management/exams");
});

// ── loading state ──────────────────────────────────────────────────────────

test("shows loading state on initial render before fetch resolves", () => {
  let resolve;
  api.get.mockImplementation(() => new Promise((r) => { resolve = r; }));

  wrap(<AdminExamIntelligence />);
  expect(screen.getByTestId("exam-intel-loading")).toBeInTheDocument();

  act(() => { resolve(EMPTY_RESPONSE); });
});

// ── data state ─────────────────────────────────────────────────────────────

test("renders exam rows after successful load", async () => {
  api.get.mockResolvedValue(makeExamsResponse());

  wrap(<AdminExamIntelligence />);

  await waitFor(() =>
    expect(screen.getByTestId("exam-mgmt-row-ssc-cgl")).toBeInTheDocument(),
  );
  expect(screen.getByText("SSC CGL")).toBeInTheDocument();
});

// ── empty state ────────────────────────────────────────────────────────────

test("renders empty message when no exams returned", async () => {
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  wrap(<AdminExamIntelligence />);

  await waitFor(() =>
    expect(screen.getByTestId("exam-mgmt-table")).toBeInTheDocument(),
  );
  expect(screen.getByText(/no exams match your filters/i)).toBeInTheDocument();
});

// ── error state ────────────────────────────────────────────────────────────

test("renders error banner when fetch fails", async () => {
  api.get.mockRejectedValue(new Error("network error"));

  wrap(<AdminExamIntelligence />);

  await waitFor(() =>
    expect(screen.getByTestId("exam-intel-error")).toBeInTheDocument(),
  );
});

// ── row fields ─────────────────────────────────────────────────────────────

test("exam row shows organisation name", async () => {
  api.get.mockResolvedValue(makeExamsResponse());
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  expect(screen.getByTestId("exam-mgmt-org-ssc-cgl").textContent).toBe("SSC");
});

test("exam row shows management mode label", async () => {
  api.get.mockResolvedValue(makeExamsResponse());
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  expect(screen.getByTestId("exam-mgmt-mode-ssc-cgl").textContent).toBe("Core");
});

test("exam row shows cadence label", async () => {
  api.get.mockResolvedValue(makeExamsResponse());
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  expect(screen.getByTestId("exam-mgmt-cadence-ssc-cgl").textContent).toBe("Annual");
});

test("exam row shows active state", async () => {
  api.get.mockResolvedValue(makeExamsResponse());
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  expect(screen.getByTestId("exam-mgmt-active-ssc-cgl").textContent).toBe("Active");
});

test("inactive exam shows Inactive state", async () => {
  api.get.mockResolvedValue(makeExamsResponse({
    items: [{ ...makeExamsResponse().items[0], is_active: false }],
  }));
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  expect(screen.getByTestId("exam-mgmt-active-ssc-cgl").textContent).toBe("Inactive");
});

test("exam row shows current cycle status", async () => {
  api.get.mockResolvedValue(makeExamsResponse());
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  const cycleCell = screen.getByTestId("exam-mgmt-cycle-ssc-cgl");
  expect(cycleCell.textContent).toContain("active");
});

test("exam row shows phase label and dates when present", async () => {
  const itemWithPhase = {
    ...makeExamsResponse().items[0],
    current_cycle: {
      id: "cy1", name: "2024", year: 2024, status: "active",
      phases: [{
        id: "ph1", slug: "prelims", label: "Prelims", phase_order: 1,
        start_date: "2024-06-01", end_date: "2024-06-30", status: "upcoming",
      }],
    },
  };
  api.get.mockResolvedValue(makeExamsResponse({ items: [itemWithPhase] }));
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  const phaseEl = screen.getByTestId("exam-mgmt-phase-ph1");
  expect(phaseEl.textContent).toContain("Prelims");
  expect(phaseEl.textContent).toContain("upcoming");
  expect(phaseEl.textContent).toContain("2024-06-01");
});

test("exam row shows blocker count badge when blockers > 0", async () => {
  api.get.mockResolvedValue(makeExamsResponse({
    items: [{ ...makeExamsResponse().items[0], blocker_count: 3 }],
  }));
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  expect(screen.getByTestId("exam-mgmt-blockers-ssc-cgl").textContent).toContain("3");
});

test("exam row shows readiness summary when present", async () => {
  api.get.mockResolvedValue(makeExamsResponse());
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  const r = screen.getByTestId("exam-mgmt-readiness-ssc-cgl");
  expect(r.textContent).toContain("S");
  expect(r.textContent).toContain("T");
  expect(r.textContent).toContain("P");
});

test("exam row shows fallback dash when readiness_summary is null", async () => {
  api.get.mockResolvedValue(makeExamsResponse({
    items: [{ ...makeExamsResponse().items[0], readiness_summary: null }],
  }));
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  expect(screen.getByTestId("exam-mgmt-readiness-ssc-cgl").textContent).toBe("—");
});

test("exam row shows org dash when organization_name is null", async () => {
  api.get.mockResolvedValue(makeExamsResponse({
    items: [{ ...makeExamsResponse().items[0], organization_name: null }],
  }));
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  expect(screen.getByTestId("exam-mgmt-org-ssc-cgl").textContent).toBe("—");
});

test("exam row shows cycle dash when no current_cycle", async () => {
  api.get.mockResolvedValue(makeExamsResponse({
    items: [{ ...makeExamsResponse().items[0], current_cycle: null }],
  }));
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  expect(screen.getByTestId("exam-mgmt-cycle-ssc-cgl").textContent).toBe("—");
});

test("Manage exam is the one and only primary row action", async () => {
  api.get.mockResolvedValue(makeExamsResponse());
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-ssc-cgl");
  const manageLink = screen.getByTestId("exam-mgmt-manage-ssc-cgl");
  expect(manageLink).toBeInTheDocument();
  expect(manageLink.getAttribute("href")).toBe("/admin/exam-intelligence/exams/e1");
});

// ── status chips ────────────────────────────────────────────────────────────

test("management rows render correct status chip label", async () => {
  api.get.mockResolvedValue({
    items: [
      { id: "e1", slug: "exam-a", name: "Exam A", status: "ready", blocker_count: 0,
        first_blocker_text: null, current_cycle: null, family_name: null,
        organization_name: null, management_mode: null, cadence: null, is_active: true,
        readiness_summary: null },
      { id: "e2", slug: "exam-b", name: "Exam B", status: "needs_action", blocker_count: 1,
        first_blocker_text: "Missing PYQ", current_cycle: null, family_name: null,
        organization_name: null, management_mode: null, cadence: null, is_active: true,
        readiness_summary: null },
      { id: "e3", slug: "exam-c", name: "Exam C", status: "blocked", blocker_count: 2,
        first_blocker_text: "No cycle", current_cycle: null, family_name: null,
        organization_name: null, management_mode: null, cadence: null, is_active: true,
        readiness_summary: null },
    ],
    total_count: 3,
    has_next: false,
    family_options: [],
  });

  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-row-exam-a");

  // Use getAllByText because the workflow filter dropdown also contains these labels.
  expect(screen.getAllByText("Ready").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("Needs action").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("Blocked").length).toBeGreaterThanOrEqual(1);
});

// ── overflow menu / Create exam ─────────────────────────────────────────────

test("Create exam is not a standalone visible button", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.queryByTestId("exam-mgmt-create-exam")).toBeNull();
});

test("More trigger exposes Create exam in overflow menu", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());

  const trigger = screen.getByTestId("exam-mgmt-more-trigger");
  expect(trigger.getAttribute("aria-expanded")).toBe("false");

  fireEvent.click(trigger);
  expect(trigger.getAttribute("aria-expanded")).toBe("true");

  const createExam = screen.getByTestId("exam-mgmt-create-exam");
  expect(createExam.getAttribute("href")).toBe("/admin/exam-intelligence/new");
  expect(createExam.classList.contains("btn-primary")).toBe(false);
});

test("More menu closes when Create exam is clicked", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());

  fireEvent.click(screen.getByTestId("exam-mgmt-more-trigger"));
  expect(screen.getByTestId("exam-mgmt-create-exam")).toBeInTheDocument();

  fireEvent.click(screen.getByTestId("exam-mgmt-create-exam"));
  expect(screen.queryByTestId("exam-mgmt-create-exam")).toBeNull();
});

// ── pagination ─────────────────────────────────────────────────────────────

test("count label uses total_count from response, not items.length", async () => {
  api.get.mockResolvedValue({ ...makeExamsResponse(), total_count: 132, has_next: true });
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-intel-count-label");
  expect(screen.getByTestId("exam-intel-count-label").textContent).toContain("132");
});

test("Previous and Next buttons are rendered", async () => {
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-table");
  expect(screen.getByTestId("exam-intel-prev")).toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-next")).toBeInTheDocument();
});

test("Previous is disabled on the first page", async () => {
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-table");
  expect(screen.getByTestId("exam-intel-prev")).toBeDisabled();
});

test("Next is disabled when has_next is false", async () => {
  api.get.mockResolvedValue({ ...EMPTY_RESPONSE, has_next: false });
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-table");
  expect(screen.getByTestId("exam-intel-next")).toBeDisabled();
});

test("Next is enabled when has_next is true", async () => {
  api.get.mockResolvedValue({ ...makeExamsResponse(), total_count: 50, has_next: true });
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-table");
  expect(screen.getByTestId("exam-intel-next")).not.toBeDisabled();
});

test("clicking Next sends request with incremented offset", async () => {
  api.get.mockResolvedValue({ ...makeExamsResponse(), total_count: 50, has_next: true });
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-table");

  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  fireEvent.click(screen.getByTestId("exam-intel-next"));

  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("offset=25");
});

test("default load sends limit=25", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("limit=25");
});

// ── filter wire: search ────────────────────────────────────────────────────

test("search input triggers fetch with q param", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  fireEvent.change(screen.getByTestId("exam-intel-search"), { target: { value: "upsc" } });

  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("q=upsc");
});

// ── filter wire: active_state ──────────────────────────────────────────────

test("default load sends active_state=active", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("active_state=active");
});

test("active_state selector defaults to Active", () => {
  wrap(<AdminExamIntelligence />);
  expect(screen.getByTestId("exam-intel-active-filter").value).toBe("active");
});

test("changing active_state triggers fetch with updated param", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  fireEvent.change(screen.getByTestId("exam-intel-active-filter"), {
    target: { value: "inactive" },
  });

  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("active_state=inactive");
});

// ── filter wire: management_mode ───────────────────────────────────────────

test("lane filter sends management_mode param", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  fireEvent.change(screen.getByTestId("exam-intel-lane-filter"), {
    target: { value: "core" },
  });

  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("management_mode=core");
});

test("empty lane filter sends no management_mode param on initial load", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).not.toContain("management_mode");
});

// ── filter wire: cadence ───────────────────────────────────────────────────

test("cadence filter sends cadence param", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  fireEvent.change(screen.getByTestId("exam-intel-cadence-filter"), {
    target: { value: "annual" },
  });

  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("cadence=annual");
});

// ── filter wire: family ────────────────────────────────────────────────────

test("family filter sends exam_family_id param", async () => {
  api.get.mockResolvedValue({
    ...EMPTY_RESPONSE,
    family_options: [{ id: "fam-1", name: "Civil Services" }],
  });
  wrap(<AdminExamIntelligence />);
  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  fireEvent.change(screen.getByTestId("exam-intel-family-filter"), {
    target: { value: "fam-1" },
  });

  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("exam_family_id=fam-1");
});

test("family filter is populated from response family_options", async () => {
  api.get.mockResolvedValue({
    ...EMPTY_RESPONSE,
    family_options: [
      { id: "fam-1", name: "Civil Services" },
      { id: "fam-2", name: "Banking" },
    ],
  });
  wrap(<AdminExamIntelligence />);
  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

  expect(screen.getByText("Civil Services")).toBeInTheDocument();
  expect(screen.getByText("Banking")).toBeInTheDocument();
});

// ── filter wire: workflow ──────────────────────────────────────────────────

test("workflow filter sends workflow param", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  fireEvent.change(screen.getByTestId("exam-intel-workflow-filter"), {
    target: { value: "blocked" },
  });

  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("workflow=blocked");
});

test("initial load sends no workflow param", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).not.toContain("workflow=");
});

// ── filter wire: sort ──────────────────────────────────────────────────────

test("default load sends sort=blockers_first", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("sort=blockers_first");
});

test("sort selector defaults to Blockers first", () => {
  wrap(<AdminExamIntelligence />);
  expect(screen.getByTestId("exam-intel-sort").value).toBe("blockers_first");
});

test("sort filter sends sort param", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);

  fireEvent.change(screen.getByTestId("exam-intel-sort"), {
    target: { value: "name" },
  });

  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("sort=name");
});

// ── filter change resets offset ─────────────────────────────────────────────

test("changing a filter resets offset to 0", async () => {
  api.get.mockResolvedValue({ ...makeExamsResponse(), total_count: 50, has_next: true });
  wrap(<AdminExamIntelligence />);
  await screen.findByTestId("exam-mgmt-table");

  // Advance to page 2
  api.get.mockClear();
  api.get.mockResolvedValue({ ...makeExamsResponse(), total_count: 50, has_next: false });
  fireEvent.click(screen.getByTestId("exam-intel-next"));
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("offset=25");

  // Now change a filter — offset must reset to 0
  api.get.mockClear();
  api.get.mockResolvedValue(EMPTY_RESPONSE);
  fireEvent.change(screen.getByTestId("exam-intel-active-filter"), {
    target: { value: "all" },
  });

  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(api.get.mock.calls[0][0]).toContain("offset=0");
});

// ── stale response protection ──────────────────────────────────────────────

test("stale response does not overwrite a newer request result", async () => {
  let resolveStale;
  const stalePromise = new Promise((r) => { resolveStale = r; });
  api.get.mockReturnValueOnce(stalePromise);

  wrap(<AdminExamIntelligence />);

  // Trigger a second fetch before the first resolves
  api.get.mockResolvedValueOnce(EMPTY_RESPONSE);
  fireEvent.change(screen.getByTestId("exam-intel-active-filter"), {
    target: { value: "all" },
  });

  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

  // Resolve the stale first fetch with data — it must be ignored
  act(() => {
    resolveStale(makeExamsResponse({ total_count: 99 }));
  });

  await waitFor(() =>
    expect(screen.getByTestId("exam-intel-count-label").textContent).not.toContain("99"),
  );
});

// ── safety banner ──────────────────────────────────────────────────────────

test("lifecycle banner starts collapsed and expands on click", () => {
  wrap(<AdminExamIntelligence />);

  expect(screen.getByTestId("admin-exam-intel-safety")).toBeInTheDocument();
  expect(screen.getByTestId("admin-exam-intel-safety-content")).not.toBeVisible();
  expect(screen.getByTestId("admin-exam-intel-safety-toggle")).toHaveAttribute(
    "aria-expanded",
    "false",
  );

  fireEvent.click(screen.getByTestId("admin-exam-intel-safety-toggle"));

  expect(screen.getByTestId("admin-exam-intel-safety-content")).toBeVisible();
  expect(screen.getByTestId("admin-exam-intel-safety-toggle")).toHaveAttribute(
    "aria-expanded",
    "true",
  );

  fireEvent.click(screen.getByTestId("admin-exam-intel-safety-toggle"));
  expect(screen.getByTestId("admin-exam-intel-safety-content")).not.toBeVisible();
});

test("banner content includes lifecycle-gated terms", () => {
  wrap(<AdminExamIntelligence />);
  fireEvent.click(screen.getByTestId("admin-exam-intel-safety-toggle"));
  const content = screen.getByTestId("admin-exam-intel-safety-content");
  expect(content.textContent).toMatch(/reviewed/);
  expect(content.textContent).toMatch(/locked/);
  expect(content.textContent).toMatch(/verified/);
});

// ── no tabs ────────────────────────────────────────────────────────────────

test("no tab controls are rendered (single-view front door)", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.queryByTestId("exam-intel-tab-overview")).toBeNull();
  expect(screen.queryByTestId("exam-intel-tab-exams")).toBeNull();
});

// ── __null__ sentinel wire ─────────────────────────────────────────────────

test("selecting Unclassified in lane filter sends management_mode=__null__", async () => {
  wrap(<AdminExamIntelligence />);
  await waitFor(() => screen.getByTestId("exam-mgmt-table"));

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
