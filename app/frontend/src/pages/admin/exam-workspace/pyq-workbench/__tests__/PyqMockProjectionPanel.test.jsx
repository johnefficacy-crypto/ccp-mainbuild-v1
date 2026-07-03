import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
jest.mock("../../../../../lib/hooks/useApiAction", () => ({ __esModule: true, default: () => ({
  run: async ({ action, onSuccess }) => { try { const data = await action(); onSuccess?.(data); return { ok: true }; } catch (error) { return { ok: false, error }; } },
}) }));

const { api } = require("../../../../../lib/api");
const Panel = require("../PyqMockProjectionPanel").default;
const status = (n = 10) => ({ total_questions: n, unprojected_count: n, projection_counts: {}, stale_projections: [] });
const row = (id, reason, label = id) => ({ question_id: id, label, eligible: false, reason });
const report = (rows, eligible = 0) => ({ eligible_count: eligible, ineligible_count: rows.length, would_create_count: eligible, would_update_count: 0, questions: rows });
const defer = () => { let resolve; const promise = new Promise((done) => { resolve = done; }); return { promise, resolve }; };
const serve = (preview) => api.get.mockImplementation((url) => Promise.resolve(url.endsWith("/status") ? status() : preview));

beforeEach(() => { api.get.mockReset(); api.post.mockReset(); });

test("shows the complete contract and truthful blocker groups", async () => {
  serve(report([
    row("tm", "not_exactly_one_verified_primary_tag:0", "Missing tag"),
    row("td", "not_exactly_one_verified_primary_tag:2"),
    row("cn", "not_exactly_one_correct:0"),
    row("cm", "not_exactly_one_correct:2"),
  ]));
  render(<Panel paperId="p" />);
  const info = await screen.findByTestId("projection-info-disclosure");
  expect(info.textContent).toMatch(/MCQ type.*at least two verified options.*exactly one verified correct option.*exactly one verified primary topic tag/i);
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), { target: { value: "valid audit reason" } });
  fireEvent.click(screen.getByTestId("projection-preview-btn"));
  const text = (await screen.findByTestId("projection-blocker-summary")).textContent;
  expect(text).toMatch(/1\s*Missing verified primary topic tag/);
  expect(text).toMatch(/1\s*Multiple verified primary tags/);
  expect(text).toMatch(/1\s*No verified correct option/);
  expect(text).toMatch(/1\s*Multiple verified correct options/);
  expect(screen.getByTestId("preview-row-cm").textContent).toMatch(/has 2/);
  expect(screen.getByTestId("preview-row-tm").textContent).toContain("Missing tag");
  expect(screen.getByTestId("projection-sync-btn")).toBeDisabled();
});

test("hides UUID details and shows a sync label", async () => {
  const uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
  serve(report([row("bad", `correct_option_id_mismatch:${uuid}`, "Mismatch")], 1));
  api.post.mockResolvedValue({ attempted: 1, outcomes: { created: 1 }, questions: [{ question_id: "s", label: "Synced question", outcome: "created" }] });
  render(<Panel paperId="p" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));
  expect((await screen.findByTestId("projection-preview-results")).textContent).not.toContain(uuid);
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), { target: { value: "sync this question" } });
  fireEvent.click(screen.getByTestId("projection-sync-btn"));
  expect((await screen.findByTestId("sync-row-s")).textContent).toContain("Synced question");
});

test("drops stale status, preview and sync responses after a paper change", async () => {
  const aStatus = defer(), aPreview = defer(), aSync = defer();
  api.get.mockImplementation((url) => {
    if (url.includes("a") && url.endsWith("/status")) return aStatus.promise;
    if (url.includes("a") && url.endsWith("/preview")) return aPreview.promise;
    return Promise.resolve(url.endsWith("/status") ? status(2) : {});
  });
  api.post.mockReturnValue(aSync.promise);
  const { rerender } = render(<Panel paperId="a" />);
  fireEvent.click(screen.getByTestId("projection-preview-btn"));
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), { target: { value: "sync old paper" } });
  fireEvent.click(screen.getByTestId("projection-sync-btn"));
  rerender(<Panel paperId="b" />);
  await waitFor(() => expect(screen.getByTestId("pyq-mock-projection-panel").textContent).toMatch(/Total questions:\s*2/));
  await act(async () => {
    aStatus.resolve(status(99));
    aPreview.resolve(report([row("old", "not_exactly_one_correct:0")]));
    aSync.resolve({ attempted: 1, outcomes: { created: 1 }, questions: [{ question_id: "old-sync", label: "Old sync", outcome: "created" }] });
    await Promise.resolve();
  });
  expect(screen.getByTestId("pyq-mock-projection-panel").textContent).not.toMatch(/Total questions:\s*99/);
  expect(screen.queryByTestId("preview-row-old")).toBeNull();
  expect(screen.queryByTestId("sync-row-old-sync")).toBeNull();
  expect(screen.queryByTestId("projection-zero-eligible-note")).toBeNull();
  fireEvent.change(screen.getByTestId("projection-audit-reason-input"), { target: { value: "sync new paper" } });
  expect(screen.getByTestId("projection-sync-btn")).not.toBeDisabled();
});
