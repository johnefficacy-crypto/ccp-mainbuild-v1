export default function ChartLegend({ items = [] }) {
  return (
    <ul className="mt-2 flex flex-wrap gap-3 text-xs text-slate-600" aria-label="chart legend">
      {items.map((item) => (
        <li key={item.label} className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: item.color }} aria-hidden="true" />
          <span>{item.label}</span>
        </li>
      ))}
    </ul>
  );
}
