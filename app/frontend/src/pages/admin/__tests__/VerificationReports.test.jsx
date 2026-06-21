/**
 * Tests for AdminVerificationReports.
 *
 * Covers:
 *   - list renders from collection (useApiCollection wired to correct URL)
 *   - row click opens drawer, card is mounted
 *   - apply-action panel permission gate (exam_intelligence.cms OR super_admin)
 *   - guided forms for cycle_date_update + phase_date_update
 *   - exam-scoped FK pickers; null exam_id degrade + warning
 *   - patch built from changed fields only; empty-patch blocked; date ordering
 *   - before-state current values rendered
 *   - 422/409 errors surfaced inline
 *   - reason length validation
 *   - policy_update_create/edit: JSON path unchanged
 *   - promote/reject, run-resolver, confirm-proof, override-conflict panels
 *   - bulk multi-select + toolbar
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

jest.mock("../../../features/admin/workflow/BulkActionPreview", () => ({
  __esModule: true,
  default: ({ dryRun, onApply, disabled }) => (
    <div data-testid="bulk-action-preview">
      <span data-testid="bap-eligible">{dryRun?.result?.eligible_count}</span>
      <span data-testid="bap-blocked">{dryRun?.result?.blocked_count}</span>
      <span data-testid="bap-action">{dryRun?.action}</span>
      <button
        type="button"
        disabled={disabled || (dryRun?.result?.eligible_count || 0) === 0}
        onClick={onApply}
        data-testid="bap-apply-btn"
      >
        Apply
      </button>
    </div>
  ),
}));

const { api } = require("../../../lib/api");
const { useAuth } = require("../../../lib/authContext");
const useApiCollection = require("../../../lib/hooks/useApiCollection").default;
const AdminVerificationReports = require("../VerificationReports").default;

const MOCK_REPORT = {
  id: "rpt-1",
  exam_id: null,
  lifecycle_status: "classified",
  criticality_tier: "tier_a",
  exam_family_key: "upsc-cse",
  recommended_action: "request_admin_review",
  trigger_reason: "date_changed",
  report_version: 1,
  created_at: "2026-06-01T10:00:00Z",
  suggested_official_urls: [
    { url: "https://upsc.gov.in/official", method: "serpapi", confidence: 0.95 },
    { url: "https://upsc.gov.in/alternate", method: "crawl", confidence: 0.72 },
  ],
  conflicts: [
    {
      conflict_id: "conf-1",
      field_path: "apply_end_date",
      status: "open",
      values: [
        { source: "scraper_a", value: "2026-08-01" },
        { source: "scraper_b", value: "2026-08-15" },
      ],
    },
  ],
};

const MOCK_CYCLE = {
  id: "cycle-123",
  cycle_name: "Cycle 2026",
  status: "expected",
  notification_date: null,
  application_start: null,
  application_end: null,
  exam_start: null,
  exam_end: null,
};

const MOCK_PHASE = {
  id: "phase-456",
  phase_name: "Phase 1",
  status: "expected",
  phase_start: null,
  phase_end: null,
};

// withPerm: admin + exam_intelligence.cms (needed to see apply-action panel)
function withPerm() {
  useAuth.mockReturnValue({
    user: { role: "admin", permissions: ["exam_intelligence.cms"] },
  });
}

function withoutPerm() {
  useAuth.mockReturnValue({
    user: { role: "viewer", permissions: ["exam_intelligence.cms"] },
  });
}

function withSuperAdmin() {
  useAuth.mockReturnValue({
    user: { role: "super_admin", permissions: [] },
  });
}

function withAdminAndRecruitments() {
  useAuth.mockReturnValue({
    user: { role: "admin", permissions: ["exam_intelligence.cms", "recruitments.manage"] },
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  withPerm();
  useApiCollection.mockReturnValue({
    items: [MOCK_REPORT],
    status: "live",
    refresh: jest.fn(),
  });
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve(MOCK_REPORT);
    }
    if (url.includes("exam-cycles")) {
      return Promise.resolve({ items: [MOCK_CYCLE] });
    }
    if (url.includes("exam-phases")) {
      return Promise.resolve({ items: [MOCK_PHASE] });
    }
    if (url.includes("policy-updates")) {
      return Promise.resolve({ items: [{ id: "pu-789", title: "Policy A" }] });
    }
    return Promise.resolve({ items: [] });
  });
});

// ─── permission gate ──────────────────────────────────────────────────────────

test("shows permission-denied state for non-admin role", async () => {
  withoutPerm();
  render(<AdminVerificationReports />);
  const msg = await screen.findByTestId("vr-permission-denied");
  expect(msg).toBeTruthy();
});

test("plain admin role is admitted (not denied)", async () => {
  useAuth.mockReturnValue({ user: { role: "admin", permissions: [] } });
  useApiCollection.mockReturnValue({ items: [], status: "empty", refresh: jest.fn() });
  render(<AdminVerificationReports />);
  await new Promise((r) => setTimeout(r, 0));
  expect(screen.queryByTestId("vr-permission-denied")).toBeFalsy();
});

// ─── apply-action panel permission gate ───────────────────────────────────────

test("apply-action panel hidden when admin lacks exam_intelligence.cms and is not super_admin", async () => {
  useAuth.mockReturnValue({ user: { role: "admin", permissions: [] } });
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("report-detail-card"));
  expect(screen.queryByTestId("apply-action-form")).toBeFalsy();
});

test("apply-action panel shown for exam_intelligence.cms holder", async () => {
  withPerm(); // admin + exam_intelligence.cms
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => expect(screen.queryByTestId("apply-action-form")).toBeTruthy());
});

test("apply-action panel shown for super_admin without explicit perm", async () => {
  withSuperAdmin();
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => expect(screen.queryByTestId("apply-action-form")).toBeTruthy());
});

// ─── list renders from collection ─────────────────────────────────────────────

test("list renders report rows from collection", async () => {
  render(<AdminVerificationReports />);
  const row = await screen.findByTestId("vr-row-rpt-1");
  expect(row).toBeTruthy();
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

  await waitFor(() => expect(screen.queryByTestId("report-detail-drawer")).toBeTruthy());
  await waitFor(() => expect(screen.queryByTestId("vr-card")).toBeTruthy());
  expect(api.get).toHaveBeenCalledWith("/api/admin/verification-reports/rpt-1");
});

// ─── cycle picker scoping ─────────────────────────────────────────────────────

test("cycle picker requests /exam-cycles with exam_id when report.exam_id is set", async () => {
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => expect(screen.queryByTestId("apply-action-form")).toBeTruthy());

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });

  await waitFor(() => {
    const cycleCalls = api.get.mock.calls.filter(([u]) => u.includes("exam-cycles"));
    expect(cycleCalls.some(([u]) => u.includes("exam_id=exam-uuid-1"))).toBe(true);
  });
});

test("report.exam_id null: cycle picker requests global URL AND warning rendered", async () => {
  // MOCK_REPORT has exam_id: null by default
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => expect(screen.queryByTestId("apply-action-form")).toBeTruthy());

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });

  await waitFor(() => expect(screen.queryByTestId("rar-no-scope-warning")).toBeTruthy());

  // The URL should NOT contain exam_id param
  await waitFor(() => {
    const cycleCalls = api.get.mock.calls.filter(([u]) => u.includes("exam-cycles"));
    expect(cycleCalls.some(([u]) => !u.includes("exam_id"))).toBe(true);
  });
});

// ─── phase flow scoping ───────────────────────────────────────────────────────

test("phase picker requests /exam-phases with exam_id + exam_cycle_id (template rows excluded)", async () => {
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    if (url.includes("exam-phases")) return Promise.resolve({ items: [MOCK_PHASE] });
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => expect(screen.queryByTestId("apply-action-form")).toBeTruthy());

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "phase_date_update" } });

  // Step 1: wait for cycle options then select
  await waitFor(() => {
    if (screen.getByTestId("rar-phase-cycle-id").options.length < 2) throw new Error("cycle opts");
  });
  fireEvent.change(screen.getByTestId("rar-phase-cycle-id"), { target: { value: "cycle-123" } });

  // Phase picker should appear and fetch scoped URL
  await waitFor(() => expect(screen.queryByTestId("rar-exam-phase-id")).toBeTruthy());
  await waitFor(() => {
    const phaseCalls = api.get.mock.calls.filter(([u]) => u.includes("exam-phases"));
    expect(
      phaseCalls.some(([u]) => u.includes("exam_id=exam-uuid-1") && u.includes("exam_cycle_id=cycle-123")),
    ).toBe(true);
  });
});

// ─── reason length validation ─────────────────────────────────────────────────

test("shows inline error when reason is fewer than 8 chars", async () => {
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "policy_update_create" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "short" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

// ─── apply-action payload — cycle_date_update (guided form) ──────────────────

test("apply-action sends correct payload for cycle_date_update via guided form", async () => {
  api.post.mockResolvedValueOnce({ ok: true, action_id: "act-1" });
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });

  await waitFor(() => {
    if (screen.getByTestId("rar-exam-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-cycle-id"), { target: { value: "cycle-123" } });

  // Guided date fields appear after cycle selected
  await waitFor(() => expect(screen.queryByTestId("rar-notification-date")).toBeTruthy());
  fireEvent.change(screen.getByTestId("rar-notification-date"), { target: { value: "2026-08-01" } });
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

// ─── generated patch contains only changed fields ─────────────────────────────

test("patch contains only the changed field — unchanged fields omitted", async () => {
  api.post.mockResolvedValueOnce({ ok: true });
  // Cycle has existing application_start value; user only changes notification_date
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) {
      return Promise.resolve({
        items: [{
          ...MOCK_CYCLE,
          application_start: "2026-09-01",  // already set
        }],
      });
    }
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-cycle-id"), { target: { value: "cycle-123" } });

  await waitFor(() => expect(screen.queryByTestId("rar-notification-date")).toBeTruthy());
  // Only set notification_date; leave application_start alone
  fireEvent.change(screen.getByTestId("rar-notification-date"), { target: { value: "2026-07-15" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "official notification date confirmed" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const body = api.post.mock.calls[0][1];
  expect(Object.keys(body.patch)).toEqual(["notification_date"]);
  expect(body.patch.application_start).toBeUndefined();
});

// ─── empty patch blocked ──────────────────────────────────────────────────────

test("empty patch (no field changed) blocked before POST", async () => {
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-cycle-id"), { target: { value: "cycle-123" } });

  await waitFor(() => expect(screen.queryByTestId("rar-notification-date")).toBeTruthy());
  // Don't fill in any date
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "reason long enough here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

// ─── reversed dates rejected ──────────────────────────────────────────────────

test("exam_end before exam_start rejected", async () => {
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-cycle-id"), { target: { value: "cycle-123" } });

  await waitFor(() => expect(screen.queryByTestId("rar-exam-start")).toBeTruthy());
  fireEvent.change(screen.getByTestId("rar-exam-start"), { target: { value: "2026-10-01" } });
  fireEvent.change(screen.getByTestId("rar-exam-end"), { target: { value: "2026-09-01" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  const errorText = screen.getByTestId("rar-error").textContent;
  expect(errorText.toLowerCase()).toContain("exam end");
  expect(api.post).not.toHaveBeenCalled();
});

test("application_end before application_start rejected", async () => {
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-cycle-id"), { target: { value: "cycle-123" } });

  await waitFor(() => expect(screen.queryByTestId("rar-application-start")).toBeTruthy());
  fireEvent.change(screen.getByTestId("rar-application-start"), { target: { value: "2026-09-15" } });
  fireEvent.change(screen.getByTestId("rar-application-end"), { target: { value: "2026-09-01" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

test("phase_end before phase_start rejected", async () => {
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    if (url.includes("exam-phases")) return Promise.resolve({ items: [MOCK_PHASE] });
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "phase_date_update" } });
  await waitFor(() => {
    if (screen.getByTestId("rar-phase-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-phase-cycle-id"), { target: { value: "cycle-123" } });
  await waitFor(() => expect(screen.queryByTestId("rar-exam-phase-id")).toBeTruthy());
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-phase-id").options.length < 2) throw new Error("phase opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-phase-id"), { target: { value: "phase-456" } });

  await waitFor(() => expect(screen.queryByTestId("rar-phase-start")).toBeTruthy());
  fireEvent.change(screen.getByTestId("rar-phase-start"), { target: { value: "2026-11-15" } });
  fireEvent.change(screen.getByTestId("rar-phase-end"), { target: { value: "2026-11-01" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

// ─── merged-row date validation (existing opposite side from row) ─────────────

async function setupCycleDateForm(examId = "exam-uuid-1", cycleOverrides = {}) {
  const cycle = { ...MOCK_CYCLE, ...cycleOverrides };
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1")
      return Promise.resolve({ ...MOCK_REPORT, exam_id: examId });
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [cycle] });
    return Promise.resolve({ items: [] });
  });
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));
  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-cycle-id"), { target: { value: "cycle-123" } });
  await waitFor(() => expect(screen.queryByTestId("rar-exam-start")).toBeTruthy());
}

test("existing exam_start in row, input exam_end before it → blocked", async () => {
  await setupCycleDateForm("exam-uuid-1", { exam_start: "2026-10-01" });
  fireEvent.change(screen.getByTestId("rar-exam-end"), { target: { value: "2026-09-01" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));
  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(screen.getByTestId("rar-error").textContent.toLowerCase()).toContain("exam");
  expect(api.post).not.toHaveBeenCalled();
});

test("existing application_start in row, input application_end before it → blocked", async () => {
  await setupCycleDateForm("exam-uuid-1", { application_start: "2026-09-15" });
  fireEvent.change(screen.getByTestId("rar-application-end"), { target: { value: "2026-09-01" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));
  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

test("existing exam_end in row, input exam_start after it → blocked", async () => {
  await setupCycleDateForm("exam-uuid-1", { exam_end: "2026-10-01" });
  fireEvent.change(screen.getByTestId("rar-exam-start"), { target: { value: "2026-10-15" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));
  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

test("existing application_start, input application_end after it → allowed", async () => {
  api.post.mockResolvedValueOnce({ ok: true });
  await setupCycleDateForm("exam-uuid-1", { application_start: "2026-09-01" });
  fireEvent.change(screen.getByTestId("rar-application-end"), { target: { value: "2026-09-30" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  expect(screen.queryByTestId("rar-error")).toBeFalsy();
});

test("same-day window: existing exam_start timestamptz, input exam_end date-only same day → allowed", async () => {
  api.post.mockResolvedValueOnce({ ok: true });
  await setupCycleDateForm("exam-uuid-1", { exam_start: "2026-10-01T00:00:00Z" });
  fireEvent.change(screen.getByTestId("rar-exam-end"), { target: { value: "2026-10-01" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  expect(screen.queryByTestId("rar-error")).toBeFalsy();
});

async function setupPhaseDateForm() {
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1")
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    if (url.includes("exam-phases"))
      return Promise.resolve({ items: [{ ...MOCK_PHASE, phase_start: "2026-11-15" }] });
    return Promise.resolve({ items: [] });
  });
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));
  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "phase_date_update" } });
  await waitFor(() => {
    if (screen.getByTestId("rar-phase-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-phase-cycle-id"), { target: { value: "cycle-123" } });
  await waitFor(() => expect(screen.queryByTestId("rar-exam-phase-id")).toBeTruthy());
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-phase-id").options.length < 2) throw new Error("phase opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-phase-id"), { target: { value: "phase-456" } });
  await waitFor(() => expect(screen.queryByTestId("rar-phase-start")).toBeTruthy());
}

test("existing phase_start in row, input phase_end before it → blocked", async () => {
  await setupPhaseDateForm();
  fireEvent.change(screen.getByTestId("rar-phase-end"), { target: { value: "2026-11-01" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));
  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

test("existing phase_end in row, input phase_start after it → blocked", async () => {
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1")
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    if (url.includes("exam-phases"))
      return Promise.resolve({ items: [{ ...MOCK_PHASE, phase_end: "2026-11-01" }] });
    return Promise.resolve({ items: [] });
  });
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));
  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "phase_date_update" } });
  await waitFor(() => {
    if (screen.getByTestId("rar-phase-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-phase-cycle-id"), { target: { value: "cycle-123" } });
  await waitFor(() => expect(screen.queryByTestId("rar-exam-phase-id")).toBeTruthy());
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-phase-id").options.length < 2) throw new Error("phase opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-phase-id"), { target: { value: "phase-456" } });
  await waitFor(() => expect(screen.queryByTestId("rar-phase-start")).toBeTruthy());
  fireEvent.change(screen.getByTestId("rar-phase-start"), { target: { value: "2026-11-15" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "valid reason here" } });
  fireEvent.click(screen.getByTestId("rar-submit"));
  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

// ─── before-state current dates rendered ─────────────────────────────────────

test("before-state current dates rendered from selected cycle row", async () => {
  const cycleWithDates = {
    ...MOCK_CYCLE,
    notification_date: "2026-07-01",
    exam_start: "2026-10-05",
  };
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [cycleWithDates] });
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "cycle_date_update" } });
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-cycle-id").options.length < 2) throw new Error("opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-cycle-id"), { target: { value: "cycle-123" } });

  await waitFor(() => expect(screen.queryByTestId("rar-notification-date-current")).toBeTruthy());
  expect(screen.getByTestId("rar-notification-date-current").textContent).toBe("2026-07-01");
  expect(screen.getByTestId("rar-exam-start-current").textContent).toBe("2026-10-05");
});

// ─── apply-action payload — phase_date_update (two-step flow) ────────────────

test("apply-action sends correct payload for phase_date_update via two-step flow", async () => {
  api.post.mockResolvedValueOnce({ ok: true });
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, exam_id: "exam-uuid-1" });
    }
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    if (url.includes("exam-phases")) return Promise.resolve({ items: [MOCK_PHASE] });
    return Promise.resolve({ items: [] });
  });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "phase_date_update" } });

  // Step 1: cycle
  await waitFor(() => {
    if (screen.getByTestId("rar-phase-cycle-id").options.length < 2) throw new Error("cycle opts");
  });
  fireEvent.change(screen.getByTestId("rar-phase-cycle-id"), { target: { value: "cycle-123" } });

  // Step 2: phase
  await waitFor(() => expect(screen.queryByTestId("rar-exam-phase-id")).toBeTruthy());
  await waitFor(() => {
    if (screen.getByTestId("rar-exam-phase-id").options.length < 2) throw new Error("phase opts");
  });
  fireEvent.change(screen.getByTestId("rar-exam-phase-id"), { target: { value: "phase-456" } });

  await waitFor(() => expect(screen.queryByTestId("rar-phase-start")).toBeTruthy());
  fireEvent.change(screen.getByTestId("rar-phase-start"), { target: { value: "2026-10-01" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "phase admit card date updated per official notice" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const body = api.post.mock.calls[0][1];
  expect(body.action_type).toBe("phase_date_update");
  expect(body.exam_phase_id).toBe("phase-456");
  expect(body.patch).toEqual({ phase_start: "2026-10-01" });
  expect(body.event_source_id).toBeUndefined();
});

// ─── apply-action payload — policy_update_create ─────────────────────────────

test("apply-action sends correct payload for policy_update_create (JSON path unchanged)", async () => {
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

// ─── apply-action payload — policy_update_edit ───────────────────────────────

test("apply-action sends correct payload for policy_update_edit", async () => {
  api.post.mockResolvedValueOnce({ ok: true });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "policy_update_edit" } });
  await screen.findByTestId("rar-policy-update-id");
  await waitFor(() => {
    if (screen.getByTestId("rar-policy-update-id").options.length < 2) throw new Error("opts");
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

// ─── provenance object value renders as JSON, not [object Object] ────────────

test("evidence_summary with object value renders pretty JSON not [object Object]", async () => {
  const reportWithObj = {
    ...MOCK_REPORT,
    exam_id: null,
    evidence_summary: { source: "scraper", confidence: 0.9 },
  };
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1")
      return Promise.resolve(reportWithObj);
    if (url.includes("exam-cycles")) return Promise.resolve({ items: [MOCK_CYCLE] });
    return Promise.resolve({ items: [] });
  });
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => expect(screen.queryByTestId("rar-provenance")).toBeTruthy());
  const provEl = screen.getByTestId("rar-provenance");
  expect(provEl.textContent).not.toContain("[object Object]");
  expect(provEl.textContent).toContain("scraper");
  expect(provEl.textContent).toContain("0.9");
});

// ─── 422/409 surfaced inline ──────────────────────────────────────────────────

test("backend 422 error surfaced inline with status code", async () => {
  api.post.mockRejectedValueOnce(
    Object.assign(new Error("validation failed — exam_cycle_id required"), { status: 422 }),
  );

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "policy_update_create" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "reason long enough for validation" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(screen.getByTestId("rar-error").textContent).toContain("422");
});

test("backend 409 error surfaced inline with status code", async () => {
  api.post.mockRejectedValueOnce(
    Object.assign(new Error("conflict: action already applied"), { status: 409 }),
  );

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "policy_update_create" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "reason long enough for validation" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
  expect(screen.getByTestId("rar-error").textContent).toContain("409");
});

// ─── useApiAction wiring — inline error on failure ───────────────────────────

test("shows inline error when api.post rejects (non-422)", async () => {
  api.post.mockRejectedValueOnce(new Error("Permission denied"));

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("apply-action-form"));

  fireEvent.change(screen.getByTestId("rar-action-type"), { target: { value: "policy_update_create" } });
  fireEvent.change(screen.getByTestId("rar-reason"), { target: { value: "reason long enough for validation" } });
  fireEvent.click(screen.getByTestId("rar-submit"));

  await waitFor(() => expect(screen.queryByTestId("rar-error")).toBeTruthy());
});

// ─── promote / reject panel ───────────────────────────────────────────────────

async function openDrawer() {
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => expect(screen.queryByTestId("promote-reject-panel")).toBeTruthy());
}

test("promote button is enabled when recruitment_id is null", async () => {
  await openDrawer();
  const btn = screen.getByTestId("promote-btn");
  expect(btn.disabled).toBe(false);
  expect(btn.textContent).toContain("Promote");
});

test("promote button is disabled when recruitment_id is set", async () => {
  api.get.mockImplementation((url) => {
    if (url === "/api/admin/verification-reports/rpt-1") {
      return Promise.resolve({ ...MOCK_REPORT, recruitment_id: "rec-999" });
    }
    return Promise.resolve({ items: [] });
  });

  await openDrawer();
  const btn = screen.getByTestId("promote-btn");
  expect(btn.disabled).toBe(true);
  expect(btn.textContent).toContain("Promoted");
  expect(screen.queryByTestId("already-promoted-note")).toBeTruthy();
});

test("promote sends POST to /promote endpoint and fires onSuccess", async () => {
  api.post.mockResolvedValueOnce({ ok: true, recruitment_id: "rec-new" });

  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("promote-btn"));

  fireEvent.click(screen.getByTestId("promote-btn"));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    "/api/admin/verification-reports/rpt-1/promote",
    {},
  ));
});

test("promote shows inline error when POST returns rejection", async () => {
  api.post.mockRejectedValueOnce(new Error("gate_blocker"));

  await openDrawer();
  fireEvent.click(screen.getByTestId("promote-btn"));

  await waitFor(() => expect(screen.queryByTestId("promote-error")).toBeTruthy());
});

test("non-admin role is denied the page entirely — promote/reject never reached", async () => {
  useAuth.mockReturnValue({
    user: { role: "viewer", permissions: ["exam_intelligence.cms"] },
  });
  render(<AdminVerificationReports />);
  const denied = await screen.findByTestId("vr-permission-denied");
  expect(denied).toBeTruthy();
  expect(screen.queryByTestId("promote-reject-panel")).toBeFalsy();
});

test("reject button opens reason form", async () => {
  await openDrawer();
  expect(screen.queryByTestId("reject-form")).toBeFalsy();
  fireEvent.click(screen.getByTestId("reject-open-btn"));
  expect(screen.queryByTestId("reject-form")).toBeTruthy();
});

test("reject shows client-side error when reason is fewer than 8 chars", async () => {
  await openDrawer();
  fireEvent.click(screen.getByTestId("reject-open-btn"));
  fireEvent.change(screen.getByTestId("reject-reason-input"), { target: { value: "short" } });
  fireEvent.click(screen.getByTestId("reject-submit-btn"));

  await waitFor(() => expect(screen.queryByTestId("reject-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

test("reject sends POST with reason when valid", async () => {
  api.post.mockResolvedValueOnce({ ok: true });

  await openDrawer();
  fireEvent.click(screen.getByTestId("reject-open-btn"));
  fireEvent.change(screen.getByTestId("reject-reason-input"), {
    target: { value: "Confirmed duplicate — exam already covered." },
  });
  fireEvent.click(screen.getByTestId("reject-submit-btn"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [url, body] = api.post.mock.calls[0];
  expect(url).toBe("/api/admin/verification-reports/rpt-1/reject");
  expect(body.reason).toBe("Confirmed duplicate — exam already covered.");
});

// ─── run-resolver panel ───────────────────────────────────────────────────────

test("run-resolver panel shown for admin", async () => {
  await openDrawer();
  expect(screen.queryByTestId("run-resolver-panel")).toBeTruthy();
});

test("run-resolver sends POST to /run-resolver", async () => {
  api.post.mockResolvedValueOnce({ ok: true, resolver_status: "resolved" });
  await openDrawer();
  fireEvent.click(screen.getByTestId("run-resolver-btn"));
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  expect(api.post.mock.calls[0][0]).toBe("/api/admin/verification-reports/rpt-1/run-resolver");
});

test("run-resolver shows cooldown message on 429-shaped error", async () => {
  api.post.mockRejectedValueOnce(Object.assign(new Error("Resolver cooldown active for this report; retry in 47s."), { status: 429 }));
  await openDrawer();
  fireEvent.click(screen.getByTestId("run-resolver-btn"));
  await waitFor(() => expect(screen.queryByTestId("resolver-cooldown-msg")).toBeTruthy());
  expect(screen.queryByTestId("run-resolver-btn").disabled).toBe(true);
});

test("non-admin role is denied the page — run-resolver never reached", async () => {
  useAuth.mockReturnValue({ user: { role: "viewer", permissions: ["exam_intelligence.cms"] } });
  render(<AdminVerificationReports />);
  const denied = await screen.findByTestId("vr-permission-denied");
  expect(denied).toBeTruthy();
  expect(screen.queryByTestId("run-resolver-panel")).toBeFalsy();
});

// ─── confirm-proof panel ──────────────────────────────────────────────────────

test("confirm-proof panel shown when report has suggested URLs", async () => {
  await openDrawer();
  expect(screen.queryByTestId("confirm-proof-panel")).toBeTruthy();
});

test("confirm-proof rejects off-list URL client-side", async () => {
  await openDrawer();
  fireEvent.click(screen.getByTestId("proof-submit-btn"));
  await waitFor(() => expect(screen.queryByTestId("proof-error")).toBeTruthy());
  expect(api.post).not.toHaveBeenCalled();
});

test("confirm-proof sends POST with chosen_url when valid", async () => {
  api.post.mockResolvedValueOnce({ ok: true });
  await openDrawer();
  fireEvent.change(screen.getByTestId("proof-url-select"), {
    target: { value: "https://upsc.gov.in/official" },
  });
  fireEvent.click(screen.getByTestId("proof-submit-btn"));
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [url, body] = api.post.mock.calls[0];
  expect(url).toBe("/api/admin/verification-reports/rpt-1/confirm-suggested-proof");
  expect(body.chosen_url).toBe("https://upsc.gov.in/official");
});

// ─── override-conflict panel ──────────────────────────────────────────────────

async function openDrawerAs(setupFn) {
  setupFn();
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => expect(screen.queryByTestId("override-conflict-panel")).toBeTruthy());
}

test("override-conflict panel hidden for admin without recruitments.manage", async () => {
  // withPerm() sets admin + exam_intelligence.cms but NOT recruitments.manage
  render(<AdminVerificationReports />);
  fireEvent.click(await screen.findByTestId("vr-open-rpt-1"));
  await waitFor(() => screen.queryByTestId("report-detail-card"));
  expect(screen.queryByTestId("override-conflict-panel")).toBeFalsy();
});

test("override-conflict panel shown for admin with recruitments.manage", async () => {
  await openDrawerAs(withAdminAndRecruitments);
  expect(screen.queryByTestId("override-conflict-panel")).toBeTruthy();
});

test("override-conflict panel shown for super_admin without recruitments.manage", async () => {
  await openDrawerAs(withSuperAdmin);
  expect(screen.queryByTestId("override-conflict-panel")).toBeTruthy();
});

test("override-conflict sends POST with correct payload", async () => {
  api.post.mockResolvedValueOnce({ ok: true });
  await openDrawerAs(withAdminAndRecruitments);

  fireEvent.click(screen.getByTestId("override-open-conf-1"));
  fireEvent.change(screen.getByTestId("override-chosen-value"), { target: { value: "2026-08-01" } });
  fireEvent.change(screen.getByTestId("override-reason"), { target: { value: "Official gazette confirms this date" } });
  fireEvent.click(screen.getByTestId("override-submit-btn"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [url, body] = api.post.mock.calls[0];
  expect(url).toBe("/api/admin/verification-reports/rpt-1/override-conflict");
  expect(body.conflict_id).toBe("conf-1");
  expect(body.chosen_value).toBe("2026-08-01");
  expect(body.override_scope).toBe("field");
  expect(body.reason).toBe("Official gazette confirms this date");
  expect(body.override_scope).not.toBe("report");
});

// ─── bulk multi-select + toolbar ─────────────────────────────────────────────

const MOCK_REPORT_2 = {
  id: "rpt-2",
  exam_id: null,
  lifecycle_status: "classified",
  criticality_tier: "tier_b",
  exam_family_key: "ssc-cgl",
  recommended_action: "request_admin_review",
  report_version: 1,
  created_at: "2026-06-02T10:00:00Z",
  suggested_official_urls: [],
  conflicts: [],
};

function renderWithTwo() {
  useApiCollection.mockReturnValue({
    items: [MOCK_REPORT, MOCK_REPORT_2],
    status: "live",
    refresh: jest.fn(),
  });
  render(<AdminVerificationReports />);
}

test("row checkboxes exist for each item", async () => {
  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  expect(screen.queryByTestId("vr-check-rpt-2")).toBeTruthy();
});

test("checking a row adds it to selection and shows bulk toolbar", async () => {
  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  expect(screen.queryByTestId("bulk-toolbar")).toBeTruthy();
});

test("select-all checks all rows", async () => {
  renderWithTwo();
  await screen.findByTestId("vr-select-all");
  fireEvent.click(screen.getByTestId("vr-select-all"));
  expect(screen.queryByTestId("bulk-toolbar")).toBeTruthy();
  expect(screen.getByTestId("vr-check-rpt-1").checked).toBe(true);
  expect(screen.getByTestId("vr-check-rpt-2").checked).toBe(true);
});

test("clear button removes selection and hides toolbar", async () => {
  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  await screen.findByTestId("bulk-toolbar");
  fireEvent.click(screen.getByTestId("bulk-clear-btn"));
  expect(screen.queryByTestId("bulk-toolbar")).toBeFalsy();
});

test("non-admin role is denied the page — bulk toolbar never reached", async () => {
  useAuth.mockReturnValue({ user: { role: "viewer", permissions: ["exam_intelligence.cms"] } });
  useApiCollection.mockReturnValue({ items: [MOCK_REPORT], status: "live", refresh: jest.fn() });
  render(<AdminVerificationReports />);
  const denied = await screen.findByTestId("vr-permission-denied");
  expect(denied).toBeTruthy();
  expect(screen.queryByTestId("bulk-toolbar")).toBeFalsy();
});

test("dry-run sends POST to bulk-dry-run and renders BulkActionPreview", async () => {
  const dryRunResp = {
    selected_ids: ["rpt-1"],
    action: "bulk_promote",
    dry_run: true,
    result: { eligible_count: 1, blocked_count: 0, blockers: [] },
  };
  api.post.mockResolvedValueOnce(dryRunResp);

  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  fireEvent.click(screen.getByTestId("bulk-dry-run-btn"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const [url, body] = api.post.mock.calls[0];
  expect(url).toBe("/api/admin/verification-reports/bulk-dry-run");
  expect(body.selected_ids).toEqual(["rpt-1"]);
  expect(body.action).toBe("bulk_promote");
  expect(body.dry_run).toBe(true);

  await waitFor(() => expect(screen.queryByTestId("bulk-action-preview")).toBeTruthy());
  expect(screen.getByTestId("bap-eligible").textContent).toBe("1");
  expect(screen.getByTestId("bap-blocked").textContent).toBe("0");
  expect(screen.getByTestId("bap-action").textContent).toBe("bulk_promote");
});

test("dry-run with bulk_reject action sends correct action value", async () => {
  api.post.mockResolvedValueOnce({
    selected_ids: ["rpt-1"],
    action: "bulk_reject",
    dry_run: true,
    result: { eligible_count: 1, blocked_count: 0, blockers: [] },
  });

  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  fireEvent.change(screen.getByTestId("bulk-action-select"), { target: { value: "bulk_reject" } });
  fireEvent.change(screen.getByTestId("bulk-reason-input"), {
    target: { value: "Confirmed duplicate — same exam already published." },
  });
  fireEvent.click(screen.getByTestId("bulk-dry-run-btn"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  expect(api.post.mock.calls[0][1].action).toBe("bulk_reject");
});

test("apply sends bulk-apply with selected_ids + action and clears selection on success", async () => {
  const refresh = jest.fn();
  useApiCollection.mockReturnValue({ items: [MOCK_REPORT, MOCK_REPORT_2], status: "live", refresh });

  const dryRunResp = {
    selected_ids: ["rpt-1"],
    action: "bulk_promote",
    dry_run: true,
    result: { eligible_count: 1, blocked_count: 0, blockers: [] },
  };
  api.post
    .mockResolvedValueOnce(dryRunResp)
    .mockResolvedValueOnce({ applied: 1 });

  render(<AdminVerificationReports />);
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  fireEvent.click(screen.getByTestId("bulk-dry-run-btn"));
  await screen.findByTestId("bap-apply-btn");

  fireEvent.click(screen.getByTestId("bap-apply-btn"));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));

  const [applyUrl, applyBody] = api.post.mock.calls[1];
  expect(applyUrl).toBe("/api/admin/verification-reports/bulk-apply");
  expect(applyBody.selected_ids).toEqual(["rpt-1"]);
  expect(applyBody.action).toBe("bulk_promote");
  expect(applyBody.dry_run).toBe(false);

  await waitFor(() => expect(screen.queryByTestId("bulk-toolbar")).toBeFalsy());
  expect(refresh).toHaveBeenCalledTimes(1);
});

test("bulk_reject shows reason textarea; bulk_promote does not", async () => {
  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  await screen.findByTestId("bulk-toolbar");

  expect(screen.queryByTestId("bulk-reason-input")).toBeFalsy();

  fireEvent.change(screen.getByTestId("bulk-action-select"), { target: { value: "bulk_reject" } });
  expect(screen.queryByTestId("bulk-reason-input")).toBeTruthy();

  fireEvent.change(screen.getByTestId("bulk-action-select"), { target: { value: "bulk_promote" } });
  expect(screen.queryByTestId("bulk-reason-input")).toBeFalsy();
});

test("bulk_reject dry-run button disabled until reason is >= 8 chars", async () => {
  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  fireEvent.change(screen.getByTestId("bulk-action-select"), { target: { value: "bulk_reject" } });

  const dryRunBtn = screen.getByTestId("bulk-dry-run-btn");
  expect(dryRunBtn.disabled).toBe(true);

  fireEvent.change(screen.getByTestId("bulk-reason-input"), { target: { value: "short!!" } });
  expect(dryRunBtn.disabled).toBe(true);

  fireEvent.change(screen.getByTestId("bulk-reason-input"), { target: { value: "valid reason here" } });
  expect(dryRunBtn.disabled).toBe(false);
});

test("bulk_reject dry-run includes reason in POST body", async () => {
  const REASON = "Confirmed duplicate — same exam already published by another source.";
  api.post.mockResolvedValueOnce({
    selected_ids: ["rpt-1"],
    action: "bulk_reject",
    dry_run: true,
    result: { eligible_count: 1, blocked_count: 0, blockers: [] },
  });

  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  fireEvent.change(screen.getByTestId("bulk-action-select"), { target: { value: "bulk_reject" } });
  fireEvent.change(screen.getByTestId("bulk-reason-input"), { target: { value: REASON } });
  fireEvent.click(screen.getByTestId("bulk-dry-run-btn"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const body = api.post.mock.calls[0][1];
  expect(body.action).toBe("bulk_reject");
  expect(body.reason).toBe(REASON);
});

test("bulk_reject apply includes reason in POST body", async () => {
  const REASON = "Confirmed duplicate — same exam already published by another source.";
  const dryRunResp = {
    selected_ids: ["rpt-1"],
    action: "bulk_reject",
    dry_run: true,
    result: { eligible_count: 1, blocked_count: 0, blockers: [] },
  };
  api.post
    .mockResolvedValueOnce(dryRunResp)
    .mockResolvedValueOnce({ applied: 1 });

  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  fireEvent.change(screen.getByTestId("bulk-action-select"), { target: { value: "bulk_reject" } });
  fireEvent.change(screen.getByTestId("bulk-reason-input"), { target: { value: REASON } });
  fireEvent.click(screen.getByTestId("bulk-dry-run-btn"));
  await screen.findByTestId("bap-apply-btn");

  fireEvent.click(screen.getByTestId("bap-apply-btn"));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));

  const applyBody = api.post.mock.calls[1][1];
  expect(applyBody.action).toBe("bulk_reject");
  expect(applyBody.dry_run).toBe(false);
  expect(applyBody.reason).toBe(REASON);
});

test("bulk_promote dry-run does NOT include reason in POST body", async () => {
  api.post.mockResolvedValueOnce({
    selected_ids: ["rpt-1"],
    action: "bulk_promote",
    dry_run: true,
    result: { eligible_count: 1, blocked_count: 0, blockers: [] },
  });

  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  fireEvent.click(screen.getByTestId("bulk-dry-run-btn"));

  await waitFor(() => expect(api.post).toHaveBeenCalled());
  const body = api.post.mock.calls[0][1];
  expect(body.action).toBe("bulk_promote");
  expect(body.reason).toBeUndefined();
});

test("clear button resets reason textarea", async () => {
  renderWithTwo();
  await screen.findByTestId("vr-check-rpt-1");
  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  fireEvent.change(screen.getByTestId("bulk-action-select"), { target: { value: "bulk_reject" } });
  fireEvent.change(screen.getByTestId("bulk-reason-input"), { target: { value: "some reason here" } });
  expect(screen.getByTestId("bulk-reason-input").value).toBe("some reason here");

  fireEvent.click(screen.getByTestId("bulk-clear-btn"));
  expect(screen.queryByTestId("bulk-toolbar")).toBeFalsy();

  fireEvent.click(screen.getByTestId("vr-check-rpt-1"));
  fireEvent.change(screen.getByTestId("bulk-action-select"), { target: { value: "bulk_reject" } });
  expect(screen.getByTestId("bulk-reason-input").value).toBe("");
});
