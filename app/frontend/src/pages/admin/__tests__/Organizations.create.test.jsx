/**
 * Tests for the "New organization" create form on Organizations.jsx.
 * Covers: correct payload, 422 (missing short_name), 409 (dup), 201 + warnings[].
 *
 * Note: this repo's CRA setup has no @testing-library/jest-dom; assertions use
 * plain Jest matchers (queryBy*-toBeNull, textContent, truthy/falsy) only.
 */
import React from "react";
import { act, render, screen, fireEvent, waitFor } from "@testing-library/react";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), put: jest.fn() },
}));

jest.mock("../../../features/admin/shared/useAdminAction", () => ({
  __esModule: true,
  default: () => ({ runAction: jest.fn(), busyKey: null, error: null }),
}));

jest.mock("../../../services/adminTrustService", () => ({
  __esModule: true,
  adminTrustService: { organizationAudit: jest.fn().mockResolvedValue({ items: [] }) },
}));

jest.mock("../../../features/admin/shared/AuditTimelineDrawer", () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock("../../../features/admin/organizations/OrganizationEditPanel", () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock("../../../shared/a11y/useFocusTrap", () => ({
  useFocusTrap: () => {},
}));

const { api } = require("../../../lib/api");
const Organizations = require("../Organizations").default;

beforeEach(() => {
  jest.clearAllMocks();
  api.get.mockResolvedValue({ items: [] });
});

function renderPage() {
  return render(<Organizations />);
}

async function openCreateModal() {
  const btn = await screen.findByRole("button", { name: /new organization/i });
  fireEvent.click(btn);
}

// ─── Button visibility ────────────────────────────────────────────────────────

test("shows New Organization button", async () => {
  renderPage();
  const btn = await screen.findByRole("button", { name: /new organization/i });
  expect(btn).toBeTruthy();
});

// ─── Correct payload ──────────────────────────────────────────────────────────

test("submits correct payload with required fields", async () => {
  api.post.mockResolvedValueOnce({ id: "org-1", name: "RPSC", warnings: [] });
  renderPage();
  await openCreateModal();

  fireEvent.change(screen.getByTestId("org-create-name"), { target: { value: "RPSC" } });
  fireEvent.change(screen.getByTestId("org-create-type"), { target: { value: "state_psc" } });
  fireEvent.change(screen.getByTestId("org-create-short_name"), { target: { value: "RPSC" } });

  fireEvent.click(screen.getByRole("button", { name: /create organization/i }));

  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith(
      "/api/admin/organizations",
      expect.objectContaining({ name: "RPSC", type: "state_psc", short_name: "RPSC" }),
    );
  });
});

test("payload never contains is_verified or trust_tier", async () => {
  api.post.mockResolvedValueOnce({ id: "org-1", name: "Test", warnings: [] });
  renderPage();
  await openCreateModal();

  fireEvent.change(screen.getByTestId("org-create-name"), { target: { value: "Test" } });
  fireEvent.change(screen.getByTestId("org-create-type"), { target: { value: "central" } });
  fireEvent.change(screen.getByTestId("org-create-short_name"), { target: { value: "TST" } });
  fireEvent.click(screen.getByRole("button", { name: /create organization/i }));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const payload = api.post.mock.calls[0][1];
  expect(payload.is_verified).toBeUndefined();
  expect(payload.trust_tier).toBeUndefined();
});

// ─── 422 / 409 inline errors ─────────────────────────────────────────────────

test("shows inline error on 422 missing short_name", async () => {
  api.post.mockRejectedValueOnce(new Error("short_name is required"));

  renderPage();
  await openCreateModal();

  fireEvent.change(screen.getByTestId("org-create-name"), { target: { value: "Test" } });
  fireEvent.change(screen.getByTestId("org-create-type"), { target: { value: "central" } });
  fireEvent.click(screen.getByRole("button", { name: /create organization/i }));

  await waitFor(() => {
    expect(screen.queryByTestId("org-create-error")).toBeTruthy();
  });
});

test("shows inline error on 409 dup", async () => {
  api.post.mockRejectedValueOnce(new Error("Duplicate organization"));

  renderPage();
  await openCreateModal();

  fireEvent.change(screen.getByTestId("org-create-name"), { target: { value: "RPSC" } });
  fireEvent.change(screen.getByTestId("org-create-type"), { target: { value: "state_psc" } });
  fireEvent.change(screen.getByTestId("org-create-short_name"), { target: { value: "RPSC" } });
  fireEvent.click(screen.getByRole("button", { name: /create organization/i }));

  await waitFor(() => {
    expect(screen.queryByTestId("org-create-error")).toBeTruthy();
  });
});

// ─── 201 + warnings[] ─────────────────────────────────────────────────────────

test("shows non-blocking page-level warning on 201 with warnings[]", async () => {
  api.post.mockResolvedValueOnce({
    id: "org-2",
    name: "RPSC",
    warnings: [{ existing_id: "org-1", existing_name: "RPSC old" }],
  });

  renderPage();
  await openCreateModal();

  fireEvent.change(screen.getByTestId("org-create-name"), { target: { value: "RPSC" } });
  fireEvent.change(screen.getByTestId("org-create-type"), { target: { value: "state_psc" } });
  fireEvent.change(screen.getByTestId("org-create-short_name"), { target: { value: "RPSC2" } });
  fireEvent.click(screen.getByRole("button", { name: /create organization/i }));

  await waitFor(() => {
    expect(screen.queryByTestId("org-create-warning")).toBeTruthy();
  });
});
