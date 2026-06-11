import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Mock api module before importing the component.
jest.mock("../../lib/api", () => ({
  api: {
    get: jest.fn(),
  },
}));

import { api } from "../../lib/api";
import AdminExamIntelligence from "./ExamIntelligence";

function wrap(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

function makeExamsResponse(overrides = {}) {
  return {
    items: [
      { id: "e1", slug: "ssc-cgl", name: "SSC CGL", exam_type: "recruitment",
        is_active: true, syllabus_verified: 1, syllabus_pending: 0,
        verified_topic_count: 1, coverage_total: 1, high_yield_topic_count: 1,
        readiness_level: "ready", pyq_coverage_status: "covered" },
    ],
    count: 1,
    total_count: 3,
    limit: 25,
    offset: 0,
    has_next: true,
    ...overrides,
  };
}

function makeOverviewResponse() {
  return {
    tables: {},
    exams: { total: 3, active: 2 },
    topic_coverage: { total: 0, high_yield: 0 },
    low_confidence_mappings: 0,
    stale_review_items: 0,
    user_facing_readiness: { level: "not_ready", locked_topic_coverage: 0, verified_syllabus_mentions: 0 },
  };
}

async function switchToExamsTab() {
  fireEvent.click(screen.getByTestId("exam-intel-tab-exams"));
}

beforeEach(() => {
  jest.clearAllMocks();
  api.get.mockResolvedValue(makeOverviewResponse());
});

// ── loading state ──────────────────────────────────────────────────────────

test("shows loading state while exams are being fetched", async () => {
  let resolve;
  api.get.mockImplementation((url) => {
    if (url.includes("/exams")) {
      return new Promise((res) => { resolve = res; });
    }
    return Promise.resolve(makeOverviewResponse());
  });

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  expect(screen.getByTestId("exam-intel-loading")).toBeInTheDocument();

  await act(async () => { resolve(makeExamsResponse()); });
});

// ── data state renders table ───────────────────────────────────────────────

test("renders exam table after successful load", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });

  await waitFor(() => expect(screen.getByTestId("exam-intel-exam-table")).toBeInTheDocument());
  expect(screen.getByText("SSC CGL")).toBeInTheDocument();
});

// ── empty state ────────────────────────────────────────────────────────────

test("renders empty state when no exams returned", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse({ items: [], count: 0, total_count: 0, has_next: false }))
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });

  await waitFor(() => expect(screen.getByText(/no exams registered yet/i)).toBeInTheDocument());
});

// ── error state ────────────────────────────────────────────────────────────

test("renders error state when fetch fails", async () => {
  api.get.mockImplementation((url) => {
    if (url.includes("/exams")) return Promise.reject(new Error("network error"));
    return Promise.resolve(makeOverviewResponse());
  });

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });

  await waitFor(() => expect(screen.getByTestId("exam-intel-error")).toBeInTheDocument());
  expect(screen.getByTestId("exam-intel-error")).toHaveTextContent("network error");
});

// ── filter resets page ─────────────────────────────────────────────────────

test("changing search input resets to page 0 and re-calls with q param", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  // Navigate to page 1 first.
  await act(async () => {
    fireEvent.click(screen.getByTestId("exam-intel-next"));
  });
  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    const lastUrl = calls[calls.length - 1][0];
    expect(lastUrl).toContain("offset=25");
  });

  // Now change the search — page should reset.
  await act(async () => {
    fireEvent.change(screen.getByTestId("exam-intel-search"), { target: { value: "ssc" } });
  });
  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    const lastUrl = calls[calls.length - 1][0];
    expect(lastUrl).toContain("q=ssc");
    expect(lastUrl).toContain("offset=0");
  });
});

test("changing exam_type filter resets to page 0", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  await act(async () => {
    fireEvent.change(screen.getByTestId("exam-intel-type-filter"), {
      target: { value: "entrance" },
    });
  });
  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    const lastUrl = calls[calls.length - 1][0];
    expect(lastUrl).toContain("exam_type=entrance");
    expect(lastUrl).toContain("offset=0");
  });
});

test("changing is_active filter resets to page 0", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  await act(async () => {
    fireEvent.change(screen.getByTestId("exam-intel-active-filter"), {
      target: { value: "true" },
    });
  });
  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    const lastUrl = calls[calls.length - 1][0];
    expect(lastUrl).toContain("is_active=true");
    expect(lastUrl).toContain("offset=0");
  });
});

// ── stale-response guard ───────────────────────────────────────────────────

test("stale response from earlier request does not overwrite newer state", async () => {
  let resolveFirst;
  let callCount = 0;

  api.get.mockImplementation((url) => {
    if (!url.includes("/exams")) return Promise.resolve(makeOverviewResponse());
    callCount++;
    if (callCount === 1) {
      // First call: held promise (will resolve late — simulating slow response).
      return new Promise((res) => { resolveFirst = res; });
    }
    // Second call: resolves immediately with search results.
    return Promise.resolve(makeExamsResponse({ items: [{ ...makeExamsResponse().items[0], name: "IBPS PO" }] }));
  });

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });

  // The first load is in flight. Change search — triggers second load.
  await act(async () => {
    fireEvent.change(screen.getByTestId("exam-intel-search"), { target: { value: "ibps" } });
  });

  // Now let the first (stale) response land — it should be discarded.
  await act(async () => { resolveFirst(makeExamsResponse()); });

  // The table should reflect the second (fresh) response, not the first stale one.
  await waitFor(() => expect(screen.getByTestId("exam-intel-exam-table")).toBeInTheDocument());
  expect(screen.getByText("IBPS PO")).toBeInTheDocument();
  expect(screen.queryByText("SSC CGL")).not.toBeInTheDocument();
});

