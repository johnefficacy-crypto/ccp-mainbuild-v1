import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../../lib/api";
import QuestionRenderer from "./components/questions/QuestionRenderer";

export default function MockReview(){
  const {attemptId}=useParams(); const [data,setData]=useState(null); const [filter,setFilter]=useState("all");
  useEffect(()=>{api.get(`/study/mocks/attempts/${attemptId}/review`).then(setData);},[attemptId]);
  const qs=useMemo(()=>{const all=data?.questions||[]; if(filter==="all") return all; if(filter==="correct") return all.filter(q=>q.is_correct===true); if(filter==="wrong") return all.filter(q=>q.is_correct===false); if(filter==="unattempted") return all.filter(q=>!q.selected_option_id); return all.filter(q=>q.error_type===filter);},[data,filter]);
  if(!data) return <div>Loading…</div>;
  return <div className="p-4"><div className="flex gap-2"><button onClick={()=>setFilter("all")}>all</button><button onClick={()=>setFilter("correct")}>correct</button><button onClick={()=>setFilter("wrong")}>wrong</button><button onClick={()=>setFilter("unattempted")}>unattempted</button><button onClick={()=>setFilter("option_trap")}>option_trap</button></div>{qs.map((q,i)=><div key={q.question_id}><h3>Q{i+1} {q.error_type||"not analyzed"}</h3><QuestionRenderer mode="review" showCorrect showExplanation question={{...q.question_snapshot, selected_option_id:q.selected_option_id}} /></div>)}</div>;
}
