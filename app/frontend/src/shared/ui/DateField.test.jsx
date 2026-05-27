import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import DateField from "./DateField";

function dayButton(container, n) {
  return Array.from(container.querySelectorAll("button")).find(
    (b) => b.textContent.trim() === String(n),
  );
}

test("typing dd-mm-yyyy emits the ISO date", () => {
  const onChange = jest.fn();
  render(<DateField value={null} onChange={onChange} />);
  fireEvent.change(screen.getByPlaceholderText("dd-mm-yyyy"), {
    target: { value: "12-03-2026" },
  });
  expect(onChange).toHaveBeenCalledWith("2026-03-12");
});

test("typing an invalid date leaves the value unchanged", () => {
  const onChange = jest.fn();
  render(<DateField value={null} onChange={onChange} />);
  fireEvent.change(screen.getByPlaceholderText("dd-mm-yyyy"), {
    target: { value: "32-13-2026" },
  });
  expect(onChange).not.toHaveBeenCalled();
});

test("picking a day from the calendar emits ISO", () => {
  const onChange = jest.fn();
  const { container } = render(<DateField value="2026-03-10" onChange={onChange} />);
  fireEvent.click(screen.getByPlaceholderText("dd-mm-yyyy"));
  fireEvent.click(dayButton(container, 15));
  expect(onChange).toHaveBeenCalledWith("2026-03-15");
});

test("clear button emits null", () => {
  const onChange = jest.fn();
  render(<DateField value="2026-03-10" onChange={onChange} />);
  fireEvent.click(screen.getByPlaceholderText("dd-mm-yyyy"));
  fireEvent.click(screen.getByText("Clear"));
  expect(onChange).toHaveBeenCalledWith(null);
});

test("minDate/maxDate disables out-of-range days and rejects typed out-of-range values", () => {
  const onChange = jest.fn();
  const { container } = render(
    <DateField value="2026-03-15" onChange={onChange} minDate="2026-03-10" maxDate="2026-03-20" />,
  );
  fireEvent.click(screen.getByPlaceholderText("dd-mm-yyyy"));
  // In-range day is selectable; out-of-range days are disabled in the picker.
  expect(dayButton(container, 5).disabled).toBe(true);
  expect(dayButton(container, 25).disabled).toBe(true);
  expect(dayButton(container, 15).disabled).toBe(false);

  // Typed out-of-range value is silently rejected.
  fireEvent.change(screen.getByPlaceholderText("dd-mm-yyyy"), {
    target: { value: "05-03-2026" },
  });
  expect(onChange).not.toHaveBeenCalled();
  // Typed in-range value is accepted.
  fireEvent.change(screen.getByPlaceholderText("dd-mm-yyyy"), {
    target: { value: "18-03-2026" },
  });
  expect(onChange).toHaveBeenCalledWith("2026-03-18");
});

test("date round-trips through the picker with no timezone shift", () => {
  const onChange = jest.fn();
  const { container } = render(<DateField value="2026-03-12" onChange={onChange} />);
  // ISO -> display carries the exact stored day, no -1/+1 drift.
  expect(screen.getByPlaceholderText("dd-mm-yyyy").value).toBe("12-03-2026");
  // Picking a day emits exactly that calendar day back as ISO (no timezone shift).
  fireEvent.click(screen.getByPlaceholderText("dd-mm-yyyy"));
  fireEvent.click(dayButton(container, 20));
  expect(onChange).toHaveBeenCalledWith("2026-03-20");
});
