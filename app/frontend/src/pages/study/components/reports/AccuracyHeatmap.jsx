import ChartContainer from './shared/ChartContainer';
import { accuracyColor } from './shared/colorScales';

export default function AccuracyHeatmap({ topics = [], difficulties = ['easy', 'medium', 'hard'], cells = [], onCellClick, loading, error, dataTestId }) {
  const map = new Map(cells.map((c) => [`${c.topic_id}:${c.difficulty}`, c]));
  return (
    <ChartContainer title="Accuracy Heatmap" summary="Topic by difficulty accuracy." loading={loading} error={error} isEmpty={!cells.length} dataTestId={dataTestId}>
      <div className="overflow-auto"><table className="min-w-full text-xs"><thead><tr><th>Topic</th>{difficulties.map((d)=><th key={d}>{d}</th>)}</tr></thead><tbody>{topics.map((t)=><tr key={t.topic_id}><td>{t.topic_name}</td>{difficulties.map((d)=>{const c=map.get(`${t.topic_id}:${d}`);return <td key={d}><button className="w-full rounded px-2 py-1 text-white" style={{background:accuracyColor(c?.accuracy_pct)}} onClick={()=>onCellClick?.(t.topic_id,d)}>{Math.round(c?.accuracy_pct||0)}%</button></td>;})}</tr>)}</tbody></table></div>
    </ChartContainer>
  );
}
