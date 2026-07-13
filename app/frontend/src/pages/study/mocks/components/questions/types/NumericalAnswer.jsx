import React from "react";
import QuestionStem from "../shared/QuestionStem";
import MarkdownSafe from "../shared/MarkdownSafe";

/**
 * Integer / numerical question renderer.
 *
 * Attempt mode: a controlled numeric input emitting `{ numeric_answer }` (the
 * key the save API + scorer use). Review mode: shows the learner's typed value
 * and, with `showCorrect`, the correct value + tolerance from the frozen
 * snapshot — never a raw spec object.
 */
export default function NumericalAnswer({
  question,
  value,
  onChange,
  mode,
  disabled,
  showCorrect,
  showExplanation,
}) {
  const isReview = mode === "review";

  if (isReview) {
    const learner = question.numeric_answer;
    const correct = question.correct_numeric_answer;
    const tol = question.numeric_tolerance;
    const hasAnswer = learner !== null && learner !== undefined && learner !== "";
    return (
      <div>
        <QuestionStem text={question.question_text} images={question.images} />
        <div className="mt-2 space-y-1 text-sm" data-testid="review-numeric">
          <div data-testid="review-numeric-your">
            Your answer: {hasAnswer ? String(learner) : <span className="text-muted-foreground">— not answered</span>}
          </div>
          {showCorrect && correct !== null && correct !== undefined ? (
            <div data-testid="review-numeric-correct" className="font-medium">
              Correct answer: {String(correct)}
              {tol ? ` (± ${tol})` : ""}
            </div>
          ) : null}
        </div>
        {showExplanation && question.explanation ? <MarkdownSafe text={question.explanation} /> : null}
      </div>
    );
  }

  return (
    <div>
      <QuestionStem text={question.question_text} images={question.images} />
      <input
        type="text"
        inputMode="decimal"
        data-testid="numeric-answer-input"
        value={value?.numeric_answer ?? ""}
        onChange={(e) => onChange?.({ ...value, numeric_answer: e.target.value })}
        disabled={disabled}
      />
      {showExplanation && question.explanation ? <MarkdownSafe text={question.explanation} /> : null}
    </div>
  );
}
