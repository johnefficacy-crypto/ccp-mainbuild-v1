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
      target: { value: "civil_services" },
    });
  });
  await waitFor(() => {
    const calls = api.get.mock.calls.filter(([url]) => url.includes("/exams"));
    const lastUrl = calls[calls.length - 1][0];
    expect(lastUrl).toContain("exam_type=civil_services");
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
