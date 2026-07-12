import React from "react";
import MCQSingle from "./types/MCQSingle";
import MCQMulti from "./types/MCQMulti";
import StatementBased from "./types/StatementBased";
import AssertionReason from "./types/AssertionReason";
import MatchFollowing from "./types/MatchFollowing";
import NumericalAnswer from "./types/NumericalAnswer";
import QuestionStimuli from "./shared/QuestionStimuli";

// Keys cover both the frontend renderer vocabulary (mcq_single, …) and the
// backend question_type enum values (mcq, integer). An unknown type falls back
// to MCQSingle. `integer` (backend) → the numeric renderer.
const MAP = { mcq_single: MCQSingle, mcq: MCQSingle, mcq_multi: MCQMulti, msq: MCQMulti, statement_based: StatementBased, assertion_reason: AssertionReason, match_following: MatchFollowing, numerical_answer: NumericalAnswer, integer: NumericalAnswer, numerical: NumericalAnswer };

export default function QuestionRenderer(props) {
  const C = MAP[props.question?.question_type] || MCQSingle;
  // Shared passage/caselet/table (projected PYQ, PR-5/6) renders above the stem
  // for every question type, so comprehension items show their passage in context.
  return (
    <>
      <QuestionStimuli stimuli={props.question?.stimuli} />
      <C {...props} />
    </>
  );
}
