import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { MasteryDeltaIndicator, TopicRadarChart } from "./components/reports";

export default function Subjects(){
  const [items,setItems]=useState([]); const [loading,setLoading]=useState(true);
  useEffect(()=>{api.get('/api/study/reports/subject-mastery').then((d)=>setItems(Array.isArray(d)?d:(d?.items||[]))).finally(()=>setLoading(false));},[]);
  const radar=items.slice(0,10).map(i=>({topic:i.topic_name||i.subject_name||i.subject_id,mastery:i.mastery||0}));
  return <section className="space-y-4" data-testid="subjects-page"><h1 className="font-heading text-3xl">Subject mastery</h1><TopicRadarChart data={radar} loading={loading} /><div className="grid md:grid-cols-2 gap-3">{items.map(i=><button key={`${i.subject_id}-${i.topic_id||''}`} className="rounded border p-3 text-left" onClick={()=> i.topic_id && (window.location.href=`/app/study/mocks?topic=${i.topic_id}`)}><div className="font-medium">{i.topic_name||i.subject_name}</div><MasteryDeltaIndicator delta={i.mastery_delta||0} /></button>)}</div></section>
}
