import React, { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";
import { AccuracyHeatmap, ErrorTypeDonut } from "./components/reports";

export default function Mistakes(){
  const [data,setData]=useState([]); const [loading,setLoading]=useState(true); const [active,setActive]=useState("");
  useEffect(()=>{api.get('/api/study/reports/mistakes?days=90').then((d)=>setData(Array.isArray(d)?d:(d?.items||[]))).finally(()=>setLoading(false));},[]);
  const donut=useMemo(()=>data.map(x=>({label:x.error_type,value:x.count})),[data]);
  const filtered=active?data.filter(d=>d.error_type===active):data;
  return <section className="space-y-4" data-testid="mistakes-page"><h1 className="font-heading text-3xl">Mistakes dashboard</h1><ErrorTypeDonut data={donut} loading={loading} /><div className="flex flex-wrap gap-2">{donut.map(d=><button key={d.label} className={`rounded px-2 py-1 border ${active===d.label?'bg-slate-900 text-white':''}`} onClick={()=>setActive(active===d.label?'':d.label)}>{d.label} ({d.value})</button>)}</div><AccuracyHeatmap data={filtered.flatMap((r)=> (r.topics||[]).map(t=>({topic:t.topic_id || 'topic',difficulty:'mixed',accuracy:Math.max(0,100-(t.count||0)*5)})))} loading={loading} /><ul className="text-sm">{filtered.flatMap(f=>f.recent_question_ids||[]).slice(0,20).map(q=><li key={q}>{q}</li>)}</ul></section>
}
