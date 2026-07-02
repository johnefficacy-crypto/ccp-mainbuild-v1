import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";

import ErrorReview from "./ErrorReview";

function makeGroup(overrides = {}) {
  return {
    microtopic_id: "m1",
    issue_count: 1,
    issues: [
      {
        id: "i1",
        issue_type: "subject_verb_agreement",
        severity: "must_fix",
        quoted_text: "they was",
        explanation: "Use 'were'.",
        suggested_text: "they were",
      },
    ],
    ...overrides,
  };
}

test("collapsed by default; expands to show issues on click", () => {
  render(<ErrorReview group={makeGroup()} />);
  expect(screen.queryByTestId("error-issue")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /Microtopic m1: 1 recurring issue/i }));
  expect(screen.getByTestId("error-issue")).toBeInTheDocument();
  expect(screen.getByText("Use 'were'.")).toBeInTheDocument();
  expect(screen.getByText("they were")).toBeInTheDocument();
});

test("defaultExpanded renders issues immediately and marks the quoted fragment", () => {
  render(<ErrorReview group={makeGroup()} defaultExpanded />);
  const mark = screen.getByTestId("error-issue").querySelector("mark");
  expect(mark).toHaveTextContent("they was");
});

test("unmapped group falls back to a readable title", () => {
  render(<ErrorReview group={makeGroup({ microtopic_id: null })} defaultExpanded />);
  expect(screen.getByText("Unmapped issues")).toBeInTheDocument();
});

test("Grammar Lab cross-link is a disabled coming-soon stub", () => {
  render(<ErrorReview group={makeGroup()} defaultExpanded />);
  const stub = screen.getByTestId("grammar-lab-stub");
  expect(stub).toBeDisabled();
  expect(stub).toHaveTextContent(/coming soon/i);
});
