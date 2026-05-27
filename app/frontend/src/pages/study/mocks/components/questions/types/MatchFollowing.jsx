import React from "react";
import QuestionStem from "../shared/QuestionStem";

export default function MatchFollowing({ question, value, onChange, mode, disabled }) {
  const matches = value?.matches || {};
  const left = question.left_items || [];
  const right = question.right_items || [];
  return <div><QuestionStem text={question.question_text} images={question.images}/>{left.map((l)=> <div key={l.id}><span>{l.label}</span><select value={matches[l.id] || ""} disabled={disabled||mode==="review"} onChange={(e)=>onChange({ ...value, matches:{...matches,[l.id]:e.target.value}})}><option value="">Select</option>{right.map(r=><option key={r.id} value={r.id}>{r.label}</option>)}</select></div>)}</div>;
}
