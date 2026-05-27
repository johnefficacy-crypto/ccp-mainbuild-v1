import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { AttemptSummaryCard, ScoreTrendChart } from "./components/reports";

export default function StudyProgressHub() {
  const [trend, setTrend] = useState([]);
  const [windowSize, setWindowSize] = useState(12);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let done = false;
    api.get('/api/study/reports/mock-trend?days=90').then((d)=>{ if(!done) setTrend(Array.isArray(d)?d:(d?.items||[])); }).finally(()=>!done&&setLoading(false));
    return () => { done = true; };
  }, []);

  const windowed = useMemo(() => trend.slice(Math.max(0, trend.length - windowSize)), [trend, windowSize]);
  const last = trend.length ? trend[trend.length - 1] : null;

  return <section className="space-y-4" data-testid="study-progress-page"><div className="flex items-center justify-between"><h2 className="font-heading text-2xl font-semibold">Progress</h2><select className="rounded border px-2 py-1" value={windowSize} onChange={(e)=>setWindowSize(Number(e.target.value))}><option value={12}>Last 12</option><option value={24}>Last 24</option><option value={50}>Last 50</option></select></div><ScoreTrendChart data={windowed} loading={loading} onPointClick={(p)=>p?.attempt_id && navigate(`/app/study/mocks/attempts/${p.attempt_id}/result`)} /><AttemptSummaryCard scorePct={last?.score_pct} accuracyPct={last?.accuracy_pct} timeUsed={last?.time_used_sec} label="Last attempt" /></section>;
}
