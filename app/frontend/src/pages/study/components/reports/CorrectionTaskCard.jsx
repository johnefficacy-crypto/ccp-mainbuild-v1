import PropTypes from "prop-types";

import { CorrectionTaskDraft } from "../../../../types/masteryEngine";

function humanizeTaskType(taskType) {
  if (!taskType) return "Correction task";
  return taskType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default function CorrectionTaskCard({ task, onAccept, onDismiss }) {
  if (!task) return null;
  const topicLabel = task.microtopic_id || task.topic_id;
  const errorTypes = task.evidence?.error_types ?? [];
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-semibold text-slate-900">{humanizeTaskType(task.task_type)}</h4>
        {typeof task.priority === "number" ? (
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">P{task.priority}</span>
        ) : null}
      </div>
      {topicLabel ? <p className="mt-0.5 text-xs text-slate-500">{topicLabel}</p> : null}
      <p className="mt-1 text-sm text-slate-600">{task.reason || "Needs correction review."}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        {typeof task.estimated_minutes === "number" ? <span>~{task.estimated_minutes} min</span> : null}
        {errorTypes.map((errorType) => (
          <span key={errorType} className="rounded bg-slate-100 px-2 py-0.5">{errorType}</span>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button onClick={onAccept} className="rounded bg-slate-900 px-3 py-1 text-xs text-white">Accept</button>
        <button onClick={onDismiss} className="rounded border border-slate-300 px-3 py-1 text-xs">Dismiss</button>
      </div>
    </article>
  );
}

CorrectionTaskCard.propTypes = {
  task: CorrectionTaskDraft,
  onAccept: PropTypes.func,
  onDismiss: PropTypes.func,
};
