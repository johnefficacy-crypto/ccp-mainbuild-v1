import React from "react";
import { render, fireEvent } from "@testing-library/react";
import NumericalAnswer from "./NumericalAnswer";
import QuestionRenderer from "../QuestionRenderer";

test("attempt mode emits { numeric_answer } on change", () => {
  const onChange = jest.fn();
  const { getByTestId } = render(
    <NumericalAnswer question={{ question_text: "6 x 7?" }} value={{}} onChange={onChange} mode="attempt" />,
  );
  fireEvent.change(getByTestId("numeric-answer-input"), { target: { value: "42" } });
  expect(onChange).toHaveBeenCalledWith({ numeric_answer: "42" });
});

test("review mode shows the learner value and the correct value + tolerance", () => {
  const { getByTestId } = render(
    <NumericalAnswer
      mode="review"
      showCorrect
      question={{
        question_text: "pi?",
        numeric_answer: 3.15,
        correct_numeric_answer: 3.14,
        numeric_tolerance: 0.02,
      }}
    />,
  );
  expect(getByTestId("review-numeric-your").textContent).toContain("3.15");
  const correct = getByTestId("review-numeric-correct").textContent;
  expect(correct).toContain("3.14");
  expect(correct).toContain("± 0.02");
});

test("review mode shows 'not answered' when the learner left it blank", () => {
  const { getByTestId } = render(
    <NumericalAnswer
      mode="review"
      showCorrect
      question={{ question_text: "q", numeric_answer: null, correct_numeric_answer: 10 }}
    />,
  );
  expect(getByTestId("review-numeric-your").textContent).toContain("not answered");
});

test("QuestionRenderer maps backend question_type 'integer' to the numeric renderer", () => {
  const { getByTestId } = render(
    <QuestionRenderer
      mode="review"
      showCorrect
      question={{ question_type: "integer", question_text: "q", numeric_answer: 5, correct_numeric_answer: 5 }}
    />,
  );
  expect(getByTestId("review-numeric")).toBeTruthy();
});
