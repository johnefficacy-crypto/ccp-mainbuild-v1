import React from "react";
import QuestionStem from "../shared/QuestionStem";
import OptionList from "../shared/OptionList";
import MarkdownSafe from "../shared/MarkdownSafe";

export default function MCQSingle({ question, mode, value, onChange, disabled, showCorrect, showExplanation }) {
  return <div><QuestionStem text={question.question_text} images={question.images} /><OptionList options={question.options} selected={value?.selected_option_id ? [value.selected_option_id] : []} disabled={disabled || mode === "review"} onSelect={(id)=>onChange({ ...value, selected_option_id:id })} />{showCorrect && question.correct_option_id ? <div>Correct: {question.correct_option_id}</div>:null}{showExplanation && question.explanation ? <MarkdownSafe text={question.explanation} />:null}</div>;
}
