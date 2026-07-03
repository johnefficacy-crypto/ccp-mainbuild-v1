/**
 * PyqMockProjectionPanel — EI-CLEAN-04 operator remediation UX.
 *
 *  1.  Preview humanizes internal reason codes (no raw `code:detail` leakage).
 *  2.  Ineligible rows aggregate into humanized blocker groups at the top.
 *  3.  Sync is disabled (with a note) when eligible_count === 0, even with a
 *      valid audit reason; Preview stays enabled.
 *  4.  Rows show the readable question label, not a truncated UUID.
 *  5.  The projection contract is explained in a keyboard-operable disclosure.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
}));

jest.mock("../../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({ run: jest.fn(), busy: false }),
}));

const { api } = require("../../../../../lib/api");
const PyqMockProjectionPanel = require("../PyqMockProjectionPanel").default;

const STATUS = {
  total_questions: 100,
  unprojected_count: 100,
  projection_counts: {},
  stale_projections: [],
};

const PREVIEW_ZERO_ELIGIBLE = {
  eligible_count: 0,
  ineligible_count: 100,
  would_create_count: 0,
  would_update_count: 0,
  questions: [
    ...Array.from({ length: 98 }, (_, i) => ({
      question_id: `q-${i}`,
      label: `Sample question number ${i}`,
      eligible: false,
      reason: "not_exactly_one_verified_primary_tag:0",
    })),
    ...Array.from({ length: 2 }, (_, i) => ({
      question_id: `r-${i}`,
      label: `Rejected question ${i}`,
      eligible: false,
      reason: "question_not_verified:rejected",
    })),
  ],
};

function mockGets(preview) {
  api.get.mockImplementation((url) => {
    if (url.endsWith("/status")) return Promise.resolve(STATUS);
    if (url.endsWith("/preview")) return Promise.resolve(preview);
    return Promise.resolve({});
  });
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
});

test("renders the projection-contract info disclosure", async () => {
  mockGets(PREVIEW_ZERO_ELIGIBLE);
  render(<PyqMockProjectionPanel paperId="paper-1" />);
  const disclosure = await screen.findByTestId("projection-info-disclosure");
  expect(disclosure.querySelector("summary")).toBeTruthy();
  expect(disclosure.textContent).toMatch(/exactly one verified primary topic tag/i);
});

test("humanizes reason codes and aggregates blockers after preview", async () => {
  mockGets(PREVIEW_ZERO_ELIGIBLE);
  render(<PyqMockProjectionPanel paperId="paper-1" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));

  await screen.findByTestId("projection-preview-results");
  // No raw code leaks
  expect(screen.queryByText(/not_exactly_one_verified_primary_tag:0/)).toBeNull();
  // Aggregated humanized blocker groups
  const summary = screen.getByTestId("projection-blocker-summary");
  expect(summary.textContent).toMatch(/98\s*Missing verified primary topic tag/);
  // Group label aggregates by code (detail dropped at group level).
  expect(summary.textContent).toMatch(/2\s*Question not verified/);
  expect(summary.textContent).toMatch(/0\s*eligible for projection/);
});

test("rows show the readable label, not a truncated UUID", async () => {
  mockGets(PREVIEW_ZERO_ELIGIBLE);
  render(<PyqMockProjectionPanel paperId="paper-1" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));

  const row = await screen.findByTestId("preview-row-q-0");
  expect(row.textContent).toContain("Sample question number 0");
  expect(row.textContent).not.toMatch(/q-0…/);
});

test("disables Sync when zero eligible, even with a valid audit reason; Preview stays enabled", async () => {
  mockGets(PREVIEW_ZERO_ELIGIBLE);
  render(<PyqMockProjectionPanel paperId="paper-1" />);
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), {
    target: { value: "syncing the corpus now" },
  });
  fireEvent.click(screen.getByTestId("projection-preview-btn"));

  await screen.findByTestId("projection-preview-results");
  expect(screen.getByTestId("projection-sync-btn")).toBeDisabled();
  expect(screen.getByTestId("projection-zero-eligible-note")).toBeTruthy();
  expect(screen.getByTestId("projection-preview-btn")).not.toBeDisabled();
});

test("falls back to a short id when a row has no label", async () => {
  mockGets({
    eligible_count: 1,
    ineligible_count: 0,
    would_create_count: 1,
    would_update_count: 0,
    questions: [{ question_id: "abcdef1234567890", label: "", eligible: true, would_update: false, reason: "eligible" }],
  });
  render(<PyqMockProjectionPanel paperId="paper-1" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));

  const row = await screen.findByTestId("preview-row-abcdef1234567890");
  expect(row.textContent).toContain("abcdef12…");
});
