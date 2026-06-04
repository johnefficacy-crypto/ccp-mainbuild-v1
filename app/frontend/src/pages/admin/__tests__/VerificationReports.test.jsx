/**
 * Tests for AdminVerificationReports.
 *
 * Covers:
 *   - list renders from collection (useApiCollection wired to correct URL)
 *   - row click opens drawer, card is mounted
 *   - apply-action panel sends correct payload per action_type
 *   - reason length validation (< 8 chars shows inline error)
 *   - useApiAction wiring (post called, success/error paths)
 *   - permission-gated empty state
 *
 * Note: no @testing-library/jest-dom — plain Jest matchers only.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

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

jest.mock("../../../shared/a11y/useFocusTrap", () => ({
  useFocusTrap: () => {},
}));

jest.mock("../../../features/admin/workflow/VerificationReportCard", () => ({
  __esModule: true,
  default: ({ report }) => <div data-testid="vr-card">{report?.id}</div>,
}));

const { api } = require("../../../lib/api");
const { useAuth } = require("../../../lib/authContext");
const useApiCollection = require("../../../lib/hooks/useApiCollection").default;
const AdminVerificationReports = require("../VerificationReports").default;

const MOCK_REPORT = {
  id: "rpt-1",
  lifecycle_status: "classified",
  criticality_tier: "tier_a",
  exam_family_key: "upsc-cse",
  recommended_action: "request_admin_review",
  trigger_reason: "date_changed",
  report_version: 1,
  created_at: "2026-06-01T10:00:00Z",
};

function withPerm() {
  useAuth.mockReturnValue({
    user: { role: "admin", permissions: ["exam_intelligence.cms"] },
  });
}

function withoutPerm() {
  useAuth.mockReturnValue({
    user: { role: "admin", permissions: [] },
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  withPerm();
  // Collection returns one report
  useApiCollection.mockReturnValue({
    items: [MOCK_REPORT],
    status: "live",
    refresh: jest.fn(),
  });
  // Detail fetch + FK pickers — each returns one item so options are populated
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve(MOCK_REPORT);
    }
    if (url.includes("exam-cycles")) {
      return Promise.resolve({ items: [{ id: "cycle-123", cycle_name: "Cycle 2026" }] });
    }
    if (url.includes("exam-phases")) {
      return Promise.resolve({ items: [{ id: "phase-456", phase_name: "Phase 1" }] });
    }
    if (url.includes("policy-updates")) {
      return Promise.resolve({ items: [{ id: "pu-789", title: "Policy A" }] });
    }
    return Promise.resolve({ items: [] });
  });
});

// ─── permission gate ──────────────────────────────────────────────────────────

test("shows permission-denied state when user lacks exam_intelligence.cms", async () => {
  withoutPerm();
  render(<AdminVerificationReports />);
  const msg = await screen.findByTestId("vr-permission-denied");
  expect(msg).toBeTruthy();
});

// ─── list renders from collection ─────────────────────────────────────────────

test("list renders report rows from collection", async () => {
  render(<AdminVerificationReports />);
  const row = await screen.findByTestId("vr-row-rpt-1");
  expect(row).toBeTruthy();
  // Confirm useApiCollection was wired to the correct endpoint
  expect(useApiCollection).toHaveBeenCalledWith(
    "/api/admin/verification-reports",
    expect.anything(),
  );
});

// ─── row click opens drawer and mounts VerificationReportCard ────────────────

test("clicking Open loads detail drawer and mounts VerificationReportCard", async () => {
  render(<AdminVerificationReports />);
  const openBtn = await screen.findByTestId("vr-open-rpt-1");
  fireEvent.click(openBtn);

  await waitFor(() => {
    expect(screen.queryByTestId("report-detail-drawer")).toBeTruthy();
  });
  await waitFor(() => {
    expect(screen.queryByTestId("vr-card")).toBeTruthy();
  });
  expect(api.get).toHaveBeenCalledWith("/api/admin/verification-reports/rpt-1");
});

// ─── reason length validation ─────────────────────────────────────────────────

test("shows inline error when reason is fewer than 8 chars", async () => {
  render(<AdminVerificationReports />);
  const openBtn = await screen.findByTestId("vr-open-rpt-1");
  fireEvent.click(openBtn);

  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "policy_update_create" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "short" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => {
    expect(screen.queryByTestId("rar-error")).toBeTruthy();
  });
  expect(api.post).not.toHaveBeenCalled();
});

// ─── apply-action payload — cycle_date_update ─────────────────────────────────

test("apply-action sends correct payload for cycle_date_update", async () => {
  api.post.mockResolvedValueOnce({ ok: true, action_id: "act-1" });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });
  // Wait for FK options to load before selecting
  await screen.findByTestId("rar-exam-cycle-id");
  await waitFor(() => {
    const sel = screen.getByTestId("rar-exam-cycle-id");
    if (sel.options.length < 2) throw new Error("options not loaded");
  });
  fireEvent.change(screen.getByTestId("rar-exam-cycle-id"), { target: { value: "cycle-123" } });
  fireEvent.change(screen.getByTestId("rar-patch"), { target: { value: '{"notification_date":"2026-08-01"}' } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "notification date shifted per gazette" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [url, body] = api.post.mock.calls[0];
  expect(url).toBe("/api/admin/verification-reports/rpt-1/apply-registry-action");
  expect(body.action_type).toBe("cycle_date_update");
  expect(body.exam_cycle_id).toBe("cycle-123");
  expect(body.patch).toEqual({ notification_date: "2026-08-01" });
  expect(body.reason).toBe("notification date shifted per gazette");
  expect(body.event_source_id).toBeUndefined();
});

// ─── apply-action payload — policy_update_create ─────────────────────────────

test("apply-action sends correct payload for policy_update_create (no FK required)", async () => {
  api.post.mockResolvedValueOnce({ ok: true, action_id: "act-2" });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "policy_update_create" } });
  fireEvent.change(screen.getByTestId("rar-patch"), { target: { value: '{"title":"New policy"}' } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "creating new policy update entry from report" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const body = api.post.mock.calls[0][1];
  expect(body.action_type).toBe("policy_update_create");
  expect(body.exam_cycle_id).toBeUndefined();
  expect(body.exam_phase_id).toBeUndefined();
  expect(body.policy_update_id).toBeUndefined();
  expect(body.event_source_id).toBeUndefined();
});

// ─── apply-action payload — phase_date_update ────────────────────────────────

test("apply-action sends correct payload for phase_date_update", async () => {
  api.post.mockResolvedValueOnce({ ok: true });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "phase_date_update" } });
  await screen.findByTestId("rar-exam-phase-id");
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-phase-id").options.length < 2) throw new Error("options not loaded");
  });
  fireEvent.change(screen.getByTestId("rar-exam-phase-id"), { target: { value: "phase-456" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "phase admit card date updated per official notice" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const body = api.post.mock.calls[0][1];
  expect(body.action_type).toBe("phase_date_update");
  expect(body.exam_phase_id).toBe("phase-456");
  expect(body.event_source_id).toBeUndefined();
});

// ─── apply-action payload — policy_update_edit ───────────────────────────────

test("apply-action sends correct payload for policy_update_edit", async () => {
  api.post.mockResolvedValueOnce({ ok: true });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "policy_update_edit" } });
  await screen.findByTestId("rar-policy-update-id");
  await waitFor(() => {
    if (screen.getByTestId("rar-policy-update-id").options.length < 2) throw new Error("options not loaded");
  });
  fireEvent.change(screen.getByTestId("rar-policy-update-id"), { target: { value: "pu-789" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "updating policy title from official gazette notification" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const body = api.post.mock.calls[0][1];
  expect(body.action_type).toBe("policy_update_edit");
  expect(body.policy_update_id).toBe("pu-789");
  expect(body.event_source_id).toBeUndefined();
});

// ─── useApiAction wiring — inline error on failure ───────────────────────────

test("shows inline error when api.post rejects", async () => {
  api.post.mockRejectedValueOnce(new Error("Permission denied"));

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "policy_update_create" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "reason long enough for validation" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => {
    expect(screen.queryByTestId("rar-error")).toBeTruthy();
  });
});
