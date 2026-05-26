export default function CorrectionTaskCard({ task, onAccept, onDismiss, showSourceLink = true }) {
  if (!task) return null;
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4">
      <h4 className="text-sm font-semibold text-slate-900">{task.title || task.topic_name || 'Correction task'}</h4>
      <p className="mt-1 text-sm text-slate-600">{task.reason || task.error_type || 'Needs correction review.'}</p>
      {showSourceLink && task.source_url ? <a className="mt-2 inline-block text-xs text-blue-700 underline" href={task.source_url}>View source</a> : null}
      <div className="mt-3 flex gap-2"><button onClick={onAccept} className="rounded bg-slate-900 px-3 py-1 text-xs text-white">Accept</button><button onClick={onDismiss} className="rounded border border-slate-300 px-3 py-1 text-xs">Dismiss</button></div>
    </article>
  );
}
