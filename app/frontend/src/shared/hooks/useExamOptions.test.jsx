/**
 * Tests for useExamOptions:
 * - fetches from /api/exams, maps slug→value / name→label
 * - select renders options with slug as the option value (not free text)
 * - selecting an option writes the slug, not the display label
 */
import React, { useState } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

jest.mock("../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
}));

const { api } = require("../../lib/api");
const useExamOptions = require("./useExamOptions").default;

const EXAM_ITEMS = [
  { slug: "upsc-cse", name: "UPSC CSE" },
  { slug: "ssc-cgl", name: "SSC CGL" },
];

function ExamSelect() {
  const options = useExamOptions();
  const [value, setValue] = useState("");
  return (
    <select
      data-testid="exam-select"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    >
      <option value="">Not provided</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

beforeEach(() => {
  api.get.mockReset();
});

test("fetches /api/exams and renders one <option> per exam", async () => {
  api.get.mockResolvedValue({ items: EXAM_ITEMS });
  render(<ExamSelect />);

  // Both exam names appear as option text.
  expect(await screen.findByText("UPSC CSE")).toBeTruthy();
  expect(screen.getByText("SSC CGL")).toBeTruthy();

  // The API was called with the exams endpoint.
  expect(api.get).toHaveBeenCalledWith("/api/exams?limit=100");
});

test("option value is the slug, not the display label", async () => {
  api.get.mockResolvedValue({ items: EXAM_ITEMS });
  render(<ExamSelect />);

  await screen.findByText("UPSC CSE");

  // <option value="upsc-cse">UPSC CSE</option>
  const upscOption = screen.getByText("UPSC CSE").closest("option");
  expect(upscOption.value).toBe("upsc-cse");

  const sscOption = screen.getByText("SSC CGL").closest("option");
  expect(sscOption.value).toBe("ssc-cgl");
});

test("selecting an exam writes the slug into the form value", async () => {
  api.get.mockResolvedValue({ items: EXAM_ITEMS });
  render(<ExamSelect />);

  await screen.findByText("UPSC CSE");

  fireEvent.change(screen.getByTestId("exam-select"), {
    target: { value: "ssc-cgl" },
  });

  // The select's current value is the slug — not the label "SSC CGL".
  expect(screen.getByTestId("exam-select").value).toBe("ssc-cgl");
});

test("falls back to empty options when api.get rejects", async () => {
  api.get.mockRejectedValue(new Error("network error"));
  render(<ExamSelect />);

  // Only the fallback "Not provided" option — no exam rows.
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.queryByText("UPSC CSE")).toBeNull();
  expect(screen.getByText("Not provided")).toBeTruthy();
});
