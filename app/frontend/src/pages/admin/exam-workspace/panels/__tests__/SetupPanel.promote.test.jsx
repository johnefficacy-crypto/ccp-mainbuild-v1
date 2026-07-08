/**
 * SetupPanel — promote-template-to-cycle action (PR4b).
 *
 * Tests the "Create cycle-bound copy" operator flow:
 *  1.  Template phases (exam_cycle_id: null) render as promotable.
 *  2.  Cycle-bound phases do NOT appear as promotable templates.
 *  3.  Submit button disabled until all required fields are valid.
 *  4.  Client blocks reversed date range before API call.
 *  5.  Happy path posts exact payload, calls refetch().
 *  6.  409 collision shows operator error with existing phase id.
 *  7.  500 audit_write_failed shows warning with phase_id.
 *  8.  audit_write_failed does NOT auto-retry / does NOT expose a retry action.
 *  9.  Status control is enum picker with backend-supported values only.
 * 10.  Reason validation rejects < 8 chars and > 500 chars client-side.
 */
import React from "react";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
}));

jest.mock("../../ExamWorkspaceContext", () => ({
  __esModule: true,
  useExamWorkspace: jest.fn(),
}));

jest.mock("../../../../../lib/hooks/useApiAction", () => ({
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

// DateField: minimal stub so phase-start/end inputs are testable without
// the real calendar widget.
jest.mock("../../../../../shared/ui/DateField", () => ({
  __esModule: true,
  default: function DateField({ label, onChange, value, id }) {
    return (
      <div>
        <label htmlFor={id}>{label}</label>
        <input
          id={id}
          data-testid={id}
          value={value || ""}
          onChange={e => onChange(e.target.value || null)}
        />
      </div>
    );
  },
}));

const { api } = require("../../../../../lib/api");
const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const SetupPanel = require("../SetupPanel").default;

const BASE_EXAM = { id: "exam-1", name: "UPSC CSE", slug: "upsc-cse" };
const REFETCH = jest.fn();

const CYCLES = [
  { id: "cyc-A", status: "active", cycle_name: "2026 Cycle", year: 2026 },
];

const TEMPLATE_PHASE = {
  id: "tmpl-prelims",
  exam_id: "exam-1",
  exam_cycle_id: null,          // template — no cycle binding
  phase_name: "Prelims",
  phase_slug: "prelims",
  phase_order: 1,
  status: "active",
  metadata: {},
};

const CYCLE_BOUND_PHASE = {
  id: "bound-mains",
  exam_id: "exam-1",
  exam_cycle_id: "cyc-A",       // cycle-bound — not a template
  phase_name: "Mains",
  phase_slug: "mains",
  phase_order: 2,
  status: "expected",
  metadata: {},
};

beforeEach(() => {
  api.post.mockReset();
  api.patch.mockReset();
  api.get.mockReset();
  api.post.mockResolvedValue({ ok: true, row: { id: "new-phase-1" } });
  REFETCH.mockReset();
});

function setup(overrides = {}) {
  useExamWorkspace.mockReturnValue({
    exam: BASE_EXAM,
    cycles: CYCLES,
    phases: [TEMPLATE_PHASE, CYCLE_BOUND_PHASE],
    refetch: REFETCH,
    ...overrides,
  });
  render(<SetupPanel />);
}

function openPromoteForm() {
  fireEvent.click(screen.getByTestId("promote-template-btn"));
}

// ── 1. Template phases render as promotable ───────────────────────────────────

test("renders template phases (exam_cycle_id null) as promotable", () => {
  setup();
  // The template-phase-card is visible
  expect(screen.getByTestId("promote-template-card")).toBeTruthy();
  // The template phase appears in the card
  expect(screen.getByTestId(`template-phase-${TEMPLATE_PHASE.id}`)).toBeTruthy();
  expect(screen.getAllByText("Prelims").length).toBeGreaterThan(0);
});

// ── 2. Cycle-bound phases do NOT appear as promotable templates ───────────────

test("does not show cycle-bound phases as promotable templates", () => {
  setup();
  // cycle-bound phase must NOT have a template-phase-* testid in the card
  expect(screen.queryByTestId(`template-phase-${CYCLE_BOUND_PHASE.id}`)).toBeNull();

  // Open the form and check the template picker options
  openPromoteForm();
  const picker = screen.getByTestId("pt-template-picker");
  const options = Array.from(picker.querySelectorAll("option")).map(o => o.value);
  expect(options).toContain(TEMPLATE_PHASE.id);
  expect(options).not.toContain(CYCLE_BOUND_PHASE.id);
});

// ── 3. Submit disabled until all required fields present ─────────────────────

test("submit disabled until template, cycle, phase_start, status, and valid reason present", () => {
  setup();
  openPromoteForm();

  const submit = screen.getByTestId("pt-submit");
  // Initially disabled (template pre-selected but no start/reason)
  expect(submit.disabled).toBe(true);

  // Set phase_start
  fireEvent.change(screen.getByTestId("pt-phase-start"), { target: { value: "2026-06-01" } });
  expect(submit.disabled).toBe(true); // still no reason

  // Short reason (< 8 chars) — still disabled
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: "short" } });
  expect(submit.disabled).toBe(true);

  // Valid reason (≥ 8 chars)
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: "Attaching prelims to 2026" } });
  expect(submit.disabled).toBe(false);
});

