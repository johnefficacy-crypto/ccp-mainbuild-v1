import React, { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api";
import AttemptSummaryCard from "../components/reports/AttemptSummaryCard";
import SectionBreakdownBars from "../components/reports/SectionBreakdownBars";
const AccuracyHeatmap = lazy(() => import("../components/reports/AccuracyHeatmap"));
const TimeDistributionChart = lazy(() => import("../components/reports/TimeDistributionChart"));
const ErrorTypeDonut = lazy(() => import("../components/reports/ErrorTypeDonut"));

export default function MockResult() {
  const { attemptId } = useParams(); const navigate = useNavigate();
  const [result,setResult]=useState(null); const [analytics,setAnalytics]=useState(null); const [tab,setTab]=useState("overview");
  useEffect(()=>{ api.get(`/study/mocks/attempts/${attemptId}/result`).then(setResult); },[attemptId]);
  useEffect(()=>{ if(tab!=="overview") api.get(`/study/mocks/attempts/${attemptId}/analytics`).then(setAnalytics).catch(()=>setAnalytics({})); },[attemptId,tab]);
  const donut=useMemo(()=>Object.entries((analytics?.response_classification||[]).reduce((a,r)=>((a[r.error_type]=(a[r.error_type]||0)+1),a),{})).map(([label,value])=>({label,value})),[analytics]);
  if(!result) return <div>Loading…</div>;
  return <div className="p-4 space-y-4">
    <AttemptSummaryCard scorePct={result.score_percentage} accuracyPct={(result.total_correct||0)/Math.max((result.total_correct||0)+(result.total_wrong||0),1)*100} timeUsed={`${Math.round((result.time_used_sec||0)/60)}m`} />
    <SectionBreakdownBars data={(result.section_breakdown||[]).map(s=>({section:s.section_name||`Section ${s.section_index+1}`,correct:s.correct,wrong:s.wrong,unattempted:s.unattempted}))} />
    <div className="flex gap-2">{["overview","topic","time","error"].map(t=><button key={t} onClick={()=>setTab(t)}>{t}</button>)}</div>
    {tab==="topic" && <Suspense fallback={<div>Loading chart…</div>}><AccuracyHeatmap topics={(analytics?.topic_breakdown||[]).map((t,i)=>({topic_id:t.topic_id||`t${i}`,topic_name:t.topic_id||"General"}))} cells={[]} /></Suspense>}
    {tab==="time" && <Suspense fallback={<div>Loading chart…</div>}><TimeDistributionChart data={[]} /></Suspense>}
    {tab==="error" && <Suspense fallback={<div>Loading chart…</div>}><ErrorTypeDonut data={donut} /></Suspense>}
    <button onClick={()=>navigate(`/app/study/mocks/attempts/${attemptId}/review`)}>Review Questions</button>
  </div>;
}
