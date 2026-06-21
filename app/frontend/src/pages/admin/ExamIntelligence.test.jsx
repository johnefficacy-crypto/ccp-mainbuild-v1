import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Prevent env.js from throwing when REACT_APP_BACKEND_URL is unset in CI.
// useApiCollection (now imported by ExamIntelligence.jsx) pulls this in.
jest.mock("../../shared/config/env", () => ({ ENABLE_DEMO_DATA: false }));

jest.mock("../../lib/api", () => ({
  api: { get: jest.fn() },
}));

import { api } from "../../lib/api";
import AdminExamIntelligence from "./ExamIntelligence";

const EMPTY_RESPONSE = { items: [], total_count: 0, has_next: false };

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
        current_cycle: { name: "2024", year: 2024, phases: [] },
        family_name: null,
      },
    ],
    total_count: 1,
    has_next: false,
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

test("active_state selector defaults to Active", async () => {
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
