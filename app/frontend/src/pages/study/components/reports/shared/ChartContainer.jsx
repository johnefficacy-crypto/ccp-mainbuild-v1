export default function ChartContainer({
  title,
  summary,
  loading,
  error,
  isEmpty,
  emptyText = 'No data to display yet.',
  height = 280,
  children,
  dataTestId,
  figureRef,
}) {
  return (
    <figure ref={figureRef} data-testid={dataTestId} className="rounded-xl border border-slate-200 bg-white p-4">
      {title ? <h3 className="text-sm font-semibold text-slate-900">{title}</h3> : null}
      <figcaption className="mb-3 mt-1 text-xs text-slate-600">{summary}</figcaption>
      <div style={{ minHeight: height }}>
        {loading ? <div className="h-full animate-pulse rounded bg-slate-100" /> : null}
        {!loading && error ? <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
        {!loading && !error && isEmpty ? (
          <div className="flex h-full items-center justify-center rounded border border-dashed border-slate-300 text-sm text-slate-500">
            {emptyText}
          </div>
        ) : null}
        {!loading && !error && !isEmpty ? children : null}
      </div>
    </figure>
  );
}