// ── 4. Client blocks reversed date range before API call ─────────────────────

test("client blocks phase_end < phase_start and does not call API", async () => {
  setup();
  openPromoteForm();

  fireEvent.change(screen.getByTestId("pt-phase-start"), { target: { value: "2026-09-01" } });
  fireEvent.change(screen.getByTestId("pt-phase-end"), { target: { value: "2026-08-01" } });
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: "Attaching prelims to 2026" } });

  // Date error visible
  expect(screen.getByTestId("pt-date-error")).toBeTruthy();

  // Submit is disabled; clicking it does nothing
  fireEvent.click(screen.getByTestId("pt-submit"));
  await waitFor(() => expect(api.post).not.toHaveBeenCalled());
});

// ── 5. Happy path posts exact payload, calls refetch() ───────────────────────

test("happy path posts exact payload and calls refetch()", async () => {
  setup();
  openPromoteForm();

  // Select template
  fireEvent.change(screen.getByTestId("pt-template-picker"), { target: { value: TEMPLATE_PHASE.id } });
  // Select cycle
  fireEvent.change(screen.getByTestId("pt-cycle-picker"), { target: { value: "cyc-A" } });
  // Dates
  fireEvent.change(screen.getByTestId("pt-phase-start"), { target: { value: "2026-06-01" } });
  fireEvent.change(screen.getByTestId("pt-phase-end"), { target: { value: "2026-07-31" } });
  // Status (leave default "expected")
  // Reason
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: "Attaching prelims to 2026 cycle" } });

  fireEvent.click(screen.getByTestId("pt-submit"));

  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));

  const [url, body] = api.post.mock.calls[0];
  expect(url).toBe("/api/admin/exam-intelligence-cms/exam-phases/promote-template");
  expect(body.template_phase_id).toBe(TEMPLATE_PHASE.id);
  expect(body.target_cycle_id).toBe("cyc-A");
  expect(body.phase_start).toBe("2026-06-01");
  expect(body.phase_end).toBe("2026-07-31");
  expect(body.status).toBe("expected");
  expect(body.reason).toBe("Attaching prelims to 2026 cycle");

  await waitFor(() => expect(REFETCH).toHaveBeenCalled());
});

// ── 6. 409 collision → operator error with existing phase id ─────────────────

test("409 collision shows operator error with humanized existing phase id (no raw UUID)", async () => {
  const rawId = "3f9a2c1e-7b84-4d21-9e6f-1a2b3c4d5e6f";
  const err = Object.assign(new Error("conflict"), {
    status: 409,
    detail: { code: "cycle_phase_already_exists", existing_phase_id: rawId },
    code: "cycle_phase_already_exists",
  });
  api.post.mockRejectedValueOnce(err);

  setup();
  openPromoteForm();
  fireEvent.change(screen.getByTestId("pt-phase-start"), { target: { value: "2026-06-01" } });
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: "Attaching prelims to 2026 cycle" } });
  fireEvent.click(screen.getByTestId("pt-submit"));

  await waitFor(() => expect(screen.getByTestId("pt-error-collision")).toBeTruthy());
  const errEl = screen.getByTestId("pt-error-collision");
  expect(errEl.textContent).toMatch(/already has a phase/i);
  // I2: the collision path must humanize the id — never render the raw UUID.
  expect(errEl.textContent).not.toContain(rawId);
  expect(screen.getByTestId("pt-error-existing-id").textContent).toBe("3f9a2c1e…");
});

// ── 7. 500 audit_write_failed shows warning with phase_id ────────────────────

test("500 audit_write_failed displays visible warning including phase_id", async () => {
  const err = Object.assign(new Error("audit failed"), {
    status: 500,
    detail: { code: "audit_write_failed", phase_id: "created-phase-abc" },
    code: "audit_write_failed",
  });
  api.post.mockRejectedValueOnce(err);

  setup();
  openPromoteForm();
  fireEvent.change(screen.getByTestId("pt-phase-start"), { target: { value: "2026-06-01" } });
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: "Attaching prelims to 2026 cycle" } });
  fireEvent.click(screen.getByTestId("pt-submit"));

  await waitFor(() => expect(screen.getByTestId("pt-error-audit-failed")).toBeTruthy());
  const errEl = screen.getByTestId("pt-error-audit-failed");
  expect(errEl.textContent).toMatch(/phase was created/i);
  expect(errEl.textContent).toMatch(/do not re-promote/i);
  // I2: raw id must not leak verbatim — operatorChrome.humanizeToken humanizes
  // non-UUID tokens (capitalizes first letter); UUID-shaped ids are truncated
  // to "${first8}…" instead (see ReviewQueueTable's I1 regression test).
  expect(screen.getByTestId("pt-error-phase-id").textContent).toBe("Created-phase-abc");
  expect(screen.getByTestId("pt-error-phase-id").textContent).not.toBe("created-phase-abc");
});

