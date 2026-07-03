import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
jest.mock("../../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({
    run: async ({ action, onSuccess }) => {
      try { const data = await action(); onSuccess?.(data); return { ok: true, data }; }
      catch (error) { return { ok: false, error }; }
    },
  }),
}));

const { api } = require("../../../../../lib/api");
const Panel = require("../PyqMockProjectionPanel").default;
const status = (n = 100) => ({ total_questions: n, unprojected_count: n, projection_counts: {}, stale_projections: [] });
const preview = (questions) => ({ eligible_count: 0, ineligible_count: questions.length, would_create_count: 0, would_update_count: 0, questions });
const row = (id, reason, label = id) => ({ question_id: id, label, eligible: false, reason });
const defer = () => { let resolve; const promise = new Promise((r) => { resolve = r; }); return { promise, resolve }; };

function mock(previewData) {
  api.get.mockImplementation((url) => url.endsWith("/status") ? Promise.resolve(status()) : Promise.resolve(previewData));
}

beforeEach(() => { api.get.mockReset(); api.post.mockReset(); });

test("renders truthful remediation and disables a zero-eligible sync", async () => {
  mock(preview([
    row("m", "not_exactly_one_verified_primary_tag:0", "Missing tag"),
    row("r", "question_not_verified:rejected", "Rejected"),
  ]));
  render(<Panel paperId="paper-1" />);
  const disclosure = await screen.findByTestId("projection-info-disclosure");
  expect(disclosure.textContent).toMatch(/MCQ type/i);
  expect(disclosure.textContent).toMatch(/at least two verified options/i);
  expect(disclosure.textContent).toMatch(/exactly one verified correct option/i);
  expect(disclosure.textContent).toMatch(/exactly one verified primary topic tag/i);
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), { target: { value: "valid audit reason" } });
  fireEvent.click(screen.getByTestId("projection-preview-btn"));
  const summary = await screen.findByTestId("projection-blocker-summary");
  expect(summary.textContent).toMatch(/1\s*Missing verified primary topic tag/);
  expect(summary.textContent).toMatch(/1\s*Question not verified/);
  expect(screen.getByTestId("projection-sync-btn")).toBeDisabled();
  expect(screen.getByTestId("preview-row-m").textContent).toContain("Missing tag");
});

test("keeps missing, duplicate, zero-correct, and multi-correct blockers separate", async () => {
  mock(preview([
    row("tm", "not_exactly_one_verified_primary_tag:0"),
    row("td", "not_exactly_one_verified_primary_tag:2"),
    row("cn", "not_exactly_one_correct:0"),
    row("cm", "not_exactly_one_correct:2"),
  ]));
  render(<Panel paperId="paper-1" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));
  const text = (await screen.findByTestId("projection-blocker-summary")).textContent;
  expect(text).toMatch(/1\s*Missing verified primary topic tag/);
  expect(text).toMatch(/1\s*Multiple verified primary tags/);
  expect(text).toMatch(/1\s*No verified correct option/);
  expect(text).toMatch(/1\s*Multiple verified correct options/);
  expect(screen.getByTestId("preview-row-cm").textContent).toMatch(/has 2/);
});

test("suppresses UUID details and renders readable sync labels", async () => {
  const uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
  mock(preview([row("bad", `correct_option_id_mismatch:${uuid}`, "Mismatch question")]));
  api.post.mockResolvedValue({ attempted: 1, outcomes: { created: 1 }, questions: [{ question_id: "s", label: "Synced question", outcome: "created" }] });
  render(<Panel paperId="paper-1" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));
  expect((await screen.findByTestId("projection-preview-results")).textContent).not.toContain(uuid);
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), { target: { value: "sync this question" } });
  fireEvent.click(screen.getByTestId("projection-sync-btn"));
  expect((await screen.findByTestId("sync-row-s")).textContent).toContain("Synced question");
});

test("ignores stale status, preview, and sync responses after paper change", async () => {
  const oldStatus = defer(), oldPreview = defer(), oldSync = defer();
  api.get.mockImplementation((url) => {
    if (url.includes("paper-a") && url.endsWith("/status")) return oldStatus.promise;
    if (url.includes("paper-a") && url.endsWith("/preview")) return oldPreview.promise;
    if (url.includes("paper-b") && url.endsWith("/status")) return Promise.resolve(status(2));
    return Promise.resolve({});
  });
  api.post.mockReturnValue(oldSync.promise);
  const { rerender } = render(<Panel paperId="paper-a" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), { target: { value: "sync old paper" } });
  fireEvent.click(screen.getByTestId("projection-sync-btn"));
  rerender(<Panel paperId="paper-b" />);
  await waitFor(() => expect(screen.getByTestId("pyq-mock-projection-panel").textContent).toMatch(/Total questions:\s*2/));
  await act(async () => {
    oldStatus.resolve(status(99));
    oldPreview.resolve(preview([row("old", "not_exactly_one_correct:0", "Old preview")]));
    oldSync.resolve({ attempted: 1, outcomes: { created: 1 }, questions: [{ question_id: "old-sync", label: "Old sync", outcome: "created" }] });
    await Promise.resolve();
  });
  const panel = screen.getByTestId("pyq-mock-projection-panel");
  expect(panel.textContent).not.toMatch(/Total questions:\s*99/);
  expect(screen.queryByTestId("preview-row-old")).toBeNull();
  expect(screen.queryByTestId("sync-row-old-sync")).toBeNull();
  expect(screen.queryByTestId("projection-zero-eligible-note")).toBeNull();
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), { target: { value: "sync new paper" } });
  expect(screen.getByTestId("projection-sync-btn")).not.toBeDisabled();
});
