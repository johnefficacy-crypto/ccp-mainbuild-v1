import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import SentenceIssueCard from "./SentenceIssueCard";

/**
 * @param {object} overrides
 * @returns {object} a valid issue shape with overrides applied
 */
function makeIssue(overrides = {}) {
  return {
    issue_type: "subject_verb_agreement",
    span_start_utf16: 0,
    span_end_utf16: 7,
    quoted_text: "they is",
    explanation: "Subject and verb do not agree.",
    severity: "must_fix",
    ...overrides,
  };
}

test("valid span highlights the quoted text and shows explanation", () => {
  render(<SentenceIssueCard issue={makeIssue()} answerText="they is here" />);

  const card = screen.getByTestId("issue-card");
  expect(card).toBeInTheDocument();

  const mark = card.querySelector("mark");
  expect(mark).toBeInTheDocument();
  expect(mark).toHaveTextContent("they is");
  expect(screen.getByText("Subject and verb do not agree.")).toBeInTheDocument();
});

test("uses UTF-16 code-unit offsets across a non-BMP emoji", () => {
  // "hi " = 3, "😀" = 2 UTF-16 units → 5, " " = 1 → 6, "they is" = 6..13.
  const answerText = "hi 😀 they is x";
  render(
    <SentenceIssueCard
      issue={makeIssue({ span_start_utf16: 6, span_end_utf16: 13 })}
      answerText={answerText}
    />,
  );

  const mark = screen.getByTestId("issue-card").querySelector("mark");
  expect(mark).toHaveTextContent("they is");
});

test("mismatched span renders the invalid variant with no highlight", () => {
  render(
    <SentenceIssueCard
      // Span points at "they is" but the answer text no longer matches.
      issue={makeIssue({ span_start_utf16: 0, span_end_utf16: 7 })}
      answerText="completely different answer"
    />,
  );

  const card = screen.getByTestId("issue-card-invalid");
  expect(card).toBeInTheDocument();
  expect(card.querySelector("mark")).not.toBeInTheDocument();
  expect(screen.getByText("Subject and verb do not agree.")).toBeInTheDocument();
});

test("suggested_text renders in the Suggested block only when present", () => {
  const { rerender } = render(
    <SentenceIssueCard
      issue={makeIssue({ suggested_text: "they are" })}
      answerText="they is here"
    />,
  );
  expect(screen.getByText("Suggested")).toBeInTheDocument();
  expect(screen.getByText("they are")).toBeInTheDocument();

  rerender(
    <SentenceIssueCard issue={makeIssue()} answerText="they is here" />,
  );
  expect(screen.queryByText("Suggested")).not.toBeInTheDocument();
});
