import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  getApiUnverifiedFields: () => [],
  getApiExistingRecruitmentId: () => null,
  getApiNextActions: () => [],
}));

jest.mock("../../../shared/ui/core", () => ({
  __esModule: true,
  EmptyState: () => null,
  ErrorState: () => null,
  LoadingSkeleton: () => null,
  StatusBadge: ({ label }) => <span>{label}</span>,
  useToast: () => ({ success: jest.fn(), error: jest.fn() }),
}));

import { api } from "../../../lib/api";
import Scraper from "../Scraper";

const ONE_ITEM = {
  id: "queue-abc-123",
  status: "pending",
  source_name: "Official",
  source_type: "official_html",
  extracted_data: { title: "Sample" },
  unverified_fields: [],
  duplicate_candidates: [],
};

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  api.get.mockImplementation((path) => {
    if (path.startsWith("/api/admin/scrape/runs")) return Promise.resolve({ items: [] });
    if (path.startsWith("/api/admin/sources")) return Promise.resolve({ items: [] });
    if (path.startsWith("/api/admin/scrape/queue")) return Promise.resolve({ items: [ONE_ITEM], total: 1 });
    return Promise.resolve({ items: [] });
  });
});

test("Scraper page renders the role banner at the top", async () => {
  render(
    <MemoryRouter>
      <Scraper />
    </MemoryRouter>,
  );
  const banner = await screen.findByTestId("scraper-role-banner");
  expect(banner.textContent).toMatch(/Scrape Monitor/);
  expect(banner.textContent).toMatch(/Daily review is in Operations/);
});

test("Scraper queue row exposes a single Inspect action; the workspace link lives in the drawer", async () => {
  render(
    <MemoryRouter>
      <Scraper />
    </MemoryRouter>,
  );
  // One action per row — Inspect — and no separate row-level deep link.
  await waitFor(() => expect(screen.getByTestId("scrape-row-inspect-queue-abc-123")).toBeTruthy());
  expect(screen.queryByTestId("scrape-row-open-ops-queue-abc-123")).toBeNull();

  // Opening the read-only inspector surfaces the Pipeline Workspace link.
  fireEvent.click(screen.getByTestId("scrape-row-inspect-queue-abc-123"));
  await waitFor(() => expect(screen.getByTestId("scrape-drawer-open-ops")).toBeTruthy());
  expect(screen.getByTestId("scrape-drawer-open-ops").getAttribute("href")).toBe(
    "/admin/operations?queue_id=queue-abc-123&mode=queue",
  );
});
