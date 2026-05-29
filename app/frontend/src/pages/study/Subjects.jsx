import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { TopicRadarChart } from "./components/reports";

const TREND_LABEL = { up: "↑ improving", down: "↓ declining", flat: "→ steady" };

export default function Subjects(){
  const [items,setItems]=useState([]); const [loading,setLoading]=useState(true);
  useEffect(()=>{api.get('/api/study/subjects').then((d)=>setItems(Array.isArray(d)?d:(d?.items||[]))).finally(()=>setLoading(false));},[]);
  const radar=items.slice(0,10).map(i=>({topic:i.subject||i.subject_id,mastery:i.progress||0}));
  return <section className="space-y-4" data-testid="subjects-page"><h1 className="font-heading text-3xl">Subject mastery</h1><TopicRadarChart data={radar} loading={loading} /><div className="grid md:grid-cols-2 gap-3">{items.map(i=><div key={i.subject_id||i.subject} className="rounded border p-3 text-left"><div className="flex items-center justify-between"><span className="font-medium">{i.subject}</span><span className="text-xs text-slate-500">{TREND_LABEL[i.trend]||i.trend}</span></div><div className="text-sm text-slate-600">{i.progress}% mastery · {i.weak_count} weak · {i.locked_topics} topics</div></div>)}</div></section>
}
