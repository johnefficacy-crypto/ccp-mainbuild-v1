import React from "react";
import MCQSingle from "./types/MCQSingle";
import MCQMulti from "./types/MCQMulti";
import StatementBased from "./types/StatementBased";
import AssertionReason from "./types/AssertionReason";
import MatchFollowing from "./types/MatchFollowing";
import NumericalAnswer from "./types/NumericalAnswer";

const MAP = { mcq_single: MCQSingle, mcq_multi: MCQMulti, statement_based: StatementBased, assertion_reason: AssertionReason, match_following: MatchFollowing, numerical_answer: NumericalAnswer };

export default function QuestionRenderer(props) {
  const C = MAP[props.question?.question_type] || MCQSingle;
  return <C {...props} />;
}
