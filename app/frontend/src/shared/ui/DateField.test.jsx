import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import DateField from "./DateField";

test("typing/selecting an ISO date emits it verbatim", () => {
  const onChange = jest.fn();
  render(<DateField value={null} onChange={onChange} label="Date" />);
  fireEvent.change(screen.getByLabelText("Date"), {
    target: { value: "2026-03-12" },
  });
  expect(onChange).toHaveBeenCalledWith("2026-03-12");
});

test("clearing the input emits null", () => {
  const onChange = jest.fn();
  render(<DateField value="2026-03-10" onChange={onChange} label="Date" />);
  fireEvent.change(screen.getByLabelText("Date"), { target: { value: "" } });
  expect(onChange).toHaveBeenCalledWith(null);
});

test("minDate/maxDate are applied to the native input and reject out-of-range values", () => {
  const onChange = jest.fn();
  render(
    <DateField
      value="2026-03-15"
      onChange={onChange}
      minDate="2026-03-10"
      maxDate="2026-03-20"
      label="Date"
    />,
  );
  const input = screen.getByLabelText("Date");
  expect(input.min).toBe("2026-03-10");
  expect(input.max).toBe("2026-03-20");

  fireEvent.change(input, { target: { value: "2026-03-05" } });
  expect(onChange).not.toHaveBeenCalled();

  fireEvent.change(input, { target: { value: "2026-03-18" } });
  expect(onChange).toHaveBeenCalledWith("2026-03-18");
});

test("date round-trips through the value prop verbatim, no timezone shift", () => {
  const onChange = jest.fn();
  render(<DateField value="2026-03-12" onChange={onChange} label="Date" />);
  expect(screen.getByLabelText("Date").value).toBe("2026-03-12");
});

test("disabled prevents changes", () => {
  const onChange = jest.fn();
  render(<DateField value={null} onChange={onChange} label="Date" disabled />);
  expect(screen.getByLabelText("Date").disabled).toBe(true);
});

test("required marks the field and renders the required indicator", () => {
  render(<DateField value={null} onChange={jest.fn()} label="Date" required />);
  expect(screen.getByLabelText(/^Date/).required).toBe(true);
  expect(screen.getByText("*")).toBeInTheDocument();
});

test("error text is associated via aria-describedby and rendered", () => {
  render(<DateField value={null} onChange={jest.fn()} label="Date" error="Required field" />);
  const input = screen.getByLabelText("Date");
  expect(input.getAttribute("aria-invalid")).toBe("true");
  expect(screen.getByText("Required field")).toBeInTheDocument();
  expect(input.getAttribute("aria-describedby")).toContain(input.id + "-error");
});

test("without a label, the input gets an aria-label of Date", () => {
  render(<DateField value={null} onChange={jest.fn()} />);
  expect(screen.getByLabelText("Date")).toBeInTheDocument();
});
