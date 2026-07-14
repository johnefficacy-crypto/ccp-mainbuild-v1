import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";

import MyWritingErrors from "./MyWritingErrors";
import useErrorLab from "../english-practice/useErrorLab";

// Factory mock so the real hook (which imports lib/api → env) is never loaded.
jest.mock("../english-practice/useErrorLab", () => ({
  __esModule: true,
  default: jest.fn(),
}));

const GROUP = {
  microtopic_id: "m1",
  microtopic_name: "Subject-verb agreement",
  microtopic_slug: "subject-verb-agreement",
  issue_count: 2,
  issues: [
    {
      id: "i1",
      issue_type: "subject_verb_agreement",
      severity: "must_fix",
      quoted_text: "they was",
      explanation: "Use 'were'.",
      suggested_text: "they were",
    },
    {
      id: "i2",
      issue_type: "article_use",
      severity: "should_fix",
      quoted_text: "a apple",
      explanation: "Use 'an'.",
    },
  ],
};

afterEach(() => jest.clearAllMocks());

test("loading state announces to assistive tech", () => {
  useErrorLab.mockReturnValue({ groups: [], status: "loading", refresh: jest.fn() });
  render(<MyWritingErrors />);
  expect(screen.getByTestId("english-loading")).toBeInTheDocument();
  expect(screen.getByRole("status")).toBeInTheDocument();
});

test("empty state renders when there are no recurring issues", () => {
  useErrorLab.mockReturnValue({ groups: [], status: "empty", refresh: jest.fn() });
  render(<MyWritingErrors />);
  expect(screen.getByTestId("english-empty")).toBeInTheDocument();
});

test("error state offers a retry that calls refresh", () => {
  const refresh = jest.fn();
  useErrorLab.mockReturnValue({ groups: [], status: "error", refresh });
  render(<MyWritingErrors />);
  fireEvent.click(screen.getByRole("button", { name: /retry|try again/i }));
  expect(refresh).toHaveBeenCalled();
});

test("live state renders microtopic groups; first is expanded by default", () => {
  useErrorLab.mockReturnValue({ groups: [GROUP], status: "live", refresh: jest.fn() });
  render(<MyWritingErrors />);
  expect(screen.getByTestId("english-groups")).toBeInTheDocument();
  expect(screen.getByTestId("error-group-m1")).toBeInTheDocument();
  // First group defaults expanded → both issues visible.
  expect(screen.getAllByTestId("error-issue")).toHaveLength(2);
  expect(screen.getByText("Use 'were'.")).toBeInTheDocument();
});

test("group toggles collapse/expand and Grammar Lab stub is disabled", () => {
  useErrorLab.mockReturnValue({ groups: [GROUP], status: "live", refresh: jest.fn() });
  render(<MyWritingErrors />);

  const stub = screen.getByTestId("grammar-lab-stub");
  expect(stub).toBeDisabled();
  expect(stub).toHaveAttribute("aria-disabled", "true");

  // Collapse the first group → issues disappear.
  const toggle = screen.getByRole("button", {
    name: /Subject-verb agreement: 2 recurring issues/i,
  });
  fireEvent.click(toggle);
  expect(screen.queryByTestId("error-issue")).not.toBeInTheDocument();
});