// ── single dispatch on filter change ──────────────────────────────────────

test("changing a filter triggers exactly one load (no double-fetch from separate effects)", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  const callsBefore = api.get.mock.calls.filter(([url]) => url.includes("/exams")).length;

  await act(async () => {
    fireEvent.change(screen.getByTestId("exam-intel-search"), { target: { value: "ssc" } });
  });
  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    const lastUrl = calls[calls.length - 1][0];
    expect(lastUrl).toContain("q=ssc");
  });

  const callsAfter = api.get.mock.calls.filter(([url]) => url.includes("/exams")).length;
  // Must be exactly one additional call — not two (which would happen with two separate effects).
  expect(callsAfter - callsBefore).toBe(1);
});

// ── header count label never inverted ─────────────────────────────────────

test("header count label does not render inverted span when non-first page returns zero rows", async () => {
  // First call returns page 0 with 1 item and total_count=30 (so offset branch fires).
  // Second call (after a data change) returns page 1 with 0 items — offset=25, count=0.
  let callCount = 0;
  api.get.mockImplementation((url) => {
    if (!url.includes("/exams")) return Promise.resolve(makeOverviewResponse());
    callCount++;
    if (callCount === 1) {
      return Promise.resolve(makeExamsResponse({ total_count: 30, has_next: true }));
    }
    // Page 1 returns zero rows.
    return Promise.resolve({
      items: [], count: 0, total_count: 30, limit: 25, offset: 25, has_next: false,
    });
  });

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  // Navigate to page 1 — backend returns 0 rows for that page.
  await act(async () => {
    fireEvent.click(screen.getByTestId("exam-intel-next"));
  });

  await waitFor(() => {
    const label = screen.getByTestId("exam-intel-count-label");
    const text = label.textContent;
    // The label must not contain an inverted "end < start" range like "26–25".
    const match = text.match(/showing (\d+)–(\d+)/);
    if (match) {
      expect(Number(match[2])).toBeGreaterThanOrEqual(Number(match[1]));
    }
    // When count=0, the "showing X–Y" part must be absent entirely.
    expect(text).not.toMatch(/showing \d+–\d+/);
  });
});

// ── PR-B1: portfolio lane filters ──────────────────────────────────────────

test("selecting 'All (non-archive)' (empty value) sends no management_mode param", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  // The default option value is "" — verify no management_mode in URL.
  const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
  const lastUrl = calls[calls.length - 1][0];
  expect(lastUrl).not.toContain("management_mode");
});

test("selecting a specific lane sends management_mode param and resets to page 0", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  // Navigate to page 1.
  await act(async () => {
    fireEvent.click(screen.getByTestId("exam-intel-next"));
  });

  // Change lane filter.
  await act(async () => {
    fireEvent.change(screen.getByTestId("exam-intel-lane-filter"), {
      target: { value: "core" },
    });
  });

  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    const lastUrl = calls[calls.length - 1][0];
    expect(lastUrl).toContain("management_mode=core");
    expect(lastUrl).toContain("offset=0");
  });
});

test("selecting archive lane sends management_mode=archive", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  await act(async () => {
    fireEvent.change(screen.getByTestId("exam-intel-lane-filter"), {
      target: { value: "archive" },
    });
  });

  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    const lastUrl = calls[calls.length - 1][0];
    expect(lastUrl).toContain("management_mode=archive");
  });
});

test("selecting a cadence filter sends cadence param and resets to page 0", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  await act(async () => {
    fireEvent.change(screen.getByTestId("exam-intel-cadence-filter"), {
      target: { value: "annual" },
    });
  });

  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    const lastUrl = calls[calls.length - 1][0];
    expect(lastUrl).toContain("cadence=annual");
    expect(lastUrl).toContain("offset=0");
  });
});

test("lane filter change fires exactly one load (single dispatch)", async () => {
  api.get.mockImplementation((url) =>
    url.includes("/exams")
      ? Promise.resolve(makeExamsResponse())
      : Promise.resolve(makeOverviewResponse())
  );

  wrap(<AdminExamIntelligence />);
  await act(async () => { await switchToExamsTab(); });
  await waitFor(() => screen.getByTestId("exam-intel-exam-table"));

  const before = api.get.mock.calls.filter(([url]) => url.includes("/exams")).length;

  await act(async () => {
    fireEvent.change(screen.getByTestId("exam-intel-lane-filter"), {
      target: { value: "light" },
    });
  });
  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    expect(calls[calls.length - 1][0]).toContain("management_mode=light");
  });

  const after = api.get.mock.calls.filter(([url]) => url.includes("/exams")).length;
  expect(after - before).toBe(1);
});
