/**
 * AddPyqPaperModal — phase assignment (EI-CLEAN-02).
 *
 *  1.  Renders a cycle-scoped phase selector with an explicit exam-wide option
 *      and each phase labelled with its canonical kind.
 *  2.  Submitting with a phase selected sends the resolved exam_phase_id.
 *  3.  Submitting with exam-wide (default) sends exam_phase_id: null.
 *  4.  Fail-closed: if the selected phase disappears from the list, submit is
 *      blocked with an error and onboardPaper is never called.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  getApiBlockingFields: () => [],
}));

// The source step's shared provenance fields are irrelevant here — stub them.
jest.mock("../PyqProvenanceFields", () => ({
  __esModule: true,
  default: () => null,
}));

const AddPyqPaperModal = require("../AddPyqPaperModal").default;

const PHASES = [
  { id: "ph-prelims", exam_cycle_id: "cyc-A", phase_name: "Prelims", phase_slug: "prelims", phase_kind: "objective_written", status: "expected" },
  { id: "ph-mains", exam_cycle_id: "cyc-A", phase_name: "Mains", phase_slug: "mains", phase_kind: "descriptive_written", status: "expected" },
];

function renderModal(props = {}) {
  const onboardPaper = jest.fn().mockResolvedValue("new-paper-1");
  const onSuccess = jest.fn();
  const utils = render(
    <AddPyqPaperModal
      examId="exam-1"
      examName="UPSC CSE"
      cycleId="cyc-A"
      cycleLabel="2026"
      cycleYear={2026}
      phases={PHASES}
      pyqDocuments={[]}
      pyqSources={[]}
      onboardPaper={onboardPaper}
      uploadPyqDocument={jest.fn()}
      onCancel={jest.fn()}
      onSuccess={onSuccess}
      {...props}
    />,
  );
  return { onboardPaper, onSuccess, ...utils };
}

function fillRequired() {
  fireEvent.change(screen.getByTestId("add-pyq-year"), { target: { value: "2024" } });
  fireEvent.change(screen.getByTestId("add-pyq-reason"), { target: { value: "adding a real prelims paper" } });
}

test("renders exam-wide option plus each cycle phase with its kind", () => {
  renderModal();
  const select = screen.getByTestId("add-pyq-phase-select");
  const options = Array.from(select.querySelectorAll("option"));
  expect(options[0].value).toBe("");
  expect(options[0].textContent).toMatch(/exam-wide/i);
  const values = options.map(o => o.value);
  expect(values).toContain("ph-prelims");
  expect(values).toContain("ph-mains");
  expect(options.find(o => o.value === "ph-prelims").textContent).toContain("objective_written");
});

test("submitting with a phase selected sends resolved exam_phase_id", async () => {
  const { onboardPaper } = renderModal();
  fillRequired();
  fireEvent.change(screen.getByTestId("add-pyq-phase-select"), { target: { value: "ph-prelims" } });
  fireEvent.click(screen.getByTestId("add-pyq-submit"));
  await waitFor(() => expect(onboardPaper).toHaveBeenCalledTimes(1));
  expect(onboardPaper.mock.calls[0][0].exam_phase_id).toBe("ph-prelims");
});

test("submitting exam-wide (default) sends exam_phase_id null", async () => {
  const { onboardPaper } = renderModal();
  fillRequired();
  fireEvent.click(screen.getByTestId("add-pyq-submit"));
  await waitFor(() => expect(onboardPaper).toHaveBeenCalledTimes(1));
  expect(onboardPaper.mock.calls[0][0].exam_phase_id).toBeNull();
});

test("fails closed when the selected phase is no longer available", async () => {
  const { onboardPaper, rerender } = renderModal();
  fillRequired();
  fireEvent.change(screen.getByTestId("add-pyq-phase-select"), { target: { value: "ph-prelims" } });
  // The phase disappears from the cycle-scoped list (e.g. cancelled/reloaded).
  rerender(
    <AddPyqPaperModal
      examId="exam-1" examName="UPSC CSE" cycleId="cyc-A" cycleLabel="2026" cycleYear={2026}
      phases={[PHASES[1]]} pyqDocuments={[]} pyqSources={[]}
      onboardPaper={onboardPaper} uploadPyqDocument={jest.fn()} onCancel={jest.fn()} onSuccess={jest.fn()}
    />,
  );
  fireEvent.click(screen.getByTestId("add-pyq-submit"));
  await waitFor(() => expect(screen.getByTestId("add-pyq-error")).toBeTruthy());
  expect(onboardPaper).not.toHaveBeenCalled();
});
