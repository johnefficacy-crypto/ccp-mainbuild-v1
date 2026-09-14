import React from "react";
import PropTypes from "prop-types";
import TaskCard from "./TaskCard";

/**
 * One day of the board.
 *
 * Drop targets are the gaps between cards, not the cards themselves: dropping
 * "onto" a card is ambiguous about before/after, and a planner day is short
 * enough that explicit gaps are both clearer and easier to hit.
 */
export default function DayColumn({
  day,
  isToday,
  grabbedId,
  grabbedPlacement,
  onGrabToggle,
  onCardKeyDown,
  onRemove,
  onDragStart,
  onDragEnd,
  onDropAt,
  busy,
  maxTasks,
}) {
  const tasks = day.tasks || [];
  const over = maxTasks != null && tasks.length > maxTasks;

  function gap(index) {
    const ghost =
      grabbedPlacement &&
      grabbedPlacement.date === day.date &&
      grabbedPlacement.index === index;
    return (
      <li
        key={`gap-${index}`}
        data-testid="board-drop-gap"
        data-date={day.date}
        data-index={index}
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
        }}
        onDrop={(e) => {
          e.preventDefault();
          const id = e.dataTransfer.getData("text/plain");
          if (id) onDropAt?.(id, day.date, index);
        }}
        className={`h-2 rounded ${ghost ? "bg-[#2E2218]" : "bg-transparent"}`}
      />
    );
  }

  return (
    <section
      aria-label={`${day.label}, ${tasks.length} ${tasks.length === 1 ? "task" : "tasks"}`}
      className={`flex min-w-[210px] flex-1 flex-col rounded-xl border p-3 ${
        isToday ? "border-[#2E2218] bg-[#FBF6EF]" : "border-[#E7DECB] bg-white/60"
      }`}
    >
      <header className="mb-2">
        <h3 className="font-heading text-[14px] leading-tight text-[#2E2218]">
          {day.label}
        </h3>
        <p className="num-mono text-[10.5px] text-clay-700">
          {tasks.length} {tasks.length === 1 ? "block" : "blocks"}
          {maxTasks != null ? ` of ${maxTasks}` : ""}
        </p>
        {over && (
          <p className="mt-1 text-[10.5px] text-amber-700">
            Over your daily limit of {maxTasks}.
          </p>
        )}
      </header>

      <ul className="flex flex-col gap-0">
        {gap(0)}
        {tasks.map((task, i) => (
          <React.Fragment key={task.id}>
            <TaskCard
              task={task}
              grabbed={grabbedId === task.id}
              onGrabToggle={onGrabToggle}
              onKeyDown={onCardKeyDown}
              onRemove={onRemove}
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
              busy={busy}
            />
            {gap(i + 1)}
          </React.Fragment>
        ))}
      </ul>

      {tasks.length === 0 && (
        <p className="py-3 text-[11.5px] text-clay-700">
          Nothing here yet. Drag a topic in, or use Add on a topic in the list.
        </p>
      )}
    </section>
  );
}

DayColumn.propTypes = {
  day: PropTypes.shape({
    date: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    tasks: PropTypes.array,
  }).isRequired,
  isToday: PropTypes.bool,
  grabbedId: PropTypes.string,
  grabbedPlacement: PropTypes.shape({
    date: PropTypes.string,
    index: PropTypes.number,
  }),
  onGrabToggle: PropTypes.func,
  onCardKeyDown: PropTypes.func,
  onRemove: PropTypes.func,
  onDragStart: PropTypes.func,
  onDragEnd: PropTypes.func,
  onDropAt: PropTypes.func,
  busy: PropTypes.bool,
  maxTasks: PropTypes.number,
};
