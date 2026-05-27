import React from "react";
import QuestionStem from "../shared/QuestionStem";
import MarkdownSafe from "../shared/MarkdownSafe";

export default function NumericalAnswer({ question, value, onChange, mode, disabled, showExplanation }) {
  return <div><QuestionStem text={question.question_text} images={question.images}/><input type="text" inputMode="decimal" value={value?.numerical_answer || ""} onChange={(e)=>onChange({ ...value, numerical_answer: e.target.value })} disabled={disabled||mode==="review"} />{showExplanation && question.explanation ? <MarkdownSafe text={question.explanation} />:null}</div>;
}
