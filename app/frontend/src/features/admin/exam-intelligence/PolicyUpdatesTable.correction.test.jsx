/**
 * F5 regression — policy affects_* flags correction-request affordance.
 *
 * The affects_* flags stay immutable (no direct edit control). This covers
 * the "Request correction" control: it captures disputed flag(s) + a reason
 * (>= 8 chars) and hands them to the parent-owned onRequestCorrection
 * mutation without ever calling any flag-editing API itself.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

const PolicyUpdatesTable = require("./PolicyUpdatesTable").default;

const ROWS = [
  {
    id: "pu-1",
    exam: "SSC CGL",
    update_type: "vacancy_change",
    title: "Vacancies revised",
    source_type: "official",
    status: "verified",
    affects_plan: true,
    affects_vacancy: true,
  },
];

test("F5: 'Request correction' is absent when onRequestCorrection is not supplied", () => {
  render(<PolicyUpdatesTable items={ROWS} />);
  expect(screen.queryByTestId("policy-correction-open-pu-1")).toBeNull();
  // Falls back to the "contact an admin" copy.
  expect(screen.getByTestId("affects-immutability-notice").textContent).toMatch(/contact an admin/i);
});

test("F5: 'Request correction' opens a flag-picker + reason form", () => {
  render(<PolicyUpdatesTable items={ROWS} onRequestCorrection={jest.fn()} />);
  expect(screen.getByTestId("affects-immutability-notice").textContent).toMatch(/Request correction/i);
  fireEvent.click(screen.getByTestId("policy-correction-open-pu-1"));
  expect(screen.getByTestId("policy-correction-form-pu-1")).toBeTruthy();
  expect(screen.getByTestId("policy-correction-flag-pu-1-affects_plan")).toBeTruthy();
  expect(screen.getByTestId("policy-correction-flag-pu-1-affects_vacancy")).toBeTruthy();
});

test("F5: submit is disabled until a flag is checked and reason is >= 8 chars", () => {
  render(<PolicyUpdatesTable items={ROWS} onRequestCorrection={jest.fn()} />);
  fireEvent.click(screen.getByTestId("policy-correction-open-pu-1"));
  const submit = screen.getByTestId("policy-correction-submit-pu-1");
  expect(submit.disabled).toBe(true);

  fireEvent.click(screen.getByTestId("policy-correction-flag-pu-1-affects_vacancy"));
  expect(submit.disabled).toBe(true); // still no reason

  fireEvent.change(screen.getByTestId("policy-correction-reason-pu-1"), { target: { value: "short" } });
  expect(submit.disabled).toBe(true); // reason < 8 chars

  fireEvent.change(screen.getByTestId("policy-correction-reason-pu-1"), {
    target: { value: "vacancy count looks stale" },
  });
  expect(submit.disabled).toBe(false);
});

test("F5: submit calls onRequestCorrection with the row, disputed flags, and trimmed reason", () => {
  const onRequestCorrection = jest.fn();
  render(<PolicyUpdatesTable items={ROWS} onRequestCorrection={onRequestCorrection} />);
  fireEvent.click(screen.getByTestId("policy-correction-open-pu-1"));
  fireEvent.click(screen.getByTestId("policy-correction-flag-pu-1-affects_plan"));
  fireEvent.click(screen.getByTestId("policy-correction-flag-pu-1-affects_vacancy"));
  fireEvent.change(screen.getByTestId("policy-correction-reason-pu-1"), {
    target: { value: "  both flags look wrong for this cycle  " },
  });
  fireEvent.click(screen.getByTestId("policy-correction-submit-pu-1"));

  expect(onRequestCorrection).toHaveBeenCalledTimes(1);
  const [row, payload] = onRequestCorrection.mock.calls[0];
  expect(row.id).toBe("pu-1");
  expect(payload.disputedFlags.sort()).toEqual(["affects_plan", "affects_vacancy"]);
  expect(payload.reason).toBe("both flags look wrong for this cycle");
});

test("F5: submit never calls any review/edit action directly — only the supplied callback", () => {
  const onReview = jest.fn();
  const onRequestCorrection = jest.fn();
  render(<PolicyUpdatesTable items={ROWS} onReview={onReview} onRequestCorrection={onRequestCorrection} />);
  fireEvent.click(screen.getByTestId("policy-correction-open-pu-1"));
  fireEvent.click(screen.getByTestId("policy-correction-flag-pu-1-affects_plan"));
  fireEvent.change(screen.getByTestId("policy-correction-reason-pu-1"), {
    target: { value: "disputing this flag" },
  });
  fireEvent.click(screen.getByTestId("policy-correction-submit-pu-1"));
  expect(onRequestCorrection).toHaveBeenCalledTimes(1);
  expect(onReview).not.toHaveBeenCalled();
});

test("F5: Cancel closes the form without calling onRequestCorrection", () => {
  const onRequestCorrection = jest.fn();
  render(<PolicyUpdatesTable items={ROWS} onRequestCorrection={onRequestCorrection} />);
  fireEvent.click(screen.getByTestId("policy-correction-open-pu-1"));
  fireEvent.click(screen.getByTestId("policy-correction-flag-pu-1-affects_plan"));
  fireEvent.click(screen.getByTestId("policy-correction-cancel-pu-1"));
  expect(screen.queryByTestId("policy-correction-form-pu-1")).toBeNull();
  expect(onRequestCorrection).not.toHaveBeenCalled();
});

test("F5: busy state disables submit and shows a busy indicator", () => {
  render(
    <PolicyUpdatesTable
      items={ROWS}
      onRequestCorrection={jest.fn()}
      correctionBusyRowId="pu-1"
    />,
  );
  fireEvent.click(screen.getByTestId("policy-correction-open-pu-1"));
  fireEvent.click(screen.getByTestId("policy-correction-flag-pu-1-affects_plan"));
  fireEvent.change(screen.getByTestId("policy-correction-reason-pu-1"), {
    target: { value: "disputing this flag" },
  });
  expect(screen.getByTestId("policy-correction-submit-pu-1").disabled).toBe(true);
  expect(screen.getByTestId("policy-correction-submit-pu-1").textContent).toBe("…");
});
