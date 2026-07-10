import React from "react";
import { render, screen } from "@testing-library/react";
import MCQSingle from "./MCQSingle";

const OPTIONS = [
  { id: "11111111-1111-4111-8111-111111111111", option_index: "A", option_text: "New Delhi" },
  { id: "22222222-2222-4222-8222-222222222222", option_index: "B", option_text: "Mumbai" },
];

test("review shows the correct option label + text, never the raw UUID", () => {
  render(
    <MCQSingle
      mode="review"
      showCorrect
      question={{
        question_text: "Capital of India?",
        options: OPTIONS,
        correct_option_id: "11111111-1111-4111-8111-111111111111",
      }}
    />,
  );
  const el = screen.getByTestId("review-correct-answer");
  expect(el.textContent).toContain("A");
  expect(el.textContent).toContain("New Delhi");
  // The UUID must never be rendered to the learner.
  expect(el.textContent).not.toContain("11111111-1111-4111-8111-111111111111");
});

test("falls back to a positional letter when a projected label is absent", () => {
  render(
    <MCQSingle
      mode="review"
      showCorrect
      question={{
        question_text: "Second option?",
        options: [
          { id: "a", option_text: "First" },
          { id: "b", option_text: "Second" },
        ],
        correct_option_id: "b",
      }}
    />,
  );
  const el = screen.getByTestId("review-correct-answer");
  expect(el.textContent).toContain("B");
  expect(el.textContent).toContain("Second");
});

test("renders nothing for the correct-answer block when correct_option_id is unknown", () => {
  render(
    <MCQSingle
      mode="review"
      showCorrect
      question={{
        question_text: "No key?",
        options: OPTIONS,
        correct_option_id: "does-not-exist",
      }}
    />,
  );
  expect(screen.queryByTestId("review-correct-answer")).toBeNull();
});
