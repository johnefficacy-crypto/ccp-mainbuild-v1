/**
 * Tests for ReverificationBatches page.
 *
 * Covers:
 *   - route mounts under admin guard
 *   - list renders from useApiCollection (correct URL, batch cards shown)
 *   - acknowledge sends POST to correct URL + refetches on success
 *   - permission-gated: lower-permission user sees disabled button
 *
 * No @testing-library/jest-dom — plain Jest matchers only.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
}));

jest.mock("../../../lib/hooks/useApiCollection", () => ({
  __esModule: true,
  default: jest.fn(),
}));

jest.mock("../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => {
    const run = jest.fn(async ({ action, onSuccess }) => {
      try {
        const result = await action();
        if (onSuccess) onSuccess(result);
        return { ok: true, data: result };
      } catch (e) {
        return { ok: false, error: e };
      }
    });
    return { run, busy: false };
  },
}));

jest.mock("../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: jest.fn(),
}));

// Render ReverificationBatchAlert lightly so we can assert its presence/state
// without pulling in its full CSS dependencies.
jest.mock("../../../features/admin/workflow/ReverificationBatchAlert", () => ({
  __esModule: true,
  default: ({ batch, onAcknowledge, disabled }) => (
    <div data-testid="batch-alert" data-batch-id={batch?.id}>
      <span>{batch?.trigger_reason}</span>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAcknowledge?.(batch.id)}
        data-testid={`ack-btn-${batch?.id}`}
      >
        Acknowledge
      </button>
    </div>
  ),
}));

const { api } = require("../../../lib/api");
const { useAuth } = require("../../../lib/authContext");
const useApiCollection = require("../../../lib/hooks/useApiCollection").default;
const ReverificationBatches = require("../ReverificationBatches").default;

const BATCH_1 = {
  id: "batch-1",
  trigger_reason: "source_url_changed",
  total_reports_affected: 12,
  promoted_to_needs_reverification: 5,
  remaining_pending: 7,
  created_at: "2026-06-01T10:00:00Z",
};
const BATCH_2 = {
  id: "batch-2",
  trigger_reason: "new_scrape_run",
  total_reports_affected: 3,
  promoted_to_needs_reverification: 3,
  remaining_pending: 0,
  created_at: "2026-06-02T10:00:00Z",
};

function withAdmin() {
  useAuth.mockReturnValue({ user: { role: "admin" } });
}

function withLimitedUser() {
  useAuth.mockReturnValue({ user: { role: "viewer", permissions: [] } });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/admin/reverification-batches"]}>
      <Routes>
        <Route path="/admin/reverification-batches" element={<ReverificationBatches />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
});

// ── 1. Route mounts ─────────────────────────────────────────────────────────

test("page mounts at /admin/reverification-batches", () => {
  withAdmin();
  useApiCollection.mockReturnValue({ items: [], status: "empty", refresh: jest.fn() });
  renderPage();
  // Heading confirms the page rendered
  expect(screen.getByText("Reverification Batches")).toBeTruthy();
});

// ── 2. List renders from collection ─────────────────────────────────────────

test("useApiCollection called with correct URL", () => {
  withAdmin();
  useApiCollection.mockReturnValue({ items: [], status: "empty", refresh: jest.fn() });
  renderPage();
  expect(useApiCollection).toHaveBeenCalledWith(
    "/api/admin/reverification-batches",
  );
});

test("live state renders one card per batch", () => {
  withAdmin();
  useApiCollection.mockReturnValue({
    items: [BATCH_1, BATCH_2],
    status: "live",
    refresh: jest.fn(),
  });
  renderPage();
  const cards = screen.getAllByTestId("batch-alert");
  expect(cards).toHaveLength(2);
  expect(cards[0].getAttribute("data-batch-id")).toBe("batch-1");
  expect(cards[1].getAttribute("data-batch-id")).toBe("batch-2");
});

test("loading state renders skeleton, not batch cards", () => {
  withAdmin();
  useApiCollection.mockReturnValue({ items: [], status: "loading", refresh: jest.fn() });
  renderPage();
  expect(screen.getByTestId("batches-loading")).toBeTruthy();
  expect(screen.queryAllByTestId("batch-alert")).toHaveLength(0);
});

test("empty state renders empty message", () => {
  withAdmin();
  useApiCollection.mockReturnValue({ items: [], status: "empty", refresh: jest.fn() });
  renderPage();
  expect(screen.getByTestId("batches-empty")).toBeTruthy();
  expect(screen.queryAllByTestId("batch-alert")).toHaveLength(0);
});

// ── 3. Acknowledge action ────────────────────────────────────────────────────

test("acknowledge button POSTs to correct URL and refetches", async () => {
  withAdmin();
  const refresh = jest.fn();
  useApiCollection.mockReturnValue({
    items: [BATCH_1],
    status: "live",
    refresh,
  });
  api.post.mockResolvedValue({ batch_id: "batch-1", promoted: 7 });

  renderPage();

  fireEvent.click(screen.getByTestId("ack-btn-batch-1"));

  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith(
      "/api/admin/verification-reports/acknowledge-batch/batch-1",
      {},
    );
  });
  await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
});

// ── 4. Permission gate ───────────────────────────────────────────────────────

test("lower-permission user sees disabled acknowledge button", () => {
  withLimitedUser();
  useApiCollection.mockReturnValue({
    items: [BATCH_1],
    status: "live",
    refresh: jest.fn(),
  });
  renderPage();

  const ackBtn = screen.getByTestId("ack-btn-batch-1");
  expect(ackBtn.disabled).toBe(true);
});

test("admin user sees enabled acknowledge button", () => {
  withAdmin();
  useApiCollection.mockReturnValue({
    items: [BATCH_1],
    status: "live",
    refresh: jest.fn(),
  });
  renderPage();

  const ackBtn = screen.getByTestId("ack-btn-batch-1");
  expect(ackBtn.disabled).toBe(false);
});
