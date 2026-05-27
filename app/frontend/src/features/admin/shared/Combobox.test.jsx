import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import Combobox from "./Combobox";

const OPTIONS = [
  { id: "a1", label: "SSC CGL", secondary: "ssc-cgl" },
  { id: "b2", label: "IBPS PO", secondary: "ibps-po" },
];

test("renders options on focus and filters by query", () => {
  const onChange = jest.fn();
  render(<Combobox options={OPTIONS} value="" onChange={onChange} testId="cb" />);

  const input = screen.getByTestId("cb");
  fireEvent.focus(input);

  // Both options visible before any query.
  expect(screen.getByTestId("cb-option-a1")).toBeTruthy();
  expect(screen.getByTestId("cb-option-b2")).toBeTruthy();

  // Typing filters down to the matching option only.
  fireEvent.change(input, { target: { value: "ibps" } });
  expect(screen.queryByTestId("cb-option-a1")).toBeNull();
  expect(screen.getByTestId("cb-option-b2")).toBeTruthy();
});

test("selecting an option emits the id, not the label", () => {
  const onChange = jest.fn();
  render(<Combobox options={OPTIONS} value="" onChange={onChange} testId="cb" />);

  fireEvent.focus(screen.getByTestId("cb"));
  // mouseDown beats the input blur, mirroring real selection.
  fireEvent.mouseDown(screen.getByTestId("cb-option-b2"));

  expect(onChange).toHaveBeenCalledWith("b2");
});

test("shows the human-readable label + a copy button for the current value", () => {
  const onChange = jest.fn();
  render(<Combobox options={OPTIONS} value="a1" onChange={onChange} testId="cb" />);

  const selected = screen.getByTestId("cb-selected");
  expect(selected.textContent).toContain("SSC CGL");
  expect(screen.getByTestId("cb-copy")).toBeTruthy();

  // Clear resets the selection to empty.
  fireEvent.click(screen.getByTestId("cb-clear"));
  expect(onChange).toHaveBeenCalledWith("");
});
