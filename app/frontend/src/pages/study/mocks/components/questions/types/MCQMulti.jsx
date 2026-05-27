import React from "react";
import QuestionStem from "../shared/QuestionStem";
import OptionList from "../shared/OptionList";
import MarkdownSafe from "../shared/MarkdownSafe";

export default function MCQMulti({ question, mode, value, onChange, disabled, showExplanation }) {
  const sel = value?.selected_option_ids || [];
  const toggle = (id)=> onChange({ ...value, selected_option_ids: sel.includes(id)?sel.filter(x=>x!==id):[...sel,id] });
  return <div><QuestionStem text={question.question_text} images={question.images}/><OptionList options={question.options} selected={sel} multiple onSelect={toggle} disabled={disabled||mode==="review"}/>{showExplanation && question.explanation ? <MarkdownSafe text={question.explanation} />:null}</div>;
}
