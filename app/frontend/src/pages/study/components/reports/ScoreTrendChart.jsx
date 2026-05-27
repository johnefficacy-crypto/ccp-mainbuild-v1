import { useMemo, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Dot } from 'recharts';
import ChartContainer from './shared/ChartContainer';
import { formatPct } from './shared/TooltipFormatter';

export default function ScoreTrendChart({ data = [], metric = 'score', highlightAttemptId, onPointClick, height = 280, loading, error, dataTestId }) {
  const exportRef = useRef(null);
  const key = metric === 'accuracy' ? 'accuracy_pct' : metric === 'time_used' ? 'time_used' : 'score_pct';
  const rows = useMemo(() => data.map((d, i) => ({ ...d, x: d.attempt_label || `A${i + 1}`, y: d[key] ?? 0 })), [data, key]);
  return <ChartContainer figureRef={exportRef} title="Score Trend" summary="Trend across attempts" loading={loading} error={error} isEmpty={!rows.length} height={height} dataTestId={dataTestId}>{<ResponsiveContainer width="100%" height={height-40}><LineChart data={rows}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="x" /><YAxis /><Tooltip formatter={(v)=> key==='time_used'? v:formatPct(v)} /><Line dataKey="y" stroke="var(--color-primary, #2563eb)" dot={(props)=><Dot {...props} data-testid={`score-trend-point-${props.index}`} r={props.payload.attempt_id===highlightAttemptId?5:3} tabIndex={0} role="button" aria-label={`Open attempt ${props.index+1}`} style={{cursor:'pointer'}} onKeyDown={(e)=>e.key==='Enter'&&onPointClick?.(props.payload)} onClick={()=>onPointClick?.(props.payload)} />} /></LineChart></ResponsiveContainer>}</ChartContainer>;
}
