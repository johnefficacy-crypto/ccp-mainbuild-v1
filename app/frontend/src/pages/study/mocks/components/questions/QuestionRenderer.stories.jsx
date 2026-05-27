import React, { useState } from "react";
import QuestionRenderer from "./QuestionRenderer";

export default { title: "Study/QuestionRenderer", component: QuestionRenderer };
const base = { id:"q1", question_text:"Solve $x^2=4$", options:[{id:"a",option_index:"A",option_text:"2"},{id:"b",option_index:"B",option_text:"4"}], correct_option_id:"a", explanation:"Because **x=2** or -2", language:"en" };
const types=["mcq_single","mcq_multi","statement_based","assertion_reason","match_following"];
const modes=["attempt","review","preview"];

function Story({question, mode}) { const [value,setValue]=useState({}); return <QuestionRenderer question={question} mode={mode} value={value} onChange={setValue} showCorrect showExplanation/>; }

export const All = () => <div>{types.flatMap((t)=>modes.map((m)=><Story key={`${t}-${m}`} mode={m} question={{...base,question_type:t,left_items:[{id:'l1',label:'L1'}],right_items:[{id:'r1',label:'R1'}]}}/>))}</div>;
