export default function MasteryDeltaIndicator({ delta = 0 }) {
  const up = delta >= 0;
  const mag = Math.min(Math.abs(delta), 100);
  return <div className="inline-flex items-center gap-2"><span aria-label={up ? 'improved' : 'declined'}>{up ? '↑' : '↓'}</span><div className="h-2 w-24 rounded bg-slate-200"><div className={`h-2 rounded ${up ? 'bg-green-700' : 'bg-red-700'}`} style={{ width: `${mag}%` }} /></div><span className="text-xs">{Math.abs(delta)}%</span></div>;
}
