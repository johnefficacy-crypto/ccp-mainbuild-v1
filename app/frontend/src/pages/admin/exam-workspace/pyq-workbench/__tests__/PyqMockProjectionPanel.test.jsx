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
  // Executes the action and forwards its result to onSuccess (mirrors the real
  // hook's happy path) so sync-result rendering can be exercised.
  default: () => ({
    run: async ({ action, onSuccess }) => {
      const data = await action();
      if (onSuccess) onSuccess(data);
      return { ok: true, data };
    },
    busy: false,
  }),
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

test("distinguishes missing vs duplicate primary tags (opposite remediations)", async () => {
  mockGets({
    eligible_count: 0,
    ineligible_count: 3,
    would_create_count: 0,
    would_update_count: 0,
    questions: [
      { question_id: "m-1", label: "Missing tag q", eligible: false, reason: "not_exactly_one_verified_primary_tag:0" },
      { question_id: "d-1", label: "Dup tag q1", eligible: false, reason: "not_exactly_one_verified_primary_tag:2" },
      { question_id: "d-2", label: "Dup tag q2", eligible: false, reason: "not_exactly_one_verified_primary_tag:3" },
    ],
  });
  render(<PyqMockProjectionPanel paperId="paper-1" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));

  const summary = await screen.findByTestId("projection-blocker-summary");
  // Missing (:0) and duplicate (:>1) aggregate separately with opposite copy.
  expect(summary.textContent).toMatch(/1\s*Missing verified primary topic tag/);
  expect(summary.textContent).toMatch(/2\s*Multiple verified primary tags/);
  // The duplicate case must NOT be mislabeled as "Missing".
  const dupRow = screen.getByTestId("preview-row-d-1");
  expect(dupRow.textContent).toMatch(/Multiple verified primary tags/);
  expect(dupRow.textContent).not.toMatch(/Missing verified primary topic tag/);
});

test("never renders a raw UUID for correct_option_id_mismatch", async () => {
  const uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
  mockGets({
    eligible_count: 0,
    ineligible_count: 1,
    would_create_count: 0,
    would_update_count: 0,
    questions: [
      { question_id: "cim-1", label: "Mismatch q", eligible: false, reason: `correct_option_id_mismatch:${uuid}` },
    ],
  });
  render(<PyqMockProjectionPanel paperId="paper-1" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));

  const results = await screen.findByTestId("projection-preview-results");
  expect(results.textContent).not.toContain(uuid);
  expect(screen.getByTestId("preview-row-cim-1").textContent).toMatch(/Correct-answer option mismatch/);
});

test("sync-result rows show the question label, not a UUID", async () => {
  // No preview loaded → sync is enabled; the mocked useApiAction runs the POST.
  mockGets(PREVIEW_ZERO_ELIGIBLE);
  api.post.mockResolvedValue({
    attempted: 1,
    outcomes: { created: 1 },
    questions: [{ question_id: "abcdef1234567890", label: "Synced question text", outcome: "created" }],
  });
  render(<PyqMockProjectionPanel paperId="paper-1" />);
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), {
    target: { value: "syncing now please" },
  });
  fireEvent.click(screen.getByTestId("projection-sync-btn"));

  const row = await screen.findByTestId("sync-row-abcdef1234567890");
  expect(row.textContent).toContain("Synced question text");
  expect(row.textContent).not.toMatch(/abcdef12…/);
});
