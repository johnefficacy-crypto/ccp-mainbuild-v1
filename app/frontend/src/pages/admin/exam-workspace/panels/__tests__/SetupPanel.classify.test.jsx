/**
 * SetupPanel — canonical phase-kind classification (EI-CLEAN-01).
 *
 *  1.  action=classify-phases opens the worklist listing only UNCLASSIFIED,
 *      cycle-bound, non-cancelled phases (null/'other' kinds; classified hidden).
 *  2.  Selecting a kind + Classify PATCHes /exam-phases/{id} with {phase_kind}
 *      and refreshes both the workspace context and readiness read-model.
 *  3.  The add-phase form exposes the phase-kind select and includes phase_kind
 *      in the create payload.
 *  4.  With no unclassified phases and no action, the worklist is not shown.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

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

jest.mock("../../../../../shared/ui/DateField", () => ({
  __esModule: true,
  default: function DateField({ label, onChange, value, id }) {
    return (
      <div>
        <label htmlFor={id}>{label}</label>
        <input id={id} data-testid={id} value={value || ""} onChange={e => onChange(e.target.value || null)} />
      </div>
    );
  },
}));

const { api } = require("../../../../../lib/api");
const { useExamWorkspace } = require("../../ExamWorkspaceContext");
const SetupPanel = require("../SetupPanel").default;

const BASE_EXAM = { id: "exam-1", name: "UPSC CSE", slug: "upsc-cse" };
const CYCLES = [{ id: "cyc-A", status: "active", cycle_name: "2026", year: 2026 }];

const UNCLASSIFIED_PHASE = {
  id: "ph-prelims", exam_id: "exam-1", exam_cycle_id: "cyc-A",
  phase_name: "Prelims", phase_slug: "prelims", phase_order: 1,
  status: "expected", phase_kind: null, metadata: {},
};
const CLASSIFIED_PHASE = {
  id: "ph-mains", exam_id: "exam-1", exam_cycle_id: "cyc-A",
  phase_name: "Mains", phase_slug: "mains", phase_order: 2,
  status: "expected", phase_kind: "descriptive_written", metadata: {},
};

const REFETCH = jest.fn();
const REFETCH_READINESS = jest.fn();

beforeEach(() => {
  api.post.mockReset();
  api.patch.mockReset();
  api.post.mockResolvedValue({ ok: true, row: { id: "new-phase-1" } });
  api.patch.mockResolvedValue({ ok: true, row: { id: "ph-prelims", phase_kind: "objective_written" } });
  REFETCH.mockReset();
  REFETCH_READINESS.mockReset();
});

function setup({ action = null, phases = [UNCLASSIFIED_PHASE, CLASSIFIED_PHASE] } = {}) {
  useExamWorkspace.mockReturnValue({
    exam: BASE_EXAM,
    cycles: CYCLES,
    phases,
    refetch: REFETCH,
    refetchReadiness: REFETCH_READINESS,
  });
  render(<SetupPanel action={action} />);
}

test("classify worklist lists only unclassified cycle-bound phases", () => {
  setup({ action: "classify-phases" });
  expect(screen.getByTestId("phase-classify-worklist")).toBeTruthy();
  expect(screen.getByTestId(`classify-row-${UNCLASSIFIED_PHASE.id}`)).toBeTruthy();
  // Classified phase must NOT be in the worklist
  expect(screen.queryByTestId(`classify-row-${CLASSIFIED_PHASE.id}`)).toBeNull();
});

test("'other' and cancelled phases are treated as unclassified / excluded", () => {
  const otherPhase = { ...UNCLASSIFIED_PHASE, id: "ph-other", phase_kind: "other" };
  const cancelled = { ...UNCLASSIFIED_PHASE, id: "ph-cancel", status: "cancelled" };
  const templateNoCycle = { ...UNCLASSIFIED_PHASE, id: "ph-tmpl", exam_cycle_id: null };
  setup({ action: "classify-phases", phases: [otherPhase, cancelled, templateNoCycle] });
  // 'other' counts as unclassified → listed
  expect(screen.getByTestId("classify-row-ph-other")).toBeTruthy();
  // cancelled + template (no cycle) do not block activation → not listed
  expect(screen.queryByTestId("classify-row-ph-cancel")).toBeNull();
  expect(screen.queryByTestId("classify-row-ph-tmpl")).toBeNull();
});

test("classify PATCHes phase_kind and refreshes context + readiness", async () => {
  setup({ action: "classify-phases" });
  fireEvent.change(screen.getByTestId(`classify-kind-${UNCLASSIFIED_PHASE.id}`), {
    target: { value: "objective_written" },
  });
  fireEvent.click(screen.getByTestId(`classify-save-${UNCLASSIFIED_PHASE.id}`));
  await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
  const [url, body] = api.patch.mock.calls[0];
  expect(url).toBe(`/api/admin/exam-intelligence-cms/exam-phases/${UNCLASSIFIED_PHASE.id}`);
  expect(body.payload).toEqual({ phase_kind: "objective_written" });
  expect(REFETCH).toHaveBeenCalled();
  expect(REFETCH_READINESS).toHaveBeenCalled();
});

test("add-phase form exposes phase-kind select and includes it in create payload", async () => {
  setup();
  fireEvent.click(screen.getByText("+ Add phase"));
  fireEvent.change(screen.getByTestId("phase-form-name"), { target: { value: "Interview" } });
  fireEvent.change(screen.getByTestId("phase-form-kind"), { target: { value: "interview" } });
  fireEvent.click(screen.getByTestId("add-phase-submit"));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  const [, body] = api.post.mock.calls[0];
  expect(body.payload.phase_kind).toBe("interview");
});

test("no worklist when all phases classified and no classify action", () => {
  setup({ phases: [CLASSIFIED_PHASE] });
  expect(screen.queryByTestId("phase-classify-worklist")).toBeNull();
});
