import React from "react";
import PropTypes from "prop-types";
import { GripVertical, X } from "lucide-react";

/**
 * One task on the board.
 *
 * The planner/yours distinction is carried by WORDS ("Yours · stays put" vs
 * "Planner · may change"), not by colour alone — the user has to be able to
 * tell what tomorrow's regeneration will replace, and colour is not available
 * to every reader. The left rail and weight reinforce the same fact for people
 * scanning quickly.
 */
export default function TaskCard({
  task,
  grabbed,
  onGrabToggle,
  onKeyDown,
  onRemove,
  onDragStart,
  onDragEnd,
  busy,
}) {
  const yours = task.placed_by_user;
  const minutes = task.planned_minutes;
  const score = task.priority_score;

  return (
    <li
      data-testid="board-task"
      data-task-id={task.id}
      data-source={yours ? "user" : "planner"}
      draggable={!busy}
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", task.id);
        onDragStart?.(task);
      }}
      onDragEnd={() => onDragEnd?.()}
      className={`relative rounded-lg border bg-white px-3 py-2.5 ${
        grabbed ? "border-[#2E2218] ring-2 ring-[#2E2218]" : "border-[#E7DECB]"
      }`}
    >
      <span
        aria-hidden="true"
        className={`absolute left-0 top-2 bottom-2 w-[3px] rounded-full ${
          yours ? "bg-[#2E2218]" : "bg-[#E7DECB]"
        }`}
      />
      <div className="pl-2">
        <div className="flex items-start gap-2">
          <button
            type="button"
            aria-label={
              grabbed
                ? `Drop ${task.topic || task.title}`
                : `Move ${task.topic || task.title}`
            }
            aria-pressed={grabbed}
            onClick={() => onGrabToggle?.(task)}
            onKeyDown={onKeyDown}
            disabled={busy}
            className="mt-0.5 shrink-0 rounded p-0.5 text-clay-700 hover:bg-[#F3EADB] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218]"
          >
            <GripVertical size={14} aria-hidden="true" />
          </button>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] leading-snug text-[#2E2218]">
              {task.topic || task.title}
            </p>
            <p className="num-mono mt-1 text-[10.5px] text-clay-700">
              {task.task_type || "study"}
              {minutes ? ` · ${minutes} min` : ""}
              {score != null ? ` · priority ${Math.round(score)}` : ""}
            </p>
          </div>
          <button
            type="button"
            aria-label={`Remove ${task.topic || task.title}`}
            onClick={() => onRemove?.(task)}
            disabled={busy}
            className="shrink-0 rounded p-0.5 text-clay-700 hover:bg-[#F3EADB] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218]"
          >
            <X size={13} aria-hidden="true" />
          </button>
        </div>
        {task.why && (
          // The same one-liner the "This week" list shows, so a block reads the
          // same wherever the user meets it.
          <p className="mt-1.5 text-[11px] leading-snug text-clay-700">{task.why}</p>
        )}
        <p
          className={`mt-1.5 text-[10.5px] ${
            yours ? "font-semibold text-[#2E2218]" : "text-clay-700"
          }`}
        >
          {yours ? "Yours · stays put" : "Planner · may change"}
        </p>
      </div>
    </li>
  );
}

TaskCard.propTypes = {
  task: PropTypes.shape({
    id: PropTypes.string.isRequired,
    title: PropTypes.string,
    topic: PropTypes.string,
    task_type: PropTypes.string,
    planned_minutes: PropTypes.number,
    priority_score: PropTypes.number,
    placed_by_user: PropTypes.bool,
    why: PropTypes.string,
  }).isRequired,
  grabbed: PropTypes.bool,
  onGrabToggle: PropTypes.func,
  onKeyDown: PropTypes.func,
  onRemove: PropTypes.func,
  onDragStart: PropTypes.func,
  onDragEnd: PropTypes.func,
  busy: PropTypes.bool,
};