// ── 8. audit_write_failed does NOT auto-retry / no retry button ───────────────

test("audit_write_failed does not auto-retry and has no retry action for re-promotion", async () => {
  const err = Object.assign(new Error("audit failed"), {
    status: 500,
    detail: { code: "audit_write_failed", phase_id: "created-phase-abc" },
    code: "audit_write_failed",
  });
  api.post.mockRejectedValueOnce(err);

  setup();
  openPromoteForm();
  fireEvent.change(screen.getByTestId("pt-phase-start"), { target: { value: "2026-06-01" } });
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: "Attaching prelims to 2026 cycle" } });
  fireEvent.click(screen.getByTestId("pt-submit"));

  await waitFor(() => expect(screen.getByTestId("pt-error-audit-failed")).toBeTruthy());

  // API was called exactly once — no auto-retry
  expect(api.post).toHaveBeenCalledTimes(1);

  // There must be no button in the error element that would re-submit the promotion
  const errEl = screen.getByTestId("pt-error-audit-failed");
  expect(errEl.querySelectorAll("button")).toHaveLength(0);
});

// ── 9. Status control is enum picker with backend-supported values only ───────

test("status control is a select with only backend-supported enum values", () => {
  setup();
  openPromoteForm();

  const picker = screen.getByTestId("pt-status-picker");
  expect(picker.tagName).toBe("SELECT");

  const optionValues = Array.from(picker.querySelectorAll("option")).map(o => o.value);
  // Must contain all backend statuses
  ["expected", "active", "completed", "cancelled"].forEach(s => {
    expect(optionValues).toContain(s);
  });
  // Must NOT contain values outside backend contract
  expect(optionValues).not.toContain("verified");
  expect(optionValues).not.toContain("open");
  expect(optionValues).not.toContain("locked");
});

// ── 10. Reason validation rejects < 8 chars and > 500 chars ─────────────────

test("submit disabled and error shown for reason < 8 chars", () => {
  setup();
  openPromoteForm();
  fireEvent.change(screen.getByTestId("pt-phase-start"), { target: { value: "2026-06-01" } });
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: "short" } });

  expect(screen.getByTestId("pt-submit").disabled).toBe(true);
  expect(screen.getByTestId("pt-reason-error").textContent).toMatch(/at least 8/i);
});

test("submit disabled and error shown for reason > 500 chars", () => {
  setup();
  openPromoteForm();
  fireEvent.change(screen.getByTestId("pt-phase-start"), { target: { value: "2026-06-01" } });
  const longReason = "x".repeat(501);
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: longReason } });

  expect(screen.getByTestId("pt-submit").disabled).toBe(true);
  expect(screen.getByTestId("pt-reason-error").textContent).toMatch(/500 char/i);
});

// ── A. cycle-scoped / no-template phases → guidance visible ──────────────────

test("A: no template phases → guidance text visible, card not silently absent", () => {
  useExamWorkspace.mockReturnValue({
    exam: BASE_EXAM,
    cycles: CYCLES,
    phases: [CYCLE_BOUND_PHASE],
    refetch: REFETCH,
  });
  render(<SetupPanel />);

  expect(screen.getByTestId("promote-template-card")).toBeTruthy();
  expect(screen.getByTestId("promote-template-empty")).toBeTruthy();
  expect(screen.getByText(/no promotable templates here/i)).toBeTruthy();
  expect(screen.getByText(/exam-level workspace/i)).toBeTruthy();
  expect(screen.queryByTestId("promote-template-btn")).toBeNull();
});

// ── B. happy path → success message visible after form closes ────────────────

test("B: happy path success message is visible after form closes", async () => {
  setup();
  openPromoteForm();

  fireEvent.change(screen.getByTestId("pt-template-picker"), { target: { value: TEMPLATE_PHASE.id } });
  fireEvent.change(screen.getByTestId("pt-cycle-picker"), { target: { value: "cyc-A" } });
  fireEvent.change(screen.getByTestId("pt-phase-start"), { target: { value: "2026-06-01" } });
  fireEvent.change(screen.getByTestId("pt-reason"), { target: { value: "Attaching prelims to 2026 cycle" } });

  fireEvent.click(screen.getByTestId("pt-submit"));

  await waitFor(() => expect(REFETCH).toHaveBeenCalled());

  expect(screen.queryByTestId("pt-submit")).toBeNull();
  expect(screen.getByTestId("pt-success")).toBeTruthy();
  expect(screen.getByTestId("pt-success").textContent).toMatch(/cycle-bound copy created/i);
});
